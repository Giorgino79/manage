"""
CORE FILE UTILITIES - Sistema Universale Gestione File
=====================================================

Funzioni complete per gestione file e documenti:
- 📁 Upload e validazione file sicura
- 🖼️ Manipolazione immagini (resize, watermark)
- 📎 Compressione e archivi (ZIP, TAR)
- 🔒 Validazione tipi MIME sicura
- 📊 Conversioni formato automatiche
- 💾 Gestione storage ottimizzata

Caratteristiche:
- Zero dipendenze da app specifiche
- Validazione sicurezza file upload
- Gestione errori robusta
- Performance ottimizzate
- Supporto cloud storage
- Logging completo operazioni

Versione: 1.0
Compatibilità: Django 3.2+, Python 3.8+
"""

import os
import shutil
import tempfile
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple, BinaryIO
from dataclasses import dataclass, field
from datetime import datetime
import logging
import zipfile
import tarfile

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from django.http import HttpResponse, Http404

# Optional dependencies
try:
    from PIL import Image, ImageOps, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION CLASSES
# =============================================================================

@dataclass
class FileConfig:
    """Configurazione gestione file"""
    # Upload limits
    max_file_size: int = 10 * 1024 * 1024  # 10MB default
    allowed_extensions: List[str] = field(default_factory=lambda: [
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp',
        '.txt', '.rtf', '.zip', '.rar'
    ])
    allowed_mimes: List[str] = field(default_factory=lambda: [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/csv',
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/bmp',
        'text/plain',
        'application/zip'
    ])
    
    # Security
    scan_for_viruses: bool = False
    quarantine_suspicious: bool = True
    
    # Storage
    storage_path: str = 'uploads'
    organize_by_date: bool = True
    preserve_filename: bool = True
    
    # Processing
    auto_optimize_images: bool = True
    generate_thumbnails: bool = True
    thumbnail_sizes: List[Tuple[int, int]] = field(default_factory=lambda: [
        (150, 150), (300, 300), (800, 600)
    ])


@dataclass 
class ImageConfig:
    """Configurazione manipolazione immagini"""
    # Quality
    quality: int = 85
    format: str = 'JPEG'  # JPEG, PNG, WEBP
    
    # Resize
    max_width: int = 1920
    max_height: int = 1080
    maintain_aspect: bool = True
    
    # Optimization
    optimize: bool = True
    progressive: bool = True
    
    # Watermark
    watermark_text: str = None
    watermark_position: str = 'bottom-right'  # bottom-right, center, etc.
    watermark_opacity: float = 0.3


@dataclass
class ArchiveConfig:
    """Configurazione creazione archivi"""
    format: str = 'zip'  # zip, tar, tar.gz, tar.bz2
    compression_level: int = 6  # 0-9 for zip
    include_hidden: bool = False
    exclude_patterns: List[str] = field(default_factory=lambda: [
        '*.tmp', '*.log', '.DS_Store', 'Thumbs.db'
    ])


# =============================================================================
# FILE UPLOAD AND VALIDATION
# =============================================================================

