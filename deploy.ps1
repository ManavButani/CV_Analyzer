# PowerShell deployment script for CV Analyzer

Write-Host "🚀 Starting CV Analyzer Deployment..." -ForegroundColor Green

# Check if AWS credentials are configured
if (-not $env:AWS_ACCESS_KEY_ID -and -not $env:AWS_PROFILE) {
    Write-Host "⚠️  Warning: AWS credentials not found. Please configure:" -ForegroundColor Yellow
    Write-Host "   - Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, OR" -ForegroundColor Yellow
    Write-Host "   - Configure AWS CLI: aws configure, OR" -ForegroundColor Yellow
    Write-Host "   - Set AWS_PROFILE environment variable" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Continuing with CDK bootstrap (will fail if credentials are missing)..." -ForegroundColor Yellow
}

# Install CDK dependencies if not already installed
if (-not (Get-Command cdk -ErrorAction SilentlyContinue)) {
    Write-Host "📦 Installing AWS CDK..." -ForegroundColor Cyan
    npm install -g aws-cdk
}

# Install Python dependencies
Write-Host "📦 Installing Python dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt

# Install CDK Python dependencies
Write-Host "📦 Installing CDK Python dependencies..." -ForegroundColor Cyan
pip install aws-cdk-lib constructs

# Bootstrap CDK (only needed once per account/region)
Write-Host "🔧 Bootstrapping CDK (if not already done)..." -ForegroundColor Cyan
cdk bootstrap
if ($LASTEXITCODE -ne 0) {
    Write-Host "Bootstrap may have already been completed" -ForegroundColor Yellow
}

# Synthesize CloudFormation template
Write-Host "📝 Synthesizing CloudFormation template..." -ForegroundColor Cyan
cdk synth

# Deploy the stack
Write-Host "🚀 Deploying infrastructure..." -ForegroundColor Cyan
cdk deploy --require-approval never

Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Get the Load Balancer URL from the outputs above"
Write-Host "   2. Update AWS Secrets Manager with your API keys:"
Write-Host "      - JWT_SECRET"
Write-Host "      - OPENAI_API_KEY (or GEMINI_API_KEY, GROK_API_KEY)"
Write-Host "   3. Test the API endpoint: <LoadBalancerURL>/scrapper_application/docs"
