"""
FATTURAZIONE ADMIN - Amministrazione fatturazione passiva
=======================================================

Django admin per gestione fatturazione passiva con:
- FatturaFornitoreAdmin: Admin principale con inlines
- DettaglioFatturaInline: Gestione righe dettaglio
- ScadenzaPagamentoInline: Gestione scadenze
- ComunicazioneFatturatoInline: Storico comunicazioni
- Filtri e azioni personalizzate
- Export integrato

Adattato da AMM/fatturazione per progetto Management
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone

from .models import (
    FatturaFornitore,
    DettaglioFattura,
    ScadenzaPagamento,
    ComunicazioneFatturato
)


class DettaglioFatturaInline(admin.TabularInline):
    """
    Inline per gestione dettagli fattura
    """
    model = DettaglioFattura
    extra = 1
    readonly_fields = ('get_importo_totale_riga',)
    fields = (
        'descrizione', 'quantita', 'unita_misura', 'prezzo_unitario',
        'sconto_percentuale', 'aliquota_iva', 'get_importo_totale_riga', 'note_riga'
    )
    
    def get_importo_totale_riga(self, obj):
        if obj.pk:
            return f"€ {obj.get_importo_totale_riga():.2f}"
        return "-"
    get_importo_totale_riga.short_description = "Totale Riga"


@admin.register(FatturaFornitore)
class FatturaFornitoreAdmin(admin.ModelAdmin):
    """
    Admin principale per fatture fornitori
    """
    
    list_display = (
        'numero_protocollo', 'numero_fattura', 'fornitore',
        'data_fattura', 'data_scadenza', 'importo_totale_display',
        'stato_display', 'priorita_display', 'giorni_scadenza_display'
    )
    
    list_filter = (
        'stato', 'priorita_pagamento', 'fornitore',
        'data_fattura', 'data_scadenza', 'data_ricezione'
    )
    
    search_fields = (
        'numero_fattura', 'numero_protocollo', 'fornitore__nome',
        'oggetto', 'note_interne'
    )
    
    readonly_fields = (
        'numero_protocollo', 'data_ricezione', 'created_at', 'updated_at',
        'creata_da', 'modificata_da'
    )
    
    fieldsets = (
        ('Identificazione', {
            'fields': (
                'numero_protocollo', 'numero_fattura', 'fornitore',
                'ordine_acquisto', 'data_fattura', 'data_ricezione'
            )
        }),
        ('Stato e Workflow', {
            'fields': (
                'stato', 'priorita_pagamento'
            )
        }),
        ('Importi', {
            'fields': (
                'importo_netto', 'importo_iva', 'importo_totale', 'valuta'
            )
        }),
        ('Pagamento', {
            'fields': (
                'termini_pagamento', 'data_scadenza', 'data_pagamento',
                'importo_pagato', 'modalita_pagamento'
            )
        }),
        ('Note', {
            'fields': ('oggetto', 'note_interne')
        }),
        ('Audit Trail', {
            'fields': (
                'creata_da', 'modificata_da', 'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [DettaglioFatturaInline]
    
    def importo_totale_display(self, obj):
        return f"€ {obj.importo_totale:.2f}"
    importo_totale_display.short_description = "Importo"
    importo_totale_display.admin_order_field = "importo_totale"
    
    def stato_display(self, obj):
        css_class = obj.get_stato_css_class()
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            css_class,
            obj.get_stato_display()
        )
    stato_display.short_description = "Stato"
    stato_display.admin_order_field = "stato"
    
    def priorita_display(self, obj):
        css_class = obj.get_priorita_css_class()
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            css_class,
            obj.get_priorita_pagamento_display()
        )
    priorita_display.short_description = "Priorità"
    priorita_display.admin_order_field = "priorita_pagamento"
    
    def giorni_scadenza_display(self, obj):
        giorni = obj.get_giorni_scadenza()
        if giorni is None:
            return "-"
        
        if giorni < 0:
            return format_html('<span style="color: red;">Scaduta ({} gg)</span>', abs(giorni))
        elif giorni <= 3:
            return format_html('<span style="color: orange;">{} giorni</span>', giorni)
        elif giorni <= 7:
            return format_html('<span style="color: yellow;">{} giorni</span>', giorni)
        else:
            return f"{giorni} giorni"
    giorni_scadenza_display.short_description = "Scadenza"
    
    def save_model(self, request, obj, form, change):
        if not change:  # Nuovo oggetto
            obj.creata_da = request.user
        obj.modificata_da = request.user
        super().save_model(request, obj, form, change)


@admin.register(DettaglioFattura)
class DettaglioFatturaAdmin(admin.ModelAdmin):
    """
    Admin per dettagli fattura
    """
    list_display = (
        'fattura', 'descrizione', 'quantita', 'prezzo_unitario',
        'aliquota_iva', 'get_importo_totale_display'
    )
    list_filter = ('aliquota_iva', 'fattura__stato')
    search_fields = ('descrizione', 'fattura__numero_protocollo', 'note_riga')
    readonly_fields = ('get_importo_iva', 'get_importo_totale_riga')
    
    def get_importo_totale_display(self, obj):
        return f"€ {obj.get_importo_totale_riga():.2f}"
    get_importo_totale_display.short_description = "Totale"
    get_importo_totale_display.admin_order_field = "importo_riga"


@admin.register(ScadenzaPagamento)
class ScadenzaPagamentoAdmin(admin.ModelAdmin):
    """
    Admin per scadenze pagamento
    """
    list_display = (
        'fattura', 'data_scadenza', 'importo_scadenza',
        'priorita', 'stato', 'giorni_alla_scadenza_display'
    )
    list_filter = ('stato', 'priorita', 'data_scadenza')
    search_fields = ('fattura__numero_protocollo', 'note_pagamento')
    readonly_fields = ('created_at', 'updated_at')
    
    def giorni_alla_scadenza_display(self, obj):
        giorni = obj.giorni_alla_scadenza()
        if giorni < 0:
            return format_html('<span style="color: red;">Scaduta ({} gg)</span>', abs(giorni))
        elif giorni <= 3:
            return format_html('<span style="color: orange;">{} giorni</span>', giorni)
        else:
            return f"{giorni} giorni"
    giorni_alla_scadenza_display.short_description = "Giorni Scadenza"


@admin.register(ComunicazioneFatturato)
class ComunicazioneFatturatoAdmin(admin.ModelAdmin):
    """
    Admin per comunicazioni fatturato
    """
    list_display = (
        'fattura', 'tipo_comunicazione', 'oggetto',
        'email_destinatario', 'email_inviata', 'data_invio'
    )
    list_filter = (
        'tipo_comunicazione', 'email_inviata',
        'data_invio', 'created_at'
    )
    search_fields = (
        'fattura__numero_protocollo', 'oggetto', 'messaggio',
        'email_destinatario'
    )
    readonly_fields = ('created_at',)
    
    def save_model(self, request, obj, form, change):
        if not change:  # Nuovo oggetto
            obj.creata_da = request.user
        super().save_model(request, obj, form, change)