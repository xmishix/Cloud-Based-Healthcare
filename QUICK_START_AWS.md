# Quick Start - AWS Deployment

## TL;DR - Get Your App on AWS in 5 Minutes

### Option 1: Elastic Beanstalk (⭐ Recommended)

**One-command deployment:**
```bash
cd "Multi Disease Patient Readmission using ML/backend"
./deploy.sh
```

That's it! The script will:
- Install AWS CLI tools
- Create your application
- Deploy to AWS
- Open it in your browser

**Future updates:**
```bash
# Make your changes
# Then simply run:
eb deploy
```

---

### Option 2: AWS App Runner (🚀 Simplest)

**Via AWS Console:**
1. Open [AWS App Runner Console](https://console.aws.amazon.com/apprunner)
2. Click "Create service"
3. Choose "Source code repository" → Connect GitHub
4. Select your repository
5. Runtime: Python 3.11
6. Build command: `pip install -r requirements.txt`
7. Start command: `gunicorn --bind 0.0.0.0:8000 app:app`
8. Click "Create & deploy"

**Auto-updates:** Enable automatic deployment from GitHub - every push deploys automatically!

---

## Comparison Table

| Method | Setup Time | Monthly Cost | Update Method | Best For |
|--------|------------|--------------|---------------|----------|
| **Elastic Beanstalk** | 5 min | $33-78 | `eb deploy` | Production apps |
| **App Runner** | 3 min | $5-50 | Git push | Low-traffic apps |

---

## Prerequisites

**Install AWS CLI:**
```bash
pip install awscli awsebcli
```

**Configure credentials:**
```bash
aws configure
# Enter your:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region: us-east-1
```

**Get AWS credentials:**
1. Go to [AWS IAM Console](https://console.aws.amazon.com/iam)
2. Create new user with programmatic access
3. Attach policy: `AdministratorAccess-AWSElasticBeanstalk`
4. Save Access Key ID and Secret Access Key

---

## Deployment Commands Cheat Sheet

### Elastic Beanstalk
```bash
eb init                    # Initialize project
eb create                  # Create environment
eb deploy                  # Deploy updates
eb open                    # Open in browser
eb status                  # Check status
eb logs                    # View logs
eb ssh                     # SSH into server
eb terminate               # Delete environment
```

### Docker (for ECS/App Runner)
```bash
docker build -t app .                        # Build image
docker tag app:latest <ecr-url>:latest       # Tag image
docker push <ecr-url>:latest                 # Push to AWS
```

---

## Monitoring Your App

**View logs:**
```bash
eb logs                    # Elastic Beanstalk
# OR
aws logs tail /aws/apprunner/<service>    # App Runner
```

**Check metrics:**
- Go to [CloudWatch Console](https://console.aws.amazon.com/cloudwatch)
- View CPU, Memory, Response Time

---

## Cost Optimization Tips

1. **Use t3.small for development** ($15/month instead of $30/month)
2. **Enable auto-scaling** - scale down during off-hours
3. **Use App Runner for low traffic** - scales to zero
4. **Store ML models in S3** - reduce deployment package size
5. **Set up budget alerts** - get notified if costs spike

---

## Security Checklist

- ✅ Enable HTTPS (free with AWS Certificate Manager)
- ✅ Use IAM roles (not access keys)
- ✅ Enable WAF for API protection
- ✅ Set up VPC security groups
- ✅ Enable CloudWatch alarms
- ✅ Use AWS Secrets Manager for credentials
- ✅ Enable automatic backups

---

## Troubleshooting

**Problem: Deployment fails with "too large"**
```bash
# Solution: Models are large (45MB). Use .ebignore
echo "venv/" > .ebignore
```

**Problem: Application timeout**
```bash
# Solution: Increase timeout in .ebextensions/python.config
# Already configured in this project!
```

**Problem: Out of memory**
```bash
# Solution: Use larger instance
eb scale 1 --instance-type t3.medium
```

**Problem: Need to rollback**
```bash
# Solution: Deploy previous version
eb deploy --version <version-number>
```

---

## Next Steps After Deployment

1. **Set up custom domain:**
   ```bash
   # Get SSL certificate from AWS Certificate Manager
   # Add domain in EB console
   ```

2. **Enable database:**
   ```bash
   # Create RDS PostgreSQL instance
   # Update app to use RDS instead of CSV
   ```

3. **Set up CI/CD:**
   - Connect GitHub to automatically deploy on push
   - Use GitHub Actions for testing before deploy

4. **Monitor and optimize:**
   - Review CloudWatch metrics
   - Set up cost alerts
   - Enable auto-scaling

---

## Support

**Need help?**
- 📖 Full guide: See `AWS_DEPLOYMENT_GUIDE.md`
- 💬 AWS Support: Create a support case
- 🌐 Community: AWS Forums, Stack Overflow

**Emergency rollback:**
```bash
eb abort            # Cancel current deployment
eb deploy --version <previous-version>
```

---

## Estimated Costs

**Development:**
- Elastic Beanstalk (t3.small): **$15-20/month**
- App Runner (low traffic): **$5-10/month**

**Production:**
- Elastic Beanstalk (t3.medium + RDS): **$70-90/month**
- ECS Fargate (high traffic): **$130-150/month**

All prices include:
- Compute resources
- Load balancer
- Data transfer (moderate usage)

---

**Ready to deploy? Run `./deploy.sh` and you're live in 5 minutes!** 🚀
