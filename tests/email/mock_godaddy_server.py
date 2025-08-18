# tests/email/mock_godaddy_server.py
import socket
import threading
import time
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from queue import Queue, Empty
import ssl


@dataclass
class MockEmail:
    """Mock email for testing"""
    uid: int
    subject: str
    sender: str
    body: str
    flags: List[str]
    received_date: datetime


class MockGoDaddyIMAPServer:
    """
    Mock GoDaddy IMAP server for testing IDLE functionality.
    Simulates real IMAP server behavior including IDLE support.
    """
    
    def __init__(self, 
                 host: str = "localhost",
                 port: int = 9993,
                 idle_supported: bool = True,
                 idle_timeout: int = 1740):  # 29 minutes
        
        self.host = host
        self.port = port
        self.idle_supported = idle_supported
        self.idle_timeout = idle_timeout
        
        # Server state
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        self.server_thread: Optional[threading.Thread] = None
        self.client_handlers: List[threading.Thread] = []
        
        # Mock mailbox data
        self.mailboxes: Dict[str, List[MockEmail]] = {
            "INBOX": [
                MockEmail(1, "Test Email 1", "sender1@example.com", "Body 1", ["\\Seen"], datetime.now()),
                MockEmail(2, "Test Email 2", "sender2@example.com", "Body 2", [], datetime.now()),
                MockEmail(3, "Test Email 3", "sender3@example.com", "Body 3", [], datetime.now()),
            ]
        }
        
        # IDLE session tracking
        self.idle_sessions: Dict[str, Dict] = {}
        self.event_queue: Queue = Queue()
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Callbacks for testing
        self.connection_callbacks: List[Callable] = []
        self.idle_callbacks: List[Callable] = []
    
    def start(self) -> None:
        """Start the mock IMAP server"""
        if self.running:
            return
        
        self.logger.info(f"Starting mock GoDaddy IMAP server on {self.host}:{self.port}")
        
        # Create server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        
        self.running = True
        
        # Start server thread
        self.server_thread = threading.Thread(
            target=self._server_worker,
            daemon=True,
            name="MockIMAPServer"
        )
        self.server_thread.start()
        
        # Wait for server to be ready
        time.sleep(0.1)
        
        self.logger.info("Mock GoDaddy IMAP server started")
    
    def stop(self) -> None:
        """Stop the mock IMAP server"""
        if not self.running:
            return
        
        self.logger.info("Stopping mock GoDaddy IMAP server")
        
        self.running = False
        
        # Close server socket
        if self.server_socket:
            self.server_socket.close()
        
        # Wait for server thread to finish
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=2)
        
        # Wait for client handlers to finish
        for handler in self.client_handlers:
            if handler.is_alive():
                handler.join(timeout=1)
        
        self.logger.info("Mock GoDaddy IMAP server stopped")
    
    def _server_worker(self) -> None:
        """Main server worker thread"""
        while self.running:
            try:
                # Accept client connections
                client_socket, address = self.server_socket.accept()
                self.logger.info(f"Client connected from {address}")
                
                # Notify connection callbacks
                for callback in self.connection_callbacks:
                    try:
                        callback(address)
                    except Exception as e:
                        self.logger.error(f"Error in connection callback: {e}")
                
                # Handle client in separate thread
                handler = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True,
                    name=f"ClientHandler_{address[0]}_{address[1]}"
                )
                handler.start()
                self.client_handlers.append(handler)
                
            except OSError:
                # Socket closed, exit gracefully
                break
            except Exception as e:
                self.logger.error(f"Server worker error: {e}")
                if self.running:
                    time.sleep(0.1)
    
    def _handle_client(self, client_socket: socket.socket, address: tuple) -> None:
        """Handle individual client connection"""
        client_id = f"{address[0]}_{address[1]}"
        selected_mailbox = None
        authenticated = False
        idle_active = False
        
        try:
            # Send greeting
            self._send_response(client_socket, "* OK Mock GoDaddy IMAP Server ready")
            
            while self.running:
                try:
                    # Receive command
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    
                    command = data.decode('utf-8').strip()
                    self.logger.debug(f"Received command from {client_id}: {command}")
                    
                    # Parse command
                    parts = command.split(' ', 2)
                    if len(parts) < 2:
                        continue
                    
                    tag = parts[0]
                    cmd = parts[1].upper()
                    args = parts[2] if len(parts) > 2 else ""
                    
                    # Handle commands
                    if cmd == "CAPABILITY":
                        self._handle_capability(client_socket, tag)
                    
                    elif cmd == "LOGIN":
                        authenticated = self._handle_login(client_socket, tag, args)
                    
                    elif cmd == "SELECT":
                        if authenticated:
                            selected_mailbox = self._handle_select(client_socket, tag, args)
                        else:
                            self._send_response(client_socket, f"{tag} NO Not authenticated")
                    
                    elif cmd == "IDLE":
                        if authenticated and selected_mailbox:
                            idle_active = self._handle_idle(client_socket, tag, client_id, selected_mailbox)
                        else:
                            self._send_response(client_socket, f"{tag} NO Not authenticated or no mailbox selected")
                    
                    elif cmd == "NOOP":
                        if authenticated:
                            self._send_response(client_socket, f"{tag} OK NOOP completed")
                        else:
                            self._send_response(client_socket, f"{tag} NO Not authenticated")
                    
                    elif cmd == "LOGOUT":
                        self._send_response(client_socket, "* BYE Logging out")
                        self._send_response(client_socket, f"{tag} OK LOGOUT completed")
                        break
                    
                    elif command == "DONE":
                        if idle_active:
                            idle_active = False
                            self._end_idle_session(client_id)
                            self._send_response(client_socket, f"A001 OK IDLE terminated")
                        else:
                            self._send_response(client_socket, "* BAD DONE without IDLE")
                    
                    else:
                        self._send_response(client_socket, f"{tag} BAD Unknown command")
                
                except socket.timeout:
                    continue
                except Exception as e:
                    self.logger.error(f"Error handling client {client_id}: {e}")
                    break
        
        except Exception as e:
            self.logger.error(f"Client handler error for {client_id}: {e}")
        
        finally:
            # Cleanup
            if idle_active:
                self._end_idle_session(client_id)
            
            try:
                client_socket.close()
            except:
                pass
            
            self.logger.info(f"Client {client_id} disconnected")
    
    def _send_response(self, client_socket: socket.socket, response: str) -> None:
        """Send response to client"""
        try:
            response_bytes = (response + "\r\n").encode('utf-8')
            client_socket.send(response_bytes)
            self.logger.debug(f"Sent response: {response}")
        except Exception as e:
            self.logger.error(f"Error sending response: {e}")
    
    def _handle_capability(self, client_socket: socket.socket, tag: str) -> None:
        """Handle CAPABILITY command"""
        capabilities = ["IMAP4rev1", "STARTTLS", "AUTH=PLAIN", "AUTH=LOGIN"]
        
        if self.idle_supported:
            capabilities.append("IDLE")
        
        capability_str = " ".join(capabilities)
        self._send_response(client_socket, f"* CAPABILITY {capability_str}")
        self._send_response(client_socket, f"{tag} OK CAPABILITY completed")
    
    def _handle_login(self, client_socket: socket.socket, tag: str, args: str) -> bool:
        """Handle LOGIN command"""
        # Simple authentication - accept any credentials
        self._send_response(client_socket, f"{tag} OK LOGIN completed")
        return True
    
    def _handle_select(self, client_socket: socket.socket, tag: str, args: str) -> Optional[str]:
        """Handle SELECT command"""
        # Extract mailbox name
        mailbox = args.strip('"')
        
        if mailbox in self.mailboxes:
            email_count = len(self.mailboxes[mailbox])
            recent_count = len([e for e in self.mailboxes[mailbox] if "\\Recent" in e.flags])
            
            self._send_response(client_socket, f"* {email_count} EXISTS")
            self._send_response(client_socket, f"* {recent_count} RECENT")
            self._send_response(client_socket, "* OK [UIDVALIDITY 1] UIDs valid")
            self._send_response(client_socket, f"* OK [UIDNEXT {email_count + 1}] Predicted next UID")
            self._send_response(client_socket, "* FLAGS (\\Answered \\Flagged \\Deleted \\Seen \\Draft)")
            self._send_response(client_socket, "* OK [PERMANENTFLAGS (\\Answered \\Flagged \\Deleted \\Seen \\Draft \\*)] Limited")
            self._send_response(client_socket, f"{tag} OK [READ-WRITE] SELECT completed")
            
            return mailbox
        else:
            self._send_response(client_socket, f"{tag} NO Mailbox doesn't exist")
            return None
    
    def _handle_idle(self, client_socket: socket.socket, tag: str, client_id: str, mailbox: str) -> bool:
        """Handle IDLE command"""
        if not self.idle_supported:
            self._send_response(client_socket, f"{tag} NO IDLE not supported")
            return False
        
        # Start IDLE session
        self._send_response(client_socket, "+ idling")
        
        # Track IDLE session
        self.idle_sessions[client_id] = {
            'socket': client_socket,
            'mailbox': mailbox,
            'started': datetime.now(),
            'tag': tag
        }
        
        # Notify IDLE callbacks
        for callback in self.idle_callbacks:
            try:
                callback(client_id, mailbox)
            except Exception as e:
                self.logger.error(f"Error in IDLE callback: {e}")
        
        self.logger.info(f"Started IDLE session for client {client_id} on mailbox {mailbox}")
        
        # Start IDLE monitoring thread
        idle_thread = threading.Thread(
            target=self._idle_monitor,
            args=(client_id,),
            daemon=True,
            name=f"IdleMonitor_{client_id}"
        )
        idle_thread.start()
        
        return True
    
    def _idle_monitor(self, client_id: str) -> None:
        """Monitor IDLE session and send events"""
        session = self.idle_sessions.get(client_id)
        if not session:
            return
        
        client_socket = session['socket']
        mailbox = session['mailbox']
        start_time = session['started']
        
        try:
            while client_id in self.idle_sessions and self.running:
                # Check for timeout
                if (datetime.now() - start_time).total_seconds() > self.idle_timeout:
                    self.logger.info(f"IDLE session {client_id} timed out")
                    break
                
                # Check for events in queue
                try:
                    event = self.event_queue.get(timeout=1.0)
                    
                    if event['client_id'] == client_id or event['client_id'] == 'all':
                        # Send event to client
                        if event['type'] == 'new_email':
                            self._send_response(client_socket, f"* {event['count']} EXISTS")
                        elif event['type'] == 'email_deleted':
                            self._send_response(client_socket, f"* {event['sequence']} EXPUNGE")
                        elif event['type'] == 'email_flagged':
                            self._send_response(client_socket, f"* {event['sequence']} FETCH (FLAGS ({event['flags']}))")
                        elif event['type'] == 'connection_close':
                            self._send_response(client_socket, "* BYE Server shutting down")
                            break
                    
                except Empty:
                    continue
                except Exception as e:
                    self.logger.error(f"Error processing IDLE event: {e}")
                    break
        
        except Exception as e:
            self.logger.error(f"IDLE monitor error for {client_id}: {e}")
        
        finally:
            # Cleanup IDLE session
            if client_id in self.idle_sessions:
                del self.idle_sessions[client_id]
    
    def _end_idle_session(self, client_id: str) -> None:
        """End IDLE session"""
        if client_id in self.idle_sessions:
            del self.idle_sessions[client_id]
            self.logger.info(f"Ended IDLE session for client {client_id}")
    
    # Test helper methods
    
    def simulate_new_email(self, client_id: str = 'all', email_count: int = 5) -> None:
        """Simulate new email arrival"""
        event = {
            'type': 'new_email',
            'client_id': client_id,
            'count': email_count
        }
        self.event_queue.put(event)
        self.logger.info(f"Simulated new email event for client {client_id}")
    
    def simulate_email_deleted(self, client_id: str = 'all', sequence: int = 3) -> None:
        """Simulate email deletion"""
        event = {
            'type': 'email_deleted',
            'client_id': client_id,
            'sequence': sequence
        }
        self.event_queue.put(event)
        self.logger.info(f"Simulated email deleted event for client {client_id}")
    
    def simulate_email_flagged(self, client_id: str = 'all', sequence: int = 2, flags: str = "\\Seen") -> None:
        """Simulate email flag change"""
        event = {
            'type': 'email_flagged',
            'client_id': client_id,
            'sequence': sequence,
            'flags': flags
        }
        self.event_queue.put(event)
        self.logger.info(f"Simulated email flagged event for client {client_id}")
    
    def simulate_connection_close(self, client_id: str = 'all') -> None:
        """Simulate server closing connection"""
        event = {
            'type': 'connection_close',
            'client_id': client_id
        }
        self.event_queue.put(event)
        self.logger.info(f"Simulated connection close event for client {client_id}")
    
    def add_connection_callback(self, callback: Callable) -> None:
        """Add callback for new connections"""
        self.connection_callbacks.append(callback)
    
    def add_idle_callback(self, callback: Callable) -> None:
        """Add callback for IDLE sessions"""
        self.idle_callbacks.append(callback)
    
    def get_active_idle_sessions(self) -> List[str]:
        """Get list of active IDLE session client IDs"""
        return list(self.idle_sessions.keys())
    
    def is_client_idle(self, client_id: str) -> bool:
        """Check if client has active IDLE session"""
        return client_id in self.idle_sessions
    
    def add_email_to_mailbox(self, mailbox: str, email: MockEmail) -> None:
        """Add email to mailbox"""
        if mailbox not in self.mailboxes:
            self.mailboxes[mailbox] = []
        
        self.mailboxes[mailbox].append(email)
        
        # Simulate new email event for all IDLE sessions
        new_count = len(self.mailboxes[mailbox])
        self.simulate_new_email('all', new_count)
    
    def remove_email_from_mailbox(self, mailbox: str, uid: int) -> bool:
        """Remove email from mailbox"""
        if mailbox not in self.mailboxes:
            return False
        
        emails = self.mailboxes[mailbox]
        for i, email in enumerate(emails):
            if email.uid == uid:
                del emails[i]
                # Simulate email deleted event
                self.simulate_email_deleted('all', i + 1)
                return True
        
        return False
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()


