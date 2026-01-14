"""AWS CDK Stack for CV Analyzer Application"""
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_rds as rds,
    aws_s3 as s3,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    aws_logs as logs,
    CfnOutput,
    RemovalPolicy,
    Duration,
    Size,
)
from constructs import Construct


class CVAnalyzerStack(Stack):
    """Main CDK Stack for CV Analyzer Infrastructure"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ============================================
        # VPC and Networking
        # ============================================
        vpc = ec2.Vpc(
            self,
            "CVAnalyzerVPC",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PUBLIC,
                    name="Public",
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    name="Private",
                    cidr_mask=24,
                ),
            ],
        )

        # ============================================
        # S3 Bucket for File Storage
        # ============================================
        uploads_bucket = s3.Bucket(
            self,
            "CVAnalyzerUploadsBucket",
            bucket_name=f"cv-analyzer-uploads-{self.account}-{self.region}",
            versioned=False,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,  # Keep data on stack deletion
            auto_delete_objects=False,
        )

        # ============================================
        # RDS Database (PostgreSQL)
        # ============================================
        # Database credentials secret (will be created manually or via AWS Secrets Manager)
        db_secret = secretsmanager.Secret(
            self,
            "DatabaseSecret",
            description="Database credentials for CV Analyzer",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "cvanalyzer"}',
                generate_string_key="password",
                exclude_characters='"@/\\',
            ),
        )

        # Database subnet group
        db_subnet_group = rds.SubnetGroup(
            self,
            "DatabaseSubnetGroup",
            vpc=vpc,
            description="Subnet group for CV Analyzer database",
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
        )

        # Security group for RDS
        db_security_group = ec2.SecurityGroup(
            self,
            "DatabaseSecurityGroup",
            vpc=vpc,
            description="Security group for CV Analyzer database",
            allow_all_outbound=True,
        )

        # RDS PostgreSQL instance
        database = rds.DatabaseInstance(
            self,
            "CVAnalyzerDatabase",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15_4
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3, ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            subnet_group=db_subnet_group,
            security_groups=[db_security_group],
            credentials=rds.Credentials.from_secret(db_secret),
            database_name="cv_analyzer",
            allocated_storage=20,
            max_allocated_storage=100,
            removal_policy=RemovalPolicy.SNAPSHOT,  # Create snapshot before deletion
            deletion_protection=False,  # Set to True in production
            backup_retention=Duration.days(7),
            enable_performance_insights=True,
        )

        # ============================================
        # ECS Cluster
        # ============================================
        cluster = ecs.Cluster(
            self,
            "CVAnalyzerCluster",
            vpc=vpc,
            container_insights=True,
        )

        # ============================================
        # Application Secrets
        # ============================================
        # Application secrets
        # Note: DATABASE_URL will be set manually after deployment
        # Format: postgresql://username:password@host:port/database
        app_secrets = secretsmanager.Secret(
            self,
            "ApplicationSecrets",
            description="Application secrets for CV Analyzer (LLM API keys, JWT secret, DATABASE_URL, etc.)",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"JWT_SECRET": "", "OPENAI_API_KEY": "", "GEMINI_API_KEY": "", "GROK_API_KEY": "", "DATABASE_URL": ""}',
                generate_string_key="JWT_SECRET",
            ),
        )

        # ============================================
        # ECS Fargate Service with Application Load Balancer
        # ============================================
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "CVAnalyzerService",
            cluster=cluster,
            cpu=512,  # 0.5 vCPU
            memory_limit_mib=1024,  # 1 GB RAM
            desired_count=1,  # Start with 1 instance, scale as needed
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_asset(
                    directory=".",
                    file="Dockerfile",
                ),
                container_port=8000,
                environment={
                    "ENVIRONMENT": "production",
                    "UPLOADS_BUCKET": uploads_bucket.bucket_name,
                    "AWS_REGION": self.region,
                },
                secrets={
                    "DATABASE_URL": ecs.Secret.from_secrets_manager(
                        app_secrets, "DATABASE_URL"
                    ),
                    "JWT_SECRET": ecs.Secret.from_secrets_manager(
                        app_secrets, "JWT_SECRET"
                    ),
                    "OPENAI_API_KEY": ecs.Secret.from_secrets_manager(
                        app_secrets, "OPENAI_API_KEY"
                    ),
                    "GEMINI_API_KEY": ecs.Secret.from_secrets_manager(
                        app_secrets, "GEMINI_API_KEY"
                    ),
                    "GROK_API_KEY": ecs.Secret.from_secrets_manager(
                        app_secrets, "GROK_API_KEY"
                    ),
                },
                log_driver=ecs.LogDrivers.aws_logs(
                    stream_prefix="cv-analyzer",
                    log_retention=logs.RetentionDays.ONE_WEEK,
                ),
            ),
            public_load_balancer=True,
            health_check_grace_period=Duration.seconds(60),
        )

        # Allow Fargate service to access S3 bucket
        uploads_bucket.grant_read_write(fargate_service.task_definition.task_role)

        # Allow Fargate service to access RDS
        database.connections.allow_default_port_from(
            fargate_service.service.connections,
            "Allow ECS to access RDS",
        )

        # Allow Fargate service to read secrets
        db_secret.grant_read(fargate_service.task_definition.task_role)
        app_secrets.grant_read(fargate_service.task_definition.task_role)

        # ============================================
        # Auto Scaling
        # ============================================
        scalable_target = fargate_service.service.auto_scale_task_count(
            min_capacity=1,
            max_capacity=10,
        )

        scalable_target.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60),
        )

        scalable_target.scale_on_memory_utilization(
            "MemoryScaling",
            target_utilization_percent=80,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60),
        )

        # ============================================
        # Outputs
        # ============================================
        CfnOutput(
            self,
            "LoadBalancerDNS",
            value=fargate_service.load_balancer.load_balancer_dns_name,
            description="Application Load Balancer DNS name",
        )

        CfnOutput(
            self,
            "LoadBalancerURL",
            value=f"http://{fargate_service.load_balancer.load_balancer_dns_name}",
            description="Application URL",
        )

        CfnOutput(
            self,
            "DatabaseEndpoint",
            value=database.instance_endpoint.hostname,
            description="RDS Database endpoint",
        )

        CfnOutput(
            self,
            "DatabaseSecretArn",
            value=db_secret.secret_arn,
            description="Database credentials secret ARN (use this to get username/password for DATABASE_URL)",
        )
        
        CfnOutput(
            self,
            "DatabaseConnectionString",
            value=f"postgresql://<username>:<password>@{database.instance_endpoint.hostname}:5432/cv_analyzer",
            description="Database connection string template (replace <username> and <password> with values from DatabaseSecret)",
        )

        CfnOutput(
            self,
            "ApplicationSecretsArn",
            value=app_secrets.secret_arn,
            description="Application secrets ARN",
        )

        CfnOutput(
            self,
            "UploadsBucketName",
            value=uploads_bucket.bucket_name,
            description="S3 bucket for file uploads",
        )
