"""
CORE CSV GENERATOR - Sistema Universale Generazione CSV
=====================================================

Funzioni complete per generazione CSV con multiple opzioni:
- 📊 CSV standard con encoding sicuro
- 🔄 Import/Export bidirezionale
- 🎨 Formattazione automatica dati
- 📱 Gestione encoding (UTF-8, ISO, Windows)
- 🔍 Validazione e sanificazione dati

Caratteristiche:
- Zero dipendenze da app specifiche
- Gestione encoding automatica
- Delimitatori personalizzabili
- Quote handling intelligente
- Performance ottimizzate per grandi dataset
- Output flessibile (file, buffer, response)

Versione: 1.0
Compatibilità: Django 3.2+, Python 3.8+
"""

import csv
import os
import tempfile
from io import StringIO, BytesIO
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
import logging
import chardet

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION CLASSES
# =============================================================================

@dataclass
class CSVConfig:
    """Configurazione completa per generazione CSV"""
    # Output
    filename: str = "export.csv"
    
    # Encoding
    encoding: str = 'utf-8-sig'  # utf-8-sig aggiunge BOM per Excel
    
    # CSV Format
    delimiter: str = ','
    quotechar: str = '"'
    quoting: int = csv.QUOTE_MINIMAL  # QUOTE_ALL, QUOTE_MINIMAL, QUOTE_NONNUMERIC, QUOTE_NONE
    lineterminator: str = '\r\n'  # Windows style per compatibilità Excel
    
    # Headers
    include_headers: bool = True
    headers_list: List[str] = None
    
    # Data formatting
    date_format: str = '%d/%m/%Y'
    datetime_format: str = '%d/%m/%Y %H:%M'
    decimal_separator: str = ','  # Italiano: virgola
    thousands_separator: str = '.'  # Italiano: punto
    
    # Advanced options
    escape_formulas: bool = True  # Previene formula injection
    max_field_size: int = 131072  # Limite dimensione campo
    dialect_name: str = 'excel'  # excel, excel-tab, unix


@dataclass
class ImportConfig:
    """Configurazione per importazione CSV"""
    # Detection
    auto_detect_encoding: bool = True
    auto_detect_delimiter: bool = True
    
    # Parsing
    skip_blank_lines: bool = True
    skip_initial_space: bool = True
    has_headers: bool = True
    header_row: int = 0  # Riga headers (0-based)
    
    # Data types
    auto_convert_types: bool = True
    date_formats: List[str] = field(default_factory=lambda: [
        '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y'
    ])
    
    # Validation
    max_rows: int = None
    required_columns: List[str] = None
    column_mapping: Dict[str, str] = None  # {csv_column: target_field}


# =============================================================================
# MAIN CSV GENERATION FUNCTIONS
# =============================================================================

def generate_csv_from_data(
    data: Union[List[Dict], List[List], Any],
    columns: List[str] = None,
    config: CSVConfig = None,
    output_type: str = 'response',  # 'response', 'file', 'buffer'
    output_path: str = None
) -> Union[HttpResponse, StringIO, str]:
    """
    Genera CSV da dati strutturati
    
    Args:
        data: Dati da esportare (lista dict, lista liste)
        columns: Lista colonne da includere (None = tutte)
        config: Configurazione CSV
        output_type: Tipo output ('response', 'file', 'buffer')
        output_path: Percorso file per output='file'
        
    Returns:
        HttpResponse, StringIO o str (percorso file)
    """
    if config is None:
        config = CSVConfig()
    
    # Converti data in formato uniforme
    csv_data, headers = _prepare_data_for_csv(data, columns, config)
    
    # Crea CSV
    if output_type == 'buffer':
        output = StringIO()
        _write_csv_data(output, csv_data, headers, config)
        output.seek(0)
        return output
    
    elif output_type == 'file':
        if not output_path:
            output_path = _generate_temp_filename(config.filename)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding=config.encoding, newline='') as file:
            _write_csv_data(file, csv_data, headers, config)
        
        return output_path
    
    else:  # response
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{config.filename}"'
        
        # Per response usiamo StringIO poi scriviamo tutto
        buffer = StringIO()
        _write_csv_data(buffer, csv_data, headers, config)
        
        # Scrivi nel response con encoding corretto
        csv_content = buffer.getvalue()
        response.write(csv_content.encode(config.encoding))
        
        return response


