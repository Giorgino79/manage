from django.db import models
from django.contrib.auth.models import AbstractUser, Group
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from datetime import datetime, timedelta, date


class Dipendente(AbstractUser):
    """
    Modello Dipendente per Management System - Versione Cornice
    
    Caratteristiche:
    - Estende AbstractUser per autenticazione integrata
    - Sistema di livelli autorizzazioni modulare
    - Gestione documenti con FileField
    - Supporto audit trail e timestamp
    """
    
    class Autorizzazioni(models.TextChoices):
        AMMINISTRATORE = 'amministratore', _('Amministratore')
        CONTABILE = 'contabile', _('Contabile') 
        OPERATIVO = 'operativo', _('Operativo')
        MAGAZZINIERE = 'magazziniere', _('Magazziniere')
        RAPPRESENTANTE = 'rappresentante', _('Rappresentante')
        AUTISTA = 'autista', _('Autista')
        SUPERVISORE = 'supervisore', _('Supervisore')
    
    class StatoDipendente(models.TextChoices):
        ATTIVO = 'attivo', _('Attivo')
        SOSPESO = 'sospeso', _('Sospeso')
        DIMESSO = 'dimesso', _('Dimesso')
        IN_PROVA = 'prova', _('In Prova')
    
    # === INFORMAZIONI BASE ===
    livello = models.CharField(
        max_length=30, 
        choices=Autorizzazioni.choices, 
        default=Autorizzazioni.OPERATIVO, 
        verbose_name=_('Livello autorizzazioni'),
        help_text=_('Determina i permessi di accesso al sistema')
    )
    
    stato = models.CharField(
        max_length=20,
        choices=StatoDipendente.choices,
        default=StatoDipendente.ATTIVO,
        verbose_name=_('Stato dipendente'),
        help_text=_('Stato lavorativo attuale')
    )
    
    # === INFORMAZIONI PERSONALI ===
    indirizzo = models.CharField(
        max_length=500, 
        blank=True, 
        null=True, 
        verbose_name=_('Indirizzo completo')
    )
    telefono = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        verbose_name=_('Telefono'),
        help_text=_('Numero di telefono principale')
    )
    telefono_emergenza = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        verbose_name=_('Telefono emergenza'),
        help_text=_('Contatto di emergenza')
    )
    data_nascita = models.DateField(
        blank=True, 
        null=True, 
        verbose_name=_('Data di nascita')
    )
    data_assunzione = models.DateField(
        blank=True, 
        null=True, 
        verbose_name=_('Data di assunzione')
    )
    
    # === DOCUMENTI IDENTITÀ ===
    codice_fiscale = models.CharField(
        verbose_name=_('Codice Fiscale'), 
        max_length=16, 
        blank=True, 
        null=True,
        unique=True,
        help_text=_('Codice fiscale italiano (16 caratteri)')
    )
    carta_identita_numero = models.CharField(
        verbose_name=_("Numero carta di identità"), 
        max_length=50, 
        blank=True, 
        null=True
    )
    carta_identita_scadenza = models.DateField(
        verbose_name=_("Scadenza carta identità"), 
        blank=True, 
        null=True
    )
    patente_numero = models.CharField(
        verbose_name=_("Numero patente di guida"), 
        max_length=50, 
        blank=True, 
        null=True
    )
    patente_scadenza = models.DateField(
        verbose_name=_("Scadenza patente"), 
        blank=True, 
        null=True
    )
    patente_categorie = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        verbose_name=_('Categorie patente'),
        help_text=_('Es: B, C, D, etc.')
    )
    
    # === POSIZIONI CONTRIBUTIVE ===
    posizione_inail = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name=_('Codice INAIL')
    )
    posizione_inps = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name=_('Codice INPS')
    )
    
    # === DOCUMENTI E ALLEGATI ===
    foto_profilo = models.FileField(
        upload_to='dipendenti/foto/', 
        blank=True, 
        null=True, 
        verbose_name=_('Foto profilo'),
        help_text=_('Immagine del dipendente (consigliato: 300x300px)')
    )
    documento_carta_identita = models.FileField(
        upload_to='dipendenti/documenti/ci/', 
        blank=True, 
        null=True, 
        verbose_name=_('Documento carta identità'),
        help_text=_('Scansione fronte/retro carta di identità')
    )
    documento_codice_fiscale = models.FileField(
        upload_to='dipendenti/documenti/cf/', 
        blank=True, 
        null=True, 
        verbose_name=_('Documento codice fiscale'),
        help_text=_('Tessera sanitaria o certificato di attribuzione CF')
    )
    documento_patente = models.FileField(
        upload_to='dipendenti/documenti/patenti/', 
        blank=True, 
        null=True, 
        verbose_name=_('Documento patente'),
        help_text=_('Scansione fronte/retro patente di guida')
    )
    
    # === AUDIT E TIMESTAMP ===
    ultimo_accesso = models.DateTimeField(
        blank=True, 
        null=True, 
        verbose_name=_('Ultimo accesso'),
        help_text=_('Ultimo login al sistema')
    )
    creato_il = models.DateTimeField(
        default=timezone.now, 
        verbose_name=_('Data creazione')
    )
    modificato_il = models.DateTimeField(
        auto_now=True, 
        verbose_name=_('Ultima modifica')
    )
    creato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dipendenti_creati',
        verbose_name=_('Creato da')
    )
    
    # === NOTE E OSSERVAZIONI ===
    note_interne = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Note interne'),
        help_text=_('Informazioni riservate al management')
    )
    
    class Meta:
        verbose_name = _('Dipendente')
        verbose_name_plural = _('Dipendenti')
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['livello']),
            models.Index(fields=['stato']),
            models.Index(fields=['data_assunzione']),
            models.Index(fields=['ultimo_accesso']),
        ]
    
    def __str__(self):
        if self.first_name and self.last_name:
            return f"{self.last_name} {self.first_name} ({self.get_livello_display()})"
        return f"{self.username} ({self.get_livello_display()})"
    
    def get_absolute_url(self):
        return reverse('dipendenti:dettaglio', kwargs={'pk': self.pk})
    
    @property
    def nome_completo(self):
        """Restituisce nome e cognome del dipendente"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    @property
    def is_amministratore(self):
        """Verifica se il dipendente è amministratore"""
        return self.livello == self.Autorizzazioni.AMMINISTRATORE
    
    @property
    def is_contabile(self):
        """Verifica se il dipendente ha accesso alla contabilità"""
        return self.livello in [self.Autorizzazioni.AMMINISTRATORE, self.Autorizzazioni.CONTABILE]
    
    @property
    def is_operativo(self):
        """Verifica se il dipendente è personale operativo"""
        return self.livello in [
            self.Autorizzazioni.OPERATIVO,
            self.Autorizzazioni.MAGAZZINIERE,
            self.Autorizzazioni.AUTISTA
        ]
    
    @property
    def eta(self):
        """Calcola l'età del dipendente"""
        if self.data_nascita:
            today = date.today()
            return today.year - self.data_nascita.year - (
                (today.month, today.day) < (self.data_nascita.month, self.data_nascita.day)
            )
        return None
    
    @property
    def anni_servizio(self):
        """Calcola gli anni di servizio"""
        if self.data_assunzione:
            today = date.today()
            return today.year - self.data_assunzione.year - (
                (today.month, today.day) < (self.data_assunzione.month, self.data_assunzione.day)
            )
        return None
    
    @property
    def documenti_in_scadenza(self):
        """Restituisce documenti in scadenza entro 30 giorni"""
        documenti_scadenza = []
        oggi = date.today()
        limite_scadenza = oggi + timedelta(days=30)
        
        if self.carta_identita_scadenza and self.carta_identita_scadenza <= limite_scadenza:
            documenti_scadenza.append({
                'tipo': 'Carta Identità',
                'scadenza': self.carta_identita_scadenza,
                'scaduto': self.carta_identita_scadenza < oggi
            })
        
        if self.patente_scadenza and self.patente_scadenza <= limite_scadenza:
            documenti_scadenza.append({
                'tipo': 'Patente',
                'scadenza': self.patente_scadenza,
                'scaduto': self.patente_scadenza < oggi
            })
        
        return documenti_scadenza
    
    def aggiorna_ultimo_accesso(self):
        """Aggiorna timestamp ultimo accesso"""
        self.ultimo_accesso = timezone.now()
        self.save(update_fields=['ultimo_accesso'])
    
    def ha_permesso(self, permesso_richiesto):
        """
        Verifica se il dipendente ha un determinato permesso
        
        Args:
            permesso_richiesto (str): Livello di permesso richiesto
            
        Returns:
            bool: True se ha il permesso, False altrimenti
        """
        # Gerarchia permessi (dal più alto al più basso)
        gerarchia = {
            self.Autorizzazioni.AMMINISTRATORE: 6,
            self.Autorizzazioni.SUPERVISORE: 5,
            self.Autorizzazioni.CONTABILE: 4,
            self.Autorizzazioni.RAPPRESENTANTE: 3,
            self.Autorizzazioni.MAGAZZINIERE: 2,
            self.Autorizzazioni.AUTISTA: 1,
            self.Autorizzazioni.OPERATIVO: 0,
        }
        
        livello_utente = gerarchia.get(self.livello, 0)
        livello_richiesto = gerarchia.get(permesso_richiesto, 0)
        
        return livello_utente >= livello_richiesto
    
    def save(self, *args, **kwargs):
        """Override save per gestire logica custom"""
        # Normalizza codice fiscale in maiuscolo
        if self.codice_fiscale:
            self.codice_fiscale = self.codice_fiscale.upper().strip()
        
        # Normalizza categorie patente
        if self.patente_categorie:
            self.patente_categorie = self.patente_categorie.upper().strip()
        
        # Assegna automaticamente i gruppi Django in base al livello
        super().save(*args, **kwargs)
        
        # Gestione gruppi Django per permessi
        self._assegna_gruppi()
    
    def _assegna_gruppi(self):
        """Assegna automaticamente i gruppi Django in base al livello autorizzazioni"""
        # Rimuovi tutti i gruppi attuali
        self.groups.clear()
        
        # Assegna gruppi in base al livello
        try:
            if self.livello == self.Autorizzazioni.AMMINISTRATORE:
                gruppo, _ = Group.objects.get_or_create(name='Amministratori')
                self.groups.add(gruppo)
                
            elif self.livello == self.Autorizzazioni.CONTABILE:
                gruppo, _ = Group.objects.get_or_create(name='Contabili')
                self.groups.add(gruppo)
                
            elif self.livello == self.Autorizzazioni.SUPERVISORE:
                gruppo, _ = Group.objects.get_or_create(name='Supervisori')
                self.groups.add(gruppo)
                
            elif self.livello == self.Autorizzazioni.RAPPRESENTANTE:
                gruppo, _ = Group.objects.get_or_create(name='Rappresentanti')
                self.groups.add(gruppo)
                
            elif self.livello == self.Autorizzazioni.MAGAZZINIERE:
                gruppo, _ = Group.objects.get_or_create(name='Magazzinieri')
                self.groups.add(gruppo)
                
            elif self.livello == self.Autorizzazioni.AUTISTA:
                gruppo, _ = Group.objects.get_or_create(name='Autisti')
                self.groups.add(gruppo)
                
            else:  # OPERATIVO
                gruppo, _ = Group.objects.get_or_create(name='Operativi')
                self.groups.add(gruppo)
                
        except Exception as e:
            # Log error but don't break save process
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Errore assegnazione gruppi per {self.username}: {e}")


