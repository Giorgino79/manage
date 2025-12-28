"""
Signal handlers per l'automazione del sistema procurement.
Gestisce eventi automatici quando i modelli vengono salvati o modificati.
"""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
import logging

logger = logging.getLogger(__name__)


@receiver(post_save)
def procurement_target_automation_handler(sender, instance, created, **kwargs):
    """
    Signal handler universale per tutti i modelli con ProcurementTargetMixin.
    Si attiva quando un'istanza viene salvata.
    """
    # Verifica se l'istanza ha il mixin ProcurementTargetMixin
    from core.mixins.procurement import ProcurementTargetMixin
    
    if not isinstance(instance, ProcurementTargetMixin):
        return
    
    # Evita ricorsioni infinite disabilitando temporaneamente il signal
    if getattr(instance, '_skip_automation', False):
        return
    
    try:
        logger.debug(f"Signal procurement attivato per {instance}")
        
        # Il mixin gestisce già l'automazione nel suo save()
        # Questo signal è per casi speciali o logging aggiuntivo
        
        # Log dell'evento
        if instance.target:
            logger.info(
                f"🔗 Collegamento procurement: {instance._meta.verbose_name} "
                f"#{instance.pk} → {instance.target_display_name}"
            )
            
    except Exception as e:
        logger.error(f"Errore in procurement signal handler: {e}")


@receiver(post_save)
def allegato_created_handler(sender, instance, created, **kwargs):
    """
    Signal per quando vengono creati nuovi allegati.
    Può triggerare automazioni aggiuntive.
    """
    # Solo per allegati appena creati
    if not created:
        return
    
    # Verifica che sia il modello Allegato
    if sender._meta.app_label != 'core' or sender._meta.model_name != 'allegato':
        return
    
    try:
        # Verifica se l'allegato è collegato a un procurement target
        target = instance.content_object
        
        if target and hasattr(target, 'target_content_type'):
            # È un procurement con target collegato
            logger.info(
                f"📎 Nuovo allegato per procurement: {instance.titolo} "
                f"→ {target} → {getattr(target, 'target_display_name', 'N/A')}"
            )
            
            # Qui potresti triggerare automazioni aggiuntive
            # come notifiche o sincronizzazioni
            
    except Exception as e:
        logger.error(f"Errore in allegato signal handler: {e}")


@receiver(pre_delete)
def procurement_target_cleanup_handler(sender, instance, **kwargs):
    """
    Signal per pulizia quando un procurement target viene eliminato.
    """
    from core.mixins.procurement import ProcurementTargetMixin
    
    if not isinstance(instance, ProcurementTargetMixin):
        return
    
    try:
        if instance.target:
            logger.info(
                f"🗑️ Eliminazione procurement con target: {instance} "
                f"→ {instance.target_display_name}"
            )
            
            # Qui potresti implementare logica di pulizia o notifica
            
    except Exception as e:
        logger.error(f"Errore in procurement cleanup signal: {e}")


def register_automation_signals():
    """
    Funzione per registrare signal personalizzati.
    Può essere chiamata da apps.py se necessario.
    """
    logger.info("Signal automation procurement registrati")


# Signal specifici per modelli

@receiver(post_save, sender='preventivi.RichiestaPreventivo')
def richiesta_preventivo_handler(sender, instance, created, **kwargs):
    """
    Handler specifico per RichiestaPreventivo.
    """
    if created and instance.target:
        logger.info(
            f"💰 Nuova richiesta preventivo collegata: {instance.numero} "
            f"→ {instance.target_display_name}"
        )
        
        # Logica specifica per preventivi
        # Es: notifica al responsabile dell'asset


@receiver(post_save, sender='acquisti.OrdineAcquisto')
def ordine_acquisto_handler(sender, instance, created, **kwargs):
    """
    Handler specifico per OrdineAcquisto.
    """
    if created and instance.target:
        logger.info(
            f"🛒 Nuovo ordine acquisto collegato: {instance.numero_ordine} "
            f"→ {instance.target_display_name}"
        )
        
        # Logica specifica per ordini
        # Es: aggiorna stato asset, crea scheduling manutenzione


# Signal per automazioni avanzate

