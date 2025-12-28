from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db import transaction, models
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta

from .models import Stabilimento, CostiStabilimento, DocStabilimento
from .forms import (
    StabilimentoForm, CostiStabilimentoForm, DocStabilimentoForm,
    StabilimentiSearchForm, CostiSearchForm, UtenzaForm
)


# =====================================
# ACCESS CONTROL MIXINS
# =====================================

def stabilimenti_access_required(user):
    """Verifica accesso agli stabilimenti (amministratore, contabile, operativo)"""
    # Staff e superuser possono sempre accedere
    if user.is_staff or user.is_superuser:
        return True
    
    # Solo amministratore, contabile, operativo possono accedere
    if hasattr(user, 'livello') and user.livello in ['amministratore', 'contabile', 'operativo']:
        return True
    
    return False


# =====================================
# VIEWS STABILIMENTI
# =====================================

@login_required
@user_passes_test(stabilimenti_access_required)
def stabilimenti_list(request):
    """Lista degli stabilimenti con filtri di ricerca"""
    form = StabilimentiSearchForm(request.GET or None)
    
    # Query base
    stabilimenti = Stabilimento.objects.select_related(
        'responsabile_operativo', 'responsabile_amministrativo'
    )
    
    # Applica filtri se il form è valido
    if form.is_valid():
        q = form.cleaned_data.get('q')
        if q:
            stabilimenti = stabilimenti.filter(
                models.Q(nome__icontains=q) |
                models.Q(codice_stabilimento__icontains=q) |
                models.Q(citta__icontains=q) |
                models.Q(indirizzo__icontains=q)
            )
        
        responsabile = form.cleaned_data.get('responsabile')
        if responsabile:
            stabilimenti = stabilimenti.filter(
                models.Q(responsabile_operativo=responsabile) |
                models.Q(responsabile_amministrativo=responsabile)
            )
        
        provincia = form.cleaned_data.get('provincia')
        if provincia:
            stabilimenti = stabilimenti.filter(provincia__iexact=provincia)
        
        attivo = form.cleaned_data.get('attivo')
        if attivo == 'true':
            stabilimenti = stabilimenti.filter(attivo=True)
        elif attivo == 'false':
            stabilimenti = stabilimenti.filter(attivo=False)
    
    # Ordinamento
    stabilimenti = stabilimenti.order_by('nome')
    
    # Paginazione
    paginator = Paginator(stabilimenti, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistiche base
    stats = {
        'totali': Stabilimento.objects.count(),
        'attivi': Stabilimento.objects.filter(attivo=True).count(),
        'con_scadenze': Stabilimento.objects.con_scadenze_prossime().count(),
    }
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'stats': stats,
        'page_title': 'Stabilimenti',
        'breadcrumbs': [
            {'name': 'Stabilimenti', 'url': None}
        ]
    }
    
    return render(request, 'stabilimenti/stabilimenti_list.html', context)


@login_required
@user_passes_test(stabilimenti_access_required)
def nuovo_stabilimento(request):
    """Creazione nuovo stabilimento"""
    if request.method == 'POST':
        form = StabilimentoForm(request.POST, user=request.user)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    stabilimento = form.save(commit=False)
                    stabilimento.creato_da = request.user
                    stabilimento.modificato_da = request.user
                    stabilimento.save()
                    
                    messages.success(
                        request, 
                        f'Stabilimento "{stabilimento.nome}" creato con successo'
                    )
                    return redirect('stabilimenti:dettaglio', pk=stabilimento.pk)
                    
            except Exception as e:
                messages.error(request, f'Errore durante la creazione: {str(e)}')
        else:
            messages.error(request, 'Correggi gli errori nel form')
    
    else:
        form = StabilimentoForm(user=request.user)
    
    context = {
        'form': form,
        'page_title': 'Nuovo Stabilimento',
        'breadcrumbs': [
            {'name': 'Stabilimenti', 'url': reverse('stabilimenti:list')},
            {'name': 'Nuovo Stabilimento', 'url': None}
        ]
    }
    
    return render(request, 'stabilimenti/nuovo_stabilimento.html', context)


