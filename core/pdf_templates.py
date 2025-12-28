"""
CORE PDF TEMPLATES - Sistema Template PDF Riutilizzabili
========================================================

Sistema completo di template PDF riutilizzabili per documenti comuni:
- 📄 Template base con header/footer configurabili
- 🧾 Template fatture professionali
- 📊 Template report con grafici e tabelle
- 📋 Template documenti amministrativi
- 🎨 Sistema styling modulare

Caratteristiche:
- Template HTML con CSS integrato
- Placeholder dinamici per dati
- Styling professionale responsive
- Compatibilità xhtml2pdf
- Sistema di ereditarietà template

Versione: 1.0
Compatibilità: Django 3.2+, Python 3.8+
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from django.template import Template, Context
from django.utils import timezone

from .pdf_generator import PDFConfig, CompanyInfo


# =============================================================================
# TEMPLATE CONFIGURATION
# =============================================================================

@dataclass
class TemplateConfig:
    """Configurazione template PDF"""
    template_name: str
    show_header: bool = True
    show_footer: bool = True
    show_page_numbers: bool = True
    watermark: str = None
    custom_css: str = None


# =============================================================================
# BASE TEMPLATE SYSTEM
# =============================================================================

def get_base_template_html() -> str:
    """Template HTML base con styling comune"""
    return """
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ document_title|default:"Documento" }}</title>
    <style>
        /* CSS Base per PDF */
        @page {
            size: A4;
            margin: {{ margins.top|default:"2cm" }} {{ margins.right|default:"2cm" }} 
                    {{ margins.bottom|default:"2.5cm" }} {{ margins.left|default:"2cm" }};
        }
        
        /* Reset e base */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'DejaVu Sans', Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.4;
            color: #333;
            background: white;
        }
        
        /* Header */
        .pdf-header {
            border-bottom: 1px solid #ddd;
            padding-bottom: 8px;
            font-size: 9pt;
            color: #666;
            margin-bottom: 10px;
        }
        
        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header-left {
            flex: 1;
        }
        
        .header-right {
            text-align: right;
        }
        
        /* Footer */
        .pdf-footer {
            border-top: 1px solid #ddd;
            padding-top: 8px;
            font-size: 9pt;
            color: #666;
            text-align: center;
            margin-top: 10px;
        }
        
        /* Company Header */
        .company-header {
            text-align: center;
            margin-bottom: 25px;
            border-bottom: 2px solid #4472C4;
            padding-bottom: 15px;
        }
        
        .company-name {
            font-size: 18pt;
            font-weight: bold;
            color: #4472C4;
            margin-bottom: 5px;
        }
        
        .company-details {
            font-size: 10pt;
            color: #666;
            line-height: 1.3;
        }
        
        /* Document Title */
        .document-title {
            text-align: center;
            font-size: 20pt;
            font-weight: bold;
            color: #2E5299;
            margin: 20px 0;
            text-transform: uppercase;
        }
        
        /* Document Info */
        .document-info {
            display: table;
            width: 100%;
            margin-bottom: 20px;
        }
        
        .info-section {
            display: table-cell;
            vertical-align: top;
            width: 50%;
            padding: 10px;
        }
        
        .info-title {
            font-weight: bold;
            color: #4472C4;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
            margin-bottom: 8px;
        }
        
        .info-content {
            font-size: 10pt;
            line-height: 1.4;
        }
        
        /* Tables */
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 10pt;
        }
        
        .data-table th,
        .data-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        
        .data-table th {
            background-color: #4472C4;
            color: white;
            font-weight: bold;
            text-align: center;
        }
        
        .data-table tbody tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        
        .data-table tbody tr:hover {
            background-color: #f5f5f5;
        }
        
        .data-table .number {
            text-align: right;
        }
        
        .data-table .center {
            text-align: center;
        }
        
        .table-total {
            background-color: #e8f0fe !important;
            font-weight: bold;
        }
        
        /* Sections */
        .section {
            margin: 20px 0;
        }
        
        .section-title {
            font-size: 14pt;
            font-weight: bold;
            color: #4472C4;
            border-left: 4px solid #4472C4;
            padding-left: 10px;
            margin-bottom: 10px;
        }
        
        .section-content {
            margin-left: 15px;
        }
        
        /* Utilities */
        .text-center { text-align: center; }
        .text-right { text-align: right; }
        .text-bold { font-weight: bold; }
        .text-small { font-size: 9pt; }
        .text-large { font-size: 12pt; }
        
        .mb-5 { margin-bottom: 5px; }
        .mb-10 { margin-bottom: 10px; }
        .mb-15 { margin-bottom: 15px; }
        .mb-20 { margin-bottom: 20px; }
        
        .mt-5 { margin-top: 5px; }
        .mt-10 { margin-top: 10px; }
        .mt-15 { margin-top: 15px; }
        .mt-20 { margin-top: 20px; }
        
        /* Status and labels */
        .status-label {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 9pt;
            font-weight: bold;
            text-transform: uppercase;
        }
        
        .status-success {
            background-color: #d4edda;
            color: #155724;
        }
        
        .status-warning {
            background-color: #fff3cd;
            color: #856404;
        }
        
        .status-danger {
            background-color: #f8d7da;
            color: #721c24;
        }
        
        .status-info {
            background-color: #d1ecf1;
            color: #0c5460;
        }
        
        /* Signatures */
        .signatures {
            margin-top: 40px;
            display: table;
            width: 100%;
        }
        
        .signature-box {
            display: table-cell;
            width: 50%;
            text-align: center;
            padding: 20px;
        }
        
        .signature-line {
            border-top: 1px solid #333;
            margin-top: 40px;
            padding-top: 5px;
            font-size: 10pt;
        }
        
        /* Watermark */
        .watermark {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-45deg);
            font-size: 48pt;
            color: rgba(0,0,0,0.1);
            z-index: -1;
            pointer-events: none;
        }
        
        /* Custom CSS placeholder */
        {{ custom_css|safe }}
    </style>
