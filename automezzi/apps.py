from django.apps import AppConfig


class AutomezziConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'automezzi'
    verbose_name = 'Gestione Automezzi'
    
    def ready(self):
        """
        Chiamato quando l'app è pronta.
        Registra automaticamente il modello Automezzo come target procurement.
        """
        try:
            from core.registry import procurement_target_registry
            from .models import Automezzo
            
            # Registra Automezzo come target procurement
            procurement_target_registry.register(
                Automezzo,
                display_name="Automezzo",
                icon="fas fa-car",
                description="Veicoli e mezzi aziendali",
                form_widget_config={
                    'search_fields': ['targa', 'marca', 'modello'],
                    'display_field': 'targa',
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
            logger.warning(f"Errore registrazione procurement target per automezzi: {e}")
