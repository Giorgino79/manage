"""
Views for Mail app
==================

Views per gestione email in Management.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Count
from django.views.decorators.http import require_http_methods
import json

from .models import (
    EmailConfiguration, EmailTemplate, EmailMessage,
    EmailStats, EmailAttachment, EmailQueue, EmailLog,
    EmailFolder, EmailLabel
)
from .services import ManagementEmailService


@login_required
def mail_dashboard(request):
    """Dashboard principale sistema mail"""
    
    # Ottieni configurazione utente
    try:
        config = EmailConfiguration.objects.get(user=request.user)
    except EmailConfiguration.DoesNotExist:
        config = None
    
    # Statistiche rapide
    stats_summary = {}
    if config:
        service = ManagementEmailService(user=request.user, config=config)
        stats_summary = service.get_user_stats(days=7)
    
    # Messaggi recenti
    recent_messages = EmailMessage.objects.filter(
        sender_config__user=request.user
    ).order_by('-created_at')[:10] if config else []
    
    # Template più utilizzati
    popular_templates = EmailTemplate.objects.filter(
        is_active=True,
        usage_count__gt=0
    ).order_by('-usage_count')[:5]
    
    context = {
        'config': config,
        'stats_summary': stats_summary,
        'recent_messages': recent_messages,
        'popular_templates': popular_templates,
    }
    
    return render(request, 'mail/dashboard.html', context)


@login_required
def email_config(request):
    """Configurazione email utente"""
    
    try:
        config = EmailConfiguration.objects.get(user=request.user)
    except EmailConfiguration.DoesNotExist:
        config = None
    
    if request.method == 'POST':
        # Salva configurazione
        display_name = request.POST.get('display_name', '')
        email_address = request.POST.get('email_address', '')
        smtp_server = request.POST.get('smtp_server', 'smtp.gmail.com')
        smtp_port = int(request.POST.get('smtp_port', 587))
        smtp_username = request.POST.get('smtp_username', '')
        smtp_password = request.POST.get('smtp_password', '')
        use_tls = request.POST.get('use_tls') == 'on'
        use_ssl = request.POST.get('use_ssl') == 'on'
        
        if config:
            # Aggiorna esistente
            config.display_name = display_name
            config.email_address = email_address
            config.smtp_server = smtp_server
            config.smtp_port = smtp_port
            config.smtp_username = smtp_username
            if smtp_password:  # Solo se fornita nuova password
                config.smtp_password = smtp_password
            config.use_tls = use_tls
            config.use_ssl = use_ssl
            config.save()
            
            messages.success(request, 'Configurazione aggiornata con successo')
        else:
            # Crea nuova
            config = EmailConfiguration.objects.create(
                user=request.user,
                display_name=display_name,
                email_address=email_address,
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                smtp_username=smtp_username,
                smtp_password=smtp_password,
                use_tls=use_tls,
                use_ssl=use_ssl
            )
            
            messages.success(request, 'Configurazione creata con successo')
        
        return redirect('mail:config')
    
    context = {
        'config': config,
    }
    
    return render(request, 'mail/config.html', context)


@login_required
def test_email_config(request):
    """Test configurazione email"""
    
    try:
        config = EmailConfiguration.objects.get(user=request.user)
        service = ManagementEmailService(user=request.user, config=config)
        result = service.test_configuration()
        
        if result['success']:
            messages.success(request, 'Test email inviata con successo! Controlla la tua casella.')
        else:
            messages.error(request, f'Errore test email: {result["error"]}')
            
    except EmailConfiguration.DoesNotExist:
        messages.error(request, 'Nessuna configurazione email trovata. Configura prima il tuo account.')
    
    return redirect('mail:config')


@login_required
def template_list(request):
    """Lista template email"""
    
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    
    templates = EmailTemplate.objects.filter(is_active=True)
    
    if search:
        templates = templates.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(subject__icontains=search)
        )
    
    if category:
        templates = templates.filter(category=category)
    
    templates = templates.order_by('-usage_count', 'name')
    
    # Paginazione
    paginator = Paginator(templates, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Categorie per filtro
    categories = EmailTemplate.objects.filter(is_active=True).values_list('category', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'category': category,
        'categories': categories,
    }
    
    return render(request, 'mail/template_list.html', context)


@login_required
def template_create(request):
    """Crea nuovo template"""
    
    if request.method == 'POST':
        name = request.POST.get('name', '')
        subject = request.POST.get('subject', '')
        content_html = request.POST.get('content_html', '')
        content_text = request.POST.get('content_text', '')
        category = request.POST.get('category', 'generico')
        description = request.POST.get('description', '')
        
        service = ManagementEmailService(user=request.user)
        result = service.create_template(
            name=name,
            subject=subject,
            content_html=content_html,
            content_text=content_text,
            category=category
        )
        
        if result['success']:
            messages.success(request, f'Template "{name}" creato con successo')
            return redirect('mail:template_list')
        else:
            messages.error(request, f'Errore creazione template: {result["error"]}')
    
    # Categorie disponibili
    categories = [
        ('preventivi', 'Preventivi'),
        ('automezzi', 'Automezzi'),
        ('stabilimenti', 'Stabilimenti'),
        ('acquisti', 'Acquisti'),
        ('fatturazione', 'Fatturazione'),
        ('anagrafica', 'Anagrafica'),
        ('sistema', 'Sistema'),
        ('generico', 'Generico'),
    ]
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'mail/template_create.html', context)


@login_required
def template_edit(request, pk):
    """Modifica template"""
    
    template = get_object_or_404(EmailTemplate, pk=pk)
    
    # Solo creatore o admin può modificare
    if template.created_by != request.user and not request.user.is_staff:
        messages.error(request, 'Non hai i permessi per modificare questo template')
        return redirect('mail:template_list')
    
    if request.method == 'POST':
        template.name = request.POST.get('name', template.name)
        template.subject = request.POST.get('subject', template.subject)
        template.content_html = request.POST.get('content_html', template.content_html)
        template.content_text = request.POST.get('content_text', template.content_text)
        template.category = request.POST.get('category', template.category)
        template.description = request.POST.get('description', template.description)
        template.save()
        
        messages.success(request, 'Template aggiornato con successo')
        return redirect('mail:template_list')
    
    categories = [
        ('preventivi', 'Preventivi'),
        ('automezzi', 'Automezzi'),
        ('stabilimenti', 'Stabilimenti'),
        ('acquisti', 'Acquisti'),
        ('fatturazione', 'Fatturazione'),
        ('anagrafica', 'Anagrafica'),
        ('sistema', 'Sistema'),
        ('generico', 'Generico'),
    ]
    
    context = {
        'template': template,
        'categories': categories,
    }
    
    return render(request, 'mail/template_edit.html', context)


@login_required
def message_list(request):
    """Lista messaggi email inviati"""
    
    # Filtri
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    try:
        config = EmailConfiguration.objects.get(user=request.user)
        messages_qs = EmailMessage.objects.filter(sender_config=config)
    except EmailConfiguration.DoesNotExist:
        messages_qs = EmailMessage.objects.none()
    
    if status:
        messages_qs = messages_qs.filter(status=status)
    
    if search:
        messages_qs = messages_qs.filter(
            Q(subject__icontains=search) |
            Q(to_addresses__icontains=search)
        )
    
    messages_qs = messages_qs.order_by('-created_at')
    
    # Paginazione
    paginator = Paginator(messages_qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status': status,
        'search': search,
        'status_choices': [
            ('pending', 'In Attesa'),
            ('sending', 'Invio'),
            ('sent', 'Inviato'),
            ('delivered', 'Consegnato'),
            ('failed', 'Fallito'),
            ('bounced', 'Rimbalzato'),
        ]
    }
    
    return render(request, 'mail/message_list.html', context)


@login_required
def message_detail(request, pk):
    """Dettaglio messaggio email"""
    
    message = get_object_or_404(EmailMessage, pk=pk)
    
    # Verifica che il messaggio appartenga all'utente
    if message.sender_config.user != request.user and not request.user.is_staff:
        raise Http404()
    
    context = {
        'message': message,
    }
    
    return render(request, 'mail/message_detail.html', context)


@login_required
def email_stats(request):
    """Statistiche email"""
    
    try:
        config = EmailConfiguration.objects.get(user=request.user)
        service = ManagementEmailService(user=request.user, config=config)
        
        # Statistiche per periodi diversi
        stats_7d = service.get_user_stats(days=7)
        stats_30d = service.get_user_stats(days=30)
        stats_90d = service.get_user_stats(days=90)
        
        # Statistiche dettagliate per categoria
        daily_stats = EmailStats.objects.filter(
            config=config
        ).order_by('-date')[:30]
        
        context = {
            'config': config,
            'stats_7d': stats_7d,
            'stats_30d': stats_30d, 
            'stats_90d': stats_90d,
            'daily_stats': daily_stats,
        }
        
    except EmailConfiguration.DoesNotExist:
        context = {
            'config': None,
            'error': 'Nessuna configurazione email trovata'
        }
    
    return render(request, 'mail/stats.html', context)


@login_required
def compose_email(request):
    """Componi nuova email"""
    
    try:
        config = EmailConfiguration.objects.get(user=request.user)
    except EmailConfiguration.DoesNotExist:
        messages.error(request, 'Configura prima il tuo account email per poter inviare messaggi')
        return redirect('mail:config')
    
    if request.method == 'POST':
        # Dati del form
        to_emails = request.POST.get('to', '').strip()
        cc_emails = request.POST.get('cc', '').strip()
        bcc_emails = request.POST.get('bcc', '').strip()
        subject = request.POST.get('subject', '').strip()
        content_text = request.POST.get('content_text', '').strip()
        content_html = request.POST.get('content_html', '').strip()
        template_id = request.POST.get('template', '')
        
        # Validazione base
        if not to_emails:
            messages.error(request, 'Inserisci almeno un destinatario')
        elif not subject:
            messages.error(request, 'Inserisci un oggetto')
        elif not content_text and not content_html:
            messages.error(request, 'Inserisci il contenuto del messaggio')
        else:
            # Prepara lista email
            to_list = [email.strip() for email in to_emails.split(',') if email.strip()]
            cc_list = [email.strip() for email in cc_emails.split(',') if email.strip()] if cc_emails else []
            bcc_list = [email.strip() for email in bcc_emails.split(',') if email.strip()] if bcc_emails else []
            
            # Invia email
            service = ManagementEmailService(user=request.user, config=config)
            result = service.send_email(
                to=to_list,
                cc=cc_list,
                bcc=bcc_list,
                subject=subject,
                content=content_text,
                html_content=content_html,
                template=template_id if template_id else None
            )
            
            if result['success']:
                messages.success(request, 'Email inviata con successo!')
                return redirect('mail:message_list')
            else:
                messages.error(request, f'Errore invio email: {result["error"]}')
    
    # Template disponibili
    templates = EmailTemplate.objects.filter(is_active=True).order_by('category', 'name')
    
    context = {
        'config': config,
        'templates': templates,
    }
    
    return render(request, 'mail/compose.html', context)


# API Views
@csrf_exempt
@login_required
def api_send_email(request):
    """API per invio email"""
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Metodo non supportato'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        to = data.get('to')
        subject = data.get('subject')
        content = data.get('content')
        html_content = data.get('html_content')
        template = data.get('template')
        context = data.get('context', {})
        
        if not to:
            return JsonResponse({'error': 'Destinatario richiesto'}, status=400)
        
        service = ManagementEmailService(user=request.user)
        result = service.send_email(
            to=to,
            subject=subject or '',
            content=content,
            html_content=html_content,
            template=template,
            context=context
        )
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON non valido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_template_preview(request, template_id):
    """API per anteprima template"""
    
    try:
        template = EmailTemplate.objects.get(pk=template_id, is_active=True)
        context = request.GET.dict()  # Usa parametri GET come contesto
        
        rendered = template.render(context)
        
        return JsonResponse({
            'success': True,
            'subject': rendered['subject'],
            'html': rendered['html'],
            'text': rendered['text']
        })
        
    except EmailTemplate.DoesNotExist:
        return JsonResponse({'error': 'Template non trovato'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
def api_resend_message(request, message_id):
    """API per reinvio messaggio"""
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Metodo non supportato'}, status=405)
    
    try:
        message = EmailMessage.objects.get(pk=message_id)
        
        # Verifica che il messaggio appartenga all'utente
        if message.sender_config.user != request.user and not request.user.is_staff:
            return JsonResponse({'error': 'Permesso negato'}, status=403)
        
        service = ManagementEmailService(user=request.user, config=message.sender_config)
        result = service.resend_message(message)
        
        return JsonResponse(result)
        
    except EmailMessage.DoesNotExist:
        return JsonResponse({'error': 'Messaggio non trovato'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Nuove view per funzionalità avanzate

@login_required
def queue_list(request):
    """Lista coda email"""
    
    try:
        config = EmailConfiguration.objects.get(user=request.user)
        queue_items = EmailQueue.objects.filter(config=config).order_by('-created_at')
    except EmailConfiguration.DoesNotExist:
        queue_items = EmailQueue.objects.none()
    
    # Paginazione
    paginator = Paginator(queue_items, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistiche coda
    stats = {
        'total': queue_items.count(),
        'pending': queue_items.filter(status='pending').count(),
        'processing': queue_items.filter(status='processing').count(),
        'sent': queue_items.filter(status='sent').count(),
        'failed': queue_items.filter(status='failed').count(),
    }
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
    }
    
    return render(request, 'mail/queue_list.html', context)


@login_required
def log_list(request):
    """Lista log email"""
    
    logs = EmailLog.objects.filter(user=request.user).order_by('-timestamp')
    
    # Filtri
    event_type = request.GET.get('event_type')
    if event_type:
        logs = logs.filter(event_type=event_type)
    
    # Paginazione
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Opzioni per filtro
    event_types = [
        ('send', 'Invio'),
        ('receive', 'Ricezione'),
        ('sync', 'Sincronizzazione'),
        ('error', 'Errore'),
        ('config', 'Configurazione'),
    ]
    
    context = {
        'page_obj': page_obj,
        'event_types': event_types,
        'current_event_type': event_type,
    }
    
    return render(request, 'mail/log_list.html', context)


@csrf_exempt
@login_required
def api_send_bulk_email(request):
    """API per invio email in massa"""
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Metodo non supportato'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        recipients = data.get('recipients', [])
        template = data.get('template')
        context = data.get('context', {})
        
        if not recipients:
            return JsonResponse({'error': 'Lista destinatari richiesta'}, status=400)
        
        if not template:
            return JsonResponse({'error': 'Template richiesto'}, status=400)
        
        service = ManagementEmailService(user=request.user)
        result = service.send_bulk_email(
            recipients=recipients,
            template=template,
            base_context=context
        )
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON non valido'}, status=400)
    except Exception as e:
        logger.error(f"Errore bulk email: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
def message_mark_read(request, pk):
    """Segna messaggio come letto"""
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Metodo non supportato'}, status=405)
    
    try:
        message = get_object_or_404(EmailMessage, pk=pk, sender_config__user=request.user)
        message.mark_as_read()
        
        return JsonResponse({
            'success': True,
            'is_read': True
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required  
def message_toggle_star(request, pk):
    """Cambia stato stella messaggio"""
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Metodo non supportato'}, status=405)
    
    try:
        message = get_object_or_404(EmailMessage, pk=pk, sender_config__user=request.user)
        message.toggle_flag()
        
        return JsonResponse({
            'success': True,
            'is_starred': message.is_flagged
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# =============================================================================
# NUOVE VIEWS - INTERFACCIA GMAIL-STYLE
# =============================================================================

@login_required
def inbox(request):
    """
    Vista principale inbox con layout Gmail-style a 3 colonne
    """
    try:
        config = EmailConfiguration.objects.get(user=request.user)
    except EmailConfiguration.DoesNotExist:
        messages.warning(request, "Configura prima il tuo account email")
        return redirect('mail:email_config')

    # Filtri
    search_query = request.GET.get('search', '')
    label_filter = request.GET.get('label', '')
    unread_only = request.GET.get('unread', '') == 'true'

    # Query messaggi inbox
    queryset = EmailMessage.objects.filter(
        sender_config=config,
        folder__folder_type='inbox'
    ).select_related('folder').prefetch_related('labels')

    # Applica filtri
    if search_query:
        queryset = queryset.filter(
            Q(subject__icontains=search_query) |
            Q(from_address__icontains=search_query) |
            Q(content_text__icontains=search_query)
        )

    if label_filter:
        queryset = queryset.filter(labels__slug=label_filter)

    if unread_only:
        queryset = queryset.filter(is_read=False)

    # Ordina per data (più recenti prima)
    queryset = queryset.order_by('-received_at', '-created_at')

    # Paginazione
    paginator = Paginator(queryset, 50)
    page = request.GET.get('page', 1)
    messages_page = paginator.get_page(page)

    # Crea cartelle di default se non esistono
    default_folders = [
        ('inbox', 'INBOX'),
        ('sent', 'Inviata'),
        ('drafts', 'Bozze'),
        ('trash', 'Cestino'),
        ('spam', 'Spam'),
    ]
    for folder_type, folder_name in default_folders:
        # Usa filter().first() per evitare MultipleObjectsReturned
        if not EmailFolder.objects.filter(config=config, folder_type=folder_type).exists():
            EmailFolder.objects.create(
                config=config,
                folder_type=folder_type,
                name=folder_name
            )

    # Cartelle con contatori
    folders = EmailFolder.objects.filter(config=config).annotate(
        unread_count=Count('emailmessage', filter=Q(emailmessage__is_read=False))
    ).order_by('folder_type')

    # Labels con contatori (usa 'messages' perché EmailLabel ha related_name='messages')
    labels = EmailLabel.objects.filter(
        configuration=config,
        is_visible=True
    ).annotate(
        unread_count=Count('messages', filter=Q(messages__is_read=False))
    )

    # Statistiche sidebar
    total_unread = EmailMessage.objects.filter(
        sender_config=config,
        is_read=False
    ).count()

    # Storage info (esempio - da implementare con calcolo reale)
    storage_used = 1024 * 1024 * 500  # 500 MB
    storage_total = 1024 * 1024 * 1024 * 15  # 15 GB
    storage_percent = int((storage_used / storage_total) * 100) if storage_total > 0 else 0

    # Messaggio selezionato (se presente nell'URL)
    selected_message = None
    selected_message_id = request.GET.get('message')
    if selected_message_id:
        try:
            selected_message = EmailMessage.objects.select_related('folder').prefetch_related(
                'labels', 'attachments'
            ).get(id=selected_message_id, sender_config=config)
            # Segna come letto
            if not selected_message.is_read:
                selected_message.is_read = True
                selected_message.save(update_fields=['is_read'])
        except EmailMessage.DoesNotExist:
            pass

    context = {
        'email_messages': messages_page,
        'page_obj': messages_page,
        'folders': folders,
        'labels': labels,
        'config': config,
        'current_folder': 'inbox',
        'total_unread': total_unread,
        'search_query': search_query,
        'unread_only': unread_only,
        'storage_used': storage_used,
        'storage_total': storage_total,
        'storage_percent': storage_percent,
        'selected_message': selected_message,
        'selected_message_id': selected_message_id,
    }

    return render(request, 'mail/inbox.html', context)


@login_required
def folder_view(request, folder_type):
    """
    Vista generica per cartelle (sent, drafts, trash, spam)
    """
    try:
        config = EmailConfiguration.objects.get(user=request.user)
    except EmailConfiguration.DoesNotExist:
        messages.warning(request, "Configura prima il tuo account email")
        return redirect('mail:email_config')

    # Mappa folder_type a query
    folder_filters = {
        'sent': {'direction': 'outgoing', 'status__in': ['sent', 'delivered']},
        'drafts': {'status': 'draft'},
        'trash': {'folder__folder_type': 'trash'},
        'spam': {'is_spam': True},
    }

    if folder_type not in folder_filters:
        messages.error(request, "Cartella non valida")
        return redirect('mail:inbox')

    # Query messaggi
    queryset = EmailMessage.objects.filter(
        sender_config=config,
        **folder_filters[folder_type]
    ).select_related('folder').prefetch_related('labels')

    # Filtri
    search_query = request.GET.get('search', '')
    if search_query:
        queryset = queryset.filter(
            Q(subject__icontains=search_query) |
            Q(from_address__icontains=search_query) |
            Q(to_addresses__icontains=search_query)
        )

    queryset = queryset.order_by('-created_at')

    # Paginazione
    paginator = Paginator(queryset, 50)
    page = request.GET.get('page', 1)
    messages_page = paginator.get_page(page)

    # Cartelle e labels (stesso di inbox)
    folders = EmailFolder.objects.filter(config=config).annotate(
        unread_count=Count('emailmessage', filter=Q(emailmessage__is_read=False))
    )

    labels = EmailLabel.objects.filter(
        configuration=config,
        is_visible=True
    ).annotate(
        unread_count=Count('messages', filter=Q(messages__is_read=False))
    )

    # Storage info
    storage_used = 1024 * 1024 * 500  # 500 MB
    storage_total = 1024 * 1024 * 1024 * 15  # 15 GB
    storage_percent = int((storage_used / storage_total) * 100) if storage_total > 0 else 0

    # Messaggio selezionato
    selected_message = None
    selected_message_id = request.GET.get('message')
    if selected_message_id:
        try:
            selected_message = EmailMessage.objects.select_related('folder').prefetch_related(
                'labels', 'attachments'
            ).get(id=selected_message_id, sender_config=config)
            if not selected_message.is_read:
                selected_message.is_read = True
                selected_message.save(update_fields=['is_read'])
        except EmailMessage.DoesNotExist:
            pass

    context = {
        'email_messages': messages_page,
        'page_obj': messages_page,
        'folders': folders,
        'labels': labels,
        'config': config,
        'current_folder': folder_type,
        'search_query': search_query,
        'storage_used': storage_used,
        'storage_total': storage_total,
        'storage_percent': storage_percent,
        'selected_message': selected_message,
        'selected_message_id': selected_message_id,
    }

    return render(request, 'mail/inbox.html', context)


@login_required
@require_http_methods(["POST"])
def bulk_action(request):
    """
    Gestisce azioni bulk sui messaggi
    Azioni: delete, mark_read, mark_unread, move_to_folder, add_label, remove_label
    """
    try:
        config = EmailConfiguration.objects.get(user=request.user)

        # Parse JSON body
        data = json.loads(request.body)
        action = data.get('action')
        message_ids = data.get('message_ids', [])

        if not message_ids:
            return JsonResponse({'error': 'Nessun messaggio selezionato'}, status=400)

        # Verifica che i messaggi appartengano all'utente
        messages_qs = EmailMessage.objects.filter(
            id__in=message_ids,
            sender_config=config
        )

        count = messages_qs.count()

        # Esegui azione
        if action == 'mark_read':
            messages_qs.update(is_read=True)

        elif action == 'mark_unread':
            messages_qs.update(is_read=False)

        elif action == 'delete':
            # Sposta in trash invece di eliminare
            trash_folder, _ = EmailFolder.objects.get_or_create(
                config=config,
                name='Trash',
                defaults={'folder_type': 'trash'}
            )
            messages_qs.update(folder=trash_folder)

        elif action == 'move_to_folder':
            folder_id = data.get('folder_id')
            if not folder_id:
                return JsonResponse({'error': 'folder_id richiesto'}, status=400)

            folder = EmailFolder.objects.get(id=folder_id, config=config)
            messages_qs.update(folder=folder)

        elif action == 'add_label':
            label_id = data.get('label_id')
            if not label_id:
                return JsonResponse({'error': 'label_id richiesto'}, status=400)

            label = EmailLabel.objects.get(id=label_id, configuration=config)
            for msg in messages_qs:
                msg.labels.add(label)

        elif action == 'remove_label':
            label_id = data.get('label_id')
            if not label_id:
                return JsonResponse({'error': 'label_id richiesto'}, status=400)

            label = EmailLabel.objects.get(id=label_id, configuration=config)
            for msg in messages_qs:
                msg.labels.remove(label)

        elif action == 'star':
            messages_qs.update(is_flagged=True)

        elif action == 'unstar':
            messages_qs.update(is_flagged=False)

        else:
            return JsonResponse({'error': 'Azione non valida'}, status=400)

        return JsonResponse({
            'success': True,
            'action': action,
            'count': count
        })

    except EmailConfiguration.DoesNotExist:
        return JsonResponse({'error': 'Configurazione email non trovata'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def save_draft(request):
    """
    Salva bozza email (autosave durante composizione)
    """
    try:
        config = EmailConfiguration.objects.get(user=request.user)

        data = json.loads(request.body)
        draft_id = data.get('draft_id')  # UUID se editing existing draft

        # Dati email
        to_addresses = data.get('to', [])
        cc_addresses = data.get('cc', [])
        bcc_addresses = data.get('bcc', [])
        subject = data.get('subject', '')
        content_html = data.get('content_html', '')
        content_text = data.get('content_text', '')

        if draft_id:
            # Update existing draft
            draft = EmailMessage.objects.get(
                id=draft_id,
                sender_config=config,
                status='draft'
            )
        else:
            # Create new draft
            draft = EmailMessage(
                sender_config=config,
                status='draft',
                direction='outgoing'
            )

        # Aggiorna campi
        draft.to_addresses = to_addresses if isinstance(to_addresses, list) else [to_addresses]
        draft.cc_addresses = cc_addresses if isinstance(cc_addresses, list) else []
        draft.bcc_addresses = bcc_addresses if isinstance(bcc_addresses, list) else []
        draft.subject = subject
        draft.content_html = content_html
        draft.content_text = content_text
        draft.save()

        return JsonResponse({
            'success': True,
            'draft_id': str(draft.id),
            'saved_at': draft.updated_at.isoformat()
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_fetch_emails(request):
    """
    API endpoint per triggare fetch manuale email IMAP
    """
    try:
        config = EmailConfiguration.objects.get(user=request.user)

        if not config.imap_enabled:
            return JsonResponse({
                'error': 'IMAP non abilitato. Configura IMAP nelle impostazioni.'
            }, status=400)

        # Import servizio
        from mail.services import ImapEmailService

        # Connetti e fetch
        service = ImapEmailService(config)

        if not service.connect():
            return JsonResponse({
                'error': 'Impossibile connettersi al server IMAP'
            }, status=500)

        # Fetch nuovi messaggi
        messages_list = service.fetch_new_messages(folder='INBOX', limit=50)

        if messages_list:
            saved_count = service.sync_messages_to_db(messages_list)
        else:
            saved_count = 0

        service.disconnect()

        # Aggiorna timestamp
        config.last_imap_sync = timezone.now()
        config.save(update_fields=['last_imap_sync'])

        return JsonResponse({
            'success': True,
            'count': saved_count,
            'new_messages': saved_count,  # Keep for backward compatibility
            'synced_at': config.last_imap_sync.isoformat()
        })

    except EmailConfiguration.DoesNotExist:
        return JsonResponse({'error': 'Configurazione non trovata'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