def import_csv_from_file(
    file_path: str = None,
    file_content: str = None,
    config: ImportConfig = None
) -> Dict[str, Any]:
    """
    Importa dati da file CSV
    
    Args:
        file_path: Percorso file CSV
        file_content: Contenuto CSV come stringa
        config: Configurazione import
        
    Returns:
        Dict con 'data', 'headers', 'stats', 'errors'
    """
    if config is None:
        config = ImportConfig()
    
    result = {
        'data': [],
        'headers': [],
        'stats': {},
        'errors': []
    }
    
    try:
        # Ottieni contenuto
        if file_path:
            content, detected_encoding = _read_csv_file_with_encoding(file_path, config)
        elif file_content:
            content = file_content
            detected_encoding = 'utf-8'
        else:
            raise ValueError("file_path o file_content richiesto")
        
        # Rileva delimiter
        delimiter = _detect_delimiter(content) if config.auto_detect_delimiter else ','
        
        # Parse CSV
        reader_config = _get_csv_reader_config(delimiter, config)
        lines = content.splitlines()
        
        if not lines:
            result['errors'].append("File CSV vuoto")
            return result
        
        # Setup reader
        reader = csv.reader(lines, **reader_config)
        
        # Headers
        if config.has_headers:
            try:
                # Skip to header row
                for _ in range(config.header_row):
                    next(reader)
                headers = next(reader)
                result['headers'] = [h.strip() for h in headers]
            except StopIteration:
                result['errors'].append("Impossibile leggere headers")
                return result
        else:
            # Genera headers automatici
            first_row = next(reader, [])
            result['headers'] = [f"Colonna_{i+1}" for i in range(len(first_row))]
            # Rewind per includere prima riga nei dati
            reader = csv.reader(lines, **reader_config)
        
        # Valida headers richieste
        if config.required_columns:
            missing = set(config.required_columns) - set(result['headers'])
            if missing:
                result['errors'].append(f"Colonne mancanti: {', '.join(missing)}")
                return result
        
        # Leggi dati
        row_count = 0
        error_count = 0
        
        for row_num, row in enumerate(reader, start=config.header_row + 2):
            if config.max_rows and row_count >= config.max_rows:
                break
            
            if config.skip_blank_lines and not any(cell.strip() for cell in row):
                continue
            
            try:
                # Padding row se necessario
                while len(row) < len(result['headers']):
                    row.append('')
                
                # Converti tipi se richiesto
                if config.auto_convert_types:
                    row = _convert_row_types(row, config)
                
                # Applica column mapping se presente
                if config.column_mapping:
                    row_dict = dict(zip(result['headers'], row))
                    mapped_dict = {}
                    for csv_col, target_field in config.column_mapping.items():
                        if csv_col in row_dict:
                            mapped_dict[target_field] = row_dict[csv_col]
                    result['data'].append(mapped_dict)
                else:
                    result['data'].append(dict(zip(result['headers'], row)))
                
                row_count += 1
                
            except Exception as e:
                error_count += 1
                result['errors'].append(f"Errore riga {row_num}: {str(e)}")
        
        # Stats
        result['stats'] = {
            'total_rows': row_count,
            'error_count': error_count,
            'detected_encoding': detected_encoding,
            'delimiter': delimiter,
            'columns_count': len(result['headers'])
        }
        
    except Exception as e:
        result['errors'].append(f"Errore generale import: {str(e)}")
        logger.error(f"Errore import CSV: {e}")
    
    return result


# =============================================================================
# DATA PREPARATION AND FORMATTING
# =============================================================================

def _prepare_data_for_csv(
    data: Any, 
    columns: List[str], 
    config: CSVConfig
) -> Tuple[List[List], List[str]]:
    """Prepara dati per scrittura CSV"""
    
    if not data:
        return [], []
    
    # Determina headers
    if config.include_headers:
        if config.headers_list:
            headers = config.headers_list
        elif columns:
            headers = columns
        elif isinstance(data[0], dict):
            headers = list(data[0].keys())
        else:
            headers = [f"Colonna_{i+1}" for i in range(len(data[0]))]
    else:
        headers = []
    
    # Converti dati in righe
    rows = []
    
    for item in data:
        if isinstance(item, dict):
            # Dict to row
            if columns:
                row = [item.get(col, '') for col in columns]
            else:
                row = list(item.values())
        elif isinstance(item, (list, tuple)):
            # Already a row
            row = list(item)
        else:
            # Single value
            row = [item]
        
        # Formatta valori
        formatted_row = []
        for value in row:
            formatted_value = _format_csv_value(value, config)
            formatted_row.append(formatted_value)
        
        rows.append(formatted_row)
    
    return rows, headers


def _format_csv_value(value: Any, config: CSVConfig) -> str:
    """Formatta singolo valore per CSV"""
    if value is None:
        return ""
    
    if isinstance(value, bool):
        return "Sì" if value else "No"
    
    if isinstance(value, date):
        return value.strftime(config.date_format)
    
    if isinstance(value, datetime):
        return value.strftime(config.datetime_format)
    
    if isinstance(value, (int, float, Decimal)):
        # Formato numerico italiano
        str_value = str(value)
        if config.decimal_separator != '.':
            str_value = str_value.replace('.', config.decimal_separator)
        return str_value
    
    # String
    str_value = str(value)
    
    # Escape formulas per sicurezza
    if config.escape_formulas:
        str_value = _escape_csv_formula(str_value)
    
    return str_value