# === AUDIT LOG ===
class AuditLogDipendente(models.Model):
    """Log delle modifiche ai dipendenti per audit trail"""
    
    class TipoAzione(models.TextChoices):
        CREAZIONE = 'creazione', _('Creazione')
        MODIFICA = 'modifica', _('Modifica')
        ELIMINAZIONE = 'eliminazione', _('Eliminazione')
        LOGIN = 'login', _('Login')
        LOGOUT = 'logout', _('Logout')
        CAMBIO_LIVELLO = 'cambio_livello', _('Cambio Livello')
    
    dipendente = models.ForeignKey(
        Dipendente,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        verbose_name=_('Dipendente')
    )
    azione = models.CharField(
        max_length=20,
        choices=TipoAzione.choices,
        verbose_name=_('Tipo azione')
    )
    dettagli = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Dettagli modifiche'),
        help_text=_('Dati delle modifiche in formato JSON')
    )
    eseguita_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs_eseguiti',
        verbose_name=_('Eseguita da')
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Data/Ora')
    )
    indirizzo_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('Indirizzo IP')
    )
    
    class Meta:
        verbose_name = _('Log Audit Dipendente')
        verbose_name_plural = _('Logs Audit Dipendenti')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['dipendente', '-timestamp']),
            models.Index(fields=['azione']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.dipendente} - {self.get_azione_display()} ({self.timestamp.strftime('%d/%m/%Y %H:%M')})"


