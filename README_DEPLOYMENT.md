# CV Analyzer - AWS Deployment Guide

This guide explains how to deploy the CV Analyzer Resume Screening Orchestrator to AWS using Infrastructure as Code (AWS CDK).

## Prerequisites

1. **AWS Account**: You need an active AWS account
2. **AWS CLI**: Install and configure AWS CLI
   ```bash
   aws configure
   # Enter your AWS Access Key ID, Secret Access Key, region, and output format
   ```
3. **Node.js**: Required for AWS CDK
   ```bash
   npm install -g aws-cdk
   ```
4. **Python 3.11+**: Required for the application
5. **Docker**: Required for building container images

## Architecture Overview

The infrastructure includes:

- **VPC**: Virtual Private Cloud with public and private subnets
- **ECS Fargate**: Containerized application running on serverless compute
- **Application Load Balancer**: Public-facing load balancer
- **RDS PostgreSQL**: Managed database for application data
- **S3 Bucket**: File storage for resume and JD uploads
- **Secrets Manager**: Secure storage for API keys and credentials
- **Auto Scaling**: Automatic scaling based on CPU and memory utilization

## Deployment Steps

### 1. Configure AWS Credentials

Choose one of the following methods:

**Option A: AWS CLI Configuration**
```bash
aws configure
```

**Option B: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

**Option C: AWS Profile**
```bash
export AWS_PROFILE=your_profile_name
```

### 2. Update CDK Configuration

Edit `app.py` and update the default account and region:

```python
env = Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT", "YOUR_ACCOUNT_ID"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1")
)
```

### 3. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install CDK Python dependencies
pip install aws-cdk-lib constructs
```

### 4. Bootstrap CDK (First Time Only)

```bash
cdk bootstrap
```

This sets up the CDK toolkit stack in your AWS account (only needed once per account/region).

### 5. Deploy Infrastructure

**Linux/Mac:**
```bash
chmod +x deploy.sh
./deploy.sh
```

**Windows (PowerShell):**
```powershell
.\deploy.ps1
```

**Manual Deployment:**
```bash
# Synthesize CloudFormation template
cdk synth

# Deploy the stack
cdk deploy
```

### 6. Configure Secrets

After deployment, update AWS Secrets Manager with your API keys and database URL:

1. Go to AWS Secrets Manager in the AWS Console
2. Find the secret named `CVAnalyzerStack-ApplicationSecrets-XXXXX`
3. Click "Retrieve secret value" → "Edit"
4. Get database credentials from `CVAnalyzerStack-DatabaseSecret-XXXXX`
5. Update the JSON with your credentials:
   ```json
   {
     "JWT_SECRET": "your-jwt-secret-key-here",
     "OPENAI_API_KEY": "your-openai-api-key",
     "GEMINI_API_KEY": "your-gemini-api-key",
     "GROK_API_KEY": "your-grok-api-key",
     "DATABASE_URL": "postgresql://username:password@database-endpoint:5432/cv_analyzer"
   }
   ```
   Note: Replace `username`, `password`, and `database-endpoint` with actual values from the DatabaseSecret.

### 7. Get Application URL

After deployment, CDK will output the Load Balancer URL. You can also find it in:

- CDK output in terminal
- AWS Console → EC2 → Load Balancers
- CloudFormation stack outputs

The API will be available at:
```
http://<load-balancer-dns>/scrapper_application/docs
```

## Configuration

### Environment Variables

The application uses the following environment variables (configured via ECS task definition):

- `ENVIRONMENT`: Set to "production"
- `DATABASE_URL`: Automatically configured from RDS
- `UPLOADS_BUCKET`: Automatically configured from S3 bucket
- `JWT_SECRET`: From Secrets Manager
- `OPENAI_API_KEY`: From Secrets Manager
- `GEMINI_API_KEY`: From Secrets Manager
- `GROK_API_KEY`: From Secrets Manager

### Scaling Configuration

Auto-scaling is configured with:
- **Min capacity**: 1 task
- **Max capacity**: 10 tasks
- **CPU scaling**: Scales at 70% CPU utilization
- **Memory scaling**: Scales at 80% memory utilization

### Database Configuration

- **Engine**: PostgreSQL 15.4
- **Instance**: t3.micro (can be upgraded)
- **Storage**: 20 GB (auto-scales to 100 GB)
- **Backup**: 7-day retention
- **Multi-AZ**: Can be enabled for production

## Cost Estimation

Approximate monthly costs (us-east-1):

- **ECS Fargate** (1 task, 0.5 vCPU, 1GB RAM): ~$15/month
- **RDS PostgreSQL** (t3.micro): ~$15/month
- **Application Load Balancer**: ~$16/month
- **S3 Storage** (minimal): ~$0.023/GB/month
- **Data Transfer**: ~$0.09/GB

**Total**: ~$50-70/month for minimal setup

## Updating the Application

To update the application code:

1. Make your code changes
2. Rebuild and push Docker image (CDK handles this automatically)
3. Redeploy:
   ```bash
   cdk deploy
   ```

## Monitoring

- **CloudWatch Logs**: Application logs are available in CloudWatch
- **ECS Service Metrics**: CPU, memory, and task count metrics
- **ALB Metrics**: Request count, response times, error rates
- **RDS Metrics**: Database connections, CPU, storage

## Troubleshooting

### Deployment Fails

1. Check AWS credentials are configured
2. Verify you have necessary IAM permissions
3. Check CloudFormation stack events in AWS Console

### Application Not Responding

1. Check ECS service status in AWS Console
2. Review CloudWatch logs for errors
3. Verify secrets are configured in Secrets Manager
4. Check security group rules allow traffic

### Database Connection Issues

1. Verify RDS security group allows connections from ECS
2. Check database credentials in Secrets Manager
3. Verify DATABASE_URL environment variable

## Cleanup

To remove all resources:

```bash
cdk destroy
```

**Warning**: This will delete all resources including the database. Make sure to backup data if needed.

## Security Best Practices

1. **Enable deletion protection** on RDS in production
2. **Use VPC endpoints** for S3 access (reduces data transfer costs)
3. **Enable encryption at rest** for RDS and S3
4. **Rotate secrets** regularly
5. **Use IAM roles** instead of access keys where possible
6. **Enable CloudTrail** for audit logging
7. **Restrict ALB access** using security groups or WAF

## Next Steps

1. Set up a custom domain with Route 53
2. Configure SSL/TLS certificate with ACM
3. Set up CI/CD pipeline with CodePipeline
4. Configure CloudWatch alarms for monitoring
5. Set up backup strategy for RDS
6. Configure log aggregation and analysis

## Support

For issues or questions:
- Check CloudFormation stack events
- Review CloudWatch logs
- Verify all secrets are configured correctly
- Ensure security groups allow necessary traffic
