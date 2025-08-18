# src/email/content_extractor.py
import os
import re
import hashlib
import tempfile
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
import html
import bleach
from pathlib import Path
import mimetypes
import uuid

logger = logging.getLogger(__name__)


@dataclass
class EmailHeaders:
    """Structured email header information"""
    message_id: str
    sender: str
    sender_name: Optional[str]
    recipients: List[str]
    cc_recipients: List[str]
    bcc_recipients: List[str]
    subject: str
    date: datetime
    reply_to: Optional[str]
    in_reply_to: Optional[str]
    references: List[str]
    thread_topic: Optional[str]
    priority: Optional[str]
    content_type: str
    encoding: Optional[str]
    custom_headers: Dict[str, str]


@dataclass
class ThreadAnalysis:
    """Email thread relationship analysis"""
    thread_id: str
    is_reply: bool
    is_forward: bool
    parent_message_id: Optional[str]
    thread_depth: int
    conversation_participants: Set[str]
    thread_subject: str
    original_subject: str
    reply_chain_length: int


@dataclass
class ValidatedAttachment:
    """Validated email attachment with security metadata"""
    filename: str
    original_filename: str
    content_type: str
    size_bytes: int
    content_hash: str
    is_safe: bool
    security_scan_result: Optional[str]
    temporary_path: Optional[str]
    extraction_timestamp: datetime
    expires_at: datetime
    metadata: Dict[str, Any]


@dataclass
class ExtractedContent:
    """Complete extracted email content"""
    headers: EmailHeaders
    plain_text: str
    html_content: Optional[str]
    sanitized_html: Optional[str]
    attachments: List[ValidatedAttachment]
    thread_analysis: ThreadAnalysis
    content_hash: str
    extraction_metadata: Dict[str, Any]
    security_flags: List[str]


class ContentExtractionError(Exception):
    """Content extraction specific errors"""
    pass


class AttachmentSecurityError(Exception):
    """Attachment security validation errors"""
    pass