# Integration test helper
class MockGoDaddyServerIntegrationTest:
    """Helper class for integration testing with mock server"""
    
    def __init__(self, idle_supported: bool = True, port: int = 9993):
        self.server = MockGoDaddyIMAPServer(
            port=port,
            idle_supported=idle_supported
        )
        self.events_received = []
        self.connections_made = []
        self.idle_sessions_started = []
    
    def setup(self):
        """Setup test environment"""
        # Add callbacks to track events
        self.server.add_connection_callback(self._on_connection)
        self.server.add_idle_callback(self._on_idle_session)
        
        # Start server
        self.server.start()
        
        # Wait for server to be ready
        time.sleep(0.1)
    
    def teardown(self):
        """Teardown test environment"""
        self.server.stop()
    
    def _on_connection(self, address):
        """Track connections"""
        self.connections_made.append(address)
    
    def _on_idle_session(self, client_id, mailbox):
        """Track IDLE sessions"""
        self.idle_sessions_started.append((client_id, mailbox))
    
    def create_test_client_config(self):
        """Create client configuration for testing"""
        return {
            'imap_host': 'localhost',
            'imap_port': self.server.port,
            'smtp_host': 'localhost',
            'smtp_port': 465,
            'username': 'test@example.com',
            'password': 'testpass'
        }
    
    def wait_for_idle_session(self, timeout: float = 5.0) -> bool:
        """Wait for IDLE session to be established"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if len(self.idle_sessions_started) > 0:
                return True
            time.sleep(0.1)
        
        return False
    
    def simulate_email_events(self, delay: float = 0.5):
        """Simulate various email events with delays"""
        time.sleep(delay)
        self.server.simulate_new_email()
        
        time.sleep(delay)
        self.server.simulate_email_deleted()
        
        time.sleep(delay)
        self.server.simulate_email_flagged()
    
    def __enter__(self):
        """Context manager entry"""
        self.setup()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.teardown()


if __name__ == "__main__":
    # Simple test of mock server
    logging.basicConfig(level=logging.INFO)
    
    with MockGoDaddyIMAPServer() as server:
        print(f"Mock server running on {server.host}:{server.port}")
        print("Press Ctrl+C to stop...")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping server...")