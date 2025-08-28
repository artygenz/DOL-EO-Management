#!/usr/bin/env python3
"""
IMAP IDLE Listener Service for lumenlighthouse.ai

This service provides real-time email monitoring using IMAP IDLE protocol.
It watches the inbox for new emails, fetches metadata, body, and attachments,
then posts normalized payloads to the FastAPI endpoint.

Key Features:
- Real-time email monitoring using IMAP IDLE protocol
- Automatic reconnection and error recovery
- Structured email data extraction (headers, body, attachments)
- Webhook delivery with retry logic
- Comprehensive logging and monitoring
- Graceful shutdown handling

Author: DOL-EO-Management Team
Version: 1.0
"""

# Standard library imports
import asyncio          # For asynchronous operations
import logging          # For application logging
import re               # For regular expressions (email parsing)
import time             # For timing operations
import uuid             # For generating unique identifiers
from datetime import datetime  # For timestamp handling
from typing import Dict, List, Optional, Tuple  # For type hints

# Email and IMAP related imports
import imaplib          # Core IMAP library for email server communication
import email            # Email message parsing and handling
from email.header import decode_header  # For decoding email headers

# HTTP and data handling imports
import aiohttp          # For asynchronous HTTP requests (webhook delivery)
import json             # For JSON serialization of structured data
import os               # For environment variable access
import base64           # For encoding binary data (attachments)

# Configure logging for this module
logger = logging.getLogger(__name__)