</head>
<body>
    {% if watermark %}
    <div class="watermark">{{ watermark }}</div>
    {% endif %}
    
    {% if show_header %}
    <div class="pdf-header">
        <div class="header-content">
            <div class="header-left">
                {% block header_left %}
                {% if company.name %}{{ company.name }}{% endif %}
                {% endblock %}
            </div>
            <div class="header-right">
                {% block header_right %}
                {{ current_date }}
                {% endblock %}
            </div>
        </div>
    </div>
    {% endif %}
    
    {% if show_footer %}
    <div class="pdf-footer">
        {% block footer %}
        {% if show_page_numbers %}Pagina <pdf:pagenumber>{% endif %}
        {% if company.website %} | {{ company.website }}{% endif %}
        {% endblock %}
    </div>
    {% endif %}
    
    <div class="document-content">
        {% block content %}
        <!-- Content will be inserted here -->
        {% endblock %}
    </div>
</body>
</html>
"""


def get_invoice_template() -> str:
    """Template fattura professionale"""
    base = get_base_template_html()
    
    invoice_content = """
{% block content %}
<!-- Company Header -->
{% if company %}
<div class="company-header">
    <div class="company-name">{{ company.name }}</div>
    <div class="company-details">
        {{ company.address }}<br>
        Tel: {{ company.phone }} | Email: {{ company.email }}<br>
        {% if company.vat_number %}P.IVA: {{ company.vat_number }}{% endif %}
        {% if company.tax_code %} | C.F.: {{ company.tax_code }}{% endif %}
    </div>
</div>
{% endif %}

<!-- Document Title -->
<div class="document-title">{{ document_type|default:"FATTURA" }}</div>

<!-- Document Info -->
<div class="document-info">
    <div class="info-section">
        <div class="info-title">DATI DOCUMENTO</div>
        <div class="info-content">
            <strong>Numero:</strong> {{ number }}<br>
            <strong>Data:</strong> {{ date }}<br>
            {% if due_date %}<strong>Scadenza:</strong> {{ due_date }}<br>{% endif %}
            {% if payment_method %}<strong>Pagamento:</strong> {{ payment_method }}<br>{% endif %}
        </div>
    </div>
    
    <div class="info-section">
        <div class="info-title">DESTINATARIO</div>
        <div class="info-content">
            {% if customer %}
            <strong>{{ customer.name }}</strong><br>
            {{ customer.address }}<br>
            {{ customer.city }} {{ customer.postal_code }}<br>
            {% if customer.vat_number %}P.IVA: {{ customer.vat_number }}<br>{% endif %}
            {% if customer.tax_code %}C.F.: {{ customer.tax_code }}{% endif %}
            {% endif %}
        </div>
    </div>
