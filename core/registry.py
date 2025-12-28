"""
Registry Pattern per la gestione dei tipi di target del sistema procurement.
Questo modulo implementa un registro centralizzato che tiene traccia di quali
modelli Django possono essere utilizzati come target per preventivi e ordini di acquisto.
"""

from typing import Dict, List, Type, Optional, Set
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import models
import logging

logger = logging.getLogger(__name__)


class ProcurementTargetRegistry:
    """
    Registry centralizzato per i tipi di target del procurement.
    
    Mantiene un registro di tutti i modelli Django che possono essere
    utilizzati come target per preventivi e ordini di acquisto, insieme
    ai loro metadati e configurazioni specifiche.
    """
    
    def __init__(self):
        self._registered_models: Dict[str, Dict] = {}
        self._display_names: Dict[str, str] = {}
        self._model_configs: Dict[str, Dict] = {}
        
    def register(
        self, 
        model_class: Type[models.Model], 
        display_name: str = None,
        icon: str = None,
        description: str = None,
        form_widget_config: Dict = None,
        automation_config: Dict = None
    ):
        """
        Registra un modello come target valido per il procurement.
        
        Args:
            model_class: La classe del modello Django da registrare
            display_name: Nome user-friendly per il modello (default: verbose_name del modello)
            icon: Icona Font Awesome per l'interfaccia (es. 'fas fa-car')
            description: Descrizione del tipo di asset
            form_widget_config: Configurazione per il widget di selezione nei form
            automation_config: Configurazione per l'automazione dei processi
        """
        if not issubclass(model_class, models.Model):
            raise ValueError(f"La classe {model_class} deve essere un modello Django")
        
        model_key = self._get_model_key(model_class)
        
        # Display name di default
        if not display_name:
            display_name = model_class._meta.verbose_name
        
        # Configurazione di default
        config = {
            'model_class': model_class,
            'display_name': display_name,
            'icon': icon or 'fas fa-cube',
            'description': description or f"Gestione {display_name.lower()}",
            'form_widget_config': form_widget_config or {},
            'automation_config': automation_config or {
                'auto_attach_documents': True,
                'create_notification': True,
                'sync_metadata': True
            }
        }
        
        self._registered_models[model_key] = config
        self._display_names[model_key] = display_name
        self._model_configs[model_key] = config
        
        logger.info(f"Registrato modello procurement target: {model_key} ({display_name})")
    
    def unregister(self, model_class: Type[models.Model]):
        """
        Rimuove un modello dal registry.
        """
        model_key = self._get_model_key(model_class)
        if model_key in self._registered_models:
            del self._registered_models[model_key]
            del self._display_names[model_key]
            del self._model_configs[model_key]
            logger.info(f"Rimosso modello procurement target: {model_key}")
    
    def is_registered(self, model_class: Type[models.Model]) -> bool:
        """
        Verifica se un modello è registrato come target valido.
        """
        model_key = self._get_model_key(model_class)
        return model_key in self._registered_models
    
    def get_registered_models(self) -> List[Type[models.Model]]:
        """
        Restituisce la lista di tutti i modelli registrati.
        """
        return [config['model_class'] for config in self._registered_models.values()]
    
    def get_registered_content_types(self) -> List[ContentType]:
        """
        Restituisce i ContentType di tutti i modelli registrati.
        """
        content_types = []
        for model_class in self.get_registered_models():
            try:
                ct = ContentType.objects.get_for_model(model_class)
                content_types.append(ct)
            except Exception as e:
                logger.warning(f"Impossibile ottenere ContentType per {model_class}: {e}")
        return content_types
    
    def get_model_config(self, model_class: Type[models.Model]) -> Optional[Dict]:
        """
        Restituisce la configurazione completa di un modello registrato.
        """
        model_key = self._get_model_key(model_class)
        return self._model_configs.get(model_key)
    
    def get_display_name(self, model_class: Type[models.Model]) -> Optional[str]:
        """
        Restituisce il display name di un modello registrato.
        """
        model_key = self._get_model_key(model_class)
        return self._display_names.get(model_key)
    
    def get_model_choices(self) -> List[tuple]:
        """
        Restituisce una lista di tuple (content_type_id, display_name) 
        per l'uso in form choices.
        """
        choices = []
        for ct in self.get_registered_content_types():
            model_key = self._get_model_key(ct.model_class())
            display_name = self._display_names.get(model_key, ct.model)
            choices.append((ct.id, display_name))
        return sorted(choices, key=lambda x: x[1])
    
    def get_widget_config_for_model(self, model_class: Type[models.Model]) -> Dict:
        """
        Restituisce la configurazione widget per un modello specifico.
        """
        config = self.get_model_config(model_class)
        if config:
            return config.get('form_widget_config', {})
        return {}
    
    def get_automation_config_for_model(self, model_class: Type[models.Model]) -> Dict:
        """
        Restituisce la configurazione automazione per un modello specifico.
        """
        config = self.get_model_config(model_class)
        if config:
            return config.get('automation_config', {})
        return {}
    
    def get_model_by_content_type(self, content_type: ContentType) -> Optional[Type[models.Model]]:
        """
        Restituisce la classe del modello dato un ContentType.
        """
        model_class = content_type.model_class()
        if self.is_registered(model_class):
            return model_class
        return None
    
    def get_model_icon(self, model_class: Type[models.Model]) -> str:
        """
        Restituisce l'icona associata al modello.
        """
        config = self.get_model_config(model_class)
        if config:
            return config.get('icon', 'fas fa-cube')
        return 'fas fa-cube'
    
    def get_queryset_for_model(self, model_class: Type[models.Model], filters: Dict = None):
        """
        Restituisce un queryset filtrato per un modello specifico.
        Applica eventuali filtri di default configurati.
        """
        if not self.is_registered(model_class):
            raise ValueError(f"Modello {model_class} non registrato")
        
        qs = model_class.objects.all()
        
        # Applica filtri di default se configurati
        config = self.get_model_config(model_class)
        if config and 'default_filters' in config.get('form_widget_config', {}):
            default_filters = config['form_widget_config']['default_filters']
            qs = qs.filter(**default_filters)
        
        # Applica filtri aggiuntivi
        if filters:
            qs = qs.filter(**filters)
        
        return qs
    
    def validate_target(self, content_type: ContentType, object_id: int) -> bool:
        """
        Valida che un target specifico esista ed sia valido.
        """
        try:
            model_class = self.get_model_by_content_type(content_type)
            if not model_class:
                return False
            
            return model_class.objects.filter(pk=object_id).exists()
        except Exception:
            return False
    
    def get_target_display_info(self, content_type: ContentType, object_id: int) -> Optional[Dict]:
        """
        Restituisce informazioni di display per un target specifico.
        """
        try:
            model_class = self.get_model_by_content_type(content_type)
            if not model_class:
                return None
            
            obj = model_class.objects.get(pk=object_id)
            config = self.get_model_config(model_class)
            
            # Prova diversi campi comuni per il nome
            name = None
            for field_name in ['targa', 'nome', 'title', 'name', '__str__']:
                if field_name == '__str__':
                    name = str(obj)
                elif hasattr(obj, field_name):
                    name = getattr(obj, field_name)
                    break
            
            return {
                'id': object_id,
                'name': name or f"#{object_id}",
                'type': config['display_name'] if config else content_type.model,
                'icon': config['icon'] if config else 'fas fa-cube',
                'model': content_type.model,
                'app_label': content_type.app_label
            }
        except Exception as e:
            logger.error(f"Errore nel recupero info target {content_type}#{object_id}: {e}")
            return None
    
    def _get_model_key(self, model_class: Type[models.Model]) -> str:
        """
        Genera una chiave univoca per un modello.
        """
        return f"{model_class._meta.app_label}.{model_class._meta.model_name}"
    
    def get_statistics(self) -> Dict:
        """
        Restituisce statistiche sul registry.
        """
        return {
            'total_registered': len(self._registered_models),
            'models': list(self._registered_models.keys()),
            'apps': list(set([key.split('.')[0] for key in self._registered_models.keys()]))
        }
    
    def export_config(self) -> Dict:
        """
        Esporta la configurazione corrente per debugging/backup.
        """
        return {
            'registered_models': {
                key: {
                    'model': f"{config['model_class']._meta.app_label}.{config['model_class']._meta.model_name}",
                    'display_name': config['display_name'],
                    'icon': config['icon'],
                    'description': config['description']
                }
                for key, config in self._registered_models.items()
            }
        }


