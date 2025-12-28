"""
ANAGRAFICA ADMIN - Django admin per anagrafica
==============================================

Admin interface per:
- Cliente: Con gestione crediti e filtri avanzati
- Fornitore: Con categorizzazione e dati fiscali

NOTA: Admin per rappresentanti rimosso
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Cliente, Fornitore


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    """Admin per gestione clienti"""
    
    list_display = [
        'nome', 'email', 'telefono', 'zona', 'limite_credito', 
        'stato_credito_display', 'attivo', 'created_at'
    ]
    
    list_filter = [
        'attivo', 'tipo_pagamento', 'giorno_chiusura', 'created_at',
        'limite_credito',
    ]
    
    search_fields = [
        'nome', 'email', 'telefono', 'partita_iva', 'codice_fiscale', 'zona'
    ]
    
    readonly_fields = ['created_at', 'updated_at', 'credito_utilizzato', 'credito_disponibile']
    
    fieldsets = (
        ('Dati Anagrafici', {
            'fields': ('nome', 'indirizzo', 'citta', 'cap', 'zona')
        }),
        ('Contatti', {
            'fields': ('telefono', 'email', 'pec')
        }),
        ('Dati Fiscali', {
            'fields': ('partita_iva', 'codice_fiscale', 'codice_univoco')
        }),
        ('Dati Commerciali', {
            'fields': ('tipo_pagamento', 'limite_credito', 'credito_utilizzato', 'credito_disponibile')
        }),
        ('Orari e Consegne', {
            'fields': ('orario_consegna', 'giorno_chiusura')
        }),
        ('Stato e Note', {
            'fields': ('attivo', 'note')
        }),
        ('Timestamp', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def stato_credito_display(self, obj):
        """Mostra stato credito con colori"""
        if obj.limite_credito == 0:
            return format_html(
                '<span style="color: gray;">Nessun limite</span>'
            )
        
        stato = obj.get_stato_credito()
        color_map = {
            'ok': 'green',
            'attenzione': 'orange', 
            'critico': 'red',
            'nessun_limite': 'gray'
        }
        color = color_map.get(stato['stato'], 'gray')
        
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color,
            stato['percentuale_uso']
        )
    
    stato_credito_display.short_description = 'Stato Credito'
    
    actions = ['attiva_clienti', 'disattiva_clienti']
    
    def attiva_clienti(self, request, queryset):
        """Attiva clienti selezionati"""
        count = queryset.update(attivo=True)
        self.message_user(request, f'{count} clienti attivati con successo.')
    attiva_clienti.short_description = "Attiva clienti selezionati"
    
    def disattiva_clienti(self, request, queryset):
        """Disattiva clienti selezionati"""
        count = queryset.update(attivo=False)
        self.message_user(request, f'{count} clienti disattivati con successo.')
    disattiva_clienti.short_description = "Disattiva clienti selezionati"


@admin.register(Fornitore)
class FornitoreAdmin(admin.ModelAdmin):
    """Admin per gestione fornitori"""
    
    list_display = [
        'nome', 'email', 'telefono', 'categoria', 
        'tipo_pagamento', 'priorita_pagamento_default', 'attivo', 'created_at'
    ]
    
    list_filter = [
        'attivo', 'categoria', 'tipo_pagamento', 'priorita_pagamento_default', 'created_at'
    ]
    
    search_fields = [
        'nome', 'email', 'telefono', 'partita_iva', 'codice_fiscale',
        'referente_nome', 'referente_email'
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Dati Anagrafici', {
            'fields': ('nome', 'indirizzo', 'citta', 'cap')
        }),
        ('Contatti', {
            'fields': ('telefono', 'email', 'pec')
        }),
        ('Dati Fiscali', {
            'fields': ('partita_iva', 'codice_fiscale', 'codice_destinatario', 'iban')
        }),
        ('Dati Commerciali', {
            'fields': ('categoria', 'tipo_pagamento', 'priorita_pagamento_default')
        }),
        ('Referente', {
            'fields': ('referente_nome', 'referente_telefono', 'referente_email'),
            'classes': ('collapse',)
        }),
        ('Stato e Note', {
            'fields': ('attivo', 'note')
        }),
        ('Timestamp', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['attiva_fornitori', 'disattiva_fornitori']
    
    def attiva_fornitori(self, request, queryset):
        """Attiva fornitori selezionati"""
        count = queryset.update(attivo=True)
        self.message_user(request, f'{count} fornitori attivati con successo.')
    attiva_fornitori.short_description = "Attiva fornitori selezionati"
    
    def disattiva_fornitori(self, request, queryset):
        """Disattiva fornitori selezionati"""
        count = queryset.update(attivo=False)
        self.message_user(request, f'{count} fornitori disattivati con successo.')
    disattiva_fornitori.short_description = "Disattiva fornitori selezionati"