"""
CORE ALLEGATI VIEWS - Views per gestione allegati
================================================

Views per il sistema CRUD allegati universale con modal Bootstrap.
Tutte le operazioni sono gestite via AJAX per un'esperienza fluida.

Caratteristiche:
- 🔄 CRUD completo con modal
- 🔒 Controllo permessi integrato
- 📱 Responsive design
- ⚡ AJAX per performance
- 🎯 API REST per integrazione

Versione: 1.0
"""

import json
import mimetypes
import os
from typing import Dict, Any, List, Optional

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import (
    HttpResponse, JsonResponse, Http404, HttpResponseForbidden,
    FileResponse, HttpResponseRedirect
)
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
)

from ..models.allegati import Allegato
from ..forms.allegati import (
    AllegatoForm, AllegatoQuickForm, AllegatoSearchForm, AllegatoBulkActionForm
)
from ..mixins.allegati import AllegatiMixin


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_parent_object(content_type_id, object_id):
    """
    Ottieni oggetto parent da ContentType e ID.
    
    Args:
        content_type_id: ID del ContentType
        object_id: ID dell'oggetto
        
    Returns:
        Model instance: Oggetto parent
        
    Raises:
        Http404: Se oggetto non trovato
    """
    try:
        content_type = ContentType.objects.get(pk=content_type_id)
        model_class = content_type.model_class()
        return get_object_or_404(model_class, pk=object_id)
    except (ContentType.DoesNotExist, ValueError):
        raise Http404("Oggetto parent non trovato")


def check_allegato_permission(user, allegato, action='view'):
    """
    Verifica permessi utente su allegato.
    
    Args:
        user: User instance
        allegato: Allegato instance
        action: Tipo azione ('view', 'edit', 'delete')
        
    Returns:
        bool: True se autorizzato
        
    Raises:
        PermissionDenied: Se non autorizzato
    """
    if user.is_superuser:
        return True
    
    if action == 'view':
        if not allegato.can_view(user):
            raise PermissionDenied("Non autorizzato a visualizzare questo allegato")
    
    elif action == 'edit':
        if not allegato.can_edit(user):
            raise PermissionDenied("Non autorizzato a modificare questo allegato")
    
    elif action == 'delete':
        if not allegato.can_delete(user):
            raise PermissionDenied("Non autorizzato a eliminare questo allegato")
    
    return True


# =============================================================================
# MODAL VIEWS (AJAX)
# =============================================================================

@method_decorator(login_required, name='dispatch')
class AllegatoCreateView(CreateView):
    """
    View per creazione allegato via modal.
    Risponde con HTML per modal o JSON per AJAX.
    """
    
    model = Allegato
    form_class = AllegatoForm
    template_name = 'core/allegati/allegato_modal_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        
        # Passa parametri parent object
        kwargs['content_type_id'] = self.request.GET.get('ct') or self.request.POST.get('content_type_id')
        kwargs['object_id'] = self.request.GET.get('oid') or self.request.POST.get('object_id')
        kwargs['user'] = self.request.user
        
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Info oggetto parent per il modal
        content_type_id = self.request.GET.get('ct')
        object_id = self.request.GET.get('oid')
        
        if content_type_id and object_id:
            try:
                parent_object = get_parent_object(content_type_id, object_id)
                context['parent_object'] = parent_object
                context['content_type_id'] = content_type_id
                context['object_id'] = object_id
            except Http404:
                pass
        
        context['modal_title'] = 'Aggiungi Allegato'
        context['modal_action'] = 'create'
        
        return context
    
    def form_valid(self, form):
        """Gestisce submit form valido"""
        
        # Salva allegato
        allegato = form.save()
        
        # Risposta diversa per AJAX vs form normale
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Risposta AJAX JSON
            return JsonResponse({
                'success': True,
                'message': f'Allegato "{allegato.titolo}" creato con successo',
                'allegato_id': allegato.pk,
                'allegato_html': self._render_allegato_item(allegato)
            })
        else:
            # Redirect normale
            messages.success(self.request, f'Allegato "{allegato.titolo}" creato con successo')
            return HttpResponseRedirect(self._get_success_url())
    
    def form_invalid(self, form):
        """Gestisce form con errori"""
        
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Risposta AJAX con errori
            return JsonResponse({
                'success': False,
                'errors': form.errors,
                'form_html': render_to_string(
                    self.template_name,
                    {'form': form, **self.get_context_data()},
                    request=self.request
                )
            })
        else:
            return super().form_invalid(form)
    
    def _render_allegato_item(self, allegato):
        """Renderizza HTML per singolo allegato"""
        return render_to_string(
            'core/allegati/allegato_item_card.html',
            {'allegato': allegato},
            request=self.request
        )
    
    def _get_success_url(self):
        """URL di redirect dopo creazione"""
        content_type_id = self.request.POST.get('content_type_id')
        object_id = self.request.POST.get('object_id')
        
        if content_type_id and object_id:
            try:
                parent_object = get_parent_object(content_type_id, object_id)
                if hasattr(parent_object, 'get_absolute_url'):
                    return parent_object.get_absolute_url()
            except Http404:
                pass
        
        return reverse('core:dashboard')


