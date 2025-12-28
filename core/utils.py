"""
CORE UTILITIES - Sistema Universale Utilities Generiche
======================================================

Funzioni utility generiche riutilizzabili:
- 🔧 Validatori e formattatori dati
- 📱 Generatori codici e ID
- 🕐 Gestione date e orari
- 💰 Calcoli finanziari e matematici
- 🌐 Networking e comunicazioni
- 📊 Statistiche e aggregazioni

Caratteristiche:
- Zero dipendenze da app specifiche
- Performance ottimizzate
- Error handling robusto
- Compatibilità internazionale
- Logging integrato
- Funzioni pure quando possibile

Versione: 1.0
Compatibilità: Django 3.2+, Python 3.8+
"""

import re
import uuid
import random
import string
import hashlib
import secrets
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, timedelta, time
import calendar
import logging
import unicodedata
import json

from django.utils import timezone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.conf import settings

logger = logging.getLogger(__name__)


# =============================================================================
# VALIDATORS AND FORMATTERS
# =============================================================================

def validate_italian_tax_code(codice_fiscale: str) -> bool:
    """
    Valida codice fiscale italiano
    
    Args:
        codice_fiscale: Codice fiscale da validare
        
    Returns:
        True se valido
    """
    if not codice_fiscale or len(codice_fiscale) != 16:
        return False
    
    codice_fiscale = codice_fiscale.upper().strip()
    
    # Controllo caratteri
    if not re.match(r'^[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]$', codice_fiscale):
        return False
    
    # Algoritmo controllo carattere finale
    dispari = "BAFHJNPRTVCESULDGIMOQKWZYX"
    pari = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    controllo = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    
    somma = 0
    
    for i in range(15):
        char = codice_fiscale[i]
        if i % 2 == 0:  # Posizione dispari (1-based)
            if char.isdigit():
                valori_dispari = [1, 0, 5, 7, 9, 13, 15, 17, 19, 21]
                somma += valori_dispari[int(char)]
            else:
                somma += dispari.index(char)
        else:  # Posizione pari
            if char.isdigit():
                somma += int(char)
            else:
                somma += pari.index(char)
    
    carattere_controllo = controllo[somma % 26]
    return carattere_controllo == codice_fiscale[15]


def validate_italian_vat(partita_iva: str) -> bool:
    """
    Valida partita IVA italiana
    
    Args:
        partita_iva: Partita IVA da validare
        
    Returns:
        True se valida
    """
    if not partita_iva or len(partita_iva) != 11:
        return False
    
    partita_iva = partita_iva.strip()
    
    if not partita_iva.isdigit():
        return False
    
    # Algoritmo controllo
    somma = 0
    for i in range(10):
        cifra = int(partita_iva[i])
        if i % 2 == 1:  # Posizioni pari (0-based)
            cifra *= 2
            if cifra > 9:
                cifra = cifra // 10 + cifra % 10
        somma += cifra
    
    resto = somma % 10
    controllo = (10 - resto) % 10
    
    return controllo == int(partita_iva[10])


def validate_iban(iban: str) -> bool:
    """
    Valida IBAN internazionale
    
    Args:
        iban: IBAN da validare
        
    Returns:
        True se valido
    """
    if not iban:
        return False
    
    # Rimuovi spazi e converti uppercase
    iban = iban.replace(' ', '').upper()
    
    # Lunghezza minima
    if len(iban) < 15 or len(iban) > 34:
        return False
    
    # Solo lettere e numeri
    if not iban.isalnum():
        return False
    
    # Sposta i primi 4 caratteri in fondo
    rearranged = iban[4:] + iban[:4]
    
    # Sostituisci lettere con numeri (A=10, B=11, ...)
    numeric_string = ''
    for char in rearranged:
        if char.isdigit():
            numeric_string += char
        else:
            numeric_string += str(ord(char) - ord('A') + 10)
    
    # Modulo 97
    return int(numeric_string) % 97 == 1


def format_currency(
    amount: Union[int, float, Decimal],
    currency: str = 'EUR',
    locale: str = 'it_IT'
) -> str:
    """
    Formatta importo come valuta
    
    Args:
        amount: Importo da formattare
        currency: Codice valuta (EUR, USD, etc.)
        locale: Locale per formattazione
        
    Returns:
        Stringa formattata
    """
    if amount is None:
        return '-'
    
    # Converti in Decimal per precisione
    if isinstance(amount, (int, float)):
        amount = Decimal(str(amount))
    
    # Formattazione italiana
    if locale.startswith('it'):
        formatted = f"{amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        if currency == 'EUR':
            return f"€ {formatted}"
        else:
            return f"{formatted} {currency}"
    else:
        # Default English format
        formatted = f"{amount:,.2f}"
        return f"{currency} {formatted}"


