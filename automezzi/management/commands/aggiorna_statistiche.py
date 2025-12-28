# automezzi/management/commands/aggiorna_statistiche.py
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Sum, Avg, Q, Max, Min
from django.utils import timezone
from datetime import date, timedelta, datetime
from decimal import Decimal

from automezzi.models import (
    Automezzo,
    StatisticheAutomezzo,
    RifornimentoCarburante,
    Manutenzione,
    DocumentoAutomezzo,
    EventoAutomezzo
)


class Command(BaseCommand):
    help = 'Aggiorna le statistiche degli automezzi: consumi, costi, scadenze'

    def add_arguments(self, parser):
        parser.add_argument(
            '--automezzo',
            type=str,
            help='Aggiorna solo l\'automezzo specificato (targa)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forza l\'aggiornamento anche se recente'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Output dettagliato per ogni automezzo'
        )
        parser.add_argument(
            '--periodo-consumi',
            type=int,
            default=365,
            help='Giorni da considerare per calcolo consumi (default: 365)'
        )
        parser.add_argument(
            '--periodo-manutenzioni',
            type=int,
            default=365,
            help='Giorni da considerare per costi manutenzioni (default: 365)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra cosa verrebbe fatto senza salvare'
        )

    def handle(self, *args, **options):
        self.verbosity = options['verbosity']
        self.verbose = options['verbose']
        self.dry_run = options['dry_run']
        self.force = options['force']
        self.periodo_consumi = options['periodo_consumi']
        self.periodo_manutenzioni = options['periodo_manutenzioni']

        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 MODALITÀ DRY-RUN - Nessuna modifica verrà salvata\n')
            )

        self.stdout.write(
            self.style.SUCCESS('📊 Aggiornamento Statistiche Automezzi...\n')
        )

        # Determina quali automezzi processare
        if options['automezzo']:
            try:
                automezzi = [Automezzo.objects.get(targa=options['automezzo'])]
                self.stdout.write(f'🎯 Aggiornamento singolo automezzo: {options["automezzo"]}\n')
            except Automezzo.DoesNotExist:
                raise CommandError(f'Automezzo con targa "{options["automezzo"]}" non trovato')
        else:
            automezzi = Automezzo.objects.filter(attivo=True)
            self.stdout.write(f'🚗 Aggiornamento tutti gli automezzi attivi: {automezzi.count()}\n')

        # Statistiche globali
        total_processed = 0
        total_updated = 0
        total_created = 0
        total_errors = 0

        # Processa ogni automezzo
        for automezzo in automezzi:
            try:
                if self.verbose:
                    self.stdout.write(f'\n🔧 Processando: {automezzo.targa} ({automezzo.marca} {automezzo.modello})')
                
                result = self.update_automezzo_statistics(automezzo)
                total_processed += 1
                
                if result['created']:
                    total_created += 1
                elif result['updated']:
                    total_updated += 1
                    
                if self.verbose and result['details']:
                    for detail in result['details']:
                        self.stdout.write(f'  {detail}')
                        
            except Exception as e:
                total_errors += 1
                self.stdout.write(
                    self.style.ERROR(f'❌ Errore per {automezzo.targa}: {str(e)}')
                )
                if self.verbosity >= 2:
                    import traceback
                    self.stdout.write(traceback.format_exc())

        # Riepilogo finale
        self.print_summary(total_processed, total_created, total_updated, total_errors)

    def update_automezzo_statistics(self, automezzo):
        """Aggiorna le statistiche per un singolo automezzo"""
        result = {
            'created': False,
            'updated': False,
            'details': []
        }

        # Ottieni o crea record statistiche
        stats, created = StatisticheAutomezzo.objects.get_or_create(
            automezzo=automezzo
        )
        
        if created:
            result['created'] = True
            result['details'].append('✨ Record statistiche creato')
        
        # Verifica se aggiornamento necessario
        if not self.force and not created:
            # Controlla se ultimo aggiornamento è recente (< 1 ora)
            if stats.data_aggiornamento:
                time_diff = timezone.now() - stats.data_aggiornamento
                if time_diff < timedelta(hours=1):
                    result['details'].append(f'⏭️  Saltato (aggiornato {time_diff.seconds//60} min fa)')
                    return result

        # Calcola nuove statistiche
        old_values = {
            'consumo_medio': stats.consumo_medio,
            'costo_km_carburante': stats.costo_km_carburante,
            'costo_manutenzioni_anno': stats.costo_manutenzioni_anno,
        }

        # 1. Calcola consumo medio
        consumo_info = self.calculate_consumo_medio(automezzo)
        if consumo_info['consumo']:
            stats.consumo_medio = consumo_info['consumo']
            result['details'].append(f'⛽ Consumo medio: {consumo_info["consumo"]:.2f} L/100km')
            
        # 2. Calcola costo per km (carburante)
        costo_km_info = self.calculate_costo_per_km(automezzo)
        if costo_km_info['costo_km']:
            stats.costo_km_carburante = costo_km_info['costo_km']
            result['details'].append(f'💰 Costo carburante: €{costo_km_info["costo_km"]:.3f}/km')

        # 3. Calcola costi manutenzioni annuali
        costo_manutenzioni = self.calculate_costo_manutenzioni_annuali(automezzo)
        if costo_manutenzioni['costo_annuale'] is not None:
            stats.costo_manutenzioni_anno = costo_manutenzioni['costo_annuale']
            result['details'].append(f'🔧 Manutenzioni/anno: €{costo_manutenzioni["costo_annuale"]:.2f}')

        # 4. Aggiorna date ultime operazioni
        ultimo_rifornimento = self.get_ultimo_rifornimento(automezzo)
        if ultimo_rifornimento:
            stats.ultimo_rifornimento = ultimo_rifornimento
            result['details'].append(f'⛽ Ultimo rifornimento: {ultimo_rifornimento}')

        ultima_manutenzione = self.get_ultima_manutenzione(automezzo)
        if ultima_manutenzione:
            stats.ultima_manutenzione = ultima_manutenzione
            result['details'].append(f'🔧 Ultima manutenzione: {ultima_manutenzione}')

        # 5. Calcola statistiche aggiuntive
        additional_stats = self.calculate_additional_statistics(automezzo)
        
        # Determina se ci sono stati cambiamenti significativi
        changes_detected = False
        for key, old_value in old_values.items():
            new_value = getattr(stats, key)
            if old_value != new_value:
                changes_detected = True
                break

        # Salva solo se necessario e non in modalità dry-run
        if (changes_detected or created) and not self.dry_run:
            stats.data_aggiornamento = timezone.now()
            stats.save()
            result['updated'] = True
            result['details'].append('💾 Statistiche salvate')
        elif self.dry_run:
            result['details'].append('🔍 [DRY-RUN] Modifiche non salvate')
        else:
            result['details'].append('📊 Nessuna modifica necessaria')

        return result

    def calculate_consumo_medio(self, automezzo):
        """Calcola il consumo medio dell'automezzo"""
        result = {'consumo': None, 'rifornimenti_analizzati': 0}
        
        # Data limite per il calcolo
        data_limite = date.today() - timedelta(days=self.periodo_consumi)
        
        # Ottieni rifornimenti ordinati per data
        rifornimenti = RifornimentoCarburante.objects.filter(
            automezzo=automezzo,
            data_rifornimento__gte=data_limite
        ).order_by('data_rifornimento')

        if rifornimenti.count() < 2:
            return result

        consumi = []
        rifornimento_precedente = None

        for rifornimento in rifornimenti:
            if rifornimento_precedente:
                km_percorsi = rifornimento.chilometri - rifornimento_precedente.chilometri
                if km_percorsi > 0:
                    # Calcola consumo per 100km
                    consumo = (rifornimento.litri / km_percorsi) * 100
                    # Filtro valori anomali (consumo troppo alto o basso)
                    if 2 <= consumo <= 50:
                        consumi.append(consumo)
                        result['rifornimenti_analizzati'] += 1
            
            rifornimento_precedente = rifornimento

        if consumi:
            # Calcola media escludendo valori estremi (outliers)
            consumi.sort()
            # Rimuovi 10% dei valori estremi da entrambi i lati
            n = len(consumi)
            start_idx = max(0, int(n * 0.1))
            end_idx = min(n, int(n * 0.9))
            if end_idx > start_idx:
                consumi_filtrati = consumi[start_idx:end_idx]
                result['consumo'] = Decimal(str(round(sum(consumi_filtrati) / len(consumi_filtrati), 2)))

        return result

    def calculate_costo_per_km(self, automezzo):
        """Calcola il costo per chilometro del carburante"""
        result = {'costo_km': None, 'km_totali': 0, 'costo_totale': 0}
        
        # Data limite per il calcolo
        data_limite = date.today() - timedelta(days=self.periodo_consumi)
        
        # Somma tutti i rifornimenti nel periodo
        rifornimenti_data = RifornimentoCarburante.objects.filter(
            automezzo=automezzo,
            data_rifornimento__gte=data_limite
        ).aggregate(
            costo_totale=Sum('costo_totale'),
            primo_km=Min('chilometri'),
            ultimo_km=Max('chilometri')
        )

        if (rifornimenti_data['costo_totale'] and 
            rifornimenti_data['primo_km'] and 
            rifornimenti_data['ultimo_km']):
            
            km_totali = rifornimenti_data['ultimo_km'] - rifornimenti_data['primo_km']
            if km_totali > 0:
                costo_per_km = rifornimenti_data['costo_totale'] / km_totali
                result['costo_km'] = round(costo_per_km, 3)
                result['km_totali'] = km_totali
                result['costo_totale'] = rifornimenti_data['costo_totale']

        return result

    def calculate_costo_manutenzioni_annuali(self, automezzo):
        """Calcola il costo annuale delle manutenzioni"""
        result = {'costo_annuale': None, 'manutenzioni': 0}
        
        # Data limite per il calcolo
        data_limite = date.today() - timedelta(days=self.periodo_manutenzioni)
        
        # Calcola costo manutenzioni completate nel periodo
        manutenzioni_data = Manutenzione.objects.filter(
            automezzo=automezzo,
            completata=True,
            data_effettuata__gte=data_limite,
            costo_effettivo__isnull=False
        ).aggregate(
            costo_totale=Sum('costo_effettivo'),
            count=Count('id')
        )

        if manutenzioni_data['costo_totale']:
            result['manutenzioni'] = manutenzioni_data['count']
            
            # Normalizza su base annuale
            giorni_analizzati = self.periodo_manutenzioni
            if giorni_analizzati < 365:
                # Se il periodo è inferiore a un anno, proietta il costo
                fattore_annuale = 365 / giorni_analizzati
                costo_annuale = manutenzioni_data['costo_totale'] * fattore_annuale
            else:
                # Se il periodo è un anno o più, calcola la media annuale
                anni_analizzati = giorni_analizzati / 365
                costo_annuale = manutenzioni_data['costo_totale'] / anni_analizzati
            
            result['costo_annuale'] = round(costo_annuale, 2)

        return result

    def get_ultimo_rifornimento(self, automezzo):
        """Ottieni data ultimo rifornimento"""
        ultimo = RifornimentoCarburante.objects.filter(
            automezzo=automezzo
        ).order_by('-data_rifornimento').first()
        
        return ultimo.data_rifornimento if ultimo else None

    def get_ultima_manutenzione(self, automezzo):
        """Ottieni data ultima manutenzione completata"""
        ultima = Manutenzione.objects.filter(
            automezzo=automezzo,
            completata=True
        ).order_by('-data_effettuata').first()
        
        return ultima.data_effettuata if ultima else None

    def calculate_additional_statistics(self, automezzo):
        """Calcola statistiche aggiuntive utili"""
        stats = {}
        
        # Numero di eventi per tipo
        eventi_count = EventoAutomezzo.objects.filter(
            automezzo=automezzo
        ).values('tipo').annotate(
            count=Count('id')
        )
        
        # Scadenze prossime
        today = date.today()
        scadenze_prossime = DocumentoAutomezzo.objects.filter(
            automezzo=automezzo,
            data_scadenza__gte=today,
            data_scadenza__lte=today + timedelta(days=90)
        ).count()
        
        # Età veicolo
        if automezzo.anno_immatricolazione:
            eta_anni = today.year - automezzo.anno_immatricolazione
            stats['eta_anni'] = eta_anni
        
        # Chilometraggio medio annuale
        if automezzo.data_acquisto:
            giorni_possesso = (today - automezzo.data_acquisto).days
            if giorni_possesso > 0:
                km_totali = automezzo.chilometri_attuali - automezzo.chilometri_iniziali
                km_anno = (km_totali / giorni_possesso) * 365
                stats['km_anno_medio'] = round(km_anno, 0)
        
        return stats

    def print_summary(self, processed, created, updated, errors):
        """Stampa riepilogo finale"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('📈 RIEPILOGO AGGIORNAMENTO STATISTICHE'))
        self.stdout.write('='*50)
        
        # Statistiche principali
        self.stdout.write(f'📊 Automezzi processati: {processed}')
        self.stdout.write(f'✨ Statistiche create: {created}')
        self.stdout.write(f'🔄 Statistiche aggiornate: {updated}')
        self.stdout.write(f'⏭️  Nessuna modifica: {processed - created - updated - errors}')
        
        if errors > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errori: {errors}'))
        
        # Percentuali di successo
        if processed > 0:
            success_rate = ((processed - errors) / processed) * 100
            self.stdout.write(f'✅ Tasso di successo: {success_rate:.1f}%')
        
        # Messaggi finali
        if errors == 0:
            self.stdout.write(self.style.SUCCESS('\n🎉 Aggiornamento completato con successo!'))
        else:
            self.stdout.write(self.style.WARNING(f'\n⚠️  Aggiornamento completato con {errors} errori'))
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('🔍 MODALITÀ DRY-RUN: Nessuna modifica è stata salvata'))
        
        self.stdout.write('='*50 + '\n')

    def log_detail(self, message, level='info'):
        """Log dettagliato condizionale"""
        if self.verbose:
            if level == 'error':
                self.stdout.write(self.style.ERROR(f'    ❌ {message}'))
            elif level == 'warning':
                self.stdout.write(self.style.WARNING(f'    ⚠️  {message}'))
            elif level == 'success':
                self.stdout.write(self.style.SUCCESS(f'    ✅ {message}'))
            else:
                self.stdout.write(f'    ℹ️  {message}')