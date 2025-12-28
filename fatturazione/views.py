"""
FATTURAZIONE VIEWS - Sistema gestione fatturazione passiva
========================================================

Views per gestire l'intero workflow della fatturazione passiva:
- DashboardView: Dashboard principale con statistiche
- FatturaListView: Lista fatture con filtri avanzati
- FatturaCreateView/UpdateView: Gestione CRUD fatture
- FatturaDetailView: Dettaglio fattura con azioni workflow
- WorkflowActionView: Gestione transizioni di stato
- Export views: PDF/Excel/CSV export
- AJAX views: Azioni rapide e search

Adattato da AMM/fatturazione per progetto Management con:
- Single-page responsive design
- Bootstrap 4 UI components
- AJAX real-time interactions
- Workflow state management
- File upload integration
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.views.decorators.http import require_http_methods, require_POST
from django.http import JsonResponse, HttpResponse, Http404
from django.db.models import Q, Count, Sum, Case, When, DecimalField
from django.utils import timezone
from django.core.paginator import Paginator
from django.urls import reverse_lazy, reverse
from django.db import transaction
from django.conf import settings
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from .models import (
    FatturaFornitore, 
    DettaglioFattura, 
    ScadenzaPagamento, 
    ComunicazioneFatturato
)
from .forms import (
    FatturaFornitoreForm, 
    DettaglioFatturaFormSet,
    FatturaSearchForm, 
    ComunicazioneFatturatoForm,
    ScadenzaPagamentoForm,
    WorkflowActionForm,
    ExportOrdiniForm
)
from anagrafica.models import Fornitore
from core.models import Allegato

logger = logging.getLogger(__name__)


class DashboardView(LoginRequiredMixin, ListView):
    """
    Dashboard principale fatturazione passiva con statistiche e fatture recenti
    """
    model = FatturaFornitore
    template_name = 'fatturazione/dashboard.html'
    context_object_name = 'fatture_recenti'
    paginate_by = 10
    
    def get_queryset(self):
        return FatturaFornitore.objects.select_related('fornitore').order_by('-created_at')[:10]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistiche generali
        stats = {
            'totali': FatturaFornitore.objects.count(),
            'in_attesa': FatturaFornitore.objects.filter(stato='ATTESA').count(),
            'ricevute': FatturaFornitore.objects.filter(stato='RICEVUTA').count(),
            'controllate': FatturaFornitore.objects.filter(stato='CONTROLLATA').count(),
            'contabilizzate': FatturaFornitore.objects.filter(stato='CONTABILIZZATA').count(),
            'programmate': FatturaFornitore.objects.filter(stato='PROGRAMMATA').count(),
            'pagate': FatturaFornitore.objects.filter(stato='PAGATA').count(),
            'scadute': FatturaFornitore.objects.filter(
                data_scadenza__lt=timezone.now().date(),
                stato__in=['RICEVUTA', 'CONTROLLATA', 'CONTABILIZZATA', 'PROGRAMMATA']
            ).count(),
            'in_scadenza': FatturaFornitore.objects.filter(
                data_scadenza__lte=timezone.now().date() + timedelta(days=7),
                data_scadenza__gte=timezone.now().date(),
                stato__in=['RICEVUTA', 'CONTROLLATA', 'CONTABILIZZATA', 'PROGRAMMATA']
            ).count(),
        }
        
        # Importi per stato
        importi = FatturaFornitore.objects.aggregate(
            totale_attesa=Sum(
                Case(When(stato='ATTESA', then='importo_totale'), 
                     default=0, output_field=DecimalField())
            ),
            totale_da_pagare=Sum(
                Case(When(stato__in=['RICEVUTA', 'CONTROLLATA', 'CONTABILIZZATA', 'PROGRAMMATA'], 
                         then='importo_totale'),
                     default=0, output_field=DecimalField())
            ),
            totale_pagato=Sum(
                Case(When(stato='PAGATA', then='importo_totale'),
                     default=0, output_field=DecimalField())
            )
        )
        
        # Fatture da controllare (priorità alta/urgente)
        fatture_prioritarie = FatturaFornitore.objects.filter(
            priorita_pagamento__in=['ALTA', 'URGENTE', 'CRITICA'],
            stato__in=['RICEVUTA', 'CONTROLLATA', 'CONTABILIZZATA', 'PROGRAMMATA']
        ).select_related('fornitore').order_by('data_scadenza', '-priorita_pagamento')[:5]
        
        # Scadenze prossime
        scadenze_prossime = ScadenzaPagamento.objects.filter(
            data_scadenza__lte=timezone.now().date() + timedelta(days=7),
            stato='PIANIFICATA'
        ).select_related('fattura', 'fattura__fornitore').order_by('data_scadenza')[:5]
        
        context.update({
            'stats': stats,
            'importi': importi,
            'fatture_prioritarie': fatture_prioritarie,
            'scadenze_prossime': scadenze_prossime,
        })
        
        return context


@login_required
def registra_fattura(request):
    """
    View per registrare una nuova fattura fornitore
    """
    if request.method == 'POST':
        form = FatturaFornitoreForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    fattura = form.save()
                    
                    messages.success(
                        request,
                        f"Fattura {fattura.numero_protocollo} registrata con successo!"
                    )
                    
                    # Log della creazione
                    logger.info(f"Fattura {fattura.numero_protocollo} creata da {request.user}")
                    
                    return redirect('fatturazione:dashboard')
                    
            except Exception as e:
                messages.error(
                    request,
                    f"Errore durante la registrazione della fattura: {str(e)}"
                )
                logger.error(f"Errore registrazione fattura: {str(e)}")
        else:
            messages.error(
                request,
                "Ci sono errori nel form. Controllare i dati inseriti."
            )
    else:
        form = FatturaFornitoreForm(user=request.user)
    
    context = {
        'form': form,
        'page_title': 'Registra Nuova Fattura'
    }
    
    return render(request, 'fatturazione/registra_fattura.html', context)


@login_required
def get_ordini_by_fornitore(request):
    """
    Endpoint AJAX per ottenere ordini filtrati per fornitore
    """
    fornitore_id = request.GET.get('fornitore_id')
    
    if not fornitore_id:
        return JsonResponse({'ordini': []})
    
    try:
        from acquisti.models import OrdineAcquisto
        
        ordini = OrdineAcquisto.objects.filter(
            fornitore_id=fornitore_id,
            stato__in=['CREATO', 'RICEVUTO']
        ).order_by('-data_ordine')
        
        ordini_data = []
        for ordine in ordini:
            ordini_data.append({
                'id': ordine.id,
                'numero_ordine': ordine.numero_ordine,
                'data_ordine': ordine.data_ordine.strftime('%d/%m/%Y'),
                'importo_totale': float(ordine.importo_totale),
                'stato': ordine.get_stato_display(),
                'display': f"{ordine.numero_ordine} - {ordine.data_ordine.strftime('%d/%m/%Y')} - €{ordine.importo_totale:,.2f}"
            })
        
        return JsonResponse({
            'ordini': ordini_data,
            'count': len(ordini_data)
        })
        
    except Exception as e:
        logger.error(f"Errore get_ordini_by_fornitore: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def export_ordini_form(request):
    """
    Form per configurare l'export degli ordini di acquisto
    """
    if request.method == 'POST':
        form = ExportOrdiniForm(request.POST)
        if form.is_valid():
            # Redirect alla view di export con parametri
            params = {
                'data_da': form.cleaned_data['data_da'].strftime('%Y-%m-%d'),
                'data_a': form.cleaned_data['data_a'].strftime('%Y-%m-%d'),
                'formato': form.cleaned_data['formato'],
                'includi_iva': '1' if form.cleaned_data['includi_iva'] else '0',
                'aliquota_iva': str(form.cleaned_data['aliquota_iva']),
                'raggruppa_per_fornitore': '1' if form.cleaned_data['raggruppa_per_fornitore'] else '0',
            }
            
            if form.cleaned_data.get('fornitore'):
                params['fornitore_id'] = form.cleaned_data['fornitore'].id
            
            if form.cleaned_data.get('stato'):
                params['stato'] = form.cleaned_data['stato']
            
            from django.http import QueryDict
            query_string = QueryDict('', mutable=True)
            query_string.update(params)
            
            return redirect(f"{reverse('fatturazione:export_ordini')}?{query_string.urlencode()}")
    else:
        form = ExportOrdiniForm()
    
    context = {
        'form': form,
        'page_title': 'Export Ordini di Acquisto'
    }
    
    return render(request, 'fatturazione/export_ordini_form.html', context)


@login_required 
def export_ordini(request):
    """
    Export ordini di acquisto in vari formati
    """
    # Recupera parametri dalla query string
    data_da_str = request.GET.get('data_da')
    data_a_str = request.GET.get('data_a')
    formato = request.GET.get('formato', 'csv')
    fornitore_id = request.GET.get('fornitore_id')
    stato = request.GET.get('stato')
    includi_iva = request.GET.get('includi_iva', '1') == '1'
    aliquota_iva = Decimal(request.GET.get('aliquota_iva', '22.00'))
    raggruppa_per_fornitore = request.GET.get('raggruppa_per_fornitore', '1') == '1'
    
    if not data_da_str or not data_a_str:
        messages.error(request, "Parametri data mancanti")
        return redirect('fatturazione:export_ordini_form')
    
    try:
        from datetime import datetime
        data_da = datetime.strptime(data_da_str, '%Y-%m-%d').date()
        data_a = datetime.strptime(data_a_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Formato date non valido")
        return redirect('fatturazione:export_ordini_form')
    
    # Costruisci queryset ordini
    from acquisti.models import OrdineAcquisto
    from datetime import datetime, time
    from django.utils import timezone
    
    # Converte le date in datetime per includere tutto il giorno finale
    data_da_dt = datetime.combine(data_da, time.min)  # 00:00:00
    data_a_dt = datetime.combine(data_a, time.max)    # 23:59:59.999999
    
    # Rende timezone-aware se necessario
    if timezone.is_naive(data_da_dt):
        data_da_dt = timezone.make_aware(data_da_dt)
    if timezone.is_naive(data_a_dt):
        data_a_dt = timezone.make_aware(data_a_dt)
    
    ordini = OrdineAcquisto.objects.filter(
        data_ordine__range=[data_da_dt, data_a_dt]
    ).select_related('fornitore', 'creato_da')
    
    if fornitore_id:
        ordini = ordini.filter(fornitore_id=fornitore_id)
    
    if stato:
        ordini = ordini.filter(stato=stato)
    
    if raggruppa_per_fornitore:
        ordini = ordini.order_by('fornitore__nome', '-data_ordine')
    else:
        ordini = ordini.order_by('-data_ordine')
    
    # Genera export in base al formato
    if formato == 'csv':
        return _export_ordini_csv(ordini, data_da, data_a, includi_iva, aliquota_iva, raggruppa_per_fornitore)
    elif formato == 'excel':
        return _export_ordini_excel(ordini, data_da, data_a, includi_iva, aliquota_iva, raggruppa_per_fornitore)
    elif formato == 'pdf':
        return _export_ordini_pdf(ordini, data_da, data_a, includi_iva, aliquota_iva, raggruppa_per_fornitore)
    else:
        messages.error(request, "Formato non supportato")
        return redirect('fatturazione:export_ordini_form')


def _export_ordini_csv(ordini, data_da, data_a, includi_iva, aliquota_iva, raggruppa_per_fornitore):
    """Export CSV degli ordini usando core.csv_generator"""
    from core.csv_generator import generate_csv_from_data, CSVConfig

    # Prepara dati per CSV
    data = []
    fornitore_corrente = None
    subtotale_netto = Decimal('0')
    subtotale_lordo = Decimal('0')
    totale_generale_netto = Decimal('0')
    totale_generale_lordo = Decimal('0')

    for ordine in ordini:
        # Gestione raggruppamento per fornitore
        if raggruppa_per_fornitore and fornitore_corrente != ordine.fornitore.nome:
            if fornitore_corrente is not None:
                # Aggiungi riga subtotale
                subtotal_row = {
                    'Numero Ordine': f'SUBTOTALE {fornitore_corrente}:',
                    'Fornitore': '',
                    'Data Ordine': '',
                    'Data Consegna': '',
                    'Importo Netto': float(subtotale_netto),
                    'Stato': '',
                    'Termini Pagamento': '',
                    'Tempi Consegna': '',
                    'Note': ''
                }
                if includi_iva:
                    subtotal_row[f'IVA ({aliquota_iva}%)'] = ''
                    subtotal_row['Totale Lordo'] = float(subtotale_lordo)
                data.append(subtotal_row)
                # Riga vuota
                data.append({k: '' for k in subtotal_row.keys()})

            fornitore_corrente = ordine.fornitore.nome
            subtotale_netto = Decimal('0')
            subtotale_lordo = Decimal('0')

        # Calcoli IVA
        importo_iva = ordine.importo_totale * (aliquota_iva / 100) if includi_iva else Decimal('0')
        importo_lordo = ordine.importo_totale + importo_iva

        # Riga dati
        row = {
            'Numero Ordine': ordine.numero_ordine,
            'Fornitore': ordine.fornitore.nome,
            'Data Ordine': ordine.data_ordine,
            'Data Consegna': ordine.data_consegna_richiesta,
            'Importo Netto': float(ordine.importo_totale),
            'Stato': ordine.get_stato_display(),
            'Termini Pagamento': ordine.termini_pagamento,
            'Tempi Consegna': ordine.tempi_consegna,
            'Note': ordine.note_ordine or ''
        }

        if includi_iva:
            row[f'IVA ({aliquota_iva}%)'] = float(importo_iva)
            row['Totale Lordo'] = float(importo_lordo)

        data.append(row)

        # Aggiorna subtotali
        subtotale_netto += ordine.importo_totale
        subtotale_lordo += importo_lordo
        totale_generale_netto += ordine.importo_totale
        totale_generale_lordo += importo_lordo

    # Ultimo subtotale se raggruppato
    if raggruppa_per_fornitore and fornitore_corrente:
        subtotal_row = {
            'Numero Ordine': f'SUBTOTALE {fornitore_corrente}:',
            'Fornitore': '',
            'Data Ordine': '',
            'Data Consegna': '',
            'Importo Netto': float(subtotale_netto),
            'Stato': '',
            'Termini Pagamento': '',
            'Tempi Consegna': '',
            'Note': ''
        }
        if includi_iva:
            subtotal_row[f'IVA ({aliquota_iva}%)'] = ''
            subtotal_row['Totale Lordo'] = float(subtotale_lordo)
        data.append(subtotal_row)
        data.append({k: '' for k in subtotal_row.keys()})

    # Totale generale
    total_row = {
        'Numero Ordine': 'TOTALE GENERALE:',
        'Fornitore': '',
        'Data Ordine': '',
        'Data Consegna': '',
        'Importo Netto': float(totale_generale_netto),
        'Stato': '',
        'Termini Pagamento': '',
        'Tempi Consegna': '',
        'Note': ''
    }
    if includi_iva:
        total_row[f'IVA ({aliquota_iva}%)'] = ''
        total_row['Totale Lordo'] = float(totale_generale_lordo)
    data.append(total_row)

    # Configurazione CSV (formato italiano)
    config = CSVConfig(
        filename=f"ordini_acquisto_{data_da}_{data_a}.csv",
        delimiter=';',
        decimal_separator=',',
        date_format='%d/%m/%Y'
    )

    return generate_csv_from_data(
        data=data,
        config=config,
        output_type='response'
    )


def _export_ordini_excel(ordini, data_da, data_a, includi_iva, aliquota_iva, raggruppa_per_fornitore):
    """Export Excel degli ordini usando core.excel_generator"""
    from core.excel_generator import generate_excel_from_data, ExcelConfig

    # Prepara dati per Excel
    data = []
    fornitore_corrente = None
    subtotale_netto = Decimal('0')
    subtotale_lordo = Decimal('0')
    totale_generale_netto = Decimal('0')
    totale_generale_lordo = Decimal('0')

    for ordine in ordini:
        # Gestione raggruppamento per fornitore
        if raggruppa_per_fornitore and fornitore_corrente != ordine.fornitore.nome:
            if fornitore_corrente is not None:
                # Aggiungi riga subtotale
                subtotal_row = {
                    'Numero Ordine': f'SUBTOTALE {fornitore_corrente}:',
                    'Fornitore': '',
                    'Data Ordine': '',
                    'Data Consegna': '',
                    'Importo Netto (€)': float(subtotale_netto),
                    'Stato': '',
                    'Termini Pagamento': '',
                    'Tempi Consegna': '',
                    'Note': ''
                }
                if includi_iva:
                    subtotal_row[f'IVA {aliquota_iva}% (€)'] = ''
                    subtotal_row['Totale Lordo (€)'] = float(subtotale_lordo)
                data.append(subtotal_row)
                # Riga vuota
                data.append({k: '' for k in subtotal_row.keys()})

            fornitore_corrente = ordine.fornitore.nome
            subtotale_netto = Decimal('0')
            subtotale_lordo = Decimal('0')

        # Calcoli IVA
        importo_iva = ordine.importo_totale * (aliquota_iva / 100) if includi_iva else Decimal('0')
        importo_lordo = ordine.importo_totale + importo_iva

        # Riga dati
        row = {
            'Numero Ordine': ordine.numero_ordine,
            'Fornitore': ordine.fornitore.nome,
            'Data Ordine': ordine.data_ordine,
            'Data Consegna': ordine.data_consegna_richiesta,
            'Importo Netto (€)': float(ordine.importo_totale),
            'Stato': ordine.get_stato_display(),
            'Termini Pagamento': ordine.termini_pagamento,
            'Tempi Consegna': ordine.tempi_consegna,
            'Note': ordine.note_ordine or ''
        }

        if includi_iva:
            row[f'IVA {aliquota_iva}% (€)'] = float(importo_iva)
            row['Totale Lordo (€)'] = float(importo_lordo)

        data.append(row)

        # Aggiorna subtotali
        subtotale_netto += ordine.importo_totale
        subtotale_lordo += importo_lordo
        totale_generale_netto += ordine.importo_totale
        totale_generale_lordo += importo_lordo

    # Ultimo subtotale se raggruppato
    if raggruppa_per_fornitore and fornitore_corrente:
        subtotal_row = {
            'Numero Ordine': f'SUBTOTALE {fornitore_corrente}:',
            'Fornitore': '',
            'Data Ordine': '',
            'Data Consegna': '',
            'Importo Netto (€)': float(subtotale_netto),
            'Stato': '',
            'Termini Pagamento': '',
            'Tempi Consegna': '',
            'Note': ''
        }
        if includi_iva:
            subtotal_row[f'IVA {aliquota_iva}% (€)'] = ''
            subtotal_row['Totale Lordo (€)'] = float(subtotale_lordo)
        data.append(subtotal_row)
        data.append({k: '' for k in subtotal_row.keys()})

    # Totale generale
    total_row = {
        'Numero Ordine': 'TOTALE GENERALE:',
        'Fornitore': '',
        'Data Ordine': '',
        'Data Consegna': '',
        'Importo Netto (€)': float(totale_generale_netto),
        'Stato': '',
        'Termini Pagamento': '',
        'Tempi Consegna': '',
        'Note': ''
    }
    if includi_iva:
        total_row[f'IVA {aliquota_iva}% (€)'] = ''
        total_row['Totale Lordo (€)'] = float(totale_generale_lordo)
    data.append(total_row)

    # Configurazione Excel
    config = ExcelConfig(
        filename=f"ordini_acquisto_{data_da}_{data_a}.xlsx",
        sheet_name="Ordini di Acquisto",
        auto_fit_columns=True,
        add_filters=True,
        add_table_style=True,
        freeze_panes="A2"
    )

    return generate_excel_from_data(
        data=data,
        config=config,
        output_type='response'
    )


def _export_ordini_pdf(ordini, data_da, data_a, includi_iva, aliquota_iva, raggruppa_per_fornitore):
    """Export PDF degli ordini"""
    from core.pdf_generator import generate_pdf_from_html, PDFConfig
    from django.template.loader import render_to_string
    
    # Prepara dati per template
    ordini_list = []
    fornitori_subtotali = {}
    fornitore_corrente = None
    subtotale_netto = Decimal('0')
    subtotale_lordo = Decimal('0')
    totale_generale_netto = Decimal('0')
    totale_generale_lordo = Decimal('0')
    
    for ordine in ordini:
        # Calcoli IVA
        importo_iva = ordine.importo_totale * (aliquota_iva / 100) if includi_iva else Decimal('0')
        importo_lordo = ordine.importo_totale + importo_iva
        
        ordine_data = {
            'ordine': ordine,
            'importo_iva': importo_iva,
            'importo_lordo': importo_lordo,
            'is_new_fornitore': False
        }
        
        if raggruppa_per_fornitore and fornitore_corrente != ordine.fornitore.nome:
            if fornitore_corrente is not None:
                # Salva subtotale del fornitore precedente
                fornitori_subtotali[fornitore_corrente] = {
                    'netto': subtotale_netto,
                    'lordo': subtotale_lordo
                }
            
            ordine_data['is_new_fornitore'] = True
            fornitore_corrente = ordine.fornitore.nome
            subtotale_netto = Decimal('0')
            subtotale_lordo = Decimal('0')
        
        ordini_list.append(ordine_data)
        
        # Aggiorna totali
        subtotale_netto += ordine.importo_totale
        subtotale_lordo += importo_lordo
        totale_generale_netto += ordine.importo_totale
        totale_generale_lordo += importo_lordo
    
    # Ultimo subtotale
    if raggruppa_per_fornitore and fornitore_corrente:
        fornitori_subtotali[fornitore_corrente] = {
            'netto': subtotale_netto,
            'lordo': subtotale_lordo
        }
    
    # Context per template
    context = {
        'ordini_list': ordini_list,
        'data_da': data_da,
        'data_a': data_a,
        'includi_iva': includi_iva,
        'aliquota_iva': aliquota_iva,
        'raggruppa_per_fornitore': raggruppa_per_fornitore,
        'fornitori_subtotali': fornitori_subtotali,
        'totale_generale_netto': totale_generale_netto,
        'totale_generale_lordo': totale_generale_lordo,
        'numero_ordini': len(ordini_list)
    }
    
    # Render HTML
    html_content = render_to_string('fatturazione/export_ordini_pdf.html', context)
    
    # Genera PDF
    config = PDFConfig(
        page_size='A4',
        orientation='landscape',
        margins={'top': 1.5, 'bottom': 1.5, 'left': 1.0, 'right': 1.0},
        filename=f"ordini_acquisto_{data_da}_{data_a}.pdf"
    )
    
    return generate_pdf_from_html(
        html_content=html_content,
        config=config,
        output_type='response'
    )


@login_required
def export_fatture_csv(request):
    """
    Export CSV lista fatture usando core.csv_generator
    """
    from core.csv_generator import generate_csv_from_data, CSVConfig

    fatture = FatturaFornitore.objects.select_related('fornitore')

    # Prepara dati
    data = []
    for fattura in fatture:
        data.append({
            'Numero Protocollo': fattura.numero_protocollo,
            'Numero Fattura': fattura.numero_fattura,
            'Fornitore': fattura.fornitore.nome,
            'Data Fattura': fattura.data_fattura,
            'Data Scadenza': fattura.data_scadenza,
            'Importo Totale': float(fattura.importo_totale),
            'Stato': fattura.get_stato_display(),
            'Priorità': fattura.get_priorita_pagamento_display()
        })

    # Configurazione CSV (formato italiano)
    config = CSVConfig(
        filename='fatture_fornitori.csv',
        delimiter=';',
        decimal_separator=',',
        date_format='%d/%m/%Y'
    )

    return generate_csv_from_data(
        data=data,
        config=config,
        output_type='response'
    )