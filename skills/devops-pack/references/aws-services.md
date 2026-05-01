---
name: aws-services
description: 'Use when writing code that interacts with AWS services: S3, SQS, DynamoDB, Lambda, Secrets Manager, or deploying with CDK/CloudFormation. Patterns for Java, C#, JavaScript, Python.'
---
# AWS Services Code Patterns

## S3 — Pre-signed URL Upload

### Java (AWS SDK v2)

```java
// Generate pre-signed PUT URL (server-side)
@Service
@RequiredArgsConstructor
public class DocumentUploadService {
    private final S3Presigner presigner;

    public PresignedUrl generateUploadUrl(UUID documentId, String contentType) {
        PutObjectRequest putRequest = PutObjectRequest.builder()
            .bucket("claims-documents")
            .key("uploads/" + documentId + "/" + UUID.randomUUID())
            .contentType(contentType)
            .build();

        PutObjectPresignRequest presignRequest = PutObjectPresignRequest.builder()
            .signatureDuration(Duration.ofMinutes(5)) // Short-lived
            .putObjectRequest(putRequest)
            .build();

        PresignedPutObjectRequest presigned = presigner.presignPutObject(presignRequest);
        return new PresignedUrl(presigned.url().toString(), presigned.expiration());
    }
}
```

### Python (boto3)

```python
import boto3
from datetime import timedelta

s3_client = boto3.client("s3")

def generate_upload_url(document_id: str, content_type: str) -> str:
    key = f"uploads/{document_id}/{uuid4()}"
    url = s3_client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": "claims-documents",
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=300,  # 5 minutes
    )
    return url
```

### C# (.NET)

```csharp
public class DocumentUploadService(IAmazonS3 s3Client)
{
    public async Task<string> GenerateUploadUrlAsync(Guid documentId, string contentType)
    {
        var request = new GetPreSignedUrlRequest
        {
            BucketName = "claims-documents",
            Key = $"uploads/{documentId}/{Guid.NewGuid()}",
            Verb = HttpVerb.PUT,
            ContentType = contentType,
            Expires = DateTime.UtcNow.AddMinutes(5),
        };
        return await s3Client.GetPreSignedURLAsync(request);
    }
}
```

## SQS — Send and Receive Messages

### Java

```java
// BAD: No idempotency, no error handling
sqsClient.sendMessage(queueUrl, jsonPayload);

// GOOD: Message group for FIFO ordering, deduplication ID
@Service
@RequiredArgsConstructor
public class PaymentEventPublisher {
    private final SqsClient sqsClient;

    @Value("${aws.sqs.payment-events-url}")
    private String queueUrl;

    public void publish(PaymentEvent event) {
        sqsClient.sendMessage(SendMessageRequest.builder()
            .queueUrl(queueUrl)
            .messageBody(objectMapper.writeValueAsString(event))
            .messageGroupId(event.tenantId().toString())     // FIFO: order per tenant
            .messageDeduplicationId(event.eventId().toString()) // Prevent duplicates
            .build());
    }
}

// Consumer with visibility timeout handling
@SqsListener("${aws.sqs.payment-events-url}")
public void handle(@Payload PaymentEvent event, @Header("MessageId") String messageId) {
    if (processedEvents.existsByEventId(event.eventId())) {
        log.info("Skipping duplicate: {}", event.eventId());
        return; // ACK (delete from queue)
    }
    paymentService.process(event);
    processedEvents.save(new ProcessedEvent(event.eventId()));
}
```

### Python

```python
import boto3, json

sqs = boto3.client("sqs")
QUEUE_URL = "https://sqs.ap-southeast-1.amazonaws.com/123456/payment-events.fifo"

def publish_event(event: PaymentEvent) -> None:
    sqs.send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=json.dumps(event.dict()),
        MessageGroupId=str(event.tenant_id),
        MessageDeduplicationId=str(event.event_id),
    )

def poll_and_process() -> None:
    response = sqs.receive_message(
        QueueUrl=QUEUE_URL,
        MaxNumberOfMessages=10,
        WaitTimeSeconds=20,  # Long polling
        VisibilityTimeout=60,  # Must be > processing time
    )
    for msg in response.get("Messages", []):
        try:
            event = PaymentEvent(**json.loads(msg["Body"]))
            process_event(event)
            sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=msg["ReceiptHandle"])
        except Exception as e:
            log.error(f"Failed to process {msg['MessageId']}: {e}")
            # Message returns to queue after visibility timeout
```

