"""
CORE VIEWS - Views per funzionalità utilities core
================================================

Views per le funzionalità core di generazione documenti:
- 📄 Generazione PDF da template
- 📊 Export Excel e CSV
- 🗂️ Upload e gestione file
- 🔧 Utilities e demo funzionalità

Tutte le views sono protette da login e includono:
- Validazione permessi
- Error handling robusto
- Logging operazioni
- Response appropriate per ogni formato

Versione: 1.0
"""

import os
import logging
from typing import Dict, Any
from datetime import date

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.urls import reverse

# Core generators
from ..pdf_generator import (
    generate_pdf_from_html, generate_pdf_with_reportlab,
    create_simple_table_pdf, create_invoice_pdf,
    PDFConfig, CompanyInfo
)
from ..excel_generator import (
    generate_excel_from_data, generate_excel_with_pandas,
    create_simple_excel, dataframe_to_excel_response,
    ExcelConfig, ColumnConfig
)
from ..csv_generator import (
    generate_csv_from_data, import_csv_from_file,
    export_simple_csv, export_csv_italian_format,
    CSVConfig
)
from ..file_utils import (
    validate_and_store_file, process_image, generate_thumbnails,
    FileConfig, ImageConfig
)
from ..utils import (
    generate_unique_code, format_currency, validate_italian_tax_code,
    calculate_vat, statistical_summary
)
from ..models import Messaggio, Promemoria

User = get_user_model()
logger = logging.getLogger(__name__)


# =============================================================================
# PDF GENERATION VIEWS
# =============================================================================

