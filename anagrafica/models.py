"""
ANAGRAFICA MODELS - Modelli per gestione clienti e fornitori
===========================================================

Modelli per la gestione anagrafica:
- Cliente: Gestione clienti con limite credito e validazioni
- Fornitore: Gestione fornitori con dati fiscali e commerciali

NOTA: I rappresentanti sono stati rimossi da questo progetto
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal
import re

User = get_user_model()


class Cliente(models.Model):
    """Modello per i clienti con gestione credito integrata"""
    
    TIPO_PAGAMENTO_CHOICES = [
        ('immediato', 'Immediato'),
        ('15_giorni', '15 giorni'),
        ('30_giorni', '30 giorni'),
        ('60_giorni', '60 giorni'),
        ('90_giorni', '90 giorni'),
        ('120_giorni', '120 giorni'),
    ]
    
    # === DATI ANAGRAFICI ===
    nome = models.CharField(
        max_length=200, 
        help_text="Nome o Ragione Sociale"
    )
    indirizzo = models.TextField(blank=True)
    citta = models.CharField(max_length=100, blank=True)
    cap = models.CharField(max_length=10, blank=True)
    telefono = models.CharField(max_length=20)
    email = models.EmailField()
    
    # === DATI FISCALI ===
    # Almeno uno tra P.IVA e CF deve essere fornito
    partita_iva = models.CharField(max_length=15, blank=True)
    codice_fiscale = models.CharField(max_length=16, blank=True)
    codice_univoco = models.CharField(max_length=10, blank=True)
    pec = models.EmailField(blank=True)
    
    # === DATI COMMERCIALI ===
    tipo_pagamento = models.CharField(
        max_length=20,
        choices=TIPO_PAGAMENTO_CHOICES,
        default='immediato'
    )
    
    # === LIMITE CREDITO ===
    limite_credito = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Limite di credito concesso (€)'
    )
    
    # === ZONA GEOGRAFICA ===
    zona = models.CharField(max_length=100, blank=True)
    
    # === ORARI E CONSEGNE ===
    orario_consegna = models.CharField(
        max_length=200,
        default='Orari negozio: 9-13 16-19:30',
        help_text='Orari di consegna e eventuali note specifiche'
    )
    
    GIORNI_SETTIMANA_CHOICES = [
        ('lunedi', 'Lunedì'),
        ('martedi', 'Martedì'),
        ('mercoledi', 'Mercoledì'),
        ('giovedi', 'Giovedì'),
        ('venerdi', 'Venerdì'),
        ('sabato', 'Sabato'),
        ('domenica', 'Domenica'),
    ]
    
    giorno_chiusura = models.CharField(
        max_length=10,
        choices=GIORNI_SETTIMANA_CHOICES,
        blank=True,
        help_text='Giorno di chiusura settimanale del cliente'
    )
    
    # === STATO ===
    attivo = models.BooleanField(default=True)
    note = models.TextField(blank=True)
    
    # === TIMESTAMP ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clienti"
        ordering = ['nome']
    
    def __str__(self):
        return self.nome
    
    def get_absolute_url(self):
        return reverse('anagrafica:dettaglio_cliente', kwargs={'pk': self.pk})
    
    # =====================================
    # 💳 METODI PER GESTIONE CREDITO
    # =====================================
    
    @property
    def credito_utilizzato(self):
        """
        Calcola credito attualmente utilizzato (ordini non pagati)
        
        ✅ Considera solo ordini confermati non ancora fatturati
        ✅ Compatibile con future app ordini
        """
        try:
            # Import dinamico per evitare circular import
            # TODO: Implementare quando ci saranno app ordini/vendite
            return Decimal('0.00')
            
        except Exception as e:
            # Log dell'errore ma non interrompere il funzionamento
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Errore calcolo credito utilizzato cliente {self.pk}: {e}")
            return Decimal('0.00')
    
    @property 
    def credito_disponibile(self):
        """Credito ancora disponibile"""
        return max(Decimal('0.00'), self.limite_credito - self.credito_utilizzato)
    
    def can_order_amount(self, importo):
        """
        Verifica se può ordinare per questo importo
        
        Args:
            importo (Decimal): Importo dell'ordine da verificare
            
        Returns:
            bool: True se può ordinare, False altrimenti
        """
        if not isinstance(importo, Decimal):
            importo = Decimal(str(importo))
        
        return self.credito_disponibile >= importo
    
    def get_stato_credito(self):
        """
        Restituisce stato del credito per UI
        
        Returns:
            dict: Contiene stato, classe_css, messaggio, percentuale_uso
        """
        if self.limite_credito == 0:
            return {
                'stato': 'nessun_limite',
                'classe_css': 'text-secondary',
                'messaggio': 'Nessun limite impostato',
                'percentuale_uso': 0
            }
        
        utilizzato = self.credito_utilizzato
        percentuale_uso = (utilizzato / self.limite_credito * 100) if self.limite_credito > 0 else 0
        
        if percentuale_uso >= 90:
            return {
                'stato': 'critico',
                'classe_css': 'text-danger',
                'messaggio': f'Credito quasi esaurito ({percentuale_uso:.1f}%)',
                'percentuale_uso': percentuale_uso
            }
        elif percentuale_uso >= 70:
            return {
                'stato': 'attenzione',
                'classe_css': 'text-warning', 
                'messaggio': f'Attenzione al credito ({percentuale_uso:.1f}%)',
                'percentuale_uso': percentuale_uso
            }
        else:
            return {
                'stato': 'ok',
                'classe_css': 'text-success',
                'messaggio': f'Credito disponibile ({percentuale_uso:.1f}%)',
                'percentuale_uso': percentuale_uso
            }
    
    # =====================================
    # ✅ VALIDAZIONI PERSONALIZZATE
    # =====================================
    
    def clean(self):
        """Validazioni personalizzate"""
        # Almeno uno tra P.IVA e CF deve essere fornito
        if not self.partita_iva and not self.codice_fiscale:
            raise ValidationError({
                'partita_iva': 'Specificare almeno Partita IVA o Codice Fiscale',
                'codice_fiscale': 'Specificare almeno Partita IVA o Codice Fiscale'
            })
        
        # Validazione limite credito
        if self.limite_credito < 0:
            raise ValidationError({
                'limite_credito': 'Il limite di credito non può essere negativo'
            })
        
        # Validazione P.IVA
        if self.partita_iva:
            self.partita_iva = self.partita_iva.replace(' ', '').upper()
            if not self._validate_partita_iva(self.partita_iva):
                raise ValidationError({
                    'partita_iva': 'Partita IVA non valida'
                })
        
        # Validazione CF
        if self.codice_fiscale:
            self.codice_fiscale = self.codice_fiscale.replace(' ', '').upper()
            if not self._validate_codice_fiscale(self.codice_fiscale):
                raise ValidationError({
                    'codice_fiscale': 'Codice Fiscale non valido'
                })
    
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
        # Pattern per persone fisiche (16 caratteri)
        pattern_persona = r'^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$'
        # Pattern per aziende (11 cifre)
        pattern_azienda = r'^\d{11}$'
        
        return bool(re.match(pattern_persona, cf) or re.match(pattern_azienda, cf))
    
    # =====================================
    # 📊 METODI INFORMATIVI AGGIUNTIVI
    # =====================================
    
    def is_nuovo_cliente(self, giorni=30):
        """Verifica se è un cliente nuovo (creato negli ultimi X giorni)"""
        from django.utils import timezone
        soglia = timezone.now() - timezone.timedelta(days=giorni)
        return self.created_at >= soglia


class Fornitore(models.Model):
    """Modello per i fornitori"""
    
    CATEGORIA_CHOICES = [
        ('materie_prime', 'Materie Prime'),
        ('semilavorati', 'Semilavorati'),
        ('servizi', 'Servizi'),
        ('consulenza', 'Consulenza'),
        ('software', 'Software/IT'),
        ('altri', 'Altri'),
    ]
    
    TIPO_PAGAMENTO_CHOICES = [
        ('bonifico_30', 'Bonifico 30 gg'),
        ('bonifico_60', 'Bonifico 60 gg'),
        ('bonifico_90', 'Bonifico 90 gg'),
        ('bonifico_120', 'Bonifico 120 gg'),
        ('rid_30', 'RID 30 gg'),
        ('rid_60', 'RID 60 gg'),
        ('riba_30', 'RIBA 30 gg'),
        ('riba_60', 'RIBA 60 gg'),
        ('contrassegno', 'Contrassegno'),
        ('anticipo', 'Anticipo 100%'),
        ('fine_mese', 'Fine Mese'),
        ('immediato', 'Pagamento Immediato'),
    ]
    
    PRIORITA_PAGAMENTO_CHOICES = [
        ('critica', '🔴 Critica (Urgente)'),
        ('alta', '🟡 Alta (Prioritaria)'),
        ('media', '🔵 Media (Normale)'),
        ('bassa', '⚪ Bassa (Differibile)'),
    ]
    
    # Dati anagrafici
    nome = models.CharField(max_length=200, help_text="Nome o Ragione Sociale")
    indirizzo = models.TextField(blank=True)
    citta = models.CharField(max_length=100, blank=True)
    cap = models.CharField(max_length=10, blank=True)
    telefono = models.CharField(max_length=20)
    email = models.EmailField()
    
    # Dati fiscali
    partita_iva = models.CharField(max_length=15)
    codice_fiscale = models.CharField(max_length=16, blank=True)
    pec = models.EmailField(blank=True, help_text="PEC del fornitore per fatturazione elettronica")
    codice_destinatario = models.CharField(max_length=7, blank=True, help_text="Codice destinatario SDI (7 caratteri)")
    
    # Dati bancari
    iban = models.CharField(max_length=34, blank=True)
    
    # Dati commerciali
    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIA_CHOICES,
        default='altri'
    )
    tipo_pagamento = models.CharField(
        max_length=20,
        choices=TIPO_PAGAMENTO_CHOICES,
        default='bonifico_30'
    )
    priorita_pagamento_default = models.CharField(
        max_length=10,
        choices=PRIORITA_PAGAMENTO_CHOICES,
        default='media',
        help_text="Priorità di default per i pagamenti a questo fornitore"
    )
    
    # Referente
    referente_nome = models.CharField(max_length=100, blank=True)
    referente_telefono = models.CharField(max_length=20, blank=True)
    referente_email = models.EmailField(blank=True)
    
    # Stato
    attivo = models.BooleanField(default=True)
    note = models.TextField(blank=True)
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Fornitore"
        verbose_name_plural = "Fornitori"
        ordering = ['nome']
    
    def __str__(self):
        return self.nome
    
    def get_absolute_url(self):
        return reverse('anagrafica:dettaglio_fornitore', kwargs={'pk': self.pk})
    
    def clean(self):
        """Validazioni personalizzate"""
        # Validazione P.IVA semplificata
        if self.partita_iva:
            self.partita_iva = self.partita_iva.replace(' ', '').replace('-', '').upper()
            if len(self.partita_iva) < 8 or len(self.partita_iva) > 15:
                raise ValidationError({
                    'partita_iva': 'Partita IVA deve essere tra 8 e 15 caratteri'
                })
        
        # Validazione CF semplificata
        if self.codice_fiscale:
            self.codice_fiscale = self.codice_fiscale.replace(' ', '').upper()
            if len(self.codice_fiscale) < 8 or len(self.codice_fiscale) > 16:
                raise ValidationError({
                    'codice_fiscale': 'Codice Fiscale non valido (8-16 caratteri)'
                })
        
        # Validazione IBAN
        if self.iban:
            self.iban = self.iban.replace(' ', '').upper()
            if not self._validate_iban(self.iban):
                raise ValidationError({
                    'iban': 'IBAN non valido'
                })
    
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
        """Validazione IBAN italiana base"""
        if not iban.startswith('IT'):
            return False
        if len(iban) != 27:  # IBAN italiano: IT + 25 caratteri
            return False
        return True