@login_required
@user_passes_test(stabilimenti_access_required)
def dettaglio_stabilimento(request, pk):
    """Dettaglio di un singolo stabilimento"""
    stabilimento = get_object_or_404(
        Stabilimento.objects.select_related(
            'responsabile_operativo', 'responsabile_amministrativo', 'creato_da'
        ),
        pk=pk
    )
    
    # Costi recenti
    costi_recenti = stabilimento.costi.select_related('fornitore').order_by('-data_creazione')[:5]
    
    # Documenti recenti  
    documenti_recenti = stabilimento.documenti.order_by('-data_inserimento')[:5]
    
    # Scadenze prossime (30 giorni)
    scadenze_prossime = stabilimento.get_prossime_scadenze(30)
    
    # Statistiche costi anno corrente
    costi_anno = stabilimento.get_costi_anno_corrente()
    
    context = {
        'stabilimento': stabilimento,
        'costi_recenti': costi_recenti,
        'documenti_recenti': documenti_recenti,
        'scadenze_prossime': scadenze_prossime,
        'costi_anno': costi_anno,
        'page_title': f'Stabilimento {stabilimento.nome}',
        'breadcrumbs': [
            {'name': 'Stabilimenti', 'url': reverse('stabilimenti:list')},
            {'name': stabilimento.nome, 'url': None}
        ]
    }
    
    return render(request, 'stabilimenti/dettaglio_stabilimento.html', context)


@login_required
@user_passes_test(stabilimenti_access_required)
def modifica_stabilimento(request, pk):
    """Modifica stabilimento esistente"""
    stabilimento = get_object_or_404(Stabilimento, pk=pk)
    
    if request.method == 'POST':
        form = StabilimentoForm(request.POST, instance=stabilimento, user=request.user)
        
        if form.is_valid():
            try:
                stabilimento_modificato = form.save(commit=False)
                stabilimento_modificato.modificato_da = request.user
                stabilimento_modificato.save()
                
                messages.success(request, f'Stabilimento "{stabilimento.nome}" modificato con successo')
                return redirect('stabilimenti:dettaglio', pk=pk)
                
            except Exception as e:
                messages.error(request, f'Errore durante la modifica: {str(e)}')
        else:
            messages.error(request, 'Correggi gli errori nel form')
    
    else:
        form = StabilimentoForm(instance=stabilimento, user=request.user)
    
    context = {
        'form': form,
        'stabilimento': stabilimento,
        'page_title': f'Modifica {stabilimento.nome}',
        'breadcrumbs': [
            {'name': 'Stabilimenti', 'url': reverse('stabilimenti:list')},
            {'name': stabilimento.nome, 'url': reverse('stabilimenti:dettaglio', kwargs={'pk': pk})},
            {'name': 'Modifica', 'url': None}
        ]
    }
    
    return render(request, 'stabilimenti/modifica_stabilimento.html', context)


# =====================================
# VIEWS COSTI
# =====================================

@login_required
@user_passes_test(stabilimenti_access_required)
def costi_list(request):
    """Lista costi di tutti gli stabilimenti"""
    form = CostiSearchForm(request.GET or None)
    
    # Query base
    costi = CostiStabilimento.objects.select_related('stabilimento', 'fornitore', 'incaricato')
    
    # Applica filtri
    if form.is_valid():
        stabilimento = form.cleaned_data.get('stabilimento')
        if stabilimento:
            costi = costi.filter(stabilimento=stabilimento)
        
        causale = form.cleaned_data.get('causale')
        if causale:
            costi = costi.filter(causale=causale)
        
        stato = form.cleaned_data.get('stato')
        if stato:
            costi = costi.filter(stato=stato)
        
        fornitore = form.cleaned_data.get('fornitore')
        if fornitore:
            costi = costi.filter(fornitore=fornitore)
        
        scadenze_prossime = form.cleaned_data.get('scadenze_prossime')
        if scadenze_prossime:
            costi = costi.scadenze_prossime()
        
        anno = form.cleaned_data.get('anno')
        if anno:
            costi = costi.filter(data_fattura__year=anno)

        
    # Ordinamento
    costi = costi.order_by('-data_creazione')
    
    # Paginazione
    paginator = Paginator(costi, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'page_title': 'Costi Stabilimenti',
        'breadcrumbs': [
            {'name': 'Stabilimenti', 'url': reverse('stabilimenti:list')},
            {'name': 'Costi', 'url': None}
        ]
    }
    
    return render(request, 'stabilimenti/costi_list.html', context)


