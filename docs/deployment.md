# Deployment Guide

Multiple options for deploying your Strands agents to production.

## Quick Decision Matrix

| Option | Best For | Setup Time | Cost | Complexity |
|--------|----------|-----------|------|------------|
| **Local** | Development, testing | 0 min | Free | ⭐ |
| **AgentCore Runtime** | AWS-hosted production | 10 min | Pay-per-use | ⭐⭐ |
| **Docker + EC2** | Self-hosted, full control | 30 min | ~$20/mo | ⭐⭐⭐ |
| **Lambda** | Serverless, event-driven | 20 min | Pay-per-invoke | ⭐⭐⭐ |

**Recommendation:** Start local, deploy to AgentCore when ready for production.

---

## Option 1: Local Development (Start Here)

**Best for:** Building and testing agents

```bash
# Run your agent locally
python main.py

# Or run specific agent
python agents/your_agent.py
```

**Pros:**
- Instant feedback
- Easy debugging
- No deployment complexity
- Free

**Cons:**
- Not accessible remotely
- Requires your machine running
- No scaling

---

## Option 2: AWS Bedrock AgentCore Runtime (Recommended for Production)

**Best for:** Production deployment with managed infrastructure

### Prerequisites
- AWS Account with credentials configured
- Python 3.10+
- Boto3 installed
- Model access: Claude Sonnet 4.0 in Bedrock console
- AWS permissions for AgentCore

### Quick Start (10 minutes)

#### 1. Install AgentCore Toolkit
```bash
pip install bedrock-agentcore strands-agents bedrock-agentcore-starter-toolkit
```

#### 2. Create AgentCore-Compatible Agent

**File: `agentcore_agent.py`**
```python
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent
from strands_tools import http_request, file_write

app = BedrockAgentCoreApp()

# Your agent
agent = Agent(
    tools=[http_request, file_write],
    system_prompt="Your agent's instructions here"
)

@app.entrypoint
def invoke(payload):
    """AgentCore entry point."""
    user_message = payload.get("prompt", "Hello!")
    result = agent(user_message)
    return {"result": result.message}

if __name__ == "__main__":
    app.run()
```

#### 3. Test Locally
```bash
# Terminal 1: Start agent
python agentcore_agent.py

# Terminal 2: Test it
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello!"}'
```

#### 4. Configure for Deployment
```bash
# Configure deployment
agentcore configure -e agentcore_agent.py

# Accept defaults or customize:
# - AWS Region (default: us-west-2)
# - Memory options (STM only or STM + LTM)
# - Execution role
```

#### 5. Deploy to AgentCore
```bash
# Deploy agent to AWS
agentcore launch

# Note the ARN in the output - you'll need it!
```

#### 6. Invoke Your Deployed Agent

**Option A: CLI**
```bash
agentcore invoke '{"prompt": "Your query here"}'
```

**Option B: Python (Boto3)**
```python
import json
import uuid
import boto3

agent_arn = "arn:aws:bedrock-agentcore:us-west-2:123456789:agent/your-agent"
prompt = "Your query"

client = boto3.client('bedrock-agentcore')

response = client.invoke_agent_runtime(
    agentRuntimeArn=agent_arn,
    runtimeSessionId=str(uuid.uuid4()),
    payload=json.dumps({"prompt": prompt}).encode(),
    qualifier="DEFAULT"
)

# Process response
content = []
for chunk in response.get("response", []):
    content.append(chunk.decode('utf-8'))
print(json.loads(''.join(content)))
```

#### 7. Check Status and Logs
```bash
# Check deployment status
agentcore status

# View resources in AWS Console:
# - Logs: CloudWatch → /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT
# - Memory: Bedrock AgentCore → Memory
# - Container: ECR → Repositories
```

#### 8. Cleanup When Done
```bash
# Remove agent from AgentCore
agentcore destroy
```

### AgentCore Deployment Modes

**Default (Recommended):** CodeBuild + Cloud Runtime
```bash
agentcore launch  # No Docker needed!
```

**Local Development:**
```bash
agentcore launch --local  # Requires Docker
```

**Hybrid:** Local Build + Cloud Runtime
```bash
agentcore launch --local-build  # Requires Docker
```

### AgentCore Best Practices

1. **Enable Observability**
   - Enable CloudWatch Transaction Search
   - Monitor in AgentCore console
   - Track token usage and costs

2. **Use Memory Features**
   - Configure STM for short-term context
   - Add LTM for long-term knowledge extraction
   - Access via invocation state

3. **Handle Errors**
   - Check deployment status before invoking
   - Monitor CloudWatch logs
   - Test locally before deploying

4. **Manage Costs**
   - Use `agentcore destroy` when not needed
   - Monitor token usage
   - Set up AWS billing alerts

### Troubleshooting AgentCore

