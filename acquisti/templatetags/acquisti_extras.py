"""
Template tags per app acquisti
"""

from django import template
from django.contrib.contenttypes.models import ContentType

register = template.Library()


@register.filter
def get_content_type_id(obj):
    """Ottiene il content_type_id di un oggetto"""
    if obj:
        content_type = ContentType.objects.get_for_model(obj.__class__)
        return content_type.id
    return None


@register.filter
def has_allegati(obj):
    """Verifica se un oggetto ha allegati"""
    if hasattr(obj, 'allegati'):
        return obj.allegati.filter(stato='attivo').exists()
    return False


@register.filter
def count_allegati(obj):
    """Conta gli allegati attivi di un oggetto"""
    if hasattr(obj, 'allegati'):
        return obj.allegati.filter(stato='attivo').count()
    return 0