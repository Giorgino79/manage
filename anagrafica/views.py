"""
ANAGRAFICA VIEWS - Views per gestione clienti e fornitori
========================================================

Views per la gestione anagrafica (senza rappresentanti):
- Cliente: Gestione clienti con limite credito
- Fornitore: Gestione fornitori con dati fiscali

NOTA: Tutte le funzioni relative ai rappresentanti sono state rimosse
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.utils.translation import gettext as _
from decimal import Decimal
import csv
import json

from .models import Cliente, Fornitore
from .forms import ClienteForm, FornitoreForm


class StaffRequiredMixin(UserPassesTestMixin):
    """Mixin per verificare che l'utente sia staff"""
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser


# ================== DASHBOARD ==================

@login_required
def dashboard_anagrafica(request):
    """Dashboard principale dell'anagrafica con statistiche crediti"""
    
    # Statistiche base
    totale_clienti = Cliente.objects.filter(attivo=True).count()
    totale_fornitori = Fornitore.objects.filter(attivo=True).count()
    
    # === STATISTICHE CREDITO ===
    # Totale crediti concessi
    totale_crediti_concessi = Cliente.objects.filter(
        attivo=True
    ).aggregate(
        totale=Sum('limite_credito')
    )['totale'] or Decimal('0.00')
    
    # Clienti con limite credito > 0
    clienti_con_credito = Cliente.objects.filter(
        attivo=True,
        limite_credito__gt=0
    ).count()
    
    # Clienti in situazione critica (credito utilizzato > 90%)
    clienti_critici = []
    for cliente in Cliente.objects.filter(attivo=True, limite_credito__gt=0):
        stato_credito = cliente.get_stato_credito()
        if stato_credito['stato'] == 'critico':
            clienti_critici.append(cliente)
    
    context = {
        # Statistiche base
        'totale_clienti': totale_clienti,
        'totale_fornitori': totale_fornitori,
        
        # Statistiche credito
        'totale_crediti_concessi': totale_crediti_concessi,
        'clienti_con_credito': clienti_con_credito,
        'clienti_critici_count': len(clienti_critici),
        'clienti_critici': clienti_critici[:5],  # Top 5 per dashboard
        
        'page_title': 'Dashboard Anagrafica',
    }
    return render(request, 'anagrafica/dashboard.html', context)


# ================== CLIENTI ==================

class ClienteListView(LoginRequiredMixin, ListView):
    """Lista clienti con info credito"""
    model = Cliente
    template_name = 'anagrafica/clienti/elenco.html'
    context_object_name = 'clienti'
    paginate_by = 20

    def get_queryset(self):
        queryset = Cliente.objects.all()
        
        # Filtri di ricerca
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(nome__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(telefono__icontains=search_query)
            )
        
        # Filtro per città
        citta_filter = self.request.GET.get('citta')
        if citta_filter:
            queryset = queryset.filter(citta__icontains=citta_filter)
        
        # Filtro per stato attivo
        attivo_filter = self.request.GET.get('attivo')
        if attivo_filter == '1':
            queryset = queryset.filter(attivo=True)
        elif attivo_filter == '0':
            queryset = queryset.filter(attivo=False)
        
        # Filtro credito
        credito_filter = self.request.GET.get('credito')
        if credito_filter == 'con_limite':
            queryset = queryset.filter(limite_credito__gt=0)
        elif credito_filter == 'senza_limite':
            queryset = queryset.filter(limite_credito=0)
        
        # Ordinamento
        ordine = self.request.GET.get('ordine', '-created_at')
        if ordine in ['nome', '-nome', 'created_at', '-created_at']:
            queryset = queryset.order_by(ordine)
        else:
            queryset = queryset.order_by('-created_at')
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Elenco Clienti'
        context['search_query'] = self.request.GET.get('search', '')
        context['credito_filter'] = self.request.GET.get('credito', '')
        
        # Statistiche credito nella lista
        queryset = self.get_queryset()
        context['totale_crediti'] = queryset.aggregate(
            totale=Sum('limite_credito')
        )['totale'] or Decimal('0.00')
        
        # Statistiche per il footer (opzionali)
        stats = {
            'totali': Cliente.objects.count(),
            'attivi': Cliente.objects.filter(attivo=True).count(),
            'inattivi': Cliente.objects.filter(attivo=False).count(),
        }
        
        # Clienti aggiunti questo mese
        from datetime import datetime
        primo_del_mese = datetime.now().replace(day=1)
        stats['questo_mese'] = Cliente.objects.filter(
            created_at__gte=primo_del_mese
        ).count()
        
        context['stats'] = stats
        return context