</div>

<!-- Items Table -->
{% if items %}
<table class="data-table">
    <thead>
        <tr>
            <th style="width: 8%">Pos.</th>
            <th style="width: 40%">Descrizione</th>
            <th style="width: 8%">Qtà</th>
            <th style="width: 10%">U.M.</th>
            <th style="width: 12%">Prezzo</th>
            <th style="width: 10%">Sconto</th>
            <th style="width: 12%">Totale</th>
        </tr>
    </thead>
    <tbody>
        {% for item in items %}
        <tr>
            <td class="center">{{ forloop.counter }}</td>
            <td>{{ item.description }}</td>
            <td class="number">{{ item.quantity|floatformat:2 }}</td>
            <td class="center">{{ item.unit|default:"PZ" }}</td>
            <td class="number">€ {{ item.price|floatformat:2 }}</td>
            <td class="number">
                {% if item.discount_percent %}{{ item.discount_percent }}%
                {% elif item.discount_amount %}€ {{ item.discount_amount|floatformat:2 }}
                {% else %}-{% endif %}
            </td>
            <td class="number">€ {{ item.total|floatformat:2 }}</td>
        </tr>
        {% endfor %}
        
        <!-- Totals Section -->
        <tr class="table-total">
            <td colspan="6" class="text-right"><strong>Subtotale:</strong></td>
            <td class="number"><strong>€ {{ subtotal|floatformat:2 }}</strong></td>
        </tr>
        
        {% if total_discount %}
        <tr>
            <td colspan="6" class="text-right">Sconto Totale:</td>
            <td class="number">€ {{ total_discount|floatformat:2 }}</td>
        </tr>
        {% endif %}
        
        {% if vat_groups %}
        {% for vat in vat_groups %}
        <tr>
            <td colspan="6" class="text-right">IVA {{ vat.rate }}%:</td>
            <td class="number">€ {{ vat.amount|floatformat:2 }}</td>
        </tr>
        {% endfor %}
        {% endif %}
        
        <tr class="table-total">
            <td colspan="6" class="text-right"><strong>TOTALE GENERALE:</strong></td>
            <td class="number"><strong>€ {{ total|floatformat:2 }}</strong></td>
        </tr>
    </tbody>
</table>
{% endif %}

<!-- Payment Info -->
{% if payment_info %}
<div class="section">
    <div class="section-title">MODALITÀ DI PAGAMENTO</div>
    <div class="section-content">
        {{ payment_info|linebreaks }}
    </div>
</div>
{% endif %}

<!-- Notes -->
{% if notes %}
<div class="section">
    <div class="section-title">NOTE</div>
    <div class="section-content">
        {{ notes|linebreaks }}
    </div>
</div>
{% endif %}

<!-- Signatures -->
<div class="signatures">
    <div class="signature-box">
        <div class="signature-line">IL FORNITORE</div>
    </div>
    <div class="signature-box">
        <div class="signature-line">IL CLIENTE</div>
    </div>
</div>
{% endblock %}
"""
    
    return base.replace('{% block content %}<!-- Content will be inserted here -->{% endblock %}', invoice_content)


def get_report_template() -> str:
    """Template report generico"""
    base = get_base_template_html()
    
    report_content = """
{% block content %}
<!-- Company Header -->
{% if company %}
<div class="company-header">
    <div class="company-name">{{ company.name }}</div>
    <div class="company-details">
        {{ company.address }} | Tel: {{ company.phone }} | Email: {{ company.email }}
    </div>
</div>
{% endif %}

<!-- Document Title -->
<div class="document-title">{{ title|default:"REPORT" }}</div>

