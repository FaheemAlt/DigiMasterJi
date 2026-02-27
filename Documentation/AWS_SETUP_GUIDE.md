# DigiMasterJi AWS Setup Guide

This guide walks you through setting up the AWS infrastructure required to run DigiMasterJi backend on AWS.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [IAM Configuration](#iam-configuration)
3. [DynamoDB Tables](#dynamodb-tables)
4. [S3 Bucket](#s3-bucket)
5. [Amazon Bedrock](#amazon-bedrock)
6. [Bedrock Knowledge Base](#bedrock-knowledge-base)
7. [ECR Repository](#ecr-repository)
8. [Lambda Function](#lambda-function)
9. [API Gateway](#api-gateway)
10. [EventBridge (Quiz Scheduler)](#eventbridge-quiz-scheduler)
11. [Environment Variables](#environment-variables)
12. [Deployment](#deployment)

---

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI v2 installed and configured
- Docker installed and running
- Python 3.11+ (for local development)

```bash
# Verify AWS CLI is configured
aws sts get-caller-identity

# Verify Docker is running
docker --version
```

---

## IAM Configuration

### Lambda Execution Role

Create an IAM role for Lambda with the following policies:

```bash
# Create the trust policy
cat > trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the role
aws iam create-role \
  --role-name digimasterji-lambda-role \
  --assume-role-policy-document file://trust-policy.json

# Attach basic Lambda execution policy
aws iam attach-role-policy \
  --role-name digimasterji-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

### Custom Policy for DigiMasterJi

Create a custom policy with access to DynamoDB, S3, and Bedrock:

```bash
cat > digimasterji-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:BatchGetItem",
        "dynamodb:BatchWriteItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/digimasterji-*",
        "arn:aws:dynamodb:*:*:table/digimasterji-*/index/*"
      ]
    },
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::digimasterji-knowledge",
        "arn:aws:s3:::digimasterji-knowledge/*"
      ]
    },
    {
      "Sid": "BedrockAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ListFoundationModels"
      ],
      "Resource": "*"
    },
    {
      "Sid": "BedrockKnowledgeBaseAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:Retrieve",
        "bedrock:RetrieveAndGenerate",
        "bedrock-agent:StartIngestionJob",
        "bedrock-agent:GetIngestionJob",
        "bedrock-agent:ListIngestionJobs"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create and attach the policy
aws iam create-policy \
  --policy-name digimasterji-lambda-policy \
  --policy-document file://digimasterji-policy.json

# Get your account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Attach to role
aws iam attach-role-policy \
  --role-name digimasterji-lambda-role \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/digimasterji-lambda-policy
```

---

## DynamoDB Tables

Create the following tables:

### Users Table

```bash
aws dynamodb create-table \
  --table-name digimasterji-users \
  --attribute-definitions \
    AttributeName=userId,AttributeType=S \
    AttributeName=email,AttributeType=S \
    AttributeName=phone,AttributeType=S \
  --key-schema \
    AttributeName=userId,KeyType=HASH \
  --global-secondary-indexes \
    '[
      {
        "IndexName": "email-index",
        "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
        "Projection": {"ProjectionType": "ALL"}
      },
      {
        "IndexName": "phone-index",
        "KeySchema": [{"AttributeName": "phone", "KeyType": "HASH"}],
        "Projection": {"ProjectionType": "ALL"}
      }
    ]' \
  --billing-mode PAY_PER_REQUEST
```

### Profiles Table

```bash
aws dynamodb create-table \
  --table-name digimasterji-profiles \
  --attribute-definitions \
    AttributeName=userId,AttributeType=S \
    AttributeName=profileId,AttributeType=S \
  --key-schema \
    AttributeName=userId,KeyType=HASH \
    AttributeName=profileId,KeyType=RANGE \
  --global-secondary-indexes \
    '[
      {
        "IndexName": "profileId-index",
        "KeySchema": [{"AttributeName": "profileId", "KeyType": "HASH"}],
        "Projection": {"ProjectionType": "ALL"}
      }
    ]' \
  --billing-mode PAY_PER_REQUEST
```

### Conversations Table

```bash
aws dynamodb create-table \
  --table-name digimasterji-conversations \
  --attribute-definitions \
    AttributeName=profileId,AttributeType=S \
    AttributeName=conversationId,AttributeType=S \
  --key-schema \
    AttributeName=profileId,KeyType=HASH \
    AttributeName=conversationId,KeyType=RANGE \
  --global-secondary-indexes \
    '[
      {
        "IndexName": "conversationId-index",
        "KeySchema": [{"AttributeName": "conversationId", "KeyType": "HASH"}],
        "Projection": {"ProjectionType": "ALL"}
      }
    ]' \
  --billing-mode PAY_PER_REQUEST
```

### Messages Table

```bash
aws dynamodb create-table \
  --table-name digimasterji-messages \
  --attribute-definitions \
    AttributeName=conversationId,AttributeType=S \
    AttributeName=messageId,AttributeType=S \
    AttributeName=profileId,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
  --key-schema \
    AttributeName=conversationId,KeyType=HASH \
    AttributeName=messageId,KeyType=RANGE \
  --global-secondary-indexes \
    '[
      {
        "IndexName": "messageId-index",
        "KeySchema": [{"AttributeName": "messageId", "KeyType": "HASH"}],
        "Projection": {"ProjectionType": "ALL"}
      },
      {
        "IndexName": "profileId-timestamp-index",
        "KeySchema": [
          {"AttributeName": "profileId", "KeyType": "HASH"},
          {"AttributeName": "timestamp", "KeyType": "RANGE"}
        ],
        "Projection": {"ProjectionType": "ALL"}
      }
    ]' \
  --billing-mode PAY_PER_REQUEST
```

### Quizzes Table

```bash
aws dynamodb create-table \
  --table-name digimasterji-quizzes \
  --attribute-definitions \
    AttributeName=profileId,AttributeType=S \
    AttributeName=quizId,AttributeType=S \
    AttributeName=status,AttributeType=S \
  --key-schema \
    AttributeName=profileId,KeyType=HASH \
    AttributeName=quizId,KeyType=RANGE \
  --global-secondary-indexes \
    '[
      {
        "IndexName": "quizId-index",
        "KeySchema": [{"AttributeName": "quizId", "KeyType": "HASH"}],
        "Projection": {"ProjectionType": "ALL"}
      },
      {
        "IndexName": "status-index",
        "KeySchema": [
          {"AttributeName": "profileId", "KeyType": "HASH"},
          {"AttributeName": "status", "KeyType": "RANGE"}
        ],
        "Projection": {"ProjectionType": "ALL"}
      }
    ]' \
  --billing-mode PAY_PER_REQUEST
```

### Knowledge Base Table

```bash
aws dynamodb create-table \
  --table-name digimasterji-knowledge-base \
  --attribute-definitions \
    AttributeName=documentId,AttributeType=S \
  --key-schema \
    AttributeName=documentId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

---

## S3 Bucket

Create the S3 bucket for knowledge base documents:

```bash
# Create bucket (use a globally unique name)
aws s3 mb s3://digimasterji-knowledge --region us-east-1

# Enable versioning (recommended)
aws s3api put-bucket-versioning \
  --bucket digimasterji-knowledge \
  --versioning-configuration Status=Enabled

# Block public access
aws s3api put-public-access-block \
  --bucket digimasterji-knowledge \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

---

## Amazon Bedrock

### Enable Model Access

1. Go to AWS Console → Amazon Bedrock
2. Navigate to "Model access" in the left sidebar
3. Click "Modify model access"
4. Enable the following models:
   - **Meta Llama 3.1 8B Instruct** (`meta.llama3-1-8b-instruct-v1:0`)
   - **Amazon Titan Text Embeddings V2** (`amazon.titan-embed-text-v2:0`)
5. Click "Next" and "Submit"

Wait for approval (usually instant for most models).

### Verify Access

```bash
# List available models
aws bedrock list-foundation-models --region us-east-1 | grep -E "llama|titan-embed"
```

---

## Bedrock Knowledge Base

### Create Knowledge Base

1. Go to AWS Console → Amazon Bedrock → Knowledge bases
2. Click "Create knowledge base"
3. Configure:
   - **Name**: `digimasterji-kb`
   - **IAM Role**: Create a new role or use existing
   - **Embedding model**: Amazon Titan Text Embeddings V2
4. Add Data Source:
   - **Type**: Amazon S3
   - **Bucket**: `digimasterji-knowledge`
   - **Chunking strategy**: Default (or customize as needed)
5. Select Vector Store:
   - **OpenSearch Serverless** (recommended for ease of use)
   - Let Bedrock create a new collection
6. Review and create

### Get Knowledge Base IDs

After creation, note down:

- **Knowledge Base ID**: e.g., `ABCD1234EF`
- **Data Source ID**: e.g., `EFGH5678IJ`

Update your `.env` file:

```
BEDROCK_KNOWLEDGE_BASE_ID=ABCD1234EF
BEDROCK_DATA_SOURCE_ID=EFGH5678IJ
```

---

## ECR Repository

Create an ECR repository for the Docker images:

```bash
aws ecr create-repository \
  --repository-name digimasterji-backend \
  --image-scanning-configuration scanOnPush=true \
  --region us-east-1
```

---

## Lambda Function

### Create the Function

After pushing your first image (via `deploy.sh`), create the Lambda function:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"

# Note: AWS_REGION is automatically provided by Lambda - don't set it manually
aws lambda create-function \
  --function-name digimasterji-backend-dev \
  --package-type Image \
  --code ImageUri=${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/digimasterji-backend:dev-latest \
  --role arn:aws:iam::${ACCOUNT_ID}:role/digimasterji-lambda-role \
  --timeout 120 \
  --memory-size 1024 \
  --environment "Variables={
    DYNAMODB_USERS_TABLE=digimasterji-users,
    DYNAMODB_PROFILES_TABLE=digimasterji-profiles,
    DYNAMODB_CONVERSATIONS_TABLE=digimasterji-conversations,
    DYNAMODB_MESSAGES_TABLE=digimasterji-messages,
    DYNAMODB_QUIZZES_TABLE=digimasterji-quizzes,
    BEDROCK_MODEL_ID=meta.llama3-1-8b-instruct-v1:0,
    BEDROCK_KNOWLEDGE_BASE_ID=YOUR_KB_ID,
    S3_KNOWLEDGE_BUCKET=digimasterji-knowledge,
    SECRET_KEY=your-production-secret-key
  }" \
  --region ${REGION}
```

### Configure Function URL (Optional - for quick testing)

```bash
aws lambda create-function-url-config \
  --function-name digimasterji-backend-dev \
  --auth-type NONE \
  --cors '{
    "AllowOrigins": ["*"],
    "AllowMethods": ["*"],
    "AllowHeaders": ["*"]
  }'

# IMPORTANT: Add public access permission for Function URL
aws lambda add-permission \
  --function-name digimasterji-backend-dev \
  --statement-id FunctionURLAllowPublicAccess \
  --action lambda:InvokeFunctionUrl \
  --principal "*" \
  --function-url-auth-type NONE
```

### Testing Lambda Function

```bash
# Test via Function URL (get URL first)
aws lambda get-function-url-config --function-name digimasterji-backend-dev
# Then: curl https://YOUR_FUNCTION_URL_ID.lambda-url.us-east-1.on.aws/health

# Test via direct invocation
aws lambda invoke \
  --function-name digimasterji-backend-dev \
  --cli-binary-format raw-in-base64-out \
  --payload '{}' \
  response.json && cat response.json
```

### Viewing Lambda Logs

```bash
# View recent logs (last 10 minutes)
aws logs tail /aws/lambda/digimasterji-backend-dev --since 10m --region us-east-1

# Follow logs in real-time
aws logs tail /aws/lambda/digimasterji-backend-dev --follow --region us-east-1

# View logs with timestamps
aws logs tail /aws/lambda/digimasterji-backend-dev --since 1h --format short --region us-east-1
```

---

## API Gateway

For production, use API Gateway HTTP API:

### Create HTTP API

```bash
aws apigatewayv2 create-api \
  --name digimasterji-api \
  --protocol-type HTTP \
  --cors-configuration '{
    "AllowOrigins": ["*"],
    "AllowMethods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "AllowHeaders": ["*"]
  }'
```

### Create Lambda Integration

```bash
API_ID="your-api-id"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"

aws apigatewayv2 create-integration \
  --api-id ${API_ID} \
  --integration-type AWS_PROXY \
  --integration-uri arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:digimasterji-backend-dev \
  --payload-format-version "2.0"
```

### Create Route

```bash
INTEGRATION_ID="your-integration-id"

aws apigatewayv2 create-route \
  --api-id ${API_ID} \
  --route-key '$default' \
  --target integrations/${INTEGRATION_ID}
```

### Deploy Stage

```bash
aws apigatewayv2 create-stage \
  --api-id ${API_ID} \
  --stage-name '$default' \
  --auto-deploy
```

### Add Lambda permission for API Gateway

```bash
aws lambda add-permission \
  --function-name digimasterji-backend-dev \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*"
```

---

## EventBridge (Quiz Scheduler)

Replace APScheduler with EventBridge for quiz generation:

### Create Scheduler Lambda

Create a separate Lambda function for quiz generation that runs daily.

### Create EventBridge Rule

```bash
# Create rule to run at midnight UTC daily
aws events put-rule \
  --name digimasterji-daily-quiz \
  --schedule-expression "cron(0 0 * * ? *)" \
  --state ENABLED

# Add Lambda as target
aws events put-targets \
  --rule digimasterji-daily-quiz \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:${ACCOUNT_ID}:function:digimasterji-quiz-scheduler"

# Grant EventBridge permission to invoke Lambda
aws lambda add-permission \
  --function-name digimasterji-quiz-scheduler \
  --statement-id eventbridge-invoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:${ACCOUNT_ID}:rule/digimasterji-daily-quiz
```

---

## Environment Variables

Required environment variables for the Lambda function:

> **Note**: Do not set `AWS_REGION` - it's automatically provided by Lambda.

| Variable                        | Description              | Example                          |
| ------------------------------- | ------------------------ | -------------------------------- |
| `DYNAMODB_USERS_TABLE`          | Users table name         | `digimasterji-users`             |
| `DYNAMODB_PROFILES_TABLE`       | Profiles table name      | `digimasterji-profiles`          |
| `DYNAMODB_CONVERSATIONS_TABLE`  | Conversations table name | `digimasterji-conversations`     |
| `DYNAMODB_MESSAGES_TABLE`       | Messages table name      | `digimasterji-messages`          |
| `DYNAMODB_QUIZZES_TABLE`        | Quizzes table name       | `digimasterji-quizzes`           |
| `DYNAMODB_KNOWLEDGE_BASE_TABLE` | KB tracking table        | `digimasterji-knowledge-base`    |
| `BEDROCK_MODEL_ID`              | Bedrock LLM model        | `meta.llama3-1-8b-instruct-v1:0` |
| `BEDROCK_KNOWLEDGE_BASE_ID`     | Bedrock KB ID            | `ABCD1234EF`                     |
| `BEDROCK_DATA_SOURCE_ID`        | Bedrock data source ID   | `EFGH5678IJ`                     |
| `S3_KNOWLEDGE_BUCKET`           | S3 bucket for docs       | `digimasterji-knowledge`         |
| `SECRET_KEY`                    | JWT secret key           | `your-secure-secret`             |
| `DEEPGRAM_API_KEY`              | Deepgram API key         | `your-deepgram-key`              |

---

## Deployment

### First Deployment

1. Build and push the Docker image:

   ```bash
   cd Backend
   ./deploy.sh dev
   ```

2. Create the Lambda function (see [Lambda Function](#lambda-function) section)

3. Configure environment variables in Lambda console or via CLI

4. Test the deployment:

   ```bash
   # Get the function URL
   aws lambda get-function-url-config --function-name digimasterji-backend-dev

   # Or test via invoke
   aws lambda invoke \
     --function-name digimasterji-backend-dev \
     --payload '{"httpMethod": "GET", "path": "/health"}' \
     response.json

   cat response.json
   ```

### Subsequent Deployments

Simply run the deploy script:

```bash
./deploy.sh dev      # Development
./deploy.sh staging  # Staging
./deploy.sh prod     # Production
```

---

## Cost Optimization Tips

1. **DynamoDB**: Use on-demand pricing for unpredictable workloads
2. **Lambda**: Set appropriate timeout and memory
3. **Bedrock**: Use smaller models (Llama 8B) for cost efficiency
4. **S3**: Enable lifecycle rules for old documents
5. **OpenSearch Serverless**: Monitor OCU usage

---

## Troubleshooting

### Lambda Import Module Errors

If Lambda fails with "Unable to import module 'app.main'", check:

1. **File Permissions**: The Docker COPY command may create directories with restrictive permissions. Lambda runs as a non-root user. Fix in Dockerfile:

   ```dockerfile
   COPY app/ ${LAMBDA_TASK_ROOT}/app/
   RUN chmod -R 755 ${LAMBDA_TASK_ROOT}/app/
   ```

2. **Python Bytecode Cache**: Local `__pycache__` files compiled with a different Python version cause conflicts. Add `.dockerignore`:

   ```
   __pycache__/
   *.py[cod]
   *$py.class
   *.pyc
   ```

3. **Docker Build Caching**: Use `--no-cache` to ensure fresh builds:

   ```bash
   docker build --platform linux/amd64 --provenance=false --no-cache -t myimage .
   ```

### AWS_REGION Reserved Variable Error

Lambda reserves `AWS_REGION` - don't set it in environment variables. Lambda provides it automatically.

### Function URL Returns "Forbidden"

After creating a Function URL, add public access permission:

```bash
aws lambda add-permission \
  --function-name YOUR_FUNCTION_NAME \
  --statement-id FunctionURLAllowPublicAccess \
  --action lambda:InvokeFunctionUrl \
  --principal "*" \
  --function-url-auth-type NONE
```

### PyMuPDF/Compilation Errors During Build

Pin versions and use binary-only installation in requirements.txt:

```
PyMuPDF==1.24.11
tiktoken==0.7.0
numpy<2.0
```

Build with `--only-binary` flag:

```dockerfile
RUN pip install --no-cache-dir --only-binary :all: -r requirements.txt
```

### Lambda Timeout Issues

- Increase timeout (max 15 minutes)
- Increase memory (more memory = more CPU)

### DynamoDB Throttling

- Switch to provisioned capacity if predictable
- Enable auto-scaling

### Bedrock Rate Limits

- Implement exponential backoff
- Request quota increase if needed

### Knowledge Base Not Finding Results

- Ensure documents are synced
- Check data source ingestion status
- Verify embedding model is working

---

## Support

For issues specific to this migration, check:

1. CloudWatch Logs for Lambda
2. DynamoDB metrics
3. Bedrock model invocation metrics
4. S3 access logs
