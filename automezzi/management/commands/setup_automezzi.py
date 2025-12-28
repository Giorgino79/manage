# automezzi/management/commands/setup_automezzi.py
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import random

from automezzi.models import (
    TipoCarburante,
    Automezzo,
    DocumentoAutomezzo,
    Manutenzione,
    RifornimentoCarburante,
    EventoAutomezzo,
    StatisticheAutomezzo
)
from dipendenti.models import Dipendente


class Command(BaseCommand):
    help = 'Setup iniziale app automezzi: crea gruppi, permessi e dati di esempio'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-sample-data',
            action='store_true',
            dest='sample_data',
            help='Crea dati di esempio per test'
        )
        parser.add_argument(
            '--create-groups',
            action='store_true',
            dest='create_groups',
            default=True,
            help='Crea gruppi e permessi (default: True)'
        )
        parser.add_argument(
            '--create-carburanti',
            action='store_true',
            dest='create_carburanti',
            default=True,
            help='Crea tipi di carburante base (default: True)'
        )
        parser.add_argument(
            '--no-groups',
            action='store_false',
            dest='create_groups',
            help='Non creare gruppi e permessi'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚗 Inizializzazione App Automezzi...\n')
        )

        # Creazione tipi carburante
        if options['create_carburanti']:
            self.create_tipi_carburante()

        # Creazione gruppi e permessi
        if options['create_groups']:
            self.create_groups_and_permissions()

        # Creazione dati di esempio
        if options['sample_data']:
            self.create_sample_data()

        self.stdout.write(
            self.style.SUCCESS('\n✅ Setup automezzi completato con successo!')
        )

    def create_tipi_carburante(self):
        """Crea i tipi di carburante base"""
        self.stdout.write('🛢️  Creazione tipi carburante...')

        carburanti = [
            {'nome': 'Benzina', 'costo_per_litro': Decimal('1.85')},
            {'nome': 'Diesel', 'costo_per_litro': Decimal('1.75')},
            {'nome': 'GPL', 'costo_per_litro': Decimal('0.85')},
            {'nome': 'Metano', 'costo_per_litro': Decimal('1.15')},
            {'nome': 'Elettrico', 'costo_per_litro': Decimal('0.25')},
        ]

        created_count = 0
        for carburante_data in carburanti:
            carburante, created = TipoCarburante.objects.get_or_create(
                nome=carburante_data['nome'],
                defaults={'costo_per_litro': carburante_data['costo_per_litro']}
            )
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ Creato: {carburante.nome}')
            else:
                self.stdout.write(f'  - Esistente: {carburante.nome}')

        self.stdout.write(f'  📊 Totale creati: {created_count}/5\n')

    def create_groups_and_permissions(self):
        """Crea gruppi e assegna permessi"""
        self.stdout.write('👥 Creazione gruppi e permessi...')

        # Definizione gruppi e permessi
        groups_permissions = {
            'Gestori Automezzi': {
                'description': 'Accesso completo alla gestione automezzi',
                'permissions': [
                    # Automezzi
                    'add_automezzo', 'change_automezzo', 'delete_automezzo', 'view_automezzo',
                    # Documenti
                    'add_documentoautomezzo', 'change_documentoautomezzo', 
                    'delete_documentoautomezzo', 'view_documentoautomezzo',
                    # Manutenzioni
                    'add_manutenzione', 'change_manutenzione', 
                    'delete_manutenzione', 'view_manutenzione',
                    # Rifornimenti
                    'add_rifornimentocarburante', 'change_rifornimentocarburante',
                    'delete_rifornimentocarburante', 'view_rifornimentocarburante',
                    # Eventi
                    'add_eventoautomezzo', 'change_eventoautomezzo',
                    'delete_eventoautomezzo', 'view_eventoautomezzo',
                    # Tipi carburante
                    'add_tipocarburante', 'change_tipocarburante',
                    'delete_tipocarburante', 'view_tipocarburante',
                    # Statistiche
                    'view_statisticheautomezzo',
                ]
            },
            'Operatori Automezzi': {
                'description': 'Gestione operativa automezzi (no eliminazione)',
                'permissions': [
                    # Automezzi - solo lettura e modifica
                    'change_automezzo', 'view_automezzo',
                    # Documenti - gestione completa tranne cancellazione
                    'add_documentoautomezzo', 'change_documentoautomezzo', 'view_documentoautomezzo',
                    # Manutenzioni - gestione completa
                    'add_manutenzione', 'change_manutenzione', 'view_manutenzione',
                    # Rifornimenti - gestione completa
                    'add_rifornimentocarburante', 'change_rifornimentocarburante', 'view_rifornimentocarburante',
                    # Eventi - gestione completa
                    'add_eventoautomezzo', 'change_eventoautomezzo', 'view_eventoautomezzo',
                    # Tipi carburante - solo lettura
                    'view_tipocarburante',
                    # Statistiche - solo lettura
                    'view_statisticheautomezzo',
                ]
            },
            'Autisti': {
                'description': 'Accesso limitato per autisti (solo propri veicoli)',
                'permissions': [
                    # Rifornimenti per i propri veicoli
                    'add_rifornimentocarburante', 'view_rifornimentocarburante',
                    # Eventi per i propri veicoli
                    'add_eventoautomezzo', 'view_eventoautomezzo',
                    # Visualizzazione automezzo assegnato
                    'view_automezzo',
                    # Visualizzazione documenti
                    'view_documentoautomezzo',
                    # Visualizzazione manutenzioni
                    'view_manutenzione',
                ]
            }
        }

        created_groups = 0
        for group_name, group_data in groups_permissions.items():
            group, created = Group.objects.get_or_create(name=group_name)
            
            if created:
                created_groups += 1
                self.stdout.write(f'  ✓ Gruppo creato: {group_name}')
            else:
                self.stdout.write(f'  - Gruppo esistente: {group_name}')

            # Assegna permessi
            permissions_added = 0
            for perm_codename in group_data['permissions']:
                try:
                    # Trova il content type dall'app automezzi
                    content_type = ContentType.objects.get(
                        app_label='automezzi',
                        model=perm_codename.split('_')[1]
                    )
                    permission = Permission.objects.get(
                        codename=perm_codename,
                        content_type=content_type
                    )
                    group.permissions.add(permission)
                    permissions_added += 1
                except (Permission.DoesNotExist, ContentType.DoesNotExist):
                    self.stdout.write(
                        self.style.WARNING(
                            f'    ⚠ Permesso non trovato: {perm_codename}'
                        )
                    )

            self.stdout.write(f'    📝 Permessi assegnati: {permissions_added}')

        self.stdout.write(f'  📊 Gruppi creati: {created_groups}/3\n')

    def create_sample_data(self):
        """Crea dati di esempio per test"""
        self.stdout.write('🔧 Creazione dati di esempio...')

        # Verifica che esistano dipendenti
        dipendenti = list(Dipendente.objects.all()[:5])
        if not dipendenti:
            self.stdout.write(
                self.style.WARNING(
                    '  ⚠ Nessun dipendente trovato. Creando dipendente di test...'
                )
            )
            # Crea dipendente di test
            dipendente_test = Dipendente.objects.create_user(
                username='autista_test',
                email='autista@test.com',
                first_name='Mario',
                last_name='Rossi',
                password='test123'
            )
            dipendenti = [dipendente_test]

        # Verifica che esistano tipi carburante
        carburanti = list(TipoCarburante.objects.all())
        if not carburanti:
            self.create_tipi_carburante()
            carburanti = list(TipoCarburante.objects.all())

        # Dati automezzi di esempio
        automezzi_data = [
            {
                'targa': 'AA123BB',
                'marca': 'Fiat',
                'modello': 'Punto',
                'anno_immatricolazione': 2018,
                'tipo_carburante': 'Benzina',
                'numero_telaio': 'ZFA31200000123456',
                'cilindrata': 1200,
                'potenza': 85,
                'chilometri_iniziali': 25000,
                'chilometri_attuali': 78000,
                'prezzo_acquisto': 15000.00,
                'data_acquisto': date.today() - timedelta(days=365*2),
            },
            {
                'targa': 'BB456CC',
                'marca': 'Ford',
                'modello': 'Focus',
                'anno_immatricolazione': 2020,
                'tipo_carburante': 'Diesel',
                'numero_telaio': 'WF0XXXGCDXKW123456',
                'cilindrata': 1500,
                'potenza': 120,
                'chilometri_iniziali': 10000,
                'chilometri_attuali': 45000,
                'prezzo_acquisto': 22000.00,
                'data_acquisto': date.today() - timedelta(days=365),
            },
            {
                'targa': 'CC789DD',
                'marca': 'Volkswagen',
                'modello': 'Golf',
                'anno_immatricolazione': 2019,
                'tipo_carburante': 'Diesel',
                'numero_telaio': 'WVWZZZ1JZKW123456',
                'cilindrata': 1600,
                'potenza': 105,
                'chilometri_iniziali': 15000,
                'chilometri_attuali': 55000,
                'prezzo_acquisto': 25000.00,
                'data_acquisto': date.today() - timedelta(days=365*1.5),
            }
        ]

        created_automezzi = []
        for i, auto_data in enumerate(automezzi_data):
            # Trova tipo carburante
            tipo_carburante = TipoCarburante.objects.get(
                nome=auto_data['tipo_carburante']
            )
            
            # Assegna dipendente se disponibile
            dipendente = dipendenti[i % len(dipendenti)] if dipendenti else None
            
            automezzo, created = Automezzo.objects.get_or_create(
                targa=auto_data['targa'],
                defaults={
                    'marca': auto_data['marca'],
                    'modello': auto_data['modello'],
                    'anno_immatricolazione': auto_data['anno_immatricolazione'],
                    'tipo_carburante': tipo_carburante,
                    'numero_telaio': auto_data['numero_telaio'],
                    'cilindrata': auto_data['cilindrata'],
                    'potenza': auto_data['potenza'],
                    'chilometri_iniziali': auto_data['chilometri_iniziali'],
                    'chilometri_attuali': auto_data['chilometri_attuali'],
                    'prezzo_acquisto': auto_data['prezzo_acquisto'],
                    'data_acquisto': auto_data['data_acquisto'],
                    'assegnato_a': dipendente,
                    'attivo': True,
                    'disponibile': dipendente is None,
                }
            )
            
            if created:
                created_automezzi.append(automezzo)
                self.stdout.write(f'  ✓ Automezzo creato: {automezzo.targa}')
                
                # Crea documenti per ogni automezzo
                self.create_sample_documents(automezzo)
                
                # Crea manutenzioni
                self.create_sample_maintenances(automezzo, dipendenti)
                
                # Crea rifornimenti
                self.create_sample_refuels(automezzo, dipendenti)
                
                # Crea eventi occasionali
                if random.choice([True, False]):
                    self.create_sample_events(automezzo, dipendenti)
                    
                # Crea/aggiorna statistiche
                self.create_automezzo_statistics(automezzo)
            else:
                self.stdout.write(f'  - Automezzo esistente: {automezzo.targa}')

        self.stdout.write(f'  📊 Automezzi creati: {len(created_automezzi)}/3\n')

    def create_sample_documents(self, automezzo):
        """Crea documenti di esempio per un automezzo"""
        documenti_data = [
            {
                'tipo': 'assicurazione',
                'numero_documento': f'POL-{random.randint(100000, 999999)}',
                'data_rilascio': date.today() - timedelta(days=300),
                'data_scadenza': date.today() + timedelta(days=65),
                'costo': Decimal('450.00'),
            },
            {
                'tipo': 'revisione',
                'numero_documento': f'REV-{random.randint(100000, 999999)}',
                'data_rilascio': date.today() - timedelta(days=200),
                'data_scadenza': date.today() + timedelta(days=165),
                'costo': Decimal('80.00'),
            },
            {
                'tipo': 'bollo',
                'numero_documento': automezzo.targa,
                'data_rilascio': date.today() - timedelta(days=360),
                'data_scadenza': date.today() + timedelta(days=5),
                'costo': Decimal('180.00'),
            },
        ]

        for doc_data in documenti_data:
            DocumentoAutomezzo.objects.get_or_create(
                automezzo=automezzo,
                tipo=doc_data['tipo'],
                defaults=doc_data
            )

    def create_sample_maintenances(self, automezzo, dipendenti):
        """Crea manutenzioni di esempio"""
        # Manutenzione completata
        Manutenzione.objects.get_or_create(
            automezzo=automezzo,
            tipo='tagliando',
            data_prevista=date.today() - timedelta(days=30),
            defaults={
                'descrizione': 'Tagliando 50.000 km',
                'data_effettuata': date.today() - timedelta(days=25),
                'costo_previsto': Decimal('300.00'),
                'costo_effettivo': Decimal('275.00'),
                'completata': True,
                'responsabile': dipendenti[0] if dipendenti else None,
            }
        )

        # Manutenzione programmata
        Manutenzione.objects.get_or_create(
            automezzo=automezzo,
            tipo='ordinaria',
            data_prevista=date.today() + timedelta(days=60),
            defaults={
                'descrizione': 'Controllo generale + cambio olio',
                'costo_previsto': Decimal('150.00'),
                'completata': False,
                'responsabile': dipendenti[0] if dipendenti else None,
            }
        )

    def create_sample_refuels(self, automezzo, dipendenti):
        """Crea rifornimenti di esempio"""
        # Crea 5 rifornimenti negli ultimi 3 mesi
        base_km = automezzo.chilometri_iniziali
        for i in range(5):
            giorni_fa = 90 - (i * 15)  # Ogni 15 giorni circa
            km_percorsi = random.randint(400, 800)
            base_km += km_percorsi
            
            litri = random.uniform(40, 60)
            prezzo_litro = automezzo.tipo_carburante.costo_per_litro + Decimal(random.uniform(-0.1, 0.1))
            costo_totale = Decimal(litri) * prezzo_litro
            
            RifornimentoCarburante.objects.get_or_create(
                automezzo=automezzo,
                data_rifornimento=date.today() - timedelta(days=giorni_fa),
                defaults={
                    'chilometri': int(base_km),
                    'litri': round(litri, 2),
                    'costo_totale': round(costo_totale, 2),
                    'costo_per_litro': round(prezzo_litro, 3),
                    'effettuato_da': dipendenti[0] if dipendenti else None,
                }
            )

        # Aggiorna chilometri automezzo
        automezzo.chilometri_attuali = base_km
        automezzo.save()

    def create_sample_events(self, automezzo, dipendenti):
        """Crea eventi di esempio"""
        eventi_possibili = [
            {
                'tipo': 'multa',
                'descrizione': 'Multa per eccesso di velocità',
                'costo': Decimal('85.00'),
            },
            {
                'tipo': 'sinistro',
                'descrizione': 'Piccolo graffio sul paraurti',
                'costo': Decimal('350.00'),
            },
            {
                'tipo': 'verifica',
                'descrizione': 'Controllo stradale routine',
                'costo': Decimal('0.00'),
            },
        ]

        evento_data = random.choice(eventi_possibili)
        EventoAutomezzo.objects.get_or_create(
            automezzo=automezzo,
            tipo=evento_data['tipo'],
            data_evento=date.today() - timedelta(days=random.randint(10, 60)),
            defaults={
                'descrizione': evento_data['descrizione'],
                'costo': evento_data['costo'],
                'risolto': random.choice([True, False]),
                'dipendente_coinvolto': random.choice(dipendenti) if dipendenti else None,
            }
        )

    def create_automezzo_statistics(self, automezzo):
        """Crea o aggiorna statistiche per un automezzo"""
        # Le statistiche vengono calcolate automaticamente dal modello
        stats, created = StatisticheAutomezzo.objects.get_or_create(
            automezzo=automezzo
        )
        
        # Forza il ricalcolo salvando
        stats.save()

    def handle_error(self, message, exception=None):
        """Gestisce errori con output colorato"""
        self.stdout.write(self.style.ERROR(f'❌ {message}'))
        if exception:
            self.stdout.write(self.style.ERROR(f'   Dettaglio: {str(exception)}'))
        raise CommandError(message)