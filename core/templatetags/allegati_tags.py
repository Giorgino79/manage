"""
ALLEGATI TEMPLATE TAGS - Template tags per sistema allegati
==========================================================

Template tags riutilizzabili per il sistema allegati universale.
Fornisce widget, contatori e utility per visualizzare allegati
in qualsiasi template del sistema.

Usage:
    {% load allegati_tags %}
    {% allegati_widget oggetto %}
    {% allegati_count oggetto %}
    {% allegati_section oggetto %}

Versione: 1.0
"""

from django import template
from django.contrib.contenttypes.models import ContentType
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.conf import settings
import json
import os

from ..models.allegati import Allegato

register = template.Library()


# =============================================================================
# INCLUSION TAGS - Widget Completi
# =============================================================================

@register.inclusion_tag('core/allegati/widgets/allegati_widget.html', takes_context=True)
def allegati_widget(context, obj, **kwargs):
    """
    Widget principale allegati per sidebar/sezioni.
    
    Usage:
        {% allegati_widget dipendente %}
        {% allegati_widget automezzo can_add=True can_edit=False %}
        {% allegati_widget ordine types_filter="doc_,email_" %}
    
    Args:
        obj: Oggetto per cui mostrare allegati
        can_add: Può aggiungere allegati (default: True)
        can_edit: Può modificare allegati (default: True)
        can_delete: Può eliminare allegati (default: True)
        types_filter: Filtro tipi allegati (es: "doc_,foto_")
        limit: Numero max allegati da mostrare (default: 10)
        show_add_button: Mostra pulsante aggiungi (default: True)
        widget_type: Tipo widget ('sidebar', 'compact', 'full')
        
    Returns:
        Template rendered con context allegati
    """
    
    # Parametri con default
    can_add = kwargs.get('can_add', True)
    can_edit = kwargs.get('can_edit', True) 
    can_delete = kwargs.get('can_delete', True)
    types_filter = kwargs.get('types_filter', None)
    limit = kwargs.get('limit', 10)
    show_add_button = kwargs.get('show_add_button', True)
    widget_type = kwargs.get('widget_type', 'sidebar')
    
    # Ottieni allegati
    if hasattr(obj, 'get_allegati'):
        allegati = obj.get_allegati().attivi()
        
        # Applica filtro tipi se specificato
        if types_filter:
            type_list = [t.strip() for t in types_filter.split(',')]
            q_objects = []
            for type_filter in type_list:
                if type_filter.endswith('_'):
                    # Wildcard filter (es: "doc_" per tutti i documenti)
                    from django.db.models import Q
                    q_objects.append(Q(tipo_allegato__startswith=type_filter))
                else:
                    # Exact filter
                    from django.db.models import Q
                    q_objects.append(Q(tipo_allegato=type_filter))
            
            if q_objects:
                from django.db.models import Q
                combined_q = q_objects[0]
                for q in q_objects[1:]:
                    combined_q |= q
                allegati = allegati.filter(combined_q)
        
        # Applica limit
        allegati_list = allegati[:limit]
        allegati_count = allegati.count()
        
    else:
        allegati_list = []
        allegati_count = 0
    
    # Content Type info per URL
    content_type = ContentType.objects.get_for_model(obj.__class__)
    
    # Context per template
    widget_context = {
        'object': obj,
        'allegati': allegati_list,
        'allegati_count': allegati_count,
        'content_type_id': content_type.pk,
        'object_id': obj.pk,
        'can_add': can_add,
        'can_edit': can_edit,
        'can_delete': can_delete,
        'show_add_button': show_add_button,
        'widget_type': widget_type,
        'has_more': allegati_count > limit,
        'types_filter': types_filter,
        'request': context.get('request'),
        'user': context.get('user'),
    }
    
    return widget_context


