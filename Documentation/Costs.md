## **Table 1: Prototype Level Usage** (Few developers, ~5-10 test users)

| AWS Service                       | Component                    | Usage Assumptions            | Unit Price                          | Monthly Cost     |
| --------------------------------- | ---------------------------- | ---------------------------- | ----------------------------------- | ---------------- |
| **DynamoDB**                      | Read/Write Requests          | 500K reads, 200K writes      | $0.125/M reads, $0.625/M writes     | **$0.19**        |
|                                   | Storage                      | 1 GB (6 tables)              | $0.25/GB (first 25GB free)          | **$0.00**        |
| **S3**                            | Storage                      | 5 GB documents               | $0.023/GB                           | **$0.12**        |
|                                   | Requests                     | 10K PUT, 50K GET             | $0.005/1K PUT, $0.0004/1K GET       | **$0.07**        |
| **Lambda**                        | Requests                     | 50K invocations              | $0.20/M (1M free)                   | **$0.00**        |
|                                   | Duration                     | 50K × 500ms × 1GB            | $0.0000166667/GB-s (400K GB-s free) | **$0.00**        |
| **API Gateway**                   | HTTP API Requests            | 50K requests                 | $1.00/M (1M free)                   | **$0.00**        |
| **Bedrock - Amazon Nova Lite**     | Input Tokens                 | 5M tokens/month              | $0.00006/1K tokens                  | **$0.30**        |
|                                   | Output Tokens                | 2M tokens/month              | $0.00024/1K tokens                  | **$0.48**        |
| **Bedrock - Titan Embeddings V2** | Input Tokens                 | 2M tokens/month              | $0.00002/1K tokens                  | **$0.04**        |
| **MongoDB Atlas**                 | Vector Search (M0 Free Tier) | 512 MB storage, shared       | Free                                | **$0.00**        |
| **ECR**                           | Storage                      | 2 GB (container image)       | $0.10/GB                            | **$0.20**        |
|                                   | Data Transfer                | In-region (free)             | $0.00                               | **$0.00**        |
| **EventBridge**                   | Scheduler                    | 8K invocations (hourly quiz) | $1.00/M (14M free)                  | **$0.00**        |
|                                   | Events                       | 10K custom events            | $1.00/M                             | **$0.01**        |
| **CloudWatch**                    | Logs Ingestion               | 2 GB                         | $0.50/GB (5GB free)                 | **$0.00**        |
|                                   | Logs Storage                 | 2 GB                         | $0.03/GB                            | **$0.06**        |
|                                   | Alarms                       | 5 alarms                     | $0.10/alarm (10 free)               | **$0.00**        |
|                                   |                              |                              | **TOTAL**                           | **~$1.47/month** |

---

## **Table 2: Early Product Release** (~500-1000 active users)

| AWS Service                       | Component                     | Usage Assumptions         | Unit Price                      | Monthly Cost       |
| --------------------------------- | ----------------------------- | ------------------------- | ------------------------------- | ------------------ |
| **DynamoDB**                      | Read/Write Requests           | 20M reads, 10M writes     | $0.125/M reads, $0.625/M writes | **$8.75**          |
|                                   | Storage                       | 25 GB (6 tables)          | $0.25/GB (first 25GB free)      | **$0.00**          |
| **S3**                            | Storage                       | 50 GB documents           | $0.023/GB                       | **$1.15**          |
|                                   | Requests                      | 200K PUT, 1M GET          | $0.005/1K PUT, $0.0004/1K GET   | **$1.40**          |
| **Lambda**                        | Requests                      | 3M invocations            | $0.20/M (1M free)               | **$0.40**          |
|                                   | Duration                      | 3M × 500ms × 1GB          | $0.0000166667/GB-s              | **$25.00**         |
| **API Gateway**                   | HTTP API Requests             | 3M requests               | $1.00/M                         | **$2.00**          |
| **Bedrock - Amazon Nova Lite**     | Input Tokens                  | 100M tokens/month         | $0.00006/1K tokens              | **$6.00**          |
|                                   | Output Tokens                 | 40M tokens/month          | $0.00024/1K tokens              | **$9.60**          |
| **Bedrock - Titan Embeddings V2** | Input Tokens                  | 20M tokens/month          | $0.00002/1K tokens              | **$0.40**          |
| **MongoDB Atlas**                 | Vector Search (M10 Dedicated) | 10 GB storage, dedicated  | ~$57/month                      | **$57.00**         |
| **ECR**                           | Storage                       | 5 GB (multi-version)      | $0.10/GB                        | **$0.50**          |
|                                   | Data Transfer                 | In-region (free)          | $0.00                           | **$0.00**          |
| **EventBridge**                   | Scheduler                     | 744K invocations          | $1.00/M (14M free)              | **$0.00**          |
|                                   | Events                        | 500K custom events        | $1.00/M                         | **$0.50**          |
| **CloudWatch**                    | Logs Ingestion                | 20 GB                     | $0.50/GB (5GB free)             | **$7.50**          |
|                                   | Logs Storage                  | 20 GB (1 month retention) | $0.03/GB                        | **$0.60**          |
|                                   | Alarms                        | 15 alarms                 | $0.10/alarm                     | **$0.50**          |
|                                   | Metrics                       | 50 custom metrics         | $0.30/metric (10 free)          | **$12.00**         |
|                                   |                               |                           | **TOTAL**                       | **~$133.30/month** |

---

## **Cost Breakdown Summary**

| Category                          | Prototype  | Early Release |
| --------------------------------- | ---------- | ------------- |
| **Database (DynamoDB)**           | $0.19      | $8.75         |
| **Storage (S3)**                  | $0.19      | $2.55         |
| **Compute (Lambda)**              | $0.00      | $25.40        |
| **API (Gateway)**                 | $0.00      | $2.00         |
| **AI/ML (Bedrock)**               | $0.82      | $16.00        |
| **Vector Search (MongoDB Atlas)** | $0.00      | $57.00        |
| **Container (ECR)**               | $0.20      | $0.50         |
| **Scheduling (EventBridge)**      | $0.01      | $0.50         |
| **Monitoring (CloudWatch)**       | $0.06      | $20.60        |
| **TOTAL**                         | **~$1.47** | **~$133.30**  |

