"""
PREVENTIVI VIEWS - Sistema gestione preventivi e gare
====================================================

Views per gestire l'intero workflow dei preventivi:
- Dashboard e overview
- Creazione e gestione richieste
- Inserimento e valutazione preventivi
- Approvazione e workflow finale
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Avg, Max
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from datetime import datetime, timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

from .models import (
    RichiestaPreventivo, 
    FornitorePreventivo, 
    Preventivo, 
    ParametroValutazione
)
from .forms import RichiestaPreventovoForm
from anagrafica.models import Fornitore

# Import per integrazione ordini di acquisto
import sys
import os
sys.path.append('/home/giorgio/Scrivania/bef-pro/bef2')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bef2.settings')


def send_email_to_fornitore(richiesta, fornitore_preventivo):
    """
    Invia email di richiesta preventivo al fornitore con allegati opzionali
    """
    try:
        from django.core.mail import EmailMessage
        import os

        # Debug: verifica dati di input
        print(f"🔍 DEBUG: Tentativo invio email a fornitore: {fornitore_preventivo.fornitore.nome}")
        print(f"🔍 DEBUG: Email fornitore: '{fornitore_preventivo.fornitore.email}'")

        # Verifica che ci sia un'email valida
        if not fornitore_preventivo.fornitore.email:
            print(f"❌ ERRORE: Fornitore {fornitore_preventivo.fornitore.nome} non ha email")
            return False

        if not fornitore_preventivo.fornitore.email.strip():
            print(f"❌ ERRORE: Email fornitore {fornitore_preventivo.fornitore.nome} è vuota")
            return False

        # Preparazione dati per il template email
        context = {
            'richiesta': richiesta,
            'fornitore': fornitore_preventivo.fornitore,
            'operatore': richiesta.operatore or richiesta.richiedente,
            'scadenza': richiesta.data_scadenza,
            'token': fornitore_preventivo.token_accesso,
        }

        # Render del template HTML per l'email
        subject = f"Richiesta Preventivo {richiesta.numero} - {richiesta.titolo}"

        # Template email con riferimento agli allegati se presenti
        has_attachments = richiesta.auto_attach_documents and richiesta.target

        message = f"""
Gentile Fornitore {fornitore_preventivo.fornitore.nome},

Vi richiediamo di fornire un preventivo per:

NUMERO RICHIESTA: {richiesta.numero}
TITOLO: {richiesta.titolo}
DESCRIZIONE: {richiesta.descrizione}

SCADENZA PREVENTIVI: {richiesta.data_scadenza.strftime('%d/%m/%Y')}
"""

        # Aggiungi info asset se presente
        if richiesta.target:
            if hasattr(richiesta.target, 'targa'):  # Automezzo
                message += f"""
ASSET COLLEGATO:
Automezzo: {richiesta.target.targa}
Marca/Modello: {richiesta.target.marca} {richiesta.target.modello}
Anno: {richiesta.target.anno_immatricolazione}
"""
            else:  # Stabilimento
                message += f"""
ASSET COLLEGATO:
Stabilimento: {richiesta.target.nome}
Indirizzo: {richiesta.target.indirizzo}, {richiesta.target.citta}
"""

        if has_attachments:
            message += """
In allegato trovate i documenti relativi all'asset.
"""

        message += f"""
Vi preghiamo di inoltrare il vostro preventivo entro la data di scadenza indicata.

Per eventuali chiarimenti potete contattare:
{context['operatore'].get_full_name()} - {context['operatore'].email}

