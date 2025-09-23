# AI-Powered Migration Validation System - Deployment Guide

**Version**: 1.0.0
**Date**: 2025-09-19
**Target Environments**: Development, Staging, Production

## Deployment Overview

This guide provides comprehensive instructions for deploying the AI-Powered Migration Validation System using a **direct master branch deployment strategy** with containerized deployment using Docker and Kubernetes, along with supporting infrastructure components.

### **Deployment Strategy**

This system uses a **direct master deployment approach** for simplified, streamlined releases:

- **No Feature Branches**: All development happens directly on the master branch
- **No Pull Requests**: Changes are committed directly to master after local testing
- **Automatic Deployment**: Every push to master triggers immediate production deployment
- **Quality Gates**: Comprehensive CI pipeline ensures code quality before deployment
- **Fast Feedback**: Immediate deployment enables rapid iteration and bug fixes

**Benefits of Direct Master Deployment:**
- Simplified workflow reduces complexity and bottlenecks
- Faster time-to-production for features and fixes
- Reduced merge conflicts and integration issues
- Clear deployment history tied to commit history
- Streamlined dependency updates and security patches

## Architecture Components

### **Core Services**
- **API Server**: FastAPI application (Python)
- **Background Workers**: Celery workers for async processing
- **Message Queue**: Redis for task queuing and caching
- **Database**: PostgreSQL for persistent storage
- **File Storage**: Local filesystem or S3-compatible storage
- **Load Balancer**: Nginx for traffic distribution

### **Monitoring & Observability**
- **Metrics**: Prometheus for metrics collection
- **Visualization**: Grafana dashboards
- **Logging**: ELK stack (Elasticsearch, Logstash, Kibana)
- **Tracing**: Jaeger for distributed tracing
- **Error Tracking**: Sentry for error monitoring

## Prerequisites

### **System Requirements**

#### **Development Environment**
- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+
- 8GB RAM minimum
- 20GB disk space

#### **Production Environment**
- Kubernetes 1.24+
- Minimum 3 nodes
- 16GB RAM per node
- 100GB SSD storage per node
- Load balancer (cloud provider or HAProxy)

### **External Dependencies**
- **LLM API Access**: OpenAI, Anthropic, Google Cloud AI
- **SSL Certificates**: For HTTPS encryption
- **DNS Configuration**: For domain routing
- **Backup Storage**: For database and file backups

## Development Deployment

### **Docker Compose Setup**

#### **1. Environment Configuration**
```bash
# Create environment file
cp .env.example .env

# Edit configuration
cat > .env << EOF
# Application
ENVIRONMENT=development
SECRET_KEY=your-secret-key-here
DEBUG=true

# Database
DATABASE_URL=postgresql://postgres:password@postgres:5432/migration_validator
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=migration_validator

# Redis
REDIS_URL=redis://redis:6379/0

# LLM Providers
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GOOGLE_AI_API_KEY=your-google-key

# File Storage
UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE=10485760  # 10MB
MAX_TOTAL_SIZE=104857600  # 100MB

# Security
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=RS256
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# Monitoring
SENTRY_DSN=your-sentry-dsn
PROMETHEUS_ENABLED=true
EOF
```

#### **2. Docker Compose Configuration**
```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: development
    ports:
      - "8000:8000"
    volumes:
      - ./src:/app/src
      - ./uploads:/app/uploads
    environment:
      - ENVIRONMENT=development
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
    command: ["uvicorn", "src.api.routes:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

  worker:
    build:
      context: .
      dockerfile: Dockerfile
      target: development
    volumes:
      - ./src:/app/src
      - ./uploads:/app/uploads
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
    command: ["celery", "-A", "src.core.tasks", "worker", "--loglevel=info"]

  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: migration_validator
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./config/nginx/development.conf:/etc/nginx/nginx.conf
    depends_on:
      - app

volumes:
  postgres_data:
  redis_data:
```

#### **3. Development Dockerfile**
```dockerfile
# Dockerfile
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

# Development stage
FROM base as development
COPY . .
EXPOSE 8000
CMD ["uvicorn", "src.api.routes:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.api.routes:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### **4. Start Development Environment**
```bash
# Build and start services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f app

# Run database migrations
docker-compose exec app python -m alembic upgrade head

