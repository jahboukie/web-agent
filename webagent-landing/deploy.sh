#!/bin/bash

# WebAgent Landing Page Deployment Script
# This script builds and prepares the landing page for deployment

echo "🚀 Building WebAgent Landing Page..."

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Build the project
echo "🔨 Building project..."
npm run build

# Export static files
echo "📤 Exporting static files..."
npm run export

echo "✅ Build complete! Static files are in the 'out' directory."
echo ""
echo "🌐 Ready for deployment to:"
echo "   - Vercel: Connect GitHub repo and deploy"
echo "   - Netlify: Upload 'out' directory"
echo "   - Custom server: Upload 'out' directory contents"
echo ""
echo "🎉 The public face of WebAgent is ready to launch!"
