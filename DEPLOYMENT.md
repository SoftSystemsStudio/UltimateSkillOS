# Deployment Guide

This guide covers deploying UltimateSkillOS in various environments.

## Docker Deployment

### Quick Start with Docker Compose

The easiest way to deploy the application is using Docker Compose:

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

Access the application at `http://localhost:8002`

### Docker Build Only

Build and run the container without Docker Compose:

```bash
# Build the image
docker build -t ultimateskillos:latest .

# Run the container
docker run -d \
  -p 8002:8002 \
  --name ultimateskillos \
  -e SKILLOS_MAX_STEPS=6 \
  ultimateskillos:latest
```

### Environment Variables

Configure the application using these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SKILLOS_MAX_STEPS` | `6` | Maximum steps per agent execution |
| `SKILLOS_VERBOSE` | `false` | Enable verbose logging |
| `SKILLOS_CIRCUIT_REDIS_URL` | `None` | Redis URL for circuit breaker (optional) |
| `SKILLOS_ROUTING_MODE` | `keyword` | Routing mode: `keyword`, `hybrid`, or `ml` |

### Volumes

The Docker setup uses these volumes:

- `./data` - Persistent data and feedback logs
- `./memory_store` - FAISS indices and memory storage
- `redis_data` - Redis persistence (when using Redis)

## Cloud Deployment

### AWS (ECS/Fargate)

1. Push image to ECR:
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker tag ultimateskillos:latest <account>.dkr.ecr.us-east-1.amazonaws.com/ultimateskillos:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/ultimateskillos:latest
```

2. Create ECS task definition with:
   - Container port: 8002
   - Health check: `/health`
   - Environment variables as needed
   - Mount EFS for persistent storage

3. Create ECS service with ALB for HTTPS

### Google Cloud (Cloud Run)

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT_ID/ultimateskillos

# Deploy to Cloud Run
gcloud run deploy ultimateskillos \
  --image gcr.io/PROJECT_ID/ultimateskillos \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8002 \
  --set-env-vars SKILLOS_MAX_STEPS=6
```

### Azure (Container Instances)

```bash
# Build and push to ACR
az acr build --registry <registry-name> --image ultimateskillos:latest .

# Deploy to ACI
az container create \
  --resource-group <resource-group> \
  --name ultimateskillos \
  --image <registry-name>.azurecr.io/ultimateskillos:latest \
  --dns-name-label ultimateskillos \
  --ports 8002 \
  --environment-variables SKILLOS_MAX_STEPS=6
```

### Heroku

```bash
# Login and create app
heroku login
heroku create ultimateskillos

# Set stack to container
heroku stack:set container

# Deploy
git push heroku main

# Set environment variables
heroku config:set SKILLOS_MAX_STEPS=6
```

## Kubernetes Deployment

Create a deployment YAML:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ultimateskillos
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ultimateskillos
  template:
    metadata:
      labels:
        app: ultimateskillos
    spec:
      containers:
      - name: app
        image: ultimateskillos:latest
        ports:
        - containerPort: 8002
        env:
        - name: SKILLOS_MAX_STEPS
          value: "6"
        livenessProbe:
          httpGet:
            path: /health
            port: 8002
          initialDelaySeconds: 40
          periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: ultimateskillos
spec:
  selector:
    app: ultimateskillos
  ports:
  - port: 80
    targetPort: 8002
  type: LoadBalancer
```

Deploy:
```bash
kubectl apply -f deployment.yaml
```

## Production Considerations

### Security

1. **HTTPS**: Use a reverse proxy (nginx, traefik) or cloud load balancer for TLS termination
2. **Authentication**: Add API key validation or OAuth middleware
3. **Rate Limiting**: Implement rate limiting to prevent abuse
4. **Secrets Management**: Use cloud provider secrets management for sensitive config

### Monitoring

1. **Health Checks**: The `/health` endpoint is ready for monitoring
2. **Logging**: Configure structured logging output
3. **Metrics**: Consider adding Prometheus metrics
4. **Tracing**: Add OpenTelemetry for distributed tracing

### Scaling

1. **Horizontal Scaling**: Run multiple instances behind a load balancer
2. **Redis**: Use managed Redis (ElastiCache, Cloud Memorystore) for circuit breaker state
3. **Storage**: Use cloud object storage (S3, GCS) for persistent data
4. **Memory**: Increase container memory for larger models/indices

### Performance

1. **Workers**: Increase uvicorn workers: `uvicorn api:app --workers 4`
2. **Connection Pooling**: Configure database connection pools
3. **Caching**: Enable Redis for response caching
4. **CDN**: Serve static web UI files from CDN

## Troubleshooting

### Container won't start

- Check logs: `docker logs <container>`
- Verify environment variables are set correctly
- Ensure required volumes are mounted

### Health check failing

- Verify port 8002 is exposed and accessible
- Check if application is starting correctly
- Review startup logs for errors

### High memory usage

- Reduce `SKILLOS_MAX_STEPS`
- Limit concurrent requests
- Increase container memory allocation

### Agent initialization errors

- Verify all required dependencies are installed
- Check Python version (requires 3.12+)
- Review configuration file syntax

## Support

For issues or questions:
- GitHub Issues: https://github.com/SoftSystemsStudio/UltimateSkillOS/issues
- Documentation: See README.md and other docs in the repo