class ClienteDetailView(LoginRequiredMixin, DetailView):
    """Dettaglio cliente con stato credito completo"""
    model = Cliente
    template_name = 'anagrafica/clienti/dettaglio.html'
    context_object_name = 'cliente'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Cliente: {self.object.nome}'
        
        # Informazioni credito dettagliate
        context['stato_credito'] = self.object.get_stato_credito()
        context['credito_utilizzato'] = self.object.credito_utilizzato
        context['credito_disponibile'] = self.object.credito_disponibile
        
        return context


class ClienteCreateView(LoginRequiredMixin, CreateView):
    """Creazione cliente"""
    model = Cliente
    form_class = ClienteForm
    template_name = 'anagrafica/clienti/nuovo.html'
    success_url = reverse_lazy('anagrafica:elenco_clienti')

    def form_valid(self, form):
        response = super().form_valid(form)
        
        messages.success(
            self.request, 
            f'✅ Cliente "{self.object.nome}" creato con successo!'
        )
        
        # Messaggio aggiuntivo per info credito
        if self.object.limite_credito > 0:
            messages.info(
                self.request, 
                f'💰 Limite credito impostato: €{self.object.limite_credito}'
            )
        
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Nuovo Cliente'
        return context


class ClienteUpdateView(LoginRequiredMixin, UpdateView):
    """Modifica cliente"""
    model = Cliente
    form_class = ClienteForm
    template_name = 'anagrafica/clienti/modifica.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Cliente {self.object.nome} aggiornato con successo!')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Modifica: {self.object.nome}'
        
        # Mostra stato credito attuale
        context['stato_credito_attuale'] = self.object.get_stato_credito()
        
        return context


class ClienteDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminazione cliente"""
    model = Cliente
    template_name = 'anagrafica/clienti/elimina.html'
    success_url = reverse_lazy('anagrafica:elenco_clienti')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        messages.success(request, f'Cliente {self.object.nome} eliminato con successo!')
        return super().delete(request, *args, **kwargs)


# ================== FORNITORI ==================

class FornitoreListView(LoginRequiredMixin, ListView):
    """Lista fornitori"""
    model = Fornitore
    template_name = 'anagrafica/fornitori/elenco.html'
    context_object_name = 'fornitori'
    paginate_by = 20

    def get_queryset(self):
        queryset = Fornitore.objects.all()
        
        # Filtro per ricerca generale (nome)
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(nome__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(telefono__icontains=search_query) |
                Q(categoria__icontains=search_query)
            )
        
        # Filtro per città
        citta_filter = self.request.GET.get('citta')
        if citta_filter:
            queryset = queryset.filter(citta__icontains=citta_filter)
        
        # Filtro per stato attivo
        attivo_filter = self.request.GET.get('attivo')
        if attivo_filter == '1':
            queryset = queryset.filter(attivo=True)
        elif attivo_filter == '0':
            queryset = queryset.filter(attivo=False)
        
        # Ordinamento
        ordine = self.request.GET.get('ordine', '-created_at')
        if ordine in ['nome', '-nome', 'created_at', '-created_at']:
            queryset = queryset.order_by(ordine)
        else:
            queryset = queryset.order_by('-created_at')
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Elenco Fornitori'
        
        # Statistiche per il footer
        stats = {
            'totali': Fornitore.objects.count(),
            'attivi': Fornitore.objects.filter(attivo=True).count(),
            'inattivi': Fornitore.objects.filter(attivo=False).count(),
        }
        
        # Fornitori aggiunti questo mese
        from datetime import datetime, timedelta
        primo_del_mese = datetime.now().replace(day=1)
        stats['questo_mese'] = Fornitore.objects.filter(
            created_at__gte=primo_del_mese
        ).count()
        
        context['stats'] = stats
        return context


class FornitoreDetailView(LoginRequiredMixin, DetailView):
    """Dettaglio fornitore"""
    model = Fornitore
    template_name = 'anagrafica/fornitori/dettaglio.html'
    context_object_name = 'fornitore'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Fornitore: {self.object.nome}'
        return context


class FornitoreCreateView(LoginRequiredMixin, CreateView):
    """Creazione fornitore"""
    model = Fornitore
    form_class = FornitoreForm
    template_name = 'anagrafica/fornitori/nuovo.html'
    success_url = reverse_lazy('anagrafica:elenco_fornitori')

    def form_valid(self, form):
        print(f"🟢 FORM VALID - Dati: {form.cleaned_data}")
        response = super().form_valid(form)
        messages.success(self.request, f'Fornitore {self.object.nome} creato con successo!')
        return response
    
    def form_invalid(self, form):
        print(f"🔴 FORM INVALID - Errori: {form.errors}")
        print(f"🔴 Non-field errors: {form.non_field_errors()}")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Nuovo Fornitore'
        return context


class FornitoreUpdateView(LoginRequiredMixin, UpdateView):
    """Modifica fornitore"""
    model = Fornitore
    form_class = FornitoreForm
    template_name = 'anagrafica/fornitori/modifica.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Fornitore {self.object.nome} aggiornato con successo!')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Modifica: {self.object.nome}'
        return context


class FornitoreDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminazione fornitore"""
    model = Fornitore
    template_name = 'anagrafica/fornitori/elimina.html'
    success_url = reverse_lazy('anagrafica:elenco_fornitori')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        messages.success(request, f'Fornitore {self.object.nome} eliminato con successo!')
        return super().delete(request, *args, **kwargs)