@login_required
@user_passes_test(stabilimenti_access_required)
def nuovo_costo(request, stabilimento_pk):
    """Nuovo costo per stabilimento (stabilimento obbligatorio)"""
    stabilimento = get_object_or_404(Stabilimento, pk=stabilimento_pk)
    
    if request.method == 'POST':
        form = CostiStabilimentoForm(request.POST, request.FILES, user=request.user, stabilimento=stabilimento)
        
        if form.is_valid():
            try:
                costo = form.save(commit=False)
                costo.incaricato = request.user
                costo.save()
                
                messages.success(request, f'Costo "{costo.titolo}" creato con successo')
                return redirect('stabilimenti:dettaglio', pk=stabilimento.pk)
                    
            except Exception as e:
                messages.error(request, f'Errore durante la creazione: {str(e)}')
        else:
            messages.error(request, 'Correggi gli errori nel form')
    
    else:
        form = CostiStabilimentoForm(user=request.user, stabilimento=stabilimento)
    
    context = {
        'form': form,
        'stabilimento': stabilimento,
        'page_title': 'Nuovo Costo',
        'breadcrumbs': [
            {'name': 'Stabilimenti', 'url': reverse('stabilimenti:list')},
            {'name': stabilimento.nome, 'url': reverse('stabilimenti:dettaglio', kwargs={'pk': stabilimento.pk})},
            {'name': 'Nuovo Costo', 'url': None}
        ]
    }
    
    return render(request, 'stabilimenti/nuovo_costo.html', context)


@login_required
@user_passes_test(stabilimenti_access_required)
def dettaglio_costo(request, pk):
    """Dettaglio di un singolo costo"""
    costo = get_object_or_404(
        CostiStabilimento.objects.select_related('stabilimento', 'fornitore', 'incaricato'),
        pk=pk
    )
    
    context = {
        'costo': costo,
        'page_title': f'Costo {costo.numero_pratica}',
        'breadcrumbs': [
            {'name': 'Stabilimenti', 'url': reverse('stabilimenti:list')},
            {'name': costo.stabilimento.nome, 'url': reverse('stabilimenti:dettaglio', kwargs={'pk': costo.stabilimento.pk})},
            {'name': f'Costo {costo.numero_pratica}', 'url': None}
        ]
    }
    
    return render(request, 'stabilimenti/dettaglio_costo.html', context)


@login_required
@user_passes_test(stabilimenti_access_required)
def modifica_costo(request, pk):
    """Modifica costo esistente"""
    costo = get_object_or_404(CostiStabilimento, pk=pk)
    
    if not costo.can_be_modified():
        messages.error(request, 'Non è possibile modificare un costo già pagato')
        return redirect('stabilimenti:dettaglio_costo', pk=pk)
    
    if request.method == 'POST':
        form = CostiStabilimentoForm(request.POST, request.FILES, instance=costo, user=request.user)
        
        if form.is_valid():
            try:
                costo_modificato = form.save()
                messages.success(request, f'Costo "{costo.titolo}" modificato con successo')
                return redirect('stabilimenti:dettaglio_costo', pk=pk)
                
            except Exception as e:
                messages.error(request, f'Errore durante la modifica: {str(e)}')
        else:
            messages.error(request, 'Correggi gli errori nel form')
    
    else:
        form = CostiStabilimentoForm(instance=costo, user=request.user)
    
    context = {
        'form': form,
        'costo': costo,
        'page_title': f'Modifica {costo.numero_pratica}',
        'breadcrumbs': [
            {'name': 'Stabilimenti', 'url': reverse('stabilimenti:list')},
            {'name': costo.stabilimento.nome, 'url': reverse('stabilimenti:dettaglio', kwargs={'pk': costo.stabilimento.pk})},
            {'name': f'Costo {costo.numero_pratica}', 'url': reverse('stabilimenti:dettaglio_costo', kwargs={'pk': pk})},
            {'name': 'Modifica', 'url': None}
        ]
    }
    
    return render(request, 'stabilimenti/modifica_costo.html', context)


# =====================================
# VIEWS DOCUMENTI
# =====================================

