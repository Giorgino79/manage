"""
CORE ALLEGATI FORMS - Form per gestione allegati
===============================================

Form per il CRUD degli allegati con validazione avanzata,
controllo file, auto-completamento e interfaccia ottimizzata per modal.

Caratteristiche:
- 📝 Form responsive per modal Bootstrap
- 🔒 Validazione sicurezza file upload
- 🎨 Styling automatico con widget personalizzati
- 📋 Auto-completamento campi in base al tipo
- 🔍 Filtri dinamici per tipi allegato

Versione: 1.0
"""

import os
from typing import Dict, List, Any, Optional

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from ..models.allegati import (
    Allegato, 
    TIPO_ALLEGATO_CHOICES, 
    STATO_ALLEGATO_CHOICES,
    PRIORITA_CHOICES,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZES,
    get_file_category
)


# =============================================================================
# CUSTOM WIDGETS
# =============================================================================

class FileDropWidget(forms.ClearableFileInput):
    """Widget drag & drop per file upload"""
    
    template_name = 'core/widgets/file_drop_widget.html'
    
    class Media:
        css = {
            'all': ('core/css/file-drop.css',)
        }
        js = ('core/js/file-drop.js',)
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'file-drop-input',
            'accept': '*/*'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)


class TagsWidget(forms.TextInput):
    """Widget per input tags con auto-completamento"""
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'form-control tags-input',
            'placeholder': 'Inserisci tag separati da virgola...',
            'data-role': 'tagsinput'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    class Media:
        css = {
            'all': ('core/css/tags-input.css',)
        }
        js = ('core/js/tags-input.js',)


class TipoAllegatoSelect(forms.Select):
    """Widget select con icone per tipi allegato"""
    
    def __init__(self, attrs=None, choices=()):
        default_attrs = {
            'class': 'form-select tipo-allegato-select'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs, choices)
    
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        
        # Aggiungi icona al label se ha valore
        if value:
            # Estrai emoji dal label
            if ' ' in label:
                emoji, text = label.split(' ', 1)
                option['label'] = f"{emoji} {text}"
        
        return option


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_filtered_tipo_choices(content_type_id=None, object_id=None):
    """
    Ottieni scelte tipo allegato filtrate in base all'oggetto parent.
    
    Args:
        content_type_id: ID del ContentType dell'oggetto parent
        object_id: ID dell'oggetto parent
        
    Returns:
        List: Lista tuple (valore, label) filtrate
    """
    
    # Mappatura tipi per modello
    FILTRI_PER_MODELLO = {
        'dipendenti.dipendente': [
            'doc_contratto', 'doc_certificato', 'doc_patente', 
            'doc_carta_identita', 'doc_codice_fiscale', 'doc_visura',
            'foto_documento', 'nota_interna', 'email_inviata', 'email_ricevuta',
            'promemoria', 'verbale', 'altro'
        ],
        
        'automezzi.automezzo': [
            'doc_libretto', 'doc_certificato', 'polizza', 'denuncia',
            'foto_generale', 'foto_documento', 'scheda_tecnica', 'manuale',
            'log_manutenzione', 'report_tecnico', 'checklist', 'nota_interna',
            'altro'
        ],
        
        'vendite.ordinevendita': [
            'doc_ordine', 'doc_fattura', 'doc_bolla', 'doc_preventivo',
            'email_inviata', 'email_ricevuta', 'nota_cliente', 'nota_interna',
            'offerta', 'altro'
        ],
        
        'clienti.cliente': [
            'doc_contratto', 'doc_fattura', 'doc_preventivo', 'doc_visura',
            'email_inviata', 'email_ricevuta', 'chiamata', 'nota_cliente',
            'brochure', 'listino', 'catalogo', 'offerta', 'altro'
        ],
        
        'fornitori.fornitore': [
            'doc_contratto', 'doc_fattura', 'doc_ordine', 'doc_visura',
            'email_inviata', 'email_ricevuta', 'nota_interna',
            'listino', 'catalogo', 'brochure', 'altro'
        ]
    }
    
    # Se non abbiamo info sull'oggetto, restituisci tutte le scelte
    if not content_type_id:
        return TIPO_ALLEGATO_CHOICES
    
    try:
        content_type = ContentType.objects.get(pk=content_type_id)
        model_key = f"{content_type.app_label}.{content_type.model}"
        
        # Ottieni tipi consentiti per questo modello
        tipi_consentiti = FILTRI_PER_MODELLO.get(model_key, [])
        
        if tipi_consentiti:
            # Filtra le scelte
            return [
                (valore, label) for valore, label in TIPO_ALLEGATO_CHOICES
                if valore in tipi_consentiti
            ]
    except:
        pass
    
    # Default: tutte le scelte
    return TIPO_ALLEGATO_CHOICES