## DynamoDB — CRUD Patterns

### JavaScript/TypeScript (AWS SDK v3)

```typescript
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, PutCommand, GetCommand, QueryCommand } from "@aws-sdk/lib-dynamodb";

const client = DynamoDBDocumentClient.from(new DynamoDBClient({}));

// Create with condition (prevent overwrite)
async function createPayment(payment: Payment): Promise<void> {
  await client.send(new PutCommand({
    TableName: "Payments",
    Item: {
      PK: `TENANT#${payment.tenantId}`,
      SK: `PAYMENT#${payment.id}`,
      ...payment,
      createdAt: new Date().toISOString(),
    },
    ConditionExpression: "attribute_not_exists(PK)", // Idempotent create
  }));
}

// Query by tenant (partition key)
async function getPaymentsByTenant(tenantId: string, limit = 20): Promise<Payment[]> {
  const result = await client.send(new QueryCommand({
    TableName: "Payments",
    KeyConditionExpression: "PK = :pk AND begins_with(SK, :prefix)",
    ExpressionAttributeValues: {
      ":pk": `TENANT#${tenantId}`,
      ":prefix": "PAYMENT#",
    },
    Limit: limit,
    ScanIndexForward: false, // Newest first
  }));
  return result.Items as Payment[];
}
```

### Python

```python
import boto3
from boto3.dynamodb.conditions import Key

table = boto3.resource("dynamodb").Table("Payments")

def create_payment(payment: dict) -> None:
    table.put_item(
        Item={
            "PK": f"TENANT#{payment['tenant_id']}",
            "SK": f"PAYMENT#{payment['id']}",
            **payment,
        },
        ConditionExpression="attribute_not_exists(PK)",  # Idempotent
    )

def get_payments_by_tenant(tenant_id: str, limit: int = 20) -> list:
    response = table.query(
        KeyConditionExpression=Key("PK").eq(f"TENANT#{tenant_id}")
            & Key("SK").begins_with("PAYMENT#"),
        Limit=limit,
        ScanIndexForward=False,
    )
    return response["Items"]
```

## Lambda — Handler Patterns

### Python (API Gateway + Lambda)

```python
# BAD: No validation, no error handling, secrets hardcoded
def handler(event, context):
    data = json.loads(event["body"])
    conn = psycopg2.connect("postgresql://user:password@host/db")
    # ...

# GOOD: Validated input, secrets from SSM, structured response
import json, os, boto3
from pydantic import BaseModel, ValidationError

ssm = boto3.client("ssm")
DB_URL = ssm.get_parameter(Name="/app/db-url", WithDecryption=True)["Parameter"]["Value"]

class CreatePaymentRequest(BaseModel):
    tenant_id: str
    amount: float
    currency: str

def handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        request = CreatePaymentRequest(**body)
    except (json.JSONDecodeError, ValidationError) as e:
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}

    try:
        result = create_payment(request)
        return {
            "statusCode": 201,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result),
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"error": "Internal error"})}
```

### Java (Spring Cloud Function on Lambda)

```java
@Bean
public Function<APIGatewayProxyRequestEvent, APIGatewayProxyResponseEvent> createPayment(
        PaymentService paymentService) {
    return request -> {
        try {
            var body = objectMapper.readValue(request.getBody(), CreatePaymentRequest.class);
            var payment = paymentService.create(body);
            return new APIGatewayProxyResponseEvent()
                .withStatusCode(201)
                .withBody(objectMapper.writeValueAsString(PaymentResponse.from(payment)));
        } catch (ValidationException e) {
            return new APIGatewayProxyResponseEvent()
                .withStatusCode(400)
                .withBody("{\"error\":\"" + e.getMessage() + "\"}");
        }
    };
}
```

## Secrets Manager

### Java

```java
// BAD: Hardcoded or environment variable
String dbPassword = System.getenv("DB_PASSWORD");

