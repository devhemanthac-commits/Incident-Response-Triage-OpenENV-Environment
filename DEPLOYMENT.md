# Deployment Guide

Deploy **Incident Response Triage** to production: **Hugging Face Spaces**, **Docker**, or **Kubernetes**.

## Option 1: Hugging Face Spaces (Easiest for Hackathons)

### Prerequisites
- Hugging Face account ([create one](https://huggingface.co/join))
- Git installed

### Step 1: Create a Space
Go to [huggingface.co/new-space](https://huggingface.co/new-space):
- **Name**: `incident-response-triage`
- **SDK**: Docker
- **Visibility**: Public

### Step 2: Clone & Push
```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/incident-response-triage
cd incident-response-triage

# Copy all files from GitHub repo
cp -r ../Incident-Response-Triage-OpenENV-Environment/* .

# Push to HF Spaces
git add .
git commit -m "Deploy v2.1.0"
git push
```

**Done!** Your Space URL: `https://huggingface.co/spaces/YOUR_USERNAME/incident-response-triage`

## Option 2: Docker (Local or Cloud VPS)

### Local
```bash
docker build -t incident-triage .
docker run -p 5000:5000 incident-triage
curl http://localhost:5000/health
```

### Docker Hub
```bash
docker tag incident-triage YOUR_USERNAME/incident-triage
docker push YOUR_USERNAME/incident-triage
```

### Cloud VPS (AWS, DigitalOcean, etc.)
```bash
ssh user@your-vps
curl -fsSL https://get.docker.com | sh
sudo docker run -d -p 80:5000 YOUR_USERNAME/incident-triage
```

### Docker Compose
```bash
docker-compose up -d
curl http://localhost:5000/health
```

## Option 3: Kubernetes (Enterprise)

```bash
docker push your-registry/incident-triage:v2.1.0

kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: incident-triage
spec:
  replicas: 3
  selector:
    matchLabels:
      app: incident-triage
  template:
    metadata:
      labels:
        app: incident-triage
    spec:
      containers:
      - name: incident-triage
        image: your-registry/incident-triage:v2.1.0
        ports:
        - containerPort: 5000
---
apiVersion: v1
kind: Service
metadata:
  name: incident-triage
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 5000
  selector:
    app: incident-triage
