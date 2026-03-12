#!/bin/bash
# Build script for TARS Dashboard
# Builds the React app and prepares it for deployment

set -e

echo "🔨 Building TARS Dashboard..."

# Navigate to dashboard directory
cd "$(dirname "$0")/dashboard"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Build the React app
echo "🏗️  Building React app..."
npm run build

echo "✅ Dashboard build complete!"
echo "📁 Build output: dashboard/dist/"
echo ""
echo "The Flask server will automatically serve the dashboard from this directory."
