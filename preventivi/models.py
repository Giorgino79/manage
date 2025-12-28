"""
PREVENTIVI MODELS - Sistema gestione preventivi e gare
======================================================

Modelli per gestire l'intero workflow dei preventivi:
- RichiestaPreventivo: Richiesta principale
- FornitorePreventivo: Relazione many-to-many con tracking
- Preventivo: Risposte ricevute dai fornitori  
- ParametroValutazione: Criteri di valutazione dinamici
- ValutazionePreventivo: Punteggi assegnati
"""

from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
import uuid
from core.mixins.procurement import ProcurementTargetMixin


class RichiestaPreventivo(ProcurementTargetMixin, models.Model):
    """
    Richiesta principale di preventivo con workflow completo
    """
    
    STATO_CHOICES = [
        ('CREATO', 'Creato'),
        ('INVIATO_FORNITORI', 'Inviato ai fornitori'),
        ('PREVENTIVI_RACCOLTI', 'Preventivi raccolti'),
        ('IN_VALUTAZIONE', 'In valutazione'),
        ('APPROVATO', 'Approvato'),
        ('ANNULLATO', 'Annullato'),
    ]
    
    PRIORITA_CHOICES = [
        ('BASSA', 'Bassa'),
        ('NORMALE', 'Normale'),
        ('ALTA', 'Alta'),
        ('URGENTE', 'Urgente'),
    ]
    
    # Identificazione
    numero = models.CharField(max_length=50, unique=True, help_text="Numero univoco preventivo")
    titolo = models.CharField(max_length=200, help_text="Titolo/oggetto della richiesta")
    descrizione = models.TextField(help_text="Descrizione dettagliata del preventivo richiesto")
    
    # Workflow
    stato = models.CharField(max_length=25, choices=STATO_CHOICES, default='CREATO')
    priorita = models.CharField(max_length=20, choices=PRIORITA_CHOICES, default='NORMALE')
    
    # Attori del processo
    richiedente = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='preventivi_richiesti',
        help_text="Buyer che ha richiesto il preventivo"
    )
    operatore = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='preventivi_gestiti',
        help_text="Operatore che gestisce i preventivi ricevuti"
    )
    approvatore = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='preventivi_approvati',
        help_text="Chi deve approvare il preventivo finale"
    )
    
    # Fornitori coinvolti (through model per tracking)
    fornitori = models.ManyToManyField(
        'anagrafica.Fornitore', 
        through='FornitorePreventivo',
        related_name='preventivi'
    )
    
    # Preventivo vincente
    preventivo_approvato = models.ForeignKey(
        'Preventivo', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='richieste_vinte',
        help_text="Preventivo scelto dopo approvazione"
    )
    
    # Tempistiche
    data_richiesta = models.DateTimeField(auto_now_add=True)
    data_scadenza = models.DateField(help_text="Scadenza per ricevere i preventivi")
    data_invio_fornitori = models.DateTimeField(null=True, blank=True, help_text="Quando inviata ai fornitori")
    data_raccolta_completata = models.DateTimeField(null=True, blank=True, help_text="Quando tutti i preventivi sono stati caricati")
    data_valutazione = models.DateTimeField(null=True, blank=True, help_text="Quando iniziata la valutazione")
    data_approvazione = models.DateTimeField(null=True, blank=True)
    
    # Informazioni aggiuntive
    budget_massimo = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Budget massimo disponibile"
    )
    valuta = models.CharField(max_length=3, default='EUR')
    note_interne = models.TextField(blank=True, help_text="Note interne non visibili ai fornitori")
    
    # Allegati (collegati tramite core.allegati)
    allegati = GenericRelation('core.Allegato')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Richiesta Preventivo"
        verbose_name_plural = "Richieste Preventivi"
        ordering = ['-data_richiesta']
        
    def __str__(self):
        return f"{self.numero} - {self.titolo}"
    
    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self.generate_numero()
        super().save(*args, **kwargs)
    
    def generate_numero(self):
        """Genera numero automatico PRV-YYYY-NNN"""
        year = timezone.now().year
        last_number = RichiestaPreventivo.objects.filter(
            numero__startswith=f'PRV-{year}-'
        ).count()
        return f'PRV-{year}-{last_number + 1:03d}'
    
    def get_absolute_url(self):
        return reverse('preventivi:dettaglio', kwargs={'pk': self.pk})
    
    @property
    def is_scaduto(self):
        """Verifica se la richiesta è scaduta"""
        return timezone.now().date() > self.data_scadenza
    
    @property
    def giorni_rimanenti(self):
        """Calcola giorni rimanenti alla scadenza"""
        delta = self.data_scadenza - timezone.now().date()
        return delta.days
    
    @property
    def fornitori_totali(self):
        """Numero totale fornitori coinvolti"""
        return self.fornitori.count()
    
    @property
    def fornitori_risposto(self):
        """Numero fornitori che hanno risposto"""
        return self.fornitorepreventivo_set.filter(ha_risposto=True).count()
    
    @property
    def percentuale_risposte(self):
        """Percentuale di fornitori che hanno risposto"""
        if self.fornitori_totali == 0:
            return 0
        return (self.fornitori_risposto / self.fornitori_totali) * 100
    
    @property
    def può_essere_inviato(self):
        """Verifica se può essere inviato ai fornitori"""
        return (self.stato == 'CREATO' and
                self.fornitori.exists())
    
    @property
    def può_raccogliere_preventivi(self):
        """Verifica se si possono raccogliere preventivi"""
        return self.stato == 'INVIATO_FORNITORI'
    
    @property
    def può_essere_valutato(self):
        """Verifica se può essere valutato"""
        return (self.stato == 'PREVENTIVI_RACCOLTI' and 
                self.preventivo_set.exists())
    
    @property
    def può_essere_approvato(self):
        """Verifica se può essere approvato"""
        return (self.stato == 'IN_VALUTAZIONE' and 
                self.preventivo_set.exists())
    
    def get_preventivi_per_valutazione(self):
        """Ritorna i preventivi ordinati per importo (più basso prima)"""
        preventivi = []
        for preventivo in self.preventivo_set.all():
            preventivi.append({
                'preventivo': preventivo,
                'importo': preventivo.importo_totale
            })
        return sorted(preventivi, key=lambda x: x['importo'])
    
    def get_ranking_preventivi(self):
        """
        Ritorna i preventivi ordinati per importo con informazioni aggiuntive
        Nel sistema semplificato, il ranking è basato solo sull'importo
        """
        preventivi_ranking = []
        
        for preventivo in self.preventivo_set.select_related('fornitore').prefetch_related('parametri'):
            # Nel nuovo sistema semplificato, il ranking è basato sull'importo
            preventivi_ranking.append({
                'preventivo': preventivo,
                'fornitore': preventivo.fornitore,
                'importo': preventivo.importo_totale,
                'parametri_count': preventivo.parametri.count(),
                'has_parametri': preventivo.parametri.exists(),
                'rank_by_price': 0,  # Verrà calcolato dopo l'ordinamento
            })
        
        # Ordina per importo (più basso = migliore)
        preventivi_ranking.sort(key=lambda x: x['importo'])
        
        # Assegna il ranking basato sull'importo
        for i, item in enumerate(preventivi_ranking, 1):
            item['rank_by_price'] = i
        
        return preventivi_ranking


