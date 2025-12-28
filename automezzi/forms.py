from django import forms
from .models import Automezzo, Manutenzione, AllegatoManutenzione, Rifornimento, EventoAutomezzo

class AutomezzoForm(forms.ModelForm):
    class Meta:
        model = Automezzo
        fields = [
            'numero_mezzo', 'targa', 'marca', 'modello', 'anno_immatricolazione', 'chilometri_attuali',
            'attivo', 'disponibile', 'bloccata', 'motivo_blocco',
            'libretto_fronte', 'libretto_retro', 'assicurazione', 'data_revisione', 'assegnato_a'
        ]
        widgets = {
            'data_revisione': forms.DateInput(attrs={'type': 'date'}),
            'motivo_blocco': forms.Textarea(attrs={'rows': 2}),
        }

class ManutenzioneForm(forms.ModelForm):
    """Form base per la manutenzione (usato per aggiornamenti)"""
    class Meta:
        model = Manutenzione
        fields = [
            'automezzo', 'data_prevista', 'descrizione', 'stato', 
            'fornitore', 'luogo', 'costo', 'seguito_da', 'responsabile', 'allegati'
        ]
        widgets = {
            'data_prevista': forms.DateInput(attrs={'type': 'date'}),
            'descrizione': forms.Textarea(attrs={'rows': 3}),
            'luogo': forms.TextInput(attrs={'placeholder': 'Es. Officina Rossi, Via Roma 10, Milano'}),
        }

class ManutenzioneCreateForm(forms.ModelForm):
    """Form specifico per l'apertura di una nuova manutenzione"""
    class Meta:
        model = Manutenzione
        fields = [
            'automezzo', 'data_prevista', 'descrizione', 
            'fornitore', 'luogo', 'responsabile', 'allegati'
        ]
        widgets = {
            'data_prevista': forms.DateInput(attrs={'type': 'date'}),
            'descrizione': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Descrivi il tipo di manutenzione da eseguire...'}),
            'luogo': forms.TextInput(attrs={'placeholder': 'Es. Officina Rossi, Via Roma 10, Milano'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Per le nuove manutenzioni, il stato è sempre "aperta"
        self.instance.stato = 'aperta'
        
        # Rendi alcuni campi opzionali per la creazione
        self.fields['fornitore'].required = False
        self.fields['luogo'].required = False
        self.fields['responsabile'].required = False
        self.fields['allegati'].required = False
        
        # Aggiungi help text specifici
        self.fields['data_prevista'].help_text = "Data prevista per l'intervento di manutenzione"
        self.fields['fornitore'].help_text = "Seleziona l'officina o il fornitore (opzionale)"
        self.fields['descrizione'].help_text = "Descrivi dettagliatamente il lavoro da eseguire"

class ManutenzioneUpdateForm(forms.ModelForm):
    """Form specifico per l'aggiornamento dello stato manutenzione"""
    class Meta:
        model = Manutenzione
        fields = [
            'automezzo', 'data_prevista', 'descrizione', 'stato',
            'fornitore', 'luogo', 'costo', 'seguito_da', 'responsabile', 'allegati'
        ]
        widgets = {
            'data_prevista': forms.DateInput(attrs={'type': 'date'}),
            'descrizione': forms.Textarea(attrs={'rows': 3}),
            'luogo': forms.TextInput(attrs={'placeholder': 'Es. Officina Rossi, Via Roma 10, Milano'}),
            'costo': forms.NumberInput(attrs={'step': '0.01', 'placeholder': '0.00'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Rendi il campo seguito_da read-only (non modificabile)
        if 'seguito_da' in self.fields:
            self.fields['seguito_da'].widget.attrs['readonly'] = True
            self.fields['seguito_da'].help_text = "Utente che ha aperto la pratica (non modificabile)"
        
        # Rendi il costo obbligatorio solo per stato "terminata"
        if self.instance and hasattr(self.instance, 'stato'):
            if self.instance.stato == 'terminata':
                self.fields['costo'].required = True
                self.fields['costo'].help_text = "Il costo è obbligatorio per manutenzioni terminate"
            else:
                self.fields['costo'].required = False
                self.fields['costo'].help_text = "Il costo può essere inserito quando la manutenzione è terminata"

class ManutenzioneResponsabileForm(forms.ModelForm):
    """Form specifico per il responsabile che porta il mezzo in manutenzione"""
    class Meta:
        model = Manutenzione
        fields = ['foglio_accettazione', 'note_responsabile']
        widgets = {
            'note_responsabile': forms.Textarea(attrs={
                'rows': 3, 
                'placeholder': 'Inserire nome dell\'addetto con cui si ha parlato e altre note importanti...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personalizza i campi
        self.fields['foglio_accettazione'].help_text = "Carica il foglio di accettazione firmato dall'officina"
        self.fields['note_responsabile'].help_text = "Nome dell'addetto, dettagli sulla consegna, condizioni del mezzo, ecc."

class ManutenzioneFinaleForm(forms.ModelForm):
    """Form specifico per il completamento finale della manutenzione"""
    class Meta:
        model = Manutenzione
        fields = ['costo', 'note_finali', 'fattura_fornitore']
        widgets = {
            'costo': forms.NumberInput(attrs={
                'step': '0.01', 
                'placeholder': '0.00',
                'required': True
            }),
            'note_finali': forms.Textarea(attrs={
                'rows': 4, 
                'placeholder': 'Note finali sulla manutenzione, eventuali problemi risolti, raccomandazioni...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Costo obbligatorio per il completamento
        self.fields['costo'].required = True
        self.fields['costo'].help_text = "Costo totale della manutenzione (indicare l'imponibile fattura, non importo ivato)"
        
        # Personalizza altri campi
        self.fields['note_finali'].help_text = "Riepilogo del lavoro svolto, parti sostituite, raccomandazioni future"
        self.fields['fattura_fornitore'].help_text = "Carica la fattura ricevuta dal fornitore"

class AllegatoManutenzioneForm(forms.ModelForm):
    """Form per aggiungere allegati aggiuntivi alla manutenzione"""
    class Meta:
        model = AllegatoManutenzione
        fields = ['nome', 'file']
        widgets = {
            'nome': forms.TextInput(attrs={
                'placeholder': 'Es. Foto danni, Preventivo alternativo, Documento garanzia...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['nome'].help_text = "Nome descrittivo per identificare l'allegato"
        self.fields['file'].help_text = "Seleziona il file da allegare"

class RifornimentoForm(forms.ModelForm):
    class Meta:
        model = Rifornimento
        fields = [
            'automezzo', 'data', 'litri', 'costo_totale',
            'chilometri', 'scontrino'
        ]
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
        }

class EventoAutomezzoForm(forms.ModelForm):
    class Meta:
        model = EventoAutomezzo
        fields = [
            'automezzo', 'tipo', 'data_evento', 'descrizione', 'costo',
            'dipendente_coinvolto', 'file_allegato', 'risolto'
        ]
        widgets = {
            'data_evento': forms.DateInput(attrs={'type': 'date'}),
            'descrizione': forms.Textarea(attrs={'rows': 2}),
        }