#!/bin/bash

# DigiMasterJi Backend - AWS Deployment Script
# =============================================
# This script builds and deploys the backend to AWS Lambda
# using ECR for container images.
#
# Prerequisites:
# 1. AWS CLI configured with appropriate credentials
# 2. Docker installed and running
# 3. AWS resources created (see AWS_SETUP_GUIDE.md)
#
# Usage:
#   ./deploy.sh [environment]
#   
#   environment: dev, staging, prod (default: dev)

set -e

# Configuration
ENVIRONMENT="${1:-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="digimasterji-backend"
LAMBDA_FUNCTION_NAME="digimasterji-backend-${ENVIRONMENT}"
IMAGE_TAG="${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"

echo "=================================================="
echo "DigiMasterJi Backend Deployment"
echo "=================================================="
echo "Environment: ${ENVIRONMENT}"
echo "AWS Region: ${AWS_REGION}"
echo "AWS Account: ${AWS_ACCOUNT_ID}"
echo "ECR Repository: ${ECR_REPOSITORY}"
echo "Image Tag: ${IMAGE_TAG}"
echo "=================================================="

# Navigate to Backend directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# Step 1: Authenticate Docker with ECR
echo ""
echo "[1/5] Authenticating Docker with ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Step 2: Build Docker image
echo ""
echo "[2/5] Building Docker image..."
# --provenance=false prevents OCI manifest format which Lambda doesn't support
# --no-cache ensures fresh build with all current files
docker build \
    --platform linux/amd64 \
    --provenance=false \
    --no-cache \
    -t ${ECR_REPOSITORY}:${IMAGE_TAG} \
    -t ${ECR_REPOSITORY}:${ENVIRONMENT}-latest \
    .

# Step 3: Tag image for ECR
echo ""
echo "[3/5] Tagging image for ECR..."
FULL_IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"
docker tag ${ECR_REPOSITORY}:${IMAGE_TAG} ${FULL_IMAGE_URI}:${IMAGE_TAG}
docker tag ${ECR_REPOSITORY}:${ENVIRONMENT}-latest ${FULL_IMAGE_URI}:${ENVIRONMENT}-latest

# Step 4: Push to ECR
echo ""
echo "[4/5] Pushing image to ECR..."
docker push ${FULL_IMAGE_URI}:${IMAGE_TAG}
docker push ${FULL_IMAGE_URI}:${ENVIRONMENT}-latest

# Step 5: Update Lambda function
echo ""
echo "[5/5] Updating Lambda function..."

# Check if Lambda function exists
if aws lambda get-function --function-name ${LAMBDA_FUNCTION_NAME} 2>/dev/null; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name ${LAMBDA_FUNCTION_NAME} \
        --image-uri ${FULL_IMAGE_URI}:${IMAGE_TAG} \
        --region ${AWS_REGION}
    
    # Wait for update to complete
    echo "Waiting for Lambda update to complete..."
    aws lambda wait function-updated --function-name ${LAMBDA_FUNCTION_NAME}
else
    echo "Lambda function ${LAMBDA_FUNCTION_NAME} does not exist."
    echo "Please create it first using AWS Console or CLI."
    echo ""
    echo "Example command to create Lambda function:"
    echo "  aws lambda create-function \\"
    echo "    --function-name ${LAMBDA_FUNCTION_NAME} \\"
    echo "    --package-type Image \\"
    echo "    --code ImageUri=${FULL_IMAGE_URI}:${IMAGE_TAG} \\"
    echo "    --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/digimasterji-lambda-role \\"
    echo "    --timeout 120 \\"
    echo "    --memory-size 1024 \\"
    echo "    --region ${AWS_REGION}"
    exit 1
fi

echo ""
echo "=================================================="
echo "Deployment Complete!"
echo "=================================================="
echo "Image URI: ${FULL_IMAGE_URI}:${IMAGE_TAG}"
echo "Lambda Function: ${LAMBDA_FUNCTION_NAME}"
echo ""
echo "To test the deployment:"
echo "  aws lambda invoke --function-name ${LAMBDA_FUNCTION_NAME} --payload '{}' response.json"
echo ""
echo "=================================================="