@method_decorator(login_required, name='dispatch')
class AllegatoUpdateView(UpdateView):
    """View per modifica allegato via modal"""
    
    model = Allegato
    form_class = AllegatoForm
    template_name = 'core/allegati/allegato_modal_form.html'
    
    def get_object(self):
        allegato = super().get_object()
        check_allegato_permission(self.request.user, allegato, 'edit')
        return allegato
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modal_title'] = f'Modifica Allegato: {self.object.titolo}'
        context['modal_action'] = 'update'
        context['parent_object'] = self.object.content_object
        return context
    
    def form_valid(self, form):
        allegato = form.save()
        
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Allegato "{allegato.titolo}" modificato con successo',
                'allegato_html': self._render_allegato_item(allegato)
            })
        else:
            messages.success(self.request, f'Allegato "{allegato.titolo}" modificato')
            return HttpResponseRedirect(self.get_success_url())
    
    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors,
                'form_html': render_to_string(
                    self.template_name,
                    {'form': form, **self.get_context_data()},
                    request=self.request
                )
            })
        return super().form_invalid(form)
    
    def _render_allegato_item(self, allegato):
        return render_to_string(
            'core/allegati/allegato_item_card.html',
            {'allegato': allegato},
            request=self.request
        )


@method_decorator(login_required, name='dispatch')
class AllegatoDetailView(DetailView):
    """View per visualizzazione dettaglio allegato via modal"""
    
    model = Allegato
    template_name = 'core/allegati/allegato_modal_detail.html'
    context_object_name = 'allegato'
    
    def get_object(self):
        allegato = super().get_object()
        check_allegato_permission(self.request.user, allegato, 'view')
        return allegato
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_object'] = self.object.content_object
        context['can_edit'] = self.object.can_edit(self.request.user)
        context['can_delete'] = self.object.can_delete(self.request.user)
        return context


@method_decorator(login_required, name='dispatch')
class AllegatoDeleteView(DeleteView):
    """View per eliminazione allegato"""
    
    model = Allegato
    template_name = 'core/allegati/allegato_modal_delete.html'
    
    def get_object(self):
        allegato = super().get_object()
        check_allegato_permission(self.request.user, allegato, 'delete')
        return allegato
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_object'] = self.object.content_object
        return context
    
    def delete(self, request, *args, **kwargs):
        """Override delete per gestire AJAX"""
        self.object = self.get_object()
        titolo = self.object.titolo
        
        # Elimina allegato
        self.object.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Allegato "{titolo}" eliminato con successo'
            })
        else:
            messages.success(request, f'Allegato "{titolo}" eliminato')
            return HttpResponseRedirect(self.get_success_url())
    
    def get_success_url(self):
        if hasattr(self.object.content_object, 'get_absolute_url'):
            return self.object.content_object.get_absolute_url()
        return reverse('core:dashboard')