@login_required
@user_passes_test(stabilimenti_access_required)
def documenti_stabilimento(request, stabilimento_pk):
    """Lista documenti di uno stabilimento"""
    stabilimento = get_object_or_404(Stabilimento, pk=stabilimento_pk)
    
    documenti = stabilimento.documenti.order_by('-data_inserimento')
    
    # Paginazione
    paginator = Paginator(documenti, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'stabilimento': stabilimento,
        'page_obj': page_obj,
        'page_title': f'Documenti {stabilimento.nome}',
        'breadcrumbs': [
            {'name': 'Stabilimenti', 'url': reverse('stabilimenti:list')},
            {'name': stabilimento.nome, 'url': reverse('stabilimenti:dettaglio', kwargs={'pk': stabilimento_pk})},
            {'name': 'Documenti', 'url': None}
        ]
    }
    
    return render(request, 'stabilimenti/documenti_stabilimento.html', context)


@login_required
@user_passes_test(stabilimenti_access_required)
def nuovo_documento(request, stabilimento_pk):
    """Nuovo documento per stabilimento"""
    stabilimento = get_object_or_404(Stabilimento, pk=stabilimento_pk)
    
    if request.method == 'POST':
        form = DocStabilimentoForm(request.POST, request.FILES, user=request.user, stabilimento=stabilimento)
        
        if form.is_valid():
            try:
                documento = form.save(commit=False)
                documento.caricato_da = request.user
                documento.save()
                
                messages.success(request, f'Documento "{documento.nome_documento}" caricato con successo')
                return redirect('stabilimenti:documenti', stabilimento_pk=stabilimento_pk)
                
            except Exception as e:
                messages.error(request, f'Errore durante il caricamento: {str(e)}')
        else:
            messages.error(request, 'Correggi gli errori nel form')
    
    else:
        form = DocStabilimentoForm(user=request.user, stabilimento=stabilimento)
    
    context = {
        'form': form,
        'stabilimento': stabilimento,
        'page_title': 'Nuovo Documento',
        'breadcrumbs': [
            {'name': 'Stabilimenti', 'url': reverse('stabilimenti:list')},
            {'name': stabilimento.nome, 'url': reverse('stabilimenti:dettaglio', kwargs={'pk': stabilimento_pk})},
            {'name': 'Documenti', 'url': reverse('stabilimenti:documenti', kwargs={'stabilimento_pk': stabilimento_pk})},
            {'name': 'Nuovo Documento', 'url': None}
        ]
    }
    
    return render(request, 'stabilimenti/nuovo_documento.html', context)


# =====================================
# VIEWS SCADENZE
# =====================================

@login_required
@user_passes_test(stabilimenti_access_required)
def scadenze_dashboard(request):
    """Dashboard scadenze documenti di tutti gli stabilimenti"""
    oggi = timezone.now().date()
    
    # Scadenze documenti per categoria temporale
    scadute = DocStabilimento.objects.filter(
        data_scadenza__lt=oggi,
        attivo=True
    ).select_related('stabilimento', 'caricato_da')
    
    questa_settimana = DocStabilimento.objects.filter(
        data_scadenza__gte=oggi,
        data_scadenza__lte=oggi + timedelta(days=7),
        attivo=True
    ).select_related('stabilimento', 'caricato_da')
    
    prossimi_30_giorni = DocStabilimento.objects.filter(
        data_scadenza__gt=oggi + timedelta(days=7),
        data_scadenza__lte=oggi + timedelta(days=30),
        attivo=True
    ).select_related('stabilimento', 'caricato_da')
    
    # DEBUG: Aggiungiamo statistiche per il debug
    tutte_scadenze = DocStabilimento.objects.filter(
        data_scadenza__isnull=False,
        attivo=True
    ).count()
    
    scadenze_future = DocStabilimento.objects.filter(
        data_scadenza__gte=oggi,
        attivo=True
    ).count()
    
    context = {
        'scadute': scadute,
        'questa_settimana': questa_settimana,
        'prossimi_30_giorni': prossimi_30_giorni,
        'debug_info': {
            'oggi': oggi,
            'tutte_scadenze': tutte_scadenze,
            'scadenze_future': scadenze_future,
        },
        'page_title': 'Scadenze Documenti Stabilimenti',
        'breadcrumbs': [
            {'name': 'Stabilimenti', 'url': reverse('stabilimenti:list')},
            {'name': 'Scadenze Documenti', 'url': None}
        ]
    }
    
    return render(request, 'stabilimenti/scadenze_dashboard.html', context)



# =====================================
# VIEWS AJAX
# =====================================

