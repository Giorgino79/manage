from django import forms
from django_select2.forms import Select2Widget
from .models import RichiestaPreventivo, Preventivo
from core.forms.procurement import ProcurementTargetFormMixin, UnifiedAssetChoiceField


class SceltaFornitoreForm(forms.Form):
    """
    Form per la scelta del fornitore vincitore nello Step 3
    """
    preventivo_scelto = forms.ModelChoiceField(
        queryset=Preventivo.objects.none(),
        empty_label="Seleziona il preventivo vincitore",
        widget=Select2Widget(attrs={
            'class': 'form-control',
            'data-placeholder': 'Seleziona il preventivo vincitore...',
            'style': 'width: 100%;'
        }),
        label="Preventivo Vincitore",
        help_text="Seleziona il preventivo da approvare"
    )
    
    note_approvazione = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Inserisci eventuali note sulla scelta del fornitore...'
        }),
        label="Note di Approvazione",
        help_text="Note opzionali sulla decisione",
        required=False
    )
    
    def __init__(self, richiesta, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra i preventivi solo per questa richiesta
        self.fields['preventivo_scelto'].queryset = richiesta.preventivo_set.all()
        
        # Personalizza le opzioni del select per mostrare fornitore + importo
        choices = [(p.id, f"{p.fornitore.nome} - €{p.importo_totale:,.2f}") 
                  for p in richiesta.preventivo_set.all()]
        self.fields['preventivo_scelto'].choices = [('', 'Seleziona il preventivo vincitore')] + choices


class RichiestaPreventovoForm(forms.ModelForm):
    """
    Form per la creazione/modifica di richieste preventivo con supporto target.
    """
    
    # Campo unificato per selezione asset
    asset_collegato = UnifiedAssetChoiceField(
        label="Asset Collegato",
        help_text="Seleziona l'automezzo o stabilimento per cui richiedere il preventivo",
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-placeholder': 'Seleziona asset...'
        })
    )
    
    auto_attach_documents = forms.BooleanField(
        label="Allega Documenti Automaticamente",
        help_text="Se attivo, i documenti verranno allegati automaticamente all'asset selezionato",
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = RichiestaPreventivo
        fields = [
            'titolo', 'descrizione', 'priorita', 'data_scadenza', 
            'budget_massimo', 'note_interne', 'approvatore'
        ]
        # Nota: asset_collegato e auto_attach_documents sono campi del form, non del modello
        widgets = {
            'titolo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Inserisci titolo del preventivo...'
            }),
            'descrizione': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descrivi dettagliatamente cosa serve...'
            }),
            'priorita': forms.Select(attrs={'class': 'form-select'}),
            'data_scadenza': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'budget_massimo': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'note_interne': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Note interne non visibili ai fornitori...'
            }),
            'approvatore': forms.Select(attrs={'class': 'form-select'})
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # IMPORTANTE: Ricarica le choices per il campo asset_collegato
        self.fields['asset_collegato']._populate_asset_choices()
        
        # Configura il campo approvatore se necessario
        if user:
            # Filtra gli approvatori disponibili se necessario
            from django.contrib.auth import get_user_model
            User = get_user_model()
            self.fields['approvatore'].queryset = User.objects.filter(is_staff=True)
        
        # Se stiamo modificando un'istanza esistente, popola il campo asset
        if self.instance and self.instance.pk:
            if self.instance.target_content_type and self.instance.target_object_id:
                model_name = self.instance.target_content_type.model
                if model_name == 'automezzo':
                    self.fields['asset_collegato'].initial = f'automezzo_{self.instance.target_object_id}'
                elif model_name == 'stabilimento':
                    self.fields['asset_collegato'].initial = f'stabilimento_{self.instance.target_object_id}'
            
            self.fields['auto_attach_documents'].initial = getattr(
                self.instance, 'auto_attach_documents', True
            )
    
    def save(self, commit=True):
        """
        Salva la richiesta preventivo con target collegato.
        """
        instance = super().save(commit=False)
        
        # Imposta il richiedente se non già impostato
        if not instance.richiedente_id and hasattr(self, '_user'):
            instance.richiedente = self._user
        
        # Gestisci il campo asset_collegato
        asset_data = self.cleaned_data.get('asset_collegato')
        if asset_data:
            # asset_data è una tupla (content_type, object_id, target_object)
            content_type, object_id, target_object = asset_data
            instance.target_content_type = content_type
            instance.target_object_id = object_id
        else:
            instance.target_content_type = None
            instance.target_object_id = None
        
        # Imposta auto_attach_documents
        instance.auto_attach_documents = self.cleaned_data.get('auto_attach_documents', True)
        
        if commit:
            instance.save()
            self.save_m2m()
        
        return instance
    
    def set_user(self, user):
        """
        Imposta l'utente corrente per il form.
        """
        self._user = user


class PreventovoForm(forms.ModelForm):
    """
    Form per l'inserimento di preventivi ricevuti dai fornitori.
    """
    
    class Meta:
        model = Preventivo
        fields = [
            'richiesta', 'fornitore', 'numero_preventivo_fornitore',
            'importo_totale', 'validita_giorni', 'termini_pagamento',
            'tempi_consegna', 'condizioni_trasporto', 'garanzia',
            'note_tecniche', 'note_commerciali', 'file_preventivo'
        ]
        widgets = {
            'richiesta': forms.Select(attrs={'class': 'form-select'}),
            'fornitore': forms.Select(attrs={'class': 'form-select'}),
            'numero_preventivo_fornitore': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Numero preventivo del fornitore...'
            }),
            'importo_totale': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'validita_giorni': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'value': '30'
            }),
            'termini_pagamento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'es. 30gg DFFM'
            }),
            'tempi_consegna': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'es. 15 giorni lavorativi'
            }),
            'condizioni_trasporto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'es. Franco fabbrica'
            }),
            'garanzia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'es. 24 mesi'
            }),
            'note_tecniche': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'note_commerciali': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'file_preventivo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx'
            })
        }
    
    def __init__(self, *args, **kwargs):
        richiesta = kwargs.pop('richiesta', None)
        super().__init__(*args, **kwargs)
        
        # Se viene passata una richiesta specifica, preselezionala
        if richiesta:
            self.fields['richiesta'].initial = richiesta
            self.fields['richiesta'].widget = forms.HiddenInput()
            
            # Filtra i fornitori per quelli coinvolti nella richiesta
            if richiesta.fornitori.exists():
                self.fields['fornitore'].queryset = richiesta.fornitori.all()
    
    def save(self, commit=True):
        """
        Salva il preventivo impostando l'operatore di inserimento.
        """
        instance = super().save(commit=False)
        
        # Imposta l'operatore se non già impostato
        if not instance.operatore_inserimento_id and hasattr(self, '_user'):
            instance.operatore_inserimento = self._user
        
        if commit:
            instance.save()
        
        return instance
    
    def set_user(self, user):
        """
        Imposta l'utente corrente per il form.
        """
        self._user = user