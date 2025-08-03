# src/email/godaddy_client.py
import imaplib
import smtplib
import ssl
import os
from typing import List, Optional
from email.message import EmailMessage
from email.parser import BytesParser
from email.policy import default
from email.header import decode_header
from email.utils import parseaddr
import base64

from .client import EmailClient


class GoDaddyEmailClient(EmailClient):
    def __init__(self):
        self.imap_host = os.getenv("EMAIL_HOST", "imap.secureserver.net")
        self.imap_port = int(os.getenv("EMAIL_PORT", 993))
        self.smtp_host = os.getenv("SMTP_HOST", "smtpout.secureserver.net")
        self.smtp_port = int(os.getenv("SMTP_PORT", 465))
        self.username = os.getenv("EMAIL_USER")
        self.password = os.getenv("EMAIL_PASS")

        self.imap = None
        self.smtp = None

    def connect(self) -> None:
        # Connect to IMAP
        self.imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
        self.imap.login(self.username, self.password)

        # Connect to SMTP
        context = ssl.create_default_context()
        self.smtp = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context)
        self.smtp.login(self.username, self.password)

    def list_inbox(self) -> List[dict]:
        """List all emails (metadata only: from, subject, date, UID)"""
        self.imap.select("INBOX")
        typ, data = self.imap.search(None, "ALL")
        emails = []
        for num in data[0].split():
            typ, msg_data = self.imap.fetch(num, '(RFC822)')
            if typ != "OK":
                continue
            raw_email = msg_data[0][1]
            msg = BytesParser(policy=default).parsebytes(raw_email)
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or 'utf-8')
            emails.append({
                "from": parseaddr(msg["From"])[1],
                "subject": subject,
                "date": msg["Date"],
                "uid": num.decode("utf-8")
            })
        return emails

    def fetch_unread_emails(self) -> List[EmailMessage]:
        """Fetch unread emails (not marked as Seen)"""
        self.imap.select("INBOX")
        status, messages = self.imap.search(None, '(UNSEEN)')
        email_list = []
        if status != "OK":
            return []
        for num in messages[0].split():
            typ, msg_data = self.imap.fetch(num, '(RFC822)')
            if typ != "OK":
                continue
            raw_email = msg_data[0][1]
            msg = BytesParser(policy=default).parsebytes(raw_email)
            email_list.append(msg)
        return email_list

    def extract_pdf_attachments(self, email_msg: EmailMessage, output_dir="attachments") -> List[str]:
        """Extract and save PDF attachments from a given email."""
        os.makedirs(output_dir, exist_ok=True)
        pdf_files = []
        for part in email_msg.walk():
            content_disposition = part.get("Content-Disposition", "")
            if part.get_content_maintype() == "application" and "pdf" in part.get_content_subtype():
                filename = part.get_filename()
                if filename:
                    filepath = os.path.join(output_dir, filename)
                    with open(filepath, "wb") as f:
                        f.write(part.get_payload(decode=True))
                    pdf_files.append(filepath)
            elif "attachment" in content_disposition:
                filename = part.get_filename()
                if filename and filename.endswith(".pdf"):
                    filepath = os.path.join(output_dir, filename)
                    with open(filepath, "wb") as f:
                        f.write(part.get_payload(decode=True))
                    pdf_files.append(filepath)
        return pdf_files

    def send_email(self, to: str, subject: str, body: str, attachments: Optional[List[str]] = None) -> None:
        """Send an email, optionally with attachments."""
        msg = EmailMessage()
        msg["From"] = self.username
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        if attachments:
            for path in attachments:
                with open(path, "rb") as f:
                    content = f.read()
                    filename = os.path.basename(path)
                    maintype, subtype = "application", "octet-stream"
                    if filename.endswith(".pdf"):
                        maintype, subtype = "application", "pdf"
                    msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)
        self.smtp.send_message(msg)

    def send_templated_response(self, to: str, template: str, **kwargs) -> None:
        """Send an email from a text template (e.g. Jinja-style formatting)."""
        subject = kwargs.get("subject", "No Subject")
        body = template.format(**kwargs)
        self.send_email(to, subject, body)

    def close(self) -> None:
        if self.imap:
            self.imap.logout()
        if self.smtp:
            self.smtp.quit()
