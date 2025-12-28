from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from stabilimenti.models import DocStabilimento
from core.models import Promemoria

User = get_user_model()


class Command(BaseCommand):
    help = 'Controlla documenti in scadenza nei prossimi 30 giorni e crea promemoria automatici'

    def add_arguments(self, parser):
        parser.add_argument(
            '--giorni',
            type=int,
            default=30,
            help='Numero di giorni di anticipo per le notifiche (default: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Esegue il controllo senza creare promemoria'
        )

    def handle(self, *args, **options):
        giorni_anticipo = options['giorni']
        dry_run = options['dry_run']
        
        oggi = timezone.now().date()
        data_limite = oggi + timedelta(days=giorni_anticipo)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Controllo documenti in scadenza nei prossimi {giorni_anticipo} giorni...'
            )
        )
        
        # Trova documenti in scadenza
        documenti_in_scadenza = DocStabilimento.objects.filter(
            data_scadenza__gte=oggi,
            data_scadenza__lte=data_limite,
            attivo=True
        ).select_related('stabilimento', 'caricato_da').order_by('data_scadenza')
        
        if not documenti_in_scadenza:
            self.stdout.write(
                self.style.SUCCESS('Nessun documento in scadenza trovato.')
            )
            return
        
        self.stdout.write(
            self.style.WARNING(
                f'Trovati {documenti_in_scadenza.count()} documenti in scadenza:'
            )
        )
        
        # Lista documenti per debugging
        for doc in documenti_in_scadenza:
            giorni_rimanenti = (doc.data_scadenza - oggi).days
            self.stdout.write(
                f'  - {doc.nome_documento} ({doc.stabilimento.nome}) - '
                f'Scade il {doc.data_scadenza.strftime("%d/%m/%Y")} '
                f'({giorni_rimanenti} giorni)'
            )
        
        # Trova amministratori e contabili
        destinatari = self._get_destinatari_promemoria()
        
        if not destinatari:
            self.stdout.write(
                self.style.ERROR(
                    'Nessun amministratore o contabile trovato per i promemoria!'
                )
            )
            return
        
        self.stdout.write(
            f'Destinatari promemoria: {", ".join([u.username for u in destinatari])}'
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY-RUN: Nessun promemoria creato.')
            )
            return
        
        # Crea promemoria
        promemoria_creati = self._crea_promemoria(documenti_in_scadenza, destinatari, giorni_anticipo)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Creati {promemoria_creati} promemoria per {documenti_in_scadenza.count()} documenti.'
            )
        )

    def _get_destinatari_promemoria(self):
        """Trova utenti amministratori e contabili per i promemoria"""
        destinatari = []
        
        # Cerca per attributo livello se presente
        if hasattr(User, 'livello'):
            destinatari.extend(
                User.objects.filter(
                    livello__in=['amministratore', 'contabile'],
                    is_active=True
                )
            )
        
        # Fallback: cerca staff e superuser
        if not destinatari:
            destinatari.extend(
                User.objects.filter(
                    is_staff=True,
                    is_active=True
                )
            )
        
        return list(set(destinatari))  # Rimuovi duplicati

    def _crea_promemoria(self, documenti, destinatari, giorni_anticipo):
        """Crea promemoria automatici per i documenti in scadenza"""
        
        oggi = timezone.now().date()
        promemoria_creati = 0
        
        # Crea un promemoria per ogni documento e destinatario
        for doc in documenti:
            giorni_rimanenti = (doc.data_scadenza - oggi).days
            
            # Determina la priorità in base ai giorni rimanenti
            if giorni_rimanenti <= 7:
                priorita = Promemoria.Priorita.ALTA
                urgenza_text = "URGENTE"
            elif giorni_rimanenti <= 15:
                priorita = Promemoria.Priorita.MEDIA
                urgenza_text = "ATTENZIONE"
            else:
                priorita = Promemoria.Priorita.BASSA
                urgenza_text = "PROGRAMMATO"
            
            # Titolo del promemoria
            titolo = f"{urgenza_text}: {doc.nome_documento} in scadenza"
            
            # Descrizione dettagliata
            descrizione = f"""DOCUMENTO IN SCADENZA - {doc.stabilimento.nome}

📄 Documento: {doc.nome_documento}
🏢 Stabilimento: {doc.stabilimento.nome}
📋 Tipo: {doc.get_tipo_documento_display()}
📅 Data scadenza: {doc.data_scadenza.strftime('%d/%m/%Y')}
⏰ Giorni rimanenti: {giorni_rimanenti}
👤 Caricato da: {doc.caricato_da.get_full_name() or doc.caricato_da.username}

Si prega di rinnovare il documento quanto prima per evitare problemi di conformità.

Generato automaticamente il {oggi.strftime('%d/%m/%Y')}"""
            
            # Crea promemoria per ogni destinatario
            for destinatario in destinatari:
                
                # Controlla se esiste già un promemoria simile non completato
                promemoria_esistente = Promemoria.objects.filter(
                    titolo__icontains=doc.nome_documento,
                    assegnato_a=destinatario,
                    completato=False,
                    data_scadenza=doc.data_scadenza
                ).first()
                
                if not promemoria_esistente:
                    # Trova un utente amministratore come creatore (può essere il sistema)
                    creatore = destinatari[0] if destinatari else destinatario
                    
                    promemoria = Promemoria.objects.create(
                        titolo=titolo,
                        descrizione=descrizione,
                        data_scadenza=doc.data_scadenza,
                        priorita=priorita,
                        creato_da=creatore,
                        assegnato_a=destinatario
                    )
                    
                    promemoria_creati += 1
                    
                    self.stdout.write(
                        f'  → Promemoria creato per {destinatario.username}: {titolo}'
                    )
                else:
                    self.stdout.write(
                        f'  ⚠ Promemoria già esistente per {destinatario.username}: {doc.nome_documento}'
                    )
        
        return promemoria_creati