def format_percentage(value: Union[int, float, Decimal], decimals: int = 2) -> str:
    """
    Formatta valore come percentuale
    
    Args:
        value: Valore da formattare (es: 0.15 per 15%)
        decimals: Numero decimali
        
    Returns:
        Stringa formattata (es: "15,00%")
    """
    if value is None:
        return '-'
    
    percentage = float(value) * 100
    formatted = f"{percentage:.{decimals}f}".replace('.', ',')
    return f"{formatted}%"


def sanitize_string(
    text: str,
    max_length: int = None,
    allowed_chars: str = None,
    remove_accents: bool = False
) -> str:
    """
    Sanifica stringa rimuovendo caratteri non consentiti
    
    Args:
        text: Testo da sanificare
        max_length: Lunghezza massima
        allowed_chars: Caratteri consentiti (None = alphanum + basic punctuation)
        remove_accents: Rimuovi accenti
        
    Returns:
        Stringa sanificata
    """
    if not text:
        return ''
    
    # Rimuovi accenti se richiesto
    if remove_accents:
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))
    
    # Caratteri consentiti di default
    if allowed_chars is None:
        allowed_chars = string.ascii_letters + string.digits + ' .-_'
    
    # Filtra caratteri
    sanitized = ''.join(c for c in text if c in allowed_chars)
    
    # Rimuovi spazi multipli
    sanitized = ' '.join(sanitized.split())
    
    # Lunghezza massima
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length].strip()
    
    return sanitized


# =============================================================================
# CODE AND ID GENERATORS
# =============================================================================

def generate_unique_code(
    length: int = 8,
    prefix: str = '',
    suffix: str = '',
    uppercase: bool = True,
    exclude_ambiguous: bool = True
) -> str:
    """
    Genera codice alfanumerico unico
    
    Args:
        length: Lunghezza del codice (escluso prefix/suffix)
        prefix: Prefisso
        suffix: Suffisso
        uppercase: Converti in maiuscolo
        exclude_ambiguous: Escludi caratteri ambigui (0, O, I, 1)
        
    Returns:
        Codice generato
    """
    chars = string.ascii_letters + string.digits
    
    if exclude_ambiguous:
        ambiguous = 'O0Il1'
        chars = ''.join(c for c in chars if c not in ambiguous)
    
    if uppercase:
        chars = chars.upper()
    
    code = ''.join(secrets.choice(chars) for _ in range(length))
    return f"{prefix}{code}{suffix}"


def generate_progressive_number(
    sequence_name: str,
    year: int = None,
    length: int = 6,
    prefix: str = '',
    separator: str = '/'
) -> str:
    """
    Genera numero progressivo per sequenza
    
    Args:
        sequence_name: Nome sequenza (es: 'fatture', 'ordini')
        year: Anno di riferimento (None = anno corrente)
        length: Lunghezza parte numerica
        prefix: Prefisso
        separator: Separatore tra anno e numero
        
    Returns:
        Numero progressivo (es: "FAT/2024/000001")
    """
    if year is None:
        year = timezone.now().year
    
    # In un'implementazione reale, questo dovrebbe usare un model
    # per tracciare i progressivi per sequenza/anno
    # Per ora generiamo un numero casuale alto per evitare collisioni
    number = random.randint(1, 999999)
    
    formatted_number = str(number).zfill(length)
    
    if prefix:
        return f"{prefix}{separator}{year}{separator}{formatted_number}"
    else:
        return f"{year}{separator}{formatted_number}"


def generate_qr_data(
    data: Dict[str, Any],
    format_type: str = 'json'
) -> str:
    """
    Genera dati per QR code
    
    Args:
        data: Dati da codificare
        format_type: Formato ('json', 'url', 'vcard', 'custom')
        
    Returns:
        Stringa dati per QR code
    """
    if format_type == 'json':
        return json.dumps(data, ensure_ascii=False)
    
    elif format_type == 'url':
        base_url = data.get('base_url', 'https://example.com')
        params = '&'.join(f"{k}={v}" for k, v in data.get('params', {}).items())
        return f"{base_url}?{params}" if params else base_url
    
    elif format_type == 'vcard':
        # Formato vCard per contatti
        lines = [
            'BEGIN:VCARD',
            'VERSION:3.0',
            f"FN:{data.get('name', '')}",
            f"ORG:{data.get('company', '')}",
            f"TEL:{data.get('phone', '')}",
            f"EMAIL:{data.get('email', '')}",
            f"URL:{data.get('website', '')}",
            'END:VCARD'
        ]
        return '\n'.join(line for line in lines if ':' in line and line.split(':', 1)[1])
    
    else:  # custom
        return str(data)


