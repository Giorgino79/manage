"""
ACQUISTI ADMIN - Admin per gestione ordini di acquisto
=====================================================
"""

from django.contrib import admin
from .models import OrdineAcquisto


@admin.register(OrdineAcquisto)
class OrdineAcquistoAdmin(admin.ModelAdmin):
    """
    Admin per ordini di acquisto
    """
    
    list_display = [
        'numero_ordine',
        'fornitore',
        'stato',
        'importo_totale',
        'data_ordine',
        'creato_da',
        'get_giorni_dalla_creazione'
    ]
    
    list_filter = [
        'stato',
        'data_ordine',
        'fornitore',
        'creato_da'
    ]
    
    search_fields = [
        'numero_ordine',
        'fornitore__nome',
        'note_ordine',
        'riferimento_esterno'
    ]
    
    readonly_fields = [
        'numero_ordine',
        'data_ordine',
        'created_at',
        'updated_at',
        'data_ricevimento',
        'data_pagamento'
    ]
    
    fieldsets = (
        ('Identificazione', {
            'fields': (
                'numero_ordine',
                'fornitore',
                'preventivo_originale',
                'stato'
            )
        }),
        ('Dati Commerciali', {
            'fields': (
                'importo_totale',
                'valuta',
                'termini_pagamento',
                'tempi_consegna',
                'data_consegna_richiesta'
            )
        }),
        ('Workflow', {
            'fields': (
                'creato_da',
                'data_ordine',
                'data_ricevimento',
                'ricevuto_da',
                'data_pagamento', 
                'pagato_da'
            )
        }),
        ('Note e Riferimenti', {
            'fields': (
                'note_ordine',
                'riferimento_esterno'
            )
        }),
        ('Timestamp', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def get_giorni_dalla_creazione(self, obj):
        """Mostra giorni dalla creazione"""
        return f"{obj.get_giorni_dalla_creazione()} gg"
    get_giorni_dalla_creazione.short_description = "Giorni"
    
    def has_delete_permission(self, request, obj=None):
        """Impedisce cancellazione ordini ricevuti o pagati"""
        if obj and obj.stato in ['RICEVUTO', 'PAGATO']:
            return False
        return super().has_delete_permission(request, obj)
