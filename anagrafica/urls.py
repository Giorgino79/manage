"""
ANAGRAFICA URLS - URL configuration per anagrafica
=================================================

URL patterns per la gestione anagrafica (senza rappresentanti):
- Dashboard anagrafica
- CRUD Clienti  
- CRUD Fornitori
- API e utility

NOTA: Tutti gli URL relativi ai rappresentanti sono stati rimossi
"""

from django.urls import path
from . import views

app_name = 'anagrafica'

urlpatterns = [
    # Dashboard
    path('', views.dashboard_anagrafica, name='dashboard'),
    
    # ================== CLIENTI ==================
    path('clienti/', views.ClienteListView.as_view(), name='elenco_clienti'),
    path('clienti/nuovo/', views.ClienteCreateView.as_view(), name='nuovo_cliente'),
    path('clienti/<int:pk>/', views.ClienteDetailView.as_view(), name='dettaglio_cliente'),
    path('clienti/<int:pk>/modifica/', views.ClienteUpdateView.as_view(), name='modifica_cliente'),
    path('clienti/<int:pk>/elimina/', views.ClienteDeleteView.as_view(), name='elimina_cliente'),
    
    # ================== FORNITORI ==================
    path('fornitori/', views.FornitoreListView.as_view(), name='elenco_fornitori'),
    path('fornitori/nuovo/', views.FornitoreCreateView.as_view(), name='nuovo_fornitore'),
    path('fornitori/<int:pk>/', views.FornitoreDetailView.as_view(), name='dettaglio_fornitore'),
    path('fornitori/<int:pk>/modifica/', views.FornitoreUpdateView.as_view(), name='modifica_fornitore'),
    path('fornitori/<int:pk>/elimina/', views.FornitoreDeleteView.as_view(), name='elimina_fornitore'),
    
    # ================== UTILITY ==================
    path('toggle/<str:tipo>/<int:pk>/', views.toggle_attivo, name='toggle_attivo'),
    path('export/', views.export_anagrafica, name='export_anagrafica'),
    
    # ================== REPORT ==================
    path('report/crediti/', views.report_crediti_clienti, name='report_crediti'),
    
    # ================== API ==================
    path('api/search/', views.api_search_anagrafica, name='api_search'),
    path('api/credito/', views.api_verifica_limite_credito, name='api_verifica_credito'),
    path('api/stats/', views.api_dashboard_stats, name='api_stats'),
]