"""
Mail System Models for Management
=================================

Sistema mail integrato in Management con configurazioni SMTP esistenti.
Compatibile con le funzioni email già presenti in core.email_utils.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from django.core.validators import EmailValidator
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import uuid
import hashlib

User = get_user_model()


class EmailConfiguration(models.Model):
    """
    Configurazione email per utenti in Management.
    Integra con le configurazioni SMTP esistenti.
    """
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                               related_name='mail_config')
    
    # Configurazione SMTP (invio)
    display_name = models.CharField("Nome Visualizzato", max_length=200)
    email_address = models.EmailField("Indirizzo Email")
    smtp_server = models.CharField("Server SMTP", max_length=200,
                                  default="smtp.gmail.com")
    smtp_port = models.IntegerField("Porta SMTP", default=587)
    smtp_username = models.CharField("Username SMTP", max_length=200)
    smtp_password = models.CharField("Password SMTP", max_length=500,
                                    help_text="Verrà crittografata automaticamente")
    use_tls = models.BooleanField("Usa TLS", default=True)
    use_ssl = models.BooleanField("Usa SSL", default=False)

    # Configurazione IMAP (ricezione)
    imap_server = models.CharField("Server IMAP", max_length=200,
                                   default="imap.gmail.com", blank=True)
    imap_port = models.IntegerField("Porta IMAP", default=993)
    imap_username = models.CharField("Username IMAP", max_length=200, blank=True,
                                    help_text="Lascia vuoto per usare smtp_username")
    imap_password = models.CharField("Password IMAP", max_length=500, blank=True,
                                    help_text="Lascia vuoto per usare smtp_password")
    imap_use_tls = models.BooleanField("IMAP usa TLS", default=False)
    imap_use_ssl = models.BooleanField("IMAP usa SSL", default=True)
    imap_enabled = models.BooleanField("Abilita ricezione IMAP", default=False)
    last_imap_sync = models.DateTimeField("Ultima sincronizzazione IMAP", null=True, blank=True)
    last_imap_error = models.TextField("Ultimo errore IMAP", blank=True)

    # Stati
    is_active = models.BooleanField("Configurazione Attiva", default=True)
    is_verified = models.BooleanField("Email Verificata", default=False)
    last_test_at = models.DateTimeField("Ultimo Test", null=True, blank=True)
    last_error = models.TextField("Ultimo Errore", blank=True)
    
    # Limiti
    daily_limit = models.IntegerField("Limite Giornaliero", default=500)
    hourly_limit = models.IntegerField("Limite Orario", default=50)
    
    # Tracking
    created_at = models.DateTimeField("Creato il", auto_now_add=True)
    updated_at = models.DateTimeField("Aggiornato il", auto_now=True)
    
    class Meta:
        verbose_name = "Configurazione Email"
        verbose_name_plural = "Configurazioni Email"
    
    def __str__(self):
        return f"{self.email_address} - {self.user.username}"
    
    @property
    def is_configured(self):
        """Verifica se configurazione è completa"""
        return (self.smtp_server and self.smtp_username and 
                self.smtp_password and self.email_address)


class EmailTemplate(models.Model):
    """
    Template email per Management.
    Compatibile con i template esistenti in templates/email/.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identificazione
    name = models.CharField("Nome Template", max_length=200)
    slug = models.SlugField("Slug", max_length=100, unique=True)
    description = models.TextField("Descrizione", blank=True)
    
    # Categorizzazione per app Management
    category = models.CharField("Categoria", max_length=100, choices=[
        ('preventivi', 'Preventivi'),
        ('automezzi', 'Automezzi'), 
        ('stabilimenti', 'Stabilimenti'),
        ('acquisti', 'Acquisti'),
        ('fatturazione', 'Fatturazione'),
        ('anagrafica', 'Anagrafica'),
        ('sistema', 'Sistema'),
        ('generico', 'Generico'),
    ], default='generico')
    
    # Contenuto
    subject = models.CharField("Oggetto", max_length=255)
    content_html = models.TextField("Contenuto HTML")
    content_text = models.TextField("Contenuto Testuale", blank=True)
    
    # Variabili disponibili
    available_variables = models.JSONField("Variabili Disponibili", default=dict)
    sample_data = models.JSONField("Dati Esempio", default=dict)
    
    # Stati
    is_active = models.BooleanField("Attivo", default=True)
    is_system = models.BooleanField("Template Sistema", default=False)
    
    # Tracking
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField("Creato il", auto_now_add=True)
    updated_at = models.DateTimeField("Aggiornato il", auto_now=True)
    usage_count = models.IntegerField("Utilizzi", default=0)
    
    class Meta:
        verbose_name = "Template Email"
        verbose_name_plural = "Template Email"
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.category})"
    
    def render(self, context=None):
        """Renderizza template con variabili"""
        if context is None:
            context = self.sample_data
            
        subject = self.subject
        html = self.content_html
        text = self.content_text
        
        # Sostituzioni variabili
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            subject = subject.replace(placeholder, str(value))
            html = html.replace(placeholder, str(value)) 
            text = text.replace(placeholder, str(value))
        
        return {
            'subject': subject,
            'html': html,
            'text': text
        }


