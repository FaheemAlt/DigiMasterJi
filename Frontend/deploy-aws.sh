#!/bin/bash
set -e

# ==============================================================================
# DigiMasterJi Frontend Deployment to AWS S3 + CloudFront
# ==============================================================================

# Configuration - UPDATE THESE VALUES
BUCKET_NAME="${BUCKET_NAME:-digimasterji-frontend}"
DISTRIBUTION_ID="${DISTRIBUTION_ID:-E34QM4YOG4C7AN}"
API_URL="${VITE_API_URL:-https://mfs8g8ik2k.execute-api.us-east-1.amazonaws.com}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 DigiMasterJi Frontend Deployment${NC}"
echo "================================================"

# Check if required tools are installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm is not installed. Please install Node.js first.${NC}"
    exit 1
fi

# Verify AWS credentials
echo -e "\n${YELLOW}🔑 Verifying AWS credentials...${NC}"
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured. Run 'aws configure' first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ AWS credentials verified${NC}"

# Check if Distribution ID is set
if [ "$DISTRIBUTION_ID" == "YOUR_DISTRIBUTION_ID" ]; then
    echo -e "${RED}❌ Please set DISTRIBUTION_ID environment variable or update this script.${NC}"
    echo "   Example: DISTRIBUTION_ID=EXXXXXXXX ./deploy-aws.sh"
    exit 1
fi

# Build the frontend
echo -e "\n${YELLOW}🏗️  Building frontend...${NC}"
VITE_API_URL=$API_URL npm run build

if [ ! -d "dist" ]; then
    echo -e "${RED}❌ Build failed - dist directory not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Build completed${NC}"

# Upload to S3 with correct MIME types and cache headers per file type
# NOTE: Each file type is uploaded separately to ensure correct Content-Type headers.
# Using a single "sync" then "cp --metadata-directive REPLACE" wipes the Content-Type
# causing browsers to reject JS/CSS as binary/octet-stream in strict mode.
echo -e "\n${YELLOW}📤 Uploading to S3 bucket: ${BUCKET_NAME}...${NC}"

# 1. HTML files — no cache (always fetch fresh)
echo "  → HTML files (no-cache)..."
aws s3 sync dist/ s3://${BUCKET_NAME} \
  --region ${AWS_REGION} \
  --exclude "*" --include "*.html" \
  --content-type "text/html; charset=utf-8" \
  --cache-control "public, max-age=0, must-revalidate" \
  --delete

# 2. JavaScript files — long cache (Vite adds content hash to filenames)
echo "  → JavaScript files (1-year cache)..."
aws s3 sync dist/ s3://${BUCKET_NAME} \
  --region ${AWS_REGION} \
  --exclude "*" --include "*.js" \
  --content-type "application/javascript" \
  --cache-control "public, max-age=31536000, immutable"

# 3. CSS files — long cache
echo "  → CSS files (1-year cache)..."
aws s3 sync dist/ s3://${BUCKET_NAME} \
  --region ${AWS_REGION} \
  --exclude "*" --include "*.css" \
  --content-type "text/css" \
  --cache-control "public, max-age=31536000, immutable"

# 4. Web manifest — no cache
echo "  → Web manifest (no-cache)..."
aws s3 sync dist/ s3://${BUCKET_NAME} \
  --region ${AWS_REGION} \
  --exclude "*" --include "*.webmanifest" --include "manifest.json" \
  --content-type "application/manifest+json" \
  --cache-control "public, max-age=0, must-revalidate"

# 5. Service worker — no cache (must always be latest version)
echo "  → Service worker (no-cache)..."
aws s3 sync dist/ s3://${BUCKET_NAME} \
  --region ${AWS_REGION} \
  --exclude "*" --include "sw.js" \
  --content-type "application/javascript" \
  --cache-control "public, max-age=0, must-revalidate"

# 6. Images & fonts — long cache
echo "  → Images & fonts (1-year cache)..."
aws s3 sync dist/ s3://${BUCKET_NAME} \
  --region ${AWS_REGION} \
  --exclude "*" \
  --include "*.png" --include "*.jpg" --include "*.jpeg" \
  --include "*.gif" --include "*.svg" --include "*.ico" \
  --include "*.woff" --include "*.woff2" --include "*.ttf" \
  --cache-control "public, max-age=31536000, immutable"

# 7. Everything else (fallback) — remove files deleted from dist
echo "  → Syncing remaining files & removing deleted..."
aws s3 sync dist/ s3://${BUCKET_NAME} \
  --region ${AWS_REGION} \
  --exclude "*.html" --exclude "*.js" --exclude "*.css" \
  --exclude "*.webmanifest" --exclude "manifest.json" \
  --exclude "*.png" --exclude "*.jpg" --exclude "*.jpeg" \
  --exclude "*.gif" --exclude "*.svg" --exclude "*.ico" \
  --exclude "*.woff" --exclude "*.woff2" --exclude "*.ttf" \
  --delete

echo -e "${GREEN}✓ Files uploaded with correct MIME types and cache headers${NC}"

# Invalidate CloudFront cache
echo -e "\n${YELLOW}🔄 Invalidating CloudFront cache...${NC}"
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id ${DISTRIBUTION_ID} \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text)

echo -e "${GREEN}✓ Cache invalidation started (ID: ${INVALIDATION_ID})${NC}"

# Get CloudFront domain
CLOUDFRONT_DOMAIN=$(aws cloudfront get-distribution \
  --id ${DISTRIBUTION_ID} \
  --query 'Distribution.DomainName' \
  --output text)

echo -e "\n${GREEN}================================================${NC}"
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo -e "\n🌐 Site URL: ${YELLOW}https://${CLOUDFRONT_DOMAIN}${NC}"
echo -e "\n📝 Note: CloudFront cache invalidation may take a few minutes to propagate globally."