@login_required
@require_http_methods(["GET", "POST"])
def pdf_generator_demo(request):
    """Demo generazione PDF"""
    
    if request.method == "GET":
        # Mostra form demo
        context = {
            'page_title': 'Demo Generatore PDF',
            'demo_data': {
                'title': 'Report di Test',
                'content': 'Contenuto di esempio per il report.',
                'table_data': [
                    ['Prodotto', 'Quantità', 'Prezzo'],
                    ['Prodotto A', '10', '€ 15,00'],
                    ['Prodotto B', '5', '€ 25,00'],
                    ['Prodotto C', '8', '€ 12,50'],
                ]
            }
        }
        return render(request, 'core/pdf_demo.html', context)
    
    else:  # POST
        try:
            # Recupera parametri
            template_type = request.POST.get('template_type', 'table')
            title = request.POST.get('title', 'Report di Test')
            
            # Prepara dati demo
            if template_type == 'table':
                data = {
                    'title': title,
                    'table_data': [
                        ['Prodotto', 'Quantità', 'Prezzo', 'Totale'],
                        ['Prodotto A', '10', '€ 15,00', '€ 150,00'],
                        ['Prodotto B', '5', '€ 25,00', '€ 125,00'],
                        ['Prodotto C', '8', '€ 12,50', '€ 100,00'],
                        ['', '', 'TOTALE:', '€ 375,00']
                    ]
                }
                
                config = PDFConfig(
                    filename=f"demo_table_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                )
                
                return generate_pdf_with_reportlab(
                    data=data,
                    template_type='table',
                    config=config,
                    output_type='response'
                )
            
            elif template_type == 'invoice':
                data = {
                    'document_type': 'FATTURA DI PROVA',
                    'number': 'DEMO-001',
                    'date': timezone.now().strftime('%d/%m/%Y'),
                    'due_date': (timezone.now() + timezone.timedelta(days=30)).strftime('%d/%m/%Y'),
                    'customer': {
                        'name': 'Cliente Demo S.r.l.',
                        'address': 'Via Roma 123',
                        'city': 'Milano',
                        'postal_code': '20100',
                        'vat_number': '12345678901'
                    },
                    'items': [
                        {'description': 'Servizio di Consulenza', 'quantity': 10, 'price': 50.00},
                        {'description': 'Sviluppo Software', 'quantity': 20, 'price': 75.00},
                    ]
                }
                
                company_info = CompanyInfo(
                    name="Management System S.r.l.",
                    address="Via Test 456, Milano",
                    phone="+39 02 1234567",
                    email="info@management.it",
                    vat_number="98765432109"
                )
                
                config = PDFConfig(
                    filename=f"demo_invoice_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                )
                
                return generate_pdf_with_reportlab(
                    data=data,
                    template_type='invoice',
                    config=config,
                    company_info=company_info,
                    output_type='response'
                )
            
            else:
                messages.error(request, "Tipo template non supportato")
                return render(request, 'core/pdf_demo.html')
                
        except Exception as e:
            logger.error(f"Errore generazione PDF demo: {e}")
            messages.error(request, f"Errore generazione PDF: {str(e)}")
            return render(request, 'core/pdf_demo.html')


# =============================================================================
# EXCEL GENERATION VIEWS
# =============================================================================

@login_required
@require_http_methods(["GET", "POST"])
def excel_generator_demo(request):
    """Demo generazione Excel"""
    
    if request.method == "GET":
        context = {
            'page_title': 'Demo Generatore Excel',
        }
        return render(request, 'core/excel_demo.html', context)
    
    else:  # POST
        try:
            export_type = request.POST.get('export_type', 'simple')
            
            if export_type == 'simple':
                # Excel semplice
                data = [
                    {'nome': 'Mario Rossi', 'eta': 30, 'citta': 'Milano', 'stipendio': 2500.50},
                    {'nome': 'Luigi Verdi', 'eta': 25, 'citta': 'Roma', 'stipendio': 2200.00},
                    {'nome': 'Anna Blu', 'eta': 35, 'citta': 'Napoli', 'stipendio': 2800.75},
                    {'nome': 'Paolo Neri', 'eta': 28, 'citta': 'Torino', 'stipendio': 2350.25},
                ]
                
                filename = f"demo_dipendenti_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                
                return create_simple_excel(
                    data=data,
                    filename=filename,
                    sheet_name='Dipendenti',
                    output_type='response'
                )
            
            elif export_type == 'styled':
                # Excel con styling
                data = [
                    {'prodotto': 'Laptop', 'categoria': 'Elettronica', 'prezzo': 899.99, 'quantita': 15},
                    {'prodotto': 'Mouse', 'categoria': 'Accessori', 'prezzo': 25.50, 'quantita': 50},
                    {'prodotto': 'Tastiera', 'categoria': 'Accessori', 'prezzo': 45.00, 'quantita': 30},
                    {'prodotto': 'Monitor', 'categoria': 'Elettronica', 'prezzo': 299.99, 'quantita': 8},
                ]
                
                columns = [
                    ColumnConfig(name='prodotto', data_type='text'),
                    ColumnConfig(name='categoria', data_type='text'),
                    ColumnConfig(name='prezzo', data_type='currency'),
                    ColumnConfig(name='quantita', data_type='integer'),
                ]
                
                config = ExcelConfig(
                    filename=f"demo_prodotti_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    sheet_name='Prodotti',
                    add_conditional_formatting=True,
                    add_charts=False
                )
                
                return generate_excel_from_data(
                    data=data,
                    columns=columns,
                    config=config,
                    output_type='response'
                )
            
            elif export_type == 'multisheet':
                # Multi-sheet Excel
                sheets_data = {
                    'Vendite': [
                        {'data': '2024-01-15', 'cliente': 'Cliente A', 'importo': 1500.00},
                        {'data': '2024-01-16', 'cliente': 'Cliente B', 'importo': 2200.50},
                        {'data': '2024-01-17', 'cliente': 'Cliente C', 'importo': 850.25},
                    ],
                    'Acquisti': [
                        {'data': '2024-01-10', 'fornitore': 'Fornitore X', 'importo': 800.00},
                        {'data': '2024-01-12', 'fornitore': 'Fornitore Y', 'importo': 1200.75},
                    ],
                    'Statistiche': [
                        {'mese': 'Gennaio', 'vendite': 4550.75, 'acquisti': 2000.75, 'margine': 2550.00},
                    ]
                }
                
                filename = f"demo_multisheet_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                config = ExcelConfig(filename=filename)
                
                return generate_excel_from_data(
                    data=[],  # Not used in multi-sheet
                    config=config,
                    sheets=sheets_data,
                    output_type='response'
                )
            
            else:
                messages.error(request, "Tipo export non supportato")
                return render(request, 'core/excel_demo.html')
                
        except Exception as e:
            logger.error(f"Errore generazione Excel demo: {e}")
            messages.error(request, f"Errore generazione Excel: {str(e)}")
            return render(request, 'core/excel_demo.html')


# =============================================================================
# CSV GENERATION VIEWS
# =============================================================================

@login_required
@require_http_methods(["GET", "POST"])
def csv_generator_demo(request):
    """Demo generazione CSV"""
    
    if request.method == "GET":
        context = {
            'page_title': 'Demo Generatore CSV',
        }
        return render(request, 'core/csv_demo.html', context)
    
    else:  # POST
        try:
            format_type = request.POST.get('format_type', 'standard')
            
            # Dati demo
            data = [
                {'nome': 'Mario Rossi', 'email': 'mario.rossi@email.it', 'telefono': '123-456-7890', 'eta': 30},
                {'nome': 'Luigi Verdi', 'email': 'luigi.verdi@email.it', 'telefono': '098-765-4321', 'eta': 25},
                {'nome': 'Anna Blu', 'email': 'anna.blu@email.it', 'telefono': '555-123-4567', 'eta': 35},
                {'nome': 'Paolo Neri', 'email': 'paolo.neri@email.it', 'telefono': '777-888-9999', 'eta': 28},
            ]
            
            filename = f"demo_contatti_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            if format_type == 'standard':
                return export_simple_csv(
                    data=data,
                    filename=filename,
                    output_type='response'
                )
            
            elif format_type == 'italian':
                return export_csv_italian_format(
                    data=data,
                    filename=filename,
                    output_type='response'
                )
            
            else:
                messages.error(request, "Formato CSV non supportato")
                return render(request, 'core/csv_demo.html')
                
        except Exception as e:
            logger.error(f"Errore generazione CSV demo: {e}")
            messages.error(request, f"Errore generazione CSV: {str(e)}")
            return render(request, 'core/csv_demo.html')


# =============================================================================
# FILE UPLOAD VIEWS
# =============================================================================

@login_required
@require_http_methods(["GET", "POST"])
def file_upload_demo(request):
    """Demo upload e gestione file"""
    
    if request.method == "GET":
        context = {
            'page_title': 'Demo Upload File',
        }
        return render(request, 'core/file_upload_demo.html', context)
    
    else:  # POST
        try:
            uploaded_file = request.FILES.get('demo_file')
            
            if not uploaded_file:
                messages.error(request, "Nessun file selezionato")
                return render(request, 'core/file_upload_demo.html')
            
            # Configurazione upload
            config = FileConfig(
                max_file_size=5 * 1024 * 1024,  # 5MB
                storage_path='demo_uploads',
                auto_optimize_images=True,
                generate_thumbnails=True
            )
            
            # Valida e salva file
            result = validate_and_store_file(
                file_obj=uploaded_file,
                filename=uploaded_file.name,
                config=config,
                subfolder='demo'
            )
            
            if result['success']:
                messages.success(
                    request, 
                    f"File '{result['original_name']}' caricato con successo! "
                    f"Dimensione: {result['size']} bytes"
                )
                
                # Log operazione
                logger.info(f"File caricato da {request.user}: {result['file_path']}")
                
                context = {
                    'page_title': 'Demo Upload File',
                    'upload_result': result
                }
                return render(request, 'core/file_upload_demo.html', context)
            else:
                error_msg = '; '.join(result['errors'])
                messages.error(request, f"Errore upload: {error_msg}")
                return render(request, 'core/file_upload_demo.html')
                
        except Exception as e:
            logger.error(f"Errore upload file demo: {e}")
            messages.error(request, f"Errore upload file: {str(e)}")
            return render(request, 'core/file_upload_demo.html')


# =============================================================================
# UTILITY VIEWS
# =============================================================================

@login_required
def utils_demo(request):
    """Demo utilities varie"""
    
    # Demo validatori
    test_cf = "RSSMRA80A01F205X"
    test_piva = "12345678901"
    test_iban = "IT60 X054 2811 1010 0000 0123 456"
    
    # Demo calcoli finanziari
    test_amount = 1000.00
    vat_calc = calculate_vat(test_amount, 22)
    
    # Demo statistiche
    test_values = [100, 200, 150, 300, 250, 180, 220]
    stats = statistical_summary(test_values)
    
    # Demo generatori
    unique_code = generate_unique_code(length=8, prefix="TEST-")
    
    context = {
        'page_title': 'Demo Utilities',
        'demos': {
            'validators': {
                'codice_fiscale': {
                    'input': test_cf,
                    'valid': validate_italian_tax_code(test_cf)
                },
                'partita_iva': {
                    'input': test_piva,
                    'valid': False  # Questo è un test, non è valida
                },
                'iban': {
                    'input': test_iban,
                    'valid': True  # Esempio
                }
            },
            'financial': {
                'base_amount': format_currency(test_amount),
                'vat_calculation': {
                    'net': format_currency(vat_calc['net']),
                    'vat': format_currency(vat_calc['vat']),
                    'gross': format_currency(vat_calc['gross'])
                }
            },
            'statistics': {
                'values': test_values,
                'stats': {
                    'count': stats.get('count', 0),
                    'mean': f"{float(stats.get('mean', 0)):.2f}",
                    'median': f"{float(stats.get('median', 0)):.2f}",
                    'min': float(stats.get('min', 0)),
                    'max': float(stats.get('max', 0))
                }
            },
            'generators': {
                'unique_code': unique_code
            }
        }
    }
    
    return render(request, 'core/utils_demo.html', context)


# =============================================================================
# API VIEWS
# =============================================================================

@login_required
@require_POST
def generate_code_api(request):
    """API per generazione codici"""
    try:
        length = int(request.POST.get('length', 8))
        prefix = request.POST.get('prefix', '')
        uppercase = request.POST.get('uppercase', 'true').lower() == 'true'
        
        code = generate_unique_code(
            length=length,
            prefix=prefix,
            uppercase=uppercase
        )
        
        return JsonResponse({
            'success': True,
            'code': code
        })
        
    except Exception as e:
        logger.error(f"Errore generazione codice API: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_POST
def validate_data_api(request):
    """API per validazione dati"""
    try:
        data_type = request.POST.get('type')
        value = request.POST.get('value', '')
        
        result = {'success': True, 'valid': False, 'message': ''}
        
        if data_type == 'codice_fiscale':
            result['valid'] = validate_italian_tax_code(value)
            result['message'] = 'Codice fiscale valido' if result['valid'] else 'Codice fiscale non valido'
        
        elif data_type == 'partita_iva':
            from .utils import validate_italian_vat
            result['valid'] = validate_italian_vat(value)
            result['message'] = 'P.IVA valida' if result['valid'] else 'P.IVA non valida'
        
        elif data_type == 'iban':
            from .utils import validate_iban
            result['valid'] = validate_iban(value)
            result['message'] = 'IBAN valido' if result['valid'] else 'IBAN non valido'
        
        else:
            result['success'] = False
            result['message'] = 'Tipo validazione non supportato'
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Errore validazione API: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def notifications_api(request):
    """API per ottenere contatori notifiche in tempo reale"""
    try:
        # Messaggi non letti
        unread_messages = Messaggio.objects.filter(
            destinatario=request.user, 
            letto=False
        ).count()
        
        # Promemoria attivi
        active_tasks = Promemoria.objects.filter(
            assegnato_a=request.user,
            completato=False
        ).count()
        
        # Promemoria scaduti
        overdue_tasks = Promemoria.objects.filter(
            assegnato_a=request.user,
            completato=False,
            data_scadenza__lt=date.today()
        ).count()
        
        return JsonResponse({
            'success': True,
            'unread_messages': unread_messages,
            'active_tasks': active_tasks,
            'overdue_tasks': overdue_tasks,
            'total_notifications': unread_messages + overdue_tasks
        })
        
    except Exception as e:
        logger.error(f"Errore API notifiche: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# =============================================================================
# CLASS-BASED VIEWS
# =============================================================================

@method_decorator(login_required, name='dispatch')
class CoreDashboardView(View):
    """Dashboard principale core utilities"""
    
    def get(self, request):
        context = {
            'page_title': 'Core Utilities Dashboard',
            'features': [
                {
                    'name': 'Generatore PDF',
                    'description': 'Crea PDF professionali da template',
                    'url': 'core:pdf_demo',
                    'icon': 'fas fa-file-pdf'
                },
                {
                    'name': 'Generatore Excel',
                    'description': 'Esporta dati in formato Excel avanzato',
                    'url': 'core:excel_demo',
                    'icon': 'fas fa-file-excel'
                },
                {
                    'name': 'Generatore CSV',
                    'description': 'Esporta dati in formato CSV',
                    'url': 'core:csv_demo',
                    'icon': 'fas fa-file-csv'
                },
                {
                    'name': 'Upload File',
                    'description': 'Carica e gestisce file in sicurezza',
                    'url': 'core:file_upload_demo',
                    'icon': 'fas fa-upload'
                },
                {
                    'name': 'Utilities',
                    'description': 'Validatori e funzioni utility',
                    'url': 'core:utils_demo',
                    'icon': 'fas fa-tools'
                }
            ]
        }
        return render(request, 'core/dashboard.html', context)


# =============================================================================
# ERROR HANDLERS
# =============================================================================

def handle_core_error(request, exception):
    """Handler errori per app core"""
    logger.error(f"Errore core per utente {request.user}: {exception}")
    
    context = {
        'error_message': 'Si è verificato un errore nelle utilities core.',
        'error_details': str(exception) if settings.DEBUG else None
    }
    
    return render(request, 'core/error.html', context, status=500)


# =============================================================================
# CHAT E MESSAGING VIEWS
# =============================================================================

@login_required
def dashboard(request):
    """Dashboard principale del sistema - homepage dopo login"""
    # Messaggi non letti per l'utente corrente
    messaggi_non_letti = Messaggio.objects.filter(
        destinatario=request.user, 
        letto=False
    ).count()
    
    # Messaggi recenti (ultimi 5)
    messaggi_ricevuti = Messaggio.objects.filter(
        destinatario=request.user
    ).select_related('mittente').order_by('-data_invio')[:5]
    
    # Promemoria attivi dell'utente
    promemoria_attivi = Promemoria.objects.filter(
        assegnato_a=request.user,
        completato=False
    ).count()
    
    # Promemoria scaduti
    promemoria_scaduti = Promemoria.objects.filter(
        assegnato_a=request.user,
        completato=False,
        data_scadenza__lt=date.today()
    ).count()
    
    # Promemoria recenti (ultimi 5)
    promemoria = Promemoria.objects.filter(
        Q(assegnato_a=request.user) | Q(creato_da=request.user)
    ).order_by('completato', 'data_scadenza')[:5]
    
    context = {
        'title': 'Dashboard Generale',
        'user': request.user,
        'messaggi_non_letti': messaggi_non_letti,
        'messaggi_ricevuti': messaggi_ricevuti,
        'promemoria_attivi': promemoria_attivi,
        'promemoria_scaduti': promemoria_scaduti,
        'promemoria': promemoria,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def chat(request):
    """Vista per la chat/messaggi"""
    # Lista di tutti gli utenti per poter inviare messaggi
    utenti = User.objects.exclude(pk=request.user.pk).filter(is_active=True)
    
    # Contatto selezionato (se presente)
    contatto_id = request.GET.get('contatto')
    contatto = None
    messaggi = None
    
    if contatto_id:
        try:
            contatto = User.objects.get(pk=contatto_id)
            # Messaggi tra l'utente corrente e il contatto
            messaggi = Messaggio.objects.filter(
                Q(mittente=request.user, destinatario=contatto) |
                Q(mittente=contatto, destinatario=request.user)
            ).order_by('data_invio')
            
            # Marca come letti i messaggi ricevuti da questo contatto
            Messaggio.objects.filter(
                mittente=contatto,
                destinatario=request.user,
                letto=False
            ).update(letto=True, data_lettura=timezone.now())
            
        except User.DoesNotExist:
            messages.error(request, "Utente non trovato")
    
    # Gestione invio messaggio
    if request.method == 'POST':
        destinatario_id = request.POST.get('destinatario')
        testo = request.POST.get('testo')
        allegato = request.FILES.get('allegato')
        
        if destinatario_id and testo:
            try:
                destinatario = User.objects.get(pk=destinatario_id)
                messaggio = Messaggio.objects.create(
                    mittente=request.user,
                    destinatario=destinatario,
                    testo=testo,
                    allegato=allegato
                )
                messages.success(request, "Messaggio inviato con successo")
                chat_url = reverse('core:chat')
                return redirect(f'{chat_url}?contatto={destinatario_id}')
            except User.DoesNotExist:
                messages.error(request, "Destinatario non trovato")
    
    context = {
        'utenti': utenti,
        'contatto': contatto,
        'messaggi': messaggi,
        'title': 'Chat e Messaggi'
    }
    return render(request, 'core/chat.html', context)


# =============================================================================
# PROMEMORIA VIEWS
# =============================================================================

@login_required 
def promemoria_list(request):
    """Lista dei promemoria"""
    # Base query: promemoria assegnati o creati dall'utente
    base_query = Q(assegnato_a=request.user) | Q(creato_da=request.user)
    
    # Se l'utente è amministratore/contabile o staff, può vedere tutti i promemoria di scadenze documenti
    if (request.user.is_staff or 
        (hasattr(request.user, 'livello') and request.user.livello in ['amministratore', 'contabile'])):
        # Aggiungi promemoria di scadenze documenti (riconosciuti dal titolo)
        base_query |= Q(titolo__icontains='in scadenza')
    
    promemoria_list = Promemoria.objects.filter(base_query).order_by('completato', 'data_scadenza')
    
    # Paginazione
    paginator = Paginator(promemoria_list, 20)
    page = request.GET.get('page')
    promemoria = paginator.get_page(page)
    
    context = {
        'promemoria': promemoria,
        'title': 'I Miei Promemoria'
    }
    return render(request, 'core/promemoria_list.html', context)


@login_required
def promemoria_create(request):
    """Creazione nuovo promemoria"""
    if request.method == 'POST':
        titolo = request.POST.get('titolo')
        descrizione = request.POST.get('descrizione')
        data_scadenza = request.POST.get('data_scadenza')
        priorita = request.POST.get('priorita', 'media')
        assegnato_a_id = request.POST.get('assegnato_a')
        
        if titolo:
            try:
                assegnato_a = User.objects.get(pk=assegnato_a_id) if assegnato_a_id else request.user
                
                promemoria = Promemoria.objects.create(
                    titolo=titolo,
                    descrizione=descrizione,
                    data_scadenza=data_scadenza if data_scadenza else None,
                    priorita=priorita,
                    creato_da=request.user,
                    assegnato_a=assegnato_a
                )
                messages.success(request, "Promemoria creato con successo")
                return redirect('core:promemoria_list')
            except User.DoesNotExist:
                messages.error(request, "Utente assegnatario non trovato")
    
    # Lista utenti per assegnazione
    utenti = User.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username')
    
    context = {
        'utenti': utenti,
        'title': 'Nuovo Promemoria'
    }
    return render(request, 'core/promemoria_form.html', context)


@login_required
def promemoria_update(request, pk):
    """Modifica promemoria"""
    promemoria = get_object_or_404(Promemoria, pk=pk)
    
    # Controllo permessi - permettiamo al destinatario, al creatore, o agli amministratori/contabili  
    has_permission = (
        promemoria.assegnato_a == request.user or 
        promemoria.creato_da == request.user or
        request.user.is_staff or
        (hasattr(request.user, 'livello') and request.user.livello in ['amministratore', 'contabile'])
    )
    
    if not has_permission:
        messages.error(request, "Non hai i permessi per modificare questo promemoria")
        return redirect('core:promemoria_list')
    
    if request.method == 'POST':
        titolo = request.POST.get('titolo')
        descrizione = request.POST.get('descrizione')
        data_scadenza = request.POST.get('data_scadenza')
        priorita = request.POST.get('priorita', 'media')
        assegnato_a_id = request.POST.get('assegnato_a')
        
        if titolo:
            try:
                assegnato_a = User.objects.get(pk=assegnato_a_id) if assegnato_a_id else promemoria.assegnato_a
                
                promemoria.titolo = titolo
                promemoria.descrizione = descrizione
                promemoria.data_scadenza = data_scadenza if data_scadenza else None
                promemoria.priorita = priorita
                promemoria.assegnato_a = assegnato_a
                promemoria.save()
                
                messages.success(request, "Promemoria aggiornato con successo")
                return redirect('core:promemoria_list')
            except User.DoesNotExist:
                messages.error(request, "Utente assegnatario non trovato")
    
    # Lista utenti per assegnazione
    utenti = User.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username')
    
    context = {
        'promemoria': promemoria,
        'utenti': utenti,
        'title': 'Modifica Promemoria'
    }
    return render(request, 'core/promemoria_form.html', context)


@login_required
def promemoria_toggle(request, pk):
    """Toggle stato completato del promemoria"""
    promemoria = get_object_or_404(Promemoria, pk=pk)

    # Controllo permessi - permettiamo al destinatario, al creatore, o agli amministratori/contabili
    # Gli utenti assegnati possono solo completare/riaprire, non eliminare
    has_permission = (
        promemoria.assegnato_a == request.user or
        promemoria.creato_da == request.user or
        request.user.is_staff or
        (hasattr(request.user, 'livello') and request.user.livello in ['amministratore', 'contabile'])
    )
    
    if not has_permission:
        messages.error(request, "Non hai i permessi per modificare questo promemoria")
        return redirect('core:promemoria_list')
    
    if promemoria.completato:
        promemoria.completato = False
        promemoria.data_completamento = None
        messages.success(request, "Promemoria riaperto")
    else:
        promemoria.completato = True
        promemoria.data_completamento = timezone.now()
        messages.success(request, "Promemoria completato!")
    
    promemoria.save()
    
    # Redirect al next se specificato
    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)
    
    return redirect('core:promemoria_list')


@login_required
def promemoria_delete(request, pk):
    """Elimina promemoria"""
    promemoria = get_object_or_404(Promemoria, pk=pk)

    # NUOVA LOGICA: Solo il creatore del promemoria può eliminarlo
    # (oppure amministratori/contabili per promemoria di sistema)
    can_delete = (
        promemoria.creato_da == request.user or
        request.user.is_staff or
        (hasattr(request.user, 'livello') and request.user.livello in ['amministratore', 'contabile'])
    )

    if not can_delete:
        if promemoria.assegnato_a == request.user:
            messages.error(request, "Non puoi eliminare questo promemoria perché non l'hai creato tu. Puoi solo completarlo.")
        else:
            messages.error(request, "Non hai i permessi per eliminare questo promemoria")
        return redirect('core:promemoria_list')

    if request.method == 'POST':
        promemoria.delete()
        messages.success(request, "Promemoria eliminato con successo")
        return redirect('core:promemoria_list')

    context = {
        'promemoria': promemoria,
        'title': 'Elimina Promemoria'
    }
    return render(request, 'core/promemoria_delete.html', context)


# =============================================================================
# EMAIL VIEWS
# =============================================================================

@login_required
def email_messages(request):
    """Vista per visualizzare anteprima messaggi email"""
    from preventivi.models import RichiestaPreventivo
    from anagrafica.models import Fornitore
    
    # Recupera una richiesta di esempio per l'anteprima
    richiesta_esempio = RichiestaPreventivo.objects.filter(
        stato__in=['BOZZA', 'INVIATO_FORNITORI']
    ).first()
    
    # Recupera un fornitore di esempio
    fornitore_esempio = Fornitore.objects.filter(attivo=True).first()
    
    # Se non ci sono dati, crea dei dati di esempio
    if not richiesta_esempio:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        richiesta_esempio = type('obj', (object,), {
            'numero': 'PREV-DEMO-001',
            'titolo': 'Richiesta Preventivo di Esempio',
            'descrizione': 'Questa è una descrizione di esempio per mostrare l\'anteprima email.',
            'data_scadenza': timezone.now().date() + timezone.timedelta(days=30),
            'richiedente': request.user,
            'operatore': request.user
        })()
    
    if not fornitore_esempio:
        fornitore_esempio = type('obj', (object,), {
            'nome': 'Fornitore di Esempio S.r.l.',
            'email': 'fornitore@esempio.it'
        })()
    
    context = {
        'page_title': 'Anteprima Messaggi Email',
        'richiesta': richiesta_esempio,
        'fornitore': fornitore_esempio,
        'operatore': richiesta_esempio.operatore if hasattr(richiesta_esempio, 'operatore') else request.user,
        'scadenza': richiesta_esempio.data_scadenza,
        'data_invio': timezone.now(),
    }
    
    return render(request, 'core/email_messages.html', context)