#!/bin/bash

# Deploy to Vercel - Quick Deployment Script
# Run: ./deploy.sh

set -e

echo ""
echo "============================================"
echo "🌲 Deploying Donor Prospects to Vercel"
echo "============================================"
echo ""

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Installing..."
    npm install -g vercel
    echo "✅ Vercel CLI installed"
    echo ""
fi

# Check if logged in
echo "🔑 Checking Vercel authentication..."
if ! vercel whoami &> /dev/null; then
    echo "📝 Please log in to Vercel:"
    vercel login
else
    echo "✅ Already logged in to Vercel"
fi

echo ""
echo "🚀 Deploying to production..."
echo ""

# Deploy to production
vercel --prod

echo ""
echo "============================================"
echo "✅ Deployment Complete!"
echo "============================================"
echo ""
echo "Your donor prospect management interface is now live!"
echo ""
echo "Next steps:"
echo "  1. Open the Vercel URL shown above"
echo "  2. Test the filtering and search"
echo "  3. Try editing a prospect's cultivation data"
echo "  4. (Optional) Add a custom domain in Vercel dashboard"
echo ""
echo "============================================"
echo ""