def validate_and_store_file(
    file_obj: BinaryIO,
    filename: str,
    config: FileConfig = None,
    subfolder: str = None,
    custom_name: str = None
) -> Dict[str, Any]:
    """
    Valida e memorizza file upload in modo sicuro
    
    Args:
        file_obj: File object da Django
        filename: Nome file originale
        config: Configurazione validazione
        subfolder: Sottocartella di destinazione
        custom_name: Nome personalizzato (None = auto-generate)
        
    Returns:
        Dict con path, url, metadata del file salvato
    """
    if config is None:
        config = FileConfig()
    
    result = {
        'success': False,
        'file_path': None,
        'file_url': None,
        'original_name': filename,
        'size': 0,
        'mime_type': None,
        'errors': []
    }
    
    try:
        # Validazione sicurezza
        validation = _validate_file_security(file_obj, filename, config)
        if not validation['valid']:
            result['errors'] = validation['errors']
            return result
        
        # Determina path di destinazione
        if config.organize_by_date:
            date_path = timezone.now().strftime('%Y/%m/%d')
            base_path = os.path.join(config.storage_path, date_path)
        else:
            base_path = config.storage_path
        
        if subfolder:
            base_path = os.path.join(base_path, subfolder)
        
        # Nome file finale
        if custom_name:
            final_name = custom_name
        elif config.preserve_filename:
            final_name = _sanitize_filename(filename)
        else:
            ext = os.path.splitext(filename)[1]
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            final_name = f"file_{timestamp}{ext}"
        
        # Ensure unique filename
        final_path = os.path.join(base_path, final_name)
        final_path = _ensure_unique_path(final_path)
        
        # Salva file
        file_content = ContentFile(file_obj.read())
        saved_path = default_storage.save(final_path, file_content)
        
        # Metadata
        file_obj.seek(0, 2)  # End of file
        file_size = file_obj.tell()
        
        result.update({
            'success': True,
            'file_path': saved_path,
            'file_url': default_storage.url(saved_path),
            'size': file_size,
            'mime_type': validation['mime_type'],
            'hash': validation.get('hash'),
        })
        
        # Post-processing per immagini
        if validation['mime_type'].startswith('image/') and config.auto_optimize_images:
            _post_process_image(saved_path, config)
        
        logger.info(f"File salvato: {saved_path} ({file_size} bytes)")
        
    except Exception as e:
        result['errors'].append(f"Errore salvataggio file: {str(e)}")
        logger.error(f"Errore upload file {filename}: {e}")
    
    return result


def _validate_file_security(
    file_obj: BinaryIO, 
    filename: str, 
    config: FileConfig
) -> Dict[str, Any]:
    """Validazione sicurezza file upload"""
    
    result = {
        'valid': False,
        'mime_type': None,
        'errors': [],
        'hash': None
    }
    
    # Dimensione file
    file_obj.seek(0, 2)  # End of file
    file_size = file_obj.tell()
    file_obj.seek(0)  # Reset
    
    if file_size > config.max_file_size:
        result['errors'].append(f"File troppo grande: {file_size} bytes (max: {config.max_file_size})")
        return result
    
    if file_size == 0:
        result['errors'].append("File vuoto")
        return result
    
    # Estensione
    _, ext = os.path.splitext(filename.lower())
    if ext not in config.allowed_extensions:
        result['errors'].append(f"Estensione non consentita: {ext}")
        return result
    
    # MIME type (controllo sui primi bytes)
    file_obj.seek(0)
    file_header = file_obj.read(1024)
    file_obj.seek(0)
    
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type:
        # Try to detect from content
        mime_type = _detect_mime_from_content(file_header)
    
    if mime_type not in config.allowed_mimes:
        result['errors'].append(f"Tipo file non consentito: {mime_type}")
        return result
    
    # Hash per controlli duplicati
    content = file_obj.read()
    file_obj.seek(0)
    file_hash = hashlib.sha256(content).hexdigest()
    
    # Controlli specifici per tipo file
    security_check = _perform_content_security_checks(content, mime_type)
    if not security_check['safe']:
        result['errors'].extend(security_check['issues'])
        return result
    
    result.update({
        'valid': True,
        'mime_type': mime_type,
        'hash': file_hash
    })
    
    return result


def _detect_mime_from_content(content: bytes) -> str:
    """Rileva MIME type da content bytes"""
    
    # Signatures comuni
    signatures = {
        b'\xff\xd8\xff': 'image/jpeg',
        b'\x89PNG\r\n\x1a\n': 'image/png',
        b'GIF87a': 'image/gif',
        b'GIF89a': 'image/gif',
        b'%PDF': 'application/pdf',
        b'PK\x03\x04': 'application/zip',
        b'PK\x05\x06': 'application/zip',
        b'PK\x07\x08': 'application/zip'
    }
    
    for sig, mime in signatures.items():
        if content.startswith(sig):
            return mime
    
    return 'application/octet-stream'