# ================== API E UTILITIES ==================

@login_required
def api_search_anagrafica(request):
    """API per ricerca nell'anagrafica"""
    query = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '')
    
    results = []
    
    if len(query) >= 2:
        # Cerca nei clienti
        if not tipo or tipo == 'clienti':
            clienti = Cliente.objects.filter(
                Q(nome__icontains=query) |
                Q(email__icontains=query) |
                Q(telefono__icontains=query)
            )[:10]
            
            for c in clienti:
                results.append({
                    'tipo': 'cliente',
                    'id': c.id,
                    'nome': c.nome,
                    'email': c.email,
                    'telefono': c.telefono,
                    'limite_credito': float(c.limite_credito),
                    'stato_credito': c.get_stato_credito(),
                    'url': c.get_absolute_url()
                })
        
        # Cerca nei fornitori
        if not tipo or tipo == 'fornitori':
            fornitori = Fornitore.objects.filter(
                Q(nome__icontains=query) |
                Q(email__icontains=query) |
                Q(telefono__icontains=query)
            )[:10]
            
            for f in fornitori:
                results.append({
                    'tipo': 'fornitore',
                    'id': f.id,
                    'nome': f.nome,
                    'email': f.email,
                    'telefono': f.telefono,
                    'url': f.get_absolute_url()
                })
    
    return JsonResponse({'results': results})


@login_required
def api_verifica_limite_credito(request):
    """API per verificare limite credito cliente"""
    cliente_id = request.GET.get('cliente_id')
    importo = request.GET.get('importo', 0)
    
    if not cliente_id:
        return JsonResponse({'error': 'cliente_id richiesto'}, status=400)
    
    try:
        cliente = Cliente.objects.get(id=cliente_id)
        importo = Decimal(str(importo))
        
        can_order = cliente.can_order_amount(importo)
        
        return JsonResponse({
            'autorizzato': can_order,
            'limite_credito': float(cliente.limite_credito),
            'credito_utilizzato': float(cliente.credito_utilizzato),
            'credito_disponibile': float(cliente.credito_disponibile),
            'importo_richiesto': float(importo),
            'stato_credito': cliente.get_stato_credito(),
            'eccedenza': float(max(0, importo - cliente.credito_disponibile)) if not can_order else 0
        })
        
    except Cliente.DoesNotExist:
        return JsonResponse({'error': 'Cliente non trovato'}, status=404)
    except ValueError:
        return JsonResponse({'error': 'Importo non valido'}, status=400)


@login_required
def export_anagrafica(request):
    """Export dati anagrafica in CSV"""
    tipo = request.GET.get('tipo', 'clienti')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{tipo}_{request.user.id}.csv"'
    
    writer = csv.writer(response)
    
    if tipo == 'clienti':
        writer.writerow([
            'Nome', 'Email', 'Telefono', 
            'Limite Credito', 'Credito Utilizzato', 'Credito Disponibile', 'Attivo'
        ])
        clienti = Cliente.objects.all()
        
        for cliente in clienti:
            writer.writerow([
                cliente.nome,
                cliente.email,
                cliente.telefono,
                float(cliente.limite_credito),
                float(cliente.credito_utilizzato),
                float(cliente.credito_disponibile),
                'Sì' if cliente.attivo else 'No'
            ])
    
    elif tipo == 'fornitori':
        writer.writerow(['Nome', 'Email', 'Telefono', 'Categoria', 'Attivo'])
        fornitori = Fornitore.objects.all()
        
        for fornitore in fornitori:
            writer.writerow([
                fornitore.nome,
                fornitore.email,
                fornitore.telefono,
                fornitore.get_categoria_display(),
                'Sì' if fornitore.attivo else 'No'
            ])
    
    return response


