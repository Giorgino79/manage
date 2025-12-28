"""
CORE PDF GENERATOR - Sistema Universale Generazione PDF
======================================================

Funzioni complete per generazione PDF con multiple librerie:
- 📄 xhtml2pdf (HTML to PDF con CSS)
- 📊 reportlab (PDF programmatici e tabelle)
- 🎨 Template system integrato con Django
- 📱 Responsive design e layout professionali

Caratteristiche:
- Zero dipendenze da app specifiche
- Configurazione completa (margini, font, header/footer)
- Gestione risorse statiche automatica
- Error handling robusto
- Output flessibile (file, buffer, response)

Versione: 1.0
Compatibilità: Django 3.2+, Python 3.8+
"""

import os
import tempfile
from io import BytesIO
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import logging

from django.conf import settings
from django.template.loader import render_to_string, get_template
from django.http import HttpResponse
from django.contrib.staticfiles import finders
from django.utils import timezone
from django.utils.html import strip_tags

# PDF Libraries
try:
    import xhtml2pdf.pisa as pisa
    XHTML2PDF_AVAILABLE = True
except ImportError:
    XHTML2PDF_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import A4, LETTER, landscape, portrait
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import black, gray, white
    from reportlab.lib.units import mm, cm, inch
    from reportlab.lib import colors
    from reportlab.graphics.shapes import Drawing, Rect
    from reportlab.platypus.frames import Frame
    from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Temporarily disabled due to system library issues
# try:
#     from weasyprint import HTML, CSS
#     WEASYPRINT_AVAILABLE = True
# except ImportError:
#     WEASYPRINT_AVAILABLE = False
WEASYPRINT_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION CLASSES
# =============================================================================

@dataclass
class PDFConfig:
    """Configurazione completa per generazione PDF"""
    # Layout
    page_size: str = "A4"  # A4, LETTER, A3, A5
    orientation: str = "portrait"  # portrait, landscape
    margins: Dict[str, float] = field(default_factory=lambda: {"top": 2.0, "bottom": 2.0, "left": 2.0, "right": 2.0})  # in cm
    
    # Typography
    font_family: str = "Arial, sans-serif"
    font_size: int = 11
    line_height: float = 1.4
    
    # Header/Footer
    header_height: float = 2.0  # cm
    footer_height: float = 1.5  # cm
    show_page_numbers: bool = True
    
    # Styling
    css_string: Optional[str] = None
    css_file_path: Optional[str] = None
    
    # Output
    filename: Optional[str] = None
    debug_mode: bool = False


@dataclass
class CompanyInfo:
    """Informazioni aziendali per branding PDF"""
    name: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    logo_path: str = ""
    tax_code: str = ""
    vat_number: str = ""


# =============================================================================
# MAIN PDF GENERATION FUNCTIONS
# =============================================================================

