# automezzi/management/commands/import_carburanti.py
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from decimal import Decimal, InvalidOperation
import csv
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date
import os
import tempfile

from automezzi.models import TipoCarburante


class Command(BaseCommand):
    help = 'Importa tipi di carburante e prezzi da varie fonti (CSV, JSON, API, XML)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Path al file da importare (CSV, JSON, XML)'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['csv', 'json', 'xml', 'api'],
            help='Formato del file o fonte dati'
        )
        parser.add_argument(
            '--api-url',
            type=str,
            help='URL API per importazione automatica prezzi'
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Aggiorna carburanti esistenti'
        )
        parser.add_argument(
            '--create-missing',
            action='store_true',
            default=True,
            help='Crea carburanti mancanti (default: True)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra cosa verrebbe importato senza salvare'
        )
        parser.add_argument(
            '--backup',
            action='store_true',
            help='Crea backup prima dell\'importazione'
        )
        parser.add_argument(
            '--preset',
            type=str,
            choices=['italia', 'europa', 'basic'],
            help='Usa preset predefiniti per prezzi'
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.update_existing = options['update_existing']
        self.create_missing = options['create_missing']
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 MODALITÀ DRY-RUN - Nessuna modifica verrà salvata\n')
            )

        self.stdout.write(
            self.style.SUCCESS('⛽ Import Carburanti e Prezzi...\n')
        )

        # Backup se richiesto
        if options['backup']:
            self.create_backup()

        try:
            # Determina metodo di importazione
            if options['preset']:
                data = self.load_preset_data(options['preset'])
                self.import_data(data)
            elif options['api_url']:
                data = self.fetch_from_api(options['api_url'])
                self.import_data(data)
            elif options['file']:
                if not options['format']:
                    # Auto-detect formato dal file
                    options['format'] = self.detect_file_format(options['file'])
                data = self.load_file_data(options['file'], options['format'])
                self.import_data(data)
            else:
                # Default: usa preset italia
                self.stdout.write('📍 Nessuna fonte specificata, uso preset Italia')
                data = self.load_preset_data('italia')
                self.import_data(data)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Errore durante l\'importazione: {str(e)}')
            )
            raise CommandError(f'Import fallito: {str(e)}')

    def create_backup(self):
        """Crea backup dei dati esistenti"""
        self.stdout.write('💾 Creazione backup...')
        
        backup_data = []
        for carburante in TipoCarburante.objects.all():
            backup_data.append({
                'nome': carburante.nome,
                'costo_per_litro': float(carburante.costo_per_litro),
                'data_backup': datetime.now().isoformat()
            })
        
        # Salva backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'backup_carburanti_{timestamp}.json'
        
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        self.stdout.write(f'  ✓ Backup salvato: {backup_file}\n')

    def detect_file_format(self, filepath):
        """Auto-rileva il formato del file"""
        ext = os.path.splitext(filepath)[1].lower()
        format_map = {
            '.csv': 'csv',
            '.json': 'json',
            '.xml': 'xml'
        }
        return format_map.get(ext, 'csv')

    def load_preset_data(self, preset):
        """Carica dati preset predefiniti"""
        self.stdout.write(f'📋 Caricamento preset: {preset}')
        
        presets = {
            'basic': [
                {'nome': 'Benzina', 'costo_per_litro': 1.80},
                {'nome': 'Diesel', 'costo_per_litro': 1.70},
                {'nome': 'GPL', 'costo_per_litro': 0.80},
                {'nome': 'Metano', 'costo_per_litro': 1.10},
            ],
            'italia': [
                {'nome': 'Benzina 95', 'costo_per_litro': 1.85},
                {'nome': 'Benzina 98', 'costo_per_litro': 1.95},
                {'nome': 'Diesel', 'costo_per_litro': 1.75},
                {'nome': 'Diesel AdBlue', 'costo_per_litro': 1.80},
                {'nome': 'GPL', 'costo_per_litro': 0.85},
                {'nome': 'Metano', 'costo_per_litro': 1.15},
                {'nome': 'Elettrico', 'costo_per_litro': 0.25},
            ],
            'europa': [
                {'nome': 'Petrol', 'costo_per_litro': 1.60},
                {'nome': 'Diesel', 'costo_per_litro': 1.45},
                {'nome': 'LPG', 'costo_per_litro': 0.75},
                {'nome': 'CNG', 'costo_per_litro': 1.05},
                {'nome': 'Electric', 'costo_per_litro': 0.30},
                {'nome': 'Hydrogen', 'costo_per_litro': 8.50},
            ]
        }
        
        data = presets.get(preset, presets['basic'])
        self.stdout.write(f'  ✓ {len(data)} carburanti caricati\n')
        return data

    def fetch_from_api(self, api_url):
        """Scarica dati da API esterna"""
        self.stdout.write(f'🌐 Connessione API: {api_url}')
        
        try:
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            
            # Prova a interpretare come JSON
            try:
                data = response.json()
                self.stdout.write('  ✓ Dati JSON ricevuti')
            except json.JSONDecodeError:
                # Prova come testo/CSV
                data = self.parse_csv_text(response.text)
                self.stdout.write('  ✓ Dati CSV ricevuti')
            
            return self.normalize_api_data(data)
            
        except requests.RequestException as e:
            raise CommandError(f'Errore connessione API: {str(e)}')

    def load_file_data(self, filepath, format_type):
        """Carica dati da file locale"""
        self.stdout.write(f'📁 Caricamento file: {filepath} (formato: {format_type})')
        
        if not os.path.exists(filepath):
            raise CommandError(f'File non trovato: {filepath}')
        
        loaders = {
            'csv': self.load_csv_file,
            'json': self.load_json_file,
            'xml': self.load_xml_file
        }
        
        loader = loaders.get(format_type)
        if not loader:
            raise CommandError(f'Formato non supportato: {format_type}')
        
        return loader(filepath)

    def load_csv_file(self, filepath):
        """Carica dati da file CSV"""
        data = []
        encodings = ['utf-8', 'utf-8-sig', 'iso-8859-1', 'windows-1252']
        
        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding) as csvfile:
                    # Auto-detect delimiter
                    sample = csvfile.read(1024)
                    csvfile.seek(0)
                    sniffer = csv.Sniffer()
                    delimiter = sniffer.sniff(sample).delimiter
                    
                    reader = csv.DictReader(csvfile, delimiter=delimiter)
                    for row in reader:
                        # Normalizza nomi colonne (case-insensitive)
                        normalized_row = {k.lower().strip(): v.strip() for k, v in row.items()}
                        data.append(self.parse_csv_row(normalized_row))
                    
                    self.stdout.write(f'  ✓ {len(data)} righe caricate (encoding: {encoding})')
                    return data
                    
            except UnicodeDecodeError:
                continue
            except Exception as e:
                self.stdout.write(f'  ⚠ Errore con encoding {encoding}: {str(e)}')
                continue
        
        raise CommandError('Impossibile leggere il file CSV con encoding supportati')

    def parse_csv_row(self, row):
        """Analizza riga CSV e estrae dati carburante"""
        # Possibili nomi per le colonne
        nome_fields = ['nome', 'name', 'tipo', 'type', 'carburante', 'fuel']
        prezzo_fields = ['prezzo', 'price', 'costo', 'cost', 'costo_per_litro', 'price_per_liter']
        
        # Trova nome carburante
        nome = None
        for field in nome_fields:
            if field in row and row[field]:
                nome = row[field]
                break
        
        # Trova prezzo
        prezzo = None
        for field in prezzo_fields:
            if field in row and row[field]:
                prezzo_str = row[field].replace(',', '.').replace('€', '').strip()
                try:
                    prezzo = float(prezzo_str)
                    break
                except ValueError:
                    continue
        
        if not nome:
            raise ValueError(f'Nome carburante non trovato in riga: {row}')
        if prezzo is None:
            raise ValueError(f'Prezzo non valido per {nome}: {row}')
        
        return {
            'nome': nome,
            'costo_per_litro': prezzo
        }

    def load_json_file(self, filepath):
        """Carica dati da file JSON"""
        with open(filepath, 'r', encoding='utf-8') as jsonfile:
            json_data = json.load(jsonfile)
        
        # Gestisci diverse strutture JSON
        if isinstance(json_data, list):
            data = json_data
        elif isinstance(json_data, dict):
            # Prova chiavi comuni
            for key in ['carburanti', 'fuels', 'data', 'items']:
                if key in json_data:
                    data = json_data[key]
                    break
            else:
                # Tratta il dict come singolo carburante
                data = [json_data]
        else:
            raise ValueError('Formato JSON non riconosciuto')
        
        # Normalizza struttura
        normalized_data = []
        for item in data:
            if 'nome' in item and 'costo_per_litro' in item:
                normalized_data.append({
                    'nome': item['nome'],
                    'costo_per_litro': float(item['costo_per_litro'])
                })
            elif 'name' in item and 'price' in item:
                normalized_data.append({
                    'nome': item['name'],
                    'costo_per_litro': float(item['price'])
                })
        
        self.stdout.write(f'  ✓ {len(normalized_data)} carburanti caricati')
        return normalized_data

    def load_xml_file(self, filepath):
        """Carica dati da file XML"""
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        data = []
        
        # Prova strutture XML comuni
        for fuel_elem in root.findall('.//carburante') or root.findall('.//fuel'):
            nome = fuel_elem.find('nome') or fuel_elem.find('name')
            prezzo = fuel_elem.find('prezzo') or fuel_elem.find('price') or fuel_elem.find('costo_per_litro')
            
            if nome is not None and prezzo is not None:
                data.append({
                    'nome': nome.text.strip(),
                    'costo_per_litro': float(prezzo.text.strip())
                })
        
        # Alternativa: attributi XML
        if not data:
            for fuel_elem in root.findall('.//*[@nome][@prezzo]'):
                data.append({
                    'nome': fuel_elem.get('nome'),
                    'costo_per_litro': float(fuel_elem.get('prezzo'))
                })
        
        self.stdout.write(f'  ✓ {len(data)} carburanti caricati')
        return data

    def normalize_api_data(self, api_data):
        """Normalizza dati ricevuti da API"""
        # Questo metodo dovrebbe essere personalizzato in base alle API specifiche
        # Esempio per API generica
        
        if isinstance(api_data, list):
            return [self.normalize_fuel_item(item) for item in api_data]
        elif isinstance(api_data, dict):
            if 'fuels' in api_data:
                return [self.normalize_fuel_item(item) for item in api_data['fuels']]
            else:
                return [self.normalize_fuel_item(api_data)]
        
        return []

    def normalize_fuel_item(self, item):
        """Normalizza singolo elemento carburante"""
        # Mappa campi comuni
        name_fields = ['name', 'nome', 'type', 'fuel_type']
        price_fields = ['price', 'prezzo', 'cost', 'costo_per_litro']
        
        nome = None
        for field in name_fields:
            if field in item:
                nome = str(item[field]).strip()
                break
        
        prezzo = None
        for field in price_fields:
            if field in item:
                try:
                    prezzo = float(item[field])
                    break
                except (ValueError, TypeError):
                    continue
        
        if not nome or prezzo is None:
            raise ValueError(f'Dati incompleti per carburante: {item}')
        
        return {
            'nome': nome,
            'costo_per_litro': prezzo
        }

    def parse_csv_text(self, csv_text):
        """Analizza testo CSV ricevuto da API"""
        lines = csv_text.strip().split('\n')
        if not lines:
            return []
        
        # Usa StringIO per simulare file
        from io import StringIO
        csvfile = StringIO(csv_text)
        reader = csv.DictReader(csvfile)
        
        data = []
        for row in reader:
            try:
                data.append(self.parse_csv_row(row))
            except ValueError as e:
                self.stdout.write(f'  ⚠ Riga ignorata: {str(e)}')
                continue
        
        return data

    def import_data(self, data):
        """Importa/aggiorna dati carburanti"""
        self.stdout.write(f'🔄 Importazione {len(data)} carburanti...')
        
        stats = {
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        with transaction.atomic():
            for fuel_data in data:
                try:
                    result = self.process_fuel(fuel_data)
                    stats[result] += 1
                    
                    # Log dettagliato
                    nome = fuel_data['nome']
                    prezzo = fuel_data['costo_per_litro']
                    
                    if result == 'created':
                        self.stdout.write(f'  ✓ Creato: {nome} - €{prezzo:.3f}/L')
                    elif result == 'updated':
                        self.stdout.write(f'  🔄 Aggiornato: {nome} - €{prezzo:.3f}/L')
                    elif result == 'skipped':
                        self.stdout.write(f'  ⏭ Saltato: {nome} (esistente)')
                    
                except Exception as e:
                    stats['errors'] += 1
                    self.stdout.write(
                        self.style.ERROR(f'  ❌ Errore {fuel_data.get("nome", "?")}: {str(e)}')
                    )
            
            # Rollback se dry-run
            if self.dry_run:
                transaction.set_rollback(True)
                self.stdout.write('\n🔍 [DRY-RUN] Modifiche non salvate')
        
        # Riepilogo
        self.print_import_summary(stats)

    def process_fuel(self, fuel_data):
        """Processa singolo carburante"""
        nome = fuel_data['nome']
        prezzo = Decimal(str(fuel_data['costo_per_litro']))
        
        try:
            carburante = TipoCarburante.objects.get(nome=nome)
            # Carburante esistente
            if self.update_existing:
                if carburante.costo_per_litro != prezzo:
                    carburante.costo_per_litro = prezzo
                    carburante.save()
                    return 'updated'
                else:
                    return 'skipped'
            else:
                return 'skipped'
                
        except TipoCarburante.DoesNotExist:
            # Carburante nuovo
            if self.create_missing:
                TipoCarburante.objects.create(
                    nome=nome,
                    costo_per_litro=prezzo
                )
                return 'created'
            else:
                return 'skipped'

    def print_import_summary(self, stats):
        """Stampa riepilogo importazione"""
        self.stdout.write('\n' + '='*40)
        self.stdout.write(self.style.SUCCESS('📊 RIEPILOGO IMPORTAZIONE'))
        self.stdout.write('='*40)
        
        total = sum(stats.values())
        
        self.stdout.write(f'📈 Totale processati: {total}')
        self.stdout.write(f'✨ Creati: {stats["created"]}')
        self.stdout.write(f'🔄 Aggiornati: {stats["updated"]}')
        self.stdout.write(f'⏭ Saltati: {stats["skipped"]}')
        
        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errori: {stats["errors"]}'))
        
        # Percentuale successo
        if total > 0:
            success = stats['created'] + stats['updated']
            success_rate = (success / total) * 100
            self.stdout.write(f'✅ Successo: {success_rate:.1f}%')
        
        # Stato finale
        if stats['errors'] == 0:
            self.stdout.write(self.style.SUCCESS('\n🎉 Importazione completata!'))
        else:
            self.stdout.write(self.style.WARNING(f'\n⚠ Completata con {stats["errors"]} errori'))
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('🔍 MODALITÀ DRY-RUN: Nessuna modifica salvata'))
        
        self.stdout.write('='*40 + '\n')