# Create initial admin user
docker-compose exec app python scripts/create_admin.py

# Access application
curl http://localhost:8000/health
```

## Staging Deployment

### **Kubernetes Configuration**

#### **1. Namespace and ConfigMap**
```yaml
# k8s/namespace.yml
apiVersion: v1
kind: Namespace
metadata:
  name: migration-validator-staging
  labels:
    environment: staging

---
# k8s/configmap.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: migration-validator-config
  namespace: migration-validator-staging
data:
  ENVIRONMENT: "staging"
  DEBUG: "false"
  DATABASE_URL: "postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@postgres:5432/$(POSTGRES_DB)"
  REDIS_URL: "redis://redis:6379/0"
  PROMETHEUS_ENABLED: "true"
  LOG_LEVEL: "INFO"
```

#### **2. Secrets Management**
```yaml
# k8s/secrets.yml
apiVersion: v1
kind: Secret
metadata:
  name: migration-validator-secrets
  namespace: migration-validator-staging
type: Opaque
data:
  SECRET_KEY: <base64-encoded-secret>
  JWT_SECRET_KEY: <base64-encoded-jwt-secret>
  POSTGRES_USER: <base64-encoded-user>
  POSTGRES_PASSWORD: <base64-encoded-password>
  POSTGRES_DB: <base64-encoded-db-name>
  OPENAI_API_KEY: <base64-encoded-openai-key>
  ANTHROPIC_API_KEY: <base64-encoded-anthropic-key>
  SENTRY_DSN: <base64-encoded-sentry-dsn>
```

#### **3. Database Deployment**
```yaml
# k8s/postgres.yml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: migration-validator-staging
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: migration-validator-secrets
              key: POSTGRES_USER
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: migration-validator-secrets
              key: POSTGRES_PASSWORD
        - name: POSTGRES_DB
          valueFrom:
            secretKeyRef:
              name: migration-validator-secrets
              key: POSTGRES_DB
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 20Gi

---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: migration-validator-staging
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
```

#### **4. Redis Deployment**
```yaml
# k8s/redis.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: migration-validator-staging
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        args: ["redis-server", "--appendonly", "yes"]
        volumeMounts:
        - name: redis-storage
          mountPath: /data
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
      volumes:
      - name: redis-storage
        persistentVolumeClaim:
          claimName: redis-pvc

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: migration-validator-staging
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi

---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: migration-validator-staging
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
```

#### **5. Application Deployment**
```yaml
# k8s/app.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: migration-validator-app
  namespace: migration-validator-staging
spec:
  replicas: 3
  selector:
    matchLabels:
      app: migration-validator-app
  template:
    metadata:
      labels:
        app: migration-validator-app
    spec:
      containers:
      - name: app
        image: migration-validator:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: migration-validator-config
        env:
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: migration-validator-secrets
              key: SECRET_KEY
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: migration-validator-secrets
              key: POSTGRES_USER
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: migration-validator-secrets
              key: POSTGRES_PASSWORD
        - name: POSTGRES_DB
          valueFrom:
            secretKeyRef:
              name: migration-validator-secrets
              key: POSTGRES_DB
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: migration-validator-secrets
              key: OPENAI_API_KEY
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/detailed
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        volumeMounts:
        - name: upload-storage
          mountPath: /app/uploads
      volumes:
      - name: upload-storage
        persistentVolumeClaim:
          claimName: upload-pvc

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: upload-pvc
  namespace: migration-validator-staging
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 50Gi

---
apiVersion: v1
kind: Service
metadata:
  name: migration-validator-service
  namespace: migration-validator-staging
spec:
  selector:
    app: migration-validator-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

#### **6. Worker Deployment**
```yaml
# k8s/worker.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: migration-validator-worker
  namespace: migration-validator-staging
spec:
  replicas: 2
  selector:
    matchLabels:
      app: migration-validator-worker
  template:
    metadata:
      labels:
        app: migration-validator-worker
    spec:
      containers:
      - name: worker
        image: migration-validator:latest
        command: ["celery", "-A", "src.core.tasks", "worker", "--loglevel=info"]
        envFrom:
        - configMapRef:
            name: migration-validator-config
        env:
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: migration-validator-secrets
              key: SECRET_KEY
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: migration-validator-secrets
              key: POSTGRES_USER
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: migration-validator-secrets
              key: POSTGRES_PASSWORD
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: migration-validator-secrets
              key: OPENAI_API_KEY
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        volumeMounts:
        - name: upload-storage
          mountPath: /app/uploads
      volumes:
      - name: upload-storage
        persistentVolumeClaim:
          claimName: upload-pvc
```

