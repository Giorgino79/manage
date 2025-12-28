from django import forms
from django.core.exceptions import ValidationError
from django.forms import modelformset_factory, inlineformset_factory
from django.utils import timezone
from decimal import Decimal
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field, HTML, Div, Fieldset
from crispy_forms.bootstrap import InlineCheckboxes, PrependedText, AppendedText, Alert
from datetime import date, timedelta
from django.contrib.auth import get_user_model

from .models import Stabilimento, CostiStabilimento, DocStabilimento
from anagrafica.models import Fornitore

User = get_user_model()


# =====================================
# FORM PRINCIPALE STABILIMENTO
# =====================================

class StabilimentoForm(forms.ModelForm):
    """
    Form principale per la creazione/modifica di uno stabilimento.
    """
    
    class Meta:
        model = Stabilimento
        fields = [
            'nome',
            'indirizzo',
            'cap',
            'citta',
            'provincia',
            'telefono',
            'email_filiale',
            'responsabile_operativo',
            'responsabile_amministrativo',
            'superficie_mq',
            'numero_piani',
            'anno_costruzione',
            'data_apertura',
            'note_generali'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome dello stabilimento'
            }),
            'indirizzo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Via, numero civico'
            }),
            'cap': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '12345',
                'maxlength': '5'
            }),
            'citta': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Città'
            }),
            'provincia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'RM',
                'maxlength': '2',
                'style': 'text-transform: uppercase;'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+39 06 12345678'
            }),
            'email_filiale': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'stabilimento@azienda.it'
            }),
            'responsabile_operativo': forms.Select(attrs={
                'class': 'form-select'
            }),
            'responsabile_amministrativo': forms.Select(attrs={
                'class': 'form-select'
            }),
            'superficie_mq': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'numero_piani': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '50'
            }),
            'anno_costruzione': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1800',
                'max': timezone.now().year
            }),
            'data_apertura': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'note_generali': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Note generali sullo stabilimento...'
            })
        }
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
        # Configura queryset utenti attivi
        self.fields['responsabile_operativo'].queryset = User.objects.filter(
            is_active=True
        ).order_by('first_name', 'last_name', 'username')
        self.fields['responsabile_amministrativo'].queryset = User.objects.filter(
            is_active=True
        ).order_by('first_name', 'last_name', 'username')
        
        # Empty labels
        self.fields['responsabile_operativo'].empty_label = "Seleziona responsabile operativo"
        self.fields['responsabile_amministrativo'].empty_label = "Seleziona responsabile amministrativo"
        
        # Precompila con utente corrente se nuovo stabilimento
        if not self.instance.pk and user:
            self.fields['responsabile_operativo'].initial = user
        
        # Labels personalizzati
        self.fields['nome'].label = "Nome Stabilimento *"
        self.fields['indirizzo'].label = "Indirizzo *"
        self.fields['cap'].label = "CAP *"
        self.fields['citta'].label = "Città *"
        self.fields['provincia'].label = "Provincia *"
        self.fields['telefono'].label = "Telefono"
        self.fields['email_filiale'].label = "Email Stabilimento"
        self.fields['responsabile_operativo'].label = "Responsabile Operativo"
        self.fields['responsabile_amministrativo'].label = "Responsabile Amministrativo"
        self.fields['superficie_mq'].label = "Superficie (mq)"
        self.fields['numero_piani'].label = "Numero Piani"
        self.fields['anno_costruzione'].label = "Anno Costruzione"
        self.fields['data_apertura'].label = "Data Apertura"
        self.fields['note_generali'].label = "Note Generali"
        
        # Help text
        self.fields['responsabile_operativo'].help_text = "Responsabile delle operazioni quotidiane"
        self.fields['responsabile_amministrativo'].help_text = "Responsabile degli aspetti amministrativi"
        self.fields['superficie_mq'].help_text = "Superficie totale in metri quadrati"
        self.fields['anno_costruzione'].help_text = "Anno di costruzione dell'edificio"
        
        # Setup Crispy Forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Alert(
                content="Compila i dati dello stabilimento. I campi contrassegnati con * sono obbligatori.",
                css_class="alert-info"
            ),
            Fieldset(
                'Dati Anagrafici',
                Row(
                    Column('nome', css_class='form-group col-md-8'),
                    Column('codice_stabilimento', css_class='form-group col-md-4') if self.instance.pk else None,
                ),
                Row(
                    Column('indirizzo', css_class='form-group col-md-12'),
                ),
                Row(
                    Column('cap', css_class='form-group col-md-2'),
                    Column('citta', css_class='form-group col-md-6'),
                    Column('provincia', css_class='form-group col-md-2'),
                ),
                Row(
                    Column('telefono', css_class='form-group col-md-6'),
                    Column('email_filiale', css_class='form-group col-md-6'),
                )
            ),
            Fieldset(
                'Responsabili',
                Row(
                    Column('responsabile_operativo', css_class='form-group col-md-6'),
                    Column('responsabile_amministrativo', css_class='form-group col-md-6'),
                )
            ),
            Fieldset(
                'Caratteristiche Strutturali',
                Row(
                    Column('superficie_mq', css_class='form-group col-md-4'),
                    Column('numero_piani', css_class='form-group col-md-4'),
                    Column('anno_costruzione', css_class='form-group col-md-4'),
                ),
                'data_apertura'
            ),
            Fieldset(
                'Note',
                'note_generali'
            )
        )
        
        # Rimuovi campi None dal layout
        self.helper.layout.fields = [f for f in self.helper.layout.fields if f is not None]
    
    def clean_provincia(self):
        """Validazione provincia"""
        provincia = self.cleaned_data.get('provincia')
        if provincia:
            provincia = provincia.upper()
            if len(provincia) != 2:
                raise ValidationError("La provincia deve essere di 2 lettere")
        return provincia
    
    def clean_anno_costruzione(self):
        """Validazione anno costruzione"""
        anno = self.cleaned_data.get('anno_costruzione')
        if anno:
            anno_corrente = timezone.now().year
            if anno < 1800 or anno > anno_corrente:
                raise ValidationError(f"L'anno deve essere compreso tra 1800 e {anno_corrente}")
        return anno
    
    def clean_data_apertura(self):
        """Validazione data apertura"""
        data = self.cleaned_data.get('data_apertura')
        if data:
            if data > date.today():
                raise ValidationError("La data di apertura non può essere nel futuro")
        return data


