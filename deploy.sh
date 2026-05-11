#!/bin/bash
# DevTools Hub - Deploy Script
set -e
cd "$(dirname "$0")"
echo "🔨 Building Hugo site..."
hugo --gc --minify
echo "✅ Build complete: public/"
if git remote -v | grep -q origin; then
    echo "📤 Pushing to GitHub..."
    git add -A
    git commit -m "site: auto-update $(date +%Y-%m-%d)"
    git push origin main
    echo "✅ Deployed!"
else
    echo "⚠️  No git remote configured."
    echo "   Run: git remote add origin <your-github-repo-url>"
fi
