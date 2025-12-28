"""
ACQUISTI VIEWS - Sistema gestione ordini di acquisto
===================================================

Views per:
- Dashboard con ordini da ricevere e ricevuti
- Creazione manuale ordini
- Gestione stati ordini
- Ricerca e filtri
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta
import logging

from .models import OrdineAcquisto
from .forms import RicercaOrdiniForm, CreaOrdineForm, CambiaStatoOrdineForm, OrdineDettaglioForm
from anagrafica.models import Fornitore

logger = logging.getLogger(__name__)


@login_required
def dashboard(request):
    """
    Dashboard principale ordini di acquisto
    Tutto in una pagina: ordini da ricevere + ordini ricevuti + form ricerca
    """
    
    # Form di ricerca
    form_ricerca = RicercaOrdiniForm(request.GET or None)
    
    # Ordini da ricevere (stato CREATO)
    ordini_da_ricevere = OrdineAcquisto.objects.filter(
        stato='CREATO'
    ).select_related('fornitore', 'creato_da').order_by('-data_ordine')
    
    # Ordini ricevuti (ultimi 10 - stati RICEVUTO/PAGATO)
    ordini_ricevuti_base = OrdineAcquisto.objects.filter(
        stato__in=['RICEVUTO', 'PAGATO']
    ).select_related('fornitore', 'ricevuto_da', 'preventivo_originale__richiesta')
    
    # Applica filtri di ricerca agli ordini ricevuti
    if form_ricerca.is_valid():
        ordini_ricevuti_base = form_ricerca.filter_queryset(ordini_ricevuti_base)
    
    # Ordini ricevuti con paginazione (10 per pagina)
    paginator = Paginator(ordini_ricevuti_base.order_by('-data_ricevimento'), 10)
    page_number = request.GET.get('page', 1)
    ordini_ricevuti = paginator.get_page(page_number)
    
    # Statistiche quick
    stats = {
        'totale_da_ricevere': ordini_da_ricevere.count(),
        'totale_ricevuti_oggi': OrdineAcquisto.objects.filter(
            stato__in=['RICEVUTO', 'PAGATO'],
            data_ricevimento__date=timezone.now().date()
        ).count(),
        'totale_ordini_mese': OrdineAcquisto.objects.filter(
            data_ordine__gte=timezone.now().replace(day=1)
        ).count(),
    }
    
    context = {
        'ordini_da_ricevere': ordini_da_ricevere,
        'ordini_ricevuti': ordini_ricevuti,
        'form_ricerca': form_ricerca,
        'stats': stats,
        'current_filters': request.GET.dict(),
    }
    
    return render(request, 'acquisti/dashboard.html', context)


@login_required
def crea_ordine(request):
    """
    Creazione manuale ordine di acquisto
    """
    if request.method == 'POST':
        form = CreaOrdineForm(request.POST)
        if form.is_valid():
            ordine = form.save(commit=False)
            ordine.creato_da = request.user
            ordine.save()
            
            # Invio automatico email al fornitore
            try:
                email_inviata = send_email_ordine_creato(ordine)
                if email_inviata:
                    messages.success(
                        request, 
                        f"Ordine {ordine.numero_ordine} creato con successo! Email inviata a {ordine.fornitore.nome}"
                    )
                else:
                    messages.success(
                        request, 
                        f"Ordine {ordine.numero_ordine} creato con successo!"
                    )
                    messages.warning(
                        request,
                        f"Attenzione: non è stato possibile inviare l'email a {ordine.fornitore.nome}. Verificare l'indirizzo email."
                    )
            except Exception as e:
                messages.success(
                    request, 
                    f"Ordine {ordine.numero_ordine} creato con successo!"
                )
                messages.error(
                    request,
                    f"Errore durante l'invio email: {str(e)}"
                )
            
            return redirect('acquisti:dashboard')
    else:
        form = CreaOrdineForm()
    
    context = {
        'form': form,
        'page_title': 'Crea Nuovo Ordine di Acquisto'
    }
    
    return render(request, 'acquisti/crea_ordine.html', context)


@login_required
def dettaglio_ordine(request, pk):
    """
    Dettaglio ordine con possibilità di modifica stato
    """
    ordine = get_object_or_404(
        OrdineAcquisto.objects.select_related(
            'fornitore', 'creato_da', 'ricevuto_da', 'pagato_da', 'preventivo_originale__richiesta'
        ), 
        pk=pk
    )
    
    # Form per cambio stato
    form_stato = CambiaStatoOrdineForm(ordine, request.POST or None)
    form_dettaglio = OrdineDettaglioForm(request.POST or None, instance=ordine)
    
    if request.method == 'POST':
        # Gestione cambio stato
        if 'cambia_stato' in request.POST and form_stato.is_valid():
            azione = form_stato.cleaned_data['azione']
            note = form_stato.cleaned_data.get('note', '')
            
            if azione == 'segna_ricevuto' and ordine.può_essere_ricevuto():
                ordine.segna_come_ricevuto(request.user)
                messages.success(request, f"Ordine {ordine.numero_ordine} segnato come RICEVUTO")
                
            elif azione == 'segna_pagato' and ordine.può_essere_pagato():
                ordine.segna_come_pagato(request.user)
                messages.success(request, f"Ordine {ordine.numero_ordine} segnato come PAGATO")
            
            # Salva note se presenti
            if note:
                ordine.note_ordine = f"{ordine.note_ordine}\n\n[{timezone.now().strftime('%d/%m/%Y %H:%M')}] {note}".strip()
                ordine.save()
            
            return redirect('acquisti:dettaglio_ordine', pk=ordine.pk)
        
        # Gestione modifica dettagli
        elif 'aggiorna_dettagli' in request.POST and form_dettaglio.is_valid():
            form_dettaglio.save()
            messages.success(request, "Dettagli ordine aggiornati con successo")
            return redirect('acquisti:dettaglio_ordine', pk=ordine.pk)
    
    # Allegati per la visualizzazione
    allegati_attivi = ordine.get_allegati_attivi().order_by('-creato_il')
    
    context = {
        'ordine': ordine,
        'form_stato': form_stato,
        'form_dettaglio': form_dettaglio,
        'allegati_attivi': allegati_attivi,
    }
    
    return render(request, 'acquisti/dettaglio_ordine.html', context)


@login_required
def segna_ricevuto_ajax(request, pk):
    """
    AJAX endpoint per segnare ordine come ricevuto
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Metodo non supportato'}, status=405)
    
    ordine = get_object_or_404(OrdineAcquisto, pk=pk)
    
    if not ordine.può_essere_ricevuto():
        return JsonResponse({
            'error': 'Ordine non può essere segnato come ricevuto'
        }, status=400)
    
    try:
        ordine.segna_come_ricevuto(request.user)
        
        return JsonResponse({
            'success': True,
            'message': f'Ordine {ordine.numero_ordine} segnato come RICEVUTO',
            'nuovo_stato': ordine.stato,
            'nuovo_stato_display': ordine.get_stato_display(),
            'css_class': ordine.get_stato_css_class(),
            'data_ricevimento': ordine.data_ricevimento.strftime('%d/%m/%Y %H:%M') if ordine.data_ricevimento else '',
            'ricevuto_da': ordine.ricevuto_da.get_full_name() if ordine.ricevuto_da else ''
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Errore durante l\'operazione: {str(e)}'
        }, status=500)