def _perform_content_security_checks(content: bytes, mime_type: str) -> Dict[str, Any]:
    """Controlli sicurezza sul contenuto file"""
    
    result = {'safe': True, 'issues': []}
    
    # Check for embedded executables in images
    if mime_type.startswith('image/'):
        # Look for suspicious patterns
        dangerous_patterns = [
            b'MZ',  # PE executable
            b'\x7fELF',  # ELF executable
            b'#!/',  # Script shebang
        ]
        
        for pattern in dangerous_patterns:
            if pattern in content:
                result['safe'] = False
                result['issues'].append("Possibile file eseguibile incorporato")
                break
    
    # Check for script injection in text files
    if mime_type.startswith('text/'):
        script_patterns = [
            b'<script',
            b'javascript:',
            b'vbscript:',
        ]
        
        content_lower = content.lower()
        for pattern in script_patterns:
            if pattern in content_lower:
                result['safe'] = False
                result['issues'].append("Possibile codice script pericoloso")
                break
    
    return result


# =============================================================================
# IMAGE PROCESSING
# =============================================================================

def process_image(
    image_path: str,
    config: ImageConfig = None,
    operations: List[str] = None
) -> Dict[str, Any]:
    """
    Elabora immagine con varie operazioni
    
    Args:
        image_path: Percorso immagine
        config: Configurazione elaborazione
        operations: Lista operazioni da eseguire
        
    Returns:
        Dict con risultati elaborazione
    """
    if not PIL_AVAILABLE:
        return {'success': False, 'error': 'PIL non disponibile'}
    
    if config is None:
        config = ImageConfig()
    
    if operations is None:
        operations = ['optimize', 'resize']
    
    result = {
        'success': False,
        'original_size': None,
        'new_size': None,
        'thumbnails': [],
        'optimized_path': None
    }
    
    try:
        # Carica immagine
        with Image.open(image_path) as img:
            result['original_size'] = img.size
            
            # Converti in RGB se necessario
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Operazioni
            if 'resize' in operations:
                img = _resize_image(img, config)
            
            if 'watermark' in operations and config.watermark_text:
                img = _add_watermark(img, config)
            
            if 'optimize' in operations:
                optimized_path = _save_optimized_image(img, image_path, config)
                result['optimized_path'] = optimized_path
            
            result['new_size'] = img.size
            result['success'] = True
            
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Errore elaborazione immagine {image_path}: {e}")
    
    return result


def _resize_image(img: Image.Image, config: ImageConfig) -> Image.Image:
    """Ridimensiona immagine mantenendo proporzioni"""
    
    width, height = img.size
    max_w, max_h = config.max_width, config.max_height
    
    if width <= max_w and height <= max_h:
        return img
    
    if config.maintain_aspect:
        # Calcola scala mantenendo aspect ratio
        scale_w = max_w / width
        scale_h = max_h / height
        scale = min(scale_w, scale_h)
        
        new_width = int(width * scale)
        new_height = int(height * scale)
    else:
        new_width, new_height = max_w, max_h
    
    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)