# =============================================================================
# FILE HANDLING VIEWS
# =============================================================================

@login_required
def allegato_download(request, pk):
    """
    Download file allegato con controllo permessi.
    
    Args:
        pk: ID allegato
        
    Returns:
        FileResponse: Response con file da scaricare
    """
    allegato = get_object_or_404(Allegato, pk=pk)
    
    # Controllo permessi
    check_allegato_permission(request.user, allegato, 'view')
    
    # Verifica file esistente
    if not allegato.file:
        raise Http404("File non presente")
    
    if not os.path.exists(allegato.file.path):
        raise Http404("File non trovato sul server")
    
    # Determina MIME type
    mime_type = allegato.mime_type
    if not mime_type:
        mime_type, _ = mimetypes.guess_type(allegato.file.path)
        if not mime_type:
            mime_type = 'application/octet-stream'
    
    # Genera response
    response = FileResponse(
        open(allegato.file.path, 'rb'),
        content_type=mime_type,
        as_attachment=True,
        filename=allegato.nome_file
    )
    
    # Headers aggiuntivi
    response['Content-Length'] = allegato.dimensione_file or os.path.getsize(allegato.file.path)
    response['Content-Disposition'] = f'attachment; filename="{allegato.nome_file}"'
    
    return response


@login_required
def allegato_preview(request, pk):
    """
    Preview allegato (per immagini e PDF).
    
    Args:
        pk: ID allegato
        
    Returns:
        HttpResponse: Response con contenuto file per preview
    """
    allegato = get_object_or_404(Allegato, pk=pk)
    
    # Controllo permessi
    check_allegato_permission(request.user, allegato, 'view')
    
    # Verifica supporto preview
    if not allegato.has_preview:
        return JsonResponse({'error': 'Preview non supportata per questo tipo di file'})
    
    if not allegato.file or not os.path.exists(allegato.file.path):
        raise Http404("File non trovato")
    
    # MIME type
    mime_type = allegato.mime_type or mimetypes.guess_type(allegato.file.path)[0]
    
    # Response con file per preview
    response = HttpResponse(content_type=mime_type)
    
    with open(allegato.file.path, 'rb') as f:
        response.write(f.read())
    
    response['Content-Length'] = allegato.dimensione_file or os.path.getsize(allegato.file.path)
    
    return response


# =============================================================================
# API VIEWS
# =============================================================================

@login_required
@require_http_methods(["GET"])
def allegati_list_api(request):
    """
    API per lista allegati di un oggetto.
    
    Query params:
        - ct: content_type_id
        - oid: object_id
        - tipo: filtro tipo allegato
        - limit: numero risultati (default: 10)
    """
    content_type_id = request.GET.get('ct')
    object_id = request.GET.get('oid')
    
    if not content_type_id or not object_id:
        return JsonResponse({'error': 'Parametri ct e oid richiesti'}, status=400)
    
    try:
        parent_object = get_parent_object(content_type_id, object_id)
    except Http404:
        return JsonResponse({'error': 'Oggetto non trovato'}, status=404)
    
    # QuerySet base
    allegati = parent_object.get_allegati().attivi()
    
    # Filtri
    tipo_filter = request.GET.get('tipo')
    if tipo_filter:
        allegati = allegati.per_tipo(tipo_filter)
    
    # Limit
    limit = int(request.GET.get('limit', 10))
    allegati = allegati[:limit]
    
    # Serializza risultati
    data = []
    for allegato in allegati:
        data.append({
            'id': allegato.pk,
            'titolo': allegato.titolo,
            'tipo': allegato.get_tipo_allegato_display(),
            'tipo_code': allegato.tipo_allegato,
            'icona': allegato.icona_tipo,
            'has_file': bool(allegato.file),
            'dimensione': allegato.dimensione_leggibile if allegato.file else None,
            'url_download': reverse('core:allegato_download', args=[allegato.pk]) if allegato.file else None,
            'url_preview': reverse('core:allegato_preview', args=[allegato.pk]) if allegato.has_preview else None,
            'url_detail': reverse('core:allegato_detail', args=[allegato.pk]),
            'creato_il': allegato.creato_il.isoformat(),
            'creato_da': allegato.creato_da.get_full_name() if allegato.creato_da else None,
            'is_scaduto': allegato.is_scaduto,
            'giorni_scadenza': allegato.giorni_scadenza,
        })
    
    return JsonResponse({
        'success': True,
        'count': len(data),
        'allegati': data
    })


