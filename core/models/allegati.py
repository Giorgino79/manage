"""
CORE ALLEGATI MODELS - Sistema Universale Allegati
=================================================

Modelli per il sistema allegati universale che permette di collegare
qualsiasi tipo di allegato (file, note, email, media) a qualsiasi
oggetto del sistema usando Django GenericForeignKey.

Caratteristiche:
- 📎 Collegamento universale a qualsiasi modello
- 🔒 Sistema permessi integrato
- 📊 Metadati completi e audit trail
- 🏷️ Sistema di categorizzazione flessibile
- 🔍 Ricerca e filtri avanzati

Versione: 1.0
"""

import os
import uuid
from typing import Dict, Any, List, Optional

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse

User = get_user_model()


# =============================================================================
# CHOICES AND CONSTANTS
# =============================================================================

TIPO_ALLEGATO_CHOICES = [
    # DOCUMENTI UFFICIALI
    ('doc_contratto', '📄 Contratto'),
    ('doc_fattura', '🧾 Fattura'), 
    ('doc_preventivo', '💰 Preventivo'),
    ('doc_ordine', '📋 Ordine'),
    ('doc_bolla', '📦 Bolla Consegna'),
    ('doc_certificato', '🏆 Certificato'),
    ('doc_libretto', '📓 Libretto'),
    ('doc_patente', '🪪 Patente'),
    ('doc_carta_identita', '🆔 Carta Identità'),
    ('doc_codice_fiscale', '📊 Codice Fiscale'),
    ('doc_visura', '📋 Visura'),
    ('doc_bilancio', '💼 Bilancio'),
    
    # COMUNICAZIONI
    ('email_inviata', '📧 Email Inviata'),
    ('email_ricevuta', '📨 Email Ricevuta'),
    ('sms_inviato', '💬 SMS Inviato'),
    ('chiamata', '☎️ Chiamata'),
    ('fax', '📠 Fax'),
    ('messaggio', '💭 Messaggio'),
    
    # MEDIA
    ('foto_documento', '📷 Foto Documento'),
    ('foto_generale', '🖼️ Fotografia'),
    ('video', '🎥 Video'),
    ('audio', '🎵 Audio'),
    ('screenshot', '🖥️ Screenshot'),
    
    # NOTE E PROMEMORIA
    ('nota_interna', '📝 Nota Interna'),
    ('nota_cliente', '💭 Nota Cliente'),
    ('promemoria', '⏰ Promemoria'),
    ('appunto', '✏️ Appunto'),
    ('verbale', '📄 Verbale'),
    
    # TECNICI E MANUTENZIONE
    ('scheda_tecnica', '⚙️ Scheda Tecnica'),
    ('manuale', '📖 Manuale'),
    ('report_tecnico', '🔧 Report Tecnico'),
    ('log_manutenzione', '🛠️ Log Manutenzione'),
    ('checklist', '✅ Checklist'),
    
    # COMMERCIALI
    ('listino', '💲 Listino Prezzi'),
    ('catalogo', '📚 Catalogo'),
    ('brochure', '📰 Brochure'),
    ('offerta', '🎯 Offerta'),
    
    # LEGALI E ASSICURATIVI
    ('polizza', '🛡️ Polizza'),
    ('denuncia', '⚠️ Denuncia'),
    ('sentenza', '⚖️ Sentenza'),
    ('decreto', '📜 Decreto'),
    
    # FINANZIARI
    ('ricevuta', '🧾 Ricevuta'),
    ('bonifico', '💳 Bonifico'),
    ('estratto_conto', '📊 Estratto Conto'),
    
    # ALTRO
    ('link_esterno', '🔗 Link Esterno'),
    ('backup', '💾 Backup'),
    ('altro', '📎 Altro'),
]

STATO_ALLEGATO_CHOICES = [
    ('attivo', 'Attivo'),
    ('archiviato', 'Archiviato'),
    ('scaduto', 'Scaduto'),
    ('eliminato', 'Eliminato'),
]

PRIORITA_CHOICES = [
    ('bassa', 'Bassa'),
    ('normale', 'Normale'),
    ('alta', 'Alta'),
    ('critica', 'Critica'),
]

