"""
Email Service Manager

This module manages the IMAP IDLE listener service as a background process.
It provides start/stop functionality and service monitoring.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional, Dict, Any
from datetime import datetime
import os

from .imap_idle_listener import IMAPIDLEListener

logger = logging.getLogger(__name__)

class EmailServiceManager:
    """
    Manages the IMAP IDLE listener service
    """
    
    def __init__(self):
        self.listener: Optional[IMAPIDLEListener] = None
        self.is_running = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
    async def start_service(self) -> bool:
        """Start the email monitoring service"""
        try:
            logger.info("Starting Email Service Manager")
            
            # Create IMAP IDLE listener
            self.listener = IMAPIDLEListener(
                host=os.getenv("IMAP_HOST", "lumenlighthouse.ai"),
                port=int(os.getenv("IMAP_PORT", "993")),
                username=os.getenv("IMAP_USERNAME"),
                password=os.getenv("IMAP_PASSWORD"),

                webhook_url=os.getenv("EMAIL_WEBHOOK_ENDPOINT", "http://localhost:80/api/email/webhook"),
                check_interval=int(os.getenv("IMAP_CHECK_INTERVAL", "60")),  # 60 seconds between sessions
                idle_timeout=int(os.getenv("IMAP_IDLE_TIMEOUT", "30")),      # 30 seconds IDLE timeout
                use_ssl=True
            )
            
            # Start monitoring
            self.monitoring_task = asyncio.create_task(
                self.listener.start_monitoring()
            )
            
            self.is_running = True
            logger.info("Email Service Manager started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Email Service Manager: {e}")
            return False
    
    async def stop_service(self):
        """Stop the email monitoring service"""
        try:
            logger.info("Stopping Email Service Manager")
            
            if self.listener:
                await self.listener.stop_monitoring()
                self.listener = None
            
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
                self.monitoring_task = None
            
            self.is_running = False
            logger.info("Email Service Manager stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Email Service Manager: {e}")
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get current service status"""
        status = {
            "is_running": self.is_running,
            "listener_connected": False,
            "listener_stats": None,
            "last_check": datetime.now().isoformat()
        }
        
        if self.listener:
            status["listener_connected"] = self.listener.imap is not None
            status["listener_stats"] = self.listener.get_stats()
        
        return status
    
    async def restart_service(self) -> bool:
        """Restart the email monitoring service"""
        logger.info("Restarting Email Service Manager")
        
        await self.stop_service()
        await asyncio.sleep(2)  # Brief pause between stop and start
        
        return await self.start_service()

# Global service manager instance
service_manager = EmailServiceManager()

def signal_handler(signum, frame):
    """Handle system signals for graceful shutdown"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    asyncio.create_task(service_manager.stop_service())

async def run_service():
    """Run the email service as a standalone process"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start the service
        success = await service_manager.start_service()
        if not success:
            logger.error("Failed to start email service")
            return
        
        # Keep the service running
        while service_manager.is_running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error in email service: {e}")
    finally:
        await service_manager.stop_service()

def start_email_service():
    """Start the email service (blocking)"""
    asyncio.run(run_service())

if __name__ == "__main__":
    # Configure logging for standalone mode
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    start_email_service()
