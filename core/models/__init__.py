"""
CORE MODELS - Import all models
===============================
"""

from .allegati import Allegato

# Definiamo direttamente i modelli qui per evitare import circolari
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import os
import uuid

User = settings.AUTH_USER_MODEL

def messaggio_allegato_path(instance, filename):
    """Funzione per generare il percorso di upload per gli allegati dei messaggi."""
    ext = filename.split('.')[-1] if '.' in filename else ''
    unique_filename = f"{instance.mittente.id}_{uuid.uuid4()}"
    if ext:
        unique_filename = f"{unique_filename}.{ext}"
    today = timezone.now()
    return os.path.join('messaggi', str(today.year), str(today.month), unique_filename)

class Messaggio(models.Model):
    """Modello per i messaggi tra utenti"""
    mittente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messaggi_inviati', verbose_name=_('Mittente'))
    destinatario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messaggi_ricevuti', verbose_name=_('Destinatario'))
    testo = models.TextField(_('Testo del messaggio'))
    data_invio = models.DateTimeField(_('Data invio'), auto_now_add=True)
    letto = models.BooleanField(_('Letto'), default=False)
    data_lettura = models.DateTimeField(_('Data lettura'), null=True, blank=True)
    allegato = models.FileField(_('Allegato'), upload_to=messaggio_allegato_path, null=True, blank=True)
    
    class Meta:
        verbose_name = _('Messaggio')
        verbose_name_plural = _('Messaggi')
        ordering = ['-data_invio']
        db_table = 'core_messaggio'
    
    def __str__(self):
        return f"Da {self.mittente} a {self.destinatario} - {self.data_invio}"
    
    def marca_come_letto(self):
        """Marca il messaggio come letto se non lo è già"""
        if not self.letto:
            self.letto = True
            self.data_lettura = timezone.now()
            self.save()
    
    @property
    def nome_allegato(self):
        """Restituisce il nome del file allegato"""
        if self.allegato:
            return os.path.basename(self.allegato.name)
        return None
    
    @property
    def is_image(self):
        """Verifica se l'allegato è un'immagine"""
        if not self.allegato:
            return False
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        file_name = self.allegato.name.lower()
        return any(file_name.endswith(ext) for ext in image_extensions)
    
    @property
    def is_document(self):
        """Verifica se l'allegato è un documento"""
        if not self.allegato:
            return False
        doc_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt']
        file_name = self.allegato.name.lower()
        return any(file_name.endswith(ext) for ext in doc_extensions)

class Promemoria(models.Model):
    """Modello per i promemoria"""
    class Priorita(models.TextChoices):
        BASSA = 'bassa', _('Bassa')
        MEDIA = 'media', _('Media')
        ALTA = 'alta', _('Alta')
    
    titolo = models.CharField(_('Titolo'), max_length=200)
    descrizione = models.TextField(_('Descrizione'), blank=True, null=True)
    data_creazione = models.DateTimeField(_('Data creazione'), auto_now_add=True)
    data_scadenza = models.DateField(_('Data scadenza'), blank=True, null=True)
    completato = models.BooleanField(_('Completato'), default=False)
    data_completamento = models.DateTimeField(_('Data completamento'), blank=True, null=True)
    priorita = models.CharField(_('Priorità'), max_length=10, choices=Priorita.choices, default=Priorita.MEDIA)
    
    creato_da = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promemoria_creati', verbose_name=_('Creato da'))
    assegnato_a = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promemoria_assegnati', verbose_name=_('Assegnato a'))
    
    class Meta:
        verbose_name = _('Promemoria')
        verbose_name_plural = _('Promemoria')
        ordering = ['completato', 'data_scadenza']
        db_table = 'core_promemoria'
    
    def __str__(self):
        return self.titolo
    
    @property
    def is_overdue(self):
        """Verifica se il promemoria è scaduto"""
        if self.data_scadenza and not self.completato:
            return self.data_scadenza < timezone.localdate()
        return False

__all__ = [
    'Allegato',
    'Messaggio',
    'Promemoria',
]