# File extensions per categoria
ALLOWED_EXTENSIONS = {
    'documenti': ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt'],
    'immagini': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'],
    'video': ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm'],
    'audio': ['mp3', 'wav', 'ogg', 'flac', 'aac'],
    'archivi': ['zip', 'rar', '7z', 'tar', 'gz'],
}

# Dimensioni massime per categoria (in bytes)
MAX_FILE_SIZES = {
    'default': 10 * 1024 * 1024,     # 10MB
    'documenti': 20 * 1024 * 1024,   # 20MB
    'immagini': 5 * 1024 * 1024,     # 5MB
    'video': 100 * 1024 * 1024,      # 100MB
    'audio': 50 * 1024 * 1024,       # 50MB
    'archivi': 50 * 1024 * 1024,     # 50MB
}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def allegato_upload_path(instance, filename):
    """Genera path upload per allegati con struttura organizzata"""
    
    # Estrai info dall'oggetto collegato
    content_type = instance.content_type
    app_label = content_type.app_label
    model_name = content_type.model
    object_id = instance.object_id
    
    # Data corrente
    now = timezone.now()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    
    # Genera nome file sicuro
    name, ext = os.path.splitext(filename)
    safe_name = slugify(name)[:50]  # Limita lunghezza
    unique_id = uuid.uuid4().hex[:8]
    safe_filename = f"{safe_name}_{unique_id}{ext.lower()}"
    
    # Path finale: allegati/app/model/year/month/object_id/filename
    return f"allegati/{app_label}/{model_name}/{year}/{month}/{object_id}/{safe_filename}"


def get_file_category(filename):
    """Determina categoria file dall'estensione"""
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    
    for category, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return category
    
    return 'altro'


# =============================================================================
# MODELS
# =============================================================================

class AllegatoQuerySet(models.QuerySet):
    """Custom QuerySet per allegati con metodi di filtraggio"""
    
    def attivi(self):
        """Solo allegati attivi"""
        return self.filter(stato='attivo')
    
    def per_tipo(self, tipo_pattern):
        """Filtra per tipo allegato (supporta wildcard con *)"""
        if tipo_pattern.endswith('*'):
            return self.filter(tipo_allegato__startswith=tipo_pattern[:-1])
        return self.filter(tipo_allegato=tipo_pattern)
    
    def documenti(self):
        """Solo documenti"""
        return self.filter(tipo_allegato__startswith='doc_')
    
    def comunicazioni(self):
        """Solo comunicazioni"""
        return self.filter(tipo_allegato__in=[
            'email_inviata', 'email_ricevuta', 'sms_inviato', 
            'chiamata', 'fax', 'messaggio'
        ])
    
    def media(self):
        """Solo file media"""
        return self.filter(tipo_allegato__in=[
            'foto_documento', 'foto_generale', 'video', 'audio', 'screenshot'
        ])
    
    def note(self):
        """Solo note e appunti"""
        return self.filter(tipo_allegato__in=[
            'nota_interna', 'nota_cliente', 'promemoria', 'appunto', 'verbale'
        ])
    
    def con_file(self):
        """Solo allegati con file"""
        return self.exclude(file='')
    
    def senza_file(self):
        """Solo allegati senza file (note, link, etc.)"""
        return self.filter(file='')
    
    def scaduti(self):
        """Allegati scaduti"""
        oggi = timezone.now().date()
        return self.filter(data_scadenza__lt=oggi, stato='attivo')
    
    def in_scadenza(self, giorni=7):
        """Allegati in scadenza entro X giorni"""
        limite = timezone.now().date() + timezone.timedelta(days=giorni)
        return self.filter(
            data_scadenza__lte=limite,
            data_scadenza__gte=timezone.now().date(),
            stato='attivo'
        )
    
    def per_utente(self, user):
        """Allegati creati da un utente"""
        return self.filter(creato_da=user)
    
    def recenti(self, giorni=30):
        """Allegati degli ultimi X giorni"""
        limite = timezone.now() - timezone.timedelta(days=giorni)
        return self.filter(creato_il__gte=limite)