def validate_file_upload(file):
    """
    Valida file upload per sicurezza e conformità.
    
    Args:
        file: File object da validare
        
    Raises:
        ValidationError: Se il file non è valido
    """
    
    if not file:
        return
    
    # Controllo dimensione
    if hasattr(file, 'size'):
        categoria = get_file_category(file.name)
        max_size = MAX_FILE_SIZES.get(categoria, MAX_FILE_SIZES['default'])
        
        if file.size > max_size:
            size_mb = max_size // (1024 * 1024)
            raise ValidationError(
                f"File troppo grande. Dimensione massima consentita: {size_mb}MB"
            )
    
    # Controllo estensione
    if hasattr(file, 'name'):
        ext = os.path.splitext(file.name)[1].lower().lstrip('.')
        categoria = get_file_category(file.name)
        
        allowed_for_category = ALLOWED_EXTENSIONS.get(categoria, [])
        
        # Se non è in una categoria specifica, controlla tutte le estensioni
        if not allowed_for_category:
            all_allowed = []
            for exts in ALLOWED_EXTENSIONS.values():
                all_allowed.extend(exts)
            allowed_for_category = all_allowed
        
        if ext not in allowed_for_category:
            raise ValidationError(
                f"Estensione file '.{ext}' non consentita. "
                f"Estensioni permesse: {', '.join(allowed_for_category)}"
            )
    
    # Controllo MIME type (basic)
    if hasattr(file, 'content_type'):
        # Lista MIME type pericolosi
        dangerous_mimes = [
            'application/x-executable',
            'application/x-msdownload', 
            'application/x-msdos-program',
            'text/x-script.phps'
        ]
        
        if file.content_type in dangerous_mimes:
            raise ValidationError("Tipo file non consentito per motivi di sicurezza")


# =============================================================================
# MAIN FORMS
# =============================================================================

