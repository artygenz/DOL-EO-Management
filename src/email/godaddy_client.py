# src/email/godaddy_client.py
import imaplib
import smtplib
import ssl
import os
from typing import List, Optional
# Use absolute imports to avoid conflict with local email package
from email.message import EmailMessage
from email.parser import BytesParser
from email.policy import default
from email.header import decode_header
import base64

# Import parseaddr function directly to avoid module name conflict
import email.utils
parseaddr = email.utils.parseaddr

from .client import EmailClient


class GoDaddyEmailClient(EmailClient):
    def __init__(self):
        self.imap_host = os.getenv("EMAIL_HOST", "imap.secureserver.net")
        self.imap_port = int(os.getenv("EMAIL_PORT", 993))
        self.smtp_host = os.getenv("SMTP_HOST", "i")
        self.smtp_port = int(os.getenv("SMTP_PORT", 465))
        self.username = os.getenv("EMAIL_USER")
        self.password = os.getenv("EMAIL_PASS")

        self.imap = None
        self.smtp = None

    def connect(self) -> None:
        # Connect to IMAP
        self.imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
        self.imap.login(self.username, self.password)

        # Connect to SMTP with GoDaddy-specific handling
        try:
            context = ssl.create_default_context()
            # Use SMTP_SSL for GoDaddy with port 465
            self.smtp = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context, timeout=30)
            # GoDaddy servers sometimes send multi-line responses, handle them properly
            self.smtp.ehlo()
            self.smtp.login(self.username, self.password)
        except Exception as e:
            # If SSL connection fails, try regular SMTP with STARTTLS
            try:
                self.smtp = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                self.smtp.ehlo()
                self.smtp.starttls(context=context)
                self.smtp.ehlo()
                self.smtp.login(self.username, self.password)
            except Exception as e2:
                raise Exception(f"SMTP connection failed: {e2}")

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

    def send_email(
        self, 
        to: str, 
        subject: str, 
        body_text: str, 
        body_html: Optional[str] = None,
        attachments: Optional[List[dict]] = None
    ) -> None:
        """
        Send an email with support for HTML content and attachments.
        
        Parameters
        ----------
        to : str
            Recipient email address
        subject : str
            Email subject line
        body_text : str
            Plain text email body
        body_html : Optional[str]
            HTML email body (optional)
        attachments : Optional[List[dict]]
            List of attachment dictionaries with keys:
            - filename: str
            - content_type: str  
            - data: bytes
        """
        # Create a new SMTP connection for each email to avoid connection issues
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context, timeout=30) as smtp:
                # Handle GoDaddy's multi-line response properly
                smtp.ehlo()
                smtp.login(self.username, self.password)
                
                msg = EmailMessage()
                msg["From"] = self.username
                msg["To"] = to
                msg["Subject"] = subject
                
                # Set the email content
                if body_html:
                    # If HTML is provided, create a multipart message
                    msg.set_content(body_text)
                    msg.add_alternative(body_html, subtype='html')
                else:
                    # Plain text only
                    msg.set_content(body_text)
                
                # Add attachments if provided
                if attachments:
                    for attachment in attachments:
                        filename = attachment.get('filename', 'attachment')
                        content_type = attachment.get('content_type', 'application/octet-stream')
                        data = attachment.get('data', b'')
                        
                        # Parse content type
                        if '/' in content_type:
                            maintype, subtype = content_type.split('/', 1)
                        else:
                            maintype, subtype = 'application', 'octet-stream'
                        
                        msg.add_attachment(
                            data, 
                            maintype=maintype, 
                            subtype=subtype, 
                            filename=filename
                        )
                
                # Send the email
                smtp.send_message(msg)
                
        except Exception as e:
            raise Exception(f"Failed to send email: {e}")

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
