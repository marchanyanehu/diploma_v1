# Deploying to Google Cloud Platform

This guide walks you through deploying the Intelligent Web Data Aggregator to GCP using Compute Engine.

## Cost Estimate (within $300 free credits)

| Resource | Monthly Cost |
|----------|-------------|
| e2-medium VM (2 vCPU, 4GB RAM) | ~$25 |
| 30GB SSD disk | ~$5 |
| Static IP | ~$3 |
| **Total** | **~$33/month** |

Your $300 credits = ~9 months of hosting!

---

## Step 1: Initial GCP Setup

### 1.1 Create a Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click **Select a project** → **New Project**
3. Name it `diploma-project` (or similar)
4. Note your **Project ID** (you'll need this)

### 1.2 Enable Required APIs

Run in Cloud Shell (click the terminal icon `>_` in GCP console):

```bash
gcloud services enable compute.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

---

## Step 2: Create the VM

### 2.1 Create Compute Engine Instance

```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Create the VM
gcloud compute instances create diploma-backend \
  --zone=europe-west1-b \
  --machine-type=e2-medium \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB \
  --tags=http-server,https-server

# Create firewall rules (port 80 for frontend+API)
gcloud compute firewall-rules create allow-http \
  --allow tcp:80,tcp:443 \
  --target-tags=http-server,https-server
```

### 2.2 Reserve a Static IP (optional but recommended)

```bash
# Reserve static IP
gcloud compute addresses create diploma-ip --region=europe-west1

# Get the IP address
gcloud compute addresses describe diploma-ip --region=europe-west1 --format="get(address)"

# Attach to VM
gcloud compute instances delete-access-config diploma-backend \
  --zone=europe-west1-b --access-config-name="External NAT"

gcloud compute instances add-access-config diploma-backend \
  --zone=europe-west1-b --address=YOUR_STATIC_IP
```

---

## Step 3: Setup the VM

### 3.1 SSH into the VM

```bash
gcloud compute ssh diploma-backend --zone=europe-west1-b
```

### 3.2 Install Docker & Docker Compose

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for docker group to take effect
exit
```

### 3.3 Clone Your Repository

```bash
gcloud compute ssh diploma-backend --zone=europe-west1-b

# Clone repo
git clone https://github.com/marchanyanehu/diploma_v1.git diploma
cd diploma

# Create .env file
cp .env.example .env
nano .env  # Edit with your API keys
```

### 3.4 Start the Application

```bash
cd ~/diploma
docker-compose up -d --build

# Check status
docker-compose ps
docker-compose logs -f frontend
```

---

## Step 4: Access Your Application

Both frontend and API are now served on **port 80**:

| URL | Description |
|-----|-------------|
| `http://YOUR_GCP_IP/` | Frontend application |
| `http://YOUR_GCP_IP/docs` | Swagger API documentation |
| `http://YOUR_GCP_IP/api/v1/...` | API endpoints |

Get your external IP:
```bash
gcloud compute instances describe diploma-backend --zone=europe-west1-b --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

---


## Step 5: Setup HTTPS (Optional but Recommended)

### Option A: Use Cloudflare (Free)

1. Get a free domain or use Cloudflare for an existing one
2. Point your domain to your GCP IP
3. Enable Cloudflare proxy for automatic HTTPS

### Option B: Let's Encrypt with Nginx

```bash
# Install Nginx and Certbot
sudo apt install nginx certbot python3-certbot-nginx -y

# Setup Nginx reverse proxy
sudo nano /etc/nginx/sites-available/diploma
```

Add:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Enable and get SSL
sudo ln -s /etc/nginx/sites-available/diploma /etc/nginx/sites-enabled/
sudo certbot --nginx -d your-domain.com
sudo systemctl restart nginx
```

---

## Useful Commands

```bash
# SSH into VM
gcloud compute ssh diploma-backend --zone=europe-west1-b

# View logs
cd ~/diploma && docker-compose logs -f

# Restart services
docker-compose restart

# Update and redeploy
git pull && docker-compose up -d --build

# Check resource usage
docker stats

# Stop everything
docker-compose down
```

---

## Troubleshooting

### VM runs out of memory
```bash
# Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Can't connect to API
1. Check firewall rules: `gcloud compute firewall-rules list`
2. Check if containers are running: `docker-compose ps`
3. Check logs: `docker-compose logs api`

### Database connection issues
Make sure PostgreSQL container is healthy:
```bash
docker-compose logs postgres
docker-compose exec postgres pg_isready
```