class IMAPIDLEListener:
    """
    IMAP IDLE listener using standard imaplib library with asyncio wrapper.
    
    This class provides real-time email monitoring capabilities using the IMAP IDLE protocol.
    It maintains a persistent connection to an IMAP server and listens for new email
    notifications, then processes and forwards them to a webhook endpoint.
    
    Key Features:
    - Real-time email monitoring via IMAP IDLE protocol
    - Automatic connection management and reconnection
    - Structured email data extraction and processing
    - Webhook delivery with retry logic
    - Comprehensive error handling and recovery
    - Performance monitoring and statistics
    
    Attributes:
        host (str): IMAP server hostname
        port (int): IMAP server port
        username (str): Email account username
        password (str): Email account password
        webhook_url (str): URL to send processed emails
        check_interval (int): Interval between IDLE sessions (seconds)
        idle_timeout (int): IDLE session timeout (seconds)
        use_ssl (bool): Whether to use SSL/TLS connection
        is_running (bool): Service running state
        last_uid (int): Last processed email UID
        stats (dict): Service statistics and metrics
        imap (imaplib.IMAP4): IMAP connection object
        server_supports_idle (bool): Whether server supports IDLE protocol
    """
    
    def __init__(
        self,
        host: str,           # IMAP server hostname (e.g., "lumenlighthouse.ai")
        port: int,           # IMAP server port (e.g., 993 for SSL, 143 for non-SSL)
        username: str,       # Email account username
        password: str,       # Email account password
        webhook_url: str,    # URL to send processed emails (e.g., "http://localhost:8000/api/email/webhook")
        check_interval: int = 30,    # Interval between IDLE sessions in seconds
        idle_timeout: int = 15,      # IDLE session timeout in seconds
        use_ssl: bool = True         # Whether to use SSL/TLS connection
    ):
        """
        Initialize the IMAP IDLE listener with connection parameters.
        
        Args:
            host: IMAP server hostname
            port: IMAP server port
            username: Email account username
            password: Email account password
            webhook_url: URL to send processed emails
            check_interval: Interval between IDLE sessions (default: 30 seconds)
            idle_timeout: IDLE session timeout (default: 15 seconds)
            use_ssl: Whether to use SSL/TLS connection (default: True)
        """
        # Store connection configuration
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.webhook_url = webhook_url
        self.check_interval = check_interval
        self.idle_timeout = idle_timeout
        self.use_ssl = use_ssl
        
        # Service state management
        self.is_running = False      # Flag to control the monitoring loop
        self.last_uid = 0            # Track the last processed email UID to avoid duplicates
        
        # Performance and error tracking statistics
        self.stats = {
            "emails_processed": 0,    # Total number of emails successfully processed
            "connection_errors": 0,   # Number of connection-related errors
            "webhook_errors": 0,      # Number of webhook delivery failures
            "start_time": None        # Service start timestamp
        }
        
        # IMAP connection management
        self.imap = None              # IMAP connection object (initialized during connect)
        self.server_supports_idle = True  # Assume IDLE support (verified during connection)
        
    async def connect(self) -> bool:
        """
        Establish connection to IMAP server and perform initial setup.
        
        This method handles the complete connection process including:
        1. Creating SSL/non-SSL IMAP connection
        2. Authenticating with username/password
        3. Selecting the INBOX mailbox
        4. Checking server capabilities (especially IDLE support)
        5. Setting up initial UID tracking
        
        Returns:
            bool: True if connection successful, False otherwise
            
        Raises:
            Exception: Various IMAP-related exceptions during connection process
        """
        try:
            logger.info(f"Connecting to IMAP server {self.host}:{self.port}")
            
            # Step 1: Create IMAP connection (SSL or non-SSL)
            if self.use_ssl:
                # Use SSL/TLS encrypted connection (recommended for security)
                self.imap = imaplib.IMAP4_SSL(self.host, self.port)
            else:
                # Use unencrypted connection (not recommended for production)
                self.imap = imaplib.IMAP4(self.host, self.port)
            
            # Step 2: Authenticate with the server
            logger.info(f"Logging in as {self.username}")
            result, data = self.imap.login(self.username, self.password)
            
            if result != 'OK':
                logger.error(f"Login failed: {result}")
                return False
            
            logger.info("Login successful")
            
            # Step 3: Select the INBOX mailbox for monitoring
            result, data = self.imap.select('INBOX')
            if result != 'OK':
                logger.error(f"Failed to select INBOX: {result}")
                return False
            
            logger.info("INBOX selected successfully")
            
            # Step 4: Verify server capabilities (especially IDLE support)
            await self._check_server_capabilities()
            
            # Step 5: Initialize UID tracking to avoid processing old emails
            await self._update_last_uid()
            
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.stats["connection_errors"] += 1
            return False
    
    async def _check_server_capabilities(self):
        """
        Check and verify server capabilities, particularly IDLE support.
        
        This method queries the IMAP server for its supported capabilities and
        specifically checks if IDLE protocol is supported. If IDLE is not supported,
        the service will fall back to polling mode.
        
        The IDLE protocol allows for real-time email notifications without
        constantly polling the server, making it more efficient.
        
        Raises:
            Exception: If capability check fails
        """
        try:
            # Query server for supported capabilities
            result, data = self.imap.capability()
            if result == 'OK' and data:
                # Decode and log server capabilities for debugging
                capabilities = data[0].decode('utf-8', errors='ignore')
                logger.info(f"Server capabilities: {capabilities}")
                
                # Check specifically for IDLE support
                if 'IDLE' in capabilities:
                    logger.info("Server supports IDLE")
                    self.server_supports_idle = True
                else:
                    logger.warning("Server does not support IDLE, will use polling")
                    self.server_supports_idle = False
            else:
                # If we can't determine capabilities, assume IDLE support
                logger.warning("Could not determine server capabilities, assuming IDLE support")
                self.server_supports_idle = True
                
        except Exception as e:
            logger.error(f"Error checking server capabilities: {e}")
            # Default to assuming IDLE support on error
            self.server_supports_idle = True
    
    async def _update_last_uid(self):
        """Update the last UID to track new emails"""
        try:
            # Search for all messages and get the highest UID
            result, data = self.imap.search(None, 'ALL')
            if result == 'OK' and data[0]:
                message_nums = data[0].decode().split()
                if message_nums:
                    # Get UID of the last message
                    result, data = self.imap.fetch(message_nums[-1], '(UID)')
                    if result == 'OK' and data[0]:
                        uid_match = re.search(r'UID (\d+)', data[0].decode())
                        if uid_match:
                            highest_uid = int(uid_match.group(1))
                            # Only update if this is the first connection (last_uid is 0)
                            if self.last_uid == 0:
                                self.last_uid = highest_uid
                                logger.info(f"Initial UID set to: {self.last_uid}")
                            else:
                                logger.info(f"Keeping existing last_uid: {self.last_uid} (highest available: {highest_uid})")
                            
        except Exception as e:
            logger.error(f"Error updating last UID: {e}")
    
    async def disconnect(self):
        """
        Safely disconnect from the IMAP server.
        
        This method performs a clean logout from the IMAP server and resets
        the connection object. It handles any errors that might occur during
        the logout process to ensure the service can continue operating.
        
        The method is called during:
        - Service shutdown
        - Connection errors requiring reconnection
        - Manual disconnection requests
        """
        if self.imap:
            try:
                # Perform clean logout from IMAP server
                self.imap.logout()
                logger.info("Disconnected from IMAP server")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
            finally:
                # Always reset the connection object regardless of logout success
                self.imap = None
    
    async def _fetch_email(self, message_num: str) -> Optional[Dict]:
        """
        Fetch and parse email data by message number with comprehensive structure.
        
        This method retrieves a complete email message from the IMAP server and
        extracts all relevant information including headers, body content, and
        attachments. The data is structured for easy processing and webhook delivery.
        
        Args:
            message_num (str): The message number to fetch from the IMAP server
            
        Returns:
            Optional[Dict]: Structured email data containing:
                - uid: Unique identifier for the email
                - message_num: Original message number
                - subject: Email subject line
                - sender: Email sender address
                - recipients: List of recipient addresses
                - body: Primary email body content
                - attachments: List of attachment metadata
                - raw_content: Email body content for database storage
                - timestamp: Processing timestamp
                - message_id: Email message ID
                - email_date: Email date header
                - received_date: Received date header
                - content_type: Primary content type
                - email_size: Size of email in bytes
                - structured_metadata: JSON metadata for processing
                
        Raises:
            Exception: Various IMAP and parsing related exceptions
        """
        try:
            # Step 1: Fetch the complete email message from IMAP server
            # RFC822 format includes the full email with headers and body
            result, data = self.imap.fetch(message_num, '(RFC822)')
            if result != 'OK':
                logger.error(f"Failed to fetch email {message_num}: {result}")
                return None
            
            # Step 2: Parse the raw email data into a structured message object
            raw_email = data[0][1]  # Extract the actual email data
            email_message = email.message_from_bytes(raw_email)
            
            # Step 3: Extract and process email headers
            headers = self._extract_all_headers(email_message)
            
            # Extract key header fields for easy access
            subject = headers.get('Subject', '')           # Email subject line
            sender_raw = headers.get('From', '')           # Raw sender field (may contain display name)
            sender = self._extract_email_from_sender(sender_raw)  # Extract just the email address
            to_recipients = headers.get('To', '')          # Primary recipients
            cc_recipients = headers.get('Cc', '')          # Carbon copy recipients
            bcc_recipients = headers.get('Bcc', '')        # Blind carbon copy recipients
            message_id = headers.get('Message-ID', '')     # Unique message identifier
            date = headers.get('Date', '')                 # Email date header
            received_date = headers.get('Received', '')    # Server received date
            
            # Step 4: Combine all recipient types into a single list
            # This makes it easier to process all recipients uniformly
            recipients = []
            if to_recipients:
                recipients.extend([r.strip() for r in to_recipients.split(',')])
            if cc_recipients:
                recipients.extend([r.strip() for r in cc_recipients.split(',')])
            if bcc_recipients:
                recipients.extend([r.strip() for r in bcc_recipients.split(',')])
            
            # Step 5: Extract email body content with structure detection
            # This handles both plain text and HTML content, detecting the primary format
            body_data = self._extract_structured_body(email_message)
            
            # Step 6: Extract attachment metadata and data
            # This processes all attachments and stores their metadata for later processing
            attachments = self._extract_attachments_with_metadata(email_message)
            
            # Step 7: Get the unique identifier (UID) for this email
            # UID is persistent and doesn't change even if emails are reordered
            uid_result, uid_data = self.imap.fetch(message_num, '(UID)')
            uid = None
            if uid_result == 'OK' and uid_data[0]:
                uid_match = re.search(r'UID (\d+)', uid_data[0].decode())
                if uid_match:
                    uid = int(uid_match.group(1))
            
            # Step 8: Prepare the primary body content for database storage
            # Prefer plain text over HTML for the raw_content field
            primary_body_content = body_data.get('text_plain', '') or body_data.get('text_html', '')
            
            # Step 9: Create structured metadata for processing
            # This contains all the detailed information needed for business logic
            structured_metadata = self._create_structured_metadata(
                headers=headers,
                body_data=body_data,
                attachments=attachments,
                raw_email=raw_email,
                uid=uid,
                message_num=message_num
            )
            
            # Step 10: Return structured email data for webhook processing
            return {
                'uid': uid,                                    # Unique identifier for tracking
                'message_num': message_num,                    # Original message number
                'subject': subject,                            # Email subject line
                'sender': sender,                              # Sender email address
                'recipients': recipients,                      # All recipient addresses
                'body': primary_body_content,                  # Primary body content for display
                'attachments': attachments,                    # Attachment metadata and data
                'raw_content': primary_body_content,           # Email body for database storage
                'timestamp': datetime.now().isoformat(),       # Processing timestamp
                'message_id': message_id,                      # Email message ID
                'email_date': date,                            # Email date header
                'received_date': received_date,                # Server received date
                'content_type': body_data.get('primary_content_type', 'text/plain'),  # Primary content type
                'email_size': len(raw_email),                  # Total email size in bytes
                'structured_metadata': structured_metadata     # Detailed metadata for processing
            }
            
        except Exception as e:
            # Log any errors during email fetching and return None to indicate failure
            logger.error(f"Error fetching email {message_num}: {e}")
            return None
    
    def _decode_header(self, header: str) -> str:
        """
        Decode email header values that may be encoded in various formats.
        
        Email headers can be encoded using different character encodings (UTF-8, ISO-8859-1, etc.)
        and may contain non-ASCII characters. This method properly decodes them into
        readable Unicode strings.
        
        Args:
            header (str): The raw header value to decode
            
        Returns:
            str: Decoded header value as a Unicode string
            
        Examples:
            - "=?UTF-8?B?SGVsbG8gV29ybGQ=?=" -> "Hello World"
            - "=?ISO-8859-1?Q?Subject_Line?=" -> "Subject Line"
        """
        if not header:
            return ""
        
        try:
            # Use email library's decode_header function to handle various encodings
            decoded_parts = decode_header(header)
            decoded_string = ""
            
            # Process each part of the decoded header
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    # Handle byte parts with specified or default encoding
                    if encoding:
                        decoded_string += part.decode(encoding, errors='ignore')
                    else:
                        decoded_string += part.decode('utf-8', errors='ignore')
                else:
                    # Handle string parts (already decoded)
                    decoded_string += str(part)
            
            return decoded_string
            
        except Exception as e:
            # If decoding fails, return the original header as a string
            logger.error(f"Error decoding header '{header}': {e}")
            return str(header)
    
    def _extract_email_from_sender(self, sender_raw: str) -> str:
        """
        Extract just the email address from a sender field that may contain a display name.
        
        This method handles various sender formats:
        - "jack.smith@lumenlighthouse.ai" (just email)
        - "Jack Smith <jack.smith@lumenlighthouse.ai>" (display name + email)
        - "Jack Smith" <jack.smith@lumenlighthouse.ai> (quoted display name + email)
        
        Args:
            sender_raw (str): The raw sender field from email headers
            
        Returns:
            str: Just the email address, or the original string if no email found
            
        Examples:
            - "jack.smith@lumenlighthouse.ai" -> "jack.smith@lumenlighthouse.ai"
            - "Jack Smith <jack.smith@lumenlighthouse.ai>" -> "jack.smith@lumenlighthouse.ai"
            - "Jack Smith" <jack.smith@lumenlighthouse.ai> -> "jack.smith@lumenlighthouse.ai"
        """
        if not sender_raw:
            return ""
        
        try:
            # Import email parsing utilities
            from email.utils import parseaddr
            
            # Use email.utils.parseaddr to extract email from various formats
            display_name, email_address = parseaddr(sender_raw)
            
            # If parseaddr found an email address, return it
            if email_address:
                logger.debug(f"Extracted email '{email_address}' from sender '{sender_raw}'")
                return email_address
            
            # If no email found by parseaddr, try regex as fallback
            import re
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            email_match = re.search(email_pattern, sender_raw)
            
            if email_match:
                email_address = email_match.group(0)
                logger.debug(f"Extracted email '{email_address}' from sender '{sender_raw}' using regex")
                return email_address
            
            # If no email found, return the original string
            logger.warning(f"No email address found in sender: '{sender_raw}'")
            return sender_raw
            
        except Exception as e:
            logger.error(f"Error extracting email from sender '{sender_raw}': {e}")
            return sender_raw
    
    def _extract_all_headers(self, email_message) -> Dict[str, str]:
        """
        Extract and decode all email headers from the email message.
        
        This method processes both standard email headers and custom headers,
        ensuring proper decoding of encoded header values. It prioritizes
        common headers for easy access while also capturing all available headers.
        
        Args:
            email_message: The parsed email message object
            
        Returns:
            Dict[str, str]: Dictionary of header names and their decoded values
            
        Common Headers Extracted:
            - Subject: Email subject line
            - From: Sender information
            - To/Cc/Bcc: Recipient information
            - Message-ID: Unique message identifier
            - Date: Email timestamp
            - Received: Server routing information
            - Content-Type: Message format information
            - X-* headers: Custom headers for various purposes
        """
        headers = {}
        
        # Priority list of common headers to extract first
        # These are the most frequently used headers in email processing
        header_names = [
            'Subject', 'From', 'To', 'Cc', 'Bcc', 'Message-ID', 'Date', 'Received',
            'Reply-To', 'Return-Path', 'X-Mailer', 'MIME-Version', 'Content-Type',
            'Content-Transfer-Encoding', 'X-Priority', 'X-MSMail-Priority',
            'Importance', 'X-Original-From', 'X-Forwarded-For', 'X-Originating-IP'
        ]
        
        # Extract and decode priority headers
        for header_name in header_names:    
            value = email_message.get(header_name, '')
            if value:
                headers[header_name] = self._decode_header(value)
        
        # Extract any remaining headers not in the priority list
        # This ensures we capture all available header information
        for header_name, header_value in email_message.items():
            if header_name not in headers:
                headers[header_name] = self._decode_header(header_value)
        
        return headers
    
    def _extract_structured_body(self, email_message) -> Dict[str, str]:
        """
        Extract email body content with structure detection and content type handling.
        
        This method processes both multipart and single-part emails, extracting
        plain text and HTML content while preserving the original structure.
        It handles various content types and character encodings properly.
        
        Args:
            email_message: The parsed email message object
            
        Returns:
            Dict[str, str]: Structured body data containing:
                - text_plain: Plain text content
                - text_html: HTML content
                - primary_content_type: Detected primary content type
                - content_parts: List of content parts with metadata
        """
        # Initialize body data structure
        body_data = {
            'text_plain': '',              # Plain text content
            'text_html': '',               # HTML content
            'primary_content_type': 'text/plain',  # Default content type
            'content_parts': []            # List of content parts with metadata
        }
        
        if email_message.is_multipart():
            # Handle multipart emails (multiple content parts)
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition'))
                
                # Skip attachment parts (handled separately)
                if 'attachment' in content_disposition:
                    continue
                
                # Extract plain text content
                if content_type == "text/plain":
                    try:
                        content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        body_data['text_plain'] += content
                        body_data['content_parts'].append({
                            'type': 'text/plain',
                            'content': content,
                            'charset': part.get_content_charset() or 'utf-8'
                        })
                    except Exception as e:
                        logger.warning(f"Error extracting text/plain content: {e}")
                        
                # Extract HTML content
                elif content_type == "text/html":
                    try:
                        content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        body_data['text_html'] += content
                        body_data['content_parts'].append({
                            'type': 'text/html',
                            'content': content,
                            'charset': part.get_content_charset() or 'utf-8'
                        })
                    except Exception as e:
                        logger.warning(f"Error extracting text/html content: {e}")
        else:
            # Handle single-part emails (simple content)
            content_type = email_message.get_content_type()
            try:
                content = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
                
                # Determine content type and store appropriately
                if content_type == "text/html":
                    body_data['text_html'] = content
                    body_data['primary_content_type'] = 'text/html'
                else:
                    body_data['text_plain'] = content
                    body_data['primary_content_type'] = 'text/plain'
                
                # Store content part metadata
                body_data['content_parts'].append({
                    'type': content_type,
                    'content': content,
                    'charset': email_message.get_content_charset() or 'utf-8'
                })
            except Exception as e:
                logger.warning(f"Error extracting single part content: {e}")
                # Fallback to raw payload if decoding fails
                body_data['text_plain'] = str(email_message.get_payload())
        
        return body_data
    
    def _extract_attachments_with_metadata(self, email_message) -> List[Dict]:
        """
        Extract email attachments with comprehensive metadata and data.
        
        This method processes multipart emails to find and extract all attachments,
        including their metadata (filename, content type, size, etc.) and binary data.
        It handles various attachment types and provides detailed information for
        further processing or storage.
        
        Args:
            email_message: The parsed email message object
            
        Returns:
            List[Dict]: List of attachment dictionaries containing:
                - filename: Decoded attachment filename
                - content_type: MIME content type
                - size: Size in bytes
                - data: Binary attachment data
                - content_id: Content-ID for embedded attachments
                - content_disposition: How the attachment should be handled
                - charset: Character encoding
                - encoding: Content transfer encoding
                - boundary: MIME boundary information
        """
        attachments = []
        
        # Only multipart emails can have attachments
        if email_message.is_multipart():
            # Walk through all parts of the email
            for part in email_message.walk():
                content_disposition = str(part.get('Content-Disposition'))
                
                # Check if this part is an attachment
                if 'attachment' in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        # Decode the filename (may be encoded)
                        filename = self._decode_header(filename)
                        
                        try:
                            # Extract attachment data and metadata
                            attachment_data = part.get_payload(decode=True)
                            content_type = part.get_content_type()
                            content_id = part.get('Content-ID', '')
                            
                            # Create comprehensive attachment record
                            attachments.append({
                                'filename': filename,                    # Decoded filename
                                'content_type': content_type,            # MIME type
                                'size': len(attachment_data) if attachment_data else 0,  # Size in bytes
                                'data': attachment_data,                 # Binary data
                                'content_id': content_id,                # Content-ID for embedded attachments
                                'content_disposition': content_disposition,  # How to handle attachment
                                'charset': part.get_content_charset(),   # Character encoding
                                'encoding': part.get('Content-Transfer-Encoding', ''),  # Transfer encoding
                                'boundary': part.get_boundary()          # MIME boundary
                            })
                        except Exception as e:
                            logger.error(f"Error extracting attachment {filename}: {e}")
        
        return attachments
    
    def _create_structured_metadata(self, headers: Dict, body_data: Dict, 
                                  attachments: List[Dict], raw_email: bytes, 
                                  uid: int, message_num: str) -> str:
        """
        Create structured metadata for email processing and analysis.
        
        This method creates a comprehensive JSON structure containing all the
        metadata needed for email processing, analysis, and business logic.
        The metadata is separate from the raw_content field and provides
        structured access to email information without storing the actual
        content data.
        
        Args:
            headers: Dictionary of email headers
            body_data: Structured body content information
            attachments: List of attachment metadata
            raw_email: Original raw email bytes
            uid: Email unique identifier
            message_num: IMAP message number
            
        Returns:
            str: JSON string containing structured metadata
        """
        from datetime import datetime
        
        # Create comprehensive metadata structure
        structured_metadata = {
            # Core email metadata
            "metadata": {
                "uid": uid,                                    # Unique identifier
                "message_num": message_num,                    # IMAP message number
                "extraction_timestamp": datetime.now().isoformat(),  # When extracted
                "email_size_bytes": len(raw_email),            # Total email size
                "content_type": body_data.get('primary_content_type', 'text/plain'),  # Primary content type
                "has_attachments": len(attachments) > 0,       # Whether email has attachments
                "attachment_count": len(attachments)           # Number of attachments
            },
            # All email headers (decoded)
            "headers": headers,
            # Body content information (without actual content)
            "body_info": {
                "text_plain_length": len(body_data.get('text_plain', '')),  # Plain text length
                "text_html_length": len(body_data.get('text_html', '')),    # HTML length
                "primary_content_type": body_data.get('primary_content_type', 'text/plain'),  # Primary type
                "content_parts_count": len(body_data.get('content_parts', []))  # Number of content parts
            },
            # Attachment metadata (without binary data)
            "attachments": [
                {
                    "filename": att.get('filename', ''),           # Attachment filename
                    "content_type": att.get('content_type', ''),   # MIME content type
                    "size": att.get('size', 0),                    # Size in bytes
                    "content_id": att.get('content_id', ''),       # Content-ID for embedded
                    "content_disposition": att.get('content_disposition', ''),  # How to handle
                    "charset": att.get('charset', ''),             # Character encoding
                    "encoding": att.get('encoding', ''),           # Transfer encoding
                    "boundary": att.get('boundary', '')            # MIME boundary
                }
                for att in attachments
            ],
            # Raw email information
            "raw_mime_info": {
                "original_encoding": "utf-8",                      # Original encoding
                "size_bytes": len(raw_email)                       # Raw email size
            }
        }
        
        # Convert to JSON string for storage/transmission
        return json.dumps(structured_metadata, indent=2, ensure_ascii=False)
    
    async def _submit_to_api_with_retry(self, email_data: Dict, max_retries: int = 3) -> bool:
        """
        Submit email to webhook API with automatic retry logic and exponential backoff.
        
        This method implements a robust retry mechanism to handle temporary network
        issues or webhook endpoint unavailability. It uses exponential backoff to
        avoid overwhelming the server during recovery.
        
        Args:
            email_data: Structured email data to submit
            max_retries: Maximum number of retry attempts (default: 3)
            
        Returns:
            bool: True if submission successful, False if all retries failed
            
        Retry Strategy:
            - Attempt 1: Immediate retry
            - Attempt 2: Wait 1 second
            - Attempt 3: Wait 2 seconds
            - Attempt 4: Wait 4 seconds (if max_retries > 3)
        """
        for attempt in range(max_retries):
            try:
                # Attempt to submit the email data
                success = await self._submit_to_api(email_data)
                if success:
                    return True
                else:
                    logger.warning(f"Webhook submission failed (attempt {attempt + 1}/{max_retries})")
            except Exception as e:
                logger.warning(f"Webhook submission error (attempt {attempt + 1}/{max_retries}): {e}")
            
            # Implement exponential backoff between retries
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4 seconds
                logger.info(f"Retrying webhook submission in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
        
        # All retries failed, update error statistics
        self.stats["webhook_errors"] += 1
        return False
    
    async def _submit_to_api(self, email_data: Dict) -> bool:
        """
        Submit email data to webhook API with comprehensive structure and metadata.
        
        This method prepares the email data for webhook delivery, including both
        the raw content and structured metadata. It handles HTTP communication
        with the webhook endpoint and provides detailed logging for monitoring.
        
        Args:
            email_data: Structured email data containing all extracted information
            
        Returns:
            bool: True if webhook delivery successful, False otherwise
            
        Webhook Payload Structure:
            - Core email fields (subject, sender, recipients, body, etc.)
            - Raw content for database storage
            - Attachment metadata and data
            - Structured metadata for processing
            - Processing statistics and information
        """
        try:
            # Step 1: Prepare comprehensive webhook payload
            payload = {
                # Core email identification
                'id': str(uuid.uuid4()),                    # Unique webhook ID
                'direction': 'incoming',                    # Email direction
                
                # Basic email information
                'subject': email_data.get('subject', ''),   # Email subject
                'sender': email_data.get('sender', ''),     # Sender address
                'recipients': email_data.get('recipients', []),  # Recipient addresses
                'body': email_data.get('body', ''),         # Primary body content
                'raw_content': email_data.get('raw_content', ''),  # Raw content for DB
                'attachments': email_data.get('attachments', []),  # Attachment data
                'timestamp': email_data.get('timestamp', ''),  # Processing timestamp
                
                # IMAP-specific information
                'uid': email_data.get('uid'),               # Unique identifier
                'message_num': email_data.get('message_num'),  # IMAP message number
                
                # Enhanced metadata fields
                'message_id': email_data.get('message_id', ''),  # Email message ID
                'email_date': email_data.get('email_date', ''),  # Email date header
                'received_date': email_data.get('received_date', ''),  # Received date
                'content_type': email_data.get('content_type', 'text/plain'),  # Content type
                'email_size': email_data.get('email_size', 0),  # Email size in bytes
                'structured_metadata': email_data.get('structured_metadata', ''),  # JSON metadata
                
                # Structured data for easy processing
                'structured_data': {
                    # Core metadata
                    'metadata': {
                        'uid': email_data.get('uid'),
                        'message_num': email_data.get('message_num'),
                        'extraction_timestamp': email_data.get('timestamp'),
                        'email_size_bytes': email_data.get('email_size', 0),
                        'content_type': email_data.get('content_type', 'text/plain'),
                        'has_attachments': len(email_data.get('attachments', [])) > 0,
                        'attachment_count': len(email_data.get('attachments', []))
                    },
                    # Header information
                    'headers': {
                        'message_id': email_data.get('message_id', ''),
                        'date': email_data.get('email_date', ''),
                        'received_date': email_data.get('received_date', ''),
                        'content_type': email_data.get('content_type', 'text/plain')
                    },
                    # Body content information
                    'body_info': {
                        'primary_content_type': email_data.get('content_type', 'text/plain'),
                        'has_plain_text': bool(email_data.get('body', '')),
                        'has_html': email_data.get('content_type') == 'text/html'
                    },
                    # Attachment summary information
                    'attachment_info': {
                        'count': len(email_data.get('attachments', [])),
                        'types': list(set([att.get('content_type', '') for att in email_data.get('attachments', [])])),
                        'total_size': sum([att.get('size', 0) for att in email_data.get('attachments', [])])
                    }
                }
            }
            
            # Step 2: Send HTTP POST request to webhook endpoint
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,                           # Webhook endpoint URL
                    json=payload,                               # JSON payload with email data
                    headers={'Content-Type': 'application/json'},  # Content type header
                    timeout=aiohttp.ClientTimeout(total=30)     # 30-second timeout
                ) as response:
                    # Step 3: Handle webhook response
                    if response.status == 200:
                        # Success: Log details and update statistics
                        logger.info(f"Email submitted successfully: {email_data.get('subject', 'No subject')}")
                        logger.info(f"Email size: {email_data.get('email_size', 0)} bytes")
                        logger.info(f"Attachments: {len(email_data.get('attachments', []))}")
                        self.stats["emails_processed"] += 1
                        return True
                    else:
                        # Failure: Log error and update error statistics
                        logger.error(f"Webhook failed with status {response.status}: {await response.text()}")
                        self.stats["webhook_errors"] += 1
                        return False
                        
        except Exception as e:
            # Handle any unexpected errors during webhook submission
            logger.error(f"Error submitting to API: {e}")
            self.stats["webhook_errors"] += 1
            return False
    
    async def _process_new_emails(self) -> int:
        """
        Process new emails by searching for all emails and filtering by UID.
        
        This method is called after an IDLE notification indicates new emails.
        It searches for all emails in the mailbox and filters them by UID to
        identify only new emails that haven't been processed yet.
        
        The method includes robust error handling and connection recovery
        to ensure reliable email processing even when connection issues occur.
        
        Returns:
            int: Number of emails successfully processed
            
        Process:
            1. Reset connection state after IDLE
            2. Search for all emails in mailbox
            3. Filter emails by UID (only process new ones)
            4. Fetch and process each new email
            5. Submit to webhook with retry logic
        """
        # Verify connection is available
        if not self.imap:
            logger.error("Not connected to IMAP server")
            return 0
        
        try:
            # Step 1: Search for all emails in the mailbox
            logger.info(f"Searching for all emails to find new ones...")
            
            # After IDLE, we need to properly reset the connection state
            # The socket might be in a problematic state from the IDLE session
            try:
                # First, try to reset the socket timeout to normal
                self.imap.sock.settimeout(None)
                
                # Send a NOOP command to ensure the connection is in a good state
                logger.info("Sending NOOP to reset connection state...")
                result, data = self.imap.noop()
                if result != 'OK':
                    logger.warning(f"NOOP failed: {result}, attempting reconnect...")
                    await self.disconnect()
                    if not await self.connect():
                        logger.error("Failed to reconnect after NOOP failure")
                        return 0
                    logger.info("Reconnected successfully after NOOP failure")
                
            except Exception as e:
                # Check if this is just a response parsing issue (common with some IMAP servers)
                error_str = str(e)
                if "unexpected response" in error_str and "OK Idle completed" in error_str:
                    logger.debug(f"NOOP response parsing issue (normal): {e}")
                    # This is actually fine - the connection is working, just response format issue
                else:
                    logger.warning(f"Error during connection reset: {e}, attempting reconnect...")
                    await self.disconnect()
                    if not await self.connect():
                        logger.error("Failed to reconnect after connection reset error")
                        return 0
                    logger.info("Reconnected successfully after connection reset error")
            
            # Now search for all emails with proper error handling
            try:
                logger.info(f"Executing search command...")
                result, data = self.imap.search(None, 'ALL')
                logger.info(f"Search result: {result}")
            except Exception as e:
                logger.error(f"Search command failed: {e}")
                # Try to reconnect and retry
                logger.info("Attempting to reconnect...")
                await self.disconnect()
                if await self.connect():    
                    logger.info("Reconnected successfully, retrying search...")
                    result, data = self.imap.search(None, 'ALL')
                    logger.info(f"Retry search result: {result}")
                else:
                    logger.error("Failed to reconnect")
                    return 0
            
            if result != 'OK':
                logger.error(f"Search failed: {result}")
                return 0
            
            if not data[0]:
                logger.debug("No new emails found")
                return 0
            
            message_nums = data[0].decode().split()
            logger.info(f"Found {len(message_nums)} total emails: {message_nums}")
            
            # Step 2: Filter emails by UID to identify only new emails
            # UID is persistent and doesn't change when emails are reordered
            new_message_nums = []
            for message_num in message_nums:
                try:
                    # Get the UID for this message
                    uid_result, uid_data = self.imap.fetch(message_num, '(UID)')
                    if uid_result == 'OK' and uid_data[0]:
                        uid_match = re.search(r'UID (\d+)', uid_data[0].decode())
                        if uid_match:
                            uid = int(uid_match.group(1))
                            # Only process emails with UID higher than last processed
                            if uid > self.last_uid:
                                new_message_nums.append(message_num)
                                logger.info(f"Found new email: message {message_num}, UID {uid}")
                except Exception as e:
                    logger.error(f"Error getting UID for message {message_num}: {e}")
            
            logger.info(f"Found {len(new_message_nums)} new emails to process: {new_message_nums}")
            
            # Step 3: Process each new email
            processed_count = 0
            
            for message_num in new_message_nums:
                try:
                    logger.info(f"Processing message number: {message_num}")
                    
                    # Step 3a: Fetch complete email data
                    email_data = await self._fetch_email(message_num)
                    if email_data:
                        logger.info(f"Email fetched successfully: {email_data.get('subject', 'No subject')}")
                        
                        # Step 3b: Submit to webhook with retry logic
                        logger.info(f"Submitting email to webhook...")
                        success = await self._submit_to_api_with_retry(email_data)
                        if success:
                            logger.info(f"Email submitted successfully to webhook")
                            processed_count += 1
                            
                            # Step 3c: Update last_uid to track progress
                            if email_data.get('uid'):
                                self.last_uid = max(self.last_uid, email_data['uid'])
                        else:
                            logger.error(f"Failed to submit email to webhook after retries")
                    else:
                        logger.error(f"Failed to fetch email data for message {message_num}")
                
                except Exception as e:
                    # Log detailed error information for debugging
                    logger.error(f"Error processing email {message_num}: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            
            return processed_count
            
        except Exception as e:
            logger.error(f"Error processing new emails: {e}")
            self.stats["connection_errors"] += 1
            return 0
    
    async def _idle_wait(self) -> bool:
        """
        Wait for IDLE notifications using raw IMAP protocol.
        
        This method implements the IMAP IDLE protocol to receive real-time
        notifications from the email server when new emails arrive. It uses
        raw socket communication for better control over the IDLE session.
        
        The IDLE protocol allows the server to push notifications to the client
        instead of the client constantly polling for new emails, making it
        much more efficient.
        
        Returns:
            bool: True if new email notification received, False otherwise
            
        IDLE Protocol Flow:
            1. Send IDLE command to server
            2. Wait for server acceptance (+ idling)
            3. Listen for notifications (EXISTS, EXPUNGE, FLAGS)
            4. Send DONE command to exit IDLE mode
        """
        # Verify IDLE support and connection
        if not self.imap or not self.server_supports_idle:
            return False
        
        try:
            logger.info("Starting IDLE mode using raw IMAP protocol...")
            
            # Step 1: Send IDLE command to server
            tag = self.imap._new_tag()
            self.imap.send(f"{tag} IDLE\r\n".encode('utf-8'))
            
            # Step 2: Wait for server response
            response = self.imap.readline()
            if response:
                response_str = response.decode('utf-8', errors='ignore')
                logger.info(f"IDLE response: {response_str}")
                
                # Step 3: Check if IDLE was accepted by server
                if response_str.startswith('+') and 'idling' in response_str:
                    logger.info("IDLE command accepted, waiting for notifications...")
                    
                    # Step 4: Wait for server notifications with timeout
                    start_time = time.time()
                    timeout = self.idle_timeout  # Configurable timeout
                    
                    while time.time() - start_time < timeout:
                        try:
                            # Read server response with timeout
                            response = self.imap.readline()
                            if response:
                                response_str = response.decode('utf-8', errors='ignore')
                                logger.info(f"IDLE notification: {response_str}")
                                
                                # Check for EXISTS notification (new message received)
                                if 'EXISTS' in response_str:
                                    logger.info("New email notification received!")
                                    return True
                                
                                # Check for EXPUNGE notification (message deleted)
                                if 'EXPUNGE' in response_str:
                                    logger.info("Email deleted notification received!")
                                    return True
                                
                                # Check for FLAGS notification (message flags changed)
                                if 'FLAGS' in response_str:
                                    logger.info("Flag change notification received!")
                                    return True
                                
                                # Check for IDLE continuation (+)
                                if response_str.startswith('+'):
                                    logger.debug("IDLE continuation received")
                                    continue
                            
                        except Exception as e:
                            # Timeout or no response, continue waiting
                            logger.debug(f"IDLE read timeout: {e}")
                            pass
                        
                        # Small delay to prevent busy waiting
                        await asyncio.sleep(0.1)
                    
                    logger.info("IDLE timeout - no notifications received")
                    return False
                else:
                    logger.error(f"IDLE command rejected: {response_str}")
                    return False
            else:
                logger.error("No response from IDLE command")
                return False
                
        except Exception as e:
            logger.error(f"IDLE error: {e}")
            return False
        finally:
            # Step 5: Exit IDLE mode by sending DONE command
            # This is critical for proper IDLE protocol completion
            try:
                # Reset socket timeout before sending DONE
                self.imap.sock.settimeout(10.0)  # Set a reasonable timeout for DONE
                self.imap.send(b"DONE\r\n")
                
                # Read the OK response from server
                try:
                    response = self.imap.readline()
                    if response:
                        logger.info(f"IDLE DONE response: {response.decode('utf-8', errors='ignore')}")
                except Exception as e:
                    logger.debug(f"Could not read DONE response: {e}")
                finally:
                    # Reset socket timeout to normal after DONE
                    self.imap.sock.settimeout(None)
            except Exception as e:
                logger.error(f"Error sending DONE command: {e}")
                # If DONE fails, the connection is likely broken, so we'll need to reconnect
                try:
                    await self.disconnect()
                except:
                    pass
    
    async def start_monitoring(self):
        """
        Start the main email monitoring loop.
        
        This is the primary method that runs the continuous email monitoring service.
        It handles connection management, IDLE/polling mode selection, and error recovery.
        The method runs indefinitely until stop_monitoring() is called.
        
        Monitoring Modes:
        - IDLE Mode: Real-time notifications (preferred, more efficient)
        - Polling Mode: Periodic checks (fallback when IDLE not supported)
        
        Error Handling:
        - Automatic reconnection on connection failures
        - Exponential backoff for retry attempts
        - Comprehensive error logging and statistics
        """
        logger.info("Starting IMAP IDLE monitoring...")
        self.is_running = True
        self.stats["start_time"] = datetime.now()
        
        # Main monitoring loop
        while self.is_running:
            try:
                # Step 1: Ensure connection is established
                if not self.imap:
                    if not await self.connect():
                        logger.error("Failed to connect, retrying in 30 seconds...")
                        await asyncio.sleep(30)
                        continue
                
                # Step 2: Choose monitoring mode based on server capabilities
                if self.server_supports_idle:
                    # Use IDLE mode for real-time notifications (more efficient)
                    logger.info("Using IDLE mode with interval for system efficiency...")
                    idle_success = await self._idle_wait()
                    
                    if idle_success:
                        logger.info("IDLE detected new emails, processing...")
                        await self._process_new_emails()
                    else:
                        logger.info("IDLE timeout, no new emails detected")
                    
                    # Add interval between IDLE sessions to prevent server overload
                    logger.info(f"Waiting {self.check_interval} seconds before next IDLE session...")
                    await asyncio.sleep(self.check_interval)
                else:
                    # Fallback to polling mode if IDLE not supported
                    logger.info("Using polling mode...")
                    await self._process_new_emails()
                    await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                # Handle any unexpected errors in the monitoring loop
                logger.error(f"Error in monitoring loop: {e}")
                self.stats["connection_errors"] += 1
                
                # Disconnect and wait before retry to allow server recovery
                await self.disconnect()
                await asyncio.sleep(30)
        
        logger.info("Monitoring stopped")
    
    async def stop_monitoring(self):
        """
        Stop the email monitoring service gracefully.
        
        This method safely stops the monitoring loop and disconnects from
        the IMAP server. It ensures clean shutdown without leaving
        connections hanging.
        """
        logger.info("Stopping IMAP monitoring...")
        self.is_running = False
        await self.disconnect()
    
    def get_stats(self) -> Dict:
        """
        Get current monitoring statistics and performance metrics.
        
        Returns:
            Dict: Statistics including:
                - emails_processed: Number of emails successfully processed
                - connection_errors: Number of connection-related errors
                - webhook_errors: Number of webhook delivery failures
                - start_time: Service start timestamp
                - uptime: Current service uptime in seconds
        """
        stats = self.stats.copy()
        if stats["start_time"]:
            stats["uptime"] = (datetime.now() - stats["start_time"]).total_seconds()
        return stats

async def main():
    """
    Main function for standalone IMAP IDLE listener service.
    
    This function initializes and starts the email monitoring service
    with configuration loaded from environment variables. It handles
    graceful shutdown on interrupt signals.
    
    Environment Variables:
        IMAP_HOST: IMAP server hostname (default: lumenlighthouse.ai)
        IMAP_PORT: IMAP server port (default: 993)
        IMAP_USERNAME: Email account username (required)
        IMAP_PASSWORD: Email account password (required)
        EMAIL_WEBHOOK_ENDPOINT: Webhook URL for email delivery (default: http://localhost:8000/api/email/webhook)
        IMAP_MAILBOX: Mailbox to monitor (default: INBOX)
        IMAP_CHECK_INTERVAL: Interval between checks in seconds (default: 30)
        IMAP_MAX_RETRIES: Maximum retry attempts (default: 5)
        IMAP_RETRY_DELAY: Delay between retries in seconds (default: 60)
    """
    # Load configuration from environment variables with sensible defaults
    config = {
        "host": os.getenv("IMAP_HOST", "lumenlighthouse.ai"),           # IMAP server hostname
        "port": int(os.getenv("IMAP_PORT", "993")),                     # IMAP server port
        "username": os.getenv("IMAP_USERNAME"),                         # Email username (required)
        "password": os.getenv("IMAP_PASSWORD"),                         # Email password (required)
        "api_endpoint": os.getenv("EMAIL_WEBHOOK_ENDPOINT", "http://localhost:8000/api/email/webhook"),  # Webhook URL
        "mailbox": os.getenv("IMAP_MAILBOX", "INBOX"),                  # Mailbox to monitor
        "check_interval": int(os.getenv("IMAP_CHECK_INTERVAL", "30")),  # Check interval in seconds
        "max_retries": int(os.getenv("IMAP_MAX_RETRIES", "5")),         # Max retry attempts
        "retry_delay": int(os.getenv("IMAP_RETRY_DELAY", "60"))         # Retry delay in seconds
    }
    
    # Validate required configuration
    if not config["username"] or not config["password"]:
        logger.error("IMAP_USERNAME and IMAP_PASSWORD environment variables are required")
        return
    
    # Step 1: Create IMAP IDLE listener instance with configuration
    listener = IMAPIDLEListener(**config)
    
    try:
        # Step 2: Start the monitoring service
        await listener.start_monitoring()
    except KeyboardInterrupt:
        # Step 3: Handle graceful shutdown on interrupt signal (Ctrl+C)
        logger.info("Received interrupt signal")
    finally:
        # Step 4: Ensure clean shutdown regardless of how the service stops
        await listener.stop_monitoring()

# Entry point for standalone execution
if __name__ == "__main__":
    # Run the main function using asyncio event loop
    asyncio.run(main())
