"""
Mail Services for Management
============================

Servizi email integrati per Management con le configurazioni SMTP esistenti.
Compatibile con core.email_utils esistente e configurazioni Django settings.
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from django.core.mail import EmailMessage as DjangoEmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from typing import Dict, List, Optional, Any, Union
import os

from mail.models import (
    EmailConfiguration, EmailTemplate, EmailMessage,
    EmailStats, EmailAttachment
)

logger = logging.getLogger(__name__)


class ManagementEmailService:
    """
    Servizio email principale per Management.
    Integra con le configurazioni SMTP esistenti in settings.py.
    """
    
    def __init__(self, user: User = None, config: EmailConfiguration = None):
        """
        Inizializza servizio email.
        
        Args:
            user: Utente Django
            config: Configurazione email specifica
        """
        self.user = user
        self.config = config
        
        # Se non specificato, cerca configurazione per l'utente
        if user and not config:
            try:
                self.config = EmailConfiguration.objects.get(
                    user=user, is_active=True
                )
            except EmailConfiguration.DoesNotExist:
                self.config = None
    
    def send_email(self,
                   to: Union[str, List[str]],
                   subject: str,
                   content: str = None,
                   html_content: str = None,
                   cc: List[str] = None,
                   bcc: List[str] = None,
                   template: str = None,
                   context: Dict = None,
                   attachments: List[str] = None,
                   source_object: Any = None,
                   category: str = 'generico') -> Dict[str, Any]:
        """
        Invia email utilizzando le configurazioni Management.
        
        Args:
            to: Destinatario/i
            subject: Oggetto
            content: Contenuto testuale
            html_content: Contenuto HTML
            cc: Lista destinatari in copia
            bcc: Lista destinatari in copia nascosta
            template: Slug template da utilizzare
            context: Variabili per template
            attachments: Lista percorsi file da allegare
            source_object: Oggetto Django collegato
            category: Categoria per statistiche
            
        Returns:
            Dict con risultato operazione
        """
        try:
            # Normalizza destinatari
            if isinstance(to, str):
                to = [to]
            
            # Renderizza template se specificato
            if template:
                template_result = self._render_template(template, context or {})
                if not template_result['success']:
                    return template_result
                
                subject = template_result['subject']
                html_content = template_result['html']
                content = template_result['text']
            
            # Determina metodo di invio
            if self.config and self.config.is_configured:
                # Usa configurazione utente
                result = self._send_with_user_config(
                    to, subject, content, html_content, attachments
                )
            else:
                # Usa configurazione Django settings (compatibilità)
                result = self._send_with_django_settings(
                    to, subject, content, html_content, attachments
                )
            
            # Salva log del messaggio
            if result['success']:
                self._log_sent_message(
                    to, subject, content, html_content, 
                    source_object, category, template
                )
                self._update_stats(category)
            
            return result
            
        except Exception as e:
            logger.error(f"Errore invio email: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 'SEND_ERROR'
            }
    
    def send_bulk_emails(self,
                        recipients: List[Dict],
                        template: str,
                        base_context: Dict = None,
                        category: str = 'generico') -> Dict[str, Any]:
        """
        Invio email di massa.
        
        Args:
            recipients: Lista [{'email': 'test@test.com', 'context': {...}}]
            template: Template da utilizzare
            base_context: Contesto base condiviso
            category: Categoria per statistiche
            
        Returns:
            Statistiche invio
        """
        results = {
            'total': len(recipients),
            'sent': 0,
            'failed': 0,
            'errors': []
        }
        
        for recipient in recipients:
            try:
                # Unisce contesto base con specifico destinatario
                context = {**(base_context or {}), **recipient.get('context', {})}
                
                result = self.send_email(
                    to=recipient['email'],
                    template=template,
                    context=context,
                    category=category
                )
                
                if result['success']:
                    results['sent'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"{recipient['email']}: {result['error']}")
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"{recipient['email']}: {str(e)}")
        
        return results
    
    def send_preventivo_email(self,
                             richiesta,
                             fornitore,
                             asset=None) -> Dict[str, Any]:
        """
        Compatibilità con core.email_utils per preventivi.
        Utilizza i template esistenti in templates/email/.
        """
        try:
            # Prepara contesto
            context = {
                'richiesta': richiesta,
                'fornitore': fornitore,
                'asset': asset,
                'data_invio': timezone.now(),
                'scadenza': getattr(richiesta, 'data_scadenza', None),
            }
            
            # Determina template basato su tipo asset
            if asset and hasattr(asset, 'targa'):
                # Automezzo
                template_name = 'richiesta_preventivo_automezzo'
                context['automezzo'] = asset
                
                # Allegati libretto
                attachments = []
                if hasattr(asset, 'libretto_fronte') and asset.libretto_fronte:
                    attachments.append(asset.libretto_fronte.path)
                if hasattr(asset, 'libretto_retro') and asset.libretto_retro:
                    attachments.append(asset.libretto_retro.path)
                
                subject = f"Richiesta Preventivo - {richiesta.titolo} - Automezzo {asset.targa}"
                
            elif asset and hasattr(asset, 'nome'):
                # Stabilimento
                template_name = 'richiesta_preventivo_stabilimento'
                context['stabilimento'] = asset
                attachments = []
                subject = f"Richiesta Preventivo - {richiesta.titolo} - Stabilimento {asset.nome}"
                
            else:
                # Generico
                template_name = 'richiesta_preventivo_generico'
                attachments = []
                subject = f"Richiesta Preventivo - {richiesta.titolo}"
            
            # Renderizza template
            try:
                html_content = render_to_string(f'email/{template_name}.html', context)
                text_content = render_to_string(f'email/{template_name}.txt', context)
            except:
                # Fallback se template non esiste
                html_content = f"""
                <h2>Richiesta Preventivo</h2>
                <p><strong>Titolo:</strong> {richiesta.titolo}</p>
                <p><strong>Fornitore:</strong> {fornitore.ragione_sociale}</p>
                <p><strong>Descrizione:</strong> {getattr(richiesta, 'descrizione', '')}</p>
                """
                text_content = f"Richiesta Preventivo: {richiesta.titolo}"
            
            # Invia email
            result = self.send_email(
                to=fornitore.email,
                subject=subject,
                content=text_content,
                html_content=html_content,
                attachments=attachments,
                source_object=richiesta,
                category='preventivi'
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Errore invio email preventivo: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 'PREVENTIVO_ERROR'
            }
    
    def create_template(self,
                       name: str,
                       subject: str,
                       content_html: str,
                       content_text: str = '',
                       category: str = 'generico',
                       variables: Dict = None) -> Dict[str, Any]:
        """
        Crea nuovo template email.
        """
        try:
            from django.utils.text import slugify
            
            slug = slugify(name)
            counter = 1
            original_slug = slug
            
            # Assicura unicità slug
            while EmailTemplate.objects.filter(slug=slug).exists():
                slug = f"{original_slug}-{counter}"
                counter += 1
            
            template = EmailTemplate.objects.create(
                name=name,
                slug=slug,
                subject=subject,
                content_html=content_html,
                content_text=content_text,
                category=category,
                available_variables=variables or {},
                created_by=self.user
            )
            
            return {
                'success': True,
                'template_id': str(template.id),
                'slug': template.slug,
                'message': 'Template creato con successo'
            }
            
        except Exception as e:
            logger.error(f"Errore creazione template: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 'TEMPLATE_ERROR'
            }
    
    def get_user_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Ottiene statistiche email utente.
        """
        if not self.config:
            return {
                'success': False,
                'error': 'Nessuna configurazione email trovata'
            }
        
        from django.utils import timezone
        from datetime import timedelta
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Statistiche dalla tabella EmailStats
        stats_qs = EmailStats.objects.filter(
            config=self.config,
            date__gte=start_date,
            date__lte=end_date
        )
        
        total_sent = sum(s.emails_sent for s in stats_qs)
        total_failed = sum(s.emails_failed for s in stats_qs)
        
        # Statistiche per categoria
        category_stats = {}
        for stat in stats_qs:
            for field_name in ['preventivi_sent', 'automezzi_sent', 'acquisti_sent']:
                category = field_name.replace('_sent', '')
                if category not in category_stats:
                    category_stats[category] = 0
                category_stats[category] += getattr(stat, field_name, 0)
        
        return {
            'success': True,
            'period_days': days,
            'total_sent': total_sent,
            'total_failed': total_failed,
            'success_rate': round((total_sent / (total_sent + total_failed) * 100), 2) if (total_sent + total_failed) > 0 else 0,
            'category_breakdown': category_stats,
            'daily_average': round(total_sent / days, 2) if days > 0 else 0
        }
    
    def test_configuration(self) -> Dict[str, Any]:
        """
        Testa configurazione email.
        """
        if not self.config:
            return {
                'success': False,
                'error': 'Nessuna configurazione email impostata'
            }
        
        # Test invio email di prova
        test_result = self.send_email(
            to=self.config.email_address,
            subject='Test Configurazione Email Management',
            content='Questo è un test della configurazione email.',
            html_content='<p>Questo è un <strong>test</strong> della configurazione email.</p>',
            category='sistema'
        )
        
        if test_result['success']:
            self.config.is_verified = True
            self.config.last_test_at = timezone.now()
            self.config.last_error = ''
            self.config.save()
        else:
            self.config.last_error = test_result['error']
            self.config.save()
        
        return test_result
    
    def _render_template(self, template_slug: str, context: Dict) -> Dict[str, Any]:
        """Renderizza template con contesto"""
        try:
            template = EmailTemplate.objects.get(slug=template_slug, is_active=True)
            rendered = template.render(context)
            
            # Aggiorna contatore utilizzi
            template.usage_count += 1
            template.save(update_fields=['usage_count'])
            
            return {
                'success': True,
                'subject': rendered['subject'],
                'html': rendered['html'],
                'text': rendered['text']
            }
            
        except EmailTemplate.DoesNotExist:
            return {
                'success': False,
                'error': f"Template '{template_slug}' non trovato",
                'code': 'TEMPLATE_NOT_FOUND'
            }
    
    def _send_with_user_config(self,
                              to: List[str],
                              subject: str,
                              content: str,
                              html_content: str,
                              attachments: List[str]) -> Dict[str, Any]:
        """Invia email con configurazione utente"""
        try:
            # Prepara messaggio
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.config.display_name} <{self.config.email_address}>"
            msg['To'] = ', '.join(to)
            
            # Contenuti
            if content:
                msg.attach(MIMEText(content, 'plain', 'utf-8'))
            if html_content:
                msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # Allegati
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        self._attach_file(msg, file_path)
            
            # Connessione SMTP
            if self.config.use_ssl:
                server = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port)
            else:
                server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
                if self.config.use_tls:
                    server.starttls()
            
            # Login e invio
            server.login(self.config.smtp_username, self.config.smtp_password)
            server.sendmail(self.config.email_address, to, msg.as_string())
            server.quit()
            
            return {
                'success': True,
                'message': 'Email inviata con configurazione utente',
                'method': 'user_config'
            }
            
        except Exception as e:
            logger.error(f"Errore invio con config utente: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 'USER_CONFIG_ERROR'
            }
    
    def _send_with_django_settings(self,
                                   to: List[str],
                                   subject: str,
                                   content: str,
                                   html_content: str,
                                   attachments: List[str]) -> Dict[str, Any]:
        """Invia email con configurazioni Django settings (compatibilità)"""
        try:
            # Usa Django EmailMessage per compatibilità con settings esistenti
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@management.local')
            
            email = DjangoEmailMessage(
                subject=subject,
                body=html_content or content,
                from_email=from_email,
                to=to
            )
            
            # Se c'è contenuto HTML
            if html_content:
                email.content_subtype = "html"
            
            # Allegati
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        email.attach_file(file_path)
            
            # Invia
            email.send()
            
            return {
                'success': True,
                'message': 'Email inviata con configurazione Django',
                'method': 'django_settings'
            }
            
        except Exception as e:
            logger.error(f"Errore invio con Django settings: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 'DJANGO_SETTINGS_ERROR'
            }
    
    def _attach_file(self, msg: MIMEMultipart, file_path: str):
        """Allega file al messaggio"""
        try:
            import mimetypes
            
            filename = os.path.basename(file_path)
            content_type, encoding = mimetypes.guess_type(file_path)
            
            if content_type is None or encoding is not None:
                content_type = 'application/octet-stream'
            
            main_type, sub_type = content_type.split('/', 1)
            
            with open(file_path, 'rb') as fp:
                attachment = MIMEBase(main_type, sub_type)
                attachment.set_payload(fp.read())
                encoders.encode_base64(attachment)
                attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {filename}'
                )
                msg.attach(attachment)
                
        except Exception as e:
            logger.warning(f"Impossibile allegare file {file_path}: {e}")
    
    def _log_sent_message(self,
                         to: List[str],
                         subject: str,
                         content: str,
                         html_content: str,
                         source_object: Any,
                         category: str,
                         template: str):
        """Log messaggio inviato"""
        try:
            EmailMessage.objects.create(
                sender_config=self.config,
                to_addresses=to,
                from_address=self.config.email_address if self.config else '',
                from_name=self.config.display_name if self.config else '',
                subject=subject,
                content_html=html_content or '',
                content_text=content or '',
                template_used=EmailTemplate.objects.filter(slug=template).first() if template else None,
                status='sent',
                direction='outgoing',
                delivery_attempts=1,
                content_type=ContentType.objects.get_for_model(source_object) if source_object else None,
                object_id=source_object.pk if source_object else None,
                related_description=f"{category} - {subject[:100]}",
                sent_at=timezone.now()
            )
        except Exception as e:
            logger.error(f"Errore log messaggio: {e}")
    
    def _update_stats(self, category: str):
        """Aggiorna statistiche"""
        if not self.config:
            return
        
        try:
            today = timezone.now().date()
            stats, created = EmailStats.objects.get_or_create(
                config=self.config,
                date=today,
                defaults={
                    'emails_sent': 0,
                    'emails_failed': 0,
                }
            )
            
            stats.emails_sent += 1
            
            # Aggiorna contatori per categoria
            if category == 'preventivi':
                stats.preventivi_sent += 1
            elif category == 'automezzi':
                stats.automezzi_sent += 1
            elif category == 'acquisti':
                stats.acquisti_sent += 1
            
            stats.save()
            
        except Exception as e:
            logger.error(f"Errore aggiornamento stats: {e}")

    def resend_message(self, message):
        """Reinvia un messaggio email"""
        try:
            # Usa gli stessi parametri del messaggio originale
            result = self.send_email(
                to=message.to_addresses,
                cc=message.cc_addresses or [],
                bcc=message.bcc_addresses or [],
                subject=message.subject,
                html_content=message.html_content,
                content=message.text_content,
                template=message.template.slug if message.template else None,
                context=message.context or {}
            )
            
            if result['success']:
                # Aggiorna il messaggio originale se necessario
                message.status = 'sent'
                message.sent_at = timezone.now()
                message.error_message = ''
                message.save()
            
            return result
            
        except Exception as e:
            logger.error(f"Errore reinvio messaggio: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Funzioni di convenienza per compatibilità con core.email_utils
def send_preventivo_email(richiesta, fornitore, asset=None):
    """
    Funzione compatibile con ProcurementEmailService.
    Utilizza il nuovo sistema mail di Management.
    """
    service = ManagementEmailService()
    return service.send_preventivo_email(richiesta, fornitore, asset)


def send_template_email(to: str, template: str, context: Dict = None, user: User = None):
    """
    Funzione di convenienza per invio email con template.
    """
    service = ManagementEmailService(user=user)
    return service.send_email(to=to, template=template, context=context)


def create_user_email_config(user: User,
                            email_address: str,
                            display_name: str,
                            smtp_username: str,
                            smtp_password: str) -> EmailConfiguration:
    """
    Crea configurazione email per utente.
    """
    config, created = EmailConfiguration.objects.get_or_create(
        user=user,
        defaults={
            'email_address': email_address,
            'display_name': display_name,
            'smtp_username': smtp_username,
            'smtp_password': smtp_password,
        }
    )
    
    if not created:
        # Aggiorna configurazione esistente
        config.email_address = email_address
        config.display_name = display_name
        config.smtp_username = smtp_username
        config.smtp_password = smtp_password
        config.save()
    
    return config