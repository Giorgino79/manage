"""
Context Processors for Mail App
"""
from mail.models import EmailMessage, EmailConfiguration


def unread_emails(request):
    """
    Aggiunge il contatore delle email non lette al contesto globale
    """
    unread_count = 0

    if request.user.is_authenticated:
        try:
            config = EmailConfiguration.objects.get(user=request.user)
            unread_count = EmailMessage.objects.filter(
                sender_config=config,
                is_read=False,
                direction='incoming'
            ).count()
        except EmailConfiguration.DoesNotExist:
            pass

    return {
        'unread_emails_count': unread_count
    }