# Istanza globale del registry
procurement_target_registry = ProcurementTargetRegistry()


def register_procurement_target(
    model_class: Type[models.Model], 
    display_name: str = None,
    **kwargs
):
    """
    Decorator function per registrare facilmente un modello.
    
    @register_procurement_target("Automezzo Aziendale", icon="fas fa-car")
    class Automezzo(models.Model):
        ...
    """
    procurement_target_registry.register(model_class, display_name, **kwargs)
    return model_class


def auto_register_common_targets():
    """
    Auto-registra i target comuni se i modelli sono disponibili.
    Questa funzione può essere chiamata durante l'inizializzazione dell'app.
    """
    try:
        # Registra Automezzo se disponibile
        if apps.is_installed('automezzi'):
            try:
                Automezzo = apps.get_model('automezzi', 'Automezzo')
                procurement_target_registry.register(
                    Automezzo,
                    display_name="Automezzo",
                    icon="fas fa-car",
                    description="Veicoli e mezzi aziendali",
                    form_widget_config={
                        'search_fields': ['targa', 'marca', 'modello'],
                        'display_field': 'targa',
                        'default_filters': {'attivo': True}
                    }
                )
            except LookupError:
                pass
        
        # Registra Stabilimento se disponibile
        if apps.is_installed('stabilimenti'):
            try:
                Stabilimento = apps.get_model('stabilimenti', 'Stabilimento')
                procurement_target_registry.register(
                    Stabilimento,
                    display_name="Stabilimento",
                    icon="fas fa-building",
                    description="Stabilimenti e sedi aziendali",
                    form_widget_config={
                        'search_fields': ['nome', 'indirizzo'],
                        'display_field': 'nome',
                        'default_filters': {'attivo': True}
                    }
                )
            except LookupError:
                pass
                
        logger.info("Auto-registrazione target procurement completata")
        
    except Exception as e:
        logger.error(f"Errore durante auto-registrazione target: {e}")