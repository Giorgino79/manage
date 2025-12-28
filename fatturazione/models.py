"""
FATTURAZIONE MODELS - Sistema gestione fatturazione passiva
========================================================

Modelli per gestire l'intero workflow della fatturazione passiva:
- FatturaFornitore: Fattura principale con stati workflow
- DettaglioFattura: Righe di dettaglio fattura
- ScadenzaPagamento: Gestione scadenze pagamento
- ComunicazioneFatturato: Sistema comunicazione con fornitori

Adattato da AMM/fatturazione per progetto Management:
- Eliminato: mag3, prodotti, cassa
- Sostituito: acq2 → acquisti Management
- Mantenuto: workflow completo e automazioni
"""

from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.utils import timezone
from django.urls import reverse
from decimal import Decimal
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FatturaFornitore(models.Model):
    """
    Fattura fornitore - Modello principale per fatturazione passiva
    Workflow completo: ATTESA → RICEVUTA → CONTROLLATA → CONTABILIZZATA → PROGRAMMATA → PAGATA
    """
    
    # STATI WORKFLOW
    STATI_FATTURA = [
        ('ATTESA', 'In Attesa'),           # Fattura attesa dal fornitore
        ('RICEVUTA', 'Ricevuta'),          # Fattura ricevuta (documento caricato)
        ('CONTROLLATA', 'Controllata'),    # Fattura controllata e verificata
        ('CONTABILIZZATA', 'Contabilizzata'), # Registrata in contabilità
        ('PROGRAMMATA', 'Programmata'),    # Pagamento programmato
        ('PAGATA', 'Pagata'),             # Pagamento effettuato
        ('STORNATA', 'Stornata'),         # Fattura stornata/annullata
    ]
    
    PRIORITA_PAGAMENTO = [
        ('NORMALE', 'Normale'),
        ('ALTA', 'Alta'),
        ('URGENTE', 'Urgente'),
        ('CRITICA', 'Critica'),
    ]
    
    # IDENTIFICAZIONE
    numero_fattura = models.CharField(
        max_length=100,
        help_text="Numero fattura del fornitore"
    )
    numero_protocollo = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        help_text="Numero protocollo interno (generato automaticamente)"
    )
    data_fattura = models.DateField(
        help_text="Data fattura del fornitore"
    )
    data_ricezione = models.DateTimeField(
        auto_now_add=True,
        help_text="Data ricezione in sistema"
    )
    
    # RELAZIONI
    fornitore = models.ForeignKey(
        'anagrafica.Fornitore',
        on_delete=models.PROTECT,
        help_text="Fornitore della fattura"
    )
    # Ordine di acquisto singolo (mantenuto per compatibilità)
    ordine_acquisto = models.ForeignKey(
        'acquisti.OrdineAcquisto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Ordine di acquisto principale di riferimento"
    )
    
    # Ordini di acquisto multipli
    ordini_acquisto = models.ManyToManyField(
        'acquisti.OrdineAcquisto',
        blank=True,
        related_name='fatture_collegate',
        help_text="Ordini di acquisto collegati a questa fattura"
    )
    
    # WORKFLOW E STATI
    stato = models.CharField(
        max_length=20,
        choices=STATI_FATTURA,
        default='ATTESA',
        help_text="Stato attuale della fattura"
    )
    priorita_pagamento = models.CharField(
        max_length=20,
        choices=PRIORITA_PAGAMENTO,
        default='NORMALE',
        help_text="Priorità di pagamento"
    )
    
    # IMPORTI
    importo_netto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Importo netto fattura"
    )
    importo_iva = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Importo IVA"
    )
    importo_totale = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Importo totale fattura"
    )
    valuta = models.CharField(
        max_length=3,
        default='EUR',
        help_text="Valuta fattura"
    )
    
    # CONTROLLI E VERIFICHE
    differenza_importo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Differenza rispetto all'ordine di acquisto"
    )
    note_controllo = models.TextField(
        blank=True,
        help_text="Note del controllo fattura"
    )
    controllata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fatture_controllate',
        help_text="Utente che ha controllato la fattura"
    )
    data_controllo = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data controllo fattura"
    )
    
    # PAGAMENTO
    data_scadenza = models.DateField(
        help_text="Data scadenza pagamento"
    )
    termini_pagamento = models.CharField(
        max_length=200,
        help_text="Termini di pagamento (es: 30gg DFFM)"
    )
    data_pagamento = models.DateField(
        null=True,
        blank=True,
        help_text="Data effettiva pagamento"
    )
    importo_pagato = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Importo effettivamente pagato"
    )
    modalita_pagamento = models.CharField(
        max_length=100,
        blank=True,
        help_text="Modalità di pagamento utilizzata"
    )
    
    # DOCUMENTI E FILES
    file_fattura = models.FileField(
        upload_to='fatturazione/fatture/%Y/%m/',
        null=True,
        blank=True,
        help_text="File fattura (PDF, immagine, etc.)"
    )
    
    # ALLEGATI (collegamento con sistema allegati universale)
    allegati = GenericRelation('core.Allegato', related_query_name='fattura_fornitore')
    
    # NOTE E DESCRIZIONI
    oggetto = models.CharField(
        max_length=500,
        blank=True,
        help_text="Oggetto/descrizione fattura"
    )
    note_interne = models.TextField(
        blank=True,
        help_text="Note interne non visibili al fornitore"
    )
    
    # AUDIT TRAIL
    creata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='fatture_create',
        help_text="Utente che ha creato la fattura"
    )
    modificata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fatture_modificate',
        help_text="Ultimo utente che ha modificato"
    )
    
    # TIMESTAMP
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # DATE WORKFLOW
    data_ricezione_documento = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data ricezione documento fisico"
    )
    data_contabilizzazione = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data registrazione in contabilità"
    )
    data_programmazione = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data programmazione pagamento"
    )
    
    class Meta:
        verbose_name = "Fattura Fornitore"
        verbose_name_plural = "Fatture Fornitori"
        ordering = ['-data_fattura', '-created_at']
        indexes = [
            models.Index(fields=['numero_protocollo']),
            models.Index(fields=['fornitore', 'stato']),
            models.Index(fields=['stato']),
            models.Index(fields=['data_scadenza']),
            models.Index(fields=['data_fattura']),
        ]
        
        # Vincolo unico per evitare duplicati
        unique_together = ['fornitore', 'numero_fattura', 'data_fattura']
    
    def __str__(self):
        return f"{self.numero_protocollo or self.numero_fattura} - {self.fornitore.nome} - €{self.importo_totale}"
    
    def save(self, *args, **kwargs):
        """Override save per generazione automatica numero protocollo"""
        if not self.numero_protocollo:
            self.numero_protocollo = self.genera_numero_protocollo()
        
        # Calcola importo totale se non presente
        if not self.importo_totale and self.importo_netto is not None:
            self.importo_totale = self.importo_netto + (self.importo_iva or 0)
        
        super().save(*args, **kwargs)
    
    def genera_numero_protocollo(self):
        """Genera numero protocollo automatico: FATF-YYYY-NNNN"""
        year = timezone.now().year
        ultimo_numero = FatturaFornitore.objects.filter(
            numero_protocollo__startswith=f'FATF-{year}-'
        ).count()
        return f'FATF-{year}-{ultimo_numero + 1:04d}'
    
    def get_absolute_url(self):
        """URL per visualizzazione fattura"""
        return reverse('fatturazione:dettaglio', kwargs={'pk': self.pk})
    
    # METODI DI STATO E CONTROLLO
    def può_essere_controllata(self):
        """Verifica se può essere controllata"""
        return self.stato == 'RICEVUTA'
    
    def può_essere_contabilizzata(self):
        """Verifica se può essere contabilizzata"""
        return self.stato == 'CONTROLLATA'
    
    def può_essere_programmata(self):
        """Verifica se può essere programmata per il pagamento"""
        return self.stato == 'CONTABILIZZATA'
    
    def può_essere_pagata(self):
        """Verifica se può essere pagata"""
        return self.stato == 'PROGRAMMATA'
    
    def può_essere_modificata(self):
        """Verifica se può essere modificata"""
        return self.stato in ['ATTESA', 'RICEVUTA']
    
    def può_essere_stornata(self):
        """Verifica se può essere stornata"""
        return self.stato not in ['PAGATA', 'STORNATA']
    
    # METODI DI CALCOLO
    def calcola_differenza_ordine(self):
        """Calcola differenza rispetto all'ordine/ordini di acquisto"""
        if self.ordini_acquisto.exists():
            # Calcola la somma di tutti gli ordini collegati
            importo_ordini = sum(ordine.importo_totale for ordine in self.ordini_acquisto.all())
            self.differenza_importo = self.importo_totale - importo_ordini
        elif self.ordine_acquisto:
            # Fallback al singolo ordine per compatibilità
            self.differenza_importo = self.importo_totale - self.ordine_acquisto.importo_totale
        else:
            self.differenza_importo = 0
        return self.differenza_importo
    
    def get_ordini_collegati(self):
        """Restituisce tutti gli ordini di acquisto collegati (multipli + singolo)"""
        ordini = list(self.ordini_acquisto.all())
        if self.ordine_acquisto and self.ordine_acquisto not in ordini:
            ordini.append(self.ordine_acquisto)
        return ordini
    
    def get_importo_totale_ordini(self):
        """Calcola importo totale di tutti gli ordini collegati"""
        ordini = self.get_ordini_collegati()
        return sum(ordine.importo_totale for ordine in ordini) if ordini else Decimal('0')
    
    def calcola_scadenza_automatica(self):
        """Calcola scadenza automatica dai termini di pagamento"""
        if 'DFFM' in self.termini_pagamento.upper():
            # Data fine mese + giorni
            giorni = self._estrai_giorni_da_termini()
            fine_mese = self.data_fattura.replace(day=28) + timedelta(days=4)
            fine_mese = fine_mese - timedelta(days=fine_mese.day)
            self.data_scadenza = fine_mese + timedelta(days=giorni)
        elif 'GG' in self.termini_pagamento.upper() or 'GIORNI' in self.termini_pagamento.upper():
            # Giorni dalla data fattura
            giorni = self._estrai_giorni_da_termini()
            self.data_scadenza = self.data_fattura + timedelta(days=giorni)
        
        return self.data_scadenza
    
    def _estrai_giorni_da_termini(self):
        """Estrae numero giorni dai termini di pagamento"""
        import re
        match = re.search(r'(\d+)', self.termini_pagamento)
        return int(match.group(1)) if match else 30
    
    def get_giorni_scadenza(self):
        """Calcola giorni alla/dalla scadenza (negativo se scaduta)"""
        if self.data_scadenza:
            diff = (self.data_scadenza - timezone.now().date()).days
            return diff
        return None
    
    def is_scaduta(self):
        """Verifica se la fattura è scaduta"""
        return self.get_giorni_scadenza() is not None and self.get_giorni_scadenza() < 0
    
    def is_in_scadenza(self, giorni=7):
        """Verifica se la fattura è in scadenza entro X giorni"""
        giorni_scadenza = self.get_giorni_scadenza()
        return giorni_scadenza is not None and 0 <= giorni_scadenza <= giorni
    
    def get_stato_css_class(self):
        """Classe CSS Bootstrap per badge dello stato"""
        css_classes = {
            'ATTESA': 'secondary',
            'RICEVUTA': 'info',
            'CONTROLLATA': 'primary',
            'CONTABILIZZATA': 'success',
            'PROGRAMMATA': 'warning',
            'PAGATA': 'success',
            'STORNATA': 'danger',
        }
        return css_classes.get(self.stato, 'secondary')
    
    def get_priorita_css_class(self):
        """Classe CSS Bootstrap per badge priorità"""
        css_classes = {
            'NORMALE': 'secondary',
            'ALTA': 'warning',
            'URGENTE': 'danger',
            'CRITICA': 'danger',
        }
        return css_classes.get(self.priorita_pagamento, 'secondary')
    
    # AZIONI WORKFLOW
    def segna_come_ricevuta(self, utente, file_fattura=None):
        """Segna fattura come ricevuta"""
        if self.può_essere_controllata():  # Era in ATTESA
            self.stato = 'RICEVUTA'
            self.data_ricezione_documento = timezone.now()
            if file_fattura:
                self.file_fattura = file_fattura
            self.modificata_da = utente
            self.save()
            logger.info(f"Fattura {self.numero_protocollo} segnata come ricevuta da {utente}")
    
    def segna_come_controllata(self, utente, note_controllo=''):
        """Segna fattura come controllata"""
        if self.può_essere_controllata():
            self.stato = 'CONTROLLATA'
            self.data_controllo = timezone.now()
            self.controllata_da = utente
            if note_controllo:
                self.note_controllo = note_controllo
            self.modificata_da = utente
            self.save()
            logger.info(f"Fattura {self.numero_protocollo} controllata da {utente}")
    
    def segna_come_contabilizzata(self, utente):
        """Segna fattura come contabilizzata"""
        if self.può_essere_contabilizzata():
            self.stato = 'CONTABILIZZATA'
            self.data_contabilizzazione = timezone.now()
            self.modificata_da = utente
            self.save()
            logger.info(f"Fattura {self.numero_protocollo} contabilizzata da {utente}")
    
    def segna_come_programmata(self, utente):
        """Segna fattura come programmata per pagamento"""
        if self.può_essere_programmata():
            self.stato = 'PROGRAMMATA'
            self.data_programmazione = timezone.now()
            self.modificata_da = utente
            self.save()
            logger.info(f"Fattura {self.numero_protocollo} programmata da {utente}")
    
    def segna_come_pagata(self, utente, data_pagamento=None, importo_pagato=None, modalita=''):
        """Segna fattura come pagata"""
        if self.può_essere_pagata():
            self.stato = 'PAGATA'
            self.data_pagamento = data_pagamento or timezone.now().date()
            self.importo_pagato = importo_pagato or self.importo_totale
            self.modalita_pagamento = modalita
            self.modificata_da = utente
            self.save()
            logger.info(f"Fattura {self.numero_protocollo} pagata da {utente}")
    
    def storna_fattura(self, utente, motivo=''):
        """Storna la fattura"""
        if self.può_essere_stornata():
            old_stato = self.stato
            self.stato = 'STORNATA'
            self.note_interne = f"{self.note_interne}\n\n[STORNO] {timezone.now()}: {motivo}".strip()
            self.modificata_da = utente
            self.save()
            logger.info(f"Fattura {self.numero_protocollo} stornata da {utente} (era {old_stato})")


