"""
Mixin per la gestione automatica delle relazioni tra procurement e asset management.
Questo modulo implementa il ProcurementTargetMixin che consente di collegare
automaticamente preventivi e ordini di acquisto ad automezzi, stabilimenti e
futuri tipi di asset attraverso generic foreign keys.
"""

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.exceptions import ValidationError


class ProcurementTargetMixin(models.Model):
    """
    Mixin che aggiunge la capacità di collegare un record di procurement
    (preventivo/ordine di acquisto) ad un target generico (automezzo, stabilimento, etc).
    
    Fornisce:
    - Generic Foreign Key per collegamento a qualsiasi modello registrato
    - Validazione automatica del tipo di target
    - Proprietà di accesso rapido al target
    - Metodi helper per la gestione del collegamento
    """
    
    # Generic Foreign Key per collegamento a qualsiasi asset
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Tipo Target",
        help_text="Tipo di asset a cui è collegato questo record (automezzo, stabilimento, etc.)"
    )
    target_object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="ID Target",
        help_text="ID specifico dell'asset target"
    )
    target = GenericForeignKey('target_content_type', 'target_object_id')
    
    # Metadati per automatizzare l'allegamento
    auto_attach_documents = models.BooleanField(
        default=True,
        verbose_name="Allega Documenti Automaticamente",
        help_text="Se attivo, i documenti vengono allegati automaticamente al target quando il record viene salvato"
    )
    
    class Meta:
        abstract = True
    
    def clean(self):
        """
        Validazione personalizzata per assicurarsi che:
        1. Se viene specificato un content_type, deve essere anche specificato l'object_id
        2. Il content_type deve essere registrato nel ProcurementTargetRegistry
        """
        super().clean()
        
        # Import qui per evitare circular imports
        from core.registry import procurement_target_registry
        
        # Validazione coerenza dei campi
        if self.target_content_type and not self.target_object_id:
            raise ValidationError("Se si specifica il tipo di target, è necessario specificare anche l'ID del target.")
        
        if self.target_object_id and not self.target_content_type:
            raise ValidationError("Se si specifica l'ID del target, è necessario specificare anche il tipo di target.")
        
        # Validazione tipo registrato
        if self.target_content_type:
            if not procurement_target_registry.is_registered(self.target_content_type.model_class()):
                available_types = ", ".join([
                    ct.model for ct in procurement_target_registry.get_registered_content_types()
                ])
                raise ValidationError(
                    f"Il tipo '{self.target_content_type.model}' non è registrato come target valido. "
                    f"Tipi disponibili: {available_types}"
                )
    
    def save(self, *args, **kwargs):
        """
        Override del save per triggerare l'automazione dopo il salvataggio.
        """
        # Controlla se il target è cambiato
        target_changed = False
        if self.pk:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                target_changed = (
                    old_instance.target_content_type != self.target_content_type or
                    old_instance.target_object_id != self.target_object_id
                )
            except self.__class__.DoesNotExist:
                target_changed = True
        else:
            target_changed = True
        
        # Salva normalmente
        super().save(*args, **kwargs)
        
        # Trigger automazione se necessario
        if target_changed and self.target and self.auto_attach_documents:
            self._trigger_automation()
    
    def _trigger_automation(self):
        """
        Triggera l'automazione per questo record.
        Importa e utilizza l'AutomationEngine per gestire i task automatici.
        """
        try:
            from core.automation.procurement import ProcurementAutomationEngine
            engine = ProcurementAutomationEngine()
            engine.process_procurement_target_link(self)
        except ImportError:
            # Log dell'errore ma non bloccare il salvataggio
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("ProcurementAutomationEngine non disponibile per l'automazione")
    
    @property
    def target_display_name(self):
        """
        Restituisce una rappresentazione user-friendly del target.
        """
        if not self.target:
            return "Nessun target collegato"
        
        # Prova a ottenere una rappresentazione specifica per tipo
        if hasattr(self.target, 'targa'):  # Automezzi
            return f"Automezzo {self.target.targa}"
        elif hasattr(self.target, 'nome'):  # Stabilimenti o altri con nome
            return f"{self.target._meta.verbose_name} {self.target.nome}"
        else:
            return f"{self.target._meta.verbose_name} #{self.target.pk}"
    
    @property
    def target_type_name(self):
        """
        Restituisce il nome del tipo di target.
        """
        if self.target_content_type:
            return self.target_content_type.model_class()._meta.verbose_name
        return None
    
    def get_target_url(self):
        """
        Restituisce l'URL di dettaglio del target, se disponibile.
        """
        if not self.target:
            return None
        
        # Import qui per evitare circular imports
        from django.urls import reverse, NoReverseMatch
        
        # Mappa dei pattern URL comuni per tipo
        url_patterns = {
            'automezzo': 'automezzi:automezzo_detail',
            'stabilimento': 'stabilimenti:stabilimento_detail',
            # Aggiungi altri pattern quando necessario
        }
        
        model_name = self.target_content_type.model
        url_pattern = url_patterns.get(model_name)
        
        if url_pattern:
            try:
                return reverse(url_pattern, kwargs={'pk': self.target.pk})
            except NoReverseMatch:
                pass
        
        return None
    
    def detach_target(self):
        """
        Scollega il target corrente dal record.
        """
        self.target_content_type = None
        self.target_object_id = None
        self.save(update_fields=['target_content_type', 'target_object_id'])
    
    def attach_target(self, target_object, auto_attach_docs=None):
        """
        Collega un nuovo target al record.
        
        Args:
            target_object: L'oggetto da collegare
            auto_attach_docs: Se specificato, override del flag auto_attach_documents
        """
        from core.registry import procurement_target_registry
        
        # Verifica che il tipo sia registrato
        if not procurement_target_registry.is_registered(target_object.__class__):
            raise ValidationError(f"Il tipo {target_object.__class__.__name__} non è registrato come target valido.")
        
        self.target = target_object
        if auto_attach_docs is not None:
            self.auto_attach_documents = auto_attach_docs
        
        self.save()

    def get_related_documents(self):
        """
        Restituisce i documenti collegati attraverso il sistema allegati.
        """
        if not hasattr(self, 'allegati'):
            return []
        
        return self.allegati.all()
    
    def __str__(self):
        """
        Rappresentazione string che include informazioni sul target.
        """
        base_str = super().__str__() if hasattr(super(), '__str__') else f"{self.__class__.__name__} #{self.pk}"
        if self.target:
            return f"{base_str} → {self.target_display_name}"
        return base_str