"""
DIPENDENTI TEMPLATE TAGS - Template tags per gestione dipendenti
================================================================

Template tags e filters personalizzati per il modulo dipendenti.
Include utilities per permessi, formattazione e controlli di accesso.

Usage:
    {% load dipendenti_tags %}
    {% if user|ha_permesso:"supervisore" %}...{% endif %}

Versione: 1.0
"""

from django import template

register = template.Library()


@register.filter
def ha_permesso(user, permesso_richiesto):
    """
    Filter per verificare se un utente ha un determinato permesso.
    
    Usage:
        {% if user|ha_permesso:"supervisore" %}
            Contenuto per supervisori
        {% endif %}
        
    Args:
        user: Oggetto utente (Dipendente)
        permesso_richiesto: Livello di permesso richiesto
        
    Returns:
        bool: True se l'utente ha il permesso richiesto
    """
    if not user or not hasattr(user, 'ha_permesso'):
        return False
    
    try:
        return user.ha_permesso(permesso_richiesto)
    except (AttributeError, TypeError):
        return False


@register.filter  
def is_supervisore(user):
    """
    Filter per verificare se un utente è supervisore.
    
    Usage:
        {% if user|is_supervisore %}...{% endif %}
        
    Returns:
        bool: True se l'utente è supervisore o superiore
    """
    return ha_permesso(user, 'supervisore')


@register.filter
def is_amministratore(user):
    """
    Filter per verificare se un utente è amministratore.
    
    Usage:
        {% if user|is_amministratore %}...{% endif %}
        
    Returns:
        bool: True se l'utente è amministratore
    """
    return ha_permesso(user, 'amministratore')


@register.filter
def livello_display(user):
    """
    Filter per ottenere il display name del livello utente.
    
    Usage:
        {{ user|livello_display }}
        
    Returns:
        str: Nome display del livello
    """
    if not user or not hasattr(user, 'get_livello_display'):
        return 'N/A'
    
    try:
        return user.get_livello_display()
    except (AttributeError, TypeError):
        return 'N/A'


@register.filter
def stato_display(user):
    """
    Filter per ottenere il display name dello stato utente.
    
    Usage:
        {{ user|stato_display }}
        
    Returns:
        str: Nome display dello stato
    """
    if not user or not hasattr(user, 'get_stato_display'):
        return 'N/A'
    
    try:
        return user.get_stato_display()
    except (AttributeError, TypeError):
        return 'N/A'


@register.filter
def stato_color(user):
    """
    Filter per ottenere il colore Bootstrap basato sullo stato utente.
    
    Usage:
        <span class="badge bg-{{ user|stato_color }}">{{ user|stato_display }}</span>
        
    Returns:
        str: Classe colore Bootstrap
    """
    if not user or not hasattr(user, 'stato'):
        return 'secondary'
    
    color_map = {
        'attivo': 'success',
        'sospeso': 'warning', 
        'dimesso': 'danger',
        'prova': 'info'
    }
    
    return color_map.get(user.stato, 'secondary')


@register.filter
def livello_color(user):
    """
    Filter per ottenere il colore Bootstrap basato sul livello utente.
    
    Usage:
        <span class="badge bg-{{ user|livello_color }}">{{ user|livello_display }}</span>
        
    Returns:
        str: Classe colore Bootstrap
    """
    if not user or not hasattr(user, 'livello'):
        return 'secondary'
    
    color_map = {
        'amministratore': 'danger',
        'supervisore': 'warning',
        'contabile': 'info', 
        'operativo': 'primary',
        'magazziniere': 'success',
        'rappresentante': 'dark',
        'autista': 'secondary'
    }
    
    return color_map.get(user.livello, 'secondary')


@register.simple_tag
def user_full_name(user):
    """
    Tag per ottenere il nome completo dell'utente.
    
    Usage:
        {% user_full_name dipendente %}
        
    Returns:
        str: Nome completo o username se non disponibile
    """
    if not user:
        return 'N/A'
    
    if hasattr(user, 'get_full_name'):
        full_name = user.get_full_name()
        if full_name.strip():
            return full_name
    
    return getattr(user, 'username', 'N/A')


@register.inclusion_tag('dipendenti/includes/user_badge.html')
def user_badge(user, show_level=True, show_status=False):
    """
    Tag di inclusione per badge utente completo.
    
    Usage:
        {% user_badge dipendente show_level=True show_status=True %}
        
    Args:
        user: Oggetto utente
        show_level: Mostra livello
        show_status: Mostra stato
        
    Returns:
        Template rendered con badge utente
    """
    return {
        'user': user,
        'show_level': show_level,
        'show_status': show_status,
        'full_name': user_full_name(user),
        'level_color': livello_color(user),
        'status_color': stato_color(user),
    }


@register.filter
def can_edit_dipendente(current_user, target_user):
    """
    Filter per verificare se l'utente corrente può modificare un altro dipendente.
    
    Usage:
        {% if request.user|can_edit_dipendente:dipendente %}...{% endif %}
        
    Returns:
        bool: True se può modificare
    """
    if not current_user or not target_user:
        return False
    
    # Amministratori possono modificare tutti
    if hasattr(current_user, 'ha_permesso') and current_user.ha_permesso('amministratore'):
        return True
    
    # Supervisori possono modificare subordinati
    if hasattr(current_user, 'ha_permesso') and current_user.ha_permesso('supervisore'):
        # Non può modificare amministratori o altri supervisori
        if hasattr(target_user, 'livello'):
            return target_user.livello not in ['amministratore', 'supervisore']
    
    # Gli utenti possono modificare solo se stessi (in alcuni casi)
    return current_user.pk == target_user.pk


@register.filter
def format_telefono(telefono):
    """
    Filter per formattare numeri di telefono italiani.
    
    Usage:
        {{ dipendente.telefono|format_telefono }}
        
    Returns:
        str: Numero formattato
    """
    if not telefono:
        return 'N/A'
    
    # Rimuovi spazi e caratteri non numerici
    cleaned = ''.join(filter(str.isdigit, str(telefono)))
    
    if not cleaned:
        return telefono
    
    # Formato per cellulari italiani (10 cifre)
    if len(cleaned) == 10 and cleaned.startswith('3'):
        return f"{cleaned[:3]} {cleaned[3:6]} {cleaned[6:]}"
    
    # Formato per fissi italiani con prefisso (9-11 cifre)
    elif 9 <= len(cleaned) <= 11:
        if len(cleaned) == 9:
            return f"{cleaned[:2]} {cleaned[2:5]} {cleaned[5:]}"
        elif len(cleaned) == 10:
            return f"{cleaned[:3]} {cleaned[3:6]} {cleaned[6:]}"
        else:  # 11 cifre
            return f"{cleaned[:4]} {cleaned[4:7]} {cleaned[7:]}"
    
    # Ritorna il numero originale se non matcha i pattern
    return telefono