class DettaglioFattura(models.Model):
    """
    Dettaglio righe della fattura fornitore
    """
    
    fattura = models.ForeignKey(
        FatturaFornitore,
        on_delete=models.CASCADE,
        related_name='dettagli',
        help_text="Fattura di appartenenza"
    )
    
    # DESCRIZIONE RIGA
    descrizione = models.CharField(
        max_length=500,
        help_text="Descrizione della riga fattura"
    )
    quantita = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Quantità fatturata"
    )
    unita_misura = models.CharField(
        max_length=20,
        blank=True,
        help_text="Unità di misura (pz, kg, etc.)"
    )
    
    # PREZZI E IMPORTI
    prezzo_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Prezzo unitario"
    )
    sconto_percentuale = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Sconto percentuale"
    )
    importo_riga = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Importo totale riga"
    )
    aliquota_iva = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=22.00,
        help_text="Aliquota IVA percentuale"
    )
    
    # CONTROLLI
    note_riga = models.TextField(
        blank=True,
        help_text="Note specifiche della riga"
    )
    
    # ORDINE VISUALIZZAZIONE
    ordine = models.IntegerField(
        default=0,
        help_text="Ordine di visualizzazione"
    )
    
    class Meta:
        verbose_name = "Dettaglio Fattura"
        verbose_name_plural = "Dettagli Fattura"
        ordering = ['ordine', 'id']
    
    def __str__(self):
        return f"{self.descrizione} - Qt: {self.quantita} - €{self.importo_riga}"
    
    def save(self, *args, **kwargs):
        """Calcolo automatico importo riga"""
        if self.quantita and self.prezzo_unitario:
            subtotale = self.quantita * self.prezzo_unitario
            if self.sconto_percentuale:
                subtotale = subtotale * (1 - self.sconto_percentuale / 100)
            self.importo_riga = subtotale
        super().save(*args, **kwargs)
    
    def get_importo_iva(self):
        """Calcola IVA della riga"""
        return self.importo_riga * (self.aliquota_iva / 100)
    
    def get_importo_totale_riga(self):
        """Calcola totale riga con IVA"""
        return self.importo_riga + self.get_importo_iva()


