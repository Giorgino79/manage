"""
PREVENTIVI ADMIN - Django admin per preventivi
============================================

Admin interface per:
- RichiestaPreventivo: Con gestione workflow e filtri avanzati
- Preventivo: Con valutazioni e ranking
- ParametroValutazione: Criteri dinamici
- ValutazionePreventivo: Punteggi assegnati
- FornitorePreventivo: Tracking email e stati
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg
from .models import (
    RichiestaPreventivo, 
    FornitorePreventivo, 
    Preventivo, 
    ParametroValutazione
)


class FornitorePrevenotivoInline(admin.TabularInline):
    """Inline per gestire fornitori associati alla richiesta"""
    model = FornitorePreventivo
    extra = 0
    readonly_fields = ['email_inviata', 'data_invio', 'ha_risposto', 'data_risposta', 'token_accesso']
    fields = ['fornitore', 'email_inviata', 'data_invio', 'ha_risposto', 'data_risposta', 'note_fornitore']


class ParametroValutazioneInline(admin.TabularInline):
    """Inline per parametri di valutazione"""
    model = ParametroValutazione
    extra = 0
    fields = ['descrizione', 'valore', 'ordine']
    ordering = ['ordine']


@admin.register(RichiestaPreventivo)
class RichiestaPrevenotivoAdmin(admin.ModelAdmin):
    """Admin per gestione richieste preventivo"""
    
    list_display = [
        'numero', 'titolo', 'richiedente', 'stato_display', 'priorita_display', 
        'fornitori_count', 'data_richiesta', 'data_scadenza', 'giorni_rimanenti_display'
    ]
    
    list_filter = [
        'stato', 'priorita', 'data_richiesta', 'data_scadenza', 'created_at'
    ]
    
    search_fields = [
        'numero', 'titolo', 'descrizione', 'richiedente__first_name', 
        'richiedente__last_name', 'richiedente__email'
    ]
    
    readonly_fields = [
        'numero', 'created_at', 'updated_at', 'data_invio_fornitori',
        'data_raccolta_completata', 'data_valutazione', 'data_approvazione', 
        'fornitori_totali', 'fornitori_risposto', 'percentuale_risposte'
    ]
    
    fieldsets = (
        ('Dati Principali', {
            'fields': ('numero', 'titolo', 'descrizione', 'stato', 'priorita')
        }),
        ('Workflow', {
            'fields': ('richiedente', 'operatore', 'approvatore', 'preventivo_approvato')
        }),
        ('Budget e Tempistiche', {
            'fields': ('budget_massimo', 'valuta', 'data_scadenza')
        }),
        ('Statistiche', {
            'fields': ('fornitori_totali', 'fornitori_risposto', 'percentuale_risposte'),
            'classes': ('collapse',)
        }),
        ('Workflow Tracking', {
            'fields': ('data_invio_fornitori', 'data_raccolta_completata', 'data_valutazione', 'data_approvazione'),
            'classes': ('collapse',)
        }),
        ('Note e Metadata', {
            'fields': ('note_interne', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [FornitorePrevenotivoInline]
    
    actions = ['marca_come_completato', 'marca_come_annullato', 'invia_solleciti']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'richiedente', 'operatore', 'approvatore'
        ).prefetch_related('fornitori')
    
    def stato_display(self, obj):
        """Mostra stato con colori"""
        color_map = {
            'CREATO': 'secondary',
            'INVIATO_FORNITORI': 'primary',
            'PREVENTIVI_RACCOLTI': 'info',
            'IN_VALUTAZIONE': 'warning',
            'APPROVATO': 'success',
            'ANNULLATO': 'danger'
        }
        color = color_map.get(obj.stato, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_stato_display()
        )
    stato_display.short_description = 'Stato'
    
    def priorita_display(self, obj):
        """Mostra priorità con colori"""
        if obj.priorita == 'NORMALE':
            return '-'
        color_map = {
            'URGENTE': 'danger',
            'ALTA': 'warning',
            'BASSA': 'info'
        }
        color = color_map.get(obj.priorita, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_priorita_display()
        )
    priorita_display.short_description = 'Priorità'
    
    def fornitori_count(self, obj):
        """Numero fornitori coinvolti"""
        return f"{obj.fornitori_risposto}/{obj.fornitori_totali}"
    fornitori_count.short_description = 'Fornitori (Risposte)'
    
    def giorni_rimanenti_display(self, obj):
        """Giorni rimanenti con colori"""
        giorni = obj.giorni_rimanenti
        if giorni < 0:
            return format_html('<span class="text-danger">Scaduto</span>')
        elif giorni <= 1:
            return format_html('<span class="text-warning">{} giorni</span>', giorni)
        elif giorni <= 7:
            return format_html('<span class="text-info">{} giorni</span>', giorni)
        else:
            return f"{giorni} giorni"
    giorni_rimanenti_display.short_description = 'Giorni Rimanenti'
    
    def marca_come_completato(self, request, queryset):
        """Action per marcare come completato"""
        count = 0
        for richiesta in queryset:
            if richiesta.può_essere_completato:
                richiesta.stato = 'COMPLETATO'
                richiesta.save()
                count += 1
        
        if count:
            self.message_user(request, f'{count} richieste marcate come completate.')
        else:
            self.message_user(request, 'Nessuna richiesta può essere completata.', level='warning')
    marca_come_completato.short_description = "Marca come completato"
    
    def marca_come_annullato(self, request, queryset):
        """Action per annullare richieste"""
        count = queryset.update(stato='ANNULLATO')
        self.message_user(request, f'{count} richieste annullate.')
    marca_come_annullato.short_description = "Annulla richieste"


class ParametroPrevenotivoInline(admin.TabularInline):
    """Inline per parametri preventivo"""
    model = ParametroValutazione
    extra = 0
    fields = ['descrizione', 'valore', 'ordine']
    ordering = ['ordine']


@admin.register(Preventivo)
class PrevenotivoAdmin(admin.ModelAdmin):
    """Admin per gestione preventivi ricevuti"""
    
    list_display = [
        'richiesta', 'fornitore', 'importo_display', 'parametri_count_display',
        'data_ricevimento', 'scadenza_display', 'operatore_inserimento'
    ]
    
    list_filter = [
        'data_ricevimento', 'richiesta__stato', 'fornitore', 'valuta', 'data_scadenza_offerta'
    ]
    
    search_fields = [
        'richiesta__numero', 'richiesta__titolo', 'fornitore__nome', 
        'numero_preventivo_fornitore', 'note_tecniche', 'note_commerciali'
    ]
    
    readonly_fields = [
        'data_ricevimento', 'data_scadenza_offerta', 'created_at', 'updated_at',
        'is_scaduto', 'giorni_validità_rimanenti'
    ]
    
    fieldsets = (
        ('Riferimenti', {
            'fields': ('richiesta', 'fornitore', 'numero_preventivo_fornitore', 'operatore_inserimento')
        }),
        ('Dati Economici', {
            'fields': ('importo_totale', 'valuta', 'validita_giorni', 'data_scadenza_offerta')
        }),
        ('Condizioni', {
            'fields': ('termini_pagamento', 'tempi_consegna', 'condizioni_trasporto', 'garanzia')
        }),
        ('Note', {
            'fields': ('note_tecniche', 'note_commerciali')
        }),
        ('Validità', {
            'fields': ('is_scaduto', 'giorni_validità_rimanenti'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('data_ricevimento', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [ParametroPrevenotivoInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'richiesta', 'fornitore', 'operatore_inserimento'
        ).prefetch_related('valutazionepreventivo_set')
    
    def importo_display(self, obj):
        """Mostra importo formattato"""
        return format_html('€ {:,.2f}', obj.importo_totale)
    importo_display.short_description = 'Importo'
    
    def parametri_count_display(self, obj):
        """Mostra numero parametri definiti"""
        count = obj.parametri.count()
        if count > 0:
            return format_html('<span class="badge bg-info">{} parametri</span>', count)
        else:
            return '-'
    parametri_count_display.short_description = 'Parametri'
    
    def scadenza_display(self, obj):
        """Mostra scadenza con colori"""
        if obj.is_scaduto:
            return format_html('<span class="text-danger">Scaduto</span>')
        elif obj.giorni_validità_rimanenti <= 7:
            return format_html(
                '<span class="text-warning">{}</span>', 
                obj.data_scadenza_offerta.strftime('%d/%m/%Y')
            )
        else:
            return obj.data_scadenza_offerta.strftime('%d/%m/%Y')
    scadenza_display.short_description = 'Scadenza Offerta'


@admin.register(ParametroValutazione)
class ParametroValutazioneAdmin(admin.ModelAdmin):
    """Admin per parametri di valutazione semplificati"""
    
    list_display = [
        'preventivo', 'descrizione', 'valore', 'ordine', 'creato_da', 'created_at'
    ]
    
    list_filter = [
        'preventivo__richiesta__stato', 'creato_da', 'created_at'
    ]
    
    search_fields = [
        'preventivo__richiesta__numero', 'preventivo__fornitore__nome',
        'descrizione', 'valore'
    ]
    
    fieldsets = (
        ('Parametro', {
            'fields': ('preventivo', 'descrizione', 'valore', 'ordine')
        }),
        ('Metadata', {
            'fields': ('creato_da', 'created_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at']


# Admin per ValutazionePreventivo rimossa - ora si usano parametri semplificati


@admin.register(FornitorePreventivo)
class FornitorePrevenotivoAdmin(admin.ModelAdmin):
    """Admin per tracking fornitori-preventivi"""
    
    list_display = [
        'richiesta', 'fornitore', 'email_status', 'risposta_status', 
        'data_invio', 'giorni_senza_risposta_display'
    ]
    
    list_filter = [
        'email_inviata', 'ha_risposto', 'data_invio', 'data_risposta', 'richiesta__stato'
    ]
    
    search_fields = [
        'richiesta__numero', 'richiesta__titolo', 'fornitore__nome', 'note_fornitore'
    ]
    
    readonly_fields = [
        'token_accesso', 'created_at', 'updated_at', 'giorni_senza_risposta'
    ]
    
    fieldsets = (
        ('Riferimenti', {
            'fields': ('richiesta', 'fornitore')
        }),
        ('Tracking Email', {
            'fields': ('email_inviata', 'data_invio', 'email_letta', 'data_lettura')
        }),
        ('Tracking Risposta', {
            'fields': ('ha_risposto', 'data_risposta', 'note_fornitore')
        }),
        ('Solleciti', {
            'fields': ('numero_solleciti', 'data_ultimo_sollecito')
        }),
        ('Sicurezza', {
            'fields': ('token_accesso',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('giorni_senza_risposta', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def email_status(self, obj):
        """Status email con colori"""
        if obj.email_inviata:
            if obj.email_letta:
                return format_html('<span class="text-success">✓ Letta</span>')
            else:
                return format_html('<span class="text-info">✓ Inviata</span>')
        else:
            return format_html('<span class="text-danger">✗ Non inviata</span>')
    email_status.short_description = 'Email'
    
    def risposta_status(self, obj):
        """Status risposta con colori"""
        if obj.ha_risposto:
            return format_html('<span class="text-success">✓ Ricevuta</span>')
        else:
            return format_html('<span class="text-warning">⏳ In attesa</span>')
    risposta_status.short_description = 'Risposta'
    
    def giorni_senza_risposta_display(self, obj):
        """Giorni senza risposta con colori"""
        giorni = obj.giorni_senza_risposta
        if giorni == 0 or obj.ha_risposto:
            return '-'
        elif giorni <= 3:
            return f"{giorni} giorni"
        elif giorni <= 7:
            return format_html('<span class="text-warning">{} giorni</span>', giorni)
        else:
            return format_html('<span class="text-danger">{} giorni</span>', giorni)
    giorni_senza_risposta_display.short_description = 'Giorni Senza Risposta'