@register.inclusion_tag('core/allegati/widgets/allegati_section.html', takes_context=True)
def allegati_section(context, obj, **kwargs):
    """
    Sezione completa allegati per pagine dettaglio.
    
    Usage:
        {% allegati_section dipendente %}
        {% allegati_section automezzo show_grid=True columns=3 %}
        {% allegati_section ordine show_stats=True paginate=True %}
    
    Args:
        obj: Oggetto per cui mostrare allegati
        show_grid: Mostra in griglia (default: False = lista)
        columns: Numero colonne griglia (default: 2)
        paginate: Attiva paginazione (default: False) 
        per_page: Elementi per pagina (default: 20)
        show_stats: Mostra statistiche (default: True)
        show_filters: Mostra filtri (default: True)
        show_search: Mostra ricerca (default: True)
        
    Returns:
        Template rendered con sezione completa
    """
    
    # Parametri
    show_grid = kwargs.get('show_grid', False)
    columns = kwargs.get('columns', 2)
    paginate = kwargs.get('paginate', False)
    per_page = kwargs.get('per_page', 20)
    show_stats = kwargs.get('show_stats', True)
    show_filters = kwargs.get('show_filters', True)
    show_search = kwargs.get('show_search', True)
    
    # Allegati
    if hasattr(obj, 'get_allegati'):
        allegati = obj.get_allegati().attivi()
        
        # Statistiche
        if show_stats:
            stats = obj.get_allegati_stats() if hasattr(obj, 'get_allegati_stats') else {}
        else:
            stats = {}
        
        # Paginazione (semplificata per ora)
        if paginate:
            allegati_list = allegati[:per_page]
        else:
            allegati_list = allegati
            
    else:
        allegati_list = []
        stats = {}
    
    # Content Type
    content_type = ContentType.objects.get_for_model(obj.__class__)
    
    return {
        'object': obj,
        'allegati': allegati_list,
        'stats': stats,
        'content_type_id': content_type.pk,
        'object_id': obj.pk,
        'show_grid': show_grid,
        'columns': columns,
        'show_stats': show_stats,
        'show_filters': show_filters,
        'show_search': show_search,
        'request': context.get('request'),
        'user': context.get('user'),
    }


@register.inclusion_tag('core/allegati/widgets/allegati_list.html')
def allegati_list(obj, **kwargs):
    """
    Lista semplice allegati.
    
    Usage:
        {% allegati_list dipendente %}
        {% allegati_list automezzo limit=5 types="doc_" %}
    """
    
    limit = kwargs.get('limit', None)
    types = kwargs.get('types', None)
    
    if hasattr(obj, 'get_allegati'):
        allegati = obj.get_allegati().attivi()
        
        if types:
            # Implementa filtro tipi se necessario
            pass
        
        if limit:
            allegati = allegati[:limit]
    else:
        allegati = []
    
    return {
        'object': obj,
        'allegati': allegati,
    }


# =============================================================================
# SIMPLE TAGS - Dati e Utility
# =============================================================================

@register.simple_tag
def allegati_count(obj, tipo=None):
    """
    Conta allegati di un oggetto.
    
    Usage:
        {% allegati_count dipendente %}
        {% allegati_count automezzo "doc_" %}
        
    Args:
        obj: Oggetto
        tipo: Filtro tipo opzionale (supporta wildcard con _)
        
    Returns:
        int: Numero allegati
    """
    if not hasattr(obj, 'get_allegati'):
        return 0
    
    allegati = obj.get_allegati().attivi()
    
    if tipo:
        if tipo.endswith('_'):
            # Wildcard
            allegati = allegati.filter(tipo_allegato__startswith=tipo)
        else:
            # Exact match
            allegati = allegati.filter(tipo_allegato=tipo)
    
    return allegati.count()


@register.simple_tag
def allegati_stats(obj):
    """
    Statistiche allegati oggetto.
    
    Usage:
        {% allegati_stats dipendente as stats %}
        Totale: {{ stats.totale }}
        Documenti: {{ stats.per_categoria.documenti }}
        
    Returns:
        dict: Statistiche complete
    """
    if hasattr(obj, 'get_allegati_stats'):
        return obj.get_allegati_stats()
    return {}


@register.simple_tag
def content_type_id(obj):
    """
    Ottieni Content Type ID di un oggetto.
    
    Usage:
        {% content_type_id dipendente as ct_id %}
        
    Returns:
        int: Content Type ID
    """
    content_type = ContentType.objects.get_for_model(obj.__class__)
    return content_type.pk


