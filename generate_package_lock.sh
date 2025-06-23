#!/bin/bash
# Generate package-lock.json for consistent dependency management

echo "🚀 Generating package-lock.json for Aura frontend..."

# Navigate to aura directory
cd aura || {
    echo "❌ Error: aura directory not found"
    exit 1
}

# Check if package.json exists
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found in aura directory"
    exit 1
fi

echo "📦 Current package.json found"

# Remove existing node_modules and lock files for clean install
echo "🧹 Cleaning existing dependencies..."
rm -rf node_modules
rm -f package-lock.json
rm -f yarn.lock

# Install dependencies to generate package-lock.json
echo "📥 Installing dependencies and generating package-lock.json..."
npm install

# Check if package-lock.json was created
if [ -f "package-lock.json" ]; then
    echo "✅ package-lock.json generated successfully!"
    echo "📊 Lock file stats:"
    wc -l package-lock.json
    echo ""
    echo "🎯 Next steps:"
    echo "1. Review the generated package-lock.json"
    echo "2. Commit it to your repository:"
    echo "   git add aura/package-lock.json"
    echo "   git commit -m 'feat: add package-lock.json for consistent dependencies'"
    echo ""
    echo "3. Update your GitHub Actions workflow to re-enable caching:"
    echo "   cache: 'npm'"
    echo "   cache-dependency-path: 'aura/package-lock.json'"
    echo ""
    echo "✅ This will speed up your CI/CD builds by ~2-3 minutes!"
else
    echo "❌ Error: package-lock.json was not generated"
    exit 1
fi
