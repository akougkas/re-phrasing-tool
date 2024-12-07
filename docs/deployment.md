# Text Humanizer Deployment Guide

This guide provides detailed instructions for deploying the Text Humanizer application in various environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Production Deployment](#production-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Cloud Deployment](#cloud-deployment)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)

## Prerequisites

### System Requirements

- Python 3.11 or higher
- pip (Python package manager)
- Git
- Docker (optional)
- nginx (for production)
- SSL certificate (for production)

### Dependencies

All Python dependencies are listed in `requirements.txt`. Key dependencies include:

- Flask: Web framework
- ChromaDB: Vector storage
- Flask-WTF: CSRF protection
- Flask-Caching: Response caching
- Flask-Compress: Response compression

## Local Development

1. **Clone Repository**
   ```bash
   git clone https://github.com/yourusername/re-phrasing-tool.git
   cd re-phrasing-tool
   ```

2. **Set Up Environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Application**
   ```bash
   cp text_humanizer/config/config.example.json text_humanizer/config/config.development.json
   # Edit config.development.json as needed
   ```

4. **Run Development Server**
   ```bash
   export APP_ENV=development
   python -m text_humanizer.main
   ```

## Production Deployment

### 1. Server Setup

1. **Update System**
   ```bash
   sudo apt update
   sudo apt upgrade
   ```

2. **Install Dependencies**
   ```bash
   sudo apt install python3.11 python3.11-venv nginx certbot python3-certbot-nginx
   ```

3. **Create Application User**
   ```bash
   sudo useradd -m -s /bin/bash texthumanizer
   sudo su - texthumanizer
   ```

### 2. Application Setup

1. **Clone and Configure**
   ```bash
   git clone https://github.com/yourusername/re-phrasing-tool.git
   cd re-phrasing-tool
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Production Configuration**
   ```bash
   cp text_humanizer/config/config.example.json text_humanizer/config/config.production.json
   # Edit config.production.json
   ```

### 3. Gunicorn Setup

1. **Install Gunicorn**
   ```bash
   pip install gunicorn
   ```

2. **Create Systemd Service**
   ```bash
   sudo nano /etc/systemd/system/texthumanizer.service
   ```
   
   Content:
   ```ini
   [Unit]
   Description=Text Humanizer Gunicorn Service
   After=network.target
   
   [Service]
   User=texthumanizer
   Group=www-data
   WorkingDirectory=/home/texthumanizer/re-phrasing-tool
   Environment="PATH=/home/texthumanizer/re-phrasing-tool/.venv/bin"
   Environment="APP_ENV=production"
   ExecStart=/home/texthumanizer/re-phrasing-tool/.venv/bin/gunicorn \
             --workers 4 \
             --bind unix:texthumanizer.sock \
             --log-level info \
             text_humanizer.main:app
   
   [Install]
   WantedBy=multi-user.target
   ```

3. **Start Service**
   ```bash
   sudo systemctl start texthumanizer
   sudo systemctl enable texthumanizer
   ```

### 4. Nginx Configuration

1. **Create Nginx Config**
   ```bash
   sudo nano /etc/nginx/sites-available/texthumanizer
   ```
   
   Content:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
   
       location / {
           include proxy_params;
           proxy_pass http://unix:/home/texthumanizer/re-phrasing-tool/texthumanizer.sock;
       }
   }
   ```

2. **Enable Site and SSL**
   ```bash
   sudo ln -s /etc/nginx/sites-available/texthumanizer /etc/nginx/sites-enabled
   sudo certbot --nginx -d your-domain.com
   sudo nginx -t
   sudo systemctl restart nginx
   ```

## Docker Deployment

1. **Build Image**
   ```bash
   docker build -t text-humanizer .
   ```

2. **Run Container**
   ```bash
   docker run -d \
       --name text-humanizer \
       -p 5000:5000 \
       -v config:/app/text_humanizer/config \
       -e APP_ENV=production \
       text-humanizer
   ```

### Docker Compose

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - config:/app/text_humanizer/config
    environment:
      - APP_ENV=production
    restart: unless-stopped

volumes:
  config:
```

Run with:
```bash
docker-compose up -d
```

## Cloud Deployment

### AWS Elastic Beanstalk

1. **Install EB CLI**
   ```bash
   pip install awsebcli
   ```

2. **Initialize EB**
   ```bash
   eb init -p python-3.11 text-humanizer
   ```

3. **Create Environment**
   ```bash
   eb create text-humanizer-prod
   ```

4. **Deploy**
   ```bash
   eb deploy
   ```

### Google Cloud Run

1. **Build Container**
   ```bash
   gcloud builds submit --tag gcr.io/your-project/text-humanizer
   ```

2. **Deploy**
   ```bash
   gcloud run deploy text-humanizer \
       --image gcr.io/your-project/text-humanizer \
       --platform managed
   ```

## Monitoring and Maintenance

### 1. Logging

Configure logging in `config.production.json`:
```json
{
    "log_level": "INFO",
    "log_file": "/var/log/texthumanizer/app.log"
}
```

### 2. Monitoring

1. **System Metrics**
   - CPU usage
   - Memory usage
   - Disk space
   - Network traffic

2. **Application Metrics**
   - Request rate
   - Response time
   - Error rate
   - Cache hit ratio

### 3. Backup

1. **Database Backup**
   ```bash
   # Backup ChromaDB
   tar -czf backup.tar.gz text_humanizer/data/chroma_db
   ```

2. **Configuration Backup**
   ```bash
   # Backup configs
   cp -r text_humanizer/config /backup/config
   ```

### 4. Updates

1. **Code Updates**
   ```bash
   git pull origin main
   source .venv/bin/activate
   pip install -r requirements.txt
   sudo systemctl restart texthumanizer
   ```

2. **Dependencies**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

### 5. Security

1. **SSL Certificate Renewal**
   ```bash
   sudo certbot renew
   ```

2. **Firewall Configuration**
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

## Troubleshooting

### Common Issues

1. **Application Won't Start**
   - Check logs: `sudo journalctl -u texthumanizer`
   - Verify permissions
   - Check configuration

2. **Performance Issues**
   - Monitor resource usage
   - Check cache settings
   - Optimize database queries

3. **SSL Problems**
   - Verify certificate renewal
   - Check nginx configuration
   - Validate domain settings

## Support

For deployment support:

1. Check documentation
2. Review logs
3. Open GitHub issue
4. Contact support team