class AllegatoManager(models.Manager):
    """Manager per allegati con metodi di convenienza"""
    
    def get_queryset(self):
        return AllegatoQuerySet(self.model, using=self._db)
    
    def for_object(self, obj):
        """Ottieni allegati per un oggetto specifico"""
        content_type = ContentType.objects.get_for_model(obj.__class__)
        return self.get_queryset().filter(
            content_type=content_type,
            object_id=obj.pk
        )
    
    def attivi(self):
        return self.get_queryset().attivi()
    
    def per_tipo(self, tipo_pattern):
        return self.get_queryset().per_tipo(tipo_pattern)
    
    def documenti(self):
        return self.get_queryset().documenti()
    
    def comunicazioni(self):
        return self.get_queryset().comunicazioni()
    
    def media(self):
        return self.get_queryset().media()
    
    def note(self):
        return self.get_queryset().note()
    
    def scaduti(self):
        return self.get_queryset().scaduti()
    
    def in_scadenza(self, giorni=7):
        return self.get_queryset().in_scadenza(giorni)


class Allegato(models.Model):
    """
    Modello universale per allegati di qualsiasi oggetto del sistema.
    Usa GenericForeignKey per collegarsi a qualsiasi modello Django.
    """
    
    # *** COLLEGAMENTO UNIVERSALE ***
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE,
        verbose_name="Tipo Oggetto"
    )
    object_id = models.PositiveIntegerField(
        verbose_name="ID Oggetto"
    )
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # *** DATI PRINCIPALI ***
    titolo = models.CharField(
        max_length=255,
        verbose_name="Titolo",
        help_text="Titolo descrittivo dell'allegato"
    )
    descrizione = models.TextField(
        blank=True,
        verbose_name="Descrizione",
        help_text="Descrizione dettagliata del contenuto"
    )
    tipo_allegato = models.CharField(
        max_length=50,
        choices=TIPO_ALLEGATO_CHOICES,
        verbose_name="Tipo Allegato"
    )
    
    # *** CONTENUTO ***
    file = models.FileField(
        upload_to=allegato_upload_path,
        blank=True,
        null=True,
        verbose_name="File",
        help_text="File allegato (max 20MB)"
    )
    url_esterno = models.URLField(
        blank=True,
        verbose_name="URL Esterno",
        help_text="Link esterno al posto del file"
    )
    contenuto_testo = models.TextField(
        blank=True,
        verbose_name="Contenuto Testo",
        help_text="Contenuto testuale per note e appunti"
    )
    
    # *** METADATI ***
    tags = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Tags",
        help_text="Tag separati da virgola per ricerca"
    )
    stato = models.CharField(
        max_length=20,
        choices=STATO_ALLEGATO_CHOICES,
        default='attivo',
        verbose_name="Stato"
    )
    priorita = models.CharField(
        max_length=20,
        choices=PRIORITA_CHOICES,
        default='normale',
        verbose_name="Priorità"
    )
    
    # *** DATE E SCADENZE ***
    data_documento = models.DateField(
        blank=True,
        null=True,
        verbose_name="Data Documento",
        help_text="Data del documento originale"
    )
    data_scadenza = models.DateField(
        blank=True,
        null=True,
        verbose_name="Data Scadenza",
        help_text="Data di scadenza del documento"
    )
    
    # *** VISIBILITÀ E ACCESSO ***
    is_pubblico = models.BooleanField(
        default=True,
        verbose_name="Pubblico",
        help_text="Visibile a tutti gli utenti autorizzati"
    )
    is_confidenziale = models.BooleanField(
        default=False,
        verbose_name="Confidenziale",
        help_text="Visibile solo al creatore e admin"
    )
    
    # *** METADATI FILE ***
    dimensione_file = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Dimensione File (bytes)",
        editable=False
    )
    mime_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="MIME Type",
        editable=False
    )
    checksum = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Checksum SHA256",
        editable=False
    )
    
    # *** AUDIT TRAIL ***
    creato_da = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='allegati_creati',
        verbose_name="Creato da"
    )
    creato_il = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creato il"
    )
    modificato_da = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='allegati_modificati',
        verbose_name="Modificato da"
    )
    modificato_il = models.DateTimeField(
        auto_now=True,
        verbose_name="Modificato il"
    )
    
    # *** VERSIONING ***
    versione = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Versione"
    )
    allegato_padre = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versioni',
        verbose_name="Allegato Padre",
        help_text="Riferimento alla versione originale"
    )
    
    objects = AllegatoManager()
    
    class Meta:
        ordering = ['-creato_il']
        verbose_name = "Allegato"
        verbose_name_plural = "Allegati"
        
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['tipo_allegato']),
            models.Index(fields=['stato']),
            models.Index(fields=['creato_il']),
            models.Index(fields=['data_scadenza']),
            models.Index(fields=['tags']),
        ]
        
        permissions = [
            ('view_allegato_confidenziale', 'Può visualizzare allegati confidenziali'),
            ('manage_all_allegati', 'Può gestire tutti gli allegati'),
            ('download_allegati', 'Può scaricare allegati'),
        ]
    
    def __str__(self):
        return f"{self.titolo} ({self.get_tipo_allegato_display()})"
    
    def save(self, *args, **kwargs):
        """Override save per aggiornare metadati file"""
        
        # Calcola metadati file se presente
        if self.file:
            import hashlib
            import mimetypes
            
            # Dimensione
            if hasattr(self.file, 'size'):
                self.dimensione_file = self.file.size
            
            # MIME type
            mime_type, _ = mimetypes.guess_type(self.file.name)
            if mime_type:
                self.mime_type = mime_type
            
            # Checksum (solo per file non troppo grandi)
            if self.dimensione_file and self.dimensione_file < 50 * 1024 * 1024:  # 50MB
                try:
                    self.file.seek(0)
                    content = self.file.read()
                    self.checksum = hashlib.sha256(content).hexdigest()
                    self.file.seek(0)
                except:
                    pass
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        """URL per visualizzazione allegato"""
        return reverse('core:allegato_detail', kwargs={'pk': self.pk})
    
    def get_download_url(self):
        """URL per download allegato"""
        return reverse('core:allegato_download', kwargs={'pk': self.pk})
    
    def get_preview_url(self):
        """URL per preview allegato"""
        return reverse('core:allegato_preview', kwargs={'pk': self.pk})
    
    @property
    def nome_file(self):
        """Ottieni nome file senza path"""
        if self.file:
            return os.path.basename(self.file.name)
        return None
    
    @property
    def estensione_file(self):
        """Ottieni estensione file"""
        if self.file:
            return os.path.splitext(self.file.name)[1].lower()
        return None
    
    @property
    def categoria_file(self):
        """Ottieni categoria file"""
        if self.file:
            return get_file_category(self.file.name)
        return None
    
    @property
    def dimensione_leggibile(self):
        """Dimensione file in formato leggibile"""
        if not self.dimensione_file:
            return "N/A"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.dimensione_file < 1024.0:
                return f"{self.dimensione_file:.1f} {unit}"
            self.dimensione_file /= 1024.0
        return f"{self.dimensione_file:.1f} TB"
    
    @property
    def is_immagine(self):
        """Verifica se è un'immagine"""
        return self.categoria_file == 'immagini'
    
    @property
    def is_documento(self):
        """Verifica se è un documento"""
        return self.categoria_file == 'documenti'
    
    @property
    def is_video(self):
        """Verifica se è un video"""
        return self.categoria_file == 'video'
    
    @property
    def is_audio(self):
        """Verifica se è un audio"""
        return self.categoria_file == 'audio'
    
    @property
    def has_preview(self):
        """Verifica se può avere preview"""
        return self.is_immagine or self.mime_type == 'application/pdf'
    
    @property
    def is_scaduto(self):
        """Verifica se è scaduto"""
        if not self.data_scadenza:
            return False
        return self.data_scadenza < timezone.now().date()
    
    @property
    def giorni_scadenza(self):
        """Giorni alla scadenza (negativo se scaduto)"""
        if not self.data_scadenza:
            return None
        
        diff = self.data_scadenza - timezone.now().date()
        return diff.days
    
    @property
    def icona_tipo(self):
        """Icona FontAwesome per il tipo"""
        icone_map = {
            'doc_': 'fas fa-file-alt',
            'email_': 'fas fa-envelope', 
            'foto_': 'fas fa-image',
            'video': 'fas fa-video',
            'audio': 'fas fa-music',
            'nota_': 'fas fa-sticky-note',
            'link_esterno': 'fas fa-external-link-alt',
            'default': 'fas fa-paperclip'
        }
        
        for prefix, icona in icone_map.items():
            if self.tipo_allegato.startswith(prefix):
                return icona
        
        return icone_map['default']
    
    @property
    def colore_priorita(self):
        """Colore Bootstrap per priorità"""
        colori = {
            'bassa': 'secondary',
            'normale': 'primary', 
            'alta': 'warning',
            'critica': 'danger'
        }
        return colori.get(self.priorita, 'primary')
    
    @property
    def colore_stato(self):
        """Colore Bootstrap per stato"""
        colori = {
            'attivo': 'success',
            'archiviato': 'secondary',
            'scaduto': 'warning', 
            'eliminato': 'danger'
        }
        return colori.get(self.stato, 'primary')
    
    def get_versioni(self):
        """Ottieni tutte le versioni di questo allegato"""
        if self.allegato_padre:
            # Se questo è una versione, ottieni tutte le versioni del padre
            return self.allegato_padre.versioni.all()
        else:
            # Se questo è il padre, ottieni le sue versioni
            return self.versioni.all()
    
    def get_versione_successiva(self):
        """Ottieni numero per prossima versione"""
        versioni = self.get_versioni()
        if versioni.exists():
            return versioni.aggregate(max_v=models.Max('versione'))['max_v'] + 1
        return self.versione + 1
    
    def crea_nuova_versione(self, file=None, **kwargs):
        """Crea una nuova versione di questo allegato"""
        
        # Prepara dati per nuova versione
        nuova_versione_data = {
            'content_type': self.content_type,
            'object_id': self.object_id,
            'titolo': self.titolo,
            'descrizione': self.descrizione,
            'tipo_allegato': self.tipo_allegato,
            'tags': self.tags,
            'stato': 'attivo',
            'priorita': self.priorita,
            'data_documento': self.data_documento,
            'data_scadenza': self.data_scadenza,
            'is_pubblico': self.is_pubblico,
            'is_confidenziale': self.is_confidenziale,
            'versione': self.get_versione_successiva(),
            'allegato_padre': self.allegato_padre or self,
            **kwargs
        }
        
        if file:
            nuova_versione_data['file'] = file
        
        return Allegato.objects.create(**nuova_versione_data)
    
    def can_view(self, user):
        """Verifica se l'utente può visualizzare questo allegato"""
        if user.is_superuser:
            return True
        
        if self.is_confidenziale:
            return user == self.creato_da or user.has_perm('core.view_allegato_confidenziale')
        
        if not self.is_pubblico:
            return user == self.creato_da
        
        return True
    
    def can_edit(self, user):
        """Verifica se l'utente può modificare questo allegato"""
        if user.is_superuser:
            return True
        
        if user.has_perm('core.manage_all_allegati'):
            return True
        
        return user == self.creato_da
    
    def can_delete(self, user):
        """Verifica se l'utente può eliminare questo allegato"""
        return self.can_edit(user)
    
    def get_tag_list(self):
        """Ottieni lista dei tag"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []
    
    def set_tags(self, tag_list):
        """Imposta tag da lista"""
        self.tags = ', '.join(tag_list) if tag_list else ''


# =============================================================================
# SIGNALS
# =============================================================================

from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver


@receiver(pre_delete, sender=Allegato)
def allegato_pre_delete(sender, instance, **kwargs):
    """Operazioni prima dell'eliminazione"""
    
    # Log eliminazione
    if instance.creato_da:
        print(f"Eliminazione allegato {instance.pk} - {instance.titolo} da parte di sistema")


@receiver(post_delete, sender=Allegato) 
def allegato_post_delete(sender, instance, **kwargs):
    """Pulizia file dopo eliminazione"""
    
    # Elimina file dal filesystem se presente
    if instance.file and hasattr(instance.file, 'path'):
        try:
            if os.path.exists(instance.file.path):
                os.remove(instance.file.path)
        except Exception as e:
            # Log errore ma non bloccare eliminazione
            print(f"Errore eliminazione file {instance.file.path}: {e}")