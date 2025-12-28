from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = 'Sistema Core'
    
    def ready(self):
        """
        Chiamato quando l'app è pronta.
        Registra i signal handlers per l'automazione.
        """
        try:
            # Importa e registra i signal handlers
            from . import signals
            signals.register_automation_signals()
            
            # Auto-registra target comuni se disponibili
            from .registry import auto_register_common_targets
            auto_register_common_targets()
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Errore durante inizializzazione core app: {e}")