@login_required
@user_passes_test(stabilimenti_access_required)
def toggle_attivo_stabilimento(request, pk):
    """Toggle stato attivo/inattivo stabilimento"""
    if request.method == 'POST':
        stabilimento = get_object_or_404(Stabilimento, pk=pk)
        
        stabilimento.attivo = not stabilimento.attivo
        if not stabilimento.attivo:
            stabilimento.data_chiusura = timezone.now().date()
        else:
            stabilimento.data_chiusura = None
        
        stabilimento.modificato_da = request.user
        stabilimento.save()
        
        stato = "attivato" if stabilimento.attivo else "disattivato"
        messages.success(request, f'Stabilimento {stato} con successo')
        
        return JsonResponse({
            'success': True,
            'attivo': stabilimento.attivo,
            'message': f'Stabilimento {stato}'
        })
    
    return JsonResponse({'success': False})

# Aggiungi queste views al file stabilimenti/views.py esistente

from decimal import Decimal
from django.db.models import Q, Sum, Avg
from datetime import datetime, timedelta

# =====================================
# VIEWS UTENZE SPECIFICHE
# =====================================

@login_required
@user_passes_test(stabilimenti_access_required)
def utenze_stabilimento(request, stabilimento_pk):
    """Lista utenze di uno stabilimento specifico"""
    stabilimento = get_object_or_404(Stabilimento, pk=stabilimento_pk)
    
    # Query per sole utenze
    utenze_types = [
        'energia_elettrica', 'gas_naturale', 'acqua', 
        'telefonia', 'rifiuti', 'utilities'
    ]
    
    utenze = CostiStabilimento.objects.filter(
        stabilimento=stabilimento,
        causale__in=utenze_types
    ).select_related('fornitore', 'incaricato').order_by('-data_creazione')
    
    # Statistiche utenze anno corrente
    anno_corrente = timezone.now().year
    stats_anno = utenze.filter(data_fattura__year=anno_corrente).aggregate(
        totale_anno=Sum('importo'),
        media_mensile=Avg('importo'),
        count_fatture=models.Count('id')
    )
    
    # Suddivisione per tipo utenza
    stats_per_tipo = {}
    for tipo_code, tipo_display in CostiStabilimento.TipoCosto.choices:
        if tipo_code in utenze_types:
            costi_tipo = utenze.filter(
                causale=tipo_code,
                data_fattura__year=anno_corrente
            ).aggregate(totale=Sum('importo'))
            stats_per_tipo[tipo_display] = costi_tipo['totale'] or Decimal('0.00')
    
    # Prossime scadenze utenze (60 giorni)
    prossime_scadenze = utenze.filter(
        data_scadenza_servizio__gte=timezone.now().date(),
        data_scadenza_servizio__lte=timezone.now().date() + timedelta(days=60)
    ).order_by('data_scadenza_servizio')[:5]
    
    # Paginazione
    paginator = Paginator(utenze, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'stabilimento': stabilimento,
        'page_obj': page_obj,
        'stats_anno': stats_anno,
        'stats_per_tipo': stats_per_tipo,
        'prossime_scadenze': prossime_scadenze,
        'anno_corrente': anno_corrente,
        'page_title': f'Utenze {stabilimento.nome}',
        'breadcrumbs': [
            {'name': 'Stabilimenti', 'url': reverse('stabilimenti:list')},
            {'name': stabilimento.nome, 'url': reverse('stabilimenti:dettaglio', kwargs={'pk': stabilimento_pk})},
            {'name': 'Utenze', 'url': None}
        ]
    }
    
    return render(request, 'stabilimenti/utenze_stabilimento.html', context)