@register.simple_tag
def allegato_icon(tipo_allegato):
    """
    Icona FontAwesome per tipo allegato.
    
    Usage:
        {% allegato_icon "doc_contratto" as icon %}
        <i class="{{ icon }}"></i>
        
    Returns:
        str: Classe CSS icona
    """
    icons_map = {
        # Documenti
        'doc_contratto': 'fas fa-file-contract',
        'doc_fattura': 'fas fa-file-invoice',
        'doc_preventivo': 'fas fa-file-alt', 
        'doc_ordine': 'fas fa-shopping-cart',
        'doc_bolla': 'fas fa-truck',
        'doc_certificato': 'fas fa-certificate',
        'doc_libretto': 'fas fa-book',
        'doc_patente': 'fas fa-id-card',
        'doc_carta_identita': 'fas fa-address-card',
        'doc_codice_fiscale': 'fas fa-hashtag',
        
        # Comunicazioni
        'email_inviata': 'fas fa-paper-plane',
        'email_ricevuta': 'fas fa-envelope',
        'sms_inviato': 'fas fa-sms',
        'chiamata': 'fas fa-phone',
        'fax': 'fas fa-fax',
        
        # Media
        'foto_documento': 'fas fa-camera',
        'foto_generale': 'fas fa-image',
        'video': 'fas fa-video',
        'audio': 'fas fa-volume-up',
        'screenshot': 'fas fa-desktop',
        
        # Note
        'nota_interna': 'fas fa-sticky-note',
        'nota_cliente': 'fas fa-comment',
        'promemoria': 'fas fa-bell',
        'appunto': 'fas fa-edit',
        
        # Altri
        'link_esterno': 'fas fa-external-link-alt',
        'altro': 'fas fa-paperclip',
    }
    
    return icons_map.get(tipo_allegato, 'fas fa-paperclip')


@register.simple_tag
def allegato_color(tipo_allegato):
    """
    Colore Bootstrap per tipo allegato.
    
    Usage:
        {% allegato_color "doc_contratto" as color %}
        <span class="badge bg-{{ color }}">Documento</span>
        
    Returns:
        str: Classe colore Bootstrap
    """
    colors_map = {
        'doc_': 'primary',      # Documenti - blu
        'email_': 'info',       # Email - azzurro
        'foto_': 'success',     # Foto - verde
        'video': 'dark',        # Video - scuro
        'audio': 'dark',        # Audio - scuro
        'nota_': 'warning',     # Note - giallo
        'promemoria': 'danger', # Promemoria - rosso
        'link_esterno': 'secondary', # Link - grigio
    }
    
    for prefix, color in colors_map.items():
        if tipo_allegato.startswith(prefix):
            return color
    
    return 'secondary'  # Default


# =============================================================================
# FILTER TAGS - Trasformazione Dati
# =============================================================================

@register.filter
def has_allegati(obj):
    """
    Verifica se oggetto ha allegati.
    
    Usage:
        {% if dipendente|has_allegati %}
            Ha allegati!
        {% endif %}
        
    Returns:
        bool: True se ha allegati
    """
    return hasattr(obj, 'ha_allegati') and obj.ha_allegati


@register.filter
def allegati_by_type(obj, tipo):
    """
    Filtra allegati per tipo.
    
    Usage:
        {% for doc in dipendente|allegati_by_type:"doc_" %}
            {{ doc.titolo }}
        {% endfor %}
        
    Returns:
        QuerySet: Allegati filtrati
    """
    if not hasattr(obj, 'get_allegati_by_type'):
        return []
    return obj.get_allegati_by_type(tipo)


@register.filter
def filesize_human(size):
    """
    Formatta dimensione file in formato leggibile.
    
    Usage:
        {{ allegato.dimensione_file|filesize_human }}
        
    Returns:
        str: Dimensione formattata (es: "2.5 MB")
    """
    if not size:
        return "N/A"
    
    try:
        size = float(size)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    except (ValueError, TypeError):
        return "N/A"


@register.filter
def truncate_filename(filename, length=30):
    """
    Tronca nome file mantenendo estensione.
    
    Usage:
        {{ allegato.nome_file|truncate_filename:20 }}
        
    Returns:
        str: Nome file troncato
    """
    if not filename or len(filename) <= length:
        return filename
    
    name, ext = os.path.splitext(filename)
    if len(ext) > length - 3:
        return filename[:length] + '...'
    
    max_name_length = length - len(ext) - 3
    return name[:max_name_length] + '...' + ext


@register.filter
def get_class_name(obj):
    """
    Ottieni nome della classe di un oggetto.
    
    Usage:
        {{ object|get_class_name }}
        
    Returns:
        str: Nome classe
    """
    return obj.__class__.__name__ if obj else ""


# =============================================================================
# URL GENERATION TAGS
# =============================================================================

@register.simple_tag
def allegato_add_url(obj):
    """
    URL per aggiungere allegato.
    
    Usage:
        {% allegato_add_url dipendente as add_url %}
        <a href="{{ add_url }}">Aggiungi</a>
        
    Returns:
        str: URL completo
    """
    content_type = ContentType.objects.get_for_model(obj.__class__)
    return f"{reverse('core:allegato_create')}?ct={content_type.pk}&oid={obj.pk}"


