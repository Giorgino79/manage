from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.utils import timezone
from decimal import Decimal
from datetime import date


class StabilimentoManager(models.Manager):
    """Manager personalizzato per gli stabilimenti"""
    
    def attivi(self):
        """Stabilimenti attivi"""
        return self.filter(attivo=True)
    
    def per_responsabile(self, responsabile):
        """Stabilimenti gestiti da un responsabile"""
        return self.filter(responsabile=responsabile)
    
    def con_scadenze_prossime(self, giorni=30):
        """Stabilimenti con scadenze nei prossimi X giorni"""
        data_limite = timezone.now().date() + timezone.timedelta(days=giorni)
        return self.filter(
            costi__data_scadenza_servizio__lte=data_limite,
            costi__data_scadenza_servizio__gte=timezone.now().date()
        ).distinct()


class Stabilimento(models.Model):
    """
    Modello per la gestione degli stabilimenti aziendali.
    
    RESPONSABILITÀ:
    - Anagrafica stabilimenti
    - Informazioni di contatto
    - Gestione responsabili
    - Coordinamento con altre app (mag2, acq2, etc.)
    """
    
    # === ANAGRAFICA ===
    nome = models.CharField(
        max_length=200,
        help_text="Nome identificativo dello stabilimento"
    )
    codice_stabilimento = models.CharField(
        max_length=10,
        unique=True,
        help_text="Codice univoco per identificazione rapida"
    )
    
    # === INDIRIZZO ===
    indirizzo = models.CharField(max_length=300)
    cap = models.CharField(
        max_length=5,
        validators=[RegexValidator(
            regex=r'^\d{5}$',
            message='Il CAP deve essere di 5 cifre'
        )]
    )
    citta = models.CharField(max_length=100)
    provincia = models.CharField(
        max_length=2,
        validators=[RegexValidator(
            regex=r'^[A-Z]{2}$',
            message='Provincia deve essere di 2 lettere maiuscole'
        )]
    )
    
    # === CONTATTI ===
    telefono = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Telefono principale dello stabilimento"
    )
    email_filiale = models.EmailField(
        blank=True,
        null=True,
        help_text="Email principale dello stabilimento"
    )
    
    # === RESPONSABILI ===
    responsabile_operativo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stabilimenti_operativi',
        help_text='Responsabile operativo dello stabilimento (scelto manualmente)'
    )
    responsabile_amministrativo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stabilimenti_amministrativi',
        help_text='Responsabile amministrativo dello stabilimento (scelto manualmente)'
    )
    
    # === TRACCIABILITÀ ===
    creato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='stabilimenti_creati',
        help_text='Utente che ha creato lo stabilimento (automatico)'
    )
    modificato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='stabilimenti_modificati',
        null=True,
        blank=True,
        help_text='Ultimo utente che ha modificato lo stabilimento'
    )
    
    # === CARATTERISTICHE STRUTTURALI ===
    superficie_mq = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Superficie in metri quadrati"
    )
    numero_piani = models.PositiveSmallIntegerField(
        default=1,
        help_text="Numero di piani dell'edificio"
    )
    anno_costruzione = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        help_text="Anno di costruzione dell'edificio"
    )
    
    # === STATO E GESTIONE ===
    attivo = models.BooleanField(
        default=True,
        help_text="Indica se lo stabilimento è attivo"
    )
    data_apertura = models.DateField(
        blank=True,
        null=True,
        help_text="Data di apertura/attivazione dello stabilimento"
    )
    data_chiusura = models.DateField(
        blank=True,
        null=True,
        help_text="Data di chiusura (se applicabile)"
    )
    
    # === NOTE ===
    note_generali = models.TextField(
        blank=True,
        null=True,
        help_text="Note generali sullo stabilimento"
    )
    
    # === TIMESTAMP ===
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)
    
    # === MANAGER ===
    objects = StabilimentoManager()
    
    class Meta:
        verbose_name = "Stabilimento"
        verbose_name_plural = "Stabilimenti"
        ordering = ['nome']
        indexes = [
            models.Index(fields=['attivo']),
            models.Index(fields=['codice_stabilimento']),
            models.Index(fields=['responsabile_operativo']),
            models.Index(fields=['responsabile_amministrativo']),
            models.Index(fields=['citta']),
        ]
    
    def __str__(self):
        return f"{self.codice_stabilimento} - {self.nome}"
    
    def save(self, *args, **kwargs):
        # Genera codice automatico se non presente
        if not self.codice_stabilimento:
            self.codice_stabilimento = self._genera_codice()
        
        # NOTA: creato_da e modificato_da vanno gestiti nella view
        # perché il model non ha accesso al request.user
        super().save(*args, **kwargs)
    
    def _genera_codice(self):
        """Genera codice stabilimento univoco"""
        ultimo_numero = Stabilimento.objects.filter(
            codice_stabilimento__startswith='STB'
        ).count()
        return f"STB{(ultimo_numero + 1):03d}"
    
    # === METODI INFORMATIVI ===
    def get_indirizzo_completo(self):
        """Restituisce l'indirizzo completo formattato"""
        return f"{self.indirizzo}, {self.cap} {self.citta} ({self.provincia})"
    
    def get_costi_anno_corrente(self):
        """Costi sostenuti nell'anno corrente"""
        anno_corrente = timezone.now().year
        return self.costi.filter(
            data_fattura__year=anno_corrente
        ).aggregate(
            totale=models.Sum('importo')
        )['totale'] or Decimal('0.00')
    
    def get_prossime_scadenze(self, giorni=30):
        """Scadenze nei prossimi X giorni"""
        data_limite = timezone.now().date() + timezone.timedelta(days=giorni)
        return self.costi.filter(
            data_scadenza_servizio__lte=data_limite,
            data_scadenza_servizio__gte=timezone.now().date()
        ).order_by('data_scadenza_servizio')
    
    def has_scadenze_urgenti(self, giorni=7):
        """Verifica se ci sono scadenze urgenti"""
        return self.get_prossime_scadenze(giorni).exists()


