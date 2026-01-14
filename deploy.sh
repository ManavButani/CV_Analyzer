#!/bin/bash
# Deployment script for CV Analyzer

set -e

echo "🚀 Starting CV Analyzer Deployment..."

# Check if AWS credentials are configured
if [ -z "$AWS_ACCESS_KEY_ID" ] && [ -z "$AWS_PROFILE" ]; then
    echo "⚠️  Warning: AWS credentials not found. Please configure:"
    echo "   - Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, OR"
    echo "   - Configure AWS CLI: aws configure, OR"
    echo "   - Set AWS_PROFILE environment variable"
    echo ""
    echo "Continuing with CDK bootstrap (will fail if credentials are missing)..."
fi

# Install CDK dependencies if not already installed
if ! command -v cdk &> /dev/null; then
    echo "📦 Installing AWS CDK..."
    npm install -g aws-cdk
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install CDK Python dependencies
echo "📦 Installing CDK Python dependencies..."
pip install aws-cdk-lib constructs

# Bootstrap CDK (only needed once per account/region)
echo "🔧 Bootstrapping CDK (if not already done)..."
cdk bootstrap || echo "Bootstrap may have already been completed"

# Synthesize CloudFormation template
echo "📝 Synthesizing CloudFormation template..."
cdk synth

# Deploy the stack
echo "🚀 Deploying infrastructure..."
cdk deploy --require-approval never

echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Get the Load Balancer URL from the outputs above"
echo "   2. Update AWS Secrets Manager with your API keys:"
echo "      - JWT_SECRET"
echo "      - OPENAI_API_KEY (or GEMINI_API_KEY, GROK_API_KEY)"
echo "   3. Test the API endpoint: <LoadBalancerURL>/scrapper_application/docs"