class ScadenzaPagamento(models.Model):
    """
    Gestione scadenze e pianificazione pagamenti
    """
    
    PRIORITA_CHOICES = [
        (1, 'Molto Bassa'),
        (2, 'Bassa'),
        (3, 'Normale'),
        (4, 'Alta'),
        (5, 'Molto Alta'),
    ]
    
    STATO_SCADENZA = [
        ('PIANIFICATA', 'Pianificata'),
        ('IN_PAGAMENTO', 'In Pagamento'),
        ('PAGATA', 'Pagata'),
        ('SCADUTA', 'Scaduta'),
        ('RIMANDATA', 'Rimandata'),
    ]
    
    fattura = models.ForeignKey(
        FatturaFornitore,
        on_delete=models.CASCADE,
        related_name='scadenze'
    )
    
    data_scadenza = models.DateField(
        help_text="Data scadenza pagamento"
    )
    importo_scadenza = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Importo della scadenza"
    )
    
    # PRIORITÀ E GESTIONE
    priorita = models.IntegerField(
        choices=PRIORITA_CHOICES,
        default=3,
        help_text="Priorità pagamento"
    )
    stato = models.CharField(
        max_length=20,
        choices=STATO_SCADENZA,
        default='PIANIFICATA'
    )
    
    # NOTE E PROMEMORIA
    note_pagamento = models.TextField(
        blank=True,
        help_text="Note sul pagamento"
    )
    promemoria_giorni = models.IntegerField(
        default=3,
        help_text="Giorni prima per promemoria"
    )
    
    # AUDIT
    creata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Scadenza Pagamento"
        verbose_name_plural = "Scadenze Pagamento"
        ordering = ['data_scadenza', '-priorita']
    
    def __str__(self):
        return f"{self.fattura.numero_protocollo} - {self.data_scadenza} - €{self.importo_scadenza}"
    
    def is_scaduta(self):
        """Verifica se è scaduta"""
        return self.data_scadenza < timezone.now().date()
    
    def giorni_alla_scadenza(self):
        """Giorni alla scadenza"""
        return (self.data_scadenza - timezone.now().date()).days
    
    def necessita_promemoria(self):
        """Verifica se necessita promemoria"""
        return self.giorni_alla_scadenza() <= self.promemoria_giorni