@login_required
@require_POST
def allegato_quick_add(request):
    """
    API per aggiunta rapida allegato (per widget sidebar).
    
    POST data:
        - titolo
        - tipo_allegato
        - file o url_esterno
        - content_type_id
        - object_id
    """
    content_type_id = request.POST.get('content_type_id')
    object_id = request.POST.get('object_id')
    
    if not content_type_id or not object_id:
        return JsonResponse({'error': 'Parametri content_type_id e object_id richiesti'}, status=400)
    
    # Valida parent object
    try:
        parent_object = get_parent_object(content_type_id, object_id)
    except Http404:
        return JsonResponse({'error': 'Oggetto parent non trovato'}, status=404)
    
    # Crea form
    form = AllegatoQuickForm(
        request.POST, 
        request.FILES,
        content_type_id=content_type_id,
        object_id=object_id,
        user=request.user
    )
    
    if form.is_valid():
        allegato = form.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Allegato "{allegato.titolo}" aggiunto',
            'allegato': {
                'id': allegato.pk,
                'titolo': allegato.titolo,
                'tipo_display': allegato.get_tipo_allegato_display(),
                'icona': allegato.icona_tipo
            }
        })
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)


@login_required 
@require_POST
def allegato_toggle_stato(request, pk):
    """
    Toggle stato allegato (attivo/archiviato).
    
    Args:
        pk: ID allegato
    """
    allegato = get_object_or_404(Allegato, pk=pk)
    check_allegato_permission(request.user, allegato, 'edit')
    
    # Toggle stato
    nuovo_stato = 'archiviato' if allegato.stato == 'attivo' else 'attivo'
    allegato.stato = nuovo_stato
    allegato.modificato_da = request.user
    allegato.save(update_fields=['stato', 'modificato_da', 'modificato_il'])
    
    return JsonResponse({
        'success': True,
        'nuovo_stato': nuovo_stato,
        'message': f'Allegato {nuovo_stato}'
    })


# =============================================================================
# TEMPLATE TAG HELPERS
# =============================================================================

@login_required
def allegati_widget_content(request):
    """
    Genera contenuto HTML per widget allegati.
    
    Query params:
        - ct: content_type_id
        - oid: object_id
        - widget_type: tipo widget ('sidebar', 'full', 'compact')
    """
    content_type_id = request.GET.get('ct')
    object_id = request.GET.get('oid')
    widget_type = request.GET.get('widget_type', 'sidebar')
    
    if not content_type_id or not object_id:
        return JsonResponse({'error': 'Parametri mancanti'}, status=400)
    
    try:
        parent_object = get_parent_object(content_type_id, object_id)
    except Http404:
        return JsonResponse({'error': 'Oggetto non trovato'}, status=404)
    
    # Template mapping
    template_map = {
        'sidebar': 'core/allegati/widgets/sidebar_widget.html',
        'full': 'core/allegati/widgets/full_widget.html',
        'compact': 'core/allegati/widgets/compact_widget.html',
    }
    
    template_name = template_map.get(widget_type, template_map['sidebar'])
    
    # Context
    context = {
        'object': parent_object,
        'allegati': parent_object.get_allegati().attivi()[:10],
        'allegati_count': parent_object.allegati_count,
        'content_type_id': content_type_id,
        'object_id': object_id,
        'can_add': True,  # TODO: controllo permessi
        'can_edit': True,  # TODO: controllo permessi
    }
    
    html = render_to_string(template_name, context, request=request)
    
    return JsonResponse({
        'success': True,
        'html': html,
        'count': context['allegati_count']
    })


