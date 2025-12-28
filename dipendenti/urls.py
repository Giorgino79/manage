from django.urls import path
from . import views

app_name = 'dipendenti'

urlpatterns = [
    # =====================================================
    # AUTHENTICATION ROUTES
    # =====================================================
    
    # Landing page and login
    path('', views.landing_page, name='landing'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # =====================================================
    # DASHBOARD & MAIN VIEWS
    # =====================================================
    
    # Main dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # =====================================================
    # PROFILE MANAGEMENT
    # =====================================================
    
    # Personal profile views
    path('profilo/', views.mio_profilo, name='mio_profilo'),

    # =====================================================
    # PRESENZE / TIMBRATURA
    # =====================================================

    # Time clock / attendance tracking
    path('timbratura/', views.timbratura, name='timbratura'),
    path('concludi-giornata/', views.concludi_giornata, name='concludi_giornata'),
    path('report-presenze/', views.report_presenze, name='report_presenze'),

    # =====================================================
    # DIPENDENTI MANAGEMENT (Admin/Supervisors only)
    # =====================================================
    
    # CRUD operations for dipendenti
    path('lista/', views.DipendenteListView.as_view(), name='lista'),
    path('dettaglio/<int:pk>/', views.DipendenteDetailView.as_view(), name='dettaglio'),
    
    # =====================================================
    # API ENDPOINTS (AJAX) - TODO: Implement
    # =====================================================
    
    # API for AJAX requests
    # path('api/dipendente/<int:pk>/', views.api_dipendente_info, name='api_dipendente_info'),
    # path('api/change-password/', views.api_change_password, name='api_change_password'),
]