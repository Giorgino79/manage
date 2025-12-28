"""
URLs for Mail app
=================

URL patterns per l'app mail di Management.
"""

from django.urls import path
from . import views

app_name = 'mail'

urlpatterns = [
    # Dashboard
    path('', views.mail_dashboard, name='dashboard'),
    
    # Configurazioni
    path('config/', views.email_config, name='config'),
    path('config/test/', views.test_email_config, name='test_config'),
    
    # Compose
    path('compose/', views.compose_email, name='compose'),
    
    # Template
    path('templates/', views.template_list, name='template_list'),
    path('templates/create/', views.template_create, name='template_create'),
    path('templates/<uuid:pk>/edit/', views.template_edit, name='template_edit'),
    
    # Messaggi
    path('messages/', views.message_list, name='message_list'),
    path('messages/<uuid:pk>/', views.message_detail, name='message_detail'),
    
    # Statistiche
    path('stats/', views.email_stats, name='stats'),
    
    # Coda e log
    path('queue/', views.queue_list, name='queue_list'),
    path('logs/', views.log_list, name='log_list'),
    
    # API endpoints
    path('api/send/', views.api_send_email, name='api_send'),
    path('api/preview/<uuid:template_id>/', views.api_template_preview, name='api_template_preview'),
    path('api/resend/<uuid:message_id>/', views.api_resend_message, name='api_resend'),
    path('api/bulk-send/', views.api_send_bulk_email, name='api_bulk_send'),
    
    # Azioni sui messaggi
    path('messages/<uuid:pk>/mark-read/', views.message_mark_read, name='message_mark_read'),
    path('messages/<uuid:pk>/toggle-star/', views.message_toggle_star, name='message_toggle_star'),

    # =============================================================================
    # NUOVE ROUTES - INTERFACCIA GMAIL-STYLE
    # =============================================================================

    # Inbox e cartelle
    path('inbox/', views.inbox, name='inbox'),
    path('folder/<str:folder_type>/', views.folder_view, name='folder_view'),

    # API Bulk Actions
    path('api/bulk-action/', views.bulk_action, name='bulk_action'),
    path('api/save-draft/', views.save_draft, name='save_draft'),
    path('api/fetch-emails/', views.api_fetch_emails, name='api_fetch_emails'),
]