class FornitorePreventivo(models.Model):
    """
    Tabella di collegamento con tracking dello stato per fornitore
    """
    
    richiesta = models.ForeignKey(RichiestaPreventivo, on_delete=models.CASCADE)
    fornitore = models.ForeignKey('anagrafica.Fornitore', on_delete=models.CASCADE)
    
    # Tracking email
    email_inviata = models.BooleanField(default=False)
    data_invio = models.DateTimeField(null=True, blank=True)
    email_letta = models.BooleanField(default=False)  # Se supportato
    data_lettura = models.DateTimeField(null=True, blank=True)
    
    # Tracking risposta
    ha_risposto = models.BooleanField(default=False)
    data_risposta = models.DateTimeField(null=True, blank=True)
    note_fornitore = models.TextField(blank=True, help_text="Note dal fornitore")
    
    # Solleciti
    numero_solleciti = models.IntegerField(default=0)
    data_ultimo_sollecito = models.DateTimeField(null=True, blank=True)
    
    # Token per link sicuro
    token_accesso = models.UUIDField(default=uuid.uuid4, unique=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['richiesta', 'fornitore']
        verbose_name = "Fornitore Preventivo"
        verbose_name_plural = "Fornitori Preventivi"
        
    def __str__(self):
        return f"{self.richiesta.numero} - {self.fornitore.nome}"
    
    @property
    def giorni_senza_risposta(self):
        """Giorni trascorsi dall'invio senza risposta"""
        if not self.data_invio or self.ha_risposto:
            return 0
        return (timezone.now() - self.data_invio).days


class Preventivo(models.Model):
    """
    Preventivo ricevuto da un fornitore
    """
    
    richiesta = models.ForeignKey(RichiestaPreventivo, on_delete=models.CASCADE)
    fornitore = models.ForeignKey('anagrafica.Fornitore', on_delete=models.PROTECT)
    
    # Contenuto del preventivo
    numero_preventivo_fornitore = models.CharField(
        max_length=100, 
        help_text="Numero del preventivo assegnato dal fornitore"
    )
    importo_totale = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="Importo totale del preventivo"
    )
    valuta = models.CharField(max_length=3, default='EUR')
    validita_giorni = models.IntegerField(help_text="Giorni di validità dell'offerta")
    
    # Condizioni commerciali
    termini_pagamento = models.CharField(max_length=200, help_text="Es: 30gg DFFM")
    tempi_consegna = models.CharField(max_length=200, help_text="Es: 15 giorni lavorativi")
    condizioni_trasporto = models.CharField(max_length=200, blank=True)
    garanzia = models.CharField(max_length=200, blank=True)
    
    # Note tecniche e commerciali
    note_tecniche = models.TextField(blank=True)
    note_commerciali = models.TextField(blank=True)
    
    # File preventivo principale
    file_preventivo = models.FileField(
        upload_to='preventivi/files/',
        help_text="File del preventivo ricevuto dal fornitore (PDF, DOC, etc.)",
        null=True,
        blank=True
    )
    
    # Allegati aggiuntivi (collegati tramite core.allegati)
    allegati = GenericRelation('core.Allegato')
    
    # Collegamento all'ordine di acquisto generato (se preventivo approvato)
    # TODO: Da implementare quando si integrerà con bef2/acquisti
    ordine_acquisto_numero = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Numero ordine di acquisto generato da questo preventivo"
    )
    
    # Metadata
    data_ricevimento = models.DateTimeField(auto_now_add=True)
    data_scadenza_offerta = models.DateField(
        help_text="Calcolato automaticamente da validità giorni"
    )
    operatore_inserimento = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT,
        help_text="Operatore che ha inserito il preventivo"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Preventivo"
        verbose_name_plural = "Preventivi"
        ordering = ['-data_ricevimento']
        unique_together = ['richiesta', 'fornitore']
        
    def __str__(self):
        return f"{self.fornitore.nome} - €{self.importo_totale}"
    
    def save(self, *args, **kwargs):
        if not self.data_scadenza_offerta:
            self.data_scadenza_offerta = (
                timezone.now().date() + 
                timezone.timedelta(days=self.validita_giorni)
            )
        super().save(*args, **kwargs)
        
        # Aggiorna lo stato del FornitorePreventivo
        try:
            fornitore_preventivo = FornitorePreventivo.objects.get(
                richiesta=self.richiesta, 
                fornitore=self.fornitore
            )
            if not fornitore_preventivo.ha_risposto:
                fornitore_preventivo.ha_risposto = True
                fornitore_preventivo.data_risposta = timezone.now()
                fornitore_preventivo.save()
        except FornitorePreventivo.DoesNotExist:
            pass
    
    @property
    def is_scaduto(self):
        """Verifica se l'offerta è scaduta"""
        return timezone.now().date() > self.data_scadenza_offerta
    
    @property
    def giorni_validità_rimanenti(self):
        """Giorni di validità rimanenti"""
        delta = self.data_scadenza_offerta - timezone.now().date()
        return max(0, delta.days)
    
    def ha_parametri(self):
        """Verifica se il preventivo ha parametri definiti"""
        return self.parametri.exists()
    
    def ha_ordine_collegato(self):
        """Verifica se esiste un ordine di acquisto collegato"""
        return bool(self.ordine_acquisto_numero)
    
    def get_ordine_url_bef2(self):
        """Ottiene l'URL per visualizzare l'ordine in bef2 (placeholder)"""
        if self.ordine_acquisto_numero:
            # TODO: Implementare quando avremo le URL di bef2
            return f"/bef2/ordini/{self.ordine_acquisto_numero}/"
        return None


class ParametroValutazione(models.Model):
    """
    Parametro semplificato per confronto preventivi - Step 2
    Due soli campi: descrizione + valore alfanumerico
    """
    
    preventivo = models.ForeignKey(Preventivo, on_delete=models.CASCADE, related_name='parametri')
    
    # Due campi semplici come richiesto
    descrizione = models.CharField(max_length=200, help_text="Descrizione del parametro (es: Tempo consegna)")
    valore = models.CharField(max_length=100, help_text="Valore alfanumerico (es: 15 giorni, Eccellente, €1200)")
    
    # Metadata
    ordine = models.IntegerField(default=0, help_text="Ordine di visualizzazione")
    creato_da = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Parametro Valutazione"
        verbose_name_plural = "Parametri Valutazione"
        ordering = ['ordine', 'descrizione']
        
    def __str__(self):
        return f"{self.descrizione}: {self.valore}"


# Nota: Il modello ValutazionePreventivo è stato rimosso perché ora i parametri
# sono semplici coppie descrizione-valore associate direttamente al preventivo