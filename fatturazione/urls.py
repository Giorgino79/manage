"""
FATTURAZIONE URLS - URL routing per fatturazione passiva
======================================================

URL patterns per il sistema di fatturazione passiva:
- Dashboard principale
- CRUD fatture 
- Workflow actions
- AJAX endpoints
- Export functions

Adattato da AMM/fatturazione per progetto Management
"""

from django.urls import path
from . import views

app_name = 'fatturazione'

urlpatterns = [
    # Dashboard principale
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Registrazione fattura
    path('registra/', views.registra_fattura, name='registra_fattura'),
    
    # Export ordini acquisto
    path('export/ordini/form/', views.export_ordini_form, name='export_ordini_form'),
    path('export/ordini/download/', views.export_ordini, name='export_ordini'),
    
    # AJAX endpoints
    path('ajax/ordini-by-fornitore/', views.get_ordini_by_fornitore, name='get_ordini_by_fornitore'),
    
    # Export
    path('export/csv/', views.export_fatture_csv, name='export_csv'),
]