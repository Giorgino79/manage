"""
Management Command: Fetch Emails
================================

Recupera nuove email dai server IMAP configurati.

Usage:
    python manage.py fetch_emails
    python manage.py fetch_emails --user username
    python manage.py fetch_emails --all
    python manage.py fetch_emails --limit 100
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone
from mail.models import EmailConfiguration
from mail.services import ImapEmailService
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetch new emails from IMAP servers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Username of specific user to fetch emails for',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Fetch emails for all users with IMAP enabled',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of messages to fetch per folder (default: 50)',
        )
        parser.add_argument(
            '--folder',
            type=str,
            default='INBOX',
            help='Folder to fetch from (default: INBOX)',
        )

    def handle(self, *args, **options):
        username = options.get('user')
        fetch_all = options.get('all')
        limit = options.get('limit')
        folder = options.get('folder')

        # Determina configurazioni da processare
        if username:
            try:
                user = User.objects.get(username=username)
                configs = [user.mail_config]
                self.stdout.write(f"Fetching emails for user: {username}")
            except User.DoesNotExist:
                raise CommandError(f'User "{username}" does not exist')
            except EmailConfiguration.DoesNotExist:
                raise CommandError(f'User "{username}" has no email configuration')

        elif fetch_all:
            configs = EmailConfiguration.objects.filter(
                imap_enabled=True,
                is_active=True
            )
            self.stdout.write(f"Fetching emails for {configs.count()} users")

        else:
            raise CommandError('Please specify --user USERNAME or --all')

        # Fetch emails per ogni configurazione
        total_fetched = 0
        total_errors = 0

        for config in configs:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Processing: {config.email_address}")
            self.stdout.write(f"{'='*60}")

            try:
                # Verifica configurazione IMAP
                if not config.imap_enabled:
                    self.stdout.write(
                        self.style.WARNING(f"  IMAP not enabled for {config.email_address}")
                    )
                    continue

                if not config.imap_server:
                    self.stdout.write(
                        self.style.WARNING(f"  IMAP server not configured for {config.email_address}")
                    )
                    continue

                # Crea servizio IMAP
                service = ImapEmailService(config)

                # Connetti
                if not service.connect():
                    self.stdout.write(
                        self.style.ERROR(f"  Failed to connect to IMAP server")
                    )
                    total_errors += 1
                    continue

                self.stdout.write(self.style.SUCCESS(f"  ✓ Connected to {config.imap_server}"))

                # Fetch messaggi
                self.stdout.write(f"  Fetching from folder: {folder}")
                messages = service.fetch_new_messages(folder=folder, limit=limit)

                if messages:
                    self.stdout.write(f"  Found {len(messages)} new messages")

                    # Salva nel database
                    saved_count = service.sync_messages_to_db(messages)

                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ Saved {saved_count}/{len(messages)} messages")
                    )

                    total_fetched += saved_count

                    # Aggiorna timestamp sync
                    config.last_imap_sync = timezone.now()
                    config.last_imap_error = ''
                    config.save(update_fields=['last_imap_sync', 'last_imap_error'])

                else:
                    self.stdout.write("  No new messages")

                # Disconnetti
                service.disconnect()

            except Exception as e:
                logger.exception(f"Error fetching emails for {config.email_address}")
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Error: {str(e)}")
                )

                # Salva errore in config
                config.last_imap_error = str(e)
                config.save(update_fields=['last_imap_error'])

                total_errors += 1

        # Riepilogo finale
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("SUMMARY")
        self.stdout.write(f"{'='*60}")
        # Conta configurazioni (gestisce sia liste che QuerySet)
        total_configs = len(configs) if isinstance(configs, list) else configs.count()
        self.stdout.write(f"Total configurations processed: {total_configs}")
        self.stdout.write(self.style.SUCCESS(f"Total messages fetched: {total_fetched}"))

        if total_errors > 0:
            self.stdout.write(self.style.ERROR(f"Errors encountered: {total_errors}"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ All configurations processed successfully"))