@login_required
def fornitori_autocomplete(request):
    """
    Endpoint per autocomplete fornitori nella ricerca
    """
    term = request.GET.get('term', '')
    
    if len(term) < 2:
        return JsonResponse({'results': []})
    
    fornitori = Fornitore.objects.filter(
        nome__icontains=term,
        attivo=True
    ).order_by('nome')[:10]
    
    results = [
        {
            'id': f.id,
            'text': f.nome
        }
        for f in fornitori
    ]
    
    return JsonResponse({'results': results})


def send_email_ordine_creato(ordine):
    """
    Invia email di notifica ordine creato al fornitore
    """
    try:
        # Verifica che ci sia un'email valida per il fornitore
        if not ordine.fornitore.email:
            logger.warning(f"Fornitore {ordine.fornitore.nome} non ha email configurata")
            return False
            
        if not ordine.fornitore.email.strip():
            logger.warning(f"Email fornitore {ordine.fornitore.nome} è vuota")
            return False
        
        # Preparazione oggetto e messaggio
        subject = f"Nuovo Ordine di Acquisto {ordine.numero_ordine}"
        
        message = f"""
Gentile {ordine.fornitore.nome},

abbiamo il piacere di comunicarVi che è stato emesso un nuovo ordine di acquisto a Vostro favore.

DETTAGLI ORDINE:
━━━━━━━━━━━━━━━━━━━━
• Numero Ordine: {ordine.numero_ordine}
• Data Ordine: {ordine.data_ordine.strftime('%d/%m/%Y')}
• Importo Totale: €{ordine.importo_totale:,.2f}
• Data Consegna Richiesta: {ordine.data_consegna_richiesta.strftime('%d/%m/%Y')}
• Termini di Pagamento: {ordine.termini_pagamento}
• Tempi di Consegna: {ordine.tempi_consegna}

{"DESCRIZIONE:" if ordine.note_ordine else ""}
{ordine.note_ordine if ordine.note_ordine else ""}

{"RIFERIMENTO ESTERNO:" if ordine.riferimento_esterno else ""}
{ordine.riferimento_esterno if ordine.riferimento_esterno else ""}

Vi preghiamo di confermare ricezione e di procedere come da accordi.

Cordiali saluti,
Il Team Acquisti
        """.strip()
        
        logger.info(f"Tentativo invio email ordine {ordine.numero_ordine} a {ordine.fornitore.email}")
        
        # Invio email
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[ordine.fornitore.email],
            fail_silently=False,
        )
        
        logger.info(f"Email ordine {ordine.numero_ordine} inviata con successo a {ordine.fornitore.email}")
        return True
        
    except Exception as e:
        logger.error(f"Errore invio email ordine {ordine.numero_ordine}: {str(e)}")
        return False


def aggiungi_nota_ajax(request, pk):
    """
    AJAX endpoint per aggiungere note rapide all'ordine
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Metodo non supportato'}, status=405)
    
    ordine = get_object_or_404(OrdineAcquisto, pk=pk)
    
    titolo = request.POST.get('titolo', '').strip()
    contenuto = request.POST.get('contenuto', '').strip()
    
    if not titolo or not contenuto:
        return JsonResponse({
            'error': 'Titolo e contenuto sono obbligatori'
        }, status=400)
    
    try:
        allegato = ordine.aggiungi_nota(
            titolo=titolo,
            contenuto=contenuto,
            tipo_nota='nota_interna',
            utente=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Nota aggiunta con successo',
            'allegato_id': allegato.id,
            'allegato_url': allegato.get_absolute_url()
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Errore durante l\'aggiunta della nota: {str(e)}'
        }, status=500)