def _escape_csv_formula(value: str) -> str:
    """Previene formula injection in CSV"""
    if value.startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def _write_csv_data(output, rows: List[List], headers: List[str], config: CSVConfig):
    """Scrive dati CSV nel file/buffer"""
    
    # Configura CSV writer
    writer_config = {
        'delimiter': config.delimiter,
        'quotechar': config.quotechar,
        'quoting': config.quoting,
        'lineterminator': config.lineterminator
    }
    
    if config.dialect_name != 'custom':
        writer = csv.writer(output, dialect=config.dialect_name, **writer_config)
    else:
        writer = csv.writer(output, **writer_config)
    
    # Scrivi headers
    if config.include_headers and headers:
        writer.writerow(headers)
    
    # Scrivi dati
    for row in rows:
        writer.writerow(row)


# =============================================================================
# IMPORT UTILITIES
# =============================================================================

def _read_csv_file_with_encoding(file_path: str, config: ImportConfig) -> Tuple[str, str]:
    """Legge file CSV rilevando encoding"""
    
    if config.auto_detect_encoding:
        # Rileva encoding
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            detected = chardet.detect(raw_data)
            encoding = detected.get('encoding', 'utf-8')
    else:
        encoding = 'utf-8'
    
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        return content, encoding
    except UnicodeDecodeError:
        # Fallback a latin-1
        with open(file_path, 'r', encoding='latin-1') as f:
            content = f.read()
        return content, 'latin-1'


def _detect_delimiter(content: str) -> str:
    """Rileva delimiter CSV"""
    sample = content[:1024]  # Primi 1KB
    sniffer = csv.Sniffer()
    
    try:
        dialect = sniffer.sniff(sample, delimiters=',;|\t')
        return dialect.delimiter
    except:
        # Default comma
        return ','


def _get_csv_reader_config(delimiter: str, config: ImportConfig) -> Dict:
    """Configurazione per CSV reader"""
    return {
        'delimiter': delimiter,
        'quotechar': '"',
        'skipinitialspace': config.skip_initial_space
    }


def _convert_row_types(row: List[str], config: ImportConfig) -> List[Any]:
    """Converti tipi di dato automaticamente"""
    converted = []
    
    for value in row:
        value = value.strip()
        
        if not value:
            converted.append(None)
            continue
        
        # Try number
        if value.replace('.', '').replace(',', '').replace('-', '').replace('+', '').isdigit():
            try:
                # Gestisci formato italiano
                if ',' in value and '.' in value:
                    # Es: 1.234,56
                    value = value.replace('.', '').replace(',', '.')
                elif ',' in value:
                    # Es: 123,45
                    value = value.replace(',', '.')
                
                if '.' in value:
                    converted.append(float(value))
                else:
                    converted.append(int(value))
                continue
            except:
                pass
        
        # Try date
        for date_fmt in config.date_formats:
            try:
                date_obj = datetime.strptime(value, date_fmt).date()
                converted.append(date_obj)
                break
            except:
                continue
        else:
            # String
            converted.append(value)
    
    return converted


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _generate_temp_filename(base_filename: str) -> str:
    """Genera percorso file temporaneo"""
    temp_dir = getattr(settings, 'TEMP_DIR', tempfile.gettempdir())
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    name, ext = os.path.splitext(base_filename)
    filename = f"{name}_{timestamp}{ext}"
    return os.path.join(temp_dir, 'csv', filename)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def export_simple_csv(
    data: List[Dict],
    filename: str = 'export.csv',
    columns: List[str] = None,
    output_type: str = 'response'
):
    """Funzione convenienza per CSV semplice"""
    config = CSVConfig(filename=filename)
    
    return generate_csv_from_data(
        data=data,
        columns=columns,
        config=config,
        output_type=output_type
    )


def export_csv_italian_format(
    data: List[Dict],
    filename: str = 'export.csv',
    output_type: str = 'response'
):
    """Funzione convenienza per CSV formato italiano"""
    config = CSVConfig(
        filename=filename,
        delimiter=';',  # Excel italiano usa ;
        decimal_separator=',',
        date_format='%d/%m/%Y'
    )
    
    return generate_csv_from_data(
        data=data,
        config=config,
        output_type=output_type
    )


def import_csv_simple(file_path: str) -> List[Dict]:
    """Funzione convenienza per import CSV semplice"""
    result = import_csv_from_file(file_path)
    
    if result['errors']:
        logger.warning(f"Errori import CSV: {result['errors']}")
    
    return result['data']


def csv_to_excel_format(csv_data: List[Dict]) -> List[Dict]:
    """Converte dati CSV per compatibilità Excel"""
    # Questa funzione può essere usata per preparare dati
    # prima di passarli all'excel_generator
    converted = []
    
    for row in csv_data:
        converted_row = {}
        for key, value in row.items():
            # Converti None in stringa vuota
            if value is None:
                converted_row[key] = ""
            # Converti booleani in testo
            elif isinstance(value, bool):
                converted_row[key] = "Sì" if value else "No"
            else:
                converted_row[key] = value
        converted.append(converted_row)
    
    return converted