"""
ACQUISTI URLs - URL patterns per app acquisti
============================================
"""

from django.urls import path
from . import views

app_name = 'acquisti'

urlpatterns = [
    # Dashboard principale
    path('', views.dashboard, name='dashboard'),
    
    # Gestione ordini
    path('crea/', views.crea_ordine, name='crea_ordine'),
    path('dettaglio/<int:pk>/', views.dettaglio_ordine, name='dettaglio_ordine'),
    
    # AJAX endpoints
    path('ajax/segna-ricevuto/<int:pk>/', views.segna_ricevuto_ajax, name='segna_ricevuto_ajax'),
    path('ajax/aggiungi-nota/<int:pk>/', views.aggiungi_nota_ajax, name='aggiungi_nota_ajax'),
    path('ajax/fornitori-autocomplete/', views.fornitori_autocomplete, name='fornitori_autocomplete'),
]