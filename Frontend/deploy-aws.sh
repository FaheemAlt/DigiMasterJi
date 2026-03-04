#!/bin/bash
set -e

# ==============================================================================
# DigiMasterJi Frontend Deployment to AWS S3 + CloudFront
# ==============================================================================

# Configuration - UPDATE THESE VALUES
BUCKET_NAME="${BUCKET_NAME:-digimasterji-frontend}"
DISTRIBUTION_ID="${DISTRIBUTION_ID:-YOUR_DISTRIBUTION_ID}"
API_URL="${VITE_API_URL:-https://your-api-gateway-url.amazonaws.com}"
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

# Upload to S3
echo -e "\n${YELLOW}📤 Uploading to S3 bucket: ${BUCKET_NAME}...${NC}"
aws s3 sync dist/ s3://${BUCKET_NAME} --delete --region ${AWS_REGION}
echo -e "${GREEN}✓ Files uploaded${NC}"

# Set cache headers for different file types
echo -e "\n${YELLOW}📋 Setting cache headers...${NC}"

# HTML files - no cache (always fetch latest)
echo "  → Setting no-cache for index.html..."
aws s3 cp s3://${BUCKET_NAME}/index.html s3://${BUCKET_NAME}/index.html \
  --metadata-directive REPLACE \
  --cache-control "public, max-age=0, must-revalidate" \
  --content-type "text/html" \
  --region ${AWS_REGION}

# JS/CSS files in assets - long cache (they have content hash in filename)
if aws s3 ls s3://${BUCKET_NAME}/assets/ --region ${AWS_REGION} &> /dev/null; then
    echo "  → Setting long cache for assets..."
    aws s3 cp s3://${BUCKET_NAME}/assets/ s3://${BUCKET_NAME}/assets/ \
      --recursive \
      --metadata-directive REPLACE \
      --cache-control "public, max-age=31536000, immutable" \
      --region ${AWS_REGION}
fi

# Service worker - no cache
if aws s3 ls s3://${BUCKET_NAME}/sw.js --region ${AWS_REGION} &> /dev/null; then
    echo "  → Setting no-cache for service worker..."
    aws s3 cp s3://${BUCKET_NAME}/sw.js s3://${BUCKET_NAME}/sw.js \
      --metadata-directive REPLACE \
      --cache-control "public, max-age=0, must-revalidate" \
      --content-type "application/javascript" \
      --region ${AWS_REGION}
fi

echo -e "${GREEN}✓ Cache headers configured${NC}"

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