@receiver(post_save)
def smart_document_attachment_handler(sender, instance, created, **kwargs):
    """
    Handler intelligente per allegamento documenti.
    Analizza il contenuto e decide automazioni appropriate.
    """
    from core.mixins.procurement import ProcurementTargetMixin
    
    if not isinstance(instance, ProcurementTargetMixin) or not instance.target:
        return
    
    try:
        # Analizza il contenuto per automazioni intelligenti
        descrizione = getattr(instance, 'descrizione', '')
        titolo = getattr(instance, 'titolo', '')
        
        keywords_analysis = {
            'manutenzione': ['manutenzione', 'riparazione', 'tagliando', 'revisione'],
            'carburante': ['carburante', 'benzina', 'diesel', 'rifornimento'],
            'assicurazione': ['assicurazione', 'polizza', 'copertura'],
            'software': ['software', 'licenza', 'programma', 'applicazione'],
            'hardware': ['hardware', 'computer', 'stampante', 'monitor']
        }
        
        detected_categories = []
        full_text = f"{titolo} {descrizione}".lower()
        
        for category, keywords in keywords_analysis.items():
            if any(keyword in full_text for keyword in keywords):
                detected_categories.append(category)
        
        if detected_categories:
            logger.info(
                f"🤖 Automazione smart: {instance} "
                f"→ Categorie rilevate: {', '.join(detected_categories)}"
            )
            
            # Qui puoi implementare automazioni specifiche per categoria
            _handle_category_automation(instance, detected_categories)
            
    except Exception as e:
        logger.error(f"Errore in smart automation handler: {e}")


def _handle_category_automation(procurement_instance, categories):
    """
    Gestisce automazioni specifiche per categoria.
    """
    target = procurement_instance.target
    
    for category in categories:
        if category == 'manutenzione' and hasattr(target, 'targa'):
            # Per automezzi: logica manutenzione
            _handle_automezzo_manutenzione(procurement_instance, target)
            
        elif category == 'carburante' and hasattr(target, 'targa'):
            # Per automezzi: logica carburante
            _handle_automezzo_carburante(procurement_instance, target)
            
        elif category == 'software' and hasattr(target, 'nome'):
            # Per stabilimenti: logica software
            _handle_software_licensing(procurement_instance, target)


def _handle_automezzo_manutenzione(procurement, automezzo):
    """
    Automazione specifica per manutenzioni automezzi.
    """
    logger.info(f"🔧 Automazione manutenzione per automezzo {automezzo.targa}")
    
    # Esempio: crea promemoria per follow-up
    # Esempio: aggiorna kilometraggio se specificato
    # Esempio: pianifica prossima manutenzione


def _handle_automezzo_carburante(procurement, automezzo):
    """
    Automazione specifica per rifornimenti automezzi.
    """
    logger.info(f"⛽ Automazione carburante per automezzo {automezzo.targa}")
    
    # Esempio: crea record rifornimento automatico
    # Esempio: aggiorna consumi


def _handle_software_licensing(procurement, stabilimento):
    """
    Automazione specifica per licensing software.
    """
    logger.info(f"💻 Automazione software per stabilimento {stabilimento.nome}")
    
    # Esempio: crea record licenza
    # Esempio: pianifica rinnovo


# Utilities per signal management

def disable_automation_signals():
    """
    Disabilita temporaneamente i signal di automazione.
    Utile per import di massa o operazioni batch.
    """
    import django.db.models.signals as signals
    
    signals.post_save.disconnect(procurement_target_automation_handler)
    signals.post_save.disconnect(allegato_created_handler)
    signals.pre_delete.disconnect(procurement_target_cleanup_handler)
    
    logger.warning("⚠️ Signal automazione procurement disabilitati")


def enable_automation_signals():
    """
    Riabilita i signal di automazione.
    """
    import django.db.models.signals as signals
    
    signals.post_save.connect(procurement_target_automation_handler)
    signals.post_save.connect(allegato_created_handler)
    signals.pre_delete.connect(procurement_target_cleanup_handler)
    
    logger.info("✅ Signal automazione procurement riabilitati")


class DisableAutomationContext:
    """
    Context manager per disabilitare temporaneamente l'automazione.
    
    Usage:
        with DisableAutomationContext():
            # Operazioni senza automazione
            pass
    """
    
    def __enter__(self):
        disable_automation_signals()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        enable_automation_signals()


def mark_instance_skip_automation(instance):
    """
    Marca un'istanza per saltare l'automazione nel prossimo save.
    """
    instance._skip_automation = True
    return instance