Cordiali saluti,
Team Gestione Preventivi
        """

        print(f"📧 DEBUG: Tentativo invio email:")
        print(f"   Subject: {subject}")
        print(f"   To: {fornitore_preventivo.fornitore.email}")
        print(f"   From: {settings.DEFAULT_FROM_EMAIL}")

        # Crea EmailMessage invece di send_mail per supportare allegati
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[fornitore_preventivo.fornitore.email],
        )

        # Allega documenti se richiesto
        if has_attachments:
            print(f"📎 DEBUG: Allegati automatici attivi per asset {richiesta.target}")

            # Se è un automezzo
            if hasattr(richiesta.target, 'targa'):
                automezzo = richiesta.target

                # Allega libretto fronte
                if automezzo.libretto_fronte:
                    try:
                        email.attach_file(automezzo.libretto_fronte.path)
                        print(f"✅ Allegato: {os.path.basename(automezzo.libretto_fronte.name)}")
                    except Exception as e:
                        print(f"⚠️ Errore allegando libretto_fronte: {e}")

                # Allega libretto retro
                if automezzo.libretto_retro:
                    try:
                        email.attach_file(automezzo.libretto_retro.path)
                        print(f"✅ Allegato: {os.path.basename(automezzo.libretto_retro.name)}")
                    except Exception as e:
                        print(f"⚠️ Errore allegando libretto_retro: {e}")

                # Allega assicurazione
                if automezzo.assicurazione:
                    try:
                        email.attach_file(automezzo.assicurazione.path)
                        print(f"✅ Allegato: {os.path.basename(automezzo.assicurazione.name)}")
                    except Exception as e:
                        print(f"⚠️ Errore allegando assicurazione: {e}")

            # Se è uno stabilimento (potresti aggiungere documenti anche per gli stabilimenti)
            else:
                print(f"ℹ️ Asset è uno stabilimento - nessun documento specifico da allegare")

        # Invio email
        email.send(fail_silently=False)

        print(f"✅ DEBUG: Email inviata con successo a {fornitore_preventivo.fornitore.email}")
        return True

    except Exception as e:
        print(f"❌ ERRORE invio email a {fornitore_preventivo.fornitore.email}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


@login_required
def dashboard(request):
    """
    Dashboard principale preventivi con statistiche e overview
    """
    # Statistiche principali
    stats = {
        'totale_richieste': RichiestaPreventivo.objects.count(),
        'richieste_attive': RichiestaPreventivo.objects.filter(
            stato__in=['RICHIESTO', 'COMPLETATO']
        ).count(),
        'in_attesa_approvazione': RichiestaPreventivo.objects.filter(
            stato='COMPLETATO'
        ).count(),
        'approvate_questo_mese': RichiestaPreventivo.objects.filter(
            stato='APPROVATO',
            data_approvazione__gte=timezone.now().replace(day=1)
        ).count(),
    }
    
    # Richieste recenti
    richieste_recenti = RichiestaPreventivo.objects.select_related(
        'richiedente', 'operatore'
    ).order_by('-data_richiesta')[:10]
    
    # Scadenze imminenti (prossimi 7 giorni)
    scadenze_imminenti = RichiestaPreventivo.objects.filter(
        stato='RICHIESTO',
        data_scadenza__lte=timezone.now().date() + timedelta(days=7)
    ).order_by('data_scadenza')[:5]
    
    # Preventivi da valutare (se l'utente è operatore)
    preventivi_da_valutare = []
    if request.user.groups.filter(name__in=['operatori', 'supervisori']).exists():
        # Nel nuovo sistema, i preventivi senza parametri devono essere gestiti
        preventivi_da_valutare = Preventivo.objects.filter(
            richiesta__operatore=request.user,
            richiesta__stato='INVIATO_FORNITORI'
        ).select_related('richiesta', 'fornitore')[:5]
    
    # Richieste da approvare (se l'utente è approvatore)
    richieste_da_approvare = []
    if request.user.groups.filter(name__in=['supervisori', 'dirigenti']).exists():
        richieste_da_approvare = RichiestaPreventivo.objects.filter(
            stato='COMPLETATO',
            approvatore=request.user
        )[:5]
    
    context = {
        'stats': stats,
        'richieste_recenti': richieste_recenti,
        'scadenze_imminenti': scadenze_imminenti,
        'preventivi_da_valutare': preventivi_da_valutare,
        'richieste_da_approvare': richieste_da_approvare,
    }
    
    return render(request, 'preventivi/dashboard.html', context)


@login_required
def richieste_list(request):
    """
    Lista paginata delle richieste preventivo con filtri
    """
    queryset = RichiestaPreventivo.objects.select_related(
        'richiedente', 'operatore', 'approvatore'
    ).prefetch_related('fornitori')
    
    # Filtri
    stato = request.GET.get('stato')
    if stato:
        queryset = queryset.filter(stato=stato)
    
    priorita = request.GET.get('priorita')
    if priorita:
        queryset = queryset.filter(priorita=priorita)
    
    richiedente = request.GET.get('richiedente')
    if richiedente:
        queryset = queryset.filter(richiedente_id=richiedente)
    
    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(
            Q(numero__icontains=search) |
            Q(titolo__icontains=search) |
            Q(descrizione__icontains=search)
        )
    
    # Ordinamento
    order_by = request.GET.get('order_by', '-data_richiesta')
    queryset = queryset.order_by(order_by)
    
    # Paginazione
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Choices per filtri
    from dipendenti.models import Dipendente
    richiedenti = Dipendente.objects.filter(
        preventivi_richiesti__isnull=False
    ).distinct().order_by('first_name', 'last_name')
    
    context = {
        'page_obj': page_obj,
        'richiedenti': richiedenti,
        'current_filters': {
            'stato': stato,
            'priorita': priorita,
            'richiedente': richiedente,
            'search': search,
            'order_by': order_by,
        }
    }
    
    return render(request, 'preventivi/richieste_list.html', context)


@login_required
def richiesta_detail(request, pk):
    """
    Dettaglio richiesta preventivo con tutti i dati associati
    """
    richiesta = get_object_or_404(
        RichiestaPreventivo.objects.select_related(
            'richiedente', 'operatore', 'approvatore'
        ).prefetch_related(
            'fornitori',
            'preventivo_set__fornitore',
            'preventivo_set__parametri'
        ),
        pk=pk
    )
    
    # Verifica permessi
    if not (request.user == richiesta.richiedente or 
            request.user == richiesta.operatore or 
            request.user == richiesta.approvatore or
            request.user.groups.filter(name__in=['supervisori', 'dirigenti']).exists()):
        messages.error(request, "Non hai i permessi per visualizzare questa richiesta.")
        return redirect('preventivi:richieste_list')
    
    # Stato fornitori
    fornitori_status = []
    for fornitore_preventivo in richiesta.fornitorepreventivo_set.select_related('fornitore'):
        try:
            preventivo = richiesta.preventivo_set.get(fornitore=fornitore_preventivo.fornitore)
        except Preventivo.DoesNotExist:
            preventivo = None

        fornitori_status.append({
            'fornitore_preventivo': fornitore_preventivo,
            'preventivo': preventivo,
            'ha_parametri': preventivo and preventivo.parametri.exists() if preventivo else False,
            'valutato': preventivo and preventivo.parametri.exists() if preventivo else False
        })

    # Ranking preventivi se completati
    ranking_preventivi = []
    if richiesta.stato in ['COMPLETATO', 'APPROVATO']:
        ranking_preventivi = richiesta.get_ranking_preventivi()

    # Nel nuovo sistema, i parametri sono associati ai preventivi, non alla richiesta
    # Raccogli tutti i parametri univoci da tutti i preventivi
    parametri = []
    parametri_visti = set()
    for status in fornitori_status:
        if status['preventivo']:
            for param in status['preventivo'].parametri.all():
                if param.titolo not in parametri_visti:
                    parametri.append(param)
                    parametri_visti.add(param.titolo)

    context = {
        'richiesta': richiesta,
        'fornitori_status': fornitori_status,
        'ranking_preventivi': ranking_preventivi,
        'parametri': parametri,
    }
    
    return render(request, 'preventivi/richiesta_detail.html', context)


@login_required
def richiesta_create(request):
    """
    Creazione nuova richiesta preventivo con supporto asset - WIZARD UNIFICATO
    """
    if request.method == 'POST':
        form = RichiestaPreventovoForm(request.POST, user=request.user)
        if form.is_valid():
            # Salva la richiesta
            richiesta = form.save(commit=False)
            richiesta.richiedente = request.user
            richiesta.save()

            # Gestisci fornitori selezionati
            fornitori_selezionati = request.POST.getlist('fornitori')
            if len(fornitori_selezionati) >= 2:
                # Associa fornitori
                fornitori = Fornitore.objects.filter(id__in=fornitori_selezionati)
                for fornitore in fornitori:
                    FornitorePreventivo.objects.get_or_create(
                        richiesta=richiesta,
                        fornitore=fornitore
                    )
                messages.success(request, f"Richiesta preventivo {richiesta.numero} creata con {len(fornitori_selezionati)} fornitori!")
                messages.info(request, "Ora puoi procedere con l'invio email ai fornitori")
                return redirect('preventivi:step1_invia_fornitori', pk=richiesta.pk)
            else:
                messages.warning(request, f"Richiesta preventivo {richiesta.numero} creata senza fornitori. Aggiungili dalla pagina dettaglio.")
                return redirect('preventivi:richiesta_detail', pk=richiesta.pk)
        else:
            messages.error(request, "Errore nella compilazione del form. Controlla i campi evidenziati.")
    else:
        form = RichiestaPreventovoForm(user=request.user)

    context = {
        'form': form,
    }

    return render(request, 'preventivi/richiesta_create_unified.html', context)


@login_required
def richiesta_select_fornitori(request, pk):
    """
    Step 2: Selezione fornitori per la richiesta
    """
    richiesta = get_object_or_404(RichiestaPreventivo, pk=pk)
    
    # Verifica che l'utente possa modificare questa richiesta
    if request.user != richiesta.richiedente and not request.user.is_staff:
        messages.error(request, "Non puoi modificare questa richiesta.")
        return redirect('preventivi:richiesta_detail', pk=pk)
    
    if request.method == 'POST':
        fornitori_selezionati = request.POST.getlist('fornitori')
        if len(fornitori_selezionati) < 2:
            messages.error(request, "Seleziona almeno 2 fornitori per il preventivo.")
        else:
            # Associa fornitori
            fornitori = Fornitore.objects.filter(id__in=fornitori_selezionati)
            for fornitore in fornitori:
                FornitorePreventivo.objects.get_or_create(
                    richiesta=richiesta,
                    fornitore=fornitore
                )
            
            messages.success(request, f"Richiesta preventivo {richiesta.numero} creata con {len(fornitori_selezionati)} fornitori!")
            messages.info(request, "Ora puoi procedere con l'invio email ai fornitori")
            return redirect('preventivi:step1_invia_fornitori', pk=richiesta.pk)
    
    # GET: Mostra form selezione fornitori
    fornitori = Fornitore.objects.filter(attivo=True).order_by('nome')
    fornitori_attuali = richiesta.fornitori.all()
    
    context = {
        'richiesta': richiesta,
        'fornitori': fornitori,
        'fornitori_attuali': fornitori_attuali,
        'step': 2,
    }
    
    return render(request, 'preventivi/richiesta_select_fornitori.html', context)


@login_required
def search_fornitori_ajax(request):
    """
    Endpoint AJAX per ricerca fornitori
    Ritorna i fornitori che matchano il termine di ricerca
    """
    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return JsonResponse({'fornitori': []})

    # Cerca fornitori attivi che matchano il query
    fornitori = Fornitore.objects.filter(
        Q(nome__icontains=query) |
        Q(categoria__icontains=query) |
        Q(citta__icontains=query)
    ).filter(attivo=True).order_by('nome')[:20]  # Limita a 20 risultati

    # Prepara la risposta JSON
    fornitori_data = []
    for fornitore in fornitori:
        fornitori_data.append({
            'id': fornitore.id,
            'nome': fornitore.nome,
            'email': fornitore.email or 'N/D',
            'telefono': fornitore.telefono or 'N/D',
            'categoria': fornitore.categoria or 'N/D',
            'citta': fornitore.citta or 'N/D',
        })

    return JsonResponse({'fornitori': fornitori_data})


def handle_step1_create(request):
    """Gestisce step 1 della creazione richiesta"""
    # Validazione dati base
    titolo = request.POST.get('titolo', '').strip()
    descrizione = request.POST.get('descrizione', '').strip()
    data_scadenza = request.POST.get('data_scadenza')
    priorita = request.POST.get('priorita', 'NORMALE')
    budget_massimo = request.POST.get('budget_massimo')
    
    if not titolo or not descrizione or not data_scadenza:
        messages.error(request, "Tutti i campi obbligatori devono essere compilati.")
        return redirect('preventivi:richiesta_create')
    
    # Salva in sessione per step successivi
    request.session['richiesta_step1'] = {
        'titolo': titolo,
        'descrizione': descrizione,
        'data_scadenza': data_scadenza,
        'priorita': priorita,
        'budget_massimo': budget_massimo,
        'note_interne': request.POST.get('note_interne', ''),
    }
    
    # Mostra step 2
    fornitori = Fornitore.objects.filter(attivo=True).order_by('nome')
    context = {
        'fornitori': fornitori,
        'step': 2,
        'step1_data': request.session['richiesta_step1']
    }
    
    return render(request, 'preventivi/richiesta_create.html', context)


def handle_step2_create(request):
    """Gestisce step 2 finale della creazione richiesta"""
    if 'richiesta_step1' not in request.session:
        messages.error(request, "Sessione scaduta. Riprova dall'inizio.")
        return redirect('preventivi:richiesta_create')
    
    # Validazione fornitori
    fornitori_selezionati = request.POST.getlist('fornitori')
    if len(fornitori_selezionati) < 2:
        messages.error(request, "Seleziona almeno 2 fornitori per il preventivo.")
        fornitori = Fornitore.objects.filter(attivo=True).order_by('nome')
        context = {
            'fornitori': fornitori,
            'step': 2,
            'step1_data': request.session['richiesta_step1']
        }
        return render(request, 'preventivi/richiesta_create.html', context)
    
    # Crea direttamente la richiesta (senza step 3)
    step1_data = request.session['richiesta_step1']
    
    try:
        # Crea richiesta preventivo
        richiesta = RichiestaPreventivo.objects.create(
            titolo=step1_data['titolo'],
            descrizione=step1_data['descrizione'],
            data_scadenza=datetime.strptime(step1_data['data_scadenza'], '%Y-%m-%d').date(),
            priorita=step1_data['priorita'],
            budget_massimo=Decimal(step1_data['budget_massimo']) if step1_data['budget_massimo'] else None,
            note_interne=step1_data['note_interne'],
            richiedente=request.user,
        )
        
        # Associa fornitori
        fornitori = Fornitore.objects.filter(id__in=fornitori_selezionati)
        for fornitore in fornitori:
            FornitorePreventivo.objects.create(
                richiesta=richiesta,
                fornitore=fornitore
            )
        
        # Pulizia sessione
        del request.session['richiesta_step1']
        
        messages.success(request, f"Richiesta preventivo {richiesta.numero} creata con successo!")
        messages.info(request, "Ora puoi procedere con il Step 1: invio email ai fornitori")
        return redirect('preventivi:step1_invia_fornitori', pk=richiesta.pk)
        
    except Exception as e:
        messages.error(request, f"Errore durante la creazione: {str(e)}")
        return redirect('preventivi:richiesta_create')




@login_required
def preventivo_create(request, richiesta_pk):
    """
    Inserimento nuovo preventivo ricevuto da fornitore
    """
    richiesta = get_object_or_404(RichiestaPreventivo, pk=richiesta_pk)
    
    # Verifica permessi
    if not (request.user == richiesta.operatore or 
            request.user.groups.filter(name__in=['supervisori', 'dirigenti']).exists()):
        messages.error(request, "Non hai i permessi per inserire preventivi per questa richiesta.")
        return redirect('preventivi:richiesta_detail', pk=richiesta_pk)
    
    if request.method == 'POST':
        try:
            # Dati preventivo
            fornitore_id = request.POST.get('fornitore')
            fornitore = get_object_or_404(Fornitore, pk=fornitore_id)
            
            # Verifica che il fornitore sia tra quelli selezionati
            if not richiesta.fornitori.filter(pk=fornitore_id).exists():
                messages.error(request, "Il fornitore selezionato non è tra quelli invitati.")
                return redirect('preventivi:preventivo_create', richiesta_pk=richiesta_pk)
            
            # Verifica che non esista già un preventivo per questo fornitore
            if richiesta.preventivo_set.filter(fornitore=fornitore).exists():
                messages.error(request, "Esiste già un preventivo per questo fornitore.")
                return redirect('preventivi:richiesta_detail', pk=richiesta_pk)
            
            preventivo = Preventivo.objects.create(
                richiesta=richiesta,
                fornitore=fornitore,
                numero_preventivo_fornitore=request.POST.get('numero_preventivo_fornitore'),
                importo_totale=Decimal(request.POST.get('importo_totale')),
                validita_giorni=int(request.POST.get('validita_giorni')),
                termini_pagamento=request.POST.get('termini_pagamento'),
                tempi_consegna=request.POST.get('tempi_consegna'),
                condizioni_trasporto=request.POST.get('condizioni_trasporto', ''),
                garanzia=request.POST.get('garanzia', ''),
                note_tecniche=request.POST.get('note_tecniche', ''),
                note_commerciali=request.POST.get('note_commerciali', ''),
                file_preventivo=request.FILES.get('file_preventivo'),
                operatore_inserimento=request.user,
            )
            
            messages.success(request, f"Preventivo di {fornitore.nome} inserito con successo!")
            messages.info(request, "Ora puoi definire i parametri di confronto per questo preventivo.")
            return redirect('preventivi:step2_raccolta', pk=richiesta_pk)
            
        except Exception as e:
            messages.error(request, f"Errore durante l'inserimento: {str(e)}")
    
    # GET: Mostra form
    fornitori_disponibili = richiesta.fornitori.filter(
        attivo=True
    ).exclude(
        preventivo__richiesta=richiesta
    )
    
    context = {
        'richiesta': richiesta,
        'fornitori_disponibili': fornitori_disponibili,
    }
    
    return render(request, 'preventivi/preventivo_create.html', context)


@login_required
def preventivo_valuta(request, pk):
    """
    OBSOLETA: Ora i parametri sono gestiti nel Step 2
    Redirect alla gestione parametri nel Step 2
    """
    preventivo = get_object_or_404(
        Preventivo.objects.select_related('richiesta', 'fornitore'),
        pk=pk
    )
    richiesta = preventivo.richiesta
    
    # Verifica permessi
    if not (request.user == richiesta.operatore or 
            request.user.groups.filter(name__in=['supervisori', 'dirigenti']).exists()):
        messages.error(request, "Non hai i permessi per gestire questo preventivo.")
        return redirect('preventivi:richiesta_detail', pk=richiesta.pk)
    
    # Nel nuovo workflow, i parametri sono gestiti nel Step 2
    messages.info(request, "I parametri di valutazione sono ora gestiti nel Step 2. Ti reindirizziamo lì.")
    return redirect('preventivi:step2_raccolta', pk=richiesta.pk)


@login_required
def step1_invia_fornitori(request, pk):
    """
    STEP 1: Operatore invia email ai fornitori
    """
    richiesta = get_object_or_404(RichiestaPreventivo, pk=pk)
    
    # Verifica permessi (operatore livello contabile)
    if not (request.user.groups.filter(name__in=['operatori', 'contabili']).exists() or
            request.user.is_staff):
        messages.error(request, "Non hai i permessi per questa operazione.")
        return redirect('preventivi:richiesta_detail', pk=pk)
    
    # Verifica che sia in stato CREATO
    if richiesta.stato != 'CREATO':
        messages.error(request, "La richiesta deve essere in stato CREATO per poter essere inviata.")
        return redirect('preventivi:richiesta_detail', pk=pk)
    
    # Verifica che ci siano fornitori
    if not richiesta.può_essere_inviato:
        messages.error(request, "La richiesta deve avere almeno un fornitore selezionato.")
        return redirect('preventivi:richiesta_detail', pk=pk)
    
    if request.method == 'POST':
        try:
            # Invio email ai fornitori
            email_inviate = 0
            errori_invio = []
            
            for fornitore_preventivo in richiesta.fornitorepreventivo_set.all():
                # Prova a inviare l'email
                email_inviata = send_email_to_fornitore(richiesta, fornitore_preventivo)
                
                if email_inviata:
                    fornitore_preventivo.email_inviata = True
                    fornitore_preventivo.data_invio = timezone.now()
                    fornitore_preventivo.save()
                    email_inviate += 1
                else:
                    errori_invio.append(fornitore_preventivo.fornitore.nome)
            
            # Aggiorna stato richiesta solo se almeno una email è stata inviata
            if email_inviate > 0:
                richiesta.stato = 'INVIATO_FORNITORI'
                richiesta.data_invio_fornitori = timezone.now()
                richiesta.operatore = request.user  # Assegna operatore
                richiesta.save()
                
                if errori_invio:
                    messages.warning(request, f"Email inviate a {email_inviate} fornitori. Errori: {', '.join(errori_invio)}")
                else:
                    messages.success(request, f"Email inviate con successo a {email_inviate} fornitori!")
                    
                return redirect('preventivi:step2_raccolta', pk=pk)
            else:
                messages.error(request, "Nessuna email è stata inviata. Controlla le configurazioni email.")
            
        except Exception as e:
            messages.error(request, f"Errore durante l'invio: {str(e)}")
    
    context = {
        'richiesta': richiesta,
        'fornitori_da_contattare': richiesta.fornitorepreventivo_set.select_related('fornitore'),
    }
    
    return render(request, 'preventivi/step1_invia_fornitori.html', context)


@login_required
def step2_raccolta(request, pk):
    """
    STEP 2: Operatore carica i preventivi ricevuti
    """
    richiesta = get_object_or_404(RichiestaPreventivo, pk=pk)
    
    # Verifica permessi (stesso operatore o staff)
    if not (request.user == richiesta.operatore or request.user.is_staff):
        messages.error(request, "Solo l'operatore assegnato può raccogliere i preventivi.")
        return redirect('preventivi:richiesta_detail', pk=pk)
    
    # Verifica stato
    if not richiesta.può_raccogliere_preventivi:
        messages.error(request, "La richiesta deve essere in stato 'Inviato ai fornitori'.")
        return redirect('preventivi:richiesta_detail', pk=pk)
    
    if request.method == 'POST':
        if 'finalizza_raccolta' in request.POST:
            # Finalizza la raccolta
            if richiesta.preventivo_set.count() > 0:
                richiesta.stato = 'PREVENTIVI_RACCOLTI'
                richiesta.data_raccolta_completata = timezone.now()
                richiesta.save()
                
                messages.success(request, "Raccolta preventivi completata! Ora può essere valutata dall'amministratore.")
                return redirect('preventivi:step3_valutazione', pk=pk)
            else:
                messages.error(request, "Devi caricare almeno un preventivo prima di finalizzare.")
    
    # Stato fornitori con preventivi
    fornitori_status = []
    for fornitore_preventivo in richiesta.fornitorepreventivo_set.select_related('fornitore'):
        try:
            preventivo = richiesta.preventivo_set.get(fornitore=fornitore_preventivo.fornitore)
        except Preventivo.DoesNotExist:
            preventivo = None
            
        fornitori_status.append({
            'fornitore_preventivo': fornitore_preventivo,
            'preventivo': preventivo,
            'può_caricare': not preventivo  # Non caricare se esiste già
        })
    
    # Calcola i parametri totali per tutti i preventivi
    parametri_totali = 0
    for status in fornitori_status:
        if status['preventivo']:
            parametri_totali += status['preventivo'].parametri.count()
    
    context = {
        'richiesta': richiesta,
        'fornitori_status': fornitori_status,
        'preventivi_caricati': richiesta.preventivo_set.count(),
        'fornitori_totali': richiesta.fornitori.count(),
        'parametri_totali': parametri_totali,
    }
    
    return render(request, 'preventivi/step2_raccolta.html', context)


@login_required
def step3_valutazione(request, pk):
    """
    STEP 3: Amministratore valuta e sceglie preventivo
    """
    from .forms import SceltaFornitoreForm
    
    richiesta = get_object_or_404(RichiestaPreventivo, pk=pk)
    
    # Verifica permessi (amministratore/dirigente)
    if not (request.user.groups.filter(name__in=['amministratori', 'dirigenti']).exists() or
            request.user.is_staff):
        messages.error(request, "Solo gli amministratori possono valutare i preventivi.")
        return redirect('preventivi:richiesta_detail', pk=pk)
    
    # Verifica stato
    if richiesta.stato not in ['PREVENTIVI_RACCOLTI', 'IN_VALUTAZIONE']:
        messages.error(request, "I preventivi devono essere stati raccolti per poter essere valutati.")
        return redirect('preventivi:richiesta_detail', pk=pk)
    
    # Se primo accesso, metti in valutazione
    if richiesta.stato == 'PREVENTIVI_RACCOLTI':
        richiesta.stato = 'IN_VALUTAZIONE'
        richiesta.data_valutazione = timezone.now()
        richiesta.approvatore = request.user
        richiesta.save()
    
    # Crea form
    form = SceltaFornitoreForm(richiesta)
    
    if request.method == 'POST':
        form = SceltaFornitoreForm(richiesta, request.POST)
        azione = request.POST.get('azione')  # conferma_con_email o conferma_senza_email
        
        if form.is_valid() and azione in ['conferma_con_email', 'conferma_senza_email']:
            preventivo_scelto = form.cleaned_data['preventivo_scelto']
            note_approvazione = form.cleaned_data['note_approvazione']
            
            # Approva richiesta
            richiesta.preventivo_approvato = preventivo_scelto
            richiesta.stato = 'APPROVATO'
            richiesta.data_approvazione = timezone.now()
            richiesta.save()
            
            # Genera automaticamente ordine di acquisto
            try:
                invia_email = (azione == 'conferma_con_email')
                numero_ordine = genera_ordine_acquisto_da_preventivo(preventivo_scelto, request.user, invia_email=invia_email)
                
                messages.success(request, f"Preventivo di {preventivo_scelto.fornitore.nome} approvato!")
                messages.success(request, f"Ordine di acquisto {numero_ordine} generato automaticamente!")
                
                if invia_email:
                    messages.success(request, "Email di conferma inviata al fornitore vincitore!")
                else:
                    messages.info(request, "Ordine creato senza invio email. Puoi inviarla dal dettaglio ordine.")
                
                # Reindirizza al dettaglio dell'ordine di acquisto
                # TODO: Aggiungere link al dettaglio ordine quando sarà implementato
                return redirect('preventivi:richiesta_detail', pk=pk)
                
            except Exception as e:
                messages.warning(request, f"Preventivo approvato, ma errore nella creazione dell'ordine: {str(e)}")
                return redirect('preventivi:richiesta_detail', pk=pk)
        else:
            messages.error(request, "Seleziona un preventivo da approvare e un'azione da eseguire.")
    
    # Calcola ranking se non fatto
    ranking_preventivi = richiesta.get_ranking_preventivi()
    
    # Nel nuovo sistema, i parametri sono associati ai singoli preventivi
    # Raccogliamo tutti i parametri di tutti i preventivi per la visualizzazione
    tutti_parametri = []
    for preventivo in richiesta.preventivo_set.all():
        for parametro in preventivo.parametri.all().order_by('ordine'):
            tutti_parametri.append(parametro)
    
    context = {
        'richiesta': richiesta,
        'ranking_preventivi': ranking_preventivi,
        'tutti_parametri': tutti_parametri,
        'form': form,
    }
    
    return render(request, 'preventivi/step3_valutazione.html', context)


@login_required  
def richiesta_approva(request, pk):
    """
    Approvazione finale richiesta preventivo
    """
    richiesta = get_object_or_404(RichiestaPreventivo, pk=pk)
    
    # Verifica permessi
    if not (request.user == richiesta.approvatore or 
            request.user.groups.filter(name__in=['supervisori', 'dirigenti']).exists()):
        messages.error(request, "Non hai i permessi per approvare questa richiesta.")
        return redirect('preventivi:richiesta_detail', pk=pk)
    
    if richiesta.stato != 'COMPLETATO':
        messages.error(request, "La richiesta deve essere completata prima dell'approvazione.")
        return redirect('preventivi:richiesta_detail', pk=pk)
    
    if request.method == 'POST':
        preventivo_id = request.POST.get('preventivo_scelto')
        note_approvazione = request.POST.get('note_approvazione', '')
        
        if preventivo_id:
            preventivo_scelto = get_object_or_404(Preventivo, pk=preventivo_id, richiesta=richiesta)
            
            # Approva richiesta
            richiesta.preventivo_approvato = preventivo_scelto
            richiesta.stato = 'APPROVATO'
            richiesta.data_approvazione = timezone.now()
            richiesta.approvatore = request.user
            richiesta.save()
            
            messages.success(request, f"Richiesta approvata! Preventivo di {preventivo_scelto.fornitore.nome} selezionato.")
            
            # TODO: Qui andrà l'integrazione con il sistema acquisti
            # per la generazione automatica dell'ordine di acquisto
            
            return redirect('preventivi:richiesta_detail', pk=pk)
        else:
            messages.error(request, "Seleziona un preventivo da approvare.")
    
    # GET: Mostra form approvazione
    ranking_preventivi = richiesta.get_ranking_preventivi()
    
    context = {
        'richiesta': richiesta,
        'ranking_preventivi': ranking_preventivi,
    }
    
    return render(request, 'preventivi/richiesta_approva.html', context)


@login_required
def preventivo_parametri_get(request, pk):
    """
    AJAX endpoint per ottenere i parametri di un preventivo
    """
    preventivo = get_object_or_404(Preventivo, pk=pk)
    
    # Verifica permessi
    if not (request.user == preventivo.richiesta.operatore or request.user.is_staff):
        return JsonResponse({'error': 'Non autorizzato'}, status=403)
    
    parametri = []
    for param in preventivo.parametri.all().order_by('ordine', 'descrizione'):
        parametri.append({
            'id': param.id,
            'descrizione': param.descrizione,
            'valore': param.valore,
        })
    
    return JsonResponse({
        'parametri': parametri
    })


@login_required
def preventivo_parametri_save(request, pk):
    """
    AJAX endpoint per salvare i parametri di un preventivo
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Metodo non supportato'}, status=405)
    
    preventivo = get_object_or_404(Preventivo, pk=pk)
    
    # Verifica permessi
    if not (request.user == preventivo.richiesta.operatore or request.user.is_staff):
        return JsonResponse({'error': 'Non autorizzato'}, status=403)
    
    try:
        # Rimuovi tutti i parametri esistenti
        preventivo.parametri.all().delete()
        
        # Trova tutti i parametri nel form
        parametri_data = []
        for key in request.POST.keys():
            if key.startswith('parametro_descrizione_'):
                index = key.split('_')[-1]
                descrizione = request.POST.get(f'parametro_descrizione_{index}', '').strip()
                valore = request.POST.get(f'parametro_valore_{index}', '').strip()
                
                if descrizione and valore:
                    parametri_data.append({
                        'descrizione': descrizione,
                        'valore': valore,
                        'ordine': int(index)
                    })
        
        # Crea nuovi parametri
        for i, param_data in enumerate(parametri_data):
            ParametroValutazione.objects.create(
                preventivo=preventivo,
                descrizione=param_data['descrizione'],
                valore=param_data['valore'],
                ordine=param_data['ordine'],
                creato_da=request.user
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Salvati {len(parametri_data)} parametri'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def genera_ordine_acquisto_da_preventivo(preventivo, utente, invia_email=False):
    """
    Genera automaticamente un ordine di acquisto dal preventivo approvato
    Crea ODA nell'app acquisti del progetto Management
    """
    try:
        # Import dell'app acquisti del progetto Management
        from acquisti.models import OrdineAcquisto
        
        # Dati dell'ordine basati sul preventivo
        fornitore = preventivo.fornitore
        richiesta = preventivo.richiesta
        
        # Calcola data consegna (15 giorni da ora)
        from datetime import timedelta
        data_consegna = (timezone.now() + timedelta(days=15)).date()
        
        # Crea l'ordine di acquisto
        ordine = OrdineAcquisto.objects.create(
            fornitore=fornitore,
            preventivo_originale=preventivo,
            importo_totale=preventivo.importo_totale,
            valuta=preventivo.valuta,
            termini_pagamento=preventivo.termini_pagamento,
            tempi_consegna=preventivo.tempi_consegna,
            data_consegna_richiesta=data_consegna,
            creato_da=utente,
            note_ordine=f"Ordine generato automaticamente dal preventivo {richiesta.numero} - {richiesta.titolo}"
        )
        
        # Aggiorna il preventivo con il riferimento all'ordine
        preventivo.ordine_acquisto_numero = ordine.numero_ordine
        preventivo.save()
        
        # Invia email di conferma se richiesto
        if invia_email and fornitore.email:
            try:
                # Genera il PDF dell'ordine di acquisto
                pdf_buffer = genera_pdf_ordine_acquisto(ordine, preventivo)
                # Invia email con PDF allegato
                invia_email_conferma_ordine(preventivo, ordine.numero_ordine, fornitore, pdf_buffer)
            except Exception as e:
                logger.warning(f"Ordine creato ma errore invio email: {str(e)}")
        
        return ordine.numero_ordine
        
    except Exception as e:
        logger.error(f"Errore creazione ordine di acquisto: {str(e)}")
        raise Exception(f"Errore creazione ordine di acquisto: {str(e)}")


def invia_email_conferma_ordine(preventivo, numero_ordine, fornitore, pdf_buffer=None):
    """
    Invia email di conferma ordine al fornitore vincitore

    Args:
        preventivo: Preventivo instance
        numero_ordine: Numero dell'ordine di acquisto
        fornitore: Fornitore instance
        pdf_buffer: BytesIO contenente il PDF dell'ordine (opzionale)
    """
    try:
        from django.core.mail import EmailMessage
        from django.conf import settings

        richiesta = preventivo.richiesta

        subject = f"Conferma Ordine {numero_ordine} - Gara {richiesta.numero}"

        message = f"""
Gentile {fornitore.nome},

siamo lieti di comunicarLe che la Sua offerta per la gara "{richiesta.titolo}" è stata ACCETTATA.

DETTAGLI ORDINE:
Numero Ordine: {numero_ordine}
Gara di riferimento: {richiesta.numero}
Importo aggiudicato: €{preventivo.importo_totale:,.2f}
Vostro preventivo n.: {preventivo.numero_preventivo_fornitore}

CONDIZIONI COMMERCIALI:
Pagamento: {preventivo.termini_pagamento}
Consegna: {preventivo.tempi_consegna}
{f"Garanzia: {preventivo.garanzia}" if preventivo.garanzia else ""}

In allegato trova l'ordine di acquisto ufficiale per procedere con la fornitura.

La preghiamo di confermare la ricezione del presente ordine e di procedere secondo le modalità concordate.

Cordiali saluti,
Il Team Acquisti
"""

        # Crea l'email con EmailMessage invece di send_mail per supportare allegati
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[fornitore.email],
        )

        # Allega il PDF se disponibile
        if pdf_buffer:
            pdf_buffer.seek(0)  # Riposiziona il puntatore all'inizio del buffer
            email.attach(
                f"Ordine_Acquisto_{numero_ordine}.pdf",
                pdf_buffer.read(),
                'application/pdf'
            )
            logger.info(f"PDF allegato all'email per ordine {numero_ordine}")

        # Invia l'email
        email.send(fail_silently=False)

        logger.info(f"Email conferma ordine inviata a {fornitore.nome} ({fornitore.email})")
        return True

    except Exception as e:
        logger.error(f"Errore invio email conferma ordine: {str(e)}")
        raise Exception(f"Errore invio email: {str(e)}")


