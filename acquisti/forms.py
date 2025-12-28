"""
ACQUISTI FORMS - Forms per gestione ordini di acquisto
=====================================================

Forms per:
- Ricerca ordini
- Creazione manuale ordini
- Cambio stato ordini
"""

from django import forms
from django.db.models import Q
from .models import OrdineAcquisto
from anagrafica.models import Fornitore
from core.forms.procurement import ProcurementTargetFormMixin


class RicercaOrdiniForm(forms.Form):
    """
    Form di ricerca per dashboard ordini
    """
    
    fornitore = forms.ModelChoiceField(
        queryset=Fornitore.objects.filter(attivo=True).order_by('nome'),
        required=False,
        empty_label="Tutti i fornitori",
        widget=forms.Select(attrs={
            'class': 'form-control',
        })
    )
    
    titolo = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cerca nel titolo dell\'ordine...'
        })
    )
    
    stato = forms.ChoiceField(
        choices=[('', 'Tutti gli stati')] + OrdineAcquisto.STATI_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        })
    )
    
    def filter_queryset(self, queryset):
        """
        Applica i filtri al queryset
        """
        if self.is_valid():
            # Filtro fornitore
            if self.cleaned_data.get('fornitore'):
                queryset = queryset.filter(fornitore=self.cleaned_data['fornitore'])
            
            # Filtro titolo (ricerca nel titolo del preventivo o nelle note)
            if self.cleaned_data.get('titolo'):
                titolo_search = self.cleaned_data['titolo']
                queryset = queryset.filter(
                    Q(preventivo_originale__richiesta__titolo__icontains=titolo_search) |
                    Q(note_ordine__icontains=titolo_search)
                )
            
            # Filtro stato
            if self.cleaned_data.get('stato'):
                queryset = queryset.filter(stato=self.cleaned_data['stato'])
        
        return queryset


class CreaOrdineForm(ProcurementTargetFormMixin, forms.ModelForm):
    """
    Form per creazione manuale ordine di acquisto
    """
    
    class Meta:
        model = OrdineAcquisto
        fields = [
            'fornitore',
            'importo_totale',
            'termini_pagamento',
            'tempi_consegna',
            'data_consegna_richiesta',
            'note_ordine',
            'riferimento_esterno'
        ]
        widgets = {
            'fornitore': forms.Select(attrs={'class': 'form-control'}),
            'importo_totale': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'termini_pagamento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'es. 30 giorni DFFM'
            }),
            'tempi_consegna': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'es. 15 giorni lavorativi'
            }),
            'data_consegna_richiesta': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'note_ordine': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Note e descrizione dell\'ordine...'
            }),
            'riferimento_esterno': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Riferimento del fornitore (se disponibile)'
            })
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Aggiungi campi per target selection
        self.add_target_fields()
        
        # Ordina fornitori per nome
        self.fields['fornitore'].queryset = Fornitore.objects.filter(
            attivo=True
        ).order_by('nome')
        
        # Se stiamo modificando un'istanza esistente
        if self.instance and self.instance.pk:
            self.setup_target_fields_from_instance(self.instance)
        
        # Salva l'utente per il save
        self._user = user
    
    def save(self, commit=True):
        """
        Salva l'ordine di acquisto con target collegato.
        """
        instance = super().save(commit=False)
        
        # Imposta il creatore se non già impostato
        if not instance.creato_da_id and hasattr(self, '_user') and self._user:
            instance.creato_da = self._user
        
        # Salva i campi target
        instance = self.save_target_fields(instance)
        
        if commit:
            instance.save()
            self.save_m2m()
        
        return instance


class CambiaStatoOrdineForm(forms.Form):
    """
    Form per cambiare lo stato di un ordine
    """
    
    AZIONI_CHOICES = [
        ('segna_ricevuto', 'Segna come RICEVUTO'),
        ('segna_pagato', 'Segna come PAGATO'),
    ]
    
    azione = forms.ChoiceField(
        choices=AZIONI_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Note sul cambio di stato (opzionale)...'
        })
    )
    
    def __init__(self, ordine, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ordine = ordine
        
        # Filtra le azioni disponibili in base allo stato attuale
        available_choices = []
        
        if ordine.può_essere_ricevuto():
            available_choices.append(('segna_ricevuto', 'Segna come RICEVUTO'))
        
        if ordine.può_essere_pagato():
            available_choices.append(('segna_pagato', 'Segna come PAGATO'))
        
        self.fields['azione'].choices = available_choices
        
        # Disabilita il form se nessuna azione disponibile
        if not available_choices:
            self.fields['azione'].choices = [('', 'Nessuna azione disponibile')]
            self.fields['azione'].widget.attrs['disabled'] = True


class OrdineDettaglioForm(forms.ModelForm):
    """
    Form per visualizzazione/modifica dettagli ordine
    """
    
    class Meta:
        model = OrdineAcquisto
        fields = [
            'note_ordine',
            'riferimento_esterno'
        ]
        widgets = {
            'note_ordine': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
            'riferimento_esterno': forms.TextInput(attrs={
                'class': 'form-control'
            })
        }