def _add_watermark(img: Image.Image, config: ImageConfig) -> Image.Image:
    """Aggiunge watermark all'immagine"""
    
    # Crea layer per watermark
    watermark = Image.new('RGBA', img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(watermark)
    
    # Font (usa default se non disponibile font custom)
    try:
        font_size = max(img.size) // 20  # Dynamic font size
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # Posizione watermark
    text_bbox = draw.textbbox((0, 0), config.watermark_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    margin = 20
    if config.watermark_position == 'bottom-right':
        x = img.size[0] - text_width - margin
        y = img.size[1] - text_height - margin
    elif config.watermark_position == 'center':
        x = (img.size[0] - text_width) // 2
        y = (img.size[1] - text_height) // 2
    else:  # bottom-left
        x = margin
        y = img.size[1] - text_height - margin
    
    # Colore con opacità
    alpha = int(255 * config.watermark_opacity)
    text_color = (255, 255, 255, alpha)
    
    draw.text((x, y), config.watermark_text, font=font, fill=text_color)
    
    # Combina immagini
    return Image.alpha_composite(img.convert('RGBA'), watermark).convert('RGB')


def _save_optimized_image(img: Image.Image, original_path: str, config: ImageConfig) -> str:
    """Salva immagine ottimizzata"""
    
    # Genera nome file ottimizzato
    base, ext = os.path.splitext(original_path)
    optimized_path = f"{base}_optimized{ext}"
    
    # Parametri salvataggio
    save_kwargs = {
        'format': config.format,
        'optimize': config.optimize,
        'quality': config.quality
    }
    
    if config.format == 'JPEG' and config.progressive:
        save_kwargs['progressive'] = True
    
    img.save(optimized_path, **save_kwargs)
    return optimized_path


def generate_thumbnails(
    image_path: str, 
    sizes: List[Tuple[int, int]] = None
) -> List[Dict[str, Any]]:
    """Genera thumbnails di varie dimensioni"""
    
    if not PIL_AVAILABLE:
        return []
    
    if sizes is None:
        sizes = [(150, 150), (300, 300)]
    
    thumbnails = []
    
    try:
        with Image.open(image_path) as img:
            base, ext = os.path.splitext(image_path)
            
            for width, height in sizes:
                # Crea thumbnail mantenendo proporzioni
                thumb = img.copy()
                thumb.thumbnail((width, height), Image.Resampling.LANCZOS)
                
                # Salva thumbnail
                thumb_path = f"{base}_thumb_{width}x{height}{ext}"
                thumb.save(thumb_path, optimize=True, quality=85)
                
                thumbnails.append({
                    'size': f"{width}x{height}",
                    'path': thumb_path,
                    'actual_size': thumb.size
                })
                
    except Exception as e:
        logger.error(f"Errore generazione thumbnails {image_path}: {e}")
    
    return thumbnails


# =============================================================================
# ARCHIVE UTILITIES
# =============================================================================

def create_archive(
    source_paths: List[str],
    archive_name: str,
    config: ArchiveConfig = None,
    base_path: str = None
) -> str:
    """
    Crea archivio da lista di file/cartelle
    
    Args:
        source_paths: Lista percorsi da includere
        archive_name: Nome archivio di output
        config: Configurazione archivio
        base_path: Percorso base per relativizzare paths
        
    Returns:
        Percorso archivio creato
    """
    if config is None:
        config = ArchiveConfig()
    
    if config.format == 'zip':
        return _create_zip_archive(source_paths, archive_name, config, base_path)
    elif config.format.startswith('tar'):
        return _create_tar_archive(source_paths, archive_name, config, base_path)
    else:
        raise ValueError(f"Formato archivio non supportato: {config.format}")


def _create_zip_archive(
    source_paths: List[str],
    archive_name: str,
    config: ArchiveConfig,
    base_path: str
) -> str:
    """Crea archivio ZIP"""
    
    if not archive_name.endswith('.zip'):
        archive_name += '.zip'
    
    with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED, 
                        compresslevel=config.compression_level) as zf:
        
        for source in source_paths:
            if os.path.isfile(source):
                # Single file
                if _should_include_file(source, config):
                    arcname = os.path.relpath(source, base_path) if base_path else os.path.basename(source)
                    zf.write(source, arcname)
            
            elif os.path.isdir(source):
                # Directory
                for root, dirs, files in os.walk(source):
                    # Filter directories
                    if not config.include_hidden:
                        dirs[:] = [d for d in dirs if not d.startswith('.')]
                    
                    for file in files:
                        if not config.include_hidden and file.startswith('.'):
                            continue
                        
                        file_path = os.path.join(root, file)
                        if _should_include_file(file_path, config):
                            if base_path:
                                arcname = os.path.relpath(file_path, base_path)
                            else:
                                arcname = os.path.relpath(file_path, source)
                            zf.write(file_path, arcname)
    
    return archive_name


def _create_tar_archive(
    source_paths: List[str],
    archive_name: str,
    config: ArchiveConfig,
    base_path: str
) -> str:
    """Crea archivio TAR"""
    
    # Determina modalità
    if config.format == 'tar.gz':
        mode = 'w:gz'
        if not archive_name.endswith('.tar.gz'):
            archive_name += '.tar.gz'
    elif config.format == 'tar.bz2':
        mode = 'w:bz2'
        if not archive_name.endswith('.tar.bz2'):
            archive_name += '.tar.bz2'
    else:  # tar
        mode = 'w'
        if not archive_name.endswith('.tar'):
            archive_name += '.tar'
    
    with tarfile.open(archive_name, mode) as tf:
        for source in source_paths:
            if _should_include_file(source, config):
                arcname = os.path.relpath(source, base_path) if base_path else os.path.basename(source)
                tf.add(source, arcname)
    
    return archive_name


def extract_archive(
    archive_path: str,
    extract_to: str,
    password: str = None
) -> Dict[str, Any]:
    """
    Estrae archivio
    
    Returns:
        Dict con risultati estrazione
    """
    result = {
        'success': False,
        'extracted_files': [],
        'errors': []
    }
    
    try:
        os.makedirs(extract_to, exist_ok=True)
        
        if archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zf:
                if password:
                    zf.setpassword(password.encode())
                zf.extractall(extract_to)
                result['extracted_files'] = zf.namelist()
        
        elif any(archive_path.endswith(ext) for ext in ['.tar', '.tar.gz', '.tar.bz2']):
            with tarfile.open(archive_path, 'r:*') as tf:
                tf.extractall(extract_to)
                result['extracted_files'] = tf.getnames()
        
        else:
            result['errors'].append(f"Formato archivio non supportato: {archive_path}")
            return result
        
        result['success'] = True
        
    except Exception as e:
        result['errors'].append(str(e))
        logger.error(f"Errore estrazione {archive_path}: {e}")
    
    return result


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _sanitize_filename(filename: str) -> str:
    """Sanifica nome file per sicurezza"""
    # Rimuovi caratteri pericolosi
    dangerous_chars = '<>:"/\\|?*'
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # Limita lunghezza
    name, ext = os.path.splitext(filename)
    if len(name) > 100:
        name = name[:100]
    
    return name + ext


def _ensure_unique_path(path: str) -> str:
    """Assicura che il path sia unico"""
    if not default_storage.exists(path):
        return path
    
    base, ext = os.path.splitext(path)
    counter = 1
    
    while True:
        new_path = f"{base}_{counter}{ext}"
        if not default_storage.exists(new_path):
            return new_path
        counter += 1


def _should_include_file(file_path: str, config: ArchiveConfig) -> bool:
    """Verifica se file deve essere incluso nell'archivio"""
    filename = os.path.basename(file_path)
    
    # Check exclude patterns
    for pattern in config.exclude_patterns:
        if filename.lower().endswith(pattern.lower().replace('*', '')):
            return False
    
    return True


def _post_process_image(image_path: str, config: FileConfig):
    """Post-processing automatico immagini"""
    if PIL_AVAILABLE and config.auto_optimize_images:
        img_config = ImageConfig()
        process_image(image_path, img_config, ['optimize', 'resize'])
    
    if config.generate_thumbnails:
        generate_thumbnails(image_path, config.thumbnail_sizes)


def get_file_info(file_path: str) -> Dict[str, Any]:
    """Ottieni informazioni dettagliate su file"""
    
    if not os.path.exists(file_path):
        return {'exists': False}
    
    stat = os.stat(file_path)
    
    info = {
        'exists': True,
        'size': stat.st_size,
        'created': datetime.fromtimestamp(stat.st_ctime),
        'modified': datetime.fromtimestamp(stat.st_mtime),
        'is_file': os.path.isfile(file_path),
        'is_dir': os.path.isdir(file_path),
        'extension': os.path.splitext(file_path)[1].lower(),
        'mime_type': mimetypes.guess_type(file_path)[0]
    }
    
    # Hash file se non troppo grande
    if info['is_file'] and info['size'] < 50 * 1024 * 1024:  # 50MB
        with open(file_path, 'rb') as f:
            info['hash'] = hashlib.sha256(f.read()).hexdigest()
    
    return info


def cleanup_temp_files(older_than_hours: int = 24):
    """Pulisce file temporanei vecchi"""
    temp_dir = getattr(settings, 'TEMP_DIR', tempfile.gettempdir())
    cutoff_time = timezone.now().timestamp() - (older_than_hours * 3600)
    
    cleaned_count = 0
    
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                if os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)
                    cleaned_count += 1
            except OSError:
                pass
    
    logger.info(f"Pulizia temp: rimossi {cleaned_count} file")
    return cleaned_count