@login_required
@user_passes_test(stabilimenti_access_required)
def nuova_utenza(request, stabilimento_pk):
    """Nuova utenza per stabilimento"""
    stabilimento = get_object_or_404(Stabilimento, pk=stabilimento_pk)
    
    if request.method == 'POST':
        form = UtenzaForm(request.POST, request.FILES, user=request.user, stabilimento=stabilimento)
        
        # DEBUG: Stampa tutti i dati POST
        print("=== DEBUG POST DATA ===")
        for key, value in request.POST.items():
            print(f"{key}: {value}")
        print("=======================")
        
        # DEBUG: Controlla validità del form
        print(f"Form valido: {form.is_valid()}")
        if not form.is_valid():
            print(f"Errori form: {form.errors}")
            print(f"Errori non-field: {form.non_field_errors()}")
            
            # Mostra errori specifici per ogni campo
            for field_name, field in form.fields.items():
                if field_name in form.errors:
                    print(f"Errore campo {field_name}: {form.errors[field_name]}")
        
        if form.is_valid():
            try:
                utenza = form.save(commit=False)
                utenza.incaricato = request.user
                utenza.save()
                
                messages.success(request, f'Utenza "{utenza.titolo}" creata con successo')
                return redirect('stabilimenti:utenze_stabilimento', stabilimento_pk=stabilimento_pk)
                
            except Exception as e:
                print(f"ERRORE durante il salvataggio: {str(e)}")
                import traceback
                traceback.print_exc()
                messages.error(request, f'Errore durante la creazione: {str(e)}')
        else:
            messages.error(request, 'Correggi gli errori nel form')
    
    else:
        form = UtenzaForm(user=request.user, stabilimento=stabilimento)
    
    context = {
        'form': form,
        'stabilimento': stabilimento,
        'page_title': 'Nuova Utenza',
        'breadcrumbs': [
            {'name': 'Stabilimenti', 'url': reverse('stabilimenti:list')},
            {'name': stabilimento.nome, 'url': reverse('stabilimenti:dettaglio', kwargs={'pk': stabilimento_pk})},
            {'name': 'Utenze', 'url': reverse('stabilimenti:utenze_stabilimento', kwargs={'stabilimento_pk': stabilimento_pk})},
            {'name': 'Nuova Utenza', 'url': None}
        ]
    }
    
    return render(request, 'stabilimenti/nuova_utenza.html', context)

@login_required
@user_passes_test(stabilimenti_access_required)
def modifica_utenza(request, pk):
    """Modifica utenza esistente"""
    utenza = get_object_or_404(CostiStabilimento, pk=pk)
    
    # Verifica che sia effettivamente un'utenza
    utenze_types = ['energia_elettrica', 'gas_naturale', 'acqua', 'telefonia', 'rifiuti', 'utilities']
    if utenza.causale not in utenze_types:
        messages.error(request, 'Questo costo non è un\'utenza')
        return redirect('stabilimenti:dettaglio_costo', pk=pk)
    
    if not utenza.can_be_modified():
        messages.error(request, 'Non è possibile modificare un\'utenza già pagata')
        return redirect('stabilimenti:dettaglio_costo', pk=pk)
    
    if request.method == 'POST':
        form = UtenzaForm(request.POST, request.FILES, instance=utenza, user=request.user)
        
        if form.is_valid():
            try:
                utenza_modificata = form.save()
                messages.success(request, f'Utenza "{utenza.titolo}" modificata con successo')
                return redirect('stabilimenti:utenze_stabilimento', stabilimento_pk=utenza.stabilimento.pk)
                
            except Exception as e:
                messages.error(request, f'Errore durante la modifica: {str(e)}')
        else:
            messages.error(request, 'Correggi gli errori nel form')
    
    else:
        form = UtenzaForm(instance=utenza, user=request.user)
    
    context = {
        'form': form,
        'utenza': utenza,
        'stabilimento': utenza.stabilimento,
        'page_title': f'Modifica Utenza {utenza.numero_pratica}',
        'breadcrumbs': [
            {'name': 'Stabilimenti', 'url': reverse('stabilimenti:list')},
            {'name': utenza.stabilimento.nome, 'url': reverse('stabilimenti:dettaglio', kwargs={'pk': utenza.stabilimento.pk})},
            {'name': 'Utenze', 'url': reverse('stabilimenti:utenze_stabilimento', kwargs={'stabilimento_pk': utenza.stabilimento.pk})},
            {'name': f'Modifica {utenza.numero_pratica}', 'url': None}
        ]
    }
    
    return render(request, 'stabilimenti/modifica_utenza.html', context)


