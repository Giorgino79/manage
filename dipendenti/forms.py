from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import re

from .models import Dipendente


class LoginForm(forms.Form):
    """Form per il login degli utenti"""
    
    username = forms.CharField(
        label=_('Username o Email'),
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Inserisci username o email',
            'autofocus': True,
            'autocomplete': 'username'
        })
    )
    
    password = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Inserisci password',
            'autocomplete': 'current-password'
        })
    )
    
    remember_me = forms.BooleanField(
        label=_('Ricordami'),
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def clean(self):
        """Validazione custom del form di login"""
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        
        if username and password:
            # Prova autenticazione con username
            user = authenticate(username=username, password=password)
            
            # Se non funziona con username, prova con email
            if not user and '@' in username:
                try:
                    dipendente = Dipendente.objects.get(email=username)
                    user = authenticate(username=dipendente.username, password=password)
                except Dipendente.DoesNotExist:
                    pass
            
            if not user:
                raise ValidationError(
                    _('Username/email o password non corretti.'),
                    code='invalid_credentials'
                )
            
            if not user.is_active:
                raise ValidationError(
                    _('Questo account è stato disattivato.'),
                    code='account_disabled'
                )
        
        return cleaned_data


class DipendenteCreationForm(UserCreationForm):
    """Form per la creazione di un nuovo dipendente"""
    
    email = forms.EmailField(
        required=True,
        label=_('Email'),
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label=_('Nome'),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label=_('Cognome'),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    livello = forms.ChoiceField(
        choices=Dipendente.Autorizzazioni.choices,
        required=True,
        label=_('Livello autorizzazioni'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    telefono = forms.CharField(
        max_length=20,
        required=False,
        label=_('Telefono'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+39 123 456 7890'
        })
    )
    
    data_assunzione = forms.DateField(
        required=False,
        label=_('Data assunzione'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    class Meta:
        model = Dipendente
        fields = (
            'username', 'email', 'first_name', 'last_name', 
            'password1', 'password2', 'livello', 'telefono', 
            'data_assunzione'
        )
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Applica classe CSS a tutti i campi
        for field_name, field in self.fields.items():
            if field_name not in ['password1', 'password2']:
                field.widget.attrs['class'] = 'form-control'
        
        # Placeholder personalizzati
        self.fields['username'].widget.attrs['placeholder'] = 'Username unico'
        self.fields['password1'].widget.attrs['placeholder'] = 'Password sicura'
        self.fields['password2'].widget.attrs['placeholder'] = 'Conferma password'
        
        # Help text personalizzati
        self.fields['username'].help_text = 'Lettere, cifre e @/./+/-/_ solamente.'
        self.fields['email'].help_text = 'Indirizzo email valido per comunicazioni.'
    
    def clean_email(self):
        """Verifica che l'email non sia già in uso"""
        email = self.cleaned_data['email']
        if Dipendente.objects.filter(email=email).exists():
            raise ValidationError(_('Un dipendente con questa email esiste già.'))
        return email
    
    def clean_telefono(self):
        """Validazione del numero di telefono"""
        telefono = self.cleaned_data.get('telefono')
        if telefono:
            # Rimuovi spazi e caratteri non numerici (eccetto + all'inizio)
            telefono_clean = re.sub(r'[^\d+]', '', telefono)
            
            # Verifica formato base
            if not re.match(r'^\+?[\d\s\-\(\)]{8,15}$', telefono):
                raise ValidationError(_('Formato telefono non valido.'))
        
        return telefono


class DipendenteChangeForm(UserChangeForm):
    """Form per la modifica di un dipendente esistente"""
    
    email = forms.EmailField(
        required=True,
        label=_('Email'),
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label=_('Nome'),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label=_('Cognome'),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    indirizzo = forms.CharField(
        max_length=500,
        required=False,
        label=_('Indirizzo'),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    telefono = forms.CharField(
        max_length=20,
        required=False,
        label=_('Telefono'),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    telefono_emergenza = forms.CharField(
        max_length=20,
        required=False,
        label=_('Telefono emergenza'),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    data_nascita = forms.DateField(
        required=False,
        label=_('Data di nascita'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    data_assunzione = forms.DateField(
        required=False,
        label=_('Data assunzione'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    livello = forms.ChoiceField(
        choices=Dipendente.Autorizzazioni.choices,
        required=True,
        label=_('Livello autorizzazioni'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    stato = forms.ChoiceField(
        choices=Dipendente.StatoDipendente.choices,
        required=True,
        label=_('Stato'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    codice_fiscale = forms.CharField(
        max_length=16,
        required=False,
        label=_('Codice Fiscale'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'RSSMRA80A01H501U',
            'style': 'text-transform: uppercase;'
        })
    )
    
    carta_identita_numero = forms.CharField(
        max_length=50,
        required=False,
        label=_('Numero Carta Identità'),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    carta_identita_scadenza = forms.DateField(
        required=False,
        label=_('Scadenza Carta Identità'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    patente_numero = forms.CharField(
        max_length=50,
        required=False,
        label=_('Numero Patente'),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    patente_scadenza = forms.DateField(
        required=False,
        label=_('Scadenza Patente'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    patente_categorie = forms.CharField(
        max_length=20,
        required=False,
        label=_('Categorie Patente'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'B, C, D'
        })
    )
    
    posizione_inail = forms.CharField(
        max_length=50,
        required=False,
        label=_('Posizione INAIL'),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    posizione_inps = forms.CharField(
        max_length=50,
        required=False,
        label=_('Posizione INPS'),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    foto_profilo = forms.FileField(
        required=False,
        label=_('Foto Profilo'),
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    
    documento_carta_identita = forms.FileField(
        required=False,
        label=_('Documento Carta Identità'),
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.jpg,.jpeg,.png'
        })
    )
    
    documento_codice_fiscale = forms.FileField(
        required=False,
        label=_('Documento Codice Fiscale'),
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.jpg,.jpeg,.png'
        })
    )
    
    documento_patente = forms.FileField(
        required=False,
        label=_('Documento Patente'),
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.jpg,.jpeg,.png'
        })
    )
    
    note_interne = forms.CharField(
        required=False,
        label=_('Note Interne'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Note riservate al management...'
        })
    )
    
    class Meta:
        model = Dipendente
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'indirizzo', 'telefono', 'telefono_emergenza',
            'data_nascita', 'data_assunzione', 'livello', 'stato',
            'codice_fiscale', 'carta_identita_numero', 'carta_identita_scadenza',
            'patente_numero', 'patente_scadenza', 'patente_categorie',
            'posizione_inail', 'posizione_inps',
            'foto_profilo', 'documento_carta_identita', 
            'documento_codice_fiscale', 'documento_patente',
            'note_interne'
        )
        exclude = ['password']
    
    def __init__(self, *args, **kwargs):
        # Estrai user dal kwargs se presente (per permessi)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Rimuovi il campo password dal form
        if 'password' in self.fields:
            del self.fields['password']
        
        # Se l'utente modifica se stesso, rimuovi alcuni campi sensibili
        if self.user and self.instance and self.user == self.instance:
            sensitive_fields = ['livello', 'stato', 'note_interne']
            for field in sensitive_fields:
                if field in self.fields:
                    self.fields[field].widget.attrs['readonly'] = True
                    self.fields[field].help_text = 'Solo gli amministratori possono modificare questo campo'
    
    def clean_codice_fiscale(self):
        """Validazione del codice fiscale"""
        cf = self.cleaned_data.get('codice_fiscale')
        if cf:
            cf = cf.upper().strip()
            
            # Verifica formato base (16 caratteri alfanumerici)
            if not re.match(r'^[A-Z]{6}[\d]{2}[A-Z][\d]{2}[A-Z][\d]{3}[A-Z]$', cf):
                raise ValidationError(_('Formato codice fiscale non valido.'))
            
            # Verifica univocità (escludendo l'istanza corrente)
            queryset = Dipendente.objects.filter(codice_fiscale=cf)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise ValidationError(_('Un dipendente con questo codice fiscale esiste già.'))
        
        return cf
    
    def clean_email(self):
        """Verifica univocità email"""
        email = self.cleaned_data['email']
        
        queryset = Dipendente.objects.filter(email=email)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError(_('Un dipendente con questa email esiste già.'))
        
        return email
    
    def clean(self):
        """Validazioni cross-field"""
        cleaned_data = super().clean()
        
        # Verifica coerenza date documenti
        carta_scadenza = cleaned_data.get('carta_identita_scadenza')
        patente_scadenza = cleaned_data.get('patente_scadenza')
        data_nascita = cleaned_data.get('data_nascita')
        
        # La data di scadenza non può essere nel passato
        from datetime import date
        oggi = date.today()
        
        if carta_scadenza and carta_scadenza < oggi:
            self.add_error('carta_identita_scadenza', 'La carta di identità risulta scaduta.')
        
        if patente_scadenza and patente_scadenza < oggi:
            self.add_error('patente_scadenza', 'La patente risulta scaduta.')
        
        # Verifica età minima (16 anni)
        if data_nascita:
            eta = oggi.year - data_nascita.year - ((oggi.month, oggi.day) < (data_nascita.month, data_nascita.day))
            if eta < 16:
                self.add_error('data_nascita', 'L\'età minima è 16 anni.')
        
        return cleaned_data


class ChangePasswordForm(forms.Form):
    """Form per il cambio password"""
    
    old_password = forms.CharField(
        label=_('Password attuale'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'current-password'
        })
    )
    
    new_password1 = forms.CharField(
        label=_('Nuova password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password'
        }),
        help_text=_('La password deve contenere almeno 8 caratteri.')
    )
    
    new_password2 = forms.CharField(
        label=_('Conferma nuova password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password'
        })
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_old_password(self):
        """Verifica che la password attuale sia corretta"""
        old_password = self.cleaned_data["old_password"]
        if not self.user.check_password(old_password):
            raise ValidationError(_('La password attuale è errata.'))
        return old_password
    
    def clean_new_password2(self):
        """Verifica che le due password coincidano"""
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        
        if password1 and password2:
            if password1 != password2:
                raise ValidationError(_('Le due password non coincidono.'))
        
        return password2
    
    def clean_new_password1(self):
        """Validazioni sulla nuova password"""
        password = self.cleaned_data.get('new_password1')
        
        if password:
            # Lunghezza minima
            if len(password) < 8:
                raise ValidationError(_('La password deve contenere almeno 8 caratteri.'))
            
            # Non può essere uguale alla vecchia
            if self.user.check_password(password):
                raise ValidationError(_('La nuova password deve essere diversa da quella attuale.'))
        
        return password
    
    def save(self):
        """Salva la nuova password"""
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        self.user.save()
        return self.user