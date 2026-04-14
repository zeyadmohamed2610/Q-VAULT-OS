#!/bin/bash
# Q-VAULT OS GitHub Deployment Script
# Run this script to push to GitHub

echo "🚀 Q-VAULT OS - GitHub Deployment"

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install Git first."
    exit 1
fi

# Initialize git if not already
if [ ! -d .git ]; then
    echo "📦 Initializing Git repository..."
    git init
fi

# Configure git (replace with your info)
echo "⚙️ Configuring Git..."
git config user.name "Zeyad Mohamed"
git config user.email "zeyadmohamed2610@gmail.com"

# Add all files
echo "📝 Adding files to staging..."
git add .

# Check status
echo "📊 Checking status..."
git status

# Create commit
echo "💾 Creating commit..."
git commit -m "🚀 Q-VAULT OS v1.2.0 - Initial SaaS Release

Features:
- Advanced Security Engine with Behavior AI
- Supabase Cloud Integration
- Plugin System with SDK
- Licensing & Payment System
- Analytics & Crash Reporting
- Production-ready architecture"

# Set main branch
echo "🌿 Setting up main branch..."
git branch -M main

# Check if remote exists
if git remote -v | grep -q origin; then
    echo "Remote 'origin' already exists"
else
    echo "🔗 Adding remote origin..."
    git remote add origin https://github.com/zeyadmohamed2610/Q-VAULT-OS.git
fi

# Push to GitHub
echo "📤 Pushing to GitHub..."
git push -u origin main

echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Go to: https://github.com/zeyadmohamed2610/Q-VAULT-OS"
echo "2. Create a new Release (v1.2.0)"
echo "3. Upload your built executable (if any)"
echo "4. Share with the world! 🌍"