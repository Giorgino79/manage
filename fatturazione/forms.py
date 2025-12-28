"""
FATTURAZIONE FORMS - Sistema gestione fatturazione passiva
=======================================================

Forms per gestire il workflow completo della fatturazione passiva:
- FatturaFornitoreForm: Form principale creazione/modifica fattura
- DettaglioFatturaFormSet: FormSet per gestione righe dettaglio
- FatturaSearchForm: Form ricerca e filtri fatture
- ComunicazioneFatturatoForm: Form comunicazioni con fornitori
- ScadenzaPagamentoForm: Form gestione scadenze

Adattato da AMM/fatturazione per progetto Management con:
- Bootstrap 4 styling responsive
- Validazioni workflow-aware
- Calcoli automatici importi
- Upload file integrato
"""

from django import forms
from django.forms import inlineformset_factory, modelformset_factory
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal, InvalidOperation
import logging
from datetime import datetime, timedelta

from .models import (
    FatturaFornitore, 
    DettaglioFattura, 
    ScadenzaPagamento, 
    ComunicazioneFatturato
)
from anagrafica.models import Fornitore
from acquisti.models import OrdineAcquisto

logger = logging.getLogger(__name__)


class FatturaFornitoreForm(forms.ModelForm):
    """
    Form principale per gestione fatture fornitore
    """
    
    # Campo per selezione multipla ordini
    ordini_acquisto = forms.ModelMultipleChoiceField(
        queryset=OrdineAcquisto.objects.none(),  # Verrà popolato dinamicamente
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        help_text="Seleziona gli ordini di acquisto collegati a questa fattura"
    )
    
    class Meta:
        model = FatturaFornitore
        fields = [
            'fornitore', 'numero_fattura', 'data_fattura', 'data_scadenza',
            'termini_pagamento', 'importo_netto', 'importo_iva', 'importo_totale',
            'priorita_pagamento', 'oggetto', 'note_interne', 'file_fattura',
            'ordini_acquisto'
        ]
        
        widgets = {
            'fornitore': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': 'Seleziona fornitore'
            }),
            'numero_fattura': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Numero fattura del fornitore'
            }),
            'data_fattura': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'data_scadenza': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'termini_pagamento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'es: 30gg DFFM, 60 giorni, etc.'
            }),
            'importo_netto': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'importo_iva': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'importo_totale': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'priorita_pagamento': forms.Select(attrs={
                'class': 'form-control'
            }),
            'oggetto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrizione/oggetto della fattura'
            }),
            'note_interne': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Note interne (non visibili al fornitore)'
            }),
            'file_fattura': forms.FileInput(attrs={
                'class': 'form-control-file',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
        }
        
        help_texts = {
            'numero_fattura': 'Numero fattura del fornitore',
            'termini_pagamento': 'Termini di pagamento (es: 30gg DFFM, 60 giorni)',
            'file_fattura': 'File fattura (PDF, JPG, PNG - max 10MB)'
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.fornitore_filter = kwargs.pop('fornitore', None)
        super().__init__(*args, **kwargs)
        
        # Configura queryset ordini acquisto
        # Inizialmente vuoto, verrà popolato tramite AJAX quando si seleziona il fornitore
        self.fields['ordini_acquisto'].queryset = OrdineAcquisto.objects.none()
        
        # Se abbiamo un fornitore specificato, filtra subito
        if self.fornitore_filter:
            self.fields['ordini_acquisto'].queryset = OrdineAcquisto.objects.filter(
                fornitore=self.fornitore_filter,
                stato__in=['CREATO', 'RICEVUTO']
            ).order_by('-data_ordine')
        
        # Se stiamo modificando una fattura esistente, popola gli ordini collegati
        if self.instance and self.instance.pk:
            if self.instance.fornitore:
                self.fields['ordini_acquisto'].queryset = OrdineAcquisto.objects.filter(
                    fornitore=self.instance.fornitore,
                    stato__in=['CREATO', 'RICEVUTO']
                ).order_by('-data_ordine')
                
                # Pre-seleziona gli ordini già collegati
                self.fields['ordini_acquisto'].initial = self.instance.ordini_acquisto.all()
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validazione date
        data_fattura = cleaned_data.get('data_fattura')
        data_scadenza = cleaned_data.get('data_scadenza')
        
        if data_fattura and data_scadenza:
            if data_scadenza <= data_fattura:
                raise ValidationError({
                    'data_scadenza': 'La data scadenza deve essere successiva alla data fattura'
                })
        
        # Validazione importi
        importo_netto = cleaned_data.get('importo_netto')
        importo_iva = cleaned_data.get('importo_iva')
        importo_totale = cleaned_data.get('importo_totale')
        
        if importo_netto and importo_iva and importo_totale:
            totale_calcolato = importo_netto + importo_iva
            if abs(totale_calcolato - importo_totale) > Decimal('0.01'):
                raise ValidationError({
                    'importo_totale': f'Importo totale non corretto. Dovrebbe essere {totale_calcolato}'
                })
        
        # Calcola scadenza automatica se necessario
        if not data_scadenza and data_fattura and cleaned_data.get('termini_pagamento'):
            termini = cleaned_data.get('termini_pagamento', '').upper()
            if 'DFFM' in termini or 'GG' in termini or 'GIORNI' in termini:
                # Prova calcolo automatico
                try:
                    giorni = self._estrai_giorni_da_termini(termini)
                    if 'DFFM' in termini:
                        # Fine mese + giorni
                        fine_mese = data_fattura.replace(day=28) + timedelta(days=4)
                        fine_mese = fine_mese - timedelta(days=fine_mese.day)
                        cleaned_data['data_scadenza'] = fine_mese + timedelta(days=giorni)
                    else:
                        # Giorni dalla fattura
                        cleaned_data['data_scadenza'] = data_fattura + timedelta(days=giorni)
                except:
                    pass  # Calcolo fallito, utente deve inserire manualmente
        
        # Validazione duplicati
        fornitore = cleaned_data.get('fornitore')
        numero_fattura = cleaned_data.get('numero_fattura')
        
        if fornitore and numero_fattura and data_fattura:
            existing = FatturaFornitore.objects.filter(
                fornitore=fornitore,
                numero_fattura=numero_fattura,
                data_fattura=data_fattura
            )
            
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
                
            if existing.exists():
                raise ValidationError({
                    'numero_fattura': 'Fattura già presente per questo fornitore con stesso numero e data'
                })
        
        return cleaned_data
    
    def _estrai_giorni_da_termini(self, termini):
        """Estrae giorni dai termini di pagamento"""
        import re
        match = re.search(r'(\d+)', termini)
        return int(match.group(1)) if match else 30
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.user:
            if not instance.pk:
                instance.creata_da = self.user
            instance.modificata_da = self.user
        
        if commit:
            instance.save()
            # Salva le relazioni many-to-many
            self.save_m2m()
            
            # Se ci sono ordini selezionati, calcola la differenza
            if instance.ordini_acquisto.exists():
                instance.calcola_differenza_ordine()
                instance.save(update_fields=['differenza_importo'])
            
        return instance


class DettaglioFatturaForm(forms.ModelForm):
    """
    Form per singola riga di dettaglio fattura
    """
    
    class Meta:
        model = DettaglioFattura
        fields = [
            'descrizione', 'quantita', 'unita_misura', 'prezzo_unitario',
            'sconto_percentuale', 'aliquota_iva', 'note_riga'
        ]
        
        widgets = {
            'descrizione': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrizione prodotto/servizio'
            }),
            'quantita': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'unita_misura': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'pz, kg, ore, etc.'
            }),
            'prezzo_unitario': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'sconto_percentuale': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'aliquota_iva': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'note_riga': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Note specifiche della riga'
            }),
        }