<!-- Report Info -->
{% if report_info %}
<div class="document-info">
    <div class="info-section">
        <div class="info-title">INFORMAZIONI REPORT</div>
        <div class="info-content">
            {% for key, value in report_info.items %}
            <strong>{{ key|title }}:</strong> {{ value }}<br>
            {% endfor %}
        </div>
    </div>
    
    {% if period %}
    <div class="info-section">
        <div class="info-title">PERIODO</div>
        <div class="info-content">
            <strong>Dal:</strong> {{ period.start }}<br>
            <strong>Al:</strong> {{ period.end }}<br>
            <strong>Generato il:</strong> {{ current_datetime }}
        </div>
    </div>
    {% endif %}
</div>
{% endif %}

<!-- Summary Stats -->
{% if summary_stats %}
<div class="section">
    <div class="section-title">RIEPILOGO</div>
    <table class="data-table">
        <thead>
            <tr>
                <th>Indicatore</th>
                <th>Valore</th>
                <th>Variazione</th>
                <th>Note</th>
            </tr>
        </thead>
        <tbody>
            {% for stat in summary_stats %}
            <tr>
                <td><strong>{{ stat.label }}</strong></td>
                <td class="number">{{ stat.value }}</td>
                <td class="center">
                    {% if stat.change %}
                    <span class="status-label {% if stat.change_positive %}status-success{% else %}status-danger{% endif %}">
                        {{ stat.change }}
                    </span>
                    {% else %}-{% endif %}
                </td>
                <td>{{ stat.notes|default:"-" }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endif %}

<!-- Sections -->
{% if sections %}
{% for section in sections %}
<div class="section">
    <div class="section-title">{{ section.title }}</div>
    
    {% if section.description %}
    <div class="section-content mb-15">
        {{ section.description|linebreaks }}
    </div>
    {% endif %}
    
    {% if section.table %}
    <table class="data-table">
        {% if section.table.headers %}
        <thead>
            <tr>
                {% for header in section.table.headers %}
                <th>{{ header }}</th>
                {% endfor %}
            </tr>
        </thead>
        {% endif %}
        <tbody>
            {% for row in section.table.rows %}
            <tr{% if row.highlight %} class="table-total"{% endif %}>
                {% for cell in row.cells %}
                <td{% if cell.class %} class="{{ cell.class }}"{% endif %}>
                    {{ cell.value }}
                </td>
                {% endfor %}
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% endif %}
    
    {% if section.chart_placeholder %}
    <div class="text-center mt-15">
        <div style="border: 2px dashed #ddd; padding: 40px; background-color: #f9f9f9;">
            <strong>Grafico: {{ section.chart_placeholder.title }}</strong><br>
            <small>{{ section.chart_placeholder.description }}</small>
        </div>
    </div>
    {% endif %}
</div>
{% endfor %}
{% endif %}

<!-- Conclusions -->
{% if conclusions %}
<div class="section">
    <div class="section-title">CONCLUSIONI</div>
    <div class="section-content">
        {{ conclusions|linebreaks }}
    </div>
</div>
{% endif %}

<!-- Appendices -->
{% if appendices %}
<div class="section">
    <div class="section-title">ALLEGATI</div>
    <div class="section-content">
        <ol>
        {% for appendix in appendices %}
            <li><strong>{{ appendix.title }}</strong>{% if appendix.description %} - {{ appendix.description }}{% endif %}</li>
        {% endfor %}
        </ol>
    </div>
</div>
{% endif %}
{% endblock %}
"""
    
    return base.replace('{% block content %}<!-- Content will be inserted here -->{% endblock %}', report_content)


def get_table_template() -> str:
    """Template tabella semplice"""
    base = get_base_template_html()
    
    table_content = """
{% block content %}
<!-- Company Header -->
{% if company %}
<div class="company-header">
    <div class="company-name">{{ company.name }}</div>
    <div class="company-details">{{ company.address }}</div>
</div>
{% endif %}

<!-- Document Title -->
{% if title %}
<div class="document-title">{{ title }}</div>
{% endif %}

<!-- Description -->
{% if description %}
<div class="section-content mb-20">
    {{ description|linebreaks }}
</div>
{% endif %}