# =====================================
# FORM COSTI STABILIMENTO
# =====================================

class CostiStabilimentoForm(forms.ModelForm):
    """
    Form per la gestione dei costi di stabilimento.
    """
    
    class Meta:
        model = CostiStabilimento
        fields = [
            'stabilimento',
            'fornitore',
            'causale',
            'stato',
            'titolo',
            'descrizione',
            'importo',
            'iva_percentuale',
            'data_richiesta',
            'data_inizio_lavori',
            'data_fine_lavori',
            'data_fattura',
            'data_scadenza_servizio',
            'preventivo',
            'fattura',
            'certificato',
            'note_interne'
        ]
        widgets = {
            'stabilimento': forms.Select(attrs={'class': 'form-select'}),
            'fornitore': forms.Select(attrs={'class': 'form-select'}),
            'causale': forms.Select(attrs={'class': 'form-select'}),
            'stato': forms.Select(attrs={'class': 'form-select'}),
            'titolo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titolo dell\'intervento o servizio'
            }),
            'descrizione': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descrizione dettagliata...'
            }),
            'importo': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01'
            }),
            'iva_percentuale': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'value': '22'
            }),
            'data_richiesta': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'data_inizio_lavori': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'data_fine_lavori': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'data_fattura': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'data_scadenza_servizio': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'preventivo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png'
            }),
            'fattura': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png'
            }),
            'certificato': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png'
            }),
            'note_interne': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Note interne non visibili nei documenti...'
            })
        }
    
    def __init__(self, *args, user=None, stabilimento=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
        # Configura queryset
        self.fields['stabilimento'].queryset = Stabilimento.objects.attivi().order_by('nome')
        self.fields['fornitore'].queryset = Fornitore.objects.filter(attivo=True).order_by('nome')
        
        # Preseleziona stabilimento se specificato
        if stabilimento and not self.instance.pk:
            self.fields['stabilimento'].initial = stabilimento
        
        # Labels
        self.fields['stabilimento'].label = "Stabilimento *"
        self.fields['fornitore'].label = "Fornitore *"
        self.fields['causale'].label = "Tipologia Costo *"
        self.fields['stato'].label = "Stato Pratica *"
        self.fields['titolo'].label = "Titolo *"
        self.fields['descrizione'].label = "Descrizione *"
        self.fields['importo'].label = "Importo (€) *"
        self.fields['iva_percentuale'].label = "IVA %"
        self.fields['data_richiesta'].label = "Data Richiesta"
        self.fields['data_inizio_lavori'].label = "Data Inizio Lavori"
        self.fields['data_fine_lavori'].label = "Data Fine Lavori"
        self.fields['data_fattura'].label = "Data Fattura"
        self.fields['data_scadenza_servizio'].label = "Prossima Scadenza"
        self.fields['preventivo'].label = "File Preventivo"
        self.fields['fattura'].label = "File Fattura"
        self.fields['certificato'].label = "Certificato/Documento"
        self.fields['note_interne'].label = "Note Interne"
        
        # Help text
        self.fields['data_scadenza_servizio'].help_text = "Data del prossimo intervento o scadenza certificazione"
        self.fields['importo'].help_text = "Importo senza IVA"
        self.fields['note_interne'].help_text = "Note visibili solo internamente"
        
        # Setup Crispy Forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.layout = Layout(
            Alert(
                content="Inserisci i dettagli del costo/servizio per lo stabilimento.",
                css_class="alert-info"
            ),
            Fieldset(
                'Identificazione',
                Row(
                    Column('stabilimento', css_class='form-group col-md-6'),
                    Column('fornitore', css_class='form-group col-md-6'),
                ),
                Row(
                    Column('causale', css_class='form-group col-md-6'),
                    Column('stato', css_class='form-group col-md-6'),
                ),
                'titolo',
                'descrizione'
            ),
            Fieldset(
                'Aspetti Economici',
                Row(
                    Column('importo', css_class='form-group col-md-6'),
                    Column('iva_percentuale', css_class='form-group col-md-6'),
                )
            ),
            Fieldset(
                'Date',
                Row(
                    Column('data_richiesta', css_class='form-group col-md-6'),
                    Column('data_scadenza_servizio', css_class='form-group col-md-6'),
                ),
                Row(
                    Column('data_inizio_lavori', css_class='form-group col-md-6'),
                    Column('data_fine_lavori', css_class='form-group col-md-6'),
                ),
                'data_fattura'
            ),
            Fieldset(
                'Documenti',
                Row(
                    Column('preventivo', css_class='form-group col-md-4'),
                    Column('fattura', css_class='form-group col-md-4'),
                    Column('certificato', css_class='form-group col-md-4'),
                )
            ),
            Fieldset(
                'Note',
                'note_interne'
            )
        )
    
    def clean_importo(self):
        """Validazione importo"""
        importo = self.cleaned_data.get('importo')
        if importo and importo <= 0:
            raise ValidationError("L'importo deve essere maggiore di zero")
        if importo and importo > Decimal('9999999.99'):
            raise ValidationError("L'importo non può superare 9.999.999,99 euro")
        return importo
    
    def clean(self):
        """Validazioni incrociate"""
        cleaned_data = super().clean()
        data_inizio = cleaned_data.get('data_inizio_lavori')
        data_fine = cleaned_data.get('data_fine_lavori')
        data_richiesta = cleaned_data.get('data_richiesta')
        
        # Verifica date lavori
        if data_inizio and data_fine and data_inizio > data_fine:
            raise ValidationError("La data di fine lavori non può essere precedente all'inizio")
        
        # Verifica data richiesta
        if data_richiesta and data_inizio and data_richiesta > data_inizio:
            raise ValidationError("La data di richiesta non può essere successiva all'inizio lavori")
        
        return cleaned_data