#### **7. Ingress Configuration**
```yaml
# k8s/ingress.yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: migration-validator-ingress
  namespace: migration-validator-staging
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - staging-api.migration-validator.com
    secretName: migration-validator-tls
  rules:
  - host: staging-api.migration-validator.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: migration-validator-service
            port:
              number: 80
```

### **Staging Deployment Commands**
```bash
# Create namespace and apply configurations
kubectl apply -f k8s/namespace.yml
kubectl apply -f k8s/secrets.yml
kubectl apply -f k8s/configmap.yml

# Deploy database and cache
kubectl apply -f k8s/postgres.yml
kubectl apply -f k8s/redis.yml

# Wait for database to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n migration-validator-staging --timeout=300s

# Run database migrations
kubectl run migration --image=migration-validator:latest \
  --rm -i --restart=Never \
  -n migration-validator-staging \
  --env-from=configmap/migration-validator-config \
  --env="SECRET_KEY=$(kubectl get secret migration-validator-secrets -o jsonpath='{.data.SECRET_KEY}' | base64 -d)" \
  -- python -m alembic upgrade head

# Deploy application and workers
kubectl apply -f k8s/app.yml
kubectl apply -f k8s/worker.yml

# Deploy ingress
kubectl apply -f k8s/ingress.yml

# Check deployment status
kubectl get pods -n migration-validator-staging
kubectl get services -n migration-validator-staging
kubectl get ingress -n migration-validator-staging
```

## Production Deployment

### **Production Considerations**

#### **1. High Availability Setup**
```yaml
# k8s/production/app-ha.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: migration-validator-app
  namespace: migration-validator-prod
spec:
  replicas: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  selector:
    matchLabels:
      app: migration-validator-app
  template:
    metadata:
      labels:
        app: migration-validator-app
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - migration-validator-app
              topologyKey: kubernetes.io/hostname
      containers:
      - name: app
        image: migration-validator:v1.0.0  # Use specific version tags
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        # Enhanced health checks
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/detailed
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
```

#### **2. Database High Availability**
```yaml
# k8s/production/postgres-ha.yml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: postgres-cluster
  namespace: migration-validator-prod
spec:
  instances: 3

  postgresql:
    parameters:
      max_connections: "200"
      shared_buffers: "256MB"
      effective_cache_size: "1GB"
      work_mem: "4MB"

  bootstrap:
    initdb:
      database: migration_validator
      owner: migration_user
      secret:
        name: postgres-credentials

  storage:
    size: 100Gi
    storageClass: fast-ssd

  monitoring:
    enabled: true

  backup:
    target: prefer-standby
    retentionPolicy: "30d"
    data:
      compression: gzip
    wal:
      retention: "7d"
```

#### **3. Horizontal Pod Autoscaler**
```yaml
# k8s/production/hpa.yml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: migration-validator-hpa
  namespace: migration-validator-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: migration-validator-app
  minReplicas: 5
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
```

### **Monitoring Setup**

#### **1. Prometheus Configuration**
```yaml
# k8s/monitoring/prometheus.yml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: prometheus
  namespace: monitoring
spec:
  replicas: 2
  serviceAccountName: prometheus
  serviceMonitorSelector:
    matchLabels:
      app: migration-validator
  ruleSelector:
    matchLabels:
      app: migration-validator
  retention: 30d
  storage:
    volumeClaimTemplate:
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 50Gi

---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: migration-validator-metrics
  namespace: migration-validator-prod
  labels:
    app: migration-validator
spec:
  selector:
    matchLabels:
      app: migration-validator-app
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

#### **2. Grafana Dashboard**
```yaml
# k8s/monitoring/grafana-dashboard.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: migration-validator-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  migration-validator.json: |
    {
      "dashboard": {
        "title": "Migration Validator System",
        "panels": [
          {
            "title": "Request Rate",
            "type": "graph",
            "targets": [
              {
                "expr": "rate(http_requests_total{service=\"migration-validator\"}[5m])",
                "legendFormat": "{{method}} {{endpoint}}"
              }
            ]
          },
          {
            "title": "Response Time",
            "type": "graph",
            "targets": [
              {
                "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service=\"migration-validator\"}[5m]))",
                "legendFormat": "95th percentile"
              }
            ]
          },
          {
            "title": "LLM API Usage",
            "type": "graph",
            "targets": [
              {
                "expr": "rate(llm_requests_total[5m])",
                "legendFormat": "{{provider}} {{model}}"
              }
            ]
          }
        ]
      }
    }
