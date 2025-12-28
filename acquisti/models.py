"""
ACQUISTI MODELS - Sistema gestione ordini di acquisto
===================================================

Modelli per gestire gli ordini di acquisto (ODA):
- OrdineAcquisto: Ordine principale con stati semplificati
- Integrazione con app preventivi
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericRelation
from decimal import Decimal
from core.mixins.procurement import ProcurementTargetMixin


class OrdineAcquisto(ProcurementTargetMixin, models.Model):
    """
    Ordine di Acquisto (ODA) - Modello principale
    Sistema semplificato per il progetto Management
    """
    
    # IDENTIFICAZIONE
    numero_ordine = models.CharField(
        max_length=50, 
        unique=True, 
        help_text="Numero ODA generato automaticamente (ODA-YYYY-NNN)"
    )
    data_ordine = models.DateTimeField(auto_now_add=True)
    data_consegna_richiesta = models.DateField(help_text="Data richiesta per la consegna")
    
    # RELAZIONI
    fornitore = models.ForeignKey(
        'anagrafica.Fornitore', 
        on_delete=models.PROTECT,
        help_text="Fornitore dell'ordine"
    )
    preventivo_originale = models.ForeignKey(
        'preventivi.Preventivo', 
        null=True, 
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Preventivo che ha generato questo ordine (se applicabile)"
    )
    
    # STATI ODA - SEMPLIFICATI
    STATI_CHOICES = [
        ('CREATO', 'Creato'),      # Ordine creato, da ricevere
        ('RICEVUTO', 'Ricevuto'),  # Merce ricevuta
        ('PAGATO', 'Pagato'),      # Pagamento effettuato
    ]
    stato = models.CharField(
        max_length=20, 
        choices=STATI_CHOICES, 
        default='CREATO',
        help_text="Stato attuale dell'ordine"
    )
    
    # DATI COMMERCIALI
    importo_totale = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="Importo totale dell'ordine"
    )
    valuta = models.CharField(max_length=3, default='EUR')
    termini_pagamento = models.CharField(
        max_length=200, 
        help_text="Condizioni di pagamento"
    )
    tempi_consegna = models.CharField(
        max_length=200, 
        help_text="Tempi di consegna previsti"
    )
    
    # GESTIONE WORKFLOW
    creato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT,
        related_name='ordini_creati',
        help_text="Utente che ha creato l'ordine"
    )
    
    # RICEVIMENTO
    data_ricevimento = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Data di ricevimento della merce"
    )
    ricevuto_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        null=True, 
        blank=True,
        related_name='ordini_ricevuti',
        on_delete=models.PROTECT,
        help_text="Utente che ha confermato il ricevimento"
    )
    
    # PAGAMENTO
    data_pagamento = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Data di pagamento"
    )
    pagato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        null=True, 
        blank=True,
        related_name='ordini_pagati',
        on_delete=models.PROTECT,
        help_text="Utente che ha confermato il pagamento"
    )
    
    # NOTE E RIFERIMENTI
    note_ordine = models.TextField(
        blank=True, 
        help_text="Note generali sull'ordine"
    )
    riferimento_esterno = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Riferimento del fornitore"
    )
    
    # ALLEGATI (collegamento con sistema allegati universale)
    allegati = GenericRelation('core.Allegato', related_query_name='ordine_acquisto')
    
    # TIMESTAMP
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Ordine di Acquisto"
        verbose_name_plural = "Ordini di Acquisto"
        ordering = ['-data_ordine']
        indexes = [
            models.Index(fields=['numero_ordine']),
            models.Index(fields=['stato']),
            models.Index(fields=['fornitore']),
            models.Index(fields=['data_ordine']),
        ]
    
    def __str__(self):
        return f"{self.numero_ordine} - {self.fornitore.nome} - €{self.importo_totale}"
    
    def save(self, *args, **kwargs):
        """Override save per numerazione automatica"""
        if not self.numero_ordine:
            self.numero_ordine = self.genera_numero_oda()
        super().save(*args, **kwargs)
    
    def genera_numero_oda(self):
        """Genera numero ODA automatico: ODA-YYYY-NNN"""
        year = timezone.now().year
        last_number = OrdineAcquisto.objects.filter(
            numero_ordine__startswith=f'ODA-{year}-'
        ).count()
        return f'ODA-{year}-{last_number + 1:03d}'
    
    # METODI DI STATO
    def può_essere_ricevuto(self):
        """Verifica se l'ordine può essere segnato come ricevuto"""
        return self.stato == 'CREATO'
    
    def può_essere_pagato(self):
        """Verifica se l'ordine può essere segnato come pagato"""
        return self.stato == 'RICEVUTO'
    
    def segna_come_ricevuto(self, utente):
        """Segna l'ordine come ricevuto"""
        if self.può_essere_ricevuto():
            self.stato = 'RICEVUTO'
            self.data_ricevimento = timezone.now()
            self.ricevuto_da = utente
            self.save()
    
    def segna_come_pagato(self, utente):
        """Segna l'ordine come pagato"""
        if self.può_essere_pagato():
            self.stato = 'PAGATO'
            self.data_pagamento = timezone.now()
            self.pagato_da = utente
            self.save()
    
    def get_stato_css_class(self):
        """Classe CSS Bootstrap per badge dello stato"""
        css_classes = {
            'CREATO': 'warning',
            'RICEVUTO': 'info',
            'PAGATO': 'success',
        }
        return css_classes.get(self.stato, 'secondary')
    
    def get_giorni_dalla_creazione(self):
        """Calcola i giorni dalla creazione dell'ordine"""
        return (timezone.now() - self.data_ordine).days
    
    def get_giorni_dalla_ricevimento(self):
        """Calcola i giorni dal ricevimento (se ricevuto)"""
        if self.data_ricevimento:
            return (timezone.now() - self.data_ricevimento).days
        return None
    
    @property
    def titolo_display(self):
        """Titolo per visualizzazione in dashboard e ricerca"""
        if self.preventivo_originale:
            return self.preventivo_originale.richiesta.titolo
        return self.note_ordine or f"Ordine {self.numero_ordine}"
    
    # METODI PER ALLEGATI
    def get_allegati_attivi(self):
        """Ritorna gli allegati attivi per questo ordine"""
        return self.allegati.filter(stato='attivo')
    
    def get_allegati_documenti(self):
        """Ritorna solo i documenti allegati"""
        return self.allegati.filter(
            stato='attivo',
            tipo_allegato__startswith='doc_'
        )
    
    def get_allegati_note(self):
        """Ritorna solo le note allegate"""
        return self.allegati.filter(
            stato='attivo',
            tipo_allegato__in=['nota_interna', 'nota_cliente', 'appunto']
        )
    
    def has_allegati(self):
        """Verifica se l'ordine ha allegati"""
        return self.allegati.filter(stato='attivo').exists()
    
    def aggiungi_nota(self, titolo, contenuto, tipo_nota='nota_interna', utente=None):
        """Aggiunge una nota rapida all'ordine"""
        from core.models.allegati import Allegato
        
        return Allegato.objects.create(
            content_object=self,
            titolo=titolo,
            contenuto_testo=contenuto,
            tipo_allegato=tipo_nota,
            creato_da=utente,
            stato='attivo'
        )
    
    def aggiungi_documento(self, titolo, file, tipo_doc='doc_ordine', utente=None, descrizione=''):
        """Aggiunge un documento all'ordine"""
        from core.models.allegati import Allegato
        
        return Allegato.objects.create(
            content_object=self,
            titolo=titolo,
            file=file,
            descrizione=descrizione,
            tipo_allegato=tipo_doc,
            creato_da=utente,
            stato='attivo'
        )