# =====================================
# FORM DOCUMENTI STABILIMENTO
# =====================================

class DocStabilimentoForm(forms.ModelForm):
    """
    Form per la gestione dei documenti di stabilimento.
    """
    
    class Meta:
        model = DocStabilimento
        fields = [
            'stabilimento',
            'nome_documento',
            'tipo_documento',
            'versione',
            'descrizione',
            'file_documento',
            'data_documento',
            'data_scadenza',
            'note'
        ]
        widgets = {
            'stabilimento': forms.Select(attrs={'class': 'form-select'}),
            'nome_documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome identificativo del documento'
            }),
            'tipo_documento': forms.Select(attrs={'class': 'form-select'}),
            'versione': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1.0'
            }),
            'descrizione': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrizione del contenuto...'
            }),
            'file_documento': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.dwg'
            }),
            'data_documento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'data_scadenza': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Note aggiuntive...'
            })
        }
    
    def __init__(self, *args, user=None, stabilimento=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
        # Configura queryset
        self.fields['stabilimento'].queryset = Stabilimento.objects.attivi().order_by('nome')
        
        # Preseleziona stabilimento se specificato
        if stabilimento and not self.instance.pk:
            self.fields['stabilimento'].initial = stabilimento
        
        # Labels
        self.fields['stabilimento'].label = "Stabilimento *"
        self.fields['nome_documento'].label = "Nome Documento *"
        self.fields['tipo_documento'].label = "Tipo Documento *"
        self.fields['versione'].label = "Versione"
        self.fields['descrizione'].label = "Descrizione"
        self.fields['file_documento'].label = "File Documento *"
        self.fields['data_documento'].label = "Data Documento"
        self.fields['data_scadenza'].label = "Data Scadenza"
        self.fields['note'].label = "Note"
        
        # Help text
        self.fields['versione'].help_text = "Versione del documento (es. 1.0, 2.1)"
        self.fields['data_documento'].help_text = "Data del documento (se diversa da oggi)"
        self.fields['data_scadenza'].help_text = "Data di scadenza del documento (se applicabile)"
        
        # Setup Crispy Forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.layout = Layout(
            Alert(
                content="Carica un nuovo documento per lo stabilimento.",
                css_class="alert-info"
            ),
            Row(
                Column('stabilimento', css_class='form-group col-md-6'),
                Column('tipo_documento', css_class='form-group col-md-6'),
            ),
            Row(
                Column('nome_documento', css_class='form-group col-md-8'),
                Column('versione', css_class='form-group col-md-4'),
            ),
            'descrizione',
            'file_documento',
            Row(
                Column('data_documento', css_class='form-group col-md-6'),
                Column('data_scadenza', css_class='form-group col-md-6'),
            ),
            'note'
        )
    
    def clean_data_scadenza(self):
        """Validazione data scadenza"""
        data_scadenza = self.cleaned_data.get('data_scadenza')
        data_documento = self.cleaned_data.get('data_documento')
        
        if data_scadenza:
            if data_documento and data_scadenza < data_documento:
                raise ValidationError("La data di scadenza non può essere precedente alla data del documento")
        
        return data_scadenza


