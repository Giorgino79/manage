from django.urls import path
from . import views

app_name = 'stabilimenti'

urlpatterns = [
    # =====================================
    # STABILIMENTI BASE
    # =====================================
    
    # Lista stabilimenti con filtri di ricerca
    path('', views.stabilimenti_list, name='list'),
    # Template: stabilimenti/stabilimenti_list.html
    
    # Creazione nuovo stabilimento
    path('nuovo/', views.nuovo_stabilimento, name='nuovo'),
    # Template: stabilimenti/nuovo_stabilimento.html
    
    # Dettaglio singolo stabilimento (dashboard principale)
    path('<int:pk>/', views.dettaglio_stabilimento, name='dettaglio'),
    # Template: stabilimenti/dettaglio_stabilimento.html
    
    # Modifica stabilimento esistente
    path('<int:pk>/modifica/', views.modifica_stabilimento, name='modifica'),
    # Template: stabilimenti/modifica_stabilimento.html
    
    
    # =====================================
    # GESTIONE COSTI
    # =====================================
    
    # Lista di tutti i costi di tutti gli stabilimenti
    path('costi/', views.costi_list, name='costi_list'),
    # Template: stabilimenti/costi_list.html
    
    # ELIMINATO: Nuovo costo generico - ora tutti i costi devono avere uno stabilimento
    
    # Nuovo costo per uno stabilimento specifico
    path('<int:stabilimento_pk>/costi/nuovo/', views.nuovo_costo, name='nuovo_costo_stabilimento'),
    # Template: stabilimenti/nuovo_costo.html (stesso template)
    
    # Dettaglio di un singolo costo
    path('costi/<int:pk>/', views.dettaglio_costo, name='dettaglio_costo'),
    # Template: stabilimenti/dettaglio_costo.html
    
    # Modifica costo esistente
    path('costi/<int:pk>/modifica/', views.modifica_costo, name='modifica_costo'),
    # Template: stabilimenti/modifica_costo.html
    
    
    # =====================================
    # GESTIONE DOCUMENTI
    # =====================================
    
    # Lista documenti di uno stabilimento specifico
    path('<int:stabilimento_pk>/documenti/', views.documenti_stabilimento, name='documenti'),
    # Template: stabilimenti/documenti_stabilimento.html
    
    # Caricamento nuovo documento per uno stabilimento
    path('<int:stabilimento_pk>/documenti/nuovo/', views.nuovo_documento, name='nuovo_documento'),
    # Template: stabilimenti/nuovo_documento.html
    
    
    # =====================================
    # DASHBOARD SCADENZE
    # =====================================
    
    # Dashboard generale delle scadenze di tutti gli stabilimenti
    path('scadenze/', views.scadenze_dashboard, name='scadenze'),
    # Template: stabilimenti/scadenze_dashboard.html
    
    
    # =====================================
    # GESTIONE UTENZE SPECIFICHE  
    # =====================================
    
    # Dashboard generale utenze
    path('utenze/', views.dashboard_utenze, name='dashboard_utenze'),
    # Template: stabilimenti/dashboard_utenze.html
    
    # Ricerca avanzata utenze
    path('utenze/ricerca/', views.ricerca_utenze, name='ricerca_utenze'), 
    # Template: stabilimenti/ricerca_utenze.html
    
    # Utenze di uno stabilimento specifico
    path('<int:stabilimento_pk>/utenze/', views.utenze_stabilimento, name='utenze_stabilimento'),
    # Template: stabilimenti/utenze_stabilimento.html
    
    # Nuova utenza per uno stabilimento
    path('<int:stabilimento_pk>/utenze/nuova/', views.nuova_utenza, name='nuova_utenza'),
    # Template: stabilimenti/nuova_utenza.html
    
    # Modifica utenza esistente
    path('utenze/<int:pk>/modifica/', views.modifica_utenza, name='modifica_utenza'),
    # Template: stabilimenti/modifica_utenza.html

    # =====================================
    # AZIONI AJAX
    # =====================================
    
    # Toggle stato attivo/inattivo stabilimento (chiamata AJAX)
    path('<int:pk>/toggle-attivo/', views.toggle_attivo_stabilimento, name='toggle_attivo'),
    # Nessun template (restituisce JSON)
]