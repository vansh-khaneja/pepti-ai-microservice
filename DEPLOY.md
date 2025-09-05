# Pepti Wiki AI - Deployment Guide for Hostinger

This guide will walk you through deploying the Pepti Wiki AI FastAPI application on Hostinger hosting platform.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Hostinger Setup](#hostinger-setup)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Vector Database Setup](#vector-database-setup)
- [Deployment Methods](#deployment-methods)
- [Production Configuration](#production-configuration)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before deploying, ensure you have:
- Hostinger hosting account with VPS or Cloud hosting plan
- Domain name pointed to your Hostinger server
- SSH access to your server
- Basic knowledge of Linux commands and Python
- Cloud PostgreSQL account (Neon, Supabase, or Hostinger)
- Qdrant Cloud account

## Benefits of Cloud Services

Using cloud-hosted PostgreSQL and Qdrant provides several advantages:

### Cost Efficiency
- **No server resources** needed for database hosting
- **Pay-as-you-scale** pricing models
- **Free tiers** available (Neon offers 3GB free, Qdrant has free tier)
- **Reduced server requirements** (1-2GB RAM instead of 4GB+)

### Reliability & Maintenance
- **Automatic backups** and point-in-time recovery
- **High availability** with built-in redundancy
- **Automatic updates** and security patches
- **24/7 monitoring** and support

### Performance
- **Optimized infrastructure** for database workloads
- **Global CDN** and edge locations
- **Connection pooling** and caching
- **Scalable resources** based on demand

## Hostinger Setup

### 1. Choose Hosting Plan
For this FastAPI application, you'll need:
- **VPS Hosting** (Recommended) - Full control over the server
- **Cloud Hosting** - Managed hosting with Python support
- **Shared Hosting** - Not recommended due to limitations

### 2. Server Requirements
- **OS**: Ubuntu 20.04+ or CentOS 8+
- **RAM**: Minimum 1GB (2GB+ recommended)
- **Storage**: 10GB+ SSD
- **Python**: 3.11+
- **Database**: Cloud PostgreSQL (Neon, Supabase, or Hostinger PostgreSQL)
- **Vector DB**: Qdrant Cloud

### 3. Initial Server Setup
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y python3.11 python3.11-pip python3.11-venv git curl wget

# Install Nginx (for reverse proxy)
sudo apt install -y nginx

# Install system dependencies for Python packages
sudo apt install -y gcc g++ libpq-dev
```

## Environment Configuration

### 1. Create Environment File
Create a `.env` file in your project root:

```bash
# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Database Configuration (Cloud PostgreSQL)
DATABASE_URL=postgresql+asyncpg://username:password@your-cloud-host:5432/pepti_wiki
DATABASE_NAME=pepti_wiki

# Qdrant Configuration (Cloud)
QDRANT_URL=https://your-cluster-id.eu-west-1-0.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=your_qdrant_api_key_here
PEPTIDE_COLLECTION=peptides

# API Keys
OPENAI_API_KEY=your_openai_api_key_here
SERP_API_KEY=your_serp_api_key_here

# CORS Configuration
ALLOWED_HOSTS=["yourdomain.com", "www.yourdomain.com", "localhost"]
```

### 2. Set Environment Variables
```bash
# Make .env file secure
chmod 600 .env

# Source environment variables
source .env
```

## Database Setup

### 1. Cloud PostgreSQL Setup

Choose one of these cloud PostgreSQL providers:

#### Option A: Neon (Recommended - Free tier available)
1. Sign up at [Neon](https://neon.tech/)
2. Create a new project
3. Copy the connection string
4. Update your `.env` file with the connection string

#### Option B: Supabase
1. Sign up at [Supabase](https://supabase.com/)
2. Create a new project
3. Go to Settings > Database
4. Copy the connection string
5. Update your `.env` file

#### Option C: Hostinger PostgreSQL
1. Log into your Hostinger control panel
2. Go to Databases > PostgreSQL
3. Create a new database
4. Note the connection details
5. Update your `.env` file

### 2. Database Migration
```bash
# Install Alembic for database migrations
pip install alembic

# Initialize Alembic (if not already done)
alembic init alembic

# Run migrations
alembic upgrade head
```

## Vector Database Setup

### 1. Qdrant Cloud Setup
1. Sign up at [Qdrant Cloud](https://cloud.qdrant.io/)
2. Create a new cluster
3. Note down your cluster URL and API key
4. Update your `.env` file with the credentials

### 2. Qdrant Cloud Configuration
1. **Create Collection**: Use the Qdrant dashboard to create your `peptides` collection
2. **Set Dimensions**: Configure the vector dimensions based on your embedding model
3. **API Key**: Generate and copy your API key
4. **Update Environment**: Add the Qdrant URL and API key to your `.env` file

**Note**: Self-hosting Qdrant is not recommended for production as it requires significant resources and maintenance.

## Deployment Methods

### Method 1: Direct Python Deployment (Recommended for VPS)

#### 1. Clone and Setup Project
```bash
# Clone your repository
git clone https://github.com/yourusername/pepti-wiki-ai.git
cd pepti-wiki-ai

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Configure Nginx
Create `/etc/nginx/sites-available/pepti-wiki`:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/pepti-wiki /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 3. Create Systemd Service
Create `/etc/systemd/system/pepti-wiki.service`:
```ini
[Unit]
Description=Pepti Wiki AI FastAPI Application
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/pepti-wiki-ai
Environment=PATH=/path/to/your/pepti-wiki-ai/venv/bin
ExecStart=/path/to/your/pepti-wiki-ai/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable pepti-wiki
sudo systemctl start pepti-wiki
sudo systemctl status pepti-wiki
```

### Method 2: Docker Deployment

#### 1. Install Docker
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2. Deploy with Docker Compose
```bash
# Update docker-compose.yml for production
# Set proper environment variables
docker-compose up -d
```

### Method 3: Hostinger Cloud Hosting

If using Hostinger's managed cloud hosting:

1. **Upload Files**: Use File Manager or SFTP to upload your project files
2. **Python Environment**: Hostinger provides Python 3.11+ support
3. **Database**: Use Hostinger's PostgreSQL add-on
4. **Environment Variables**: Set through Hostinger's control panel

## Production Configuration

### 1. SSL Certificate (Let's Encrypt)
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 2. Firewall Configuration
```bash
# Configure UFW
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### 3. Log Management
```bash
# View application logs
sudo journalctl -u pepti-wiki -f

# View Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## Monitoring & Maintenance

### 1. Health Monitoring
- Monitor the `/health` endpoint
- Set up uptime monitoring (UptimeRobot, Pingdom)
- Monitor server resources (CPU, RAM, Disk)

### 2. Log Rotation
Create `/etc/logrotate.d/pepti-wiki`:
```
/var/log/pepti-wiki/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
}
```

### 3. Backup Strategy
```bash
# Cloud database backup (most providers offer automatic backups)
# For manual backups, use your cloud provider's tools:

# Neon: Automatic backups included
# Supabase: Automatic backups + manual snapshots
# Hostinger: Check control panel for backup options

# Application data backup
#!/bin/bash
# Backup application files
tar -czf /backups/app_$(date +%Y%m%d_%H%M%S).tar.gz /path/to/your/pepti-wiki-ai
find /backups -name "app_*.tar.gz" -mtime +7 -delete
```

### 4. Updates and Maintenance
```bash
# Update application
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart pepti-wiki

# Update system packages
sudo apt update && sudo apt upgrade -y
```

## Troubleshooting

### Common Issues

#### 1. Application Won't Start
```bash
# Check service status
sudo systemctl status pepti-wiki

# Check logs
sudo journalctl -u pepti-wiki -n 50

# Test manually
cd /path/to/your/project
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 2. Database Connection Issues
```bash
# Test database connection (replace with your cloud database details)
psql -h your-cloud-host -U your-username -d pepti_wiki

# Test connection from Python
python -c "
import psycopg2
try:
    conn = psycopg2.connect('your_database_url_here')
    print('Database connection successful')
    conn.close()
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

#### 3. Nginx Issues
```bash
# Test Nginx configuration
sudo nginx -t

# Check Nginx status
sudo systemctl status nginx

# Reload Nginx
sudo systemctl reload nginx
```

#### 4. Port Already in Use
```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>
```

### Performance Optimization

#### 1. Gunicorn for Production
```bash
# Install Gunicorn
pip install gunicorn

# Update systemd service
ExecStart=/path/to/your/pepti-wiki-ai/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

#### 2. Redis for Caching
```bash
# Install Redis
sudo apt install -y redis-server

# Configure in your application
# Add Redis caching for frequently accessed data
```

## Security Considerations

1. **Environment Variables**: Never commit `.env` files to version control
2. **Database Security**: 
   - Use strong passwords for cloud databases
   - Enable SSL connections
   - Use connection pooling
   - Restrict IP access if possible
3. **Vector Database Security**:
   - Use API keys with limited permissions
   - Enable HTTPS for Qdrant connections
   - Regular key rotation
4. **Firewall**: Only open necessary ports (80, 443, 22)
5. **SSL**: Always use HTTPS in production
6. **Updates**: Keep all packages and system updated
7. **Monitoring**: Set up proper logging and monitoring
8. **Cloud Security**: 
   - Enable database backups
   - Use VPC/private networks when available
   - Monitor access logs

## Support

For deployment issues:
1. Check the logs first
2. Verify all environment variables are set correctly
3. Ensure all services are running
4. Check firewall and network configuration

## Additional Resources

- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Hostinger Documentation](https://support.hostinger.com/)
- [Nginx Configuration](https://nginx.org/en/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

**Note**: This guide assumes you have root/sudo access to your Hostinger server. For shared hosting, contact Hostinger support for Python application deployment assistance.