```

### **Backup and Disaster Recovery**

#### **1. Database Backup Script**
```bash
#!/bin/bash
# scripts/backup-database.sh

NAMESPACE="migration-validator-prod"
BACKUP_BUCKET="migration-validator-backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create database backup
kubectl exec -n $NAMESPACE postgres-cluster-1 -- \
  pg_dump -U migration_user migration_validator | \
  gzip > "db_backup_${DATE}.sql.gz"

# Upload to S3
aws s3 cp "db_backup_${DATE}.sql.gz" "s3://${BACKUP_BUCKET}/database/"

# Cleanup local backup
rm "db_backup_${DATE}.sql.gz"

# Retain only last 30 days of backups
aws s3 ls "s3://${BACKUP_BUCKET}/database/" | \
  head -n -30 | \
  awk '{print $4}' | \
  xargs -I {} aws s3 rm "s3://${BACKUP_BUCKET}/database/{}"
```

#### **2. File Storage Backup**
```bash
#!/bin/bash
# scripts/backup-files.sh

NAMESPACE="migration-validator-prod"
BACKUP_BUCKET="migration-validator-backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create temporary pod for backup
kubectl run backup-pod --image=alpine --rm -i --restart=Never \
  -n $NAMESPACE \
  --overrides='
{
  "spec": {
    "containers": [
      {
        "name": "backup",
        "image": "alpine",
        "command": ["sleep", "3600"],
        "volumeMounts": [
          {
            "name": "upload-storage",
            "mountPath": "/uploads"
          }
        ]
      }
    ],
    "volumes": [
      {
        "name": "upload-storage",
        "persistentVolumeClaim": {
          "claimName": "upload-pvc"
        }
      }
    ]
  }
}' \
  -- tar czf - -C /uploads . | \
  aws s3 cp - "s3://${BACKUP_BUCKET}/files/uploads_${DATE}.tar.gz"
```

### **SSL/TLS Configuration**

#### **1. Certificate Management**
```yaml
# k8s/security/certificate.yml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@migration-validator.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx

---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: migration-validator-cert
  namespace: migration-validator-prod
spec:
  secretName: migration-validator-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - api.migration-validator.com
  - www.migration-validator.com
```

## CI/CD Pipeline

### **GitHub Actions Workflow**
```yaml
# .github/workflows/deploy.yml
name: Build and Deploy

on:
  push:
    branches: [master]
    tags: ['v*']

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: migration-validator

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
    - name: Checkout
      uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2

    - name: Login to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=semver,pattern={{version}}
          type=semver,pattern={{major}}.{{minor}}

    - name: Build and push
      uses: docker/build-push-action@v4
      with:
        context: .
        platforms: linux/amd64,linux/arm64
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        target: production
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy-production:
    if: github.ref == 'refs/heads/master'
    needs: build
    runs-on: ubuntu-latest
    environment: production

    steps:
    - name: Checkout
      uses: actions/checkout@v3

    - name: Setup kubectl
      uses: azure/setup-kubectl@v3
      with:
        version: 'v1.24.0'

    - name: Configure kubectl
      run: |
        echo "${{ secrets.KUBE_CONFIG_PROD }}" | base64 -d > kubeconfig
        export KUBECONFIG=kubeconfig

    - name: Deploy to production
      run: |
        kubectl set image deployment/migration-validator-app \
          app=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:master \
          -n migration-validator-prod
        kubectl rollout status deployment/migration-validator-app \
          -n migration-validator-prod --timeout=300s

  deploy-tagged-release:
    if: startsWith(github.ref, 'refs/tags/v')
    needs: build
    runs-on: ubuntu-latest
    environment: production

    steps:
    - name: Checkout
      uses: actions/checkout@v3

    - name: Setup kubectl
      uses: azure/setup-kubectl@v3

    - name: Configure kubectl
      run: |
        echo "${{ secrets.KUBE_CONFIG_PROD }}" | base64 -d > kubeconfig
        export KUBECONFIG=kubeconfig

    - name: Deploy tagged release to production
      run: |
        export VERSION=${GITHUB_REF#refs/tags/}
        kubectl set image deployment/migration-validator-app \
          app=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${VERSION} \
          -n migration-validator-prod
        kubectl rollout status deployment/migration-validator-app \
          -n migration-validator-prod --timeout=600s
```

## Operations & Maintenance

### **Health Monitoring**
```bash
# scripts/health-check.sh
#!/bin/bash

NAMESPACE="migration-validator-prod"
HEALTH_ENDPOINT="https://api.migration-validator.com/health"

# Check API health
response=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_ENDPOINT)
if [ $response != "200" ]; then
    echo "API health check failed: $response"
    exit 1