class AllegatoForm(forms.ModelForm):
    """
    Form principale per creazione/modifica allegati.
    
    Caratteristiche:
    - Widget personalizzati
    - Validazione sicurezza
    - Auto-completamento
    - Responsive design per modal
    """
    
    class Meta:
        model = Allegato
        fields = [
            'titolo', 'descrizione', 'tipo_allegato', 'file', 
            'url_esterno', 'contenuto_testo', 'tags', 'priorita',
            'data_documento', 'data_scadenza', 'is_pubblico', 'is_confidenziale'
        ]
        
        widgets = {
            'titolo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Inserisci titolo allegato...',
                'maxlength': 255
            }),
            'descrizione': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrizione opzionale...'
            }),
            'tipo_allegato': TipoAllegatoSelect(attrs={
                'class': 'form-select',
                'required': True
            }),
            'file': FileDropWidget(attrs={
                'class': 'form-control',
                'accept': '*/*'
            }),
            'url_esterno': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://esempio.com/documento.pdf'
            }),
            'contenuto_testo': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Contenuto testuale per note...'
            }),
            'tags': TagsWidget(),
            'priorita': forms.Select(attrs={
                'class': 'form-select'
            }),
            'data_documento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'data_scadenza': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'is_pubblico': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_confidenziale': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        
        labels = {
            'titolo': 'Titolo *',
            'descrizione': 'Descrizione',
            'tipo_allegato': 'Tipo Allegato *',
            'file': 'File',
            'url_esterno': 'URL Esterno',
            'contenuto_testo': 'Contenuto Testuale',
            'tags': 'Tag',
            'priorita': 'Priorità',
            'data_documento': 'Data Documento',
            'data_scadenza': 'Data Scadenza',
            'is_pubblico': 'Pubblico',
            'is_confidenziale': 'Confidenziale'
        }
        
        help_texts = {
            'titolo': 'Nome descrittivo per identificare l\'allegato',
            'tipo_allegato': 'Seleziona la categoria che meglio descrive l\'allegato',
            'file': 'Carica un file dal tuo computer (max 20MB)',
            'url_esterno': 'In alternativa al file, inserisci un link esterno',
            'contenuto_testo': 'Per note testuali, appunti o contenuto senza file',
            'tags': 'Parole chiave separate da virgola per facilitare la ricerca',
            'data_documento': 'Data del documento originale (se applicabile)',
            'data_scadenza': 'Data di scadenza del documento (se applicabile)',
            'is_pubblico': 'Visibile a tutti gli utenti autorizzati',
            'is_confidenziale': 'Visibile solo al creatore e agli amministratori'
        }
    
    def __init__(self, *args, **kwargs):
        # Estrai parametri custom
        self.content_type_id = kwargs.pop('content_type_id', None)
        self.object_id = kwargs.pop('object_id', None)
        self.parent_object = kwargs.pop('parent_object', None)
        self.user = kwargs.pop('user', None)
        
        super().__init__(*args, **kwargs)
        
        # Filtra scelte tipo allegato
        if self.content_type_id:
            filtered_choices = get_filtered_tipo_choices(
                self.content_type_id, 
                self.object_id
            )
            self.fields['tipo_allegato'].choices = filtered_choices
        
        # Imposta valori di default intelligenti
        if not self.instance.pk:
            self.fields['priorita'].initial = 'normale'
            self.fields['is_pubblico'].initial = True
            self.fields['is_confidenziale'].initial = False
        
        # Nascondi campi non necessari inizialmente
        self._setup_field_visibility()
        
        # Aggiungi attributi per JavaScript
        self._add_js_attributes()
    
    def _setup_field_visibility(self):
        """Imposta visibilità campi in base al contesto"""
        
        # Nascondi campi avanzati se non necessari
        advanced_fields = ['data_documento', 'data_scadenza', 'is_confidenziale']
        for field_name in advanced_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['data-advanced'] = 'true'
        
        # Raggruppa campi correlati
        content_fields = ['file', 'url_esterno', 'contenuto_testo']
        for field_name in content_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['data-content-type'] = field_name
    
    def _add_js_attributes(self):
        """Aggiungi attributi per JavaScript interattivo"""
        
        # Tipo allegato trigger per UI dinamica
        self.fields['tipo_allegato'].widget.attrs.update({
            'data-trigger': 'tipo-change',
            'onchange': 'handleTipoAllegatoChange(this.value)'
        })
        
        # File upload con validazione live
        self.fields['file'].widget.attrs.update({
            'data-max-size': MAX_FILE_SIZES['default'],
            'onchange': 'validateFileUpload(this)'
        })
        
        # Auto-suggest per titolo
        self.fields['titolo'].widget.attrs.update({
            'data-suggest': 'true',
            'oninput': 'suggestTitolo(this.value, this.form.tipo_allegato.value)'
        })
    
    def clean_file(self):
        """Validazione file upload"""
        file = self.cleaned_data.get('file')
        
        if file:
            validate_file_upload(file)
        
        return file
    
    def clean_url_esterno(self):
        """Validazione URL esterno"""
        url = self.cleaned_data.get('url_esterno')
        
        if url:
            # Controllo URL sicuri
            if not url.startswith(('http://', 'https://')):
                raise ValidationError("URL deve iniziare con http:// o https://")
        
        return url
    
    def clean(self):
        """Validazione cross-field"""
        cleaned_data = super().clean()
        
        file = cleaned_data.get('file')
        url_esterno = cleaned_data.get('url_esterno')
        contenuto_testo = cleaned_data.get('contenuto_testo')
        tipo_allegato = cleaned_data.get('tipo_allegato')
        
        # Almeno uno tra file, url o contenuto deve essere presente
        if not any([file, url_esterno, contenuto_testo]):
            raise ValidationError(
                "È necessario fornire almeno uno tra: file, URL esterno o contenuto testuale."
            )
        
        # Non può essere sia pubblico che confidenziale
        is_pubblico = cleaned_data.get('is_pubblico')
        is_confidenziale = cleaned_data.get('is_confidenziale')
        
        if is_pubblico and is_confidenziale:
            raise ValidationError(
                "Un allegato non può essere contemporaneamente pubblico e confidenziale."
            )
        
        # Validazione tipo-specifica
        if tipo_allegato:
            if tipo_allegato.startswith('doc_') and not file and not url_esterno:
                raise ValidationError(
                    "I documenti richiedono un file o un URL esterno."
                )
            
            if tipo_allegato.startswith('nota_') and not contenuto_testo:
                raise ValidationError(
                    "Le note richiedono contenuto testuale."
                )
            
            if tipo_allegato == 'link_esterno' and not url_esterno:
                raise ValidationError(
                    "I link esterni richiedono un URL."
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        """Override save per impostare metadati"""
        
        allegato = super().save(commit=False)
        
        # Imposta oggetto parent
        if self.content_type_id and self.object_id:
            try:
                content_type = ContentType.objects.get(pk=self.content_type_id)
                allegato.content_type = content_type
                allegato.object_id = self.object_id
            except ContentType.DoesNotExist:
                pass
        
        # Imposta utente creatore/modificatore
        if self.user:
            if not allegato.pk:
                allegato.creato_da = self.user
            else:
                allegato.modificato_da = self.user
        
        if commit:
            allegato.save()
        
        return allegato


class AllegatoQuickForm(forms.ModelForm):
    """
    Form semplificata per aggiunta rapida allegati.
    Solo campi essenziali per uso in sidebar/widget.
    """
    
    class Meta:
        model = Allegato
        fields = ['titolo', 'tipo_allegato', 'file', 'url_esterno']
        
        widgets = {
            'titolo': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Titolo allegato...'
            }),
            'tipo_allegato': forms.Select(attrs={
                'class': 'form-select form-select-sm'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control form-control-sm'
            }),
            'url_esterno': forms.URLInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'https://...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.content_type_id = kwargs.pop('content_type_id', None)
        self.object_id = kwargs.pop('object_id', None)
        self.user = kwargs.pop('user', None)
        
        super().__init__(*args, **kwargs)
        
        # Filtra tipi
        if self.content_type_id:
            filtered_choices = get_filtered_tipo_choices(self.content_type_id)
            self.fields['tipo_allegato'].choices = filtered_choices