class CostiStabilimentoManager(models.Manager):
    """Manager per i costi di stabilimento"""
    
    def per_tipo(self, tipo_costo):
        """Filtra per tipo di costo"""
        return self.filter(causale=tipo_costo)
    
    def scadenze_prossime(self, giorni=30):
        """Costi con scadenze nei prossimi X giorni"""
        data_limite = timezone.now().date() + timezone.timedelta(days=giorni)
        return self.filter(
            data_scadenza_servizio__lte=data_limite,
            data_scadenza_servizio__gte=timezone.now().date()
        )
    
    def dell_anno(self, anno):
        """Costi di un anno specifico"""
        return self.filter(data_fattura__year=anno)
    
    def del_periodo(self, data_inizio, data_fine):
        """Costi in un periodo specifico"""
        return self.filter(
            data_fattura__gte=data_inizio,
            data_fattura__lte=data_fine
        )
    

class CostiStabilimento(models.Model):
    """
    Modello per la gestione dei costi sostenuti per gli stabilimenti.
    
    RESPONSABILITÀ:
    - Tracciamento costi per tipologia
    - Gestione scadenze servizi/certificazioni
    - Archiviazione documenti
    - Reportistica costi
    """
    
    class TipoCosto(models.TextChoices):
        MANUTENZIONE_ORDINARIA = 'manutenzione_ordinaria', 'Manutenzione Ordinaria'
        MANUTENZIONE_STRAORDINARIA = 'manutenzione_straordinaria', 'Manutenzione Straordinaria'
        ADEGUAMENTO = 'adeguamento', 'Adeguamento Strutturale'
        SERVIZI_PERIODICI = 'servizi_periodici', 'Servizi Periodici'
        CERTIFICAZIONI = 'certificazioni', 'Certificazioni Obbligatorie'
        ENERGIA_ELETTRICA = 'energia_elettrica', 'Energia Elettrica'  # ← AGGIUNGI
        GAS_NATURALE = 'gas_naturale', 'Gas Naturale'
        ACQUA = 'acqua', 'Acqua e Scarichi'
        TELEFONIA = 'telefonia', 'Telefonia e Internet'
        RIFIUTI = 'rifiuti', 'Smaltimento Rifiuti'
        SICUREZZA = 'sicurezza', 'Sicurezza e Vigilanza'
        PULIZIE = 'pulizie', 'Servizi di Pulizia'
        ASSICURAZIONI = 'assicurazioni', 'Assicurazioni'
        TASSE = 'tasse', 'Tasse e Tributi'
        ALTRO = 'altro', 'Altro'
    
    class StatoCosto(models.TextChoices):
        PREVENTIVO = 'preventivo', 'Preventivo'
        APPROVATO = 'approvato', 'Approvato'
        IN_CORSO = 'in_corso', 'In Corso'
        COMPLETATO = 'completato', 'Completato'
        FATTURATO = 'fatturato', 'Fatturato'
        PAGATO = 'pagato', 'Pagato'
    
    # === RELAZIONI ===
    stabilimento = models.ForeignKey(
        Stabilimento,
        on_delete=models.PROTECT,
        related_name='costi',
        help_text='Stabilimento di riferimento'
    )
    incaricato = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='costi_gestiti',
        help_text='Responsabile interno della pratica'
    )
    fornitore = models.ForeignKey(
        'anagrafica.Fornitore',
        on_delete=models.PROTECT,
        related_name='costi_stabilimenti',
        help_text='Fornitore del servizio/lavoro'
    )
    
    # === IDENTIFICATIVI ===
    numero_pratica = models.CharField(
        max_length=50,
        unique=True,
        help_text='Numero pratica generato automaticamente'
    )
    
    # === CLASSIFICAZIONE ===
    causale = models.CharField(
        max_length=50,
        choices=TipoCosto.choices,
        default=TipoCosto.SERVIZI_PERIODICI,
        verbose_name='Tipologia Costo'
    )
    stato = models.CharField(
        max_length=20,
        choices=StatoCosto.choices,
        default=StatoCosto.PREVENTIVO,
        verbose_name='Stato della Pratica'
    )
    
    # === DESCRIZIONE ===
    titolo = models.CharField(
        max_length=200,
        help_text='Titolo/oggetto dell\'intervento o servizio'
    )
    descrizione = models.TextField(
        help_text='Descrizione dettagliata dell\'intervento'
    )
    
    # === ASPETTI ECONOMICI ===
    importo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Importo del costo'
    )
    iva_percentuale = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=22,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='IVA %'
    )
    
    # === DATE ===
    data_richiesta = models.DateField(
        default=timezone.now,
        help_text='Data della richiesta/preventivo'
    )
    data_inizio_lavori = models.DateField(
        blank=True,
        null=True,
        help_text='Data inizio intervento/servizio'
    )
    data_fine_lavori = models.DateField(
        blank=True,
        null=True,
        help_text='Data fine intervento/servizio'
    )
    data_fattura = models.DateField(
        blank=True,
        null=True,
        help_text='Data della fattura'
    )
    data_scadenza_servizio = models.DateField(
        blank=True,
        null=True,
        verbose_name='Prossima Scadenza',
        help_text='Data del prossimo intervento programmato o scadenza certificazione'
    )
    
    # === DOCUMENTI ===
    fattura = models.FileField(
        upload_to='fatture_stabilimenti/%Y/%m/',
        blank=True,
        null=True,
        help_text='File della fattura'
    )
    preventivo = models.FileField(
        upload_to='preventivi_stabilimenti/%Y/%m/',
        blank=True,
        null=True,
        help_text='File del preventivo'
    )
    certificato = models.FileField(
        upload_to='certificati_stabilimenti/%Y/%m/',
        blank=True,
        null=True,
        help_text='Certificato o documento ufficiale'
    )
    
    # === ALLEGATI AGGIUNTIVI ===
    allegato1 = models.FileField(
        upload_to='allegati_stabilimenti/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Allegato 1'
    )
    allegato2 = models.FileField(
        upload_to='allegati_stabilimenti/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Allegato 2'
    )
    allegato3 = models.FileField(
        upload_to='allegati_stabilimenti/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Allegato 3'
    )
    
    # === NOTE ===
    note_interne = models.TextField(
        blank=True,
        null=True,
        help_text='Note interne non visibili nei documenti'
    )
    
    # === TIMESTAMP ===
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)
    
    # === CONSUMI ===
    consumo_kwh = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    consumo_mc = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    periodo_fatturazione_da = models.DateField(null=True, blank=True)
    periodo_fatturazione_a = models.DateField(null=True, blank=True)
    codice_pdr_pod = models.CharField(max_length=50, null=True, blank=True)
    # === MANAGER ===
    objects = CostiStabilimentoManager()
    
    class Meta:
        verbose_name = "Costo Stabilimento"
        verbose_name_plural = "Costi Stabilimenti"
        ordering = ['-data_creazione']
        indexes = [
            models.Index(fields=['stabilimento', 'causale']),
            models.Index(fields=['data_scadenza_servizio']),
            models.Index(fields=['stato']),
            models.Index(fields=['fornitore']),
            models.Index(fields=['data_fattura']),
            models.Index(fields=['numero_pratica']),
        ]
    
    def __str__(self):
        return f"{self.numero_pratica} - {self.titolo} ({self.stabilimento.nome})"
    
    def save(self, *args, **kwargs):
        # Genera numero pratica se nuovo
        if not self.numero_pratica:
            self.numero_pratica = self._genera_numero_pratica()
        super().save(*args, **kwargs)
    
    def _genera_numero_pratica(self):
        """Genera numero pratica univoco"""
        anno = timezone.now().year
        ultimo_numero = CostiStabilimento.objects.filter(
            numero_pratica__startswith=f"STB-{anno}-"
        ).count()
        return f"STB-{anno}-{(ultimo_numero + 1):04d}"
    
    # === METODI DI CALCOLO ===
    def calcola_totale_con_iva(self):
        """Calcola l'importo totale comprensivo di IVA"""
        return self.importo * (1 + (self.iva_percentuale / Decimal('100')))
    
    def calcola_iva(self):
        """Calcola l'importo dell'IVA"""
        return self.importo * (self.iva_percentuale / Decimal('100'))
    
    # === METODI INFORMATIVI ===
    def is_scaduto(self):
        """Verifica se il servizio è scaduto"""
        if self.data_scadenza_servizio:
            return self.data_scadenza_servizio < timezone.now().date()
        return False
    
    def giorni_alla_scadenza(self):
        """Restituisce i giorni rimanenti alla scadenza"""
        if self.data_scadenza_servizio:
            delta = self.data_scadenza_servizio - timezone.now().date()
            return delta.days
        return None
    
    def is_in_scadenza(self, giorni=30):
        """Verifica se il servizio è in scadenza nei prossimi X giorni"""
        giorni_rimasti = self.giorni_alla_scadenza()
        if giorni_rimasti is not None:
            return 0 <= giorni_rimasti <= giorni
        return False
    
    def get_durata_lavori(self):
        """Calcola la durata dei lavori in giorni"""
        if self.data_inizio_lavori and self.data_fine_lavori:
            return (self.data_fine_lavori - self.data_inizio_lavori).days
        return None
    
    def can_be_deleted(self):
        """Verifica se il costo può essere eliminato"""
        return self.stato in [self.StatoCosto.PREVENTIVO, self.StatoCosto.APPROVATO]
    
    def can_be_modified(self):
        """Verifica se il costo può essere modificato"""
        return self.stato not in [self.StatoCosto.PAGATO]

    def is_urgente(self):
        """Verifica se la scadenza è urgente (7 giorni)"""
        return self.is_in_scadenza(7)
    
    def is_prossima_scadenza(self):
        """Verifica se la scadenza è prossima (30 giorni)"""
        return self.is_in_scadenza(30)
    
    def is_scadenza_settimanale(self):
        """Verifica se la scadenza è nella prossima settimana (7 giorni)"""
        return self.is_in_scadenza(7)
    
    def is_scadenza_quindicinale(self):
        """Verifica se la scadenza è nei prossimi 15 giorni"""
        return self.is_in_scadenza(15)