class EnhancedContentExtractor:
    """Enhanced email content extraction with security and thread analysis"""
    
    # Allowed HTML tags for sanitization
    ALLOWED_HTML_TAGS = [
        'p', 'br', 'div', 'span', 'strong', 'b', 'em', 'i', 'u',
        'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'blockquote', 'pre', 'code', 'table', 'tr', 'td', 'th',
        'thead', 'tbody', 'tfoot'
    ]
    
    # Allowed HTML attributes
    ALLOWED_HTML_ATTRIBUTES = {
        '*': ['class', 'id'],
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'table': ['border', 'cellpadding', 'cellspacing'],
    }
    
    # Dangerous file extensions
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs',
        '.js', '.jar', '.app', '.deb', '.pkg', '.dmg', '.msi'
    }
    
    # Maximum attachment size (50MB)
    MAX_ATTACHMENT_SIZE = 50 * 1024 * 1024
    
    def __init__(self, temp_dir: Optional[str] = None, cleanup_interval_hours: int = 24):
        """
        Initialize the enhanced content extractor
        
        Args:
            temp_dir: Directory for temporary attachment storage
            cleanup_interval_hours: Hours after which temp files are cleaned up
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.cleanup_interval = timedelta(hours=cleanup_interval_hours)
        self.extraction_stats = {
            'total_extractions': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'security_violations': 0,
            'attachments_processed': 0
        }
        
        # Ensure temp directory exists
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Enhanced content extractor initialized with temp dir: {self.temp_dir}")
    
    def extract_email_content(self, email_msg: EmailMessage) -> ExtractedContent:
        """
        Extract complete content from email message with security validation
        
        Args:
            email_msg: Email message to extract content from
            
        Returns:
            ExtractedContent: Complete extracted and validated content
            
        Raises:
            ContentExtractionError: If extraction fails
        """
        try:
            self.extraction_stats['total_extractions'] += 1
            extraction_start = datetime.now()
            
            logger.debug(f"Starting content extraction for message: {email_msg.get('Message-ID', 'Unknown')}")
            
            # Extract structured headers
            headers = self._extract_email_headers(email_msg)
            
            # Extract and sanitize content
            plain_text, html_content, sanitized_html = self._extract_and_sanitize_content(email_msg)
            
            # Analyze thread relationships
            try:
                thread_analysis = self._analyze_email_threading(email_msg, headers)
            except Exception as e:
                logger.warning(f"Thread analysis failed, using fallback: {e}")
                # Create fallback thread analysis
                thread_analysis = ThreadAnalysis(
                    thread_id=headers.message_id,
                    is_reply=False,
                    is_forward=False,
                    parent_message_id=None,
                    thread_depth=0,
                    conversation_participants={headers.sender},
                    thread_subject=headers.subject,
                    original_subject=headers.subject,
                    reply_chain_length=0
                )
            
            # Extract and validate attachments
            attachments = self._extract_and_validate_attachments(email_msg)
            
            # Calculate content hash for deduplication
            content_hash = self._calculate_content_hash(plain_text, headers.message_id)
            
            # Collect security flags
            security_flags = self._collect_security_flags(email_msg, attachments)
            
            # Create extraction metadata
            extraction_metadata = {
                'extraction_timestamp': extraction_start,
                'extraction_duration_ms': (datetime.now() - extraction_start).total_seconds() * 1000,
                'extractor_version': '1.0.0',
                'content_length': len(plain_text),
                'attachment_count': len(attachments),
                'thread_depth': thread_analysis.thread_depth,
                'security_flags_count': len(security_flags)
            }
            
            extracted_content = ExtractedContent(
                headers=headers,
                plain_text=plain_text,
                html_content=html_content,
                sanitized_html=sanitized_html,
                attachments=attachments,
                thread_analysis=thread_analysis,
                content_hash=content_hash,
                extraction_metadata=extraction_metadata,
                security_flags=security_flags
            )
            
            self.extraction_stats['successful_extractions'] += 1
            self.extraction_stats['attachments_processed'] += len(attachments)
            
            logger.info(f"Successfully extracted content from message {headers.message_id}")
            return extracted_content
            
        except Exception as e:
            self.extraction_stats['failed_extractions'] += 1
            logger.error(f"Content extraction failed: {e}")
            raise ContentExtractionError(f"Failed to extract email content: {e}") from e
    
    def _extract_email_headers(self, email_msg: EmailMessage) -> EmailHeaders:
        """Extract and parse structured email headers"""
        try:
            # Decode subject
            subject = self._decode_header_value(email_msg.get('Subject', ''))
            
            # Parse sender information
            sender_raw = email_msg.get('From', '')
            sender_name, sender_email = parseaddr(sender_raw)
            sender_name = self._decode_header_value(sender_name) if sender_name else None
            
            # Parse recipients
            recipients = self._parse_address_list(email_msg.get('To', ''))
            cc_recipients = self._parse_address_list(email_msg.get('Cc', ''))
            bcc_recipients = self._parse_address_list(email_msg.get('Bcc', ''))
            
            # Parse date
            date_str = email_msg.get('Date')
            try:
                date = parsedate_to_datetime(date_str) if date_str else datetime.now()
            except (ValueError, TypeError):
                date = datetime.now()
                logger.warning(f"Could not parse date '{date_str}', using current time")
            
            # Parse threading headers
            in_reply_to = email_msg.get('In-Reply-To')
            references = self._parse_references(email_msg.get('References', ''))
            
            # Extract custom headers (X- headers and other important ones)
            custom_headers = {}
            for header_name, header_value in email_msg.items():
                if (header_name.startswith('X-') or 
                    header_name in ['List-ID', 'List-Unsubscribe', 'Precedence', 'Auto-Submitted']):
                    custom_headers[header_name] = self._decode_header_value(header_value)
            
            return EmailHeaders(
                message_id=email_msg.get('Message-ID', f"generated-{uuid.uuid4()}"),
                sender=sender_email,
                sender_name=sender_name,
                recipients=recipients,
                cc_recipients=cc_recipients,
                bcc_recipients=bcc_recipients,
                subject=subject,
                date=date,
                reply_to=email_msg.get('Reply-To'),
                in_reply_to=in_reply_to,
                references=references,
                thread_topic=email_msg.get('Thread-Topic'),
                priority=email_msg.get('X-Priority') or email_msg.get('Priority'),
                content_type=email_msg.get_content_type(),
                encoding=email_msg.get_content_charset(),
                custom_headers=custom_headers
            )
            
        except Exception as e:
            logger.error(f"Header extraction failed: {e}")
            raise ContentExtractionError(f"Failed to extract email headers: {e}") from e
    
    def _decode_header_value(self, header_value: str) -> str:
        """Decode RFC 2047 encoded header values"""
        if not header_value:
            return ""
        
        try:
            decoded_parts = decode_header(header_value)
            decoded_string = ""
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_string += part.decode(encoding)
                    else:
                        # Try common encodings
                        for enc in ['utf-8', 'latin-1', 'ascii']:
                            try:
                                decoded_string += part.decode(enc)
                                break
                            except UnicodeDecodeError:
                                continue
                        else:
                            # If all fail, use error handling
                            decoded_string += part.decode('utf-8', errors='replace')
                else:
                    decoded_string += str(part)
            
            return decoded_string.strip()
            
        except Exception as e:
            logger.warning(f"Header decoding failed for '{header_value}': {e}")
            return str(header_value)
    
    def _parse_address_list(self, address_string: str) -> List[str]:
        """Parse comma-separated email address list"""
        if not address_string:
            return []
        
        addresses = []
        try:
            # Split by comma and parse each address
            for addr in address_string.split(','):
                addr = addr.strip()
                if addr:
                    _, email = parseaddr(addr)
                    if email and '@' in email:
                        addresses.append(email)
        except Exception as e:
            logger.warning(f"Address parsing failed for '{address_string}': {e}")
        
        return addresses
    
    def _parse_references(self, references_string: str) -> List[str]:
        """Parse References header into list of message IDs"""
        if not references_string:
            return []
        
        # References are space-separated message IDs in angle brackets
        references = []
        try:
            # Find all message IDs in angle brackets
            message_ids = re.findall(r'<([^>]+)>', references_string)
            references.extend(message_ids)
        except Exception as e:
            logger.warning(f"References parsing failed for '{references_string}': {e}")
        
        return references 
   
    def _extract_and_sanitize_content(self, email_msg: EmailMessage) -> Tuple[str, Optional[str], Optional[str]]:
        """Extract and sanitize email content (plain text and HTML)"""
        plain_text = ""
        html_content = None
        sanitized_html = None
        
        try:
            # Walk through email parts
            for part in email_msg.walk():
                content_type = part.get_content_type()
                content_disposition = part.get('Content-Disposition', '')
                
                # Skip attachments
                if 'attachment' in content_disposition:
                    continue
                
                if content_type == 'text/plain':
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        try:
                            text = payload.decode(charset)
                        except UnicodeDecodeError:
                            text = payload.decode('utf-8', errors='replace')
                        
                        # Clean and normalize plain text
                        plain_text += self._clean_plain_text(text)
                
                elif content_type == 'text/html':
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        try:
                            html = payload.decode(charset)
                        except UnicodeDecodeError:
                            html = payload.decode('utf-8', errors='replace')
                        
                        html_content = html
                        # Sanitize HTML content
                        sanitized_html = self._sanitize_html_content(html)
                        
                        # If no plain text, extract from HTML
                        if not plain_text:
                            plain_text = self._html_to_plain_text(sanitized_html)
            
            # If still no content, try to get from main message
            if not plain_text and not html_content:
                try:
                    content = email_msg.get_content()
                    if isinstance(content, str):
                        if email_msg.get_content_type() == 'text/html':
                            html_content = content
                            sanitized_html = self._sanitize_html_content(content)
                            plain_text = self._html_to_plain_text(sanitized_html)
                        else:
                            plain_text = self._clean_plain_text(content)
                except Exception as e:
                    logger.warning(f"Failed to extract main content: {e}")
            
            return plain_text.strip(), html_content, sanitized_html
            
        except Exception as e:
            logger.error(f"Content extraction and sanitization failed: {e}")
            raise ContentExtractionError(f"Failed to extract and sanitize content: {e}") from e
    
    def _clean_plain_text(self, text: str) -> str:
        """Clean and normalize plain text content"""
        if not text:
            return ""
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive whitespace while preserving structure
        lines = []
        for line in text.split('\n'):
            # Strip trailing whitespace but preserve leading for indentation
            line = line.rstrip()
            lines.append(line)
        
        # Join lines and normalize multiple blank lines to single
        text = '\n'.join(lines)
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        
        # Decode HTML entities that might be in plain text
        text = html.unescape(text)
        
        return text
    
    def _sanitize_html_content(self, html_content: str) -> str:
        """Sanitize HTML content to remove dangerous elements"""
        if not html_content:
            return ""
        
        try:
            # Use bleach to sanitize HTML
            sanitized = bleach.clean(
                html_content,
                tags=self.ALLOWED_HTML_TAGS,
                attributes=self.ALLOWED_HTML_ATTRIBUTES,
                strip=True,
                strip_comments=True
            )
            
            # Additional security: remove any remaining script-like content
            sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
            sanitized = re.sub(r'vbscript:', '', sanitized, flags=re.IGNORECASE)
            sanitized = re.sub(r'data:', '', sanitized, flags=re.IGNORECASE)
            
            return sanitized
            
        except Exception as e:
            logger.error(f"HTML sanitization failed: {e}")
            # Return empty string if sanitization fails for security
            return ""
    
    def _html_to_plain_text(self, html_content: str) -> str:
        """Convert HTML content to plain text"""
        if not html_content:
            return ""
        
        try:
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', html_content)
            
            # Decode HTML entities
            text = html.unescape(text)
            
            # Clean up whitespace
            text = self._clean_plain_text(text)
            
            return text
            
        except Exception as e:
            logger.warning(f"HTML to plain text conversion failed: {e}")
            return ""
    
    def _analyze_email_threading(self, email_msg: EmailMessage, headers: EmailHeaders) -> ThreadAnalysis:
        """Analyze email thread relationships with enhanced thread analyzer integration"""
        try:
            # Try to use enhanced thread analyzer if available
            try:
                from .thread_analyzer import EmailThreadAnalyzer
                if not hasattr(self, '_thread_analyzer'):
                    self._thread_analyzer = EmailThreadAnalyzer(conversation_cache_size=100)
                
                # Use enhanced thread analysis
                enhanced_analysis = self._thread_analyzer.analyze_email_thread(email_msg, headers)
                logger.debug(f"Using enhanced thread analysis for {headers.message_id}")
                return enhanced_analysis
                
            except ImportError:
                logger.debug("Enhanced thread analyzer not available, using basic analysis")
            except Exception as e:
                logger.warning(f"Enhanced thread analysis failed, falling back to basic: {e}")
            
            # Fallback to basic thread analysis
            return self._basic_thread_analysis(email_msg, headers)
            
        except Exception as e:
            logger.error(f"Thread analysis failed: {e}")
            # Return minimal thread analysis on failure
            return ThreadAnalysis(
                thread_id=headers.message_id,
                is_reply=False,
                is_forward=False,
                parent_message_id=None,
                thread_depth=0,
                conversation_participants={headers.sender},
                thread_subject=headers.subject,
                original_subject=headers.subject,
                reply_chain_length=0
            )
    
    def _basic_thread_analysis(self, email_msg: EmailMessage, headers: EmailHeaders) -> ThreadAnalysis:
        """Basic thread analysis implementation"""
        # Determine if this is a reply or forward
        is_reply = bool(headers.in_reply_to or headers.references)
        is_forward = 'fwd:' in headers.subject.lower() or 'fw:' in headers.subject.lower()
        
        # Generate thread ID
        if headers.references:
            # Use first reference as thread root
            thread_id = headers.references[0]
        elif headers.in_reply_to:
            thread_id = headers.in_reply_to
        else:
            # New thread
            thread_id = headers.message_id
        
        # Calculate thread depth
        thread_depth = len(headers.references) if headers.references else 0
        if headers.in_reply_to and not headers.references:
            thread_depth = 1
        
        # Extract conversation participants
        participants = set()
        participants.add(headers.sender)
        participants.update(headers.recipients)
        participants.update(headers.cc_recipients)
        
        # Determine original subject (remove Re:, Fwd: prefixes)
        original_subject = self._extract_original_subject(headers.subject)
        
        # Calculate reply chain length
        reply_chain_length = headers.subject.lower().count('re:') + headers.subject.lower().count('fwd:')
        
        # Parent message ID
        parent_message_id = headers.in_reply_to or (headers.references[-1] if headers.references else None)
        
        return ThreadAnalysis(
            thread_id=thread_id,
            is_reply=is_reply,
            is_forward=is_forward,
            parent_message_id=parent_message_id,
            thread_depth=thread_depth,
            conversation_participants=participants,
            thread_subject=original_subject,
            original_subject=original_subject,
            reply_chain_length=reply_chain_length
        )
    
    def _extract_original_subject(self, subject: str) -> str:
        """Extract original subject by removing reply/forward prefixes"""
        if not subject:
            return ""
        
        # Remove common prefixes (case insensitive) - apply multiple times to handle nested prefixes
        original = subject
        prefixes = [r'^\[.*?\]\s*', r'^re:\s*', r'^fwd?:\s*', r'^fw:\s*']
        
        # Keep applying prefixes until no more changes
        changed = True
        while changed:
            old_original = original
            for prefix in prefixes:
                original = re.sub(prefix, '', original, flags=re.IGNORECASE)
            changed = (original != old_original)
        
        return original.strip()
    
    def _extract_and_validate_attachments(self, email_msg: EmailMessage) -> List[ValidatedAttachment]:
        """Extract and validate email attachments with security checks"""
        attachments = []
        
        try:
            for part in email_msg.walk():
                content_disposition = part.get('Content-Disposition', '')
                
                if 'attachment' in content_disposition or part.get_filename():
                    attachment = self._process_attachment(part)
                    if attachment:
                        attachments.append(attachment)
            
            logger.debug(f"Extracted {len(attachments)} attachments")
            return attachments
            
        except Exception as e:
            logger.error(f"Attachment extraction failed: {e}")
            raise ContentExtractionError(f"Failed to extract attachments: {e}") from e
    
    def _process_attachment(self, part) -> Optional[ValidatedAttachment]:
        """Process individual attachment with security validation"""
        try:
            filename = part.get_filename()
            if not filename:
                # Generate filename if missing
                ext = mimetypes.guess_extension(part.get_content_type()) or '.bin'
                filename = f"attachment_{uuid.uuid4().hex[:8]}{ext}"
            
            # Decode filename if needed
            filename = self._decode_header_value(filename)
            original_filename = filename
            
            # Get attachment content
            payload = part.get_payload(decode=True)
            if not payload:
                logger.warning(f"Empty attachment: {filename}")
                return None
            
            # Security validation
            security_result = self._validate_attachment_security(filename, payload)
            if not security_result['is_safe']:
                logger.warning(f"Unsafe attachment detected: {filename} - {security_result['reason']}")
                self.extraction_stats['security_violations'] += 1
                
                # Still create record but mark as unsafe
                return ValidatedAttachment(
                    filename=filename,
                    original_filename=original_filename,
                    content_type=part.get_content_type(),
                    size_bytes=len(payload),
                    content_hash=hashlib.sha256(payload).hexdigest(),
                    is_safe=False,
                    security_scan_result=security_result['reason'],
                    temporary_path=None,
                    extraction_timestamp=datetime.now(),
                    expires_at=datetime.now() + self.cleanup_interval,
                    metadata={'security_violation': True}
                )
            
            # Create secure temporary file
            temp_path = self._create_secure_temp_file(filename, payload)
            
            # Calculate content hash
            content_hash = hashlib.sha256(payload).hexdigest()
            
            # Collect metadata
            metadata = {
                'content_type': part.get_content_type(),
                'content_disposition': part.get('Content-Disposition', ''),
                'content_encoding': part.get('Content-Transfer-Encoding'),
                'size_mb': round(len(payload) / (1024 * 1024), 2)
            }
            
            return ValidatedAttachment(
                filename=filename,
                original_filename=original_filename,
                content_type=part.get_content_type(),
                size_bytes=len(payload),
                content_hash=content_hash,
                is_safe=True,
                security_scan_result="CLEAN",
                temporary_path=temp_path,
                extraction_timestamp=datetime.now(),
                expires_at=datetime.now() + self.cleanup_interval,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Attachment processing failed: {e}")
            return None
    
    def _validate_attachment_security(self, filename: str, content: bytes) -> Dict[str, Any]:
        """Validate attachment security"""
        # Check file size
        if len(content) > self.MAX_ATTACHMENT_SIZE:
            return {
                'is_safe': False,
                'reason': f'File too large: {len(content)} bytes (max: {self.MAX_ATTACHMENT_SIZE})'
            }
        
        # Check dangerous extensions
        file_ext = Path(filename).suffix.lower()
        if file_ext in self.DANGEROUS_EXTENSIONS:
            return {
                'is_safe': False,
                'reason': f'Dangerous file extension: {file_ext}'
            }
        
        # Check for embedded executables in common formats
        if self._contains_embedded_executable(content):
            return {
                'is_safe': False,
                'reason': 'Contains embedded executable content'
            }
        
        # Check for suspicious content patterns
        suspicious_patterns = [
            b'<script',
            b'javascript:',
            b'vbscript:',
            b'data:text/html',
            b'<?php',
            b'<%',
            b'eval(',
            b'exec(',
            b'system(',
        ]
        
        content_lower = content.lower()
        for pattern in suspicious_patterns:
            if pattern in content_lower:
                return {
                    'is_safe': False,
                    'reason': f'Suspicious content pattern detected: {pattern.decode("utf-8", errors="ignore")}'
                }
        
        return {'is_safe': True, 'reason': 'CLEAN'}
    
    def _contains_embedded_executable(self, content: bytes) -> bool:
        """Check if content contains embedded executable signatures"""
        # Check for common executable signatures
        executable_signatures = [
            b'MZ',  # DOS/Windows executable
            b'\x7fELF',  # Linux ELF
            b'\xca\xfe\xba\xbe',  # Java class file
            b'PK\x03\x04',  # ZIP (could contain executables)
        ]
        
        for signature in executable_signatures:
            if content.startswith(signature):
                return True
        
        return False
    
    def _create_secure_temp_file(self, filename: str, content: bytes) -> str:
        """Create secure temporary file for attachment"""
        try:
            # Create secure filename
            safe_filename = self._sanitize_filename(filename)
            temp_filename = f"{uuid.uuid4().hex}_{safe_filename}"
            temp_path = os.path.join(self.temp_dir, temp_filename)
            
            # Write content to temporary file with restricted permissions
            with open(temp_path, 'wb') as f:
                f.write(content)
            
            # Set restrictive permissions (owner read/write only)
            os.chmod(temp_path, 0o600)
            
            logger.debug(f"Created secure temp file: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Failed to create secure temp file: {e}")
            raise AttachmentSecurityError(f"Failed to create secure temp file: {e}") from e
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage"""
        # Remove path separators and dangerous characters
        safe_chars = re.sub(r'[^\w\-_\.]', '_', filename)
        
        # Limit length
        if len(safe_chars) > 100:
            name, ext = os.path.splitext(safe_chars)
            safe_chars = name[:90] + ext
        
        return safe_chars
    
    def _calculate_content_hash(self, content: str, message_id: str) -> str:
        """Calculate SHA-256 hash of email content for deduplication"""
        try:
            # Combine content and message ID for unique hash
            hash_input = f"{content}\n{message_id}".encode('utf-8')
            return hashlib.sha256(hash_input).hexdigest()
        except Exception as e:
            logger.error(f"Content hash calculation failed: {e}")
            return hashlib.sha256(f"error_{datetime.now().isoformat()}".encode()).hexdigest()
    
    def _collect_security_flags(self, email_msg: EmailMessage, attachments: List[ValidatedAttachment]) -> List[str]:
        """Collect security flags for the email"""
        flags = []
        
        try:
            # Check for unsafe attachments
            unsafe_attachments = [att for att in attachments if not att.is_safe]
            if unsafe_attachments:
                flags.append(f"UNSAFE_ATTACHMENTS:{len(unsafe_attachments)}")
            
            # Check for suspicious headers
            suspicious_headers = ['X-Spam-Flag', 'X-Spam-Status', 'X-Virus-Status']
            for header in suspicious_headers:
                if email_msg.get(header):
                    flags.append(f"SUSPICIOUS_HEADER:{header}")
            
            # Check for external links in content
            # This is a basic check - more sophisticated analysis could be added
            content = ""
            try:
                if hasattr(email_msg, 'get_content'):
                    content = str(email_msg.get_content() or "")
                else:
                    # For multipart messages, get content from parts
                    for part in email_msg.walk():
                        if part.get_content_type().startswith('text/'):
                            try:
                                part_content = part.get_payload(decode=True)
                                if part_content:
                                    charset = part.get_content_charset() or 'utf-8'
                                    content += part_content.decode(charset, errors='ignore')
                            except Exception:
                                continue
            except Exception:
                pass
            
            if re.search(r'https?://[^\s<>"]+', content):
                flags.append("CONTAINS_EXTERNAL_LINKS")
            
            # Check for forwarded emails (potential phishing vector)
            subject = email_msg.get('Subject', '').lower()
            if 'fwd:' in subject or 'fw:' in subject:
                flags.append("FORWARDED_EMAIL")
            
            return flags
            
        except Exception as e:
            logger.error(f"Security flag collection failed: {e}")
            return ["SECURITY_CHECK_FAILED"]
    
    def cleanup_expired_attachments(self) -> int:
        """Clean up expired temporary attachment files"""
        cleaned_count = 0
        
        try:
            temp_path = Path(self.temp_dir)
            current_time = datetime.now()
            
            for file_path in temp_path.glob("*"):
                if file_path.is_file():
                    # Check file age
                    file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if file_age > self.cleanup_interval:
                        try:
                            file_path.unlink()
                            cleaned_count += 1
                            logger.debug(f"Cleaned up expired temp file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to clean up temp file {file_path}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired temporary files")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Temp file cleanup failed: {e}")
            return 0
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get content extraction statistics"""
        return self.extraction_stats.copy()
    
    def reset_extraction_stats(self) -> None:
        """Reset extraction statistics"""
        self.extraction_stats = {
            'total_extractions': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'security_violations': 0,
            'attachments_processed': 0
        }
        logger.info("Extraction statistics reset")
    
    def detect_thread_duplicates(self, email_msg: EmailMessage, headers: EmailHeaders, 
                               content: str) -> Optional[Dict[str, Any]]:
        """
        Detect thread-based duplicates using enhanced thread analyzer
        
        Args:
            email_msg: Email message
            headers: Email headers
            content: Email content
            
        Returns:
            Duplicate detection result or None if analyzer not available
        """
        try:
            if hasattr(self, '_thread_analyzer'):
                thread_analysis = self._analyze_email_threading(email_msg, headers)
                duplicate_check = self._thread_analyzer.detect_thread_based_duplicates(
                    headers, content, thread_analysis
                )
                
                return {
                    'is_duplicate': duplicate_check.is_duplicate,
                    'duplicate_type': duplicate_check.duplicate_type,
                    'original_message_id': duplicate_check.original_message_id,
                    'confidence_score': duplicate_check.confidence_score,
                    'detection_method': duplicate_check.detection_method,
                    'metadata': duplicate_check.duplicate_metadata
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Thread duplicate detection failed: {e}")
            return None
    
    def get_conversation_context(self, email_msg: EmailMessage, headers: EmailHeaders) -> Optional[Dict[str, Any]]:
        """
        Get conversation context for email using enhanced thread analyzer
        
        Args:
            email_msg: Email message
            headers: Email headers
            
        Returns:
            Conversation context or None if analyzer not available
        """
        try:
            if hasattr(self, '_thread_analyzer'):
                thread_analysis = self._analyze_email_threading(email_msg, headers)
                context = self._thread_analyzer.track_conversation_context(
                    email_msg, headers, thread_analysis
                )
                
                return {
                    'conversation_id': context.conversation_id,
                    'thread_type': context.thread_type.value,
                    'participant_count': len(context.participants),
                    'message_count': len(context.message_timeline),
                    'workflow_correlation': {
                        'workflow_type': context.workflow_correlation.workflow_type.value,
                        'confidence': context.workflow_correlation.correlation_confidence,
                        'task_ids': context.workflow_correlation.related_task_ids,
                        'approval_ids': context.workflow_correlation.approval_request_ids
                    },
                    'conversation_summary': context.conversation_summary
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Conversation context retrieval failed: {e}")
            return None
    
    def detect_pmo_correlation(self, email_msg: EmailMessage, headers: EmailHeaders, 
                             content: str) -> Optional[Dict[str, Any]]:
        """
        Detect PMO response correlation using enhanced thread analyzer
        
        Args:
            email_msg: Email message
            headers: Email headers
            content: Email content
            
        Returns:
            PMO correlation result or None if analyzer not available
        """
        try:
            if hasattr(self, '_thread_analyzer'):
                thread_analysis = self._analyze_email_threading(email_msg, headers)
                correlation = self._thread_analyzer.detect_pmo_response_correlation(
                    headers, content, thread_analysis
                )
                
                return {
                    'workflow_type': correlation.workflow_type.value,
                    'correlation_confidence': correlation.correlation_confidence,
                    'original_request_id': correlation.original_request_id,
                    'related_task_ids': correlation.related_task_ids,
                    'approval_request_ids': correlation.approval_request_ids,
                    'status_update_ids': correlation.status_update_ids,
                    'metadata': correlation.correlation_metadata
                }
            
            return None
            
        except Exception as e:
            logger.error(f"PMO correlation detection failed: {e}")
            return None