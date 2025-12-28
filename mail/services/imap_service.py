"""
IMAP Email Service - Ricezione e sincronizzazione email
=======================================================

Servizio per ricevere email da server IMAP e sincronizzare con il database locale.
Supporta Gmail, Outlook, e altri provider IMAP standard.
"""

import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.files.base import ContentFile
from django.db import transaction
import re
import hashlib

logger = logging.getLogger(__name__)


class ImapEmailService:
    """
    Servizio per ricezione email via IMAP

    Usage:
        service = ImapEmailService(email_config)
        service.connect()
        messages = service.fetch_new_messages()
        service.disconnect()
    """

    def __init__(self, email_config):
        """
        Args:
            email_config: Istanza di EmailConfiguration
        """
        self.config = email_config
        self.imap = None
        self.connected = False

    def connect(self) -> bool:
        """
        Connette al server IMAP

        Returns:
            True se connessione riuscita, False altrimenti
        """
        try:
            # Determina se usare SSL o TLS
            if self.config.imap_use_ssl:
                self.imap = imaplib.IMAP4_SSL(
                    self.config.imap_server,
                    self.config.imap_port
                )
            else:
                self.imap = imaplib.IMAP4(
                    self.config.imap_server,
                    self.config.imap_port
                )

                # Se TLS, upgrade connection
                if self.config.imap_use_tls:
                    self.imap.starttls()

            # Login - usa credenziali IMAP o fallback a SMTP
            username = self.config.imap_username or self.config.smtp_username
            password = self.config.imap_password or self.config.smtp_password

            self.imap.login(username, password)

            self.connected = True
            logger.info(f"IMAP connected: {self.config.email_address}")
            return True

        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            self.config.last_imap_error = str(e)
            self.config.save(update_fields=['last_imap_error'])
            return False

    def disconnect(self):
        """Disconnette dal server IMAP"""
        if self.imap and self.connected:
            try:
                self.imap.close()
                self.imap.logout()
            except:
                pass
            self.connected = False
            logger.info(f"IMAP disconnected: {self.config.email_address}")

    def list_folders(self) -> List[str]:
        """
        Lista tutte le cartelle IMAP

        Returns:
            Lista nomi cartelle
        """
        if not self.connected:
            raise Exception("Not connected to IMAP server")

        folders = []
        try:
            status, folder_list = self.imap.list()
            if status == 'OK':
                for folder in folder_list:
                    # Parse folder name from IMAP response
                    # Format: (\\HasNoChildren) "/" "INBOX"
                    parts = folder.decode().split('"')
                    if len(parts) >= 3:
                        folder_name = parts[-2]
                        folders.append(folder_name)

            logger.info(f"Found {len(folders)} IMAP folders")
            return folders

        except Exception as e:
            logger.error(f"Error listing folders: {e}")
            return []

    def fetch_new_messages(self, folder='INBOX', limit=50) -> List[Dict]:
        """
        Recupera nuovi messaggi da una cartella

        Args:
            folder: Nome cartella IMAP (default: INBOX)
            limit: Numero massimo di messaggi da recuperare

        Returns:
            Lista dizionari con dati email
        """
        if not self.connected:
            raise Exception("Not connected to IMAP server")

        messages = []

        try:
            # Seleziona cartella
            status, count = self.imap.select(folder, readonly=False)
            if status != 'OK':
                logger.error(f"Cannot select folder: {folder}")
                return messages

            # Cerca messaggi non letti
            # Puoi anche usare 'ALL' per tutti o '(UNSEEN)' solo non letti
            status, message_ids = self.imap.search(None, 'UNSEEN')

            if status != 'OK':
                logger.warning(f"No new messages in {folder}")
                return messages

            # Processa messaggi (ultimi 'limit')
            ids = message_ids[0].split()
            ids = ids[-limit:] if len(ids) > limit else ids

            logger.info(f"Found {len(ids)} new messages in {folder}")

            for msg_id in ids:
                try:
                    msg_data = self._fetch_message(msg_id, folder)
                    if msg_data:
                        messages.append(msg_data)
                except Exception as e:
                    logger.error(f"Error fetching message {msg_id}: {e}")
                    continue

            return messages

        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            return messages

    def _fetch_message(self, msg_id: bytes, folder: str) -> Optional[Dict]:
        """
        Recupera singolo messaggio

        Args:
            msg_id: ID messaggio IMAP
            folder: Cartella corrente

        Returns:
            Dizionario con dati messaggio
        """
        try:
            # Fetch messaggio completo
            status, msg_data = self.imap.fetch(msg_id, '(RFC822)')

            if status != 'OK':
                logger.error(f"Cannot fetch message {msg_id}")
                return None

            # Parse email
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)

            # Estrai dati
            subject = self._decode_header(email_message.get('Subject', ''))
            from_addr = self._decode_header(email_message.get('From', ''))
            to_addr = self._decode_header(email_message.get('To', ''))
            cc_addr = self._decode_header(email_message.get('Cc', ''))
            date_str = email_message.get('Date')
            message_id_header = email_message.get('Message-ID', '')

            # Parse data
            received_at = None
            if date_str:
                try:
                    received_at = parsedate_to_datetime(date_str)
                    # Converti a timezone-aware
                    if received_at.tzinfo is None:
                        received_at = timezone.make_aware(received_at)
                except:
                    received_at = timezone.now()
            else:
                received_at = timezone.now()

            # Estrai corpo email
            body_html, body_text, attachments = self._extract_body_and_attachments(email_message)

            return {
                'server_uid': msg_id.decode(),
                'message_id': message_id_header,
                'folder': folder,
                'subject': subject,
                'from_address': from_addr,
                'to_addresses': [addr.strip() for addr in to_addr.split(',') if addr.strip()],
                'cc_addresses': [addr.strip() for addr in cc_addr.split(',') if addr.strip()] if cc_addr else [],
                'body_html': body_html,
                'body_text': body_text,
                'received_at': received_at,
                'attachments': attachments,
                'has_attachments': len(attachments) > 0,
                'is_read': False,  # Appena ricevuto
            }

        except Exception as e:
            logger.error(f"Error parsing message: {e}")
            return None

    def _decode_header(self, header: str) -> str:
        """Decodifica header email (gestisce encoding)"""
        if not header:
            return ''

        decoded_parts = []
        for part, encoding in decode_header(header):
            if isinstance(part, bytes):
                try:
                    decoded_parts.append(part.decode(encoding or 'utf-8', errors='replace'))
                except:
                    decoded_parts.append(part.decode('utf-8', errors='replace'))
            else:
                decoded_parts.append(str(part))

        return ' '.join(decoded_parts)

    def _extract_body_and_attachments(self, email_message) -> Tuple[str, str, List[Dict]]:
        """
        Estrae corpo email e allegati

        Returns:
            (body_html, body_text, attachments_list)
        """
        body_html = ''
        body_text = ''
        attachments = []

        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))

                # Corpo email
                if content_type == 'text/plain' and 'attachment' not in content_disposition:
                    try:
                        body_text = part.get_payload(decode=True).decode('utf-8', errors='replace')
                    except:
                        body_text = str(part.get_payload())

                elif content_type == 'text/html' and 'attachment' not in content_disposition:
                    try:
                        body_html = part.get_payload(decode=True).decode('utf-8', errors='replace')
                    except:
                        body_html = str(part.get_payload())

                # Allegati
                elif 'attachment' in content_disposition or part.get_filename():
                    filename = part.get_filename()
                    if filename:
                        filename = self._decode_header(filename)

                        # Estrai contenuto allegato
                        payload = part.get_payload(decode=True)
                        if payload:
                            attachments.append({
                                'filename': filename,
                                'content_type': content_type,
                                'size': len(payload),
                                'content': payload,
                            })
        else:
            # Email non multipart (solo testo)
            content_type = email_message.get_content_type()
            payload = email_message.get_payload(decode=True)

            if payload:
                if content_type == 'text/html':
                    body_html = payload.decode('utf-8', errors='replace')
                else:
                    body_text = payload.decode('utf-8', errors='replace')

        # Se non c'è body_text, estrai da HTML
        if not body_text and body_html:
            body_text = self._html_to_text(body_html)

        return body_html, body_text, attachments

    def _html_to_text(self, html: str) -> str:
        """Converti HTML a testo semplice (rudimentale)"""
        # Rimuovi tag HTML
        text = re.sub(r'<[^>]+>', '', html)
        # Rimuovi spazi multipli
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def mark_as_read(self, msg_id: bytes):
        """Segna messaggio come letto sul server"""
        try:
            self.imap.store(msg_id, '+FLAGS', '\\Seen')
        except Exception as e:
            logger.error(f"Error marking message as read: {e}")

    def mark_as_unread(self, msg_id: bytes):
        """Segna messaggio come non letto sul server"""
        try:
            self.imap.store(msg_id, '-FLAGS', '\\Seen')
        except Exception as e:
            logger.error(f"Error marking message as unread: {e}")

    def move_to_folder(self, msg_id: bytes, dest_folder: str):
        """Sposta messaggio in altra cartella"""
        try:
            # Copia in destinazione
            self.imap.copy(msg_id, dest_folder)
            # Marca per eliminazione dalla cartella corrente
            self.imap.store(msg_id, '+FLAGS', '\\Deleted')
            # Expunge per rimuovere definitivamente
            self.imap.expunge()
        except Exception as e:
            logger.error(f"Error moving message: {e}")

    def delete_message(self, msg_id: bytes):
        """Elimina messaggio (sposta in Trash o elimina)"""
        try:
            self.imap.store(msg_id, '+FLAGS', '\\Deleted')
            self.imap.expunge()
        except Exception as e:
            logger.error(f"Error deleting message: {e}")

    def sync_messages_to_db(self, messages: List[Dict]):
        """
        Salva messaggi ricevuti nel database

        Args:
            messages: Lista messaggi da salvare
        """
        from mail.models import EmailMessage, EmailAttachment, EmailFolder

        saved_count = 0

        for msg_data in messages:
            try:
                with transaction.atomic():
                    # Verifica se messaggio già esiste (per Message-ID)
                    if msg_data['message_id']:
                        existing = EmailMessage.objects.filter(
                            message_id=msg_data['message_id'],
                            sender_config=self.config
                        ).first()

                        if existing:
                            logger.debug(f"Message already exists: {msg_data['subject']}")
                            continue

                    # Trova o crea cartella
                    folder, _ = EmailFolder.objects.get_or_create(
                        config=self.config,
                        name=msg_data['folder'],
                        defaults={
                            'folder_type': 'inbox' if msg_data['folder'].upper() == 'INBOX' else 'custom'
                        }
                    )

                    # Crea messaggio
                    email_msg = EmailMessage.objects.create(
                        sender_config=self.config,
                        folder=folder,
                        direction='incoming',
                        status='received',

                        # Identificatori
                        message_id=msg_data['message_id'],
                        server_uid=msg_data['server_uid'],

                        # Contenuto
                        subject=msg_data['subject'],
                        from_address=msg_data['from_address'],
                        to_addresses=msg_data['to_addresses'],
                        cc_addresses=msg_data['cc_addresses'],
                        content_html=msg_data['body_html'],
                        content_text=msg_data['body_text'],

                        # Metadata
                        has_attachments=msg_data['has_attachments'],
                        is_read=msg_data['is_read'],
                        received_at=msg_data['received_at'],
                    )

                    # Salva allegati
                    for att_data in msg_data['attachments']:
                        # Calcola hash
                        file_hash = hashlib.sha256(att_data['content']).hexdigest()

                        # Crea allegato
                        attachment = EmailAttachment(
                            message=email_msg,
                            filename=att_data['filename'],
                            content_type=att_data['content_type'],
                            size=att_data['size'],
                            file_hash=file_hash,
                        )

                        # Salva file
                        attachment.file.save(
                            att_data['filename'],
                            ContentFile(att_data['content']),
                            save=True
                        )

                    # Aggiorna contatori cartella
                    folder.total_messages = folder.emailmessage_set.count()
                    folder.unread_messages = folder.emailmessage_set.filter(is_read=False).count()
                    folder.save(update_fields=['total_messages', 'unread_messages'])

                    saved_count += 1
                    logger.info(f"Saved message: {email_msg.subject}")

            except Exception as e:
                logger.error(f"Error saving message to DB: {e}")
                continue

        logger.info(f"Saved {saved_count}/{len(messages)} messages to database")
        return saved_count

    def __enter__(self):
        """Context manager support"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support"""
        self.disconnect()
