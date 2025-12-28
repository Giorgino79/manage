from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    EmailConfiguration, EmailTemplate, EmailMessage, 
    EmailStats, EmailAttachment, EmailQueue, EmailLog, EmailFolder
)
from .services import ManagementEmailService


@admin.register(EmailConfiguration)
class EmailConfigurationAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_address', 'smtp_server', 'is_active', 'is_verified', 'last_test_at']
    list_filter = ['is_active', 'is_verified', 'smtp_server', 'created_at']
    search_fields = ['user__username', 'email_address', 'display_name']
    readonly_fields = ['created_at', 'updated_at', 'last_test_at']
    
    fieldsets = (
        ('Utente', {
            'fields': ('user', 'display_name', 'email_address')
        }),
        ('Configurazione SMTP', {
            'fields': ('smtp_server', 'smtp_port', 'smtp_username', 'smtp_password', 'use_tls', 'use_ssl')
        }),
        ('Limiti e Stati', {
            'fields': ('daily_limit', 'hourly_limit', 'is_active', 'is_verified')
        }),
        ('Informazioni', {
            'fields': ('last_test_at', 'last_error', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['test_configuration', 'activate_configurations', 'deactivate_configurations']
    
    def test_configuration(self, request, queryset):
        """Testa configurazioni selezionate"""
        results = []
        for config in queryset:
            service = ManagementEmailService(user=config.user, config=config)
            result = service.test_configuration()
            
            if result['success']:
                results.append(f"✅ {config.email_address}: Test OK")
            else:
                results.append(f"❌ {config.email_address}: {result['error']}")
        
        self.message_user(request, " | ".join(results))
    test_configuration.short_description = "Testa configurazioni email"
    
    def activate_configurations(self, request, queryset):
        """Attiva configurazioni"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Attivate {updated} configurazioni")
    activate_configurations.short_description = "Attiva configurazioni selezionate"
    
    def deactivate_configurations(self, request, queryset):
        """Disattiva configurazioni"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Disattivate {updated} configurazioni")
    deactivate_configurations.short_description = "Disattiva configurazioni selezionate"


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'slug', 'is_active', 'usage_count', 'created_by', 'created_at']
    list_filter = ['category', 'is_active', 'is_system', 'created_at']
    search_fields = ['name', 'slug', 'subject', 'description']
    readonly_fields = ['id', 'usage_count', 'created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Informazioni Base', {
            'fields': ('name', 'slug', 'description', 'category')
        }),
        ('Contenuto', {
            'fields': ('subject', 'content_html', 'content_text')
        }),
        ('Variabili', {
            'fields': ('available_variables', 'sample_data'),
            'classes': ('collapse',)
        }),
        ('Stati', {
            'fields': ('is_active', 'is_system')
        }),
        ('Metadati', {
            'fields': ('id', 'usage_count', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['duplicate_templates', 'activate_templates', 'deactivate_templates']
    
    def duplicate_templates(self, request, queryset):
        """Duplica template selezionati"""
        count = 0
        for template in queryset:
            template.pk = None
            template.name = f"{template.name} (copia)"
            template.slug = f"{template.slug}-copy-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            template.usage_count = 0
            template.save()
            count += 1
        
        self.message_user(request, f"Duplicati {count} template")
    duplicate_templates.short_description = "Duplica template selezionati"
    
    def activate_templates(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Attivati {updated} template")
    activate_templates.short_description = "Attiva template"
    
    def deactivate_templates(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Disattivati {updated} template")
    deactivate_templates.short_description = "Disattiva template"


@admin.register(EmailMessage)
class EmailMessageAdmin(admin.ModelAdmin):
    list_display = ['subject_truncated', 'sender_config', 'to_addresses_display', 'status', 'template_used', 'sent_at', 'delivery_attempts']
    list_filter = ['status', 'sender_config', 'template_used__category', 'sent_at', 'has_attachments']
    search_fields = ['subject', 'to_addresses', 'content_html', 'content_text']
    readonly_fields = ['id', 'created_at', 'sent_at', 'received_at', 'updated_at']
    date_hierarchy = 'sent_at'
    
    fieldsets = (
        ('Messaggio', {
            'fields': ('sender_config', 'subject', 'to_addresses', 'cc_addresses', 'bcc_addresses')
        }),
        ('Contenuto', {
            'fields': ('template_used', 'content_html', 'content_text', 'has_attachments'),
            'classes': ('collapse',)
        }),
        ('Status e Risultati', {
            'fields': ('status', 'smtp_response', 'error_message', 'delivery_attempts')
        }),
        ('Collegamento', {
            'fields': ('content_type', 'object_id', 'related_description'),
            'classes': ('collapse',)
        }),
        ('Date', {
            'fields': ('id', 'created_at', 'sent_at', 'received_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def subject_truncated(self, obj):
        """Oggetto troncato per list_display"""
        return obj.subject[:50] + "..." if len(obj.subject) > 50 else obj.subject
    subject_truncated.short_description = 'Oggetto'
    
    def to_addresses_display(self, obj):
        """Destinatari per list_display"""
        if isinstance(obj.to_addresses, list):
            addresses = obj.to_addresses[:2]  # Prime 2
            display = ", ".join(addresses)
            if len(obj.to_addresses) > 2:
                display += f" (+{len(obj.to_addresses) - 2} altri)"
            return display
        return str(obj.to_addresses)
    to_addresses_display.short_description = 'Destinatari'
    
    actions = ['retry_failed_messages', 'mark_as_delivered']
    
    def retry_failed_messages(self, request, queryset):
        """Riprova invio messaggi falliti"""
        failed_messages = queryset.filter(status='failed')
        count = 0
        
        for message in failed_messages:
            try:
                service = ManagementEmailService(config=message.sender_config)
                result = service.send_email(
                    to=message.to_addresses,
                    subject=message.subject,
                    html_content=message.content_html,
                    content=message.content_text
                )
                
                if result['success']:
                    message.status = 'sent'
                    message.sent_at = timezone.now()
                    message.delivery_attempts += 1
                    message.error_message = ''
                    message.save()
                    count += 1
                    
            except Exception as e:
                message.delivery_attempts += 1
                message.error_message = str(e)
                message.save()
        
        self.message_user(request, f"Reinviati {count} messaggi su {failed_messages.count()}")
    retry_failed_messages.short_description = "Riprova invio messaggi falliti"
    
    def mark_as_delivered(self, request, queryset):
        updated = queryset.filter(status='sent').update(status='delivered')
        self.message_user(request, f"Marcati come consegnati {updated} messaggi")
    mark_as_delivered.short_description = "Marca come consegnati"


@admin.register(EmailStats)
class EmailStatsAdmin(admin.ModelAdmin):
    list_display = ['config', 'date', 'emails_sent', 'emails_failed', 'success_rate', 'preventivi_sent', 'automezzi_sent']
    list_filter = ['date', 'config']
    search_fields = ['config__user__username', 'config__email_address']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    
    def success_rate(self, obj):
        """Calcola tasso di successo"""
        total = obj.emails_sent + obj.emails_failed
        if total == 0:
            return "0%"
        rate = (obj.emails_sent / total) * 100
        color = "green" if rate > 90 else "orange" if rate > 70 else "red"
        return format_html('<span style="color: {}">{:.1f}%</span>', color, rate)
    success_rate.short_description = 'Tasso Successo'
    
    def get_queryset(self, request):
        """Ordina per data decrescente"""
        return super().get_queryset(request).order_by('-date')


@admin.register(EmailAttachment)
class EmailAttachmentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'message_subject', 'content_type', 'size_formatted', 'source_app', 'created_at']
    list_filter = ['content_type', 'source_app', 'created_at']
    search_fields = ['filename', 'message__subject', 'source_info']
    readonly_fields = ['file_hash', 'created_at']
    
    def message_subject(self, obj):
        """Oggetto del messaggio collegato"""
        return obj.message.subject[:40] + "..." if len(obj.message.subject) > 40 else obj.message.subject
    message_subject.short_description = 'Messaggio'
    
    def size_formatted(self, obj):
        """Dimensione formattata"""
        if obj.size > 1024 * 1024:  # MB
            return f"{obj.size / (1024 * 1024):.1f} MB"
        elif obj.size > 1024:  # KB
            return f"{obj.size / 1024:.1f} KB"
        else:
            return f"{obj.size} bytes"
    size_formatted.short_description = 'Dimensione'


@admin.register(EmailQueue)
class EmailQueueAdmin(admin.ModelAdmin):
    list_display = ['subject_truncated', 'config', 'to_display', 'status', 'priority', 'scheduled_at', 'attempt_count']
    list_filter = ['status', 'priority', 'config', 'scheduled_at', 'created_at']
    search_fields = ['subject', 'to_addresses']
    readonly_fields = ['id', 'created_at', 'updated_at', 'sent_at']
    date_hierarchy = 'scheduled_at'
    
    fieldsets = (
        ('Email', {
            'fields': ('config', 'to_addresses', 'cc_addresses', 'bcc_addresses', 'subject')
        }),
        ('Contenuto', {
            'fields': ('content_html', 'content_text'),
            'classes': ('collapse',)
        }),
        ('Configurazioni', {
            'fields': ('priority', 'scheduled_at', 'max_attempts')
        }),
        ('Stato', {
            'fields': ('status', 'attempt_count', 'error_message', 'sent_at')
        }),
        ('Metadati', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def subject_truncated(self, obj):
        return obj.subject[:50] + "..." if len(obj.subject) > 50 else obj.subject
    subject_truncated.short_description = 'Oggetto'
    
    def to_display(self, obj):
        if isinstance(obj.to_addresses, list):
            addresses = obj.to_addresses[:2]
            display = ", ".join(addresses)
            if len(obj.to_addresses) > 2:
                display += f" (+{len(obj.to_addresses) - 2})"
            return display
        return str(obj.to_addresses)
    to_display.short_description = 'Destinatari'

    actions = ['retry_failed', 'cancel_pending']
    
    def retry_failed(self, request, queryset):
        updated = queryset.filter(status='failed').update(
            status='pending',
            attempt_count=0,
            error_message=''
        )
        self.message_user(request, f"Rimessi in coda {updated} email")
    retry_failed.short_description = "Riprova email fallite"
    
    def cancel_pending(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='cancelled')
        self.message_user(request, f"Annullate {updated} email")
    cancel_pending.short_description = "Annulla email in attesa"


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'event_type', 'success_icon', 'event_description_short', 'config', 'user']
    list_filter = ['event_type', 'success', 'timestamp']
    search_fields = ['event_description', 'error_message', 'config__email_address', 'user__username']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Evento', {
            'fields': ('event_type', 'event_description', 'success')
        }),
        ('Dettagli', {
            'fields': ('config', 'message', 'user', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Dati', {
            'fields': ('event_data', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Meta', {
            'fields': ('timestamp',)
        })
    )
    
    def success_icon(self, obj):
        if obj.success:
            return format_html('<span style="color: green;">✓</span>')
        else:
            return format_html('<span style="color: red;">✗</span>')
    success_icon.short_description = 'Esito'
    
    def event_description_short(self, obj):
        return obj.event_description[:80] + "..." if len(obj.event_description) > 80 else obj.event_description
    event_description_short.short_description = 'Descrizione'


@admin.register(EmailFolder)
class EmailFolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'config', 'folder_type', 'total_messages', 'unread_messages']
    list_filter = ['folder_type', 'config']
    search_fields = ['name', 'config__email_address']
    readonly_fields = ['created_at', 'updated_at']