// GOOD: Secrets Manager with caching
@Configuration
public class SecretsConfig {
    @Bean
    public DataSource dataSource(SecretsManagerClient secretsClient) {
        String secretJson = secretsClient.getSecretValue(
            GetSecretValueRequest.builder().secretId("prod/db-credentials").build()
        ).secretString();

        var creds = objectMapper.readValue(secretJson, DbCredentials.class);
        return DataSourceBuilder.create()
            .url(creds.url())
            .username(creds.username())
            .password(creds.password())
            .build();
    }
}
```

### Python

```python
import boto3, json

def get_secret(secret_name: str) -> dict:
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])

# Usage
db_creds = get_secret("prod/db-credentials")
DATABASE_URL = f"postgresql://{db_creds['username']}:{db_creds['password']}@{db_creds['host']}/{db_creds['dbname']}"
```

## CDK — Infrastructure as Code

### TypeScript (AWS CDK v2)

```typescript
import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as rds from "aws-cdk-lib/aws-rds";
import * as sqs from "aws-cdk-lib/aws-sqs";

export class PaymentServiceStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // VPC with private subnets
    const vpc = new ec2.Vpc(this, "Vpc", {
      maxAzs: 2,
      natGateways: 1,
    });

    // RDS PostgreSQL (Multi-AZ)
    const db = new rds.DatabaseInstance(this, "Database", {
      engine: rds.DatabaseInstanceEngine.postgres({ version: rds.PostgresEngineVersion.VER_16 }),
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MEDIUM),
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      multiAz: true,
      storageEncrypted: true,
      backupRetention: cdk.Duration.days(7),
      deletionProtection: true,
    });

    // SQS FIFO Queue
    const paymentQueue = new sqs.Queue(this, "PaymentQueue", {
      fifo: true,
      contentBasedDeduplication: false, // We provide dedup IDs
      visibilityTimeout: cdk.Duration.seconds(60),
      retentionPeriod: cdk.Duration.days(14),
      deadLetterQueue: {
        queue: new sqs.Queue(this, "PaymentDLQ", { fifo: true }),
        maxReceiveCount: 3,
      },
    });

    // ECS Fargate Service
    const cluster = new ecs.Cluster(this, "Cluster", { vpc });
    const taskDef = new ecs.FargateTaskDefinition(this, "TaskDef", {
      memoryLimitMiB: 1024,
      cpu: 512,
    });

    taskDef.addContainer("App", {
      image: ecs.ContainerImage.fromAsset("./app"),
      portMappings: [{ containerPort: 8080 }],
      logging: ecs.LogDrivers.awsLogs({ streamPrefix: "payment-service" }),
      secrets: {
        DB_URL: ecs.Secret.fromSecretsManager(db.secret!, "host"),
      },
    });

    // Grant permissions (least privilege)
    db.grantConnect(taskDef.taskRole);
    paymentQueue.grantSendMessages(taskDef.taskRole);
  }
}
```

## Anti-Patterns

- Hardcoding AWS credentials or region in code (use SDK default credential chain).
- Using `*` in IAM policies (always specify exact resources and actions).
- SQS visibility timeout shorter than processing time (causes duplicate processing).
- DynamoDB Scan instead of Query (Scan reads entire table, expensive at scale).
- Lambda with VPC for no reason (adds cold start latency; only use VPC if accessing private resources).
- S3 bucket without encryption or lifecycle policy.
- Storing secrets in Lambda environment variables (use Secrets Manager or SSM).
- Single-AZ RDS in production.

## Gotchas

- **Lambda cold start**: 100ms-2s. Worse with VPC (ENI attachment). Use provisioned concurrency for < 100ms SLO.
- **DynamoDB hot partition**: single partition handles 3000 RCU / 1000 WCU. Distribute partition keys evenly.
- **SQS FIFO throughput**: 300 msg/s per queue (3000 with high throughput mode). Use multiple message groups.
- **S3 request rate**: 5500 GET/s and 3500 PUT/s per prefix. Use random prefixes for high-throughput.
- **Secrets Manager cost**: $0.40/secret/month + $0.05/10K API calls. Cache secrets in-process with TTL.
- **RDS Proxy**: required for Lambda → RDS to avoid connection exhaustion. Adds ~5ms latency.
- **EventBridge**: max 256KB event size. For larger payloads, put data in S3 and send S3 reference in event.
- **CDK bootstrap**: must run `cdk bootstrap` once per account+region before first deploy.