@register.simple_tag
def allegato_api_url(obj, endpoint='list'):
    """
    URL API allegati.
    
    Usage:
        {% allegato_api_url dipendente "list" as api_url %}
        
    Returns:
        str: URL API
    """
    content_type = ContentType.objects.get_for_model(obj.__class__)
    
    url_map = {
        'list': 'core:allegati_list_api',
        'quick_add': 'core:allegato_quick_add',
        'widget': 'core:allegati_widget_content',
        'stats': 'core:allegati_stats',
    }
    
    if endpoint in url_map:
        base_url = reverse(url_map[endpoint])
        return f"{base_url}?ct={content_type.pk}&oid={obj.pk}"
    
    return ''


# =============================================================================
# JAVASCRIPT HELPERS
# =============================================================================

@register.simple_tag
def allegati_js_config(obj):
    """
    Configurazione JavaScript per allegati.
    
    Usage:
        {% allegati_js_config dipendente as js_config %}
        <script>
            var allegatiConfig = {{ js_config|safe }};
        </script>
        
    Returns:
        str: JSON configuration
    """
    content_type = ContentType.objects.get_for_model(obj.__class__)
    
    config = {
        'objectId': obj.pk,
        'contentTypeId': content_type.pk,
        'urls': {
            'list': reverse('core:allegati_list_api'),
            'create': reverse('core:allegato_create'),
            'quickAdd': reverse('core:allegato_quick_add'),
            'widget': reverse('core:allegati_widget_content'),
            'stats': reverse('core:allegati_stats'),
        },
        'csrf_token': '{{ csrf_token }}',  # Sarà sostituito nel template
        'permissions': {
            'canAdd': True,  # TODO: controllo permessi reale
            'canEdit': True,
            'canDelete': True,
        }
    }
    
    return mark_safe(json.dumps(config, indent=2))


@register.inclusion_tag('core/allegati/widgets/allegati_scripts.html', takes_context=True)
def allegati_scripts(context, obj):
    """
    Include script JavaScript per allegati.
    
    Usage:
        {% allegati_scripts dipendente %}
        
    Returns:
        Template con script JavaScript
    """
    content_type = ContentType.objects.get_for_model(obj.__class__)
    
    return {
        'object': obj,
        'content_type_id': content_type.pk,
        'object_id': obj.pk,
        'request': context.get('request'),
    }


# =============================================================================
# CONDITIONAL TAGS
# =============================================================================

@register.simple_tag
def user_can_manage_allegati(user, obj):
    """
    Verifica se utente può gestire allegati dell'oggetto.
    
    Usage:
        {% user_can_manage_allegati user dipendente as can_manage %}
        {% if can_manage %}...{% endif %}
        
    Returns:
        bool: True se può gestire
    """
    # Logica permessi semplificata
    if user.is_superuser:
        return True
    
    if user.is_staff:
        return True
    
    # TODO: Implementare logica permessi specifica per modello
    return True


@register.inclusion_tag('core/allegati/widgets/allegati_badge.html')
def allegati_badge(obj, **kwargs):
    """
    Badge con contatore allegati.
    
    Usage:
        {% allegati_badge dipendente %}
        {% allegati_badge automezzo style="danger" %}
    """
    
    if hasattr(obj, 'allegati_count'):
        count = obj.allegati_count
    else:
        count = 0
    
    style = kwargs.get('style', 'primary')
    show_zero = kwargs.get('show_zero', False)
    
    return {
        'count': count,
        'style': style,
        'show_zero': show_zero,
        'show_badge': count > 0 or show_zero,
    }


# =============================================================================
# DEBUG TAGS (Development only)
# =============================================================================

@register.simple_tag
def allegati_debug_info(obj):
    """
    Informazioni debug per sviluppo.
    Solo in modalità DEBUG.
    
    Returns:
        dict: Info debug se DEBUG=True, altrimenti {}
    """
    if not getattr(settings, 'DEBUG', False):
        return {}
    
    try:
        content_type = ContentType.objects.get_for_model(obj.__class__)
        
        debug_info = {
            'model': f"{content_type.app_label}.{content_type.model}",
            'object_id': obj.pk,
            'content_type_id': content_type.pk,
            'has_mixin': hasattr(obj, 'get_allegati'),
            'methods_available': [
                method for method in dir(obj) 
                if method.startswith('get_allegati') or method.startswith('add_allegato')
            ]
        }
        
        if hasattr(obj, 'get_allegati'):
            allegati = obj.get_allegati()
            debug_info.update({
                'allegati_totali': allegati.count(),
                'allegati_attivi': allegati.attivi().count(),
                'types_presenti': list(allegati.values_list('tipo_allegato', flat=True).distinct()),
            })
        
        return debug_info
    except Exception as e:
        return {'error': str(e)}