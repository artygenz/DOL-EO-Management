#!/bin/bash

# Test script for dedicated health check endpoints using curl
# Make sure to replace YOUR_ADMIN_TOKEN with a valid admin JWT token

BASE_URL="http://localhost:8000"
API_URL="$BASE_URL/api/monitoring"
ADMIN_TOKEN="YOUR_ADMIN_TOKEN_HERE"

echo "Testing Dedicated Health Check Endpoints with curl"
echo "================================================="

# Test 1: Database health check
echo ""
echo "1. Testing GET /health/database"
echo "Command: curl -H \"Authorization: Bearer $ADMIN_TOKEN\" $API_URL/health/database"
echo ""

curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  "$API_URL/health/database" | jq '.' 2>/dev/null || echo "Response (raw):"

echo ""
echo "================================================="

# Test 2: Redis health check
echo ""
echo "2. Testing GET /health/redis"
echo "Command: curl -H \"Authorization: Bearer $ADMIN_TOKEN\" $API_URL/health/redis"
echo ""

curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  "$API_URL/health/redis" | jq '.' 2>/dev/null || echo "Response (raw):"

echo ""
echo "================================================="

# Test 3: General health check (for comparison)
echo ""
echo "3. Testing GET /health/connections (for comparison)"
echo "Command: curl -H \"Authorization: Bearer $ADMIN_TOKEN\" $API_URL/health/connections"
echo ""

curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  "$API_URL/health/connections" | jq '.' 2>/dev/null || echo "Response (raw):"

echo ""
echo "================================================="
echo "Health endpoint testing completed!"
echo ""
echo "Available health endpoints:"
echo "- GET  $API_URL/health/database - Detailed database health check"
echo "- GET  $API_URL/health/redis - Detailed Redis health check"
echo "- GET  $API_URL/health/connections - General health check (all services)"
echo ""
echo "All endpoints require admin authentication."
echo ""
echo "Key differences:"
echo "- /health/database: Tests DB connectivity, table access, connection pool status"
echo "- /health/redis: Tests Redis connectivity, various operations, Redis info"
echo "- /health/connections: Tests all services but may return false positives"