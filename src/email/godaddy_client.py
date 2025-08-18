# src/email/godaddy_client.py
import imaplib
import smtplib
import ssl
import os
import time
import logging
from typing import List, Optional, Dict, Any
from email.message import EmailMessage
from email.parser import BytesParser
from email.policy import default
from email.header import decode_header
from email.utils import parseaddr
import base64
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from .client import EmailClient


class ConnectionHealth(Enum):
    """Connection health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DISCONNECTED = "disconnected"


@dataclass
class ServerCapabilities:
    """Server capability information"""
    idle_supported: bool
    idle_timeout: Optional[int]
    max_connections: Optional[int]
    rate_limit_per_minute: Optional[int]
    supported_extensions: List[str]
    last_checked: datetime
    cache_expires: datetime


@dataclass
class ConnectionHealthStatus:
    """Connection health status information"""
    status: ConnectionHealth
    last_check: datetime
    response_time_ms: float
    error_count: int
    last_error: Optional[str]
    uptime_percentage: float


@dataclass
class RateLimitInfo:
    """Rate limiting information"""
    is_rate_limited: bool
    requests_per_minute: int
    current_usage: int
    reset_time: Optional[datetime]
    backoff_seconds: int


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
        
        # Capability detection and caching
        self._capabilities_cache: Optional[ServerCapabilities] = None
        self._connection_health: Optional[ConnectionHealthStatus] = None
        self._rate_limit_info: RateLimitInfo = RateLimitInfo(
            is_rate_limited=False,
            requests_per_minute=60,  # Default conservative limit
            current_usage=0,
            reset_time=None,
            backoff_seconds=0
        )
        
        # Health monitoring
        self._error_count = 0
        self._last_successful_operation = None
        self._connection_start_time = None
        
        # Logger for capability detection
        self.logger = logging.getLogger(__name__)

    def connect(self) -> None:
        """Enhanced connect method with capability detection"""
        try:
            start_time = time.time()
            self._connection_start_time = datetime.now()
            
            # Connect to IMAP
            self.imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            self.imap.login(self.username, self.password)

            # Connect to SMTP
            context = ssl.create_default_context()
            self.smtp = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context)
            self.smtp.login(self.username, self.password)
            
            # Detect server capabilities after successful connection
            self._detect_server_capabilities()
            
            # Update connection health
            response_time = (time.time() - start_time) * 1000
            self._update_connection_health(ConnectionHealth.HEALTHY, response_time)
            
            self.logger.info("Successfully connected to GoDaddy email servers")
            
        except Exception as e:
            self._update_connection_health(ConnectionHealth.DISCONNECTED, 0, str(e))
            self.logger.error(f"Failed to connect to GoDaddy email servers: {e}")
            raise

    def _detect_server_capabilities(self) -> ServerCapabilities:
        """Detect and cache server capabilities"""
        # Check if we have valid cached capabilities (24-hour cache)
        if (self._capabilities_cache and 
            datetime.now() < self._capabilities_cache.cache_expires):
            self.logger.debug("Using cached server capabilities")
            return self._capabilities_cache
        
        self.logger.info("Detecting server capabilities...")
        
        try:
            # Get IMAP capabilities
            typ, capabilities_data = self.imap.capability()
            if typ != 'OK':
                raise Exception("Failed to get IMAP capabilities")
            
            capabilities_str = capabilities_data[0].decode('utf-8')
            supported_extensions = capabilities_str.split()
            
            # Check for IDLE support
            idle_supported = 'IDLE' in supported_extensions
            idle_timeout = None
            
            if idle_supported:
                # Try to determine IDLE timeout (GoDaddy typically uses 29 minutes)
                idle_timeout = 29 * 60  # 29 minutes in seconds
                self.logger.info("IMAP IDLE support detected")
            else:
                self.logger.info("IMAP IDLE not supported, will use polling")
            
            # Detect GoDaddy-specific rate limits
            # GoDaddy typically allows 60 connections per minute
            rate_limit_per_minute = self._detect_rate_limits()
            
            # Create capabilities object
            now = datetime.now()
            capabilities = ServerCapabilities(
                idle_supported=idle_supported,
                idle_timeout=idle_timeout,
                max_connections=10,  # Conservative estimate for GoDaddy
                rate_limit_per_minute=rate_limit_per_minute,
                supported_extensions=supported_extensions,
                last_checked=now,
                cache_expires=now + timedelta(hours=24)  # 24-hour cache
            )
            
            # Cache the capabilities
            self._capabilities_cache = capabilities
            
            self.logger.info(f"Server capabilities detected: IDLE={idle_supported}, "
                           f"Rate limit={rate_limit_per_minute}/min, "
                           f"Extensions={len(supported_extensions)}")
            
            return capabilities
            
        except Exception as e:
            self.logger.error(f"Failed to detect server capabilities: {e}")
            # Return default capabilities on failure
            now = datetime.now()
            default_capabilities = ServerCapabilities(
                idle_supported=False,
                idle_timeout=None,
                max_connections=5,
                rate_limit_per_minute=30,  # Conservative default
                supported_extensions=[],
                last_checked=now,
                cache_expires=now + timedelta(hours=1)  # Shorter cache on failure
            )
            self._capabilities_cache = default_capabilities
            return default_capabilities

    def _detect_rate_limits(self) -> int:
        """Detect GoDaddy-specific rate limiting"""
        try:
            # Test with a series of quick operations to detect rate limits
            start_time = time.time()
            test_operations = 0
            
            # Perform lightweight operations to test rate limits
            for i in range(5):
                try:
                    # Use NOOP command for lightweight testing
                    typ, data = self.imap.noop()
                    if typ == 'OK':
                        test_operations += 1
                    time.sleep(0.1)  # Small delay between operations
                except Exception:
                    break
            
            elapsed_time = time.time() - start_time
            
            # Estimate rate limit based on successful operations
            if test_operations >= 5 and elapsed_time < 1.0:
                # If we can do 5 operations quickly, assume higher limit
                estimated_limit = 60
            else:
                # Conservative estimate
                estimated_limit = 30
            
            self.logger.debug(f"Rate limit detection: {test_operations} ops in {elapsed_time:.2f}s, "
                            f"estimated limit: {estimated_limit}/min")
            
            return estimated_limit
            
        except Exception as e:
            self.logger.warning(f"Rate limit detection failed: {e}")
            return 30  # Conservative default

    def get_server_capabilities(self) -> ServerCapabilities:
        """Get cached server capabilities, detecting if necessary"""
        if not self.imap:
            raise Exception("Not connected to IMAP server")
        
        return self._detect_server_capabilities()

    def test_idle_support(self) -> bool:
        """Test IMAP IDLE support with actual server interaction"""
        if not self.imap:
            raise Exception("Not connected to IMAP server")
        
        capabilities = self.get_server_capabilities()
        if not capabilities.idle_supported:
            return False
        
        try:
            # Select inbox for IDLE testing
            self.imap.select("INBOX")
            
            # Start IDLE command
            tag = self.imap._new_tag()
            self.imap.send(f'{tag} IDLE\r\n'.encode('ascii'))
            
            # Wait for IDLE response
            response = self.imap.readline()
            if b'+ idling' in response.lower() or b'+ waiting' in response.lower():
                # IDLE is working, send DONE to exit
                self.imap.send(b'DONE\r\n')
                # Read the completion response
                self.imap.readline()
                self.logger.info("IDLE support confirmed through testing")
                return True
            else:
                self.logger.warning("IDLE command not accepted by server")
                return False
                
        except Exception as e:
            self.logger.error(f"IDLE support test failed: {e}")
            return False

    def _update_connection_health(self, status: ConnectionHealth, response_time: float, error: Optional[str] = None):
        """Update connection health status"""
        now = datetime.now()
        
        if error:
            self._error_count += 1
        else:
            self._last_successful_operation = now
        
        # Calculate uptime percentage
        uptime_percentage = 100.0
        if self._connection_start_time:
            total_time = (now - self._connection_start_time).total_seconds()
            if total_time > 0:
                # Simple uptime calculation based on error frequency
                error_rate = self._error_count / max(1, total_time / 60)  # errors per minute
                uptime_percentage = max(0, 100 - (error_rate * 10))
        
        self._connection_health = ConnectionHealthStatus(
            status=status,
            last_check=now,
            response_time_ms=response_time,
            error_count=self._error_count,
            last_error=error,
            uptime_percentage=uptime_percentage
        )

    def get_connection_health(self) -> ConnectionHealthStatus:
        """Get current connection health status"""
        if not self._connection_health:
            # Perform a health check if no status exists
            self._perform_health_check()
        
        return self._connection_health

    def _perform_health_check(self) -> ConnectionHealthStatus:
        """Perform active connection health check"""
        if not self.imap or not self.smtp:
            self._update_connection_health(ConnectionHealth.DISCONNECTED, 0, "Not connected")
            return self._connection_health
        
        try:
            start_time = time.time()
            
            # Test IMAP connection
            typ, data = self.imap.noop()
            if typ != 'OK':
                raise Exception(f"IMAP health check failed: {data}")
            
            # Test SMTP connection
            status = self.smtp.noop()
            if status[0] != 250:
                raise Exception(f"SMTP health check failed: {status}")
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine health status based on response time
            if response_time < 1000:  # Less than 1 second
                health_status = ConnectionHealth.HEALTHY
            elif response_time < 5000:  # Less than 5 seconds
                health_status = ConnectionHealth.DEGRADED
            else:
                health_status = ConnectionHealth.UNHEALTHY
            
            self._update_connection_health(health_status, response_time)
            
        except Exception as e:
            self._update_connection_health(ConnectionHealth.UNHEALTHY, 0, str(e))
        
        return self._connection_health

    def handle_rate_limiting(self, retry_after: Optional[int] = None) -> None:
        """Handle rate limiting with exponential backoff"""
        if retry_after:
            backoff_seconds = retry_after
        else:
            # Exponential backoff: start with 1 second, max 60 seconds
            backoff_seconds = min(60, 2 ** min(self._rate_limit_info.current_usage // 10, 6))
        
        self._rate_limit_info = RateLimitInfo(
            is_rate_limited=True,
            requests_per_minute=self._rate_limit_info.requests_per_minute,
            current_usage=self._rate_limit_info.current_usage + 1,
            reset_time=datetime.now() + timedelta(seconds=backoff_seconds),
            backoff_seconds=backoff_seconds
        )
        
        self.logger.warning(f"Rate limit detected, backing off for {backoff_seconds} seconds")
        time.sleep(backoff_seconds)
        
        # Reset rate limit status after backoff
        self._rate_limit_info = RateLimitInfo(
            is_rate_limited=False,
            requests_per_minute=self._rate_limit_info.requests_per_minute,
            current_usage=0,
            reset_time=None,
            backoff_seconds=0
        )

    def get_rate_limit_info(self) -> RateLimitInfo:
        """Get current rate limiting information"""
        return self._rate_limit_info

    def _check_rate_limit_before_operation(self) -> None:
        """Check rate limits before performing operations"""
        if self._rate_limit_info.is_rate_limited:
            if self._rate_limit_info.reset_time and datetime.now() < self._rate_limit_info.reset_time:
                remaining_time = (self._rate_limit_info.reset_time - datetime.now()).total_seconds()
                self.logger.info(f"Rate limited, waiting {remaining_time:.1f} seconds")
                time.sleep(remaining_time)
        
        # Update usage counter
        self._rate_limit_info.current_usage += 1

    def list_inbox(self) -> List[dict]:
        """List all emails (metadata only: from, subject, date, UID)"""
        self._check_rate_limit_before_operation()
        
        try:
            start_time = time.time()
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
            
            # Update health status on successful operation
            response_time = (time.time() - start_time) * 1000
            self._update_connection_health(ConnectionHealth.HEALTHY, response_time)
            
            return emails
            
        except Exception as e:
            self._update_connection_health(ConnectionHealth.UNHEALTHY, 0, str(e))
            # Check if this might be a rate limiting error
            if "rate" in str(e).lower() or "limit" in str(e).lower():
                self.handle_rate_limiting()
            raise

    def fetch_unread_emails(self) -> List[EmailMessage]:
        """Fetch unread emails (not marked as Seen)"""
        self._check_rate_limit_before_operation()
        
        try:
            start_time = time.time()
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
            
            # Update health status on successful operation
            response_time = (time.time() - start_time) * 1000
            self._update_connection_health(ConnectionHealth.HEALTHY, response_time)
            
            return email_list
            
        except Exception as e:
            self._update_connection_health(ConnectionHealth.UNHEALTHY, 0, str(e))
            # Check if this might be a rate limiting error
            if "rate" in str(e).lower() or "limit" in str(e).lower():
                self.handle_rate_limiting()
            raise

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
        self._check_rate_limit_before_operation()
        
        try:
            start_time = time.time()
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
            
            # Update health status on successful operation
            response_time = (time.time() - start_time) * 1000
            self._update_connection_health(ConnectionHealth.HEALTHY, response_time)
            
        except Exception as e:
            self._update_connection_health(ConnectionHealth.UNHEALTHY, 0, str(e))
            # Check if this might be a rate limiting error
            if "rate" in str(e).lower() or "limit" in str(e).lower():
                self.handle_rate_limiting()
            raise

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
