"""
FORMS PER CHAT E PROMEMORIA
===========================

Forms per la gestione di chat, messaggi e promemoria
nel sistema Management.

Versione: 1.0
"""

from django import forms
from django.contrib.auth import get_user_model
from ..models import Messaggio, Promemoria

User = get_user_model()


class MessaggioForm(forms.ModelForm):
    """Form per l'invio di messaggi"""
    
    class Meta:
        model = Messaggio
        fields = ['destinatario', 'testo', 'allegato']
        widgets = {
            'destinatario': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'testo': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Scrivi il tuo messaggio...',
                'required': True
            }),
            'allegato': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.gif,.zip'
            })
        }
        labels = {
            'destinatario': 'Destinatario',
            'testo': 'Messaggio',
            'allegato': 'Allegato (opzionale)'
        }
    
    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        
        # Escludi l'utente corrente dalla lista destinatari
        if current_user:
            self.fields['destinatario'].queryset = User.objects.exclude(
                pk=current_user.pk
            ).filter(is_active=True).order_by('first_name', 'last_name', 'username')
        else:
            self.fields['destinatario'].queryset = User.objects.filter(
                is_active=True
            ).order_by('first_name', 'last_name', 'username')


class PromemorialForm(forms.ModelForm):
    """Form per creazione/modifica promemoria"""
    
    class Meta:
        model = Promemoria
        fields = [
            'titolo', 'descrizione', 'data_scadenza', 
            'priorita', 'assegnato_a'
        ]
        widgets = {
            'titolo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titolo del promemoria...',
                'required': True,
                'maxlength': 200
            }),
            'descrizione': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descrizione dettagliata (opzionale)...'
            }),
            'data_scadenza': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'priorita': forms.Select(attrs={
                'class': 'form-select'
            }),
            'assegnato_a': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            })
        }
        labels = {
            'titolo': 'Titolo',
            'descrizione': 'Descrizione',
            'data_scadenza': 'Data scadenza (opzionale)',
            'priorita': 'Priorità',
            'assegnato_a': 'Assegnato a'
        }
    
    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        
        # Lista utenti attivi per assegnazione
        self.fields['assegnato_a'].queryset = User.objects.filter(
            is_active=True
        ).order_by('first_name', 'last_name', 'username')
        
        # Se c'è un utente corrente, preselezionalo come assegnatario
        if current_user and not self.instance.pk:
            self.fields['assegnato_a'].initial = current_user


class PromemorialSearchForm(forms.Form):
    """Form per la ricerca nei promemoria"""
    
    STATUS_CHOICES = [
        ('', 'Tutti i promemoria'),
        ('attivi', 'Solo attivi'),
        ('completati', 'Solo completati'),
        ('scaduti', 'Solo scaduti')
    ]
    
    PRIORITA_ALL = [('', 'Tutte le priorità')] + Promemoria.Priorita.choices
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cerca per titolo o descrizione...'
        }),
        label='Ricerca'
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Stato'
    )
    
    priorita = forms.ChoiceField(
        choices=PRIORITA_ALL,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Priorità'
    )
    
    assegnato_a = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by(
            'first_name', 'last_name', 'username'
        ),
        required=False,
        empty_label='Tutti gli utenti',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Assegnato a'
    )
    
    data_da = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Scadenza da'
    )
    
    data_a = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Scadenza a'
    )


class ChatFilterForm(forms.Form):
    """Form per filtri nella chat"""
    
    contatto = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by(
            'first_name', 'last_name', 'username'
        ),
        required=False,
        empty_label='Seleziona contatto...',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'select-contatto'
        }),
        label='Contatto'
    )
    
    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        
        # Escludi l'utente corrente dalla lista contatti
        if current_user:
            self.fields['contatto'].queryset = User.objects.exclude(
                pk=current_user.pk
            ).filter(is_active=True).order_by('first_name', 'last_name', 'username')