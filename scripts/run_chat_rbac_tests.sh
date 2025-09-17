#!/bin/bash

# Chat RBAC Test Runner Script
# This script runs the RBAC tests in the Docker environment

set -e

echo "🚀 Starting Chat RBAC Tests in Docker Environment"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found. Please run this script from the project root."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker first."
    exit 1
fi

echo "📋 Checking Docker services status..."

# Start required services
echo "🔧 Starting required services..."
docker-compose up -d db redis

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
timeout=60
counter=0
while ! docker-compose exec -T db pg_isready -U dol_user -d dol_db > /dev/null 2>&1; do
    if [ $counter -ge $timeout ]; then
        echo "❌ Error: Database failed to start within $timeout seconds"
        exit 1
    fi
    echo "   Waiting for database... ($counter/$timeout)"
    sleep 2
    counter=$((counter + 2))
done

echo "✅ Database is ready"

# Wait for Redis to be ready
echo "⏳ Waiting for Redis to be ready..."
timeout=30
counter=0
while ! docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; do
    if [ $counter -ge $timeout ]; then
        echo "❌ Error: Redis failed to start within $timeout seconds"
        exit 1
    fi
    echo "   Waiting for Redis... ($counter/$timeout)"
    sleep 2
    counter=$((counter + 2))
done

echo "✅ Redis is ready"

# Run database migrations
echo "🔄 Running database migrations..."
docker-compose run --rm migrate

# Start the API service
echo "🚀 Starting API service..."
docker-compose up -d api

# Wait for API to be ready
echo "⏳ Waiting for API to be ready..."
timeout=60
counter=0
while ! curl -s http://localhost:8000/health > /dev/null 2>&1; do
    if [ $counter -ge $timeout ]; then
        echo "❌ Error: API failed to start within $timeout seconds"
        echo "📋 API logs:"
        docker-compose logs api
        exit 1
    fi
    echo "   Waiting for API... ($counter/$timeout)"
    sleep 2
    counter=$((counter + 2))
done

echo "✅ API is ready"

# Check if we have the required environment variables
echo "🔍 Checking environment variables..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY not set. Some tests may fail."
    echo "   Set OPENAI_API_KEY in your .env file or environment"
fi

# Run the RBAC tests
echo "🧪 Running Chat RBAC Tests..."
echo "=============================="

# Set environment variable to indicate we're in Docker
export DOCKER_ENV=1

# Run the test script
docker-compose run --rm -e DOCKER_ENV=1 -e OPENAI_API_KEY="$OPENAI_API_KEY" api python scripts/test_chat_rbac.py

# Capture the exit code
TEST_EXIT_CODE=$?

echo ""
echo "📊 Test Results Summary"
echo "======================="

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All RBAC tests passed!"
else
    echo "❌ Some RBAC tests failed (exit code: $TEST_EXIT_CODE)"
fi

# Show recent logs if tests failed
if [ $TEST_EXIT_CODE -ne 0 ]; then
    echo ""
    echo "📋 Recent API logs (last 20 lines):"
    docker-compose logs --tail=20 api
fi

# Cleanup (optional - comment out if you want to keep services running)
echo ""
echo "🧹 Cleaning up services..."
docker-compose down

echo "🏁 Test execution completed"
exit $TEST_EXIT_CODE
