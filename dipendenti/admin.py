from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Dipendente, AuditLogDipendente, Presenza, GiornataLavorativa
from .forms import DipendenteCreationForm, DipendenteChangeForm


@admin.register(Dipendente)
class DipendenteAdmin(UserAdmin):
    """Admin personalizzato per il modello Dipendente"""
    
    form = DipendenteChangeForm
    add_form = DipendenteCreationForm
    
    list_display = [
        'username', 'email', 'first_name', 'last_name', 
        'livello', 'stato', 'is_active', 'date_joined', 'ultimo_accesso'
    ]
    list_filter = [
        'livello', 'stato', 'is_active', 'is_staff', 'is_superuser',
        'date_joined', 'ultimo_accesso'
    ]
    search_fields = [
        'username', 'first_name', 'last_name', 'email', 
        'codice_fiscale', 'telefono'
    ]
    ordering = ['-date_joined']
    
    fieldsets = (
        (_('Informazioni di Base'), {
            'fields': ('username', 'password', 'email')
        }),
        (_('Informazioni Personali'), {
            'fields': (
                'first_name', 'last_name', 'indirizzo', 
                'telefono', 'telefono_emergenza',
                'data_nascita', 'data_assunzione'
            )
        }),
        (_('Autorizzazioni e Stato'), {
            'fields': ('livello', 'stato', 'is_active', 'is_staff', 'is_superuser')
        }),
        (_('Documenti di Identità'), {
            'fields': (
                'codice_fiscale', 
                'carta_identita_numero', 'carta_identita_scadenza',
                'patente_numero', 'patente_scadenza', 'patente_categorie'
            ),
            'classes': ['collapse']
        }),
        (_('Posizioni Contributive'), {
            'fields': ('posizione_inail', 'posizione_inps'),
            'classes': ['collapse']
        }),
        (_('File e Documenti'), {
            'fields': (
                'foto_profilo',
                'documento_carta_identita',
                'documento_codice_fiscale', 
                'documento_patente'
            ),
            'classes': ['collapse']
        }),
        (_('Note e Audit'), {
            'fields': ('note_interne', 'ultimo_accesso', 'creato_da'),
            'classes': ['collapse']
        }),
        (_('Gruppi e Permessi'), {
            'fields': ('groups', 'user_permissions'),
            'classes': ['collapse']
        }),
        (_('Date Importanti'), {
            'fields': ('last_login', 'date_joined'),
            'classes': ['collapse']
        }),
    )
    
    add_fieldsets = (
        (_('Informazioni di Base'), {
            'classes': ['wide'],
            'fields': (
                'username', 'email', 'password1', 'password2',
                'first_name', 'last_name', 'livello'
            )
        }),
        (_('Informazioni Aggiuntive'), {
            'classes': ['wide', 'collapse'],
            'fields': (
                'telefono', 'data_assunzione', 'is_active'
            )
        }),
    )
    
    readonly_fields = ['ultimo_accesso', 'date_joined', 'last_login', 'creato_da']
    
    actions = [
        'attiva_dipendenti',
        'disattiva_dipendenti',
        'reset_password_email',
        'export_dipendenti'
    ]
    
    def attiva_dipendenti(self, request, queryset):
        """Azione per attivare dipendenti selezionati"""
        updated = queryset.update(is_active=True, stato=Dipendente.StatoDipendente.ATTIVO)
        self.message_user(
            request,
            f'{updated} dipendenti sono stati attivati.'
        )
    attiva_dipendenti.short_description = _('Attiva dipendenti selezionati')
    
    def disattiva_dipendenti(self, request, queryset):
        """Azione per disattivare dipendenti selezionati"""
        updated = queryset.update(is_active=False, stato=Dipendente.StatoDipendente.SOSPESO)
        self.message_user(
            request,
            f'{updated} dipendenti sono stati disattivati.'
        )
    disattiva_dipendenti.short_description = _('Disattiva dipendenti selezionati')
    
    def reset_password_email(self, request, queryset):
        """Azione per inviare email di reset password (placeholder)"""
        count = queryset.count()
        self.message_user(
            request,
            f'Reset password richiesto per {count} dipendenti. (Funzionalità da implementare)'
        )
    reset_password_email.short_description = _('Invia email reset password')
    
    def export_dipendenti(self, request, queryset):
        """Azione per esportare dipendenti selezionati (placeholder)"""
        count = queryset.count()
        self.message_user(
            request,
            f'Export richiesto per {count} dipendenti. (Funzionalità da implementare)'
        )
    export_dipendenti.short_description = _('Esporta dipendenti selezionati')
    
    def get_queryset(self, request):
        """Ottimizza query con select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('creato_da')
    
    def save_model(self, request, obj, form, change):
        """Override save per impostare creato_da"""
        if not change:  # Nuovo oggetto
            obj.creato_da = request.user
        super().save_model(request, obj, form, change)


@admin.register(AuditLogDipendente)
class AuditLogDipendenteAdmin(admin.ModelAdmin):
    """Admin per l'audit log dei dipendenti"""
    
    list_display = [
        'dipendente', 'azione', 'eseguita_da', 
        'timestamp', 'indirizzo_ip'
    ]
    list_filter = [
        'azione', 'timestamp', 'dipendente__livello'
    ]
    search_fields = [
        'dipendente__username', 'dipendente__first_name', 
        'dipendente__last_name', 'eseguita_da__username',
        'indirizzo_ip'
    ]
    readonly_fields = [
        'dipendente', 'azione', 'dettagli', 'eseguita_da', 
        'timestamp', 'indirizzo_ip'
    ]
    ordering = ['-timestamp']
    
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        """Non permettere aggiunta manuale di log"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Non permettere modifica dei log"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Solo superuser può cancellare log"""
        return request.user.is_superuser
    
    def get_queryset(self, request):
        """Ottimizza query"""
        qs = super().get_queryset(request)
        return qs.select_related('dipendente', 'eseguita_da')