class EmailFolder(models.Model):
    """
    Cartelle email per organizzazione messaggi
    """
    
    config = models.ForeignKey(EmailConfiguration, on_delete=models.CASCADE, related_name='folders')
    name = models.CharField("Nome Cartella", max_length=100)
    folder_type = models.CharField("Tipo", max_length=20, choices=[
        ('inbox', 'Posta in Arrivo'),
        ('sent', 'Posta Inviata'),
        ('drafts', 'Bozze'),
        ('trash', 'Cestino'),
        ('spam', 'Spam'),
        ('custom', 'Personalizzata'),
    ], default='custom')
    
    # Statistiche
    total_messages = models.IntegerField("Totale Messaggi", default=0)
    unread_messages = models.IntegerField("Messaggi Non Letti", default=0)
    
    # Metadata
    created_at = models.DateTimeField("Creato il", auto_now_add=True)
    updated_at = models.DateTimeField("Aggiornato il", auto_now=True)
    
    class Meta:
        verbose_name = "Cartella Email"
        verbose_name_plural = "Cartelle Email"
        unique_together = ['config', 'name']
        ordering = ['config', 'folder_type', 'name']
    
    def __str__(self):
        return f"{self.config.email_address} - {self.name}"


class EmailMessage(models.Model):
    """
    Log dei messaggi email inviati dal sistema Management.
    Traccia tutti gli invii per audit e debug.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Mittente
    sender_config = models.ForeignKey(EmailConfiguration, on_delete=models.CASCADE,
                                     related_name='sent_messages')
    folder = models.ForeignKey(EmailFolder, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Identificazione messaggio
    message_id = models.CharField("Message ID", max_length=255, blank=True)
    thread_id = models.CharField("Thread ID", max_length=255, blank=True)
    server_uid = models.CharField("UID Server", max_length=100, blank=True)
    
    # Destinatari
    to_addresses = models.JSONField("Destinatari")
    cc_addresses = models.JSONField("CC", default=list)
    bcc_addresses = models.JSONField("BCC", default=list)
    
    # Mittente dettagli
    from_address = models.EmailField("Da", blank=True)
    from_name = models.CharField("Nome Mittente", max_length=200, blank=True)
    reply_to = models.EmailField("Rispondi A", blank=True)
    
    # Contenuto
    subject = models.TextField("Oggetto")
    content_html = models.TextField("Contenuto HTML", blank=True)
    content_text = models.TextField("Contenuto Testuale", blank=True)
    template_used = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, 
                                     null=True, blank=True)
    
    # Allegati (se presenti)
    has_attachments = models.BooleanField("Ha Allegati", default=False)
    attachments_info = models.JSONField("Info Allegati", default=list)
    
    # Contenuto
    content_size = models.IntegerField("Dimensione (bytes)", default=0)
    
    # Stati e Date
    direction = models.CharField("Direzione", max_length=10, choices=[
        ('incoming', 'In Arrivo'),
        ('outgoing', 'In Uscita'),
    ], default='outgoing')
    
    status = models.CharField("Stato", max_length=20, choices=[
        ('draft', 'Bozza'),
        ('pending', 'In Attesa'),
        ('queued', 'In Coda'),
        ('sending', 'Invio'),
        ('sent', 'Inviato'),
        ('delivered', 'Consegnato'),
        ('failed', 'Fallito'),
        ('bounced', 'Rimbalzato'),
        ('received', 'Ricevuto'),
    ], default='pending')
    
    is_read = models.BooleanField("Letto", default=True)
    is_flagged = models.BooleanField("Contrassegnato", default=False)
    is_spam = models.BooleanField("Spam", default=False)

    # Etichette (many-to-many)
    labels = models.ManyToManyField(
        'EmailLabel',
        blank=True,
        related_name='messages',
        verbose_name="Etichette"
    )

    # Risultato invio
    smtp_response = models.TextField("Risposta SMTP", blank=True)
    error_message = models.TextField("Messaggio Errore", blank=True)
    delivery_attempts = models.IntegerField("Tentativi Consegna", default=0)
    
    # Relazione generica per collegamento con oggetti Management
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, 
                                    null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    related_description = models.CharField("Descrizione Collegamento", 
                                          max_length=500, blank=True)
    
    # Date
    sent_at = models.DateTimeField("Inviato il", null=True, blank=True)
    received_at = models.DateTimeField("Ricevuto il", null=True, blank=True)
    created_at = models.DateTimeField("Creato il", auto_now_add=True)
    updated_at = models.DateTimeField("Aggiornato il", auto_now=True)
    
    class Meta:
        verbose_name = "Messaggio Email"
        verbose_name_plural = "Messaggi Email"
        ordering = ['-sent_at', '-received_at', '-created_at']
        indexes = [
            models.Index(fields=['sender_config', 'folder']),
            models.Index(fields=['message_id']),
            models.Index(fields=['direction', 'status']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        if self.direction == 'incoming':
            return f"{self.subject[:50]} - da {self.from_address}"
        else:
            return f"{self.subject[:50]} - a {', '.join(self.to_addresses[:2])}"
    
    def mark_as_sent(self):
        """Segna messaggio come inviato"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save()
    
    def mark_as_failed(self, error_msg):
        """Segna messaggio come fallito"""
        self.status = 'failed'
        self.error_message = error_msg
        self.delivery_attempts += 1
        self.save()
    
    @property
    def content_hash(self):
        """Hash del contenuto per deduplicazione"""
        content = f"{self.subject}{self.content_text}{self.content_html}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def mark_as_read(self):
        """Segna messaggio come letto"""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])
    
    def toggle_flag(self):
        """Cambia stato contrassegno"""
        self.is_flagged = not self.is_flagged
        self.save(update_fields=['is_flagged'])