@login_required
@user_passes_test(stabilimenti_access_required)
def dashboard_utenze(request):
    """Dashboard generale utenze di tutti gli stabilimenti"""
    # Tipi di utenze
    utenze_types = ['energia_elettrica', 'gas_naturale', 'acqua', 'telefonia', 'rifiuti', 'utilities']
    
    # Query base utenze
    utenze = CostiStabilimento.objects.filter(
        causale__in=utenze_types
    ).select_related('stabilimento', 'fornitore')
    
    # Statistiche generali
    anno_corrente = timezone.now().year
    stats_generali = utenze.filter(data_fattura__year=anno_corrente).aggregate(
        totale_anno=Sum('importo'),
        media_mensile=Avg('importo'),
        count_fatture=models.Count('id')
    )
    
    # Costi per stabilimento
    costi_per_stabilimento = {}
    for stabilimento in Stabilimento.objects.attivi():
        costo_stabilimento = utenze.filter(
            stabilimento=stabilimento,
            data_fattura__year=anno_corrente
        ).aggregate(totale=Sum('importo'))['totale'] or Decimal('0.00')
        
        if costo_stabilimento > 0:
            costi_per_stabilimento[stabilimento] = costo_stabilimento
    
    # Ordinamento per costo decrescente
    costi_per_stabilimento = dict(
        sorted(costi_per_stabilimento.items(), key=lambda x: x[1], reverse=True)
    )
    
    # Suddivisione per tipo utenza (tutti gli stabilimenti)
    stats_per_tipo = {}
    for tipo_code, tipo_display in CostiStabilimento.TipoCosto.choices:
        if tipo_code in utenze_types:
            costi_tipo = utenze.filter(
                causale=tipo_code,
                data_fattura__year=anno_corrente
            ).aggregate(totale=Sum('importo'))
            
            total = costi_tipo['totale'] or Decimal('0.00')
            if total > 0:
                stats_per_tipo[tipo_display] = total
    
    # Prossime scadenze utenze (30 giorni)
    oggi = timezone.now().date()
    prossime_scadenze = utenze.filter(
        data_scadenza_servizio__gte=oggi,
        data_scadenza_servizio__lte=oggi + timedelta(days=30)
    ).order_by('data_scadenza_servizio')[:10]
    
    # Utenze in scadenza urgente (7 giorni)
    scadenze_urgenti = utenze.filter(
        data_scadenza_servizio__gte=oggi,
        data_scadenza_servizio__lte=oggi + timedelta(days=7)
    ).count()
    
    context = {
        'stats_generali': stats_generali,
        'costi_per_stabilimento': costi_per_stabilimento,
        'stats_per_tipo': stats_per_tipo,
        'prossime_scadenze': prossime_scadenze,
        'scadenze_urgenti': scadenze_urgenti,
        'anno_corrente': anno_corrente,
        'page_title': 'Dashboard Utenze',
        'breadcrumbs': [
            {'name': 'Stabilimenti', 'url': reverse('stabilimenti:list')},
            {'name': 'Dashboard Utenze', 'url': None}
        ]
    }
    
    return render(request, 'stabilimenti/dashboard_utenze.html', context)


@login_required
@user_passes_test(stabilimenti_access_required) 
def ricerca_utenze(request):
    """Ricerca avanzata utenze con filtri specifici"""
    utenze_types = ['energia_elettrica', 'gas_naturale', 'acqua', 'telefonia', 'rifiuti', 'utilities']
    
    # Form di ricerca (riutilizziamo CostiSearchForm ma filtrato)
    form = CostiSearchForm(request.GET or None)
    
    # Query base
    utenze = CostiStabilimento.objects.filter(
        causale__in=utenze_types
    ).select_related('stabilimento', 'fornitore', 'incaricato')
    
    # Applica filtri
    if form.is_valid():
        stabilimento = form.cleaned_data.get('stabilimento')
        if stabilimento:
            utenze = utenze.filter(stabilimento=stabilimento)
        
        causale = form.cleaned_data.get('causale')
        if causale and causale in utenze_types:
            utenze = utenze.filter(causale=causale)
        
        stato = form.cleaned_data.get('stato')
        if stato:
            utenze = utenze.filter(stato=stato)
        
        fornitore = form.cleaned_data.get('fornitore')
        if fornitore:
            utenze = utenze.filter(fornitore=fornitore)
        
        anno = form.cleaned_data.get('anno')
        if anno:
            utenze = utenze.filter(data_fattura__year=anno)
    
    # Ordinamento
    utenze = utenze.order_by('-data_fattura', '-data_creazione')
    
    # Paginazione
    paginator = Paginator(utenze, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'page_title': 'Ricerca Utenze',
        'breadcrumbs': [
            {'name': 'Stabilimenti', 'url': reverse('stabilimenti:list')},
            {'name': 'Ricerca Utenze', 'url': None}
        ]
    }
    
    return render(request, 'stabilimenti/ricerca_utenze.html', context)