class ComunicazioneFatturato(models.Model):
    """
    Sistema di comunicazione con fornitori per fatturazione
    """
    
    TIPO_COMUNICAZIONE = [
        ('RICHIESTA', 'Richiesta Fattura'),
        ('SOLLECITO', 'Sollecito'),
        ('CHIARIMENTO', 'Richiesta Chiarimenti'),
        ('CONFERMA', 'Conferma Ricezione'),
        ('PAGAMENTO', 'Avviso Pagamento'),
    ]
    
    fattura = models.ForeignKey(
        FatturaFornitore,
        on_delete=models.CASCADE,
        related_name='comunicazioni'
    )
    
    tipo_comunicazione = models.CharField(
        max_length=20,
        choices=TIPO_COMUNICAZIONE
    )
    
    oggetto = models.CharField(
        max_length=200,
        help_text="Oggetto comunicazione"
    )
    messaggio = models.TextField(
        help_text="Contenuto messaggio"
    )
    
    # EMAIL
    email_inviata = models.BooleanField(default=False)
    data_invio = models.DateTimeField(
        null=True,
        blank=True
    )
    email_destinatario = models.EmailField(
        help_text="Email destinatario"
    )
    
    # RISPOSTA
    risposta_ricevuta = models.BooleanField(default=False)
    data_risposta = models.DateTimeField(
        null=True,
        blank=True
    )
    contenuto_risposta = models.TextField(
        blank=True,
        help_text="Contenuto risposta ricevuta"
    )
    
    # AUDIT
    creata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Comunicazione Fatturato"
        verbose_name_plural = "Comunicazioni Fatturato"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.tipo_comunicazione} - {self.fattura.numero_protocollo} - {self.oggetto}"