@login_required
def toggle_attivo(request, tipo, pk):
    """Toggle stato attivo/inattivo per entità anagrafica"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Non hai i permessi per questa operazione.')
        return redirect('anagrafica:dashboard')
    
    if tipo == 'cliente':
        obj = get_object_or_404(Cliente, pk=pk)
        obj.attivo = not obj.attivo
        obj.save()
        messages.success(request, f'Cliente {obj.nome} {"attivato" if obj.attivo else "disattivato"}.')
        return redirect('anagrafica:elenco_clienti')
    
    elif tipo == 'fornitore':
        obj = get_object_or_404(Fornitore, pk=pk)
        obj.attivo = not obj.attivo
        obj.save()
        messages.success(request, f'Fornitore {obj.nome} {"attivato" if obj.attivo else "disattivato"}.')
        return redirect('anagrafica:elenco_fornitori')
    
    messages.error(request, 'Tipo non valido.')
    return redirect('anagrafica:dashboard')


# === REPORT CREDITI ===

@login_required
def report_crediti_clienti(request):
    """Report dettagliato sui crediti dei clienti"""
    
    # Filtri
    clienti_qs = Cliente.objects.filter(attivo=True)
    
    # Filtro per stato credito
    stato_credito = request.GET.get('stato')
    if stato_credito:
        if stato_credito == 'con_limite':
            clienti_qs = clienti_qs.filter(limite_credito__gt=0)
        elif stato_credito == 'senza_limite':
            clienti_qs = clienti_qs.filter(limite_credito=0)
    
    # Calcola stati credito per ogni cliente
    clienti_con_stato = []
    totale_crediti = 0
    totale_utilizzato = 0
    clienti_critici = 0
    clienti_attenzione = 0
    
    for cliente in clienti_qs:
        stato = cliente.get_stato_credito()
        credito_utilizzato = cliente.credito_utilizzato
        
        clienti_con_stato.append({
            'cliente': cliente,
            'stato_credito': stato,
            'credito_utilizzato': credito_utilizzato,
            'credito_disponibile': cliente.credito_disponibile,
            'percentuale_uso': (credito_utilizzato / cliente.limite_credito * 100) if cliente.limite_credito > 0 else 0
        })
        
        totale_crediti += cliente.limite_credito
        totale_utilizzato += credito_utilizzato
        
        if stato['stato'] == 'critico':
            clienti_critici += 1
        elif stato['stato'] == 'attenzione':
            clienti_attenzione += 1
    
    # Ordina per percentuale utilizzo decrescente
    clienti_con_stato.sort(key=lambda x: x['percentuale_uso'], reverse=True)
    
    context = {
        'page_title': 'Report Crediti Clienti',
        'clienti_con_stato': clienti_con_stato,
        'totale_crediti': totale_crediti,
        'totale_utilizzato': totale_utilizzato,
        'totale_disponibile': totale_crediti - totale_utilizzato,
        'percentuale_utilizzo_globale': (totale_utilizzato / totale_crediti * 100) if totale_crediti > 0 else 0,
        'clienti_critici': clienti_critici,
        'clienti_attenzione': clienti_attenzione,
        'stato_filter': stato_credito,
    }
    
    return render(request, 'anagrafica/report_crediti.html', context)


# === API DASHBOARD ===

@login_required
def api_dashboard_stats(request):
    """API per statistiche dashboard real-time"""
    
    stats = {
        'clienti_attivi': Cliente.objects.filter(attivo=True).count(),
        'fornitori_attivi': Fornitore.objects.filter(attivo=True).count(),
    }
    
    # Statistiche crediti
    clienti_con_credito = Cliente.objects.filter(attivo=True, limite_credito__gt=0)
    stats['clienti_con_credito'] = clienti_con_credito.count()
    stats['totale_crediti_concessi'] = float(
        clienti_con_credito.aggregate(Sum('limite_credito'))['limite_credito__sum'] or 0
    )
    
    # Calcola crediti utilizzati
    credito_utilizzato_totale = sum(
        cliente.credito_utilizzato for cliente in clienti_con_credito
    )
    stats['credito_utilizzato_totale'] = float(credito_utilizzato_totale)
    stats['credito_disponibile_totale'] = stats['totale_crediti_concessi'] - stats['credito_utilizzato_totale']
    
    # Clienti in stato critico
    clienti_critici = 0
    for cliente in clienti_con_credito:
        if cliente.get_stato_credito()['stato'] == 'critico':
            clienti_critici += 1
    stats['clienti_critici'] = clienti_critici
    
    return JsonResponse(stats)