class EmailStats(models.Model):
    """
    Statistiche email per monitoraggio sistema.
    """
    
    config = models.ForeignKey(EmailConfiguration, on_delete=models.CASCADE,
                              related_name='stats')
    date = models.DateField("Data", default=timezone.now)
    
    # Contatori
    emails_sent = models.IntegerField("Email Inviate", default=0)
    emails_failed = models.IntegerField("Email Fallite", default=0)
    emails_bounced = models.IntegerField("Email Rimbalzate", default=0)
    
    # Dettagli per categoria
    preventivi_sent = models.IntegerField("Preventivi Inviati", default=0)
    automezzi_sent = models.IntegerField("Automezzi Inviati", default=0)
    acquisti_sent = models.IntegerField("Acquisti Inviati", default=0)
    
    # Metadata
    created_at = models.DateTimeField("Creato il", auto_now_add=True)
    updated_at = models.DateTimeField("Aggiornato il", auto_now=True)
    
    class Meta:
        verbose_name = "Statistiche Email"
        verbose_name_plural = "Statistiche Email"
        unique_together = ['config', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.config.email_address} - {self.date}"


class EmailAttachment(models.Model):
    """
    Allegati email con integrazione file system Management.
    """
    
    message = models.ForeignKey(EmailMessage, on_delete=models.CASCADE,
                               related_name='attachments')
    
    # File info
    filename = models.CharField("Nome File", max_length=255)
    content_type = models.CharField("Tipo MIME", max_length=100)
    size = models.IntegerField("Dimensione (bytes)", default=0)
    
    # Path del file (relativo a media root Management)
    file_path = models.FileField("File", upload_to='mail_attachments/%Y/%m/')
    file_hash = models.CharField("Hash File", max_length=64, blank=True)
    
    # Source (da dove viene il file)
    source_app = models.CharField("App Origine", max_length=100, blank=True)
    source_info = models.CharField("Info Origine", max_length=500, blank=True)
    
    # Metadata
    created_at = models.DateTimeField("Creato il", auto_now_add=True)
    
    class Meta:
        verbose_name = "Allegato Email"
        verbose_name_plural = "Allegati Email"
        ordering = ['filename']
    
    def __str__(self):
        return f"{self.filename} ({self.size} bytes)"
    
    def save(self, *args, **kwargs):
        """Calcola hash file"""
        if self.file_path and not self.file_hash:
            self.file_hash = self._generate_file_hash()
        super().save(*args, **kwargs)
    
    def _generate_file_hash(self):
        """Hash SHA256 del file"""
        hasher = hashlib.sha256()
        try:
            for chunk in self.file_path.chunks():
                hasher.update(chunk)
            return hasher.hexdigest()
        except:
            return ''


