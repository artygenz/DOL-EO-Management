#!/bin/bash

# Database Export Script
# Usage: ./scripts/db_export.sh

echo "🔄 Exporting database data..."
echo "This will capture all current data and save it to database_seed.sql"

# Run the export service
docker-compose run --rm export-db

echo "✅ Database export completed!"
echo "📁 Data saved to: database_seed.sql"
echo ""
echo "To import this data on another machine:"
echo "  docker-compose run --rm import-db"