class DocStabilimento(models.Model):
    """
    Modello per la gestione di documenti generici legati agli stabilimenti.
    
    RESPONSABILITÀ:
    - Archiviazione documenti vari
    - Categorizzazione documenti
    - Tracciamento versioni
    """
    
    class TipoDocumento(models.TextChoices):
        # Autorizzazioni e Licenze
        SCIA = 'scia', 'SCIA (Segnalazione Certificata di Inizio Attività)'
        DIA = 'dia', 'DIA (Dichiarazione di Inizio Attività)'
        AUTORIZZAZIONE = 'autorizzazione', 'Autorizzazione Edilizia'
        PERMESSO_COSTRUIRE = 'permesso_costruire', 'Permesso di Costruire'
        
        # Contratti di Servizio
        CONTRATTO_DERATTIZZAZIONE = 'contratto_derattizzazione', 'Contratto Derattizzazione'
        CONTRATTO_DISINFESTAZIONE = 'contratto_disinfestazione', 'Contratto Disinfestazione'
        CONTRATTO_PULIZIE = 'contratto_pulizie', 'Contratto Pulizie'
        CONTRATTO_VIGILANZA = 'contratto_vigilanza', 'Contratto Vigilanza'
        CONTRATTO_MANUTENZIONE = 'contratto_manutenzione', 'Contratto Manutenzione'
        
        # Certificazioni di Sicurezza
        CERTIFICATO_PREVENZIONE_INCENDI = 'cert_prevenzione_incendi', 'Certificato Prevenzione Incendi'
        CERTIFICATO_AGIBILITA = 'cert_agibilita', 'Certificato di Agibilità'
        CERTIFICATO_CONFORMITA = 'cert_conformita', 'Certificato di Conformità'
        
        # Controlli Periodici
        COLLAUDO_IMPIANTI = 'collaudo_impianti', 'Collaudo Impianti'
        VERIFICA_ASCENSORI = 'verifica_ascensori', 'Verifica Ascensori'
        CONTROLLO_CALDAIE = 'controllo_caldaie', 'Controllo Caldaie'
        CONTROLLO_ANTINCENDIO = 'controllo_antincendio', 'Controllo Sistemi Antincendio'
        
        # Documenti Ambientali
        AUTORIZZAZIONE_EMISSIONI = 'aut_emissioni', 'Autorizzazione Emissioni'
        GESTIONE_RIFIUTI = 'gestione_rifiuti', 'Autorizzazione Gestione Rifiuti'
        
        # Documentazione Generale
        PLANIMETRIA = 'planimetria', 'Planimetria'
        DENUNCIA = 'denuncia', 'Denuncia/Comunicazione'
        RAPPORTO = 'rapporto', 'Rapporto Tecnico'
        VERBALE = 'verbale', 'Verbale Controllo'
        CONTRATTO = 'contratto', 'Contratto Generico'
        CERTIFICAZIONE = 'certificazione', 'Certificazione Generica'
        ALTRO = 'altro', 'Altro'
    
    # === RELAZIONI ===
    stabilimento = models.ForeignKey(
        Stabilimento,
        on_delete=models.PROTECT,
        related_name='documenti',
        help_text='Stabilimento di riferimento'
    )
    caricato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='documenti_caricati',
        help_text='Utente che ha caricato il documento'
    )
    
    # === IDENTIFICAZIONE ===
    nome_documento = models.CharField(
        max_length=200,
        help_text='Nome identificativo del documento'
    )
    tipo_documento = models.CharField(
        max_length=30,
        choices=TipoDocumento.choices,
        default=TipoDocumento.ALTRO,
        help_text='Tipologia del documento'
    )
    versione = models.CharField(
        max_length=10,
        default='1.0',
        help_text='Versione del documento'
    )
    
    # === CONTENUTO ===
    descrizione = models.TextField(
        blank=True,
        null=True,
        help_text='Descrizione del contenuto del documento'
    )
    file_documento = models.FileField(
        upload_to='documenti_stabilimenti/%Y/%m/',
        help_text='File del documento'
    )
    
    # === DATE ===
    data_documento = models.DateField(
        blank=True,
        null=True,
        help_text='Data del documento (se diversa dalla data di caricamento)'
    )
    data_scadenza = models.DateField(
        blank=True,
        null=True,
        help_text='Data di scadenza del documento (se applicabile)'
    )
    
    # === STATO ===
    attivo = models.BooleanField(
        default=True,
        help_text='Indica se il documento è ancora valido/attivo'
    )
    
    # === NOTE ===
    note = models.TextField(
        blank=True,
        null=True,
        help_text='Note aggiuntive sul documento'
    )
    
    # === TIMESTAMP ===
    data_inserimento = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Documento Stabilimento"
        verbose_name_plural = "Documenti Stabilimenti"
        ordering = ['-data_inserimento']
        unique_together = ['stabilimento', 'nome_documento', 'versione']
        indexes = [
            models.Index(fields=['stabilimento', 'tipo_documento']),
            models.Index(fields=['data_scadenza']),
            models.Index(fields=['attivo']),
        ]
    
    def __str__(self):
        return f"{self.nome_documento} v{self.versione} - {self.stabilimento.nome}"
    
    # === METODI INFORMATIVI ===
    def is_scaduto(self):
        """Verifica se il documento è scaduto"""
        if self.data_scadenza:
            return self.data_scadenza < timezone.now().date()
        return False
    
    def giorni_alla_scadenza(self):
        """Restituisce i giorni rimanenti alla scadenza"""
        if self.data_scadenza:
            delta = self.data_scadenza - timezone.now().date()
            return delta.days
        return None
    
    def get_estensione_file(self):
        """Restituisce l'estensione del file"""
        if self.file_documento:
            return self.file_documento.name.split('.')[-1].lower()
        return None