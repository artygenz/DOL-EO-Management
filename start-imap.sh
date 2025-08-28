#!/bin/bash

# Simple IMAP Service Startup Script
# Works with the main docker-compose.yml file

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Please create one with your IMAP credentials:"
    echo ""
    echo "IMAP_USERNAME=your_email@lumenlighthouse.ai"
    echo "IMAP_PASSWORD=your_app_password"
    echo "IMAP_HOST=lumenlighthouse.ai"
    echo "IMAP_PORT=993"
    echo "IMAP_MAILBOX=INBOX"
    echo ""
    exit 1
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p attachments logs

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

case "${1:-start}" in
    "start")
        print_status "Starting IMAP service with main stack..."
        docker-compose up -d imap-listener
        print_success "IMAP service started!"
        print_status "View logs: docker-compose logs -f imap-listener"
        ;;
    "stop")
        print_status "Stopping IMAP service..."
        docker-compose stop imap-listener
        print_success "IMAP service stopped!"
        ;;
    "restart")
        print_status "Restarting IMAP service..."
        docker-compose restart imap-listener
        print_success "IMAP service restarted!"
        ;;
    "logs")
        print_status "Showing IMAP service logs..."
        docker-compose logs -f imap-listener
        ;;
    "status")
        print_status "Checking IMAP service status..."
        if docker-compose ps imap-listener | grep -q "Up"; then
            print_success "IMAP service is running"
        else
            print_warning "IMAP service is not running"
        fi
        ;;
    "test")
        print_status "Testing webhook endpoint..."
        if curl -s http://localhost:8000/api/email/webhook/health > /dev/null; then
            print_success "Webhook endpoint is accessible"
        else
            print_warning "Webhook endpoint is not accessible. Make sure the API server is running."
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|status|test}"
        echo ""
        echo "Commands:"
        echo "  start   - Start IMAP service"
        echo "  stop    - Stop IMAP service"
        echo "  restart - Restart IMAP service"
        echo "  logs    - Show IMAP service logs"
        echo "  status  - Check IMAP service status"
        echo "  test    - Test webhook endpoint"
        exit 1
        ;;
esac
