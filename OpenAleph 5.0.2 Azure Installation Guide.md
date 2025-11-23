# OpenAleph 5.0.2 Installation Guide
## Complete Deployment on Ubuntu 22.04 LTS (Azure)

**Document Version:** 1.0  
**Date:** November 23, 2025  
**Author:** LucroTech Business Solutions  
**Platform:** Ubuntu 22.04 LTS on Azure

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Azure VM Setup](#azure-vm-setup)
3. [Initial System Configuration](#initial-system-configuration)
4. [Docker Installation](#docker-installation)
5. [OpenAleph Repository Setup](#openaleph-repository-setup)
6. [Configuration Files](#configuration-files)
7. [Elasticsearch Custom Build](#elasticsearch-custom-build)
8. [Service Deployment](#service-deployment)
9. [Database Initialization](#database-initialization)
10. [NGINX and SSL Setup](#nginx-and-ssl-setup)
11. [User Management](#user-management)
12. [Verification and Testing](#verification-and-testing)
13. [Troubleshooting](#troubleshooting)
14. [Maintenance](#maintenance)

---

## Prerequisites

### Required Information
- Domain name (e.g., aleph.lucrotech.co.za)
- DNS access to update A records
- Email address for Let's Encrypt notifications
- Admin user details (name, email, password)

### Azure Requirements
- Active Azure subscription
- Permissions to create Virtual Machines
- Permissions to configure Network Security Groups

---

## Azure VM Setup

### VM Specifications

**Minimum Requirements:**
- **VM Size:** Standard B4ms (4 vCPUs, 16GB RAM)
- **OS:** Ubuntu 22.04 LTS Server
- **Disk:** 128GB Premium SSD (minimum 64GB)
- **Region:** Your preferred region

**Network Security Group Rules:**
```
Priority  Name         Port   Protocol  Source      Destination  Action
100       SSH          22     TCP       Your-IP     Any          Allow
110       HTTP         80     TCP       Any         Any          Allow
120       HTTPS        443    TCP       Any         Any          Allow
```

### DNS Configuration

1. Create an A record pointing your domain to the VM's public IP address:
   ```
   Type: A
   Name: aleph (or your subdomain)
   Value: <VM-Public-IP>
   TTL: 300
   ```

2. Verify DNS propagation:
   ```bash
   nslookup aleph.lucrotech.co.za
   ```

---

## Initial System Configuration

### 1. Connect to VM

```bash
ssh azureuser@<VM-Public-IP>
```

### 2. Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### 3. Install Prerequisites

```bash
sudo apt install -y git curl wget apt-transport-https ca-certificates software-properties-common
```

### 4. Configure System Settings for Elasticsearch

```bash
# Set virtual memory map count (required for Elasticsearch)
sudo sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf

# Add swap space (4GB)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verify settings
sysctl vm.max_map_count
free -h
```

---

## Docker Installation

### 1. Add Docker Repository

```bash
# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up the Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

### 2. Install Docker

```bash
# Update package index
sudo apt update

# Install Docker Engine
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add your user to docker group
sudo usermod -aG docker $USER

# Apply group changes
newgrp docker

# Verify installation
docker --version
docker compose version
```

**Expected Output:**
```
Docker version 29.0.2 or later
Docker Compose version v2.40.3 or later
```

---

## OpenAleph Repository Setup

### 1. Clone Repository

```bash
cd ~
git clone https://github.com/openaleph/openaleph.git
cd openaleph
```

### 2. Install Make

```bash
sudo apt install -y make
make --version
```

---

## Configuration Files

### 1. Environment Configuration (aleph.env)

```bash
# Copy template
cp aleph.env.tmpl aleph.env

# Generate secret key
openssl rand -hex 24
```

Edit `aleph.env`:

```bash
nano aleph.env
```

**Critical Settings:**

```bash
# Secret key (use the one generated above)
ALEPH_SECRET_KEY=<your-generated-secret-key>

# Domain configuration
ALEPH_UI_URL=https://aleph.lucrotech.co.za

# Elasticsearch configuration (BOTH variables are required)
ALEPH_ELASTICSEARCH_URI=http://elasticsearch:9200
OPENALEPH_ELASTICSEARCH_URI=http://elasticsearch:9200

# Single user mode (optional - simplifies initial setup)
ALEPH_SINGLE_USER=true

# Elasticsearch memory settings
ES_JAVA_OPTS=-Xms512m -Xmx512m
```

Save and exit (Ctrl+X, Y, Enter).

### 2. Docker Compose Configuration (docker-compose.yml)

**Critical Fix #1: PostgreSQL Version**

Find the postgres section and ensure it uses version 12:

```yaml
  postgres:
    image: postgres:12.0
    volumes:
      - postgres-data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: aleph
      POSTGRES_PASSWORD: aleph
      POSTGRES_DATABASE: aleph
```

**Critical Fix #2: Ingest Service Image**

Find the ingest section and change to `latest` tag:

```yaml
  ingest:
    image: ghcr.io/openaleph/ingest-file:latest
    tmpfs:
      - /tmp:mode=777
    volumes:
      - archive-data:/data
    depends_on:
      - postgres
      - redis
    restart: on-failure
    env_file:
      - aleph.env
```

**Critical Fix #3: API Port Exposure**

Find the api section and add port mapping:

```yaml
  api:
    image: ghcr.io/openaleph/openaleph:${ALEPH_TAG:-5.0.2}
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - elasticsearch
      - redis
```

**Critical Fix #4: ALEPH_TAG Variable**

Search for all occurrences of malformed `${ALEPH_TAG:-ALEPH_TAG:-5.0.2}` and fix to `${ALEPH_TAG:-5.0.2}`:

```bash
sed -i 's/\${ALEPH_TAG:-ALEPH_TAG:-5\.0\.2}/\${ALEPH_TAG:-5.0.2}/g' docker-compose.yml
```

**Critical Fix #5: Elasticsearch (Temporary - will be replaced)**

For now, comment out or remove the elasticsearch section - we'll add it back after creating the custom Dockerfile.

---

## Elasticsearch Custom Build

### 1. Create Custom Dockerfile

Elasticsearch 9.0 requires the ICU analysis plugin for OpenAleph to work properly.

```bash
nano Dockerfile.elasticsearch
```

Add this content:

```dockerfile
FROM docker.elastic.co/elasticsearch/elasticsearch:9.0.0
RUN bin/elasticsearch-plugin install --batch analysis-icu
```

Save and exit (Ctrl+X, Y, Enter).

### 2. Update docker-compose.yml for Elasticsearch

Edit `docker-compose.yml` and add/replace the elasticsearch section:

```yaml
  elasticsearch:
    build:
      context: .
      dockerfile: Dockerfile.elasticsearch
    hostname: elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - xpack.security.http.ssl.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
```

**Important:** Ensure proper indentation - `elasticsearch:` should be at the same level as `postgres:` and `api:`.

---

## Service Deployment

### 1. Build Docker Images

```bash
# This will take 10-20 minutes on first run
make build
```

Expected output:
```
openaleph-ui built
openaleph-api built
openaleph-app built
openaleph-procrastinate-worker built
```

### 2. Start Services

```bash
# Start all services
docker compose up -d --build

# Wait for services to initialize (90 seconds)
sleep 90

# Verify all services are running
docker compose ps
```

**Expected Status:** All services should show "Up" status.

**Common Issue:** If postgres shows "Exited", check for data directory version mismatch:

```bash
# Check logs
docker compose logs postgres --tail=20

# If version mismatch, remove volume and restart
docker compose down
docker volume rm openaleph_postgres-data
docker compose up -d
sleep 60
```

### 3. Verify Elasticsearch

```bash
# Check Elasticsearch version
docker compose exec elasticsearch curl http://localhost:9200

# Should return version 9.0.0
```

### 4. Upgrade Elasticsearch Client in API

The API container needs the Elasticsearch 9.x client:

```bash
# Install correct client version
docker compose exec api pip install --break-system-packages 'elasticsearch>=9,<10'

# Verify version
docker compose exec api pip list | grep elasticsearch

# Restart API to apply changes
docker compose restart api
sleep 15
```

---

## Database Initialization

### 1. Run Database Migrations

```bash
# Run upgrade to create database schema
docker compose run --rm shell aleph upgrade
```

**Expected:** Should complete without errors.

### 2. Create Elasticsearch Indices

```bash
# Create all required indices
docker compose run --rm shell aleph resetindex
```

**Expected:** Should complete successfully after a few minutes.

### 3. Verify Indices

```bash
# List created indices
docker compose exec api curl http://elasticsearch:9200/_cat/indices
```

**Expected Output:**
```
green open openaleph-collection-v1
green open openaleph-entity-intervals-v1
green open openaleph-xref-v1
green open openaleph-notifications-v1
green open openaleph-entity-documents-v1
green open openaleph-entity-things-v1
green open openaleph-entity-pages-v1
```

---

## NGINX and SSL Setup

### 1. Install NGINX and Certbot

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

### 2. Create NGINX Configuration

```bash
sudo nano /etc/nginx/sites-available/openaleph
```

Add this configuration:

```nginx
server {
    server_name aleph.lucrotech.co.za;
    client_max_body_size 100M;

    # Proxy API requests
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_read_timeout 90;
    }

    # Proxy UI requests
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    listen 80;
}
```

Save and exit (Ctrl+X, Y, Enter).

### 3. Enable Site

```bash
# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Enable OpenAleph site
sudo ln -s /etc/nginx/sites-available/openaleph /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart NGINX
sudo systemctl restart nginx
```

### 4. Obtain SSL Certificate

```bash
sudo certbot --nginx -d aleph.lucrotech.co.za
```

**Prompts:**
1. Enter email address for renewal notifications
2. Agree to Terms of Service (Y)
3. Share email with EFF (your choice - Y or N)

Certbot will automatically:
- Obtain the certificate
- Configure HTTPS in NGINX
- Set up HTTP to HTTPS redirect
- Configure automatic renewal

**Expected Output:**
```
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/aleph.lucrotech.co.za/fullchain.pem
Key is saved at: /etc/letsencrypt/live/aleph.lucrotech.co.za/privkey.pem
```

### 5. Verify HTTPS

```bash
curl -I https://aleph.lucrotech.co.za
```

Should return `HTTP/1.1 200 OK`.

---

## User Management

### Create Admin User

```bash
docker compose run --rm shell aleph createuser \
  --name "Werner" \
  --admin \
  --password "YourSecurePassword" \
  werner@lucrotech.co.za
```

**Expected Output:**
```
User created. ID: X, API Key: <api-key>
```

**Important:** Save the API key for future reference.

---

## Verification and Testing

### 1. Service Health Check

```bash
# Check all services are running
docker compose ps

# All services should show "Up" status
```

### 2. Elasticsearch Health

```bash
# Check cluster health
docker compose exec elasticsearch curl http://localhost:9200/_cluster/health
```

Should return `"status":"green"` or `"status":"yellow"`.

### 3. Web Interface Testing

1. Open browser and navigate to: `https://aleph.lucrotech.co.za`
2. Log in with admin credentials
3. Test the following pages:
   - **Datasets** - Should load without errors
   - **Investigations** - Should allow creating new investigations
   - **Notifications** - Should load without errors
   - **Settings** - Should show user settings

### 4. Create Test Investigation

1. Click "New Investigation"
2. Enter name and description
3. Verify it appears in your investigations list

---

## Troubleshooting

### Common Issues

#### 1. Elasticsearch Not Starting

**Symptoms:** Container exits immediately or shows errors

**Solutions:**

```bash
# Check logs
docker compose logs elasticsearch --tail=50

# If ICU plugin error, rebuild
docker compose down
docker volume rm openaleph_elasticsearch-data
docker compose up -d --build

# If memory issues, increase heap size in docker-compose.yml
ES_JAVA_OPTS=-Xms1g -Xmx1g
```

#### 2. "Internal Server Error" on Datasets Page

**Symptoms:** 500 error when accessing /datasets

**Solutions:**

```bash
# Check if Elasticsearch is accessible
docker compose exec api curl http://elasticsearch:9200

# Check API logs
docker compose logs api --tail=50

# Verify Elasticsearch client version
docker compose exec api pip list | grep elasticsearch

# Should be 9.x.x - if not, reinstall
docker compose exec api pip install --break-system-packages 'elasticsearch>=9,<10'
docker compose restart api
```

#### 3. No Indices Created

**Symptoms:** `curl http://elasticsearch:9200/_cat/indices` returns nothing

**Solutions:**

```bash
# Check Elasticsearch logs
docker compose logs elasticsearch --tail=30

# Run resetindex again
docker compose run --rm shell aleph resetindex

# Check for ICU tokenizer errors - if present, rebuild Elasticsearch
```

#### 4. PostgreSQL Version Mismatch

**Symptoms:** "database files are incompatible with server"

**Solutions:**

```bash
docker compose down
docker volume rm openaleph_postgres-data
docker compose up -d
sleep 60
docker compose run --rm shell aleph upgrade
```

#### 5. Website Loads Indefinitely

**Symptoms:** Browser shows loading spinner forever

**Solutions:**

```bash
# Check if API port is published
docker compose ps api
# Should show: 0.0.0.0:8000->8000/tcp

# If not, edit docker-compose.yml and add under api:
ports:
  - "8000:8000"

# Restart
docker compose up -d api
```

#### 6. SSL Certificate Issues

**Symptoms:** Certificate errors or HTTP instead of HTTPS

**Solutions:**

```bash
# Verify certificate
sudo certbot certificates

# Renew if needed
sudo certbot renew --dry-run

# Check NGINX configuration
sudo nginx -t

# Reload NGINX
sudo systemctl reload nginx
```

### Log Files

```bash
# View all logs
docker compose logs

# View specific service logs
docker compose logs api --tail=100
docker compose logs elasticsearch --tail=100
docker compose logs worker --tail=100

# Follow logs in real-time
docker compose logs -f api
```

---

## Maintenance

### Daily Operations

#### Start Services

```bash
cd ~/openaleph
docker compose up -d
```

#### Stop Services

```bash
cd ~/openaleph
docker compose down
```

#### Restart Services

```bash
cd ~/openaleph
docker compose restart
```

#### View Service Status

```bash
docker compose ps
```

### Backup Procedures

#### 1. Database Backup

```bash
# Create backup directory
mkdir -p ~/backups

# Backup PostgreSQL database
docker compose exec -T postgres pg_dump -U aleph aleph | gzip > ~/backups/aleph-db-$(date +%Y%m%d-%H%M%S).sql.gz
```

#### 2. Elasticsearch Backup

```bash
# Backup Elasticsearch data
docker compose exec -T elasticsearch curl -X PUT "localhost:9200/_snapshot/backup" -H 'Content-Type: application/json' -d'
{
  "type": "fs",
  "settings": {
    "location": "/usr/share/elasticsearch/snapshots"
  }
}'

# Create snapshot
docker compose exec -T elasticsearch curl -X PUT "localhost:9200/_snapshot/backup/snapshot_$(date +%Y%m%d)"
```

#### 3. Volume Backup

```bash
# Stop services
docker compose down

# Backup volumes
sudo tar czf ~/backups/aleph-volumes-$(date +%Y%m%d-%H%M%S).tar.gz \
  /var/lib/docker/volumes/openaleph_postgres-data \
  /var/lib/docker/volumes/openaleph_elasticsearch-data \
  /var/lib/docker/volumes/openaleph_archive-data

# Restart services
docker compose up -d
```

#### 4. Configuration Backup

```bash
cd ~/openaleph
tar czf ~/backups/aleph-config-$(date +%Y%m%d-%H%M%S).tar.gz \
  aleph.env \
  docker-compose.yml \
  Dockerfile.elasticsearch
```

### Restore Procedures

#### Restore Database

```bash
# Stop services
docker compose down

# Remove old data
docker volume rm openaleph_postgres-data

# Start only postgres
docker compose up -d postgres
sleep 30

# Restore backup
gunzip < ~/backups/aleph-db-YYYYMMDD-HHMMSS.sql.gz | \
  docker compose exec -T postgres psql -U aleph aleph

# Start all services
docker compose up -d
```

### Updates

#### Update OpenAleph

```bash
cd ~/openaleph

# Pull latest code
git pull origin main

# Rebuild images
make build

# Stop services
docker compose down

# Start with new images
docker compose up -d

# Run migrations
docker compose run --rm shell aleph upgrade
```

#### Update SSL Certificate

Certificates auto-renew, but you can manually renew:

```bash
sudo certbot renew
sudo systemctl reload nginx
```

### Monitoring

#### Check Disk Space

```bash
df -h
```

Elasticsearch data can grow large - monitor `/var/lib/docker/volumes`.

#### Check Memory Usage

```bash
free -h
docker stats
```

#### Check Service Health

```bash
# Overall service status
docker compose ps

# Elasticsearch cluster health
docker compose exec api curl http://elasticsearch:9200/_cluster/health

# Database connection test
docker compose exec postgres pg_isready -U aleph
```

### Security Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Docker images
cd ~/openaleph
docker compose pull
docker compose up -d
```

---

## System Requirements Summary

### Minimum Specifications
- **CPU:** 4 cores
- **RAM:** 16GB
- **Disk:** 128GB SSD
- **OS:** Ubuntu 22.04 LTS
- **Network:** Ports 80, 443, 22 open

### Software Versions
- **Docker:** 29.0.2+
- **Docker Compose:** 2.40.3+
- **PostgreSQL:** 12.0
- **Elasticsearch:** 9.0.0 with ICU plugin
- **Python Elasticsearch Client:** 9.1.0
- **OpenAleph:** 5.0.2
- **NGINX:** 1.18.0+

---

## Critical Configuration Points

### Must Be Configured Correctly

1. **Both Elasticsearch URI variables** in aleph.env:
   - `ALEPH_ELASTICSEARCH_URI=http://elasticsearch:9200`
   - `OPENALEPH_ELASTICSEARCH_URI=http://elasticsearch:9200`

2. **PostgreSQL version** must be 12.x (not 10.x or 17.x)

3. **Elasticsearch** must be version 9.0.0 with ICU plugin installed

4. **Elasticsearch Python client** must be 9.x.x in API container

5. **API port** must be published to host (`ports: - "8000:8000"`)

6. **System settings:**
   - `vm.max_map_count=262144`
   - Adequate swap space (4GB minimum)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Internet (HTTPS)                      │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              NGINX Reverse Proxy (SSL)                   │
│                  Port 443 → 80/8080                      │
└────────────────────┬─────────────────┬──────────────────┘
                     │                 │
         ┌───────────▼──────┐   ┌─────▼──────────┐
         │   UI Container   │   │  API Container │
         │   Port: 8080     │   │   Port: 8000   │
         └──────────────────┘   └─────┬──────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
         ┌──────────▼────────┐ ┌─────▼───────┐ ┌──────▼─────────┐
         │ PostgreSQL 12     │ │ Elasticsearch│ │ Redis          │
         │ (Database)        │ │ 9.0 + ICU    │ │ (Cache/Queue)  │
         └───────────────────┘ └──────────────┘ └────────────────┘
                    │                 │
         ┌──────────▼────────┐ ┌─────▼──────────┐
         │ Worker Container  │ │ Ingest Container│
         │ (Background Jobs) │ │ (File Processing)│
         └───────────────────┘ └─────────────────┘
```

---

## Support and Resources

### Official Documentation
- **OpenAleph Docs:** https://openaleph.org/docs/
- **GitHub Repository:** https://github.com/openaleph/openaleph
- **Community:** https://darc.social

### Docker Documentation
- **Docker Docs:** https://docs.docker.com/
- **Docker Compose:** https://docs.docker.com/compose/

### Elasticsearch Documentation
- **Elasticsearch 9.0:** https://www.elastic.co/guide/en/elasticsearch/reference/9.0/index.html
- **ICU Analysis Plugin:** https://www.elastic.co/guide/en/elasticsearch/plugins/9.0/analysis-icu.html

---

## Appendix A: Complete aleph.env Template

```bash
# Secret key - REQUIRED - Generate with: openssl rand -hex 24
ALEPH_SECRET_KEY=your-generated-secret-key-here

# Domain configuration
ALEPH_UI_URL=https://aleph.lucrotech.co.za

# Elasticsearch URIs - BOTH required
ALEPH_ELASTICSEARCH_URI=http://elasticsearch:9200
OPENALEPH_ELASTICSEARCH_URI=http://elasticsearch:9200

# Single user mode (optional)
ALEPH_SINGLE_USER=true

# Elasticsearch Java options
ES_JAVA_OPTS=-Xms512m -Xmx512m

# PostgreSQL (default values work with docker-compose.yml)
POSTGRES_USER=aleph
POSTGRES_PASSWORD=aleph
POSTGRES_DATABASE=aleph

# Redis (default values work with docker-compose.yml)
REDIS_URL=redis://redis:6379/0

# Optional: Email configuration for notifications
# ALEPH_MAIL_FROM=noreply@lucrotech.co.za
# ALEPH_MAIL_HOST=smtp.gmail.com
# ALEPH_MAIL_USERNAME=your-email@gmail.com
# ALEPH_MAIL_PASSWORD=your-app-password
# ALEPH_MAIL_PORT=587
# ALEPH_MAIL_USE_TLS=true
```

---

## Appendix B: Quick Reference Commands

### Service Management
```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart all services
docker compose restart

# View service status
docker compose ps

# View logs
docker compose logs -f api
```

### Database Operations
```bash
# Run migrations
docker compose run --rm shell aleph upgrade

# Create indices
docker compose run --rm shell aleph resetindex

# Create user
docker compose run --rm shell aleph createuser --name "Name" --admin --password "pass" email@domain.com

# Database backup
docker compose exec -T postgres pg_dump -U aleph aleph > backup.sql
```

### Elasticsearch Operations
```bash
# Check cluster health
docker compose exec api curl http://elasticsearch:9200/_cluster/health

# List indices
docker compose exec api curl http://elasticsearch:9200/_cat/indices

# Check Elasticsearch version
docker compose exec elasticsearch curl http://localhost:9200
```

### System Maintenance
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Renew SSL certificate
sudo certbot renew

# Clean Docker resources
docker system prune -a
```

---

## Appendix C: Environment Variables Reference

### Core Settings
| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| ALEPH_SECRET_KEY | Yes | Secret key for encryption | Generated via openssl |
| ALEPH_UI_URL | Yes | Public URL | https://aleph.domain.com |
| ALEPH_ELASTICSEARCH_URI | Yes | ES connection (legacy) | http://elasticsearch:9200 |
| OPENALEPH_ELASTICSEARCH_URI | Yes | ES connection (new) | http://elasticsearch:9200 |

### Optional Settings
| Variable | Default | Description |
|----------|---------|-------------|
| ALEPH_SINGLE_USER | false | Simplified auth mode |
| ES_JAVA_OPTS | -Xms2g -Xmx2g | Java heap size |
| POSTGRES_USER | aleph | Database user |
| POSTGRES_PASSWORD | aleph | Database password |
| REDIS_URL | redis://redis:6379/0 | Redis connection |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-23 | Initial documentation based on successful deployment |

---

## License

This documentation is provided as-is for use with OpenAleph deployments. OpenAleph itself is open source software - see the LICENSE file in the OpenAleph repository for details.

---

**End of Document**
