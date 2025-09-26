#!/bin/bash

# Test script for migration endpoints using curl
# Make sure to replace YOUR_ADMIN_TOKEN with a valid admin JWT token

BASE_URL="http://localhost:8000"
API_URL="$BASE_URL/api/monitoring"
ADMIN_TOKEN="YOUR_ADMIN_TOKEN_HERE"

echo "Testing Migration Endpoints with curl"
echo "===================================="

# Test 1: Get migration status
echo ""
echo "1. Testing GET /migrations/status"
echo "Command: curl -H \"Authorization: Bearer $ADMIN_TOKEN\" $API_URL/migrations/status"
echo ""

curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  "$API_URL/migrations/status" | jq '.' 2>/dev/null || echo "Response (raw):"

echo ""
echo "===================================="

# Test 2: Run migrations (commented out for safety)
echo ""
echo "2. Testing POST /migrations/upgrade (COMMENTED OUT FOR SAFETY)"
echo "To test this endpoint:"
echo "1. Replace YOUR_ADMIN_TOKEN with a valid admin token"
echo "2. Uncomment the curl command below"
echo "3. Ensure you're in a test environment"
echo ""

# Uncomment the following lines to test the upgrade endpoint
# echo "Command: curl -X POST -H \"Authorization: Bearer $ADMIN_TOKEN\" $API_URL/migrations/upgrade"
# echo ""
# 
# curl -s -w "\nHTTP Status: %{http_code}\n" \
#   -X POST \
#   -H "Authorization: Bearer $ADMIN_TOKEN" \
#   -H "Content-Type: application/json" \
#   "$API_URL/migrations/upgrade" | jq '.' 2>/dev/null || echo "Response (raw):"

echo ""
echo "===================================="
echo "Migration endpoint testing completed!"
echo ""
echo "Available endpoints:"
echo "- POST $API_URL/migrations/upgrade - Run database migrations"
echo "- GET  $API_URL/migrations/status - Check migration status"
echo ""
echo "Both endpoints require admin authentication."
