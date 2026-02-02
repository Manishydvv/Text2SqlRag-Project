#!/bin/bash
#
# Build and Push Lambda Base Image
#
# This script builds the Lambda base image with all system dependencies
# pre-installed and pushes it to ECR. This is a one-time operation that
# only needs to be repeated when system dependencies change.
#
# USAGE:
#   ./build-base-image.sh
#
# PREREQUISITES:
#   - AWS CLI configured with credentials
#   - Docker installed and running
#   - ECR repository 'lambda-python-deps' created
#
# TIME:
#   Initial build: ~25-30 minutes (one-time)
#   Subsequent deployments: ~5 minutes (85% faster!)
#

set -e  # Exit on error

# Configuration
AWS_ACCOUNT_ID="050451405297"
AWS_REGION="us-east-1"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
ECR_REPOSITORY="rag-text-to-sql"
IMAGE_TAG="3.12"
FULL_IMAGE_URI="${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"

echo "=========================================="
echo "🏗️  Building Lambda Base Image"
echo "=========================================="
echo "AWS Account: ${AWS_ACCOUNT_ID}"
echo "AWS Region: ${AWS_REGION}"
echo "ECR Repository: ${ECR_REPOSITORY}"
echo "Image Tag: ${IMAGE_TAG}"
echo "Full URI: ${FULL_IMAGE_URI}"
echo ""

# Step 1: Build the base image
echo "📦 Step 1: Building Docker image..."
echo "   Platform: linux/amd64 (x86-64)"
echo "   Dockerfile: Dockerfile.lambda.base"
echo ""

docker build \
  --platform linux/amd64 \
  -t "${FULL_IMAGE_URI}" \
  -f Dockerfile.lambda.base \
  .

echo ""
echo "✅ Build complete!"
echo ""

# Step 2: Login to ECR
echo "🔐 Step 2: Logging into Amazon ECR..."
aws ecr get-login-password --region "${AWS_REGION}" | \
  docker login --username AWS --password-stdin "${ECR_REGISTRY}"

echo "✅ Logged into ECR successfully!"
echo ""

# Step 3: Push to ECR
echo "📤 Step 3: Pushing image to ECR..."
echo "   This may take 2-5 minutes..."
echo ""

docker push "${FULL_IMAGE_URI}"

echo ""
echo "=========================================="
echo "✅ BASE IMAGE PUBLISHED SUCCESSFULLY!"
echo "=========================================="
echo ""
echo "📋 Image Details:"
echo "   URI: ${FULL_IMAGE_URI}"
echo "   Repository: ${ECR_REPOSITORY}"
echo "   Tag: ${IMAGE_TAG}"
echo "   Platform: linux/amd64"
echo ""
echo "🎉 Next Steps:"
echo "   1. The base image is now in ECR"
echo "   2. Dockerfile.lambda will automatically use it"
echo "   3. Deployments will be 6-7x faster (32 min → 5 min)"
echo ""
echo "💡 To rebuild (only when system deps change):"
echo "   ./build-base-image.sh"
echo ""
echo "🔗 View in AWS Console:"
echo "   https://console.aws.amazon.com/ecr/repositories/private/${AWS_ACCOUNT_ID}/${ECR_REPOSITORY}?region=${AWS_REGION}"
echo "=========================================="
