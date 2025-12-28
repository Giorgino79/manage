"""
Mail Services
"""
from .email_service import ManagementEmailService
from .imap_service import ImapEmailService

__all__ = ['ManagementEmailService', 'ImapEmailService']