**Permission denied:**
- Verify IAM permissions for AgentCore
- Check execution role has required permissions

**Build failed:**
- Check CodeBuild logs in AWS Console
- Verify requirements.txt is correct
- Ensure ARM64 compatibility

**Agent not responding:**
- Check deployment status: `agentcore status`
- View CloudWatch logs
- Verify model access in Bedrock console

**Port 8080 in use (local only):**
```bash
# Kill process on port 8080
lsof -ti:8080 | xargs kill -9
```

### Resources
- [AgentCore Docs](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
- [Starter Toolkit](https://github.com/awslabs/bedrock-agentcore-starter-toolkit)
- [Strands + AgentCore Guide](docs/strands-guide.md)

---

## Option 3: Docker + AWS EC2/ECS

**Best for:** Full control, custom infrastructure

### Quick Docker Setup

**Dockerfile:**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

**Build and Run:**
```bash
# Build image
docker build -t my-agent .

# Run locally
docker run -p 8080:8080 --env-file .env my-agent

# Push to ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-west-2.amazonaws.com
docker tag my-agent:latest <account>.dkr.ecr.us-west-2.amazonaws.com/my-agent:latest
docker push <account>.dkr.ecr.us-west-2.amazonaws.com/my-agent:latest
```

### Deploy to EC2
1. Launch EC2 instance (t3.small minimum)
2. Install Docker
3. Pull and run your container
4. Set up HTTPS with SSL certificate
5. Configure auto-restart

### Deploy to ECS
1. Create ECS cluster
2. Define task definition
3. Create service with load balancer
4. Configure auto-scaling

**Time:** 30-60 minutes | **Cost:** ~$20-50/month

---

## Option 4: AWS Lambda (Serverless)

**Best for:** Event-driven, sporadic usage

### Limitations
- 15-minute timeout
- Cold starts
- Limited to REST/Event triggers

### Quick Setup

**Lambda Handler:**
```python
import json
from strands import Agent

agent = Agent(...)

def lambda_handler(event, context):
    prompt = json.loads(event['body']).get('prompt')
    response = agent(prompt)
    
    return {
        'statusCode': 200,
        'body': json.dumps({'result': str(response)})
    }
```

**Deploy:**
```bash
# Package dependencies
pip install -r requirements.txt -t package/
cp *.py package/
cd package && zip -r ../lambda.zip .

# Deploy with AWS CLI
aws lambda create-function \
  --function-name my-agent \
  --runtime python3.10 \
  --handler main.lambda_handler \
  --zip-file fileb://lambda.zip \
  --role <lambda-execution-role-arn>
```

**Time:** 20-30 minutes | **Cost:** Pay per invocation

---

## Deployment Checklist

Before deploying to production:

- [ ] Agent works locally
- [ ] Environment variables configured
- [ ] Error handling implemented
- [ ] Logging configured
- [ ] Token usage monitored
- [ ] Security reviewed (no hardcoded keys)
- [ ] Costs estimated
- [ ] Rollback plan ready

## Cost Comparison (Monthly Estimates)

| Option | Compute | Storage | Data Transfer | Total Est. |
|--------|---------|---------|---------------|------------|
| Local | $0 | $0 | $0 | **$0** |
| AgentCore | Pay-per-use | Included | Included | **$10-50** |
| EC2 (t3.small) | $15 | $5 | $5 | **$25** |
| Lambda | Pay-per-invoke | $0 | $0 | **$5-20** |

*Plus API costs (Anthropic/OpenAI)*

---

## Recommended Path

### Phase 1: Build (Week 1)
- ✅ Build agent locally
- ✅ Test thoroughly
- ✅ Create demos

### Phase 2: Deploy (Week 2)
- 🎯 Deploy to AgentCore
- 🎯 Test production deployment
- 🎯 Monitor for 1 week

### Phase 3: Optimize (Week 3)
- ⚙️ Add monitoring
- ⚙️ Optimize costs
- ⚙️ Scale if needed

**Don't deploy until you have a working agent worth deploying.**

---

## Quick Commands Reference

```bash
# Local development
python main.py

# AgentCore deployment
agentcore configure -e agentcore_agent.py
agentcore launch
agentcore invoke '{"prompt": "test"}'
agentcore status
agentcore destroy

# Docker
docker build -t my-agent .
docker run -p 8080:8080 my-agent

# Check if agent is running
curl http://localhost:8080/health
```

---

## When to Deploy

**Deploy to AgentCore when:**
- ✅ Agent works reliably locally
- ✅ You need remote access
- ✅ You have users/clients testing
- ✅ You want to showcase production deployment

**Don't deploy when:**
- ❌ Agent is still under development
- ❌ You're making frequent changes
- ❌ Local testing is sufficient
- ❌ You haven't tested error cases

**Rule:** Build → Test → Validate → Deploy. In that order.