# FormSet per gestione dettagli fattura
DettaglioFatturaFormSet = inlineformset_factory(
    FatturaFornitore,
    DettaglioFattura,
    form=DettaglioFatturaForm,
    extra=1,
    can_delete=True,
    fields=['descrizione', 'quantita', 'unita_misura', 'prezzo_unitario', 
           'sconto_percentuale', 'aliquota_iva', 'note_riga']
)


class FatturaSearchForm(forms.Form):
    """
    Form per ricerca e filtri fatture
    """
    
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cerca per numero, fornitore, oggetto...'
        }),
        label='Ricerca'
    )
    
    fornitore = forms.ModelChoiceField(
        queryset=Fornitore.objects.all(),
        required=False,
        empty_label='Tutti i fornitori',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    stato = forms.ChoiceField(
        choices=[('', 'Tutti gli stati')] + FatturaFornitore.STATI_FATTURA,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    priorita = forms.ChoiceField(
        choices=[('', 'Tutte le priorità')] + FatturaFornitore.PRIORITA_PAGAMENTO,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    data_fattura_da = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Data fattura da'
    )
    
    data_fattura_a = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Data fattura a'
    )
    
    data_scadenza_da = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Scadenza da'
    )
    
    data_scadenza_a = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Scadenza a'
    )
    
    scadute = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Solo fatture scadute'
    )
    
    in_scadenza = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='In scadenza (prossimi 7 giorni)'
    )