def generate_pdf_from_html(
    html_content: str = None,
    template_name: str = None,
    context: Dict[str, Any] = None,
    config: PDFConfig = None,
    company_info: CompanyInfo = None,
    output_type: str = 'response',  # 'response', 'file', 'buffer'
    output_path: str = None
) -> Union[HttpResponse, BytesIO, str]:
    """
    Genera PDF da HTML utilizzando xhtml2pdf o weasyprint (in ordine di preferenza)

    Args:
        html_content: HTML string diretto
        template_name: Nome template Django da renderizzare
        context: Context per il template
        config: Configurazione PDF
        company_info: Informazioni aziendali
        output_type: Tipo di output ('response', 'file', 'buffer')
        output_path: Percorso file per output_type='file'

    Returns:
        HttpResponse, BytesIO o str (percorso file)
    """
    # Usa weasyprint se xhtml2pdf non è disponibile
    use_weasyprint = not XHTML2PDF_AVAILABLE and WEASYPRINT_AVAILABLE

    if not XHTML2PDF_AVAILABLE and not WEASYPRINT_AVAILABLE:
        raise ImportError("Nessuna libreria PDF disponibile. Installa: pip install xhtml2pdf o pip install weasyprint")
    
    # Configurazione di default
    if config is None:
        config = PDFConfig()
    
    if context is None:
        context = {}
    
    # Aggiungi info aziendali al context
    if company_info:
        context['company'] = company_info
    
    # Aggiungi configurazioni al context
    context.update({
        'config': config,
        'current_date': timezone.now().strftime('%d/%m/%Y'),
        'current_datetime': timezone.now().strftime('%d/%m/%Y %H:%M'),
        'STATIC_URL': getattr(settings, 'STATIC_URL', '/static/'),
        'MEDIA_URL': getattr(settings, 'MEDIA_URL', '/media/'),
    })
    
    # Genera HTML
    if template_name:
        try:
            html_content = render_to_string(template_name, context)
        except Exception as e:
            logger.error(f"Errore rendering template {template_name}: {e}")
            raise
    elif not html_content:
        raise ValueError("html_content o template_name richiesto")
    
    # Aggiungi CSS base se non specificato
    if not config.css_string and not config.css_file_path:
        config.css_string = _get_default_css(config)
    
    # Prepara CSS
    css_content = ""
    if config.css_file_path and os.path.exists(config.css_file_path):
        with open(config.css_file_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
    elif config.css_string:
        css_content = config.css_string
    
    # Combina HTML con CSS
    if css_content:
        html_with_css = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                {css_content}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
    else:
        html_with_css = html_content
    
    # Genera PDF
    if use_weasyprint:
        # Usa WeasyPrint
        try:
            html_obj = HTML(string=html_with_css)

            if output_type == 'buffer':
                result_buffer = BytesIO()
                html_obj.write_pdf(result_buffer)
                result_buffer.seek(0)
                return result_buffer

            elif output_type == 'file':
                if not output_path:
                    output_path = _generate_temp_filename(config.filename or 'document.pdf')

                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                html_obj.write_pdf(output_path)
                return output_path

            else:  # response
                response = HttpResponse(content_type='application/pdf')
                filename = config.filename or 'document.pdf'
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                html_obj.write_pdf(response)
                return response

        except Exception as e:
            logger.error(f"Errore generazione PDF con WeasyPrint: {e}")
            if output_type == 'response':
                return HttpResponse('Errore generazione PDF', status=500)
            return None

    else:
        # Usa xhtml2pdf
        if output_type == 'buffer':
            result_buffer = BytesIO()
            pisa_status = pisa.CreatePDF(
                html_with_css,
                dest=result_buffer,
                encoding='utf-8',
                link_callback=_link_callback
            )

            if pisa_status.err:
                logger.error(f"Errore generazione PDF: {pisa_status.err}")
                return None

            result_buffer.seek(0)
            return result_buffer

        elif output_type == 'file':
            if not output_path:
                output_path = _generate_temp_filename(config.filename or 'document.pdf')

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, 'w+b') as result_file:
                pisa_status = pisa.CreatePDF(
                    html_with_css,
                    dest=result_file,
                    encoding='utf-8',
                    link_callback=_link_callback
                )

            if pisa_status.err:
                logger.error(f"Errore generazione PDF: {pisa_status.err}")
                return None

            return output_path

        else:  # response
            response = HttpResponse(content_type='application/pdf')
            filename = config.filename or 'document.pdf'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            pisa_status = pisa.CreatePDF(
                html_with_css,
                dest=response,
                encoding='utf-8',
                link_callback=_link_callback
            )

            if pisa_status.err:
                logger.error(f"Errore generazione PDF: {pisa_status.err}")
                return HttpResponse('Errore generazione PDF', status=500)

            return response