def genera_pdf_ordine_acquisto(ordine, preventivo=None):
    """
    Genera il PDF dell'ordine di acquisto

    Args:
        ordine: OrdineAcquisto instance
        preventivo: Preventivo instance (opzionale)

    Returns:
        BytesIO contenente il PDF generato
    """
    try:
        from django.template.loader import render_to_string
        from core.pdf_generator import generate_pdf_from_html, PDFConfig
        from io import BytesIO

        # Prepara i dati del preventivo se disponibile
        preventivo_info = None
        preventivo_numero = None

        if preventivo:
            preventivo_numero = preventivo.numero_preventivo_fornitore
            preventivo_info = {
                'numero_gara': preventivo.richiesta.numero,
                'titolo_gara': preventivo.richiesta.titolo,
                'numero_preventivo_fornitore': preventivo.numero_preventivo_fornitore,
                'garanzia': preventivo.garanzia,
                'condizioni_trasporto': preventivo.condizioni_trasporto,
            }

        # Prepara il context per il template
        context = {
            'numero_ordine': ordine.numero_ordine,
            'data_ordine': ordine.data_ordine.strftime('%d/%m/%Y'),
            'data_consegna': ordine.data_consegna_richiesta.strftime('%d/%m/%Y'),
            'fornitore': ordine.fornitore,
            'importo_totale': ordine.importo_totale,
            'valuta': ordine.valuta,
            'termini_pagamento': ordine.termini_pagamento,
            'tempi_consegna': ordine.tempi_consegna,
            'note_ordine': ordine.note_ordine,
            'riferimento_esterno': ordine.riferimento_esterno,
            'preventivo_numero': preventivo_numero,
            'preventivo_info': preventivo_info,
            'creato_da': ordine.creato_da.get_full_name() if ordine.creato_da.get_full_name() else ordine.creato_da.username,
            'data_generazione': timezone.now().strftime('%d/%m/%Y %H:%M'),
        }

        # Renderizza il template HTML
        html_content = render_to_string('acquisti/ordine_acquisto_pdf.html', context)

        # Configura il PDF
        config = PDFConfig(
            page_size='A4',
            orientation='portrait',
            margins={'top': 1.5, 'bottom': 1.5, 'left': 2.0, 'right': 2.0},
            filename=f"ordine_acquisto_{ordine.numero_ordine}.pdf"
        )

        # Genera il PDF e ritorna come BytesIO
        pdf_buffer = generate_pdf_from_html(
            html_content=html_content,
            config=config,
            output_type='buffer'
        )

        logger.info(f"PDF generato con successo per ordine {ordine.numero_ordine}")
        return pdf_buffer

    except Exception as e:
        logger.error(f"Errore generazione PDF ordine acquisto: {str(e)}")
        raise Exception(f"Errore generazione PDF: {str(e)}")