from django.apps import AppConfig


class StabilimentiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "stabilimenti"
    verbose_name = 'Gestione Stabilimenti'
    
    def ready(self):
        """
        Chiamato quando l'app è pronta.
        Registra automaticamente il modello Stabilimento come target procurement.
        """
        try:
            from core.registry import procurement_target_registry
            from .models import Stabilimento
            
            # Registra Stabilimento come target procurement
            procurement_target_registry.register(
                Stabilimento,
                display_name="Stabilimento",
                icon="fas fa-building",
                description="Stabilimenti e sedi aziendali",
                form_widget_config={
                    'search_fields': ['nome', 'indirizzo', 'citta'],
                    'display_field': 'nome',
                    'default_filters': {'attivo': True}
                },
                automation_config={
                    'auto_attach_documents': True,
                    'create_notification': True,
                    'sync_metadata': True
                }
            )
            
        except Exception as e:
            # Non bloccare l'avvio se ci sono errori di registrazione
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Errore registrazione procurement target per stabilimenti: {e}")