def generate_hash_id(data: str, algorithm: str = 'sha256', length: int = 8) -> str:
    """
    Genera ID hash da dati
    
    Args:
        data: Dati di input
        algorithm: Algoritmo hash (md5, sha1, sha256)
        length: Lunghezza output (troncatura)
        
    Returns:
        Hash ID
    """
    if algorithm == 'md5':
        hash_obj = hashlib.md5(data.encode('utf-8'))
    elif algorithm == 'sha1':
        hash_obj = hashlib.sha1(data.encode('utf-8'))
    else:  # sha256
        hash_obj = hashlib.sha256(data.encode('utf-8'))
    
    hash_hex = hash_obj.hexdigest()
    return hash_hex[:length].upper()


# =============================================================================
# DATE AND TIME UTILITIES
# =============================================================================

def get_date_range(
    period_type: str,
    reference_date: date = None,
    offset: int = 0
) -> Tuple[date, date]:
    """
    Ottieni range date per periodo
    
    Args:
        period_type: Tipo periodo ('day', 'week', 'month', 'quarter', 'year')
        reference_date: Data di riferimento (None = oggi)
        offset: Offset periodi (-1 = periodo precedente, +1 = successivo)
        
    Returns:
        Tuple (data_inizio, data_fine)
    """
    if reference_date is None:
        reference_date = timezone.now().date()
    
    if period_type == 'day':
        target_date = reference_date + timedelta(days=offset)
        return target_date, target_date
    
    elif period_type == 'week':
        # Settimana dal lunedì alla domenica
        monday = reference_date - timedelta(days=reference_date.weekday())
        monday = monday + timedelta(weeks=offset)
        sunday = monday + timedelta(days=6)
        return monday, sunday
    
    elif period_type == 'month':
        # Primo e ultimo giorno del mese
        year = reference_date.year
        month = reference_date.month + offset
        
        # Gestisci overflow anno
        while month > 12:
            year += 1
            month -= 12
        while month < 1:
            year -= 1
            month += 12
        
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        return first_day, last_day
    
    elif period_type == 'quarter':
        # Trimestre
        quarter = (reference_date.month - 1) // 3 + 1 + offset
        year = reference_date.year
        
        while quarter > 4:
            year += 1
            quarter -= 4
        while quarter < 1:
            year -= 1
            quarter += 4
        
        first_month = (quarter - 1) * 3 + 1
        first_day = date(year, first_month, 1)
        
        last_month = first_month + 2
        last_day = date(year, last_month, calendar.monthrange(year, last_month)[1])
        
        return first_day, last_day
    
    elif period_type == 'year':
        year = reference_date.year + offset
        return date(year, 1, 1), date(year, 12, 31)
    
    else:
        raise ValueError(f"Tipo periodo non supportato: {period_type}")


def calculate_business_days(
    start_date: date,
    end_date: date,
    holidays: List[date] = None
) -> int:
    """
    Calcola giorni lavorativi tra due date
    
    Args:
        start_date: Data inizio
        end_date: Data fine
        holidays: Lista festività da escludere
        
    Returns:
        Numero giorni lavorativi
    """
    if holidays is None:
        holidays = []
    
    business_days = 0
    current = start_date
    
    while current <= end_date:
        # Lunedì = 0, Domenica = 6
        if current.weekday() < 5 and current not in holidays:
            business_days += 1
        current += timedelta(days=1)
    
    return business_days


