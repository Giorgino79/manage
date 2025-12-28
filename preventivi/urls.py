"""
PREVENTIVI URLs - Configurazione URL patterns
============================================

URL patterns per:
- Dashboard e overview
- CRUD richieste preventivo
- Gestione e valutazione preventivi
- Workflow approvazione
"""

from django.urls import path
from . import views

app_name = 'preventivi'

urlpatterns = [
    # =====================================================
    # DASHBOARD & OVERVIEW
    # =====================================================
    
    # Dashboard principale preventivi
    path('', views.dashboard, name='dashboard'),
    
    # =====================================================
    # RICHIESTE PREVENTIVO
    # =====================================================
    
    # Lista richieste con filtri
    path('richieste/', views.richieste_list, name='richieste_list'),
    
    # Dettaglio richiesta
    path('richieste/<int:pk>/', views.richiesta_detail, name='richiesta_detail'),
    
    # Creazione nuova richiesta (wizard multi-step)
    path('richieste/nuovo/', views.richiesta_create, name='richiesta_create'),
    
    # Step fornitori per richiesta
    path('richieste/<int:pk>/fornitori/', views.richiesta_select_fornitori, name='richiesta_select_fornitori'),
    
    # Approvazione richiesta
    path('richieste/<int:pk>/approva/', views.richiesta_approva, name='richiesta_approva'),
    
    # =====================================================
    # WORKFLOW PREVENTIVI - 3 STEP
    # =====================================================
    
    # Step 1: Invio email ai fornitori (operatore)
    path('richieste/<int:pk>/step1-invia/', views.step1_invia_fornitori, name='step1_invia_fornitori'),
    
    # Step 2: Raccolta preventivi ricevuti (operatore)
    path('richieste/<int:pk>/step2-raccolta/', views.step2_raccolta, name='step2_raccolta'),
    
    # Step 3: Valutazione e scelta (amministratore)  
    path('richieste/<int:pk>/step3-valutazione/', views.step3_valutazione, name='step3_valutazione'),
    
    # =====================================================
    # PREVENTIVI (Offerte ricevute)
    # =====================================================
    
    # Inserimento preventivo ricevuto
    path('richieste/<int:richiesta_pk>/preventivo/nuovo/', views.preventivo_create, name='preventivo_create'),
    
    # Valutazione preventivo
    path('preventivi/<int:pk>/valuta/', views.preventivo_valuta, name='preventivo_valuta'),
    
    # =====================================================
    # API ENDPOINTS (per chiamate AJAX)
    # =====================================================
    
    # Gestione parametri preventivo (AJAX)
    path('preventivi/<int:pk>/parametri/', views.preventivo_parametri_get, name='preventivo_parametri_get'),
    path('preventivi/<int:pk>/parametri/save/', views.preventivo_parametri_save, name='preventivo_parametri_save'),

    # Ricerca fornitori (AJAX)
    path('api/search-fornitori/', views.search_fornitori_ajax, name='search_fornitori_ajax'),

    # TODO: Implementare altri API endpoints per:
    # - Aggiornamento stato email
    # - Upload allegati via AJAX
    # - Calcolo automatico punteggi
    # - Export dati in Excel/PDF
]