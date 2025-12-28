"""
CORE URLS - URL configuration per app core
=========================================

Configurazione URL per tutte le funzionalità core utilities:
- Dashboard principale
- Generatori PDF, Excel, CSV
- Upload file e gestione
- API utilities
- Demo e test funzionalità

Pattern URL seguono convenzioni RESTful:
- /core/ - Dashboard principale
- /core/pdf/ - Funzionalità PDF
- /core/excel/ - Funzionalità Excel  
- /core/csv/ - Funzionalità CSV
- /core/files/ - Gestione file
- /core/utils/ - Utilities varie
- /core/api/ - API endpoints

Versione: 1.0
"""

from django.urls import path
from . import views

# Import allegati views directly since they're now imported in views.__init__
try:
    from .views.allegati import (
        AllegatoCreateView, AllegatoUpdateView, AllegatoDetailView, AllegatoDeleteView,
        allegato_download, allegato_preview, allegato_toggle_stato,
        allegati_list_api, allegato_quick_add, allegati_widget_content,
        allegati_bulk_action, allegati_stats
    )
    allegati_available = True
except ImportError:
    allegati_available = False

app_name = 'core'

urlpatterns = [
    # Dashboard principale
    path('', views.CoreDashboardView.as_view(), name='dashboard'),
    
    # =================================================================
    # PDF GENERATION URLS
    # =================================================================
    path('pdf/', views.pdf_generator_demo, name='pdf_demo'),
    path('pdf/demo/', views.pdf_generator_demo, name='pdf_generator_demo'),
    
    # =================================================================
    # EXCEL GENERATION URLS
    # =================================================================
    path('excel/', views.excel_generator_demo, name='excel_demo'),
    path('excel/demo/', views.excel_generator_demo, name='excel_generator_demo'),
    
    # =================================================================
    # CSV GENERATION URLS
    # =================================================================
    path('csv/', views.csv_generator_demo, name='csv_demo'),
    path('csv/demo/', views.csv_generator_demo, name='csv_generator_demo'),
    
    # =================================================================
    # FILE MANAGEMENT URLS
    # =================================================================
    path('files/', views.file_upload_demo, name='file_upload_demo'),
    path('files/upload/', views.file_upload_demo, name='file_upload'),
    
    # =================================================================
    # UTILITIES URLS
    # =================================================================
    path('utils/', views.utils_demo, name='utils_demo'),
    path('utilities/', views.utils_demo, name='utilities_demo'),
    
    # =================================================================
    # CHAT E MESSAGING URLS
    # =================================================================
    path('chat/', views.chat, name='chat'),
    path('dashboard-main/', views.dashboard, name='dashboard_main'),
    
    # =================================================================
    # EMAIL URLS
    # =================================================================
    path('email/messages/', views.email_messages, name='email_messages'),
    
    # =================================================================
    # PROMEMORIA URLS
    # =================================================================
    path('promemoria/', views.promemoria_list, name='promemoria_list'),
    path('promemoria/create/', views.promemoria_create, name='promemoria_create'),
    path('promemoria/<int:pk>/update/', views.promemoria_update, name='promemoria_update'),
    path('promemoria/<int:pk>/toggle/', views.promemoria_toggle, name='promemoria_toggle'),
    path('promemoria/<int:pk>/delete/', views.promemoria_delete, name='promemoria_delete'),
    
    # =================================================================
    # ALLEGATI URLS (conditional - only if allegati module is available)
    # =================================================================
    
    # =================================================================
    # API ENDPOINTS
    # =================================================================
    
    # API esistenti
    path('api/generate-code/', views.generate_code_api, name='generate_code_api'),
    path('api/validate-data/', views.validate_data_api, name='validate_data_api'),
    path('api/notifications/', views.notifications_api, name='notifications_api'),
    
    # URL temporaneo per allegati_lista - redirect al dashboard
    path('allegati/', views.CoreDashboardView.as_view(), name='allegati_lista'),
]

# Aggiungi allegati URLs solo se il modulo è disponibile
if allegati_available:
    urlpatterns += [
        # ALLEGATI URLS
        path('allegati/add/', AllegatoCreateView.as_view(), name='allegato_create'),
        path('allegati/<int:pk>/edit/', AllegatoUpdateView.as_view(), name='allegato_update'),
        path('allegati/<int:pk>/detail/', AllegatoDetailView.as_view(), name='allegato_detail'),
        path('allegati/<int:pk>/delete/', AllegatoDeleteView.as_view(), name='allegato_delete'),
        path('allegati/<int:pk>/download/', allegato_download, name='allegato_download'),
        path('allegati/<int:pk>/preview/', allegato_preview, name='allegato_preview'),
        path('allegati/<int:pk>/toggle/', allegato_toggle_stato, name='allegato_toggle_stato'),
        
        # Allegati API
        path('api/allegati/list/', allegati_list_api, name='allegati_list_api'),
        path('api/allegati/quick-add/', allegato_quick_add, name='allegato_quick_add'),
        path('api/allegati/widget/', allegati_widget_content, name='allegati_widget_content'),
        path('api/allegati/bulk/', allegati_bulk_action, name='allegati_bulk_action'),
        path('api/allegati/stats/', allegati_stats, name='allegati_stats'),
    ]