class AllegatoSearchForm(forms.Form):
    """
    Form per ricerca e filtro allegati.
    """
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cerca per titolo, descrizione o tag...'
        }),
        label='Ricerca'
    )
    
    tipo_allegato = forms.ChoiceField(
        required=False,
        choices=[('', 'Tutti i tipi')] + list(TIPO_ALLEGATO_CHOICES),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Tipo'
    )
    
    stato = forms.ChoiceField(
        required=False,
        choices=[('', 'Tutti gli stati')] + list(STATO_ALLEGATO_CHOICES),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Stato'
    )
    
    data_da = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Da'
    )
    
    data_a = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control', 
            'type': 'date'
        }),
        label='A'
    )
    
    solo_con_file = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Solo con file'
    )
    
    solo_scaduti = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Solo scaduti'
    )


class AllegatoBulkActionForm(forms.Form):
    """
    Form per azioni bulk su allegati selezionati.
    """
    
    ACTION_CHOICES = [
        ('', 'Seleziona azione...'),
        ('archivia', 'Archivia'),
        ('attiva', 'Attiva'),
        ('elimina', 'Elimina'),
        ('cambia_tipo', 'Cambia tipo'),
        ('aggiungi_tag', 'Aggiungi tag'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Azione'
    )
    
    nuovo_tipo = forms.ChoiceField(
        required=False,
        choices=[('', 'Seleziona nuovo tipo...')] + list(TIPO_ALLEGATO_CHOICES),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Nuovo tipo'
    )
    
    tag_da_aggiungere = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tag da aggiungere...'
        }),
        label='Tag'
    )
    
    allegati_selezionati = forms.CharField(
        widget=forms.HiddenInput(),
        label='Allegati selezionati'
    )