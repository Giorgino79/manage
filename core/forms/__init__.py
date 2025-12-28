"""
CORE FORMS - Import all forms
=============================
"""

from .allegati import (
    AllegatoForm,
    AllegatoQuickForm,
    AllegatoSearchForm,
    AllegatoBulkActionForm,
)
from .chat import (
    MessaggioForm,
    PromemorialForm,
    PromemorialSearchForm,
    ChatFilterForm,
)
from .procurement import (
    SmartTargetSelectorWidget,
    ProcurementTargetField,
    ProcurementTargetForm,
    QuickTargetSearchForm,
    TargetInfoWidget,
    ProcurementTargetFormMixin,
)

__all__ = [
    # Allegati forms
    'AllegatoForm',
    'AllegatoQuickForm', 
    'AllegatoSearchForm',
    'AllegatoBulkActionForm',
    # Chat e Promemoria forms
    'MessaggioForm',
    'PromemorialForm',
    'PromemorialSearchForm',
    'ChatFilterForm',
    # Procurement forms
    'SmartTargetSelectorWidget',
    'ProcurementTargetField',
    'ProcurementTargetForm',
    'QuickTargetSearchForm',
    'TargetInfoWidget',
    'ProcurementTargetFormMixin',
]