fi

# Check pod status
unhealthy_pods=$(kubectl get pods -n $NAMESPACE --field-selector=status.phase!=Running -o name)
if [ ! -z "$unhealthy_pods" ]; then
    echo "Unhealthy pods detected: $unhealthy_pods"
    exit 1
fi

# Check database connectivity
db_status=$(kubectl exec -n $NAMESPACE postgres-cluster-1 -- pg_isready -U migration_user)
if [ $? != 0 ]; then
    echo "Database connectivity failed"
    exit 1
fi

echo "All health checks passed"
```

### **Log Aggregation**
```bash
# scripts/collect-logs.sh
#!/bin/bash

NAMESPACE="migration-validator-prod"
LOG_DIR="/var/log/migration-validator"
DATE=$(date +%Y%m%d)

mkdir -p $LOG_DIR

# Collect application logs
kubectl logs -n $NAMESPACE -l app=migration-validator-app --since=24h > \
  "$LOG_DIR/app-logs-$DATE.log"

# Collect worker logs
kubectl logs -n $NAMESPACE -l app=migration-validator-worker --since=24h > \
  "$LOG_DIR/worker-logs-$DATE.log"

# Collect system events
kubectl get events -n $NAMESPACE --sort-by='.firstTimestamp' > \
  "$LOG_DIR/events-$DATE.log"

# Compress and upload logs
tar czf "$LOG_DIR/logs-$DATE.tar.gz" -C $LOG_DIR *.log
aws s3 cp "$LOG_DIR/logs-$DATE.tar.gz" "s3://migration-validator-logs/"

# Cleanup local logs older than 7 days
find $LOG_DIR -name "*.log" -mtime +7 -delete
find $LOG_DIR -name "*.tar.gz" -mtime +7 -delete
```

## Troubleshooting Guide

### **Common Issues**

#### **1. Pod Startup Issues**
```bash
# Check pod status
kubectl get pods -n migration-validator-prod

# Describe pod for events
kubectl describe pod <pod-name> -n migration-validator-prod

# Check logs
kubectl logs <pod-name> -n migration-validator-prod --previous

# Check resource constraints
kubectl top pods -n migration-validator-prod
```

#### **2. Database Connection Issues**
```bash
# Check database pod status
kubectl get pods -l app=postgres -n migration-validator-prod

# Test database connectivity
kubectl exec -it postgres-cluster-1 -n migration-validator-prod -- \
  psql -U migration_user -d migration_validator -c "SELECT version();"

# Check database logs
kubectl logs postgres-cluster-1 -n migration-validator-prod
```

#### **3. LLM API Issues**
```bash
# Check API key configuration
kubectl get secret migration-validator-secrets -o yaml

# Test LLM connectivity from pod
kubectl exec -it <app-pod> -n migration-validator-prod -- \
  python -c "from src.services.llm_service import LLMService; print('LLM test')"

# Monitor LLM metrics
curl https://api.migration-validator.com/metrics | grep llm_requests
```

This comprehensive deployment guide provides step-by-step instructions for deploying the AI-Powered Migration Validation System across different environments with proper monitoring, security, and operational procedures.