class EmailQueue(models.Model):
    """
    Coda per invii email asincroni
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    config = models.ForeignKey(EmailConfiguration, on_delete=models.CASCADE, related_name='queued_emails')
    
    # Destinazione
    to_addresses = models.JSONField("Destinatari")
    cc_addresses = models.JSONField("CC", default=list)
    bcc_addresses = models.JSONField("BCC", default=list)
    
    # Contenuto
    subject = models.TextField("Oggetto")
    content_html = models.TextField("Contenuto HTML", blank=True)
    content_text = models.TextField("Contenuto Testuale", blank=True)
    
    # Configurazioni
    priority = models.IntegerField("Priorità", default=5, choices=[
        (1, 'Molto Alta'),
        (2, 'Alta'),
        (3, 'Media-Alta'),
        (4, 'Media'),
        (5, 'Media-Bassa'),
        (6, 'Bassa'),
        (7, 'Molto Bassa'),
    ])
    
    # Scheduling
    scheduled_at = models.DateTimeField("Programmato per", default=timezone.now)
    max_attempts = models.IntegerField("Tentativi Massimi", default=3)
    attempt_count = models.IntegerField("Tentativi Effettuati", default=0)
    
    # Stati
    status = models.CharField("Stato", max_length=20, choices=[
        ('pending', 'In Attesa'),
        ('processing', 'Elaborazione'),
        ('sent', 'Inviato'),
        ('failed', 'Fallito'),
        ('cancelled', 'Annullato'),
    ], default='pending')
    
    error_message = models.TextField("Messaggio Errore", blank=True)
    sent_at = models.DateTimeField("Inviato il", null=True, blank=True)
    
    # Relazione generica per tracking origine
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    source_object = GenericForeignKey('content_type', 'object_id')
    
    # Tracking
    created_at = models.DateTimeField("Creato il", auto_now_add=True)
    updated_at = models.DateTimeField("Aggiornato il", auto_now=True)
    
    class Meta:
        verbose_name = "Email in Coda"
        verbose_name_plural = "Email in Coda"
        ordering = ['priority', 'scheduled_at', 'created_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['config', 'status']),
        ]
    
    def __str__(self):
        return f"{self.subject[:50]} - {self.status}"


class EmailLog(models.Model):
    """
    Log completo di tutte le operazioni email
    """
    
    config = models.ForeignKey(EmailConfiguration, on_delete=models.CASCADE, null=True, blank=True, related_name='logs')
    message = models.ForeignKey(EmailMessage, on_delete=models.CASCADE, null=True, blank=True, related_name='logs')
    
    # Evento
    event_type = models.CharField("Tipo Evento", max_length=50, choices=[
        ('send', 'Invio'),
        ('receive', 'Ricezione'),
        ('sync', 'Sincronizzazione'),
        ('error', 'Errore'),
        ('config', 'Configurazione'),
    ])
    
    event_description = models.TextField("Descrizione Evento")
    event_data = models.JSONField("Dati Evento", default=dict)
    
    # Risultato
    success = models.BooleanField("Successo", default=True)
    error_message = models.TextField("Messaggio Errore", blank=True)
    
    # Context
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField("IP Address", null=True, blank=True)
    user_agent = models.TextField("User Agent", blank=True)
    
    # Timestamp
    timestamp = models.DateTimeField("Timestamp", auto_now_add=True)
    
    class Meta:
        verbose_name = "Log Email"
        verbose_name_plural = "Log Email"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['config', 'event_type']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.timestamp.strftime('%d/%m/%Y %H:%M')}"


class EmailLabel(models.Model):
    """
    Etichette personalizzate per organizzare messaggi email (tipo Gmail)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relazione
    configuration = models.ForeignKey(
        EmailConfiguration,
        on_delete=models.CASCADE,
        related_name='labels',
        verbose_name="Configurazione"
    )

    # Identificazione
    name = models.CharField("Nome Etichetta", max_length=100)
    slug = models.SlugField("Slug", max_length=100)

    # Colore (hex code)
    color = models.CharField(
        "Colore",
        max_length=7,
        default="#4285f4",
        help_text="Codice colore hex (es. #4285f4)"
    )

    # Icona (opzionale, usa Feather Icons)
    icon = models.CharField("Icona", max_length=50, blank=True, default="tag")

    # Ordinamento
    order = models.IntegerField("Ordine", default=0)

    # Stati
    is_visible = models.BooleanField("Visibile", default=True)
    is_system = models.BooleanField(
        "Etichetta Sistema",
        default=False,
        help_text="Le etichette sistema non possono essere eliminate"
    )

    # Contatori
    message_count = models.IntegerField("Numero Messaggi", default=0)

    # Timestamp
    created_at = models.DateTimeField("Creato il", auto_now_add=True)
    updated_at = models.DateTimeField("Aggiornato il", auto_now=True)

    class Meta:
        verbose_name = "Etichetta Email"
        verbose_name_plural = "Etichette Email"
        ordering = ['order', 'name']
        unique_together = [['configuration', 'slug']]
        indexes = [
            models.Index(fields=['configuration', 'is_visible']),
        ]

    def __str__(self):
        return self.name

    def update_message_count(self):
        """Aggiorna contatore messaggi"""
        self.message_count = self.messages.count()
        self.save(update_fields=['message_count'])