# =====================================
# FORM DI RICERCA E FILTRI
# =====================================

class StabilimentiSearchForm(forms.Form):
    """Form per ricerca e filtri nella lista stabilimenti"""
    
    q = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cerca per nome, città, codice...',
            'autocomplete': 'off'
        })
    )
    
    responsabile = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('first_name', 'last_name'),
        required=False,
        empty_label="Tutti i responsabili",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    provincia = forms.CharField(
        max_length=2,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'RM',
            'maxlength': '2'
        })
    )
    
    attivo = forms.ChoiceField(
        choices=[
            ('', 'Tutti gli stabilimenti'),
            ('true', 'Solo attivi'),
            ('false', 'Solo inattivi')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Labels
        self.fields['q'].label = "Cerca"
        self.fields['responsabile'].label = "Responsabile"
        self.fields['provincia'].label = "Provincia"
        self.fields['attivo'].label = "Stato"
        
        # Setup Crispy Forms
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.layout = Layout(
            Row(
                Column('q', css_class='form-group col-md-4'),
                Column('responsabile', css_class='form-group col-md-3'),
                Column('provincia', css_class='form-group col-md-2'),
                Column('attivo', css_class='form-group col-md-2'),
                Column(
                    Submit('submit', 'Filtra', css_class='btn btn-primary'),
                    css_class='form-group col-md-1 d-flex align-items-end'
                ),
            )
        )


class CostiSearchForm(forms.Form):
    """Form per ricerca costi stabilimenti"""
    
    stabilimento = forms.ModelChoiceField(
        queryset=Stabilimento.objects.attivi().order_by('nome'),
        required=False,
        empty_label="Tutti gli stabilimenti",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    causale = forms.ChoiceField(
        choices=[('', 'Tutte le tipologie')] + list(CostiStabilimento.TipoCosto.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    stato = forms.ChoiceField(
        choices=[('', 'Tutti gli stati')] + list(CostiStabilimento.StatoCosto.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    fornitore = forms.ModelChoiceField(
        queryset=Fornitore.objects.filter(attivo=True).order_by('nome'),
        required=False,
        empty_label="Tutti i fornitori",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    scadenze_prossime = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    anno = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Popola anni disponibili
        anni_disponibili = [('', 'Tutti gli anni')]
        anno_corrente = timezone.now().year
        for anno in range(anno_corrente, anno_corrente - 5, -1):
            anni_disponibili.append((str(anno), str(anno)))
        self.fields['anno'].choices = anni_disponibili
        
        # Labels
        self.fields['stabilimento'].label = "Stabilimento"
        self.fields['causale'].label = "Tipologia"
        self.fields['stato'].label = "Stato"
        self.fields['fornitore'].label = "Fornitore"
        self.fields['scadenze_prossime'].label = "Solo scadenze prossime (30 gg)"
        self.fields['anno'].label = "Anno"
        
        # Setup Crispy Forms
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.layout = Layout(
            Row(
                Column('stabilimento', css_class='form-group col-md-3'),
                Column('causale', css_class='form-group col-md-2'),
                Column('stato', css_class='form-group col-md-2'),
                Column('fornitore', css_class='form-group col-md-2'),
                Column('anno', css_class='form-group col-md-2'),
                Column(
                    Submit('submit', 'Filtra', css_class='btn btn-primary'),
                    css_class='form-group col-md-1 d-flex align-items-end'
                ),
            ),
            Row(
                Column('scadenze_prossime', css_class='form-group col-md-3'),
            )
        )
        
# Sostituisci il UtenzaForm esistente nel file stabilimenti/forms.py con questo:

# In stabilimenti/forms.py, sostituisci UtenzaForm con questa versione:

class UtenzaForm(CostiStabilimentoForm):
    """
    Form specializzato per utenze - estende CostiStabilimentoForm
    """
    
    class Meta(CostiStabilimentoForm.Meta):
        # Usa la stessa lista di campi di base più i nuovi
        fields = [
            'stabilimento',
            'fornitore',
            'causale',
            'stato',
            'titolo',
            'descrizione',
            'importo',
            'iva_percentuale',
            'data_richiesta',
            'data_inizio_lavori',
            'data_fine_lavori',
            'data_fattura',
            'data_scadenza_servizio',
            'preventivo',
            'fattura',
            'certificato',
            'note_interne',
            # Campi specifici utenze
            'consumo_kwh', 
            'consumo_mc', 
            'periodo_fatturazione_da', 
            'periodo_fatturazione_a',
            'codice_pdr_pod'
        ]
        
        # Estendi i widgets ereditando quelli esistenti
        widgets = {
            **CostiStabilimentoForm.Meta.widgets,  # Eredita tutti i widget esistenti
            # Widget per i nuovi campi
            'consumo_kwh': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'consumo_mc': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'periodo_fatturazione_da': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'periodo_fatturazione_a': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'codice_pdr_pod': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Codice identificativo utenza'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # NASCONDI IL CAMPO data_richiesta (sarà impostato automaticamente)
        self.fields['data_richiesta'].widget = forms.HiddenInput()
        self.fields['data_richiesta'].required = False
        
        # Preimposta data_richiesta se non presente
        if not self.instance.pk and not self.fields['data_richiesta'].initial:
            self.fields['data_richiesta'].initial = timezone.now().date()
        
        # Filtra solo le causali utenze
        UTENZE_CHOICES = [
            ('energia_elettrica', 'Energia Elettrica'),
            ('gas_naturale', 'Gas Naturale'),
            ('acqua', 'Acqua e Scarichi'),
            ('telefonia', 'Telefonia e Internet'),
            ('rifiuti', 'Smaltimento Rifiuti'),
        ]
        self.fields['causale'].choices = [('', '---------')] + UTENZE_CHOICES
        
        # Labels specifici per utenze
        self.fields['consumo_kwh'].label = "Consumo kWh"
        self.fields['consumo_mc'].label = "Consumo mc"
        self.fields['periodo_fatturazione_da'].label = "Periodo Da"
        self.fields['periodo_fatturazione_a'].label = "Periodo A"
        self.fields['codice_pdr_pod'].label = "Codice PDR/POD"
        
        # Help text
        self.fields['consumo_kwh'].help_text = "Consumo in kWh per energia elettrica"
        self.fields['consumo_mc'].help_text = "Consumo in metri cubi per gas/acqua"
        self.fields['periodo_fatturazione_da'].help_text = "Inizio periodo fatturazione"
        self.fields['periodo_fatturazione_a'].help_text = "Fine periodo fatturazione"
        self.fields['codice_pdr_pod'].help_text = "Codice identificativo utenza (PDR per gas, POD per luce)"
        
        # Rendi i nuovi campi non obbligatori
        self.fields['consumo_kwh'].required = False
        self.fields['consumo_mc'].required = False
        self.fields['periodo_fatturazione_da'].required = False
        self.fields['periodo_fatturazione_a'].required = False
        self.fields['codice_pdr_pod'].required = False
        
        # Valori predefiniti per utenze
        if not self.instance.pk:
            self.fields['stato'].initial = 'fatturato'
            self.fields['causale'].initial = 'energia_elettrica'
            self.fields['iva_percentuale'].initial = 22
        
        # Modifica alcuni label per adattarli alle utenze
        self.fields['titolo'].label = "Descrizione Bolletta *"
        self.fields['titolo'].widget.attrs['placeholder'] = "Es: Bolletta Enel Gennaio 2025"
        self.fields['data_scadenza_servizio'].label = "Prossima Lettura"
        self.fields['data_scadenza_servizio'].help_text = "Data della prossima lettura o scadenza contratto"
        self.fields['fattura'].help_text = "Carica il PDF della bolletta"
        
        # Nascondi campi non rilevanti per le utenze
        self.fields['data_inizio_lavori'].widget = forms.HiddenInput()
        self.fields['data_inizio_lavori'].required = False
        self.fields['data_fine_lavori'].widget = forms.HiddenInput()
        self.fields['data_fine_lavori'].required = False
    
    def clean_periodo_fatturazione_a(self):
        """Validazione periodo fatturazione"""
        periodo_da = self.cleaned_data.get('periodo_fatturazione_da')
        periodo_a = self.cleaned_data.get('periodo_fatturazione_a')
        
        if periodo_da and periodo_a and periodo_da > periodo_a:
            raise ValidationError("Il periodo di fine non può essere precedente all'inizio")
        
        return periodo_a
    
    def clean_causale(self):
        """Assicura che sia selezionata una causale di tipo utenza"""
        causale = self.cleaned_data.get('causale')
        utenze_valide = ['energia_elettrica', 'gas_naturale', 'acqua', 'telefonia', 'rifiuti']
        
        if causale and causale not in utenze_valide:
            raise ValidationError("Seleziona un tipo di utenza valido")
        
        return causale
    
    def save(self, commit=True):
        """Override save per gestire i campi specifici delle utenze"""
        instance = super().save(commit=False)
        
        # Assicurati che data_richiesta sia impostata
        if not instance.data_richiesta:
            instance.data_richiesta = instance.data_fattura or timezone.now().date()
        
        # Se non ci sono date lavori, impostale uguali alla data fattura
        if not instance.data_inizio_lavori and instance.data_fattura:
            instance.data_inizio_lavori = instance.data_fattura
        if not instance.data_fine_lavori and instance.data_fattura:
            instance.data_fine_lavori = instance.data_fattura
        
        if commit:
            instance.save()
        return instance