def parse_flexible_date(date_str: str) -> Optional[date]:
    """
    Parse date da stringa con formati flessibili
    
    Args:
        date_str: Stringa data (es: "2024-03-15", "15/03/2024", "15-03-24")
        
    Returns:
        Oggetto date o None se non parsabile
    """
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    # Formati supportati
    formats = [
        '%Y-%m-%d',  # 2024-03-15
        '%d/%m/%Y',  # 15/03/2024
        '%d-%m-%Y',  # 15-03-2024
        '%d.%m.%Y',  # 15.03.2024
        '%d/%m/%y',  # 15/03/24
        '%d-%m-%y',  # 15-03-24
        '%Y/%m/%d',  # 2024/03/15
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    return None


def format_time_duration(seconds: int) -> str:
    """
    Formatta durata in formato leggibile
    
    Args:
        seconds: Secondi
        
    Returns:
        Stringa formattata (es: "2h 30m 45s")
    """
    if seconds < 0:
        return "0s"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


# =============================================================================
# FINANCIAL AND MATH UTILITIES
# =============================================================================

def calculate_vat(
    net_amount: Union[int, float, Decimal],
    vat_rate: Union[int, float, Decimal],
    precision: int = 2
) -> Dict[str, Decimal]:
    """
    Calcola IVA su importo
    
    Args:
        net_amount: Importo netto
        vat_rate: Aliquota IVA (es: 22 per 22%)
        precision: Precisione decimali
        
    Returns:
        Dict con 'net', 'vat', 'gross'
    """
    if isinstance(net_amount, (int, float)):
        net_amount = Decimal(str(net_amount))
    if isinstance(vat_rate, (int, float)):
        vat_rate = Decimal(str(vat_rate))
    
    vat_amount = (net_amount * vat_rate / Decimal('100')).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    gross_amount = net_amount + vat_amount
    
    return {
        'net': net_amount,
        'vat': vat_amount,
        'gross': gross_amount
    }


def calculate_discount(
    original_price: Union[int, float, Decimal],
    discount_percent: Union[int, float, Decimal] = None,
    discount_amount: Union[int, float, Decimal] = None
) -> Dict[str, Decimal]:
    """
    Calcola sconto su prezzo
    
    Args:
        original_price: Prezzo originale
        discount_percent: Sconto percentuale (es: 15 per 15%)
        discount_amount: Sconto fisso
        
    Returns:
        Dict con 'original', 'discount', 'final'
    """
    if isinstance(original_price, (int, float)):
        original_price = Decimal(str(original_price))
    
    if discount_percent is not None:
        discount_percent = Decimal(str(discount_percent))
        discount = (original_price * discount_percent / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
    elif discount_amount is not None:
        discount = Decimal(str(discount_amount))
    else:
        discount = Decimal('0')
    
    final_price = max(original_price - discount, Decimal('0'))
    
    return {
        'original': original_price,
        'discount': discount,
        'final': final_price
    }


def calculate_compound_interest(
    principal: Union[int, float, Decimal],
    rate: Union[int, float, Decimal],
    periods: int,
    compounding_frequency: int = 1
) -> Decimal:
    """
    Calcola interesse composto
    
    Args:
        principal: Capitale iniziale
        rate: Tasso interesse annuo (es: 5 per 5%)
        periods: Numero anni
        compounding_frequency: Frequenza capitalizzazione (1=annuale, 12=mensile)
        
    Returns:
        Montante finale
    """
    if isinstance(principal, (int, float)):
        principal = Decimal(str(principal))
    if isinstance(rate, (int, float)):
        rate = Decimal(str(rate))
    
    rate_decimal = rate / Decimal('100')
    
    # Formula interesse composto: A = P(1 + r/n)^(nt)
    factor = (Decimal('1') + rate_decimal / Decimal(str(compounding_frequency)))
    exponent = compounding_frequency * periods
    
    # Approssimazione per calcolo potenza con Decimal
    amount = principal
    for _ in range(exponent):
        amount *= factor
    
    return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def statistical_summary(values: List[Union[int, float, Decimal]]) -> Dict[str, Any]:
    """
    Calcola statistiche descrittive
    
    Args:
        values: Lista valori numerici
        
    Returns:
        Dict con statistiche
    """
    if not values:
        return {}
    
    # Converti in Decimal per precisione
    decimal_values = [Decimal(str(v)) for v in values if v is not None]
    
    if not decimal_values:
        return {}
    
    n = len(decimal_values)
    total = sum(decimal_values)
    mean = total / n
    
    # Mediana
    sorted_values = sorted(decimal_values)
    if n % 2 == 0:
        median = (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
    else:
        median = sorted_values[n//2]
    
    # Varianza e deviazione standard (approssimata)
    variance = sum((x - mean) ** 2 for x in decimal_values) / n
    std_dev = variance ** Decimal('0.5')
    
    return {
        'count': n,
        'sum': total,
        'mean': mean,
        'median': median,
        'min': min(decimal_values),
        'max': max(decimal_values),
        'variance': variance,
        'std_dev': std_dev,
        'range': max(decimal_values) - min(decimal_values)
    }


# =============================================================================
# NETWORK AND COMMUNICATION UTILITIES
# =============================================================================

def extract_domain_from_email(email: str) -> str:
    """
    Estrae dominio da indirizzo email
    
    Args:
        email: Indirizzo email
        
    Returns:
        Dominio o stringa vuota se non valido
    """
    try:
        validate_email(email)
        return email.split('@')[1].lower()
    except ValidationError:
        return ''


def normalize_phone_number(
    phone: str,
    country_code: str = '+39',
    remove_formatting: bool = True
) -> str:
    """
    Normalizza numero di telefono
    
    Args:
        phone: Numero telefono
        country_code: Prefisso paese
        remove_formatting: Rimuovi formattazione
        
    Returns:
        Numero normalizzato
    """
    if not phone:
        return ''
    
    # Rimuovi caratteri non numerici
    digits_only = re.sub(r'[^\d+]', '', phone)
    
    # Se inizia con 00, sostituisci con +
    if digits_only.startswith('00'):
        digits_only = '+' + digits_only[2:]
    
    # Se non ha prefisso internazionale, aggiungilo
    if not digits_only.startswith('+'):
        if country_code == '+39' and digits_only.startswith('0'):
            # Italia: rimuovi lo 0 iniziale
            digits_only = country_code + digits_only[1:]
        else:
            digits_only = country_code + digits_only
    
    if remove_formatting:
        return digits_only
    else:
        # Formattazione italiana basic
        if digits_only.startswith('+39'):
            clean = digits_only[3:]
            if len(clean) == 10:
                return f"+39 {clean[:3]} {clean[3:6]} {clean[6:]}"
            elif len(clean) == 9:
                return f"+39 {clean[:2]} {clean[2:5]} {clean[5:]}"
        
        return digits_only


def generate_slug(
    text: str,
    max_length: int = 50,
    allow_unicode: bool = False
) -> str:
    """
    Genera slug da testo
    
    Args:
        text: Testo di origine
        max_length: Lunghezza massima
        allow_unicode: Permetti caratteri unicode
        
    Returns:
        Slug generato
    """
    if not text:
        return ''
    
    # Converti in lowercase
    slug = text.lower()
    
    if not allow_unicode:
        # Rimuovi accenti
        slug = unicodedata.normalize('NFKD', slug)
        slug = ''.join(c for c in slug if not unicodedata.combining(c))
    
    # Sostituisci spazi e caratteri speciali con trattini
    slug = re.sub(r'[^\w\s-]' if allow_unicode else r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    
    # Rimuovi trattini iniziali/finali
    slug = slug.strip('-')
    
    # Limita lunghezza
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip('-')
    
    return slug or 'item'


# =============================================================================
# UTILITY HELPERS
# =============================================================================

def safe_division(numerator: Union[int, float, Decimal], 
                 denominator: Union[int, float, Decimal],
                 default: Any = 0) -> Any:
    """
    Divisione sicura che evita divisione per zero
    
    Args:
        numerator: Numeratore
        denominator: Denominatore
        default: Valore di default se denominatore = 0
        
    Returns:
        Risultato divisione o default
    """
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return default


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Divide lista in chunks di dimensione specifica
    
    Args:
        lst: Lista da dividere
        chunk_size: Dimensione chunk
        
    Returns:
        Lista di chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def flatten_dict(d: Dict[str, Any], separator: str = '.') -> Dict[str, Any]:
    """
    Appiattisce dizionario nidificato
    
    Args:
        d: Dizionario da appiattire
        separator: Separatore chiavi
        
    Returns:
        Dizionario appiattito
    """
    def _flatten(obj, parent_key=''):
        items = []
        for key, value in obj.items():
            new_key = f"{parent_key}{separator}{key}" if parent_key else key
            if isinstance(value, dict):
                items.extend(_flatten(value, new_key))
            else:
                items.append((new_key, value))
        return items
    
    return dict(_flatten(d))


def deep_merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge profondo di dizionari
    
    Args:
        *dicts: Dizionari da fare merge
        
    Returns:
        Dizionario merged
    """
    result = {}
    
    for d in dicts:
        for key, value in d.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge_dicts(result[key], value)
            else:
                result[key] = value
    
    return result


def retry_on_exception(
    func: Callable,
    max_attempts: int = 3,
    exceptions: Tuple = (Exception,),
    delay: float = 1.0
) -> Any:
    """
    Retry funzione in caso di eccezione
    
    Args:
        func: Funzione da eseguire
        max_attempts: Numero massimo tentativi
        exceptions: Tuple eccezioni da intercettare
        delay: Delay tra tentativi (secondi)
        
    Returns:
        Risultato funzione
    """
    import time
    
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            if attempt < max_attempts - 1:
                logger.warning(f"Tentativo {attempt + 1} fallito: {e}. Retry in {delay}s")
                time.sleep(delay)
            else:
                logger.error(f"Tutti i tentativi falliti. Ultima eccezione: {e}")
    
    raise last_exception