@admin.register(Presenza)
class PresenzaAdmin(admin.ModelAdmin):
    """Admin per la gestione delle timbrature presenze"""

    list_display = [
        'dipendente', 'data', 'tipo', 'orario',
        'indirizzo_ip', 'timestamp'
    ]
    list_filter = [
        'tipo', 'data', 'dipendente'
    ]
    search_fields = [
        'dipendente__username', 'dipendente__first_name',
        'dipendente__last_name', 'note', 'indirizzo_ip'
    ]
    readonly_fields = [
        'timestamp', 'orario', 'indirizzo_ip',
        'latitudine', 'longitudine'
    ]
    ordering = ['-data', '-timestamp']

    date_hierarchy = 'data'

    fieldsets = (
        (_('Informazioni Timbratura'), {
            'fields': ('dipendente', 'data', 'tipo', 'orario', 'timestamp')
        }),
        (_('Note'), {
            'fields': ('note',)
        }),
        (_('Geolocalizzazione'), {
            'fields': ('latitudine', 'longitudine', 'indirizzo_ip'),
            'classes': ['collapse']
        }),
    )

    def has_change_permission(self, request, obj=None):
        """Solo superuser può modificare le timbrature"""
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """Solo superuser può cancellare le timbrature"""
        return request.user.is_superuser

    def get_queryset(self, request):
        """Ottimizza query"""
        qs = super().get_queryset(request)
        return qs.select_related('dipendente')


@admin.register(GiornataLavorativa)
class GiornataLavorativaAdmin(admin.ModelAdmin):
    """Admin per la gestione delle giornate lavorative concluse"""

    list_display = [
        'dipendente', 'data', 'ore_lavorate', 'ore_straordinari',
        'ore_standard', 'timestamp_conclusione'
    ]
    list_filter = [
        'data', 'dipendente', 'conclusa'
    ]
    search_fields = [
        'dipendente__username', 'dipendente__first_name',
        'dipendente__last_name', 'note_conclusione'
    ]
    readonly_fields = [
        'timestamp_conclusione', 'ore_straordinari'
    ]
    ordering = ['-data', '-timestamp_conclusione']

    date_hierarchy = 'data'

    fieldsets = (
        (_('Informazioni Giornata'), {
            'fields': ('dipendente', 'data', 'conclusa')
        }),
        (_('Ore Lavorate'), {
            'fields': ('ore_lavorate', 'ore_standard', 'ore_straordinari')
        }),
        (_('Note e Timestamp'), {
            'fields': ('note_conclusione', 'timestamp_conclusione'),
            'classes': ['collapse']
        }),
    )

    def has_change_permission(self, request, obj=None):
        """Solo superuser può modificare le giornate concluse"""
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """Solo superuser può cancellare le giornate concluse"""
        return request.user.is_superuser

    def get_queryset(self, request):
        """Ottimizza query"""
        qs = super().get_queryset(request)
        return qs.select_related('dipendente')


# Personalizzazione del admin site
admin.site.site_header = _('Management System - Amministrazione')
admin.site.site_title = _('Management System Admin')
admin.site.index_title = _('Pannello di Controllo')
