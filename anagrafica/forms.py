"""
ANAGRAFICA FORMS - Forms per gestione clienti e fornitori
========================================================

Forms per la gestione anagrafica (senza rappresentanti):
- ClienteForm: Form per clienti con validazioni complete
- FornitoreForm: Form per fornitori con validazioni fiscali

NOTA: Tutti i forms relativi ai rappresentanti sono stati rimossi
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import Cliente, Fornitore
import re


class ClienteForm(forms.ModelForm):
    """Form per la gestione dei clienti"""
    
    class Meta:
        model = Cliente
        fields = [
            'nome', 'zona', 'indirizzo', 'citta', 'cap',
            'telefono', 'email', 'partita_iva', 'codice_fiscale',
            'codice_univoco', 'pec', 'tipo_pagamento', 'limite_credito',
            'orario_consegna', 'giorno_chiusura', 'attivo', 'note'
        ]
        widgets = {
            'indirizzo': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'note': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'limite_credito': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'class': 'form-control'}),
            'orario_consegna': forms.TextInput(attrs={'placeholder': 'es: 9-13 16-19:30', 'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'zona': forms.TextInput(attrs={'class': 'form-control'}),
            'citta': forms.TextInput(attrs={'class': 'form-control'}),
            'cap': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '5', 'pattern': '[0-9]{5}'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'partita_iva': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'IT12345678901'}),
            'codice_fiscale': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'RSSMRA85M01H501Z'}),
            'codice_univoco': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'XXXXXXX'}),
            'pec': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'esempio@pec.it'}),
            'tipo_pagamento': forms.Select(attrs={'class': 'form-select'}),
            'giorno_chiusura': forms.Select(attrs={'class': 'form-select'}),
            'attivo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Labels personalizzate
        self.fields['nome'].label = 'Nome/Ragione Sociale *'
        self.fields['telefono'].label = 'Telefono *'
        self.fields['email'].label = 'Email *'
        self.fields['partita_iva'].label = 'Partita IVA'
        self.fields['codice_fiscale'].label = 'Codice Fiscale'
        self.fields['codice_univoco'].label = 'Codice Univoco'
        self.fields['tipo_pagamento'].label = 'Tipo di Pagamento'
        self.fields['limite_credito'].label = 'Limite di Credito (€)'
        
        # Help text
        self.fields['partita_iva'].help_text = 'Formato: IT + 11 cifre'
        self.fields['codice_fiscale'].help_text = '16 caratteri per persone fisiche, 11 per aziende'
        self.fields['codice_univoco'].help_text = 'Per fatturazione elettronica'
        self.fields['limite_credito'].help_text = 'Limite massimo di credito concedibile (€)'
    
    def clean(self):
        cleaned_data = super().clean()
        piva = cleaned_data.get('partita_iva')
        cf = cleaned_data.get('codice_fiscale')
        
        # Almeno uno tra P.IVA e CF deve essere fornito
        if not piva and not cf:
            raise ValidationError({
                'partita_iva': 'Specificare almeno Partita IVA o Codice Fiscale',
                'codice_fiscale': 'Specificare almeno Partita IVA o Codice Fiscale'
            })
        
        return cleaned_data
    
    def clean_partita_iva(self):
        piva = self.cleaned_data.get('partita_iva', '')
        if piva:
            piva = piva.replace(' ', '').upper()
            if not self._validate_partita_iva(piva):
                raise ValidationError('Partita IVA non valida. Formato: IT + 11 cifre')
        return piva
    
    def clean_codice_fiscale(self):
        cf = self.cleaned_data.get('codice_fiscale', '')
        if cf:
            cf = cf.replace(' ', '').upper()
            if not self._validate_codice_fiscale(cf):
                raise ValidationError('Codice Fiscale non valido')
        return cf
    
    def clean_limite_credito(self):
        limite = self.cleaned_data.get('limite_credito')
        if limite is not None and limite < 0:
            raise ValidationError('Il limite di credito non può essere negativo')
        return limite
    
    def _validate_partita_iva(self, piva):
        """Validazione Partita IVA italiana con checksum"""
        if not piva.startswith('IT'):
            return False
        numbers = piva[2:]
        if len(numbers) != 11 or not numbers.isdigit():
            return False
        
        # Calcolo checksum
        odd_chars = [int(numbers[i]) for i in range(0, 10, 2)]
        even_chars = [int(numbers[i]) for i in range(1, 10, 2)]
        
        total = sum(odd_chars)
        for char in even_chars:
            doubled = char * 2
            total += doubled // 10 + doubled % 10
        
        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(numbers[10])
    
    def _validate_codice_fiscale(self, cf):
        """Validazione Codice Fiscale"""
        pattern_persona = r'^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$'
        pattern_azienda = r'^\d{11}$'
        return bool(re.match(pattern_persona, cf) or re.match(pattern_azienda, cf))


class FornitoreForm(forms.ModelForm):
    """Form per la gestione dei fornitori"""
    
    class Meta:
        model = Fornitore
        fields = [
            'nome', 'indirizzo', 'citta', 'cap', 'telefono', 'email',
            'partita_iva', 'codice_fiscale', 'iban', 'categoria',
            'tipo_pagamento', 'priorita_pagamento_default', 'pec', 'codice_destinatario',
            'referente_nome', 'referente_telefono', 'referente_email', 
            'attivo', 'note'
        ]
        widgets = {
            'indirizzo': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'note': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'citta': forms.TextInput(attrs={'class': 'form-control'}),
            'cap': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '5', 'pattern': '[0-9]{5}'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'partita_iva': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'IT12345678901 o 12345678901'}),
            'codice_fiscale': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'RSSMRA85M01H501Z'}),
            'iban': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'IT60X0542811101000000123456'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'tipo_pagamento': forms.Select(attrs={'class': 'form-select'}),
            'priorita_pagamento_default': forms.Select(attrs={'class': 'form-select'}),
            'pec': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'fornitore@pec.it'}),
            'codice_destinatario': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '7'}),
            'referente_nome': forms.TextInput(attrs={'class': 'form-control'}),
            'referente_telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'referente_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'attivo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Labels personalizzate
        self.fields['nome'].label = 'Nome/Ragione Sociale *'
        self.fields['telefono'].label = 'Telefono *'
        self.fields['email'].label = 'Email *'
        self.fields['partita_iva'].label = 'Partita IVA *'
        self.fields['codice_fiscale'].label = 'Codice Fiscale'
        self.fields['categoria'].label = 'Categoria Merceologica'
        self.fields['tipo_pagamento'].label = 'Tipo di Pagamento'
        self.fields['priorita_pagamento_default'].label = 'Priorità Pagamento Default'
        self.fields['referente_nome'].label = 'Nome Referente'
        self.fields['referente_telefono'].label = 'Telefono Referente'
        self.fields['referente_email'].label = 'Email Referente'
        
        # Help text
        self.fields['partita_iva'].help_text = 'Partita IVA (accetta qualsiasi formato valido)'
        self.fields['iban'].help_text = 'IBAN per bonifici (IT + 25 caratteri)'
        self.fields['codice_destinatario'].help_text = 'Codice SDI a 7 caratteri per fatturazione elettronica'
    
    def clean_partita_iva(self):
        piva = self.cleaned_data.get('partita_iva', '')
        if not piva:
            raise ValidationError('Partita IVA è obbligatoria')
        
        piva = piva.replace(' ', '').replace('-', '').upper()
        
        # Validazione flessibile per partite IVA di vari paesi
        if len(piva) < 8:
            raise ValidationError('Partita IVA troppo breve (minimo 8 caratteri)')
        
        if len(piva) > 15:
            raise ValidationError('Partita IVA troppo lunga (massimo 15 caratteri)')
        
        # Accetta vari formati: IT12345678901, 12345678901, GB123456789, etc.
        return piva
    
    def clean_codice_fiscale(self):
        cf = self.cleaned_data.get('codice_fiscale', '')
        if cf:
            cf = cf.replace(' ', '').upper()
            # Validazione flessibile per codice fiscale
            if len(cf) < 8 or len(cf) > 16:
                raise ValidationError('Codice Fiscale non valido (8-16 caratteri)')
        return cf
    
    def clean_iban(self):
        iban = self.cleaned_data.get('iban', '')
        if iban:
            iban = iban.replace(' ', '').upper()
            if not self._validate_iban(iban):
                raise ValidationError('IBAN non valido. Formato: IT + 25 caratteri')
        return iban
    
    def _validate_partita_iva(self, piva):
        """Validazione Partita IVA italiana"""
        if not piva.startswith('IT'):
            return False
        numbers = piva[2:]
        if len(numbers) != 11 or not numbers.isdigit():
            return False
        
        # Calcolo checksum
        odd_chars = [int(numbers[i]) for i in range(0, 10, 2)]
        even_chars = [int(numbers[i]) for i in range(1, 10, 2)]
        
        total = sum(odd_chars)
        for char in even_chars:
            doubled = char * 2
            total += doubled // 10 + doubled % 10
        
        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(numbers[10])
    
    def _validate_codice_fiscale(self, cf):
        """Validazione Codice Fiscale"""
        pattern_persona = r'^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$'
        pattern_azienda = r'^\d{11}$'
        return bool(re.match(pattern_persona, cf) or re.match(pattern_azienda, cf))
    
    def _validate_iban(self, iban):
        """Validazione IBAN italiana semplificata"""
        if not iban.startswith('IT'):
            return False
        if len(iban) != 27:  # IBAN italiano: IT + 25 caratteri
            return False
        # Verifica formato base
        code_part = iban[2:]
        if not re.match(r'^\d{2}[A-Z]\d{5}\d{10}[A-Z0-9]{12}$', code_part):
            return False
        return True


class AnagraficaSearchForm(forms.Form):
    """Form di ricerca nell'anagrafica"""
    
    TIPO_CHOICES = [
        ('', 'Tutti'),
        ('clienti', 'Clienti'),
        ('fornitori', 'Fornitori'),
    ]
    
    query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Cerca per nome, email, telefono...',
            'class': 'form-control'
        }),
        label='Cerca'
    )
    
    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Tipo'
    )
    
    attivo = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Solo attivi'
    )