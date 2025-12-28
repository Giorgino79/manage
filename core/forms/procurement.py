"""
Form widgets e utilities per il sistema procurement.
Contiene widget intelligenti per la selezione di target e gestione delle relazioni.
"""

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
import json


class SmartTargetSelectorWidget(forms.MultiWidget):
    """
    Widget intelligente per la selezione di target procurement.
    Combina una select per il tipo di target con una select per l'oggetto specifico.
    Utilizza AJAX per caricare dinamicamente le opzioni del secondo campo.
    """
    
    template_name = 'core/forms/widgets/smart_target_selector.html'
    
    def __init__(self, attrs=None):
        widgets = [
            forms.Select(attrs={'class': 'form-select target-type-selector'}),
            forms.Select(attrs={'class': 'form-select target-object-selector'}),
        ]
        super().__init__(widgets, attrs)
    
    def decompress(self, value):
        """
        Decompone il valore del campo per i due widget.
        value può essere una tupla (content_type_id, object_id) o None.
        """
        if value:
            if isinstance(value, (list, tuple)) and len(value) == 2:
                return value
            # Se value è un singolo valore, prova a interpretarlo
            return [value, None]
        return [None, None]
    
    def format_output(self, rendered_widgets):
        """
        Formato personalizzato per l'output del widget.
        """
        return mark_safe(
            f'<div class="smart-target-selector row">'
            f'<div class="col-md-6">'
            f'<label class="form-label">Tipo Asset:</label>'
            f'{rendered_widgets[0]}'
            f'</div>'
            f'<div class="col-md-6">'
            f'<label class="form-label">Seleziona Asset:</label>'
            f'{rendered_widgets[1]}'
            f'</div>'
            f'</div>'
        )
    
    class Media:
        js = ('core/js/smart_target_selector.js',)
        css = {
            'all': ('core/css/smart_target_selector.css',)
        }


class UnifiedAssetChoiceField(forms.ChoiceField):
    """
    Campo unificato per la selezione di automezzi e stabilimenti.
    Utilizza un singolo select con tutti gli asset disponibili.
    """
    
    def __init__(self, *args, **kwargs):
        # Prima chiamiamo super().__init__ senza choices
        super().__init__(*args, **kwargs)
        # Poi popoliamo le choices
        self._populate_asset_choices()
    
    def _populate_asset_choices(self):
        """
        Popola le scelte con automezzi e stabilimenti.
        """
        choices = [('', 'Seleziona asset...')]
        
        try:
            # Importa i modelli
            from django.apps import apps
            
            # Automezzi
            if apps.is_installed('automezzi'):
                Automezzo = apps.get_model('automezzi', 'Automezzo')
                automezzi = Automezzo.objects.filter(attivo=True).order_by('targa')
                for automezzo in automezzi:
                    choices.append((
                        f'automezzo_{automezzo.pk}',
                        f'🚗 {automezzo.targa} - {automezzo.marca} {automezzo.modello}'
                    ))
            
            # Stabilimenti
            if apps.is_installed('stabilimenti'):
                Stabilimento = apps.get_model('stabilimenti', 'Stabilimento')
                stabilimenti = Stabilimento.objects.filter(attivo=True).order_by('nome')
                for stabilimento in stabilimenti:
                    choices.append((
                        f'stabilimento_{stabilimento.pk}',
                        f'🏢 {stabilimento.nome} - {stabilimento.citta}'
                    ))
                    
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Errore nel caricamento asset choices: {e}")
        
        self.choices = choices
    
    def to_python(self, value):
        """
        Converte il valore del campo in oggetto target.
        """
        if not value or value == '':
            return None
        
        try:
            from django.apps import apps
            from django.contrib.contenttypes.models import ContentType
            
            # Parse del valore "tipo_id"
            asset_type, asset_id = value.split('_', 1)
            asset_id = int(asset_id)
            
            if asset_type == 'automezzo' and apps.is_installed('automezzi'):
                Automezzo = apps.get_model('automezzi', 'Automezzo')
                target = Automezzo.objects.get(pk=asset_id)
                content_type = ContentType.objects.get_for_model(Automezzo)
                return (content_type, target.pk, target)
                
            elif asset_type == 'stabilimento' and apps.is_installed('stabilimenti'):
                Stabilimento = apps.get_model('stabilimenti', 'Stabilimento')
                target = Stabilimento.objects.get(pk=asset_id)
                content_type = ContentType.objects.get_for_model(Stabilimento)
                return (content_type, target.pk, target)
                
        except (ValueError, TypeError, LookupError) as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Errore parsing asset value {value}: {e}")
            raise forms.ValidationError(f"Asset non valido: {value}")
        
        raise forms.ValidationError(f"Tipo di asset non supportato: {value}")
    
    def validate(self, value):
        """
        Validazione del campo.
        """
        # Se il campo è obbligatorio, verrà gestito dal framework
        if value is None and not self.required:
            return
        
        # La validazione vera viene fatta in to_python