class Presenza(models.Model):
    """
    Modello per registrare le timbrature (entrate/uscite) dei dipendenti
    """

    class TipoTimbratura(models.TextChoices):
        ENTRATA = 'entrata', _('Entrata')
        USCITA = 'uscita', _('Uscita')

    dipendente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='presenze',
        verbose_name=_('Dipendente')
    )

    data = models.DateField(
        default=date.today,
        verbose_name=_('Data'),
        db_index=True
    )

    tipo = models.CharField(
        max_length=10,
        choices=TipoTimbratura.choices,
        verbose_name=_('Tipo timbratura')
    )

    orario = models.TimeField(
        auto_now_add=True,
        verbose_name=_('Orario')
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Timestamp completo')
    )

    note = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Note')
    )

    # Geolocalizzazione opzionale
    latitudine = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name=_('Latitudine')
    )

    longitudine = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name=_('Longitudine')
    )

    indirizzo_ip = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name=_('Indirizzo IP')
    )

    class Meta:
        verbose_name = _('Presenza')
        verbose_name_plural = _('Presenze')
        ordering = ['-data', '-orario']
        indexes = [
            models.Index(fields=['dipendente', '-data']),
            models.Index(fields=['-data']),
            models.Index(fields=['tipo']),
        ]
        unique_together = [['dipendente', 'data', 'tipo', 'timestamp']]

    def __str__(self):
        return f"{self.dipendente.nome_completo} - {self.get_tipo_display()} {self.data} {self.orario.strftime('%H:%M')}"

    @property
    def ore_lavorate_oggi(self):
        """Calcola le ore lavorate nella giornata"""
        if self.tipo == self.TipoTimbratura.USCITA:
            entrata = Presenza.objects.filter(
                dipendente=self.dipendente,
                data=self.data,
                tipo=self.TipoTimbratura.ENTRATA,
                timestamp__lt=self.timestamp
            ).order_by('-timestamp').first()

            if entrata:
                diff = datetime.combine(date.today(), self.orario) - datetime.combine(date.today(), entrata.orario)
                return diff.total_seconds() / 3600  # Ritorna ore come float
        return None


