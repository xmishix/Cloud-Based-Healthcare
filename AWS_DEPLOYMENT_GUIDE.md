# AWS Deployment Guide - Patient Readmission Prediction System

This guide covers the most efficient ways to deploy this ML-powered Flask application on AWS with easy update capabilities.

## Table of Contents
1. [Option 1: AWS Elastic Beanstalk (Recommended)](#option-1-aws-elastic-beanstalk)
2. [Option 2: AWS App Runner (Easiest)](#option-2-aws-app-runner)
3. [Option 3: ECS Fargate (Most Scalable)](#option-3-ecs-fargate)
4. [Option 4: EC2 with Auto Scaling](#option-4-ec2-with-auto-scaling)
5. [Cost Comparison](#cost-comparison)
6. [Updating Your Application](#updating-your-application)

---

## Option 1: AWS Elastic Beanstalk (⭐ Recommended)

**Best for:** Balanced approach - easy deployment, auto-scaling, and simple updates

### Pros
- ✅ Fully managed platform
- ✅ Auto-scaling and load balancing included
- ✅ Zero-downtime deployments
- ✅ Easy rollbacks
- ✅ Built-in monitoring
- ✅ One-command deployments
- ✅ Good for production workloads

### Cons
- ❌ Less control than ECS/EC2
- ❌ Slight overhead cost

### Prerequisites
```bash
# Install AWS CLI
pip install awscli

# Install EB CLI
pip install awsebcli

# Configure AWS credentials
aws configure
```

### Deployment Steps

#### 1. Initialize Elastic Beanstalk
```bash
cd "Multi Disease Patient Readmission using ML/backend"

# Initialize EB application
eb init -p python-3.11 patient-readmission-app --region us-east-1

# Create environment
eb create patient-readmission-env \
  --instance-type t3.medium \
  --envvars FLASK_ENV=production
```

#### 2. Deploy Application
```bash
# Deploy
eb deploy

# Open in browser
eb open
```

#### 3. Configure Domain (Optional)
```bash
# Add custom domain
eb setenv DOMAIN_NAME=your-domain.com

# Configure SSL certificate in AWS Certificate Manager
# Then attach via EB console
```

### Updating Your Application

**Simple updates (one command):**
```bash
# Make your code changes
# Commit changes
git add .
git commit -m "Updated feature X"

# Deploy with zero downtime
eb deploy
```

**Rollback if needed:**
```bash
eb deploy --version <previous-version>
```

### Cost Estimate
- **Small**: t3.small (~$15/month)
- **Medium**: t3.medium (~$30/month)
- **Large**: t3.large (~$60/month)
- Plus: Data transfer, Load Balancer (~$18/month)

**Total: $33-$78/month**

---

## Option 2: AWS App Runner (🚀 Easiest)

**Best for:** Simplest deployment with minimal configuration

### Pros
- ✅ Simplest AWS service
- ✅ Automatic scaling from zero
- ✅ Pay per use (cost-efficient for low traffic)
- ✅ Auto-deploy from GitHub
- ✅ Built-in HTTPS

### Cons
- ❌ Less customization
- ❌ Cold starts possible
- ❌ Higher cost at high traffic

### Deployment Steps

#### 1. Build and Push Docker Image
```bash
cd "Multi Disease Patient Readmission using ML/backend"

# Login to AWS ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repository
aws ecr create-repository --repository-name patient-readmission --region us-east-1

# Build Docker image
docker build -t patient-readmission .

# Tag image
docker tag patient-readmission:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/patient-readmission:latest

# Push to ECR
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/patient-readmission:latest
```

#### 2. Create App Runner Service

**Via AWS Console:**
1. Go to AWS App Runner
2. Click "Create service"
3. Choose "Container registry" → Select your ECR image
4. Configure:
   - vCPU: 2
   - Memory: 4 GB
   - Port: 8000
5. Click "Create & deploy"

**Via CLI:**
```bash
# Create apprunner.yaml configuration file
cat > apprunner.yaml << EOF
version: 1.0
runtime: python311
build:
  commands:
    build:
      - pip install -r requirements.txt
run:
  runtime-version: 3.11
  command: gunicorn --bind 0.0.0.0:8000 --workers 4 app:app
  network:
    port: 8000
EOF

# Deploy via CLI
aws apprunner create-service \
  --service-name patient-readmission \
  --source-configuration file://apprunner.yaml
```

### Updating Your Application

**Automatic updates from GitHub:**
1. Connect App Runner to your GitHub repository
2. Enable auto-deployment
3. Push code changes → automatic deployment

**Manual update:**
```bash
# Build and push new Docker image
docker build -t patient-readmission .
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/patient-readmission:latest

# App Runner auto-detects and deploys
```

### Cost Estimate
- **Base**: $0.007/vCPU-hour + $0.0008/GB-hour
- **Example** (2 vCPU, 4GB): ~$50/month for 24/7 operation
- **Low traffic**: Can scale to zero = $5-15/month

---

## Option 3: ECS Fargate (⚙️ Most Scalable)

**Best for:** Production workloads with high traffic and scaling needs

### Pros
- ✅ Container-based (consistent environments)
- ✅ Highly scalable
- ✅ Full control over infrastructure
- ✅ Blue/green deployments
- ✅ Integration with AWS services

### Cons
- ❌ More complex setup
- ❌ Requires VPC, ALB configuration

### Deployment Steps

#### 1. Create ECS Cluster
```bash
# Create cluster
aws ecs create-cluster --cluster-name patient-readmission-cluster
```

#### 2. Create Task Definition
```bash
# Create task-definition.json
cat > task-definition.json << EOF
{
  "family": "patient-readmission",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "containerDefinitions": [
    {
      "name": "app",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/patient-readmission:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/patient-readmission",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF

# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

#### 3. Create Service with Load Balancer
```bash
# Create service (requires VPC, subnets, ALB setup)
aws ecs create-service \
  --cluster patient-readmission-cluster \
  --service-name patient-readmission-service \
  --task-definition patient-readmission \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=app,containerPort=8000"
```

### Updating Your Application

**Blue/Green Deployment:**
```bash
# Build and push new Docker image
docker build -t patient-readmission:v2 .
docker tag patient-readmission:v2 <account-id>.dkr.ecr.us-east-1.amazonaws.com/patient-readmission:v2
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/patient-readmission:v2

# Update task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Update service
aws ecs update-service \
  --cluster patient-readmission-cluster \
  --service patient-readmission-service \
  --task-definition patient-readmission:2
```

### Cost Estimate
- **Fargate**: $0.04048/vCPU-hour + $0.004445/GB-hour
- **Example** (2 vCPU, 4GB): ~$60/month per task
- **Load Balancer**: ~$18/month
- **2 tasks**: ~$138/month

---

## Option 4: EC2 with Auto Scaling

**Best for:** Full control and cost optimization

### Deployment Steps

#### 1. Launch EC2 Instance
```bash
# Create instance
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.medium \
  --key-name your-key-pair \
  --security-group-ids sg-xxx \
  --user-data file://startup-script.sh
```

#### 2. User Data Script
```bash
# startup-script.sh
#!/bin/bash
sudo yum update -y
sudo yum install python3.11 git -y
cd /home/ec2-user
git clone <your-repo>
cd "Multi Disease Patient Readmission using ML/backend"
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:8000 --workers 4 --daemon app:app
```

### Updating Your Application

**Using CodeDeploy:**
```bash
# Create appspec.yml
cat > appspec.yml << EOF
version: 0.0
os: linux
files:
  - source: /
    destination: /var/www/app
hooks:
  ApplicationStop:
    - location: scripts/stop_server.sh
  ApplicationStart:
    - location: scripts/start_server.sh
EOF

# Deploy
aws deploy create-deployment \
  --application-name patient-readmission \
  --deployment-group-name production
```

### Cost Estimate
- **EC2 t3.medium**: ~$30/month
- **Load Balancer**: ~$18/month
- **Total**: ~$48/month

---

## Cost Comparison

| Service | Monthly Cost | Setup Complexity | Update Ease | Scalability |
|---------|--------------|------------------|-------------|-------------|
| **Elastic Beanstalk** | $33-78 | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **App Runner** | $5-50 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **ECS Fargate** | $138+ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **EC2** | $48 | ⭐ | ⭐⭐ | ⭐⭐⭐ |

---

## Updating Your Application (Quick Reference)

### Elastic Beanstalk
```bash
eb deploy
```

### App Runner
```bash
git push origin main  # Auto-deploys if connected to GitHub
# OR
docker build -t app . && docker push <ecr-url> # Auto-detects new image
```

### ECS Fargate
```bash
docker build -t app . && docker push <ecr-url>
aws ecs update-service --cluster <cluster> --service <service> --force-new-deployment
```

### EC2
```bash
ssh ec2-user@<ip>
cd /var/www/app
git pull
sudo systemctl restart gunicorn
```

---

## Additional Optimizations

### 1. Use S3 for Model Storage
Store large ML models in S3 and download on startup:
```python
import boto3

s3 = boto3.client('s3')
s3.download_file('my-bucket', 'models/diabetes_model.pkl', 'diabetes_model.pkl')
```

### 2. CloudFront CDN
Serve static assets (frontend) via CloudFront for better performance.

### 3. RDS for Data Storage
Replace CSV files with PostgreSQL or Aurora for better scalability.

### 4. CloudWatch Monitoring
Set up alarms for CPU, memory, and response times.

### 5. Secrets Manager
Store API keys and database credentials securely:
```bash
aws secretsmanager create-secret --name patient-readmission/api-keys --secret-string '{"key":"value"}'
```

---

## CI/CD Pipeline (GitHub Actions)

Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy to AWS

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Deploy to Elastic Beanstalk
        run: |
          pip install awsebcli
          eb deploy patient-readmission-env
```

---

## Security Best Practices

1. **Enable HTTPS** - Use AWS Certificate Manager
2. **WAF** - Protect against common web attacks
3. **VPC** - Deploy in private subnets
4. **IAM Roles** - Use roles instead of access keys
5. **Security Groups** - Restrict inbound traffic
6. **Encryption** - Enable at rest and in transit
7. **Secrets** - Use AWS Secrets Manager
8. **Logging** - Enable CloudWatch Logs and CloudTrail

---

## Recommended Deployment for Healthcare Application

**For this healthcare ML application, I recommend:**

### Production Setup:
1. **AWS Elastic Beanstalk** with t3.medium instances
2. **RDS PostgreSQL** for patient data
3. **S3** for ML models and reports
4. **CloudFront** for static assets
5. **WAF** for security
6. **CloudWatch** for monitoring
7. **Backup** automated daily snapshots

### Development/Staging:
1. **AWS App Runner** (cost-efficient, easy updates)

### Estimated Monthly Cost:
- Elastic Beanstalk: $45
- RDS (db.t3.small): $25
- S3: $5
- CloudFront: $10
- **Total: ~$85/month**

---

## Quick Start (Recommended Path)

```bash
# 1. Install EB CLI
pip install awsebcli

# 2. Navigate to backend
cd "Multi Disease Patient Readmission using ML/backend"

# 3. Initialize and deploy
eb init -p python-3.11 patient-readmission-app
eb create patient-readmission-env --instance-type t3.medium
eb open

# 4. Future updates
# Make changes → git commit → eb deploy
```

---

## Support and Troubleshooting

### Common Issues

**Large package size:**
- Models are 45MB+ → use S3 storage
- Use `.ebignore` to exclude unnecessary files

**Timeout during deployment:**
- Increase timeout in `.ebextensions/python.config`
- Use larger instance type

**Memory issues:**
- ML models require 4GB+ RAM
- Use t3.medium or larger

### Getting Help
- AWS Documentation: https://docs.aws.amazon.com
- AWS Support: Create a support ticket
- Community: AWS Forums, Stack Overflow

---

**Created for:** Multi-Disease Patient Readmission Prediction System
**Last Updated:** 2025-11-13