class ProcurementTargetField(forms.MultiValueField):
    """
    Campo personalizzato per la selezione di target procurement.
    Gestisce la validazione e la conversione dei valori.
    """
    
    widget = SmartTargetSelectorWidget
    
    def __init__(self, *args, **kwargs):
        self.queryset_filters = kwargs.pop('queryset_filters', {})
        
        fields = [
            forms.ModelChoiceField(
                queryset=ContentType.objects.none(),
                empty_label="Seleziona tipo asset...",
                required=False
            ),
            forms.CharField(
                max_length=20,
                required=False
            )
        ]
        
        super().__init__(fields, *args, **kwargs)
        self._populate_content_type_choices()
    
    def _populate_content_type_choices(self):
        """
        Popola le scelte per il primo campo (tipo di content type).
        """
        from core.registry import procurement_target_registry
        
        # Ottieni i content types registrati
        content_types = procurement_target_registry.get_registered_content_types()
        self.fields[0].queryset = ContentType.objects.filter(
            id__in=[ct.id for ct in content_types]
        )
    
    def compress(self, data_list):
        """
        Combina i valori dei due campi in un singolo valore.
        Restituisce una tupla (content_type_id, object_id) o None.
        """
        if data_list:
            content_type_id = data_list[0]
            object_id = data_list[1]
            
            if content_type_id and object_id:
                try:
                    content_type = ContentType.objects.get(id=content_type_id.id)
                    object_id = int(object_id)
                    return (content_type, object_id)
                except (ContentType.DoesNotExist, ValueError, TypeError):
                    pass
        
        return None
    
    def validate(self, value):
        """
        Validazione personalizzata del campo.
        """
        super().validate(value)
        
        if value:
            content_type, object_id = value
            
            # Verifica che il target esista
            from core.registry import procurement_target_registry
            if not procurement_target_registry.validate_target(content_type, object_id):
                raise ValidationError("Il target selezionato non esiste o non è valido.")


class ProcurementTargetForm(forms.Form):
    """
    Form di esempio per l'uso del ProcurementTargetField.
    Può essere ereditato da altri form che necessitano di target selection.
    """
    
    target = ProcurementTargetField(
        label="Asset Collegato",
        help_text="Seleziona l'asset a cui collegare questo record",
        required=False
    )
    
    auto_attach_documents = forms.BooleanField(
        label="Allega Documenti Automaticamente",
        help_text="Se attivo, i documenti verranno allegati automaticamente all'asset selezionato",
        initial=True,
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        # Estrai parametri personalizzati
        self.instance = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)
        
        # Se abbiamo un'istanza, popola i valori iniziali
        if self.instance and hasattr(self.instance, 'target_content_type'):
            if self.instance.target_content_type and self.instance.target_object_id:
                self.fields['target'].initial = [
                    self.instance.target_content_type.id,
                    self.instance.target_object_id
                ]
            
            self.fields['auto_attach_documents'].initial = getattr(
                self.instance, 'auto_attach_documents', True
            )
    
    def save_target_to_instance(self, instance):
        """
        Salva i dati del target sull'istanza del modello.
        """
        target = self.cleaned_data.get('target')
        auto_attach = self.cleaned_data.get('auto_attach_documents', True)
        
        if target:
            content_type, object_id = target
            instance.target_content_type = content_type
            instance.target_object_id = object_id
        else:
            instance.target_content_type = None
            instance.target_object_id = None
        
        instance.auto_attach_documents = auto_attach
        
        return instance


