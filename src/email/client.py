# src/email/client.py
from abc import ABC, abstractmethod
from typing import List, Optional
from email.message import EmailMessage as StdEmailMessage

class EmailClient(ABC):
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the email server (IMAP/SMTP)."""
        pass

    @abstractmethod
    def fetch_unread_emails(self) -> List[StdEmailMessage]:
        """Fetch unread emails, ideally filtering PDFs or specific criteria."""
        pass

    @abstractmethod
    def send_email(self, to: str, subject: str, body: str, attachments: Optional[List[str]] = None) -> None:
        """Send an email with optional file attachments."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close any open connections."""
        pass