class GiornataLavorativa(models.Model):
    """
    Modello per tracciare le giornate lavorative concluse.
    Quando l'operatore conclude la giornata, vengono salvate ore totali e straordinari.
    """
    dipendente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='giornate_lavorative',
        verbose_name=_('Dipendente')
    )
    data = models.DateField(
        default=date.today,
        db_index=True,
        verbose_name=_('Data')
    )
    ore_lavorate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name=_('Ore Lavorate'),
        help_text=_('Ore totali lavorate nella giornata')
    )
    ore_straordinari = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name=_('Ore Straordinari'),
        help_text=_('Ore oltre le 8 ore standard')
    )
    ore_standard = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=8.0,
        verbose_name=_('Ore Standard'),
        help_text=_('Ore standard per questa giornata')
    )
    conclusa = models.BooleanField(
        default=True,
        verbose_name=_('Giornata Conclusa')
    )
    timestamp_conclusione = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Data/Ora Conclusione')
    )
    note_conclusione = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Note Conclusione'),
        help_text=_('Note sulla giornata lavorativa')
    )

    class Meta:
        verbose_name = _('Giornata Lavorativa')
        verbose_name_plural = _('Giornate Lavorative')
        ordering = ['-data']
        unique_together = ['dipendente', 'data']
        indexes = [
            models.Index(fields=['dipendente', 'data']),
            models.Index(fields=['data']),
        ]

    def __str__(self):
        return f"{self.dipendente.username} - {self.data.strftime('%d/%m/%Y')} - {self.ore_lavorate}h"

    @property
    def ha_straordinari(self):
        """Indica se ci sono straordinari"""
        return self.ore_straordinari > 0

    @property
    def percentuale_straordinari(self):
        """Calcola percentuale straordinari sul totale"""
        if self.ore_lavorate > 0:
            return (self.ore_straordinari / self.ore_lavorate) * 100
        return 0