class ComunicazioneFatturatoForm(forms.ModelForm):
    """
    Form per comunicazioni con fornitori
    """
    
    class Meta:
        model = ComunicazioneFatturato
        fields = [
            'tipo_comunicazione', 'oggetto', 'messaggio', 
            'email_destinatario'
        ]
        
        widgets = {
            'tipo_comunicazione': forms.Select(attrs={
                'class': 'form-control'
            }),
            'oggetto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Oggetto comunicazione'
            }),
            'messaggio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Contenuto del messaggio...'
            }),
            'email_destinatario': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@fornitore.com'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.fattura = kwargs.pop('fattura', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Pre-compila email se fattura ha fornitore
        if self.fattura and hasattr(self.fattura.fornitore, 'email'):
            self.fields['email_destinatario'].initial = self.fattura.fornitore.email
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.fattura:
            instance.fattura = self.fattura
        if self.user:
            instance.creata_da = self.user
            
        if commit:
            instance.save()
            
        return instance


class ScadenzaPagamentoForm(forms.ModelForm):
    """
    Form per gestione scadenze pagamento
    """
    
    class Meta:
        model = ScadenzaPagamento
        fields = [
            'data_scadenza', 'importo_scadenza', 'priorita',
            'note_pagamento', 'promemoria_giorni'
        ]
        
        widgets = {
            'data_scadenza': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'importo_scadenza': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'priorita': forms.Select(attrs={
                'class': 'form-control'
            }),
            'note_pagamento': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Note sul pagamento...'
            }),
            'promemoria_giorni': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '30'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.fattura = kwargs.pop('fattura', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Pre-compila importo con totale fattura
        if self.fattura and not self.instance.pk:
            self.fields['importo_scadenza'].initial = self.fattura.importo_totale
    
    def clean_importo_scadenza(self):
        importo = self.cleaned_data.get('importo_scadenza')
        
        if self.fattura and importo:
            if importo > self.fattura.importo_totale:
                raise ValidationError(
                    f'Importo scadenza non può essere superiore al totale fattura (€{self.fattura.importo_totale})'
                )
        
        return importo
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.fattura:
            instance.fattura = self.fattura
        if self.user:
            instance.creata_da = self.user
            
        if commit:
            instance.save()
            
        return instance


class ExportOrdiniForm(forms.Form):
    """
    Form per export ordini di acquisto in vari formati
    """
    
    FORMATO_CHOICES = [
        ('pdf', 'PDF - Report dettagliato'),
        ('excel', 'Excel - Foglio di calcolo'),
        ('csv', 'CSV - Dati separati da virgola'),
    ]
    
    STATO_CHOICES = [
        ('', 'Tutti gli stati'),
        ('CREATO', 'Creati'),
        ('RICEVUTO', 'Ricevuti'),
        ('PAGATO', 'Pagati'),
    ]
    
    data_da = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Data da',
        help_text='Data inizio periodo (inclusa)'
    )
    
    data_a = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Data a',
        help_text='Data fine periodo (inclusa)'
    )
    
    fornitore = forms.ModelChoiceField(
        queryset=None,  # Verrà popolato nel __init__
        required=False,
        empty_label='Tutti i fornitori',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Fornitore'
    )
    
    stato = forms.ChoiceField(
        choices=STATO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Stato ordine'
    )
    
    formato = forms.ChoiceField(
        choices=FORMATO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Formato export'
    )
    
    includi_iva = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Includi calcolo IVA',
        help_text='Aggiungi colonne per IVA e totale lordo'
    )
    
    aliquota_iva = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        initial=22.00,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0',
            'max': '100'
        }),
        label='Aliquota IVA (%)',
        help_text='Aliquota IVA da applicare per i calcoli'
    )
    
    raggruppa_per_fornitore = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Raggruppa per fornitore',
        help_text='Organizza i dati per fornitore con subtotali'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Popola i fornitori
        from anagrafica.models import Fornitore
        self.fields['fornitore'].queryset = Fornitore.objects.filter(
            attivo=True
        ).order_by('nome')
        
        # Imposta date di default (ultimo mese)
        from django.utils import timezone
        from datetime import timedelta
        
        oggi = timezone.now().date()
        un_mese_fa = oggi - timedelta(days=30)
        
        if not self.data:
            self.fields['data_da'].initial = un_mese_fa
            self.fields['data_a'].initial = oggi
    
    def clean(self):
        cleaned_data = super().clean()
        data_da = cleaned_data.get('data_da')
        data_a = cleaned_data.get('data_a')
        
        if data_da and data_a:
            if data_da > data_a:
                raise ValidationError({
                    'data_a': 'La data fine deve essere successiva alla data inizio'
                })
            
            # Verifica che il periodo non sia troppo esteso (max 1 anno)
            if (data_a - data_da).days > 365:
                raise ValidationError({
                    'data_a': 'Il periodo non può essere superiore a 1 anno'
                })
        
        return cleaned_data