class QuickTargetSearchForm(forms.Form):
    """
    Form per ricerca rapida di target in popup/modal.
    """
    
    target_type = forms.ModelChoiceField(
        queryset=ContentType.objects.none(),
        label="Tipo Asset",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    search_term = forms.CharField(
        max_length=200,
        label="Cerca",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Inserisci termine di ricerca...'
        }),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Popola i tipi disponibili
        from core.registry import procurement_target_registry
        content_types = procurement_target_registry.get_registered_content_types()
        self.fields['target_type'].queryset = ContentType.objects.filter(
            id__in=[ct.id for ct in content_types]
        )
    
    def get_search_results(self):
        """
        Esegue la ricerca e restituisce i risultati.
        """
        if not self.is_valid():
            return []
        
        target_type = self.cleaned_data['target_type']
        search_term = self.cleaned_data.get('search_term', '')
        
        from core.registry import procurement_target_registry
        model_class = procurement_target_registry.get_model_by_content_type(target_type)
        
        if not model_class:
            return []
        
        # Ottieni queryset base
        qs = procurement_target_registry.get_queryset_for_model(model_class)
        
        # Applica ricerca se specificata
        if search_term:
            # Cerca nei campi comuni
            search_fields = []
            if hasattr(model_class, 'targa'):
                search_fields.append('targa__icontains')
            if hasattr(model_class, 'nome'):
                search_fields.append('nome__icontains')
            if hasattr(model_class, 'title'):
                search_fields.append('title__icontains')
            
            if search_fields:
                from django.db.models import Q
                query = Q()
                for field in search_fields:
                    query |= Q(**{field: search_term})
                qs = qs.filter(query)
        
        # Limita risultati
        return qs[:20]


class TargetInfoWidget(forms.Widget):
    """
    Widget read-only per mostrare informazioni su un target già collegato.
    """
    
    template_name = 'core/forms/widgets/target_info.html'
    
    def format_value(self, value):
        """
        Formatta il valore per la visualizzazione.
        """
        if not value:
            return None
        
        if hasattr(value, 'target_display_name'):
            return {
                'display_name': value.target_display_name,
                'type_name': value.target_type_name,
                'url': value.get_target_url()
            }
        
        return str(value)
    
    def render(self, name, value, attrs=None, renderer=None):
        """
        Rendering personalizzato del widget.
        """
        if not value:
            return mark_safe('<span class="text-muted">Nessun target collegato</span>')
        
        formatted_value = self.format_value(value)
        if isinstance(formatted_value, dict):
            html = f'<div class="target-info">'
            html += f'<strong>{formatted_value["display_name"]}</strong>'
            html += f'<br><small class="text-muted">{formatted_value["type_name"]}</small>'
            if formatted_value["url"]:
                html += f'<br><a href="{formatted_value["url"]}" class="btn btn-sm btn-outline-primary mt-1">'
                html += f'<i class="fas fa-eye"></i> Visualizza</a>'
            html += '</div>'
            return mark_safe(html)
        
        return mark_safe(f'<span class="target-info">{formatted_value}</span>')


class ProcurementTargetFormMixin:
    """
    Mixin per aggiungere funzionalità di target selection ai form.
    """
    
    def add_target_fields(self):
        """
        Aggiunge i campi per la selezione del target.
        """
        self.fields['target'] = ProcurementTargetField(
            label="Asset Collegato",
            help_text="Seleziona l'asset a cui collegare questo record",
            required=False
        )
        
        self.fields['auto_attach_documents'] = forms.BooleanField(
            label="Allega Documenti Automaticamente",
            initial=True,
            required=False
        )
    
    def setup_target_fields_from_instance(self, instance):
        """
        Configura i campi target basandosi sull'istanza esistente.
        """
        if hasattr(instance, 'target_content_type') and instance.target_content_type:
            self.fields['target'].initial = [
                instance.target_content_type.id,
                instance.target_object_id
            ]
        
        if hasattr(instance, 'auto_attach_documents'):
            self.fields['auto_attach_documents'].initial = instance.auto_attach_documents
    
    def save_target_fields(self, instance):
        """
        Salva i campi target nell'istanza.
        """
        target = self.cleaned_data.get('target')
        auto_attach = self.cleaned_data.get('auto_attach_documents', True)
        
        if target:
            content_type, object_id = target
            instance.target_content_type = content_type
            instance.target_object_id = object_id
        else:
            instance.target_content_type = None
            instance.target_object_id = None
        
        instance.auto_attach_documents = auto_attach
        return instance