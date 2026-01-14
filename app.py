#!/usr/bin/env python3
"""AWS CDK App Entry Point"""
import os
from aws_cdk import App, Environment
from infrastructure.cv_analyzer_stack import CVAnalyzerStack

app = App()

# Get environment configuration
env = Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT", "123456789012"),  # Replace with your account ID
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1")  # Replace with your preferred region
)

# Create the stack
CVAnalyzerStack(
    app,
    "CVAnalyzerStack",
    env=env,
    description="Resume Screening Orchestrator - AI-powered CV Analyzer"
)

app.synth()