def generate_pdf_with_reportlab(
    data: Dict[str, Any],
    template_type: str = 'table',  # 'table', 'invoice', 'report', 'custom'
    config: PDFConfig = None,
    company_info: CompanyInfo = None,
    output_type: str = 'response',
    output_path: str = None
) -> Union[HttpResponse, BytesIO, str]:
    """
    Genera PDF programmaticamente con ReportLab
    
    Args:
        data: Dati per la generazione (struttura dipende da template_type)
        template_type: Tipo di template predefinito
        config: Configurazione PDF
        company_info: Informazioni aziendali  
        output_type: Tipo di output
        output_path: Percorso file per output='file'
        
    Returns:
        HttpResponse, BytesIO o str (percorso file)
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab non disponibile. Installa: pip install reportlab")
    
    if config is None:
        config = PDFConfig()
    
    # Determina page size
    page_size = _get_page_size(config.page_size, config.orientation)
    
    # Setup output
    if output_type == 'buffer':
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=page_size, **_get_margins(config))
    elif output_type == 'file':
        if not output_path:
            output_path = _generate_temp_filename(config.filename or 'document.pdf')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc = SimpleDocTemplate(output_path, pagesize=page_size, **_get_margins(config))
    else:  # response
        response = HttpResponse(content_type='application/pdf')
        filename = config.filename or 'document.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        doc = SimpleDocTemplate(response, pagesize=page_size, **_get_margins(config))
    
    # Genera contenuto in base al template type
    story = []
    styles = getSampleStyleSheet()
    
    if template_type == 'table':
        story.extend(_build_table_template(data, styles, config, company_info))
    elif template_type == 'invoice':
        story.extend(_build_invoice_template(data, styles, config, company_info))
    elif template_type == 'report':
        story.extend(_build_report_template(data, styles, config, company_info))
    else:
        # Template custom - data deve contenere story elements
        story = data.get('story', [])
    
    # Build PDF
    try:
        doc.build(story)
    except Exception as e:
        logger.error(f"Errore build ReportLab PDF: {e}")
        raise
    
    # Return appropriate output
    if output_type == 'buffer':
        buffer.seek(0)
        return buffer
    elif output_type == 'file':
        return output_path
    else:
        return response


# =============================================================================
# TEMPLATE BUILDERS (REPORTLAB)
# =============================================================================

def _build_table_template(data: Dict, styles, config: PDFConfig, company_info: CompanyInfo) -> List:
    """Costruisce template tabella semplice"""
    story = []
    
    # Header aziendale
    if company_info and company_info.name:
        story.extend(_build_company_header(company_info, styles))
        story.append(Spacer(1, 20))
    
    # Titolo
    if 'title' in data:
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            alignment=1  # CENTER
        )
        story.append(Paragraph(data['title'], title_style))
    
    # Tabella dati
    if 'table_data' in data:
        table_data = data['table_data']
        col_widths = data.get('col_widths', None)
        
        table = Table(table_data, colWidths=col_widths)
        
        # Stile tabella
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    return story


def _build_invoice_template(data: Dict, styles, config: PDFConfig, company_info: CompanyInfo) -> List:
    """Costruisce template fattura professionale"""
    story = []
    
    # Header aziendale
    if company_info:
        story.extend(_build_company_header(company_info, styles))
        story.append(Spacer(1, 15))
    
    # Intestazione fattura
    invoice_title = data.get('document_type', 'FATTURA')
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.darkblue,
        alignment=1
    )
    story.append(Paragraph(invoice_title, title_style))
    story.append(Spacer(1, 20))
    
    # Dati documento
    doc_info = [
        ['Numero:', data.get('number', 'N/A')],
        ['Data:', data.get('date', 'N/A')],
        ['Scadenza:', data.get('due_date', 'N/A')]
    ]
    
    doc_table = Table(doc_info, colWidths=[3*cm, 4*cm])
    doc_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    story.append(doc_table)
    story.append(Spacer(1, 20))
    
    # Cliente
    if 'customer' in data:
        customer = data['customer']
        story.append(Paragraph('<b>Destinatario:</b>', styles['Normal']))
        customer_info = f"""
        {customer.get('name', '')}<br/>
        {customer.get('address', '')}<br/>
        {customer.get('city', '')} {customer.get('postal_code', '')}<br/>
        P.IVA: {customer.get('vat_number', 'N/A')}
        """
        story.append(Paragraph(customer_info, styles['Normal']))
        story.append(Spacer(1, 20))
    
    # Tabella prodotti
    if 'items' in data:
        headers = ['Descrizione', 'Qtà', 'Prezzo', 'Totale']
        table_data = [headers]
        
        total = 0
        for item in data['items']:
            qty = item.get('quantity', 0)
            price = item.get('price', 0)
            item_total = qty * price
            total += item_total
            
            table_data.append([
                item.get('description', ''),
                str(qty),
                f"€ {price:.2f}",
                f"€ {item_total:.2f}"
            ])
        
        # Riga totale
        table_data.append(['', '', 'TOTALE:', f"€ {total:.2f}"])
        
        table = Table(table_data, colWidths=[8*cm, 2*cm, 3*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.lightgrey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.yellow),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
    
    return story


def _build_report_template(data: Dict, styles, config: PDFConfig, company_info: CompanyInfo) -> List:
    """Costruisce template report generico"""
    story = []
    
    # Header
    if company_info:
        story.extend(_build_company_header(company_info, styles))
        story.append(Spacer(1, 15))
    
    # Titolo report
    if 'title' in data:
        story.append(Paragraph(data['title'], styles['Title']))
        story.append(Spacer(1, 12))
    
    # Sottotitolo/Data
    if 'subtitle' in data:
        story.append(Paragraph(data['subtitle'], styles['Heading2']))
        story.append(Spacer(1, 12))
    
    # Sezioni
    if 'sections' in data:
        for section in data['sections']:
            if 'title' in section:
                story.append(Paragraph(section['title'], styles['Heading3']))
                story.append(Spacer(1, 6))
            
            if 'content' in section:
                story.append(Paragraph(section['content'], styles['Normal']))
                story.append(Spacer(1, 12))
            
            if 'table' in section:
                table = Table(section['table'])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
                story.append(Spacer(1, 12))
    
    return story


def _build_company_header(company_info: CompanyInfo, styles) -> List:
    """Costruisce header aziendale standard"""
    story = []
    
    # Logo + Info aziendali side by side
    company_data = []
    
    if company_info.logo_path and os.path.exists(company_info.logo_path):
        # TODO: Implementare inserimento logo
        pass
    
    company_text = f"""
    <b>{company_info.name}</b><br/>
    {company_info.address}<br/>
    Tel: {company_info.phone}<br/>
    Email: {company_info.email}<br/>
    {company_info.website}
    """
    
    if company_info.tax_code:
        company_text += f"<br/>C.F.: {company_info.tax_code}"
    if company_info.vat_number:
        company_text += f"<br/>P.IVA: {company_info.vat_number}"
    
    story.append(Paragraph(company_text, styles['Normal']))
    
    return story


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _get_default_css(config: PDFConfig) -> str:
    """Restituisce CSS di default per PDF"""
    return f"""
    @page {{
        size: {config.page_size.lower()};
        margin: {config.margins['top']}cm {config.margins['right']}cm {config.margins['bottom']}cm {config.margins['left']}cm;
    }}
    
    body {{
        font-family: {config.font_family};
        font-size: {config.font_size}pt;
        line-height: {config.line_height};
        color: #333;
    }}
    
    .header {{
        border-bottom: 1px solid #ddd;
        padding-bottom: 5px;
        font-size: 10pt;
        margin-bottom: 10px;
    }}
    
    .footer {{
        border-top: 1px solid #ddd;
        padding-top: 5px;
        text-align: center;
        font-size: 9pt;
        color: #666;
        margin-top: 10px;
    }}
    
    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
    }}
    
    th, td {{
        padding: 8px;
        text-align: left;
        border: 1px solid #ddd;
    }}
    
    th {{
        background-color: #f2f2f2;
        font-weight: bold;
    }}
    
    .text-center {{ text-align: center; }}
    .text-right {{ text-align: right; }}
    .font-bold {{ font-weight: bold; }}
    .text-small {{ font-size: 9pt; }}
    """


def _link_callback(uri, rel):
    """Callback per risolvere CSS e immagini nei template"""
    if uri.startswith(('http://', 'https://')):
        return uri
    
    # Cerca nei file statici
    result = finders.find(uri.lstrip('/'))
    if result:
        return result
    
    # Percorso assoluto
    if os.path.exists(uri):
        return uri
    
    # Media files
    media_path = os.path.join(getattr(settings, 'MEDIA_ROOT', ''), uri.lstrip('/'))
    if os.path.exists(media_path):
        return media_path
    
    logger.warning(f"Risorsa PDF non trovata: {uri}")
    return uri


def _get_page_size(size: str, orientation: str):
    """Converte stringa page size in oggetto ReportLab"""
    size_map = {
        'A4': A4,
        'A3': (A4[1] * 1.414, A4[0] * 1.414),
        'A5': (A4[0] / 1.414, A4[1] / 1.414),
        'LETTER': LETTER
    }
    
    page_size = size_map.get(size.upper(), A4)
    
    if orientation.lower() == 'landscape':
        return landscape(page_size)
    else:
        return portrait(page_size)


def _get_margins(config: PDFConfig) -> Dict:
    """Converte margini in unità ReportLab"""
    return {
        'topMargin': config.margins['top'] * cm,
        'bottomMargin': config.margins['bottom'] * cm,
        'leftMargin': config.margins['left'] * cm,
        'rightMargin': config.margins['right'] * cm
    }


def _generate_temp_filename(base_filename: str) -> str:
    """Genera percorso file temporaneo"""
    temp_dir = getattr(settings, 'TEMP_DIR', tempfile.gettempdir())
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    name, ext = os.path.splitext(base_filename)
    filename = f"{name}_{timestamp}{ext}"
    return os.path.join(temp_dir, 'pdfs', filename)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_table_pdf(
    data: List[List[str]], 
    headers: List[str] = None,
    title: str = None,
    filename: str = 'table.pdf',
    output_type: str = 'response'
):
    """Funzione convenienza per PDF tabella semplice"""
    table_data = [headers] + data if headers else data
    
    pdf_data = {
        'title': title,
        'table_data': table_data
    }
    
    config = PDFConfig(filename=filename)
    
    return generate_pdf_with_reportlab(
        data=pdf_data,
        template_type='table',
        config=config,
        output_type=output_type
    )


def create_invoice_pdf(
    invoice_data: Dict,
    company_info: CompanyInfo = None,
    filename: str = 'invoice.pdf',
    output_type: str = 'response'
):
    """Funzione convenienza per PDF fattura"""
    config = PDFConfig(filename=filename)
    
    return generate_pdf_with_reportlab(
        data=invoice_data,
        template_type='invoice',
        config=config,
        company_info=company_info,
        output_type=output_type
    )