class WorkflowActionForm(forms.Form):
    """
    Form per azioni di workflow (controllo, contabilizzazione, pagamento)
    """
    
    ACTION_CHOICES = [
        ('ricevuta', 'Segna come Ricevuta'),
        ('controllata', 'Segna come Controllata'),
        ('contabilizzata', 'Segna come Contabilizzata'),
        ('programmata', 'Segna come Programmata'),
        ('pagata', 'Segna come Pagata'),
        ('storna', 'Storna Fattura'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Note sull\'azione (opzionale)...'
        })
    )
    
    # Campi specifici per pagamento
    data_pagamento = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    importo_pagato = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0'
        })
    )
    
    modalita_pagamento = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Bonifico, contanti, etc.'
        })
    )
    
    file_ricevuta = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control-file',
            'accept': '.pdf,.jpg,.jpeg,.png'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.fattura = kwargs.pop('fattura', None)
        super().__init__(*args, **kwargs)
        
        if self.fattura:
            # Pre-compila importo pagamento
            self.fields['importo_pagato'].initial = self.fattura.importo_totale
            
            # Filtra azioni disponibili in base allo stato
            available_actions = []
            if self.fattura.stato == 'ATTESA':
                available_actions.append(('ricevuta', 'Segna come Ricevuta'))
            elif self.fattura.stato == 'RICEVUTA':
                available_actions.append(('controllata', 'Segna come Controllata'))
            elif self.fattura.stato == 'CONTROLLATA':
                available_actions.append(('contabilizzata', 'Segna come Contabilizzata'))
            elif self.fattura.stato == 'CONTABILIZZATA':
                available_actions.append(('programmata', 'Segna come Programmata'))
            elif self.fattura.stato == 'PROGRAMMATA':
                available_actions.append(('pagata', 'Segna come Pagata'))
            
            # Storno sempre disponibile (tranne se già pagata/stornata)
            if self.fattura.può_essere_stornata():
                available_actions.append(('storna', 'Storna Fattura'))
            
            self.fields['action'].choices = available_actions
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        
        # Validazioni specifiche per pagamento
        if action == 'pagata':
            if not cleaned_data.get('data_pagamento'):
                cleaned_data['data_pagamento'] = timezone.now().date()
            
            if not cleaned_data.get('importo_pagato'):
                if self.fattura:
                    cleaned_data['importo_pagato'] = self.fattura.importo_totale
        
        return cleaned_data