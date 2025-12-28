from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy, reverse
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import Http404
from datetime import date, timedelta
import json

from .models import Dipendente, AuditLogDipendente, Presenza, GiornataLavorativa
from .forms import DipendenteCreationForm, DipendenteChangeForm, LoginForm


# =====================================================
# AUTHENTICATION VIEWS
# =====================================================

def landing_page(request):
    """
    Landing page del sistema - mostra form di login se non autenticato
    """
    if request.user.is_authenticated:
        return redirect('dipendenti:dashboard')
    
    return render(request, 'dipendenti/landing.html')


def user_login(request):
    """
    View per il login degli utenti
    """
    if request.user.is_authenticated:
        return redirect('core:dashboard_main')
    
    form = LoginForm()
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    
                    # Aggiorna ultimo accesso
                    if hasattr(user, 'aggiorna_ultimo_accesso'):
                        user.aggiorna_ultimo_accesso()
                    
                    # Log dell'accesso
                    _log_audit_action(
                        dipendente=user,
                        azione=AuditLogDipendente.TipoAzione.LOGIN,
                        eseguita_da=user,
                        request=request
                    )
                    
                    messages.success(
                        request, 
                        f'Benvenuto {user.nome_completo}! Ultimo accesso: {user.ultimo_accesso or "Mai"}'
                    )
                    
                    # Redirect to next or dashboard
                    next_url = request.GET.get('next')
                    if next_url and next_url.startswith('/'):
                        return redirect(next_url)
                    return redirect('core:dashboard_main')
                else:
                    messages.error(request, 'Account disattivato. Contatta l\'amministratore.')
            else:
                messages.error(request, 'Credenziali non valide.')
    
    return render(request, 'dipendenti/login.html', {'form': form})


def user_logout(request):
    """
    View per il logout degli utenti
    """
    if request.user.is_authenticated:
        # Log del logout
        _log_audit_action(
            dipendente=request.user,
            azione=AuditLogDipendente.TipoAzione.LOGOUT,
            eseguita_da=request.user,
            request=request
        )
        
        nome_utente = request.user.nome_completo
        logout(request)
        messages.info(request, f'Arrivederci {nome_utente}!')
    
    return redirect('dipendenti:landing')


# =====================================================
# DASHBOARD VIEWS
# =====================================================

@login_required
def dashboard(request):
    """
    Dashboard principale per dipendenti autenticati
    """
    user = request.user
    
    # Statistiche generali
    stats = {
        'totale_dipendenti': Dipendente.objects.filter(stato=Dipendente.StatoDipendente.ATTIVO).count(),
        'nuovi_questa_settimana': Dipendente.objects.filter(
            creato_il__gte=timezone.now() - timedelta(days=7)
        ).count(),
        'documenti_in_scadenza': _get_documenti_in_scadenza(),
        'ultimo_accesso_sistema': Dipendente.objects.exclude(
            ultimo_accesso__isnull=True
        ).order_by('-ultimo_accesso').first(),
    }
    
    # Notifiche personalizzate per l'utente
    notifiche = []
    
    # Verifica documenti in scadenza dell'utente
    if hasattr(user, 'documenti_in_scadenza'):
        documenti_scadenza = user.documenti_in_scadenza
        if documenti_scadenza:
            for doc in documenti_scadenza:
                if doc['scaduto']:
                    notifiche.append({
                        'tipo': 'danger',
                        'messaggio': f'Il documento {doc["tipo"]} è scaduto il {doc["scadenza"].strftime("%d/%m/%Y")}',
                        'icona': 'fas fa-exclamation-circle'
                    })
                else:
                    notifiche.append({
                        'tipo': 'warning',
                        'messaggio': f'Il documento {doc["tipo"]} scade il {doc["scadenza"].strftime("%d/%m/%Y")}',
                        'icona': 'fas fa-exclamation-triangle'
                    })
    
    # Attività recenti (per amministratori)
    attivita_recenti = []
    if user.is_amministratore:
        attivita_recenti = AuditLogDipendente.objects.select_related(
            'dipendente', 'eseguita_da'
        ).order_by('-timestamp')[:10]
    
    context = {
        'stats': stats,
        'notifiche': notifiche,
        'attivita_recenti': attivita_recenti,
        'user': user,
    }
    
    return render(request, 'dipendenti/dashboard.html', context)


# =====================================================
# DIPENDENTI CRUD VIEWS
# =====================================================

class DipendenteListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Lista dipendenti - solo per amministratori e supervisori"""
    model = Dipendente
    template_name = 'dipendenti/lista.html'
    context_object_name = 'dipendenti'
    paginate_by = 20
    
    def test_func(self):
        return self.request.user.ha_permesso(Dipendente.Autorizzazioni.SUPERVISORE)
    
    def get_queryset(self):
        queryset = Dipendente.objects.all()
        
        # Filtri di ricerca
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(codice_fiscale__icontains=search)
            )
        
        # Filtro per livello
        livello = self.request.GET.get('livello')
        if livello:
            queryset = queryset.filter(livello=livello)
        
        # Filtro per stato
        stato = self.request.GET.get('stato')
        if stato:
            queryset = queryset.filter(stato=stato)
        
        return queryset.order_by('-date_joined')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['livelli'] = Dipendente.Autorizzazioni.choices
        context['stati'] = Dipendente.StatoDipendente.choices
        context['search_query'] = self.request.GET.get('q', '')
        context['filtro_livello'] = self.request.GET.get('livello', '')
        context['filtro_stato'] = self.request.GET.get('stato', '')
        return context


class DipendenteDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Dettaglio dipendente"""
    model = Dipendente
    template_name = 'dipendenti/dettaglio.html'
    context_object_name = 'dipendente'
    
    def test_func(self):
        # L'utente può vedere i propri dati o deve essere amministratore/supervisore
        dipendente = self.get_object()
        return (
            self.request.user == dipendente or 
            self.request.user.ha_permesso(Dipendente.Autorizzazioni.SUPERVISORE)
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dipendente = self.get_object()
        
        # Aggiungi statistiche per amministratori
        if self.request.user.is_amministratore:
            context['audit_logs'] = dipendente.audit_logs.order_by('-timestamp')[:20]
        
        return context


# =====================================================
# PROFILE VIEWS
# =====================================================

@login_required
def mio_profilo(request):
    """View per visualizzare/modificare il proprio profilo"""
    user = request.user
    
    context = {
        'dipendente': user,
    }
    
    return render(request, 'dipendenti/mio_profilo.html', context)


# =====================================================
# UTILITY FUNCTIONS
# =====================================================

def _get_documenti_in_scadenza(giorni=30):
    """Restituisce conteggio documenti in scadenza entro X giorni"""
    limite = date.today() + timedelta(days=giorni)
    
    count = Dipendente.objects.filter(
        Q(carta_identita_scadenza__lte=limite) |
        Q(patente_scadenza__lte=limite)
    ).count()
    
    return count


def _log_audit_action(dipendente, azione, eseguita_da, request=None, dettagli=None):
    """Utility per registrare azioni nell'audit log"""
    ip_address = None
    if request:
        ip_address = request.META.get('REMOTE_ADDR')
        if request.META.get('HTTP_X_FORWARDED_FOR'):
            ip_address = request.META.get('HTTP_X_FORWARDED_FOR').split(',')[0]
    
    AuditLogDipendente.objects.create(
        dipendente=dipendente,
        azione=azione,
        dettagli=dettagli or {},
        eseguita_da=eseguita_da,
        indirizzo_ip=ip_address
    )


# =====================================================
# TIMBRATURA PRESENZE
# =====================================================

@login_required
def timbratura(request):
    """
    Pagina per timbrare entrata/uscita
    Accessibile a tutti gli utenti autenticati
    """
    oggi = date.today()

    # Ottieni timbrature di oggi per l'utente corrente
    timbrature_oggi = Presenza.objects.filter(
        dipendente=request.user,
        data=oggi
    ).order_by('timestamp')

    # Determina stato attuale (se è dentro o fuori)
    ultima_timbratura = timbrature_oggi.last()
    stato_attuale = 'fuori'  # Default: fuori

    if ultima_timbratura:
        if ultima_timbratura.tipo == Presenza.TipoTimbratura.ENTRATA:
            stato_attuale = 'dentro'
        else:
            stato_attuale = 'fuori'

    # Calcola ore lavorate oggi
    ore_lavorate_oggi = 0
    entrate = timbrature_oggi.filter(tipo=Presenza.TipoTimbratura.ENTRATA)
    uscite = timbrature_oggi.filter(tipo=Presenza.TipoTimbratura.USCITA)

    for i in range(min(entrate.count(), uscite.count())):
        entrata = entrate[i]
        uscita = uscite[i]
        diff = timezone.datetime.combine(oggi, uscita.orario) - timezone.datetime.combine(oggi, entrata.orario)
        ore_lavorate_oggi += diff.total_seconds() / 3600

    # Se è dentro, calcola anche le ore dall'ultima entrata a ora
    if stato_attuale == 'dentro':
        ultima_entrata = entrate.last()
        if ultima_entrata:
            diff = timezone.now() - timezone.datetime.combine(oggi, ultima_entrata.orario).replace(tzinfo=timezone.now().tzinfo)
            ore_lavorate_oggi += diff.total_seconds() / 3600

    # Calcola straordinari (oltre le 8 ore standard)
    ore_standard = 8.0
    straordinari_oggi = max(0, ore_lavorate_oggi - ore_standard)

    # Gestione POST - timbratura
    if request.method == 'POST':
        tipo_timbratura = request.POST.get('tipo')
        note = request.POST.get('note', '').strip()

        # Ottieni IP
        ip_address = request.META.get('REMOTE_ADDR')
        if request.META.get('HTTP_X_FORWARDED_FOR'):
            ip_address = request.META.get('HTTP_X_FORWARDED_FOR').split(',')[0]

        # Crea timbratura
        presenza = Presenza.objects.create(
            dipendente=request.user,
            data=oggi,
            tipo=tipo_timbratura,
            note=note if note else None,
            indirizzo_ip=ip_address
        )

        tipo_text = "ENTRATA" if tipo_timbratura == Presenza.TipoTimbratura.ENTRATA else "USCITA"
        messages.success(
            request,
            f"{tipo_text} registrata alle {presenza.orario.strftime('%H:%M:%S')}"
        )

        return redirect('dipendenti:timbratura')

    # Timbrature della settimana
    inizio_settimana = oggi - timedelta(days=oggi.weekday())
    fine_settimana = inizio_settimana + timedelta(days=6)

    timbrature_settimana = Presenza.objects.filter(
        dipendente=request.user,
        data__gte=inizio_settimana,
        data__lte=fine_settimana
    ).order_by('-data', '-timestamp')

    # Giornate concluse della settimana
    giornate_concluse = GiornataLavorativa.objects.filter(
        dipendente=request.user,
        data__gte=inizio_settimana,
        data__lte=fine_settimana
    ).order_by('-data')

    # Crea dizionario delle giornate concluse per data
    giornate_map = {g.data: g for g in giornate_concluse}

    # Prepara dati per la tabella settimanale
    from collections import defaultdict
    timbrature_per_giorno = defaultdict(list)
    for t in timbrature_settimana:
        timbrature_per_giorno[t.data].append(t)

    giornate_settimana = []
    for data_giorno in sorted(timbrature_per_giorno.keys(), reverse=True):
        giornata_conclusa = giornate_map.get(data_giorno)
        giornate_settimana.append({
            'data': data_giorno,
            'timbrature': timbrature_per_giorno[data_giorno],
            'conclusa': giornata_conclusa is not None,
            'ore_lavorate': giornata_conclusa.ore_lavorate if giornata_conclusa else None,
            'ore_straordinari': giornata_conclusa.ore_straordinari if giornata_conclusa else None,
        })

    # Verifica se oggi è già stata conclusa
    giornata_oggi_conclusa = GiornataLavorativa.objects.filter(
        dipendente=request.user,
        data=oggi
    ).first()

    context = {
        'timbrature_oggi': timbrature_oggi,
        'stato_attuale': stato_attuale,
        'ore_lavorate_oggi': round(ore_lavorate_oggi, 2),
        'straordinari_oggi': round(straordinari_oggi, 2),
        'giornate_settimana': giornate_settimana,
        'giornata_oggi_conclusa': giornata_oggi_conclusa,
        'oggi': oggi,
    }

    return render(request, 'dipendenti/timbratura.html', context)


@login_required
def concludi_giornata(request):
    """
    Conclude la giornata lavorativa corrente, calcolando ore totali e straordinari
    """
    oggi = date.today()

    # Verifica se la giornata è già stata conclusa
    giornata_esistente = GiornataLavorativa.objects.filter(
        dipendente=request.user,
        data=oggi
    ).first()

    if giornata_esistente:
        messages.warning(request, f'La giornata del {oggi.strftime("%d/%m/%Y")} è già stata conclusa alle {giornata_esistente.timestamp_conclusione.strftime("%H:%M")}.')
        return redirect('dipendenti:timbratura')

    # Recupera tutte le timbrature di oggi
    timbrature_oggi = Presenza.objects.filter(
        dipendente=request.user,
        data=oggi
    ).order_by('timestamp')

    if not timbrature_oggi.exists():
        messages.error(request, 'Non ci sono timbrature da concludere per oggi.')
        return redirect('dipendenti:timbratura')

    # Calcola ore lavorate
    ore_lavorate = 0
    entrate = timbrature_oggi.filter(tipo=Presenza.TipoTimbratura.ENTRATA)
    uscite = timbrature_oggi.filter(tipo=Presenza.TipoTimbratura.USCITA)

    for i in range(min(entrate.count(), uscite.count())):
        entrata = entrate[i]
        uscita = uscite[i]
        diff = timezone.datetime.combine(oggi, uscita.orario) - timezone.datetime.combine(oggi, entrata.orario)
        ore_lavorate += diff.total_seconds() / 3600

    # Calcola straordinari
    ore_standard = 8.0
    straordinari = max(0, ore_lavorate - ore_standard)

    # Gestione POST - conferma conclusione
    if request.method == 'POST':
        note_conclusione = request.POST.get('note_conclusione', '').strip()

        # Crea record giornata lavorativa
        giornata = GiornataLavorativa.objects.create(
            dipendente=request.user,
            data=oggi,
            ore_lavorate=round(ore_lavorate, 2),
            ore_straordinari=round(straordinari, 2),
            ore_standard=ore_standard,
            note_conclusione=note_conclusione if note_conclusione else None
        )

        messages.success(
            request,
            f'Giornata conclusa con successo! Ore lavorate: {giornata.ore_lavorate}h - Straordinari: {giornata.ore_straordinari}h'
        )
        return redirect('dipendenti:timbratura')

    # Mostra conferma
    context = {
        'oggi': oggi,
        'timbrature': timbrature_oggi,
        'ore_lavorate': round(ore_lavorate, 2),
        'straordinari': round(straordinari, 2),
        'ore_standard': ore_standard,
        'entrate_count': entrate.count(),
        'uscite_count': uscite.count(),
    }

    return render(request, 'dipendenti/concludi_giornata.html', context)


@login_required
def report_presenze(request):
    """
    Genera report presenze personalizzato per l'utente autenticato
    Supporta selezione date e export in PDF/Excel
    """
    from collections import defaultdict
    from django.http import HttpResponse
    import json

    # Parametri della richiesta
    data_inizio = request.GET.get('data_inizio')
    data_fine = request.GET.get('data_fine')
    formato = request.GET.get('formato', 'web')  # web, pdf, excel

    # Validazione date
    if not data_inizio or not data_fine:
        messages.error(request, 'Seleziona un periodo valido per generare il report.')
        return redirect('dipendenti:timbratura')

    try:
        from datetime import datetime
        data_inizio_obj = datetime.strptime(data_inizio, '%Y-%m-%d').date()
        data_fine_obj = datetime.strptime(data_fine, '%Y-%m-%d').date()

        if data_inizio_obj > data_fine_obj:
            messages.error(request, 'La data di inizio non può essere successiva alla data di fine.')
            return redirect('dipendenti:timbratura')

    except ValueError:
        messages.error(request, 'Formato date non valido.')
        return redirect('dipendenti:timbratura')

    # Recupera timbrature nel periodo
    timbrature = Presenza.objects.filter(
        dipendente=request.user,
        data__gte=data_inizio_obj,
        data__lte=data_fine_obj
    ).order_by('data', 'timestamp')

    # Raggruppa per giorno e calcola ore
    timbrature_per_giorno = defaultdict(list)
    for t in timbrature:
        timbrature_per_giorno[t.data].append(t)

    # Calcola statistiche per ogni giorno
    ore_standard = 8.0
    report_giorni = []
    totale_ore = 0
    totale_straordinari = 0

    for data_giorno in sorted(timbrature_per_giorno.keys()):
        timbrature_giorno = timbrature_per_giorno[data_giorno]

        # Separa entrate e uscite
        entrate = [t for t in timbrature_giorno if t.tipo == Presenza.TipoTimbratura.ENTRATA]
        uscite = [t for t in timbrature_giorno if t.tipo == Presenza.TipoTimbratura.USCITA]

        # Calcola ore lavorate
        ore_lavorate = 0
        for i in range(min(len(entrate), len(uscite))):
            diff = timezone.datetime.combine(data_giorno, uscite[i].orario) - \
                   timezone.datetime.combine(data_giorno, entrate[i].orario)
            ore_lavorate += diff.total_seconds() / 3600

        # Calcola straordinari
        straordinari = max(0, ore_lavorate - ore_standard)

        totale_ore += ore_lavorate
        totale_straordinari += straordinari

        report_giorni.append({
            'data': data_giorno,
            'entrate': entrate,
            'uscite': uscite,
            'ore_lavorate': round(ore_lavorate, 2),
            'straordinari': round(straordinari, 2),
            'note': ', '.join([t.note for t in timbrature_giorno if t.note])
        })

    # Statistiche generali
    giorni_lavorati = len(report_giorni)
    media_ore_giorno = round(totale_ore / giorni_lavorati, 2) if giorni_lavorati > 0 else 0

    context = {
        'data_inizio': data_inizio_obj,
        'data_fine': data_fine_obj,
        'report_giorni': report_giorni,
        'totale_ore': round(totale_ore, 2),
        'totale_straordinari': round(totale_straordinari, 2),
        'giorni_lavorati': giorni_lavorati,
        'media_ore_giorno': media_ore_giorno,
        'ore_standard': ore_standard,
    }

    # Export PDF
    if formato == 'pdf':
        return _genera_report_pdf(request.user, context)

    # Export Excel
    elif formato == 'excel':
        return _genera_report_excel(request.user, context)

    # Visualizzazione web
    return render(request, 'dipendenti/report_presenze.html', context)


def _genera_report_pdf(dipendente, context):
    """Genera report presenze in formato PDF"""
    from django.template.loader import render_to_string
    from core.pdf_generator import generate_pdf_from_html, PDFConfig
    from django.http import HttpResponse

    html_content = render_to_string('dipendenti/report_presenze_pdf.html', {
        **context,
        'dipendente': dipendente
    })

    config = PDFConfig(
        page_size='A4',
        margins={'top': 1.5, 'bottom': 1.5, 'left': 1.5, 'right': 1.5}  # in cm
    )

    pdf_buffer = generate_pdf_from_html(html_content=html_content, config=config, output_type='buffer')

    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    filename = f"Report_Presenze_{dipendente.username}_{context['data_inizio'].strftime('%Y%m%d')}-{context['data_fine'].strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


def _genera_report_excel(dipendente, context):
    """Genera report presenze in formato Excel usando core.excel_generator"""
    from core.excel_generator import generate_excel_from_data, ExcelConfig

    # Prepara dati principali
    data = []
    for giorno in context['report_giorni']:
        # Entrate e uscite come stringhe
        entrate_str = ', '.join([e.orario.strftime('%H:%M') for e in giorno['entrate']])
        uscite_str = ', '.join([u.orario.strftime('%H:%M') for u in giorno['uscite']])

        data.append({
            'Data': giorno['data'],
            'Giorno': giorno['data'].strftime('%A'),
            'Entrate': entrate_str,
            'Uscite': uscite_str,
            'Ore Lavorate': float(giorno['ore_lavorate']),
            'Straordinari': float(giorno['straordinari']),
            'Note': giorno['note'] or ''
        })

    # Riga vuota
    data.append({k: '' for k in data[0].keys()})

    # Totali
    data.append({
        'Data': '',
        'Giorno': '',
        'Entrate': '',
        'Uscite': 'TOTALE:',
        'Ore Lavorate': float(context['totale_ore']),
        'Straordinari': float(context['totale_straordinari']),
        'Note': ''
    })

    # Riga vuota
    data.append({k: '' for k in data[0].keys()})

    # Statistiche
    data.append({
        'Data': 'Giorni lavorati:',
        'Giorno': context['giorni_lavorati'],
        'Entrate': '',
        'Uscite': '',
        'Ore Lavorate': '',
        'Straordinari': '',
        'Note': ''
    })
    data.append({
        'Data': 'Media ore/giorno:',
        'Giorno': f"{context['media_ore_giorno']:.2f}",
        'Entrate': '',
        'Uscite': '',
        'Ore Lavorate': '',
        'Straordinari': '',
        'Note': ''
    })

    # Configurazione Excel
    filename = f"Report_Presenze_{dipendente.username}_{context['data_inizio'].strftime('%Y%m%d')}-{context['data_fine'].strftime('%Y%m%d')}.xlsx"

    config = ExcelConfig(
        filename=filename,
        sheet_name="Report Presenze",
        auto_fit_columns=True,
        add_filters=True,
        freeze_panes="A2"
    )

    return generate_excel_from_data(
        data=data,
        config=config,
        output_type='response'
    )
