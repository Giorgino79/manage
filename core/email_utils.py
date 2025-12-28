"""
Utilities per l'invio di email nel sistema procurement.
Gestisce l'invio di email con allegati specifici per automezzi.
"""

import logging
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class ProcurementEmailService:
    """
    Servizio per l'invio di email relative ai procurement.
    """
    
    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@company.com')
    
    def invia_richiesta_preventivo_automezzo(self, richiesta_preventivo, fornitore, automezzo):
        """
        Invia email di richiesta preventivo per automezzo con libretto allegato.
        """
        try:
            # Prepara il contesto per il template
            context = {
                'richiesta': richiesta_preventivo,
                'fornitore': fornitore,
                'automezzo': automezzo,
                'data_invio': timezone.now(),
                'scadenza': richiesta_preventivo.data_scadenza,
            }
            
            # Genera l'email da template
            subject = f"Richiesta Preventivo - {richiesta_preventivo.titolo} - Automezzo {automezzo.targa}"
            html_content = render_to_string('email/richiesta_preventivo_automezzo.html', context)
            text_content = render_to_string('email/richiesta_preventivo_automezzo.txt', context)
            
            # Crea email
            email = EmailMessage(
                subject=subject,
                body=html_content,
                from_email=self.from_email,
                to=[fornitore.email],
                reply_to=[self.from_email]
            )
            email.content_subtype = "html"  # Per HTML
            
            # Allega libretto fronte se disponibile
            if automezzo.libretto_fronte:
                try:
                    email.attach_file(automezzo.libretto_fronte.path)
                    logger.info(f"📎 Libretto fronte allegato per {automezzo.targa}")
                except Exception as e:
                    logger.warning(f"Impossibile allegare libretto fronte per {automezzo.targa}: {e}")
            
            # Allega libretto retro se disponibile
            if automezzo.libretto_retro:
                try:
                    email.attach_file(automezzo.libretto_retro.path)
                    logger.info(f"📎 Libretto retro allegato per {automezzo.targa}")
                except Exception as e:
                    logger.warning(f"Impossibile allegare libretto retro per {automezzo.targa}: {e}")
            
            # Invia email
            email.send()
            
            logger.info(f"✅ Email preventivo inviata a {fornitore.email} per automezzo {automezzo.targa}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Errore invio email preventivo per automezzo {automezzo.targa}: {e}")
            return False
    
    def invia_richiesta_preventivo_stabilimento(self, richiesta_preventivo, fornitore, stabilimento):
        """
        Invia email di richiesta preventivo per stabilimento.
        """
        try:
            # Prepara il contesto per il template
            context = {
                'richiesta': richiesta_preventivo,
                'fornitore': fornitore,
                'stabilimento': stabilimento,
                'data_invio': timezone.now(),
                'scadenza': richiesta_preventivo.data_scadenza,
            }
            
            # Genera l'email da template
            subject = f"Richiesta Preventivo - {richiesta_preventivo.titolo} - Stabilimento {stabilimento.nome}"
            html_content = render_to_string('email/richiesta_preventivo_stabilimento.html', context)
            text_content = render_to_string('email/richiesta_preventivo_stabilimento.txt', context)
            
            # Crea email
            email = EmailMessage(
                subject=subject,
                body=html_content,
                from_email=self.from_email,
                to=[fornitore.email],
                reply_to=[self.from_email]
            )
            email.content_subtype = "html"
            
            # Invia email
            email.send()
            
            logger.info(f"✅ Email preventivo inviata a {fornitore.email} per stabilimento {stabilimento.nome}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Errore invio email preventivo per stabilimento {stabilimento.nome}: {e}")
            return False
    
    def invia_richiesta_preventivo_generico(self, richiesta_preventivo, fornitore):
        """
        Invia email di richiesta preventivo generico (senza asset specifico).
        """
        try:
            # Prepara il contesto per il template
            context = {
                'richiesta': richiesta_preventivo,
                'fornitore': fornitore,
                'data_invio': timezone.now(),
                'scadenza': richiesta_preventivo.data_scadenza,
            }
            
            # Genera l'email da template
            subject = f"Richiesta Preventivo - {richiesta_preventivo.titolo}"
            html_content = render_to_string('email/richiesta_preventivo_generico.html', context)
            
            # Crea email
            email = EmailMessage(
                subject=subject,
                body=html_content,
                from_email=self.from_email,
                to=[fornitore.email],
                reply_to=[self.from_email]
            )
            email.content_subtype = "html"
            
            # Invia email
            email.send()
            
            logger.info(f"✅ Email preventivo generico inviata a {fornitore.email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Errore invio email preventivo generico: {e}")
            return False
    
    def invia_richiesta_preventivo_con_asset(self, richiesta_preventivo, fornitore):
        """
        Metodo intelligente che determina il tipo di asset e invia l'email appropriata.
        """
        if not richiesta_preventivo.target:
            return self.invia_richiesta_preventivo_generico(richiesta_preventivo, fornitore)
        
        target = richiesta_preventivo.target
        
        # Se è un automezzo
        if hasattr(target, 'targa'):
            return self.invia_richiesta_preventivo_automezzo(richiesta_preventivo, fornitore, target)
        
        # Se è uno stabilimento
        elif hasattr(target, 'nome') and 'stabilimento' in target.__class__.__name__.lower():
            return self.invia_richiesta_preventivo_stabilimento(richiesta_preventivo, fornitore, target)
        
        # Fallback generico
        else:
            return self.invia_richiesta_preventivo_generico(richiesta_preventivo, fornitore)
    
    def test_configurazione_email(self):
        """
        Testa la configurazione email.
        """
        try:
            from django.core.mail import get_connection
            connection = get_connection()
            connection.open()
            connection.close()
            logger.info("✅ Configurazione email OK")
            return True
        except Exception as e:
            logger.error(f"❌ Errore configurazione email: {e}")
            return False


# Istanza globale del servizio
procurement_email_service = ProcurementEmailService()


def invia_email_preventivo_automatica(richiesta_preventivo, fornitore):
    """
    Funzione di convenienza per inviare email preventivo automatica.
    """
    return procurement_email_service.invia_richiesta_preventivo_con_asset(
        richiesta_preventivo, fornitore
    )