<!-- Main Table -->
{% if table_data %}
<table class="data-table">
    {% if table_data.0 %}
    <thead>
        <tr>
            {% for header in table_data.0 %}
            <th>{{ header }}</th>
            {% endfor %}
        </tr>
    </thead>
    {% endif %}
    <tbody>
        {% for row in table_data|slice:"1:" %}
        <tr{% if row.is_total %} class="table-total"{% endif %}>
            {% for cell in row %}
            <td{% if forloop.counter > 2 %} class="number"{% endif %}>{{ cell }}</td>
            {% endfor %}
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endif %}

<!-- Additional Notes -->
{% if notes %}
<div class="section mt-20">
    <div class="section-title">NOTE</div>
    <div class="section-content">
        {{ notes|linebreaks }}
    </div>
</div>
{% endif %}
{% endblock %}
"""
    
    return base.replace('{% block content %}<!-- Content will be inserted here -->{% endblock %}', table_content)


# =============================================================================
# TEMPLATE GENERATION FUNCTIONS
# =============================================================================

def generate_pdf_from_template(
    template_name: str,
    context: Dict[str, Any],
    config: PDFConfig = None,
    company_info: CompanyInfo = None,
    template_config: TemplateConfig = None
) -> str:
    """
    Genera PDF da template predefinito
    
    Args:
        template_name: Nome template ('invoice', 'report', 'table', 'base')
        context: Dati per il template
        config: Configurazione PDF
        company_info: Informazioni aziendali
        template_config: Configurazione template
        
    Returns:
        HTML renderizzato per PDF
    """
    if config is None:
        config = PDFConfig()
    
    if template_config is None:
        template_config = TemplateConfig(template_name=template_name)
    
    # Seleziona template
    if template_name == 'invoice':
        html_template = get_invoice_template()
    elif template_name == 'report':
        html_template = get_report_template()
    elif template_name == 'table':
        html_template = get_table_template()
    else:
        html_template = get_base_template_html()
    
    # Prepara context completo
    full_context = {
        'show_header': template_config.show_header,
        'show_footer': template_config.show_footer,
        'show_page_numbers': template_config.show_page_numbers,
        'watermark': template_config.watermark,
        'custom_css': template_config.custom_css or '',
        'margins': {
            'top': f"{config.margins['top']}cm",
            'right': f"{config.margins['right']}cm", 
            'bottom': f"{config.margins['bottom']}cm",
            'left': f"{config.margins['left']}cm"
        },
        'current_date': timezone.now().strftime('%d/%m/%Y'),
        'current_datetime': timezone.now().strftime('%d/%m/%Y %H:%M'),
        'company': company_info,
        **context
    }
    
    # Renderizza template
    template = Template(html_template)
    rendered_html = template.render(Context(full_context))
    
    return rendered_html


def create_invoice_from_template(
    invoice_data: Dict[str, Any],
    company_info: CompanyInfo = None,
    config: PDFConfig = None
) -> str:
    """Crea fattura da template con calcoli automatici"""
    
    # Calcola totali se non presenti
    if 'items' in invoice_data and 'subtotal' not in invoice_data:
        subtotal = 0
        total_discount = 0
        vat_amount = 0
        
        for item in invoice_data['items']:
            quantity = item.get('quantity', 1)
            price = item.get('price', 0)
            discount_percent = item.get('discount_percent', 0)
            discount_amount = item.get('discount_amount', 0)
            
            line_total = quantity * price
            
            # Applica sconti
            if discount_percent:
                line_discount = line_total * discount_percent / 100
                line_total -= line_discount
                total_discount += line_discount
            elif discount_amount:
                line_total -= discount_amount
                total_discount += discount_amount
            
            item['total'] = line_total
            subtotal += line_total
        
        # Calcola IVA (default 22%)
        vat_rate = invoice_data.get('vat_rate', 22)
        vat_amount = subtotal * vat_rate / 100
        
        # Aggiungi calcoli al context
        invoice_data.update({
            'subtotal': subtotal,
            'total_discount': total_discount,
            'vat_amount': vat_amount,
            'total': subtotal + vat_amount,
            'vat_groups': [{'rate': vat_rate, 'amount': vat_amount}]
        })
    
    return generate_pdf_from_template(
        template_name='invoice',
        context=invoice_data,
        config=config,
        company_info=company_info
    )