# =============================================================================
# BULK OPERATIONS
# =============================================================================

@login_required
@require_POST 
def allegati_bulk_action(request):
    """
    Azioni bulk su allegati selezionati.
    
    POST data:
        - action: tipo azione
        - allegati_ids: lista ID allegati (JSON)
        - parametri aggiuntivi in base all'azione
    """
    try:
        action = request.POST.get('action')
        allegati_ids = json.loads(request.POST.get('allegati_ids', '[]'))
        
        if not action or not allegati_ids:
            return JsonResponse({'error': 'Azione e allegati richiesti'}, status=400)
        
        # Ottieni allegati
        allegati = Allegato.objects.filter(pk__in=allegati_ids)
        
        # Verifica permessi su tutti gli allegati
        for allegato in allegati:
            if action in ['elimina']:
                check_allegato_permission(request.user, allegato, 'delete')
            else:
                check_allegato_permission(request.user, allegato, 'edit')
        
        # Esegui azione
        count = 0
        
        if action == 'archivia':
            count = allegati.update(stato='archiviato', modificato_da=request.user)
        
        elif action == 'attiva':
            count = allegati.update(stato='attivo', modificato_da=request.user)
        
        elif action == 'elimina':
            count = allegati.count()
            allegati.delete()
        
        elif action == 'cambia_tipo':
            nuovo_tipo = request.POST.get('nuovo_tipo')
            if nuovo_tipo:
                count = allegati.update(tipo_allegato=nuovo_tipo, modificato_da=request.user)
        
        elif action == 'aggiungi_tag':
            tag_da_aggiungere = request.POST.get('tag_da_aggiungere')
            if tag_da_aggiungere:
                for allegato in allegati:
                    tags_attuali = allegato.get_tag_list()
                    if tag_da_aggiungere not in tags_attuali:
                        tags_attuali.append(tag_da_aggiungere)
                        allegato.set_tags(tags_attuali)
                        allegato.modificato_da = request.user
                        allegato.save(update_fields=['tags', 'modificato_da', 'modificato_il'])
                        count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Azione "{action}" eseguita su {count} allegati',
            'count': count
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# =============================================================================
# STATS AND REPORTS
# =============================================================================

@login_required
def allegati_stats(request):
    """
    Statistiche allegati per dashboard.
    
    Query params:
        - giorni: periodo statistiche (default: 30)
    """
    giorni = int(request.GET.get('giorni', 30))
    
    # Statistiche generali
    from django.utils import timezone
    from datetime import timedelta
    
    data_limite = timezone.now() - timedelta(days=giorni)
    
    stats = {
        'totali': {
            'allegati': Allegato.objects.count(),
            'allegati_attivi': Allegato.objects.filter(stato='attivo').count(),
            'allegati_recenti': Allegato.objects.filter(creato_il__gte=data_limite).count(),
            'allegati_scaduti': Allegato.objects.scaduti().count(),
            'allegati_in_scadenza': Allegato.objects.in_scadenza(7).count(),
        },
        'per_tipo': list(
            Allegato.objects.values('tipo_allegato')
            .annotate(count=Count('pk'))
            .order_by('-count')[:10]
        ),
        'per_utente': list(
            Allegato.objects.filter(creato_il__gte=data_limite)
            .values('creato_da__username', 'creato_da__first_name', 'creato_da__last_name')
            .annotate(count=Count('pk'))
            .order_by('-count')[:10]
        )
    }
    
    return JsonResponse({
        'success': True,
        'stats': stats,
        'periodo_giorni': giorni
    })