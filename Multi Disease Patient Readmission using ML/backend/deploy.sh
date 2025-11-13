#!/bin/bash
# Quick Deployment Script for AWS Elastic Beanstalk

set -e

echo "🚀 Patient Readmission Prediction - AWS Deployment"
echo "=================================================="

# Check if EB CLI is installed
if ! command -v eb &> /dev/null; then
    echo "❌ EB CLI not found. Installing..."
    pip install awsebcli
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run: aws configure"
    exit 1
fi

echo "✅ AWS credentials verified"

# Check if EB is initialized
if [ ! -d ".elasticbeanstalk" ]; then
    echo "📦 Initializing Elastic Beanstalk..."
    eb init -p python-3.11 patient-readmission-app --region us-east-1

    echo "🔧 Creating environment..."
    eb create patient-readmission-env \
        --instance-type t3.medium \
        --envvars FLASK_ENV=production \
        --single

    echo "✅ Environment created!"
else
    echo "📦 Deploying updates..."
    eb deploy
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Opening application in browser..."
eb open

echo ""
echo "💡 Useful commands:"
echo "   eb status           - Check application status"
echo "   eb logs             - View logs"
echo "   eb ssh              - SSH into instance"
echo "   eb deploy           - Deploy updates"
echo "   eb terminate        - Terminate environment"
