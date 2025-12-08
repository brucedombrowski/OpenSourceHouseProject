
# Production Deployment Guide

**House Project Management System** - Deploy to Production

---

## Recent Changes

- **Dec 8, 2025:** Documentation reviewed and confirmed up-to-date
- **Dec 6, 2025:** Backup and scaling sections expanded

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Requirements](#server-requirements)
3. [Database Setup](#database-setup)
4. [Application Deployment](#application-deployment)
5. [Web Server Configuration](#web-server-configuration)
6. [Security Hardening](#security-hardening)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Backup Strategy](#backup-strategy)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### What You Need

- **Server**: Linux server (Ubuntu 22.04+ or similar)
- **Domain**: Optional but recommended (e.g., `project.yourcompany.com`)
- **SSL Certificate**: Let's Encrypt recommended
- **Database**: PostgreSQL 14+ (production) or SQLite (small deployments)
- **Python**: 3.10 or higher
- **Git**: For code deployment

### Skills Required

- Basic Linux command line
- SSH access management
- Web server configuration (nginx or Apache)
- Basic database administration

---

## Server Requirements

### Minimum Specs

**For small teams (< 10 users, < 500 tasks):**
- 1 CPU core
- 1 GB RAM
- 10 GB disk space
- Ubuntu 22.04 LTS

**For larger deployments (10-50 users, 500-5000 tasks):**
- 2 CPU cores
- 4 GB RAM
- 50 GB disk space
- Ubuntu 22.04 LTS

### Software Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and essential tools
sudo apt install -y python3.10 python3.10-venv python3-pip \
    git nginx postgresql postgresql-contrib \
    build-essential libpq-dev

# Install supervisor (process management)
sudo apt install -y supervisor
```

---

## Database Setup

### Option 1: PostgreSQL (Recommended for Production)

```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql

# In PostgreSQL shell:
CREATE DATABASE house_project;
CREATE USER house_user WITH PASSWORD 'your_secure_password_here';
ALTER ROLE house_user SET client_encoding TO 'utf8';
ALTER ROLE house_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE house_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE house_project TO house_user;
\q
```

### Option 2: SQLite (Small Deployments Only)

For single-user or very small teams, SQLite can work:

```bash
# No special setup needed, file-based
# Database will be db.sqlite3 in project root
# Not recommended for > 5 concurrent users
```

---

## Application Deployment

### 1. Create Application User

```bash
# Create dedicated user (no sudo access)
sudo adduser houseproject --disabled-password --gecos ""
sudo su - houseproject
```

### 2. Clone Repository

```bash
# As houseproject user
cd /home/houseproject
git clone https://github.com/brucedombrowski/OpenSourceHouseProject.git app
cd app
```

### 3. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install production server
pip install gunicorn psycopg2-binary
```

### 4. Configure Environment Variables

```bash
# Create .env file
cat > .env << 'EOF'
# Security
DEBUG=False
SECRET_KEY=your_very_long_random_secret_key_here_min_50_chars

# Database (PostgreSQL)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=house_project
DB_USER=house_user
DB_PASSWORD=your_secure_password_here
DB_HOST=localhost
DB_PORT=5432

# For SQLite instead:
# DB_ENGINE=django.db.backends.sqlite3
# DB_NAME=db.sqlite3

# Allowed hosts (your domain)
ALLOWED_HOSTS=project.yourcompany.com,localhost,127.0.0.1

# Security settings
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True

# Static files
STATIC_ROOT=/home/houseproject/app/staticfiles
STATIC_URL=/static/
EOF

# Set secure permissions
chmod 600 .env
```

**Generate SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Update settings.py for Production

Edit `house_wbs/settings.py`:

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Security
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')

# Database
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DB_NAME', BASE_DIR / 'db.sqlite3'),
        'USER': os.getenv('DB_USER', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', ''),
        'PORT': os.getenv('DB_PORT', ''),
    }
}

# Static files
STATIC_ROOT = os.getenv('STATIC_ROOT', BASE_DIR / 'staticfiles')
STATIC_URL = os.getenv('STATIC_URL', '/static/')

# Security (when HTTPS is enabled)
if not DEBUG:
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True') == 'True'
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True') == 'True'
    CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'True') == 'True'
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
```

### 6. Initialize Database

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Load initial data (optional)
python manage.py import_wbs_csv data/wbs_items_template.csv --update
python manage.py import_dependencies_csv data/wbs_dependencies_template.csv --update
python manage.py rollup_wbs_dates
python manage.py rollup_wbs_progress
```

### 7. Test Application

```bash
# Test with development server
python manage.py runserver 0.0.0.0:8000

# Visit http://your-server-ip:8000
# If it works, proceed to production server setup
```

---

## Web Server Configuration

### Option 1: Nginx + Gunicorn (Recommended)

#### Create Gunicorn systemd service

```bash
# As root
sudo nano /etc/systemd/system/gunicorn.service
```

```ini
[Unit]
Description=Gunicorn daemon for House Project
After=network.target

[Service]
User=houseproject
Group=www-data
WorkingDirectory=/home/houseproject/app
Environment="PATH=/home/houseproject/app/venv/bin"
EnvironmentFile=/home/houseproject/app/.env
ExecStart=/home/houseproject/app/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/home/houseproject/app/gunicorn.sock \
    --timeout 60 \
    --access-logfile /home/houseproject/app/logs/gunicorn-access.log \
    --error-logfile /home/houseproject/app/logs/gunicorn-error.log \
    house_wbs.wsgi:application

[Install]
WantedBy=multi-user.target
```

```bash
# Create logs directory
sudo mkdir -p /home/houseproject/app/logs
sudo chown houseproject:www-data /home/houseproject/app/logs

# Enable and start service
sudo systemctl enable gunicorn
sudo systemctl start gunicorn
sudo systemctl status gunicorn
```

#### Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/houseproject
```

```nginx
upstream houseproject {
    server unix:/home/houseproject/app/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name project.yourcompany.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name project.yourcompany.com;

    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/project.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/project.yourcompany.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 20M;

    # Logging
    access_log /var/log/nginx/houseproject-access.log;
    error_log /var/log/nginx/houseproject-error.log;

    # Static files
    location /static/ {
        alias /home/houseproject/app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files (if you add user uploads later)
    location /media/ {
        alias /home/houseproject/app/media/;
    }

    # Application
    location / {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_pass http://houseproject;

        # Timeouts for long operations
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/houseproject /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

#### Setup SSL with Let's Encrypt

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d project.yourcompany.com

# Test auto-renewal
sudo certbot renew --dry-run
```

### Option 2: Apache + mod_wsgi

```bash
# Install Apache and mod_wsgi
sudo apt install -y apache2 libapache2-mod-wsgi-py3

# Create Apache config
sudo nano /etc/apache2/sites-available/houseproject.conf
```

```apache
<VirtualHost *:80>
    ServerName project.yourcompany.com
    Redirect permanent / https://project.yourcompany.com/
</VirtualHost>

<VirtualHost *:443>
    ServerName project.yourcompany.com

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/project.yourcompany.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/project.yourcompany.com/privkey.pem

    Alias /static /home/houseproject/app/staticfiles
    <Directory /home/houseproject/app/staticfiles>
        Require all granted
    </Directory>

    WSGIDaemonProcess houseproject python-home=/home/houseproject/app/venv python-path=/home/houseproject/app
    WSGIProcessGroup houseproject
    WSGIScriptAlias / /home/houseproject/app/house_wbs/wsgi.py

    <Directory /home/houseproject/app/house_wbs>
        <Files wsgi.py>
            Require all granted
        </Files>
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/houseproject-error.log
    CustomLog ${APACHE_LOG_DIR}/houseproject-access.log combined
</VirtualHost>
```

```bash
# Enable site and SSL
sudo a2enmod ssl wsgi
sudo a2ensite houseproject
sudo systemctl restart apache2
```

---

## Security Hardening

### 1. Firewall Configuration

```bash
# Enable UFW firewall
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'  # or 'Apache Full'
sudo ufw enable
sudo ufw status
```

### 2. Secure Database

```bash
# PostgreSQL: Edit pg_hba.conf to restrict access
sudo nano /etc/postgresql/14/main/pg_hba.conf

# Change from:
# host    all             all             0.0.0.0/0            md5
# To:
# host    house_project   house_user      127.0.0.1/32         md5

sudo systemctl restart postgresql
```

### 3. File Permissions

```bash
# Secure application directory
sudo chown -R houseproject:www-data /home/houseproject/app
sudo chmod -R 750 /home/houseproject/app
sudo chmod 600 /home/houseproject/app/.env

# Static files readable by web server
sudo chmod -R 755 /home/houseproject/app/staticfiles
```

### 4. Application Security Checklist

- ✅ `DEBUG = False` in production
- ✅ Strong `SECRET_KEY` (50+ characters)
- ✅ `ALLOWED_HOSTS` set to specific domains
- ✅ SSL/HTTPS enabled
- ✅ `SECURE_SSL_REDIRECT = True`
- ✅ `SESSION_COOKIE_SECURE = True`
- ✅ `CSRF_COOKIE_SECURE = True`
- ✅ HSTS headers enabled
- ✅ Database credentials in `.env` (not in code)
- ✅ `.env` file permissions 600
- ✅ Regular security updates

### 5. Rate Limiting (Optional)

Install django-ratelimit:

```bash
pip install django-ratelimit
```

Add to views:

```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='100/h', method='GET')
def gantt_chart(request):
    # ... existing code
```

---

## Monitoring & Maintenance

### 1. Log Monitoring

```bash
# Application logs
tail -f /home/houseproject/app/logs/gunicorn-error.log
tail -f /home/houseproject/app/logs/gunicorn-access.log

# Nginx logs
tail -f /var/log/nginx/houseproject-error.log

# System logs
journalctl -u gunicorn -f
```

### 2. Health Check Script

```bash
# Create monitoring script
nano /home/houseproject/app/healthcheck.sh
```

```bash
#!/bin/bash
URL="https://project.yourcompany.com/gantt/"
HTTP_CODE=$(curl -o /dev/null -s -w "%{http_code}" $URL)

if [ "$HTTP_CODE" -eq 200 ]; then
    echo "$(date): Application is healthy (HTTP $HTTP_CODE)"
    exit 0
else
    echo "$(date): Application is down (HTTP $HTTP_CODE)" | tee -a /home/houseproject/app/logs/healthcheck.log
    # Optional: Send alert email
    exit 1
fi
```

```bash
chmod +x /home/houseproject/app/healthcheck.sh

# Add to cron (every 5 minutes)
crontab -e
```

```cron
*/5 * * * * /home/houseproject/app/healthcheck.sh >> /home/houseproject/app/logs/healthcheck.log 2>&1
```

### 3. Restart Application

```bash
# Restart Gunicorn
sudo systemctl restart gunicorn

# Reload Nginx
sudo systemctl reload nginx

# Check status
sudo systemctl status gunicorn
sudo systemctl status nginx
```

### 4. Update Application

```bash
# As houseproject user
cd /home/houseproject/app
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
python manage.py migrate
python manage.py collectstatic --noinput
exit

# As root, restart services
sudo systemctl restart gunicorn
```

---

## Backup Strategy

### 1. Database Backups

#### PostgreSQL

```bash
# Create backup script
nano /home/houseproject/app/backup_db.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/houseproject/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="house_project"

mkdir -p $BACKUP_DIR

# Dump database
pg_dump -U house_user -h localhost $DB_NAME | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete

echo "$(date): Database backup completed: db_$DATE.sql.gz"
```

```bash
chmod +x /home/houseproject/app/backup_db.sh

# Daily backups at 2 AM
crontab -e
```

```cron
0 2 * * * /home/houseproject/app/backup_db.sh >> /home/houseproject/app/logs/backup.log 2>&1
```

### 2. Application Data Backups

```bash
# Full backup using Django command
cd /home/houseproject/app
source venv/bin/activate
python manage.py full_backup backups/$(date +%Y%m%d)/
```

### 3. Restore from Backup

#### PostgreSQL

```bash
# Restore database
gunzip -c /home/houseproject/backups/db_20251206_020000.sql.gz | psql -U house_user -h localhost house_project
```

#### Django JSON backup

```bash
python manage.py loaddata backups/20251206/wbsitem.json
python manage.py loaddata backups/20251206/taskdependency.json
python manage.py loaddata backups/20251206/projectitem.json
```

### 4. Off-site Backups

Use rsync, AWS S3, or similar:

```bash
# Example: rsync to remote server
rsync -avz /home/houseproject/backups/ user@backup-server:/backups/houseproject/
```

---

## Troubleshooting

### Application Won't Start

```bash
# Check Gunicorn status
sudo systemctl status gunicorn

# View logs
sudo journalctl -u gunicorn -n 50

# Check socket exists
ls -la /home/houseproject/app/gunicorn.sock

# Test Django directly
cd /home/houseproject/app
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

### Static Files Not Loading

```bash
# Recollect static files
cd /home/houseproject/app
source venv/bin/activate
python manage.py collectstatic --noinput

# Check permissions
ls -la /home/houseproject/app/staticfiles/

# Fix permissions if needed
sudo chown -R houseproject:www-data /home/houseproject/app/staticfiles
sudo chmod -R 755 /home/houseproject/app/staticfiles
```

### Database Connection Errors

```bash
# Test PostgreSQL connection
psql -U house_user -h localhost -d house_project

# Check PostgreSQL is running
sudo systemctl status postgresql

# View PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

### 502 Bad Gateway (Nginx)

```bash
# Check Gunicorn is running
sudo systemctl status gunicorn

# Check socket permissions
ls -la /home/houseproject/app/gunicorn.sock
# Should be owned by houseproject:www-data

# Check Nginx error log
sudo tail -f /var/log/nginx/houseproject-error.log
```

### Performance Issues

```bash
# Check resource usage
htop

# Check database query performance
# Enable query logging in PostgreSQL:
sudo nano /etc/postgresql/14/main/postgresql.conf
# Set: log_min_duration_statement = 1000  # Log queries > 1s

# Check slow queries
sudo tail -f /var/log/postgresql/postgresql-14-main.log | grep duration
```

---

## Scaling Considerations

### Horizontal Scaling

For larger deployments:

1. **Load Balancer**: Use nginx or HAProxy to distribute requests
2. **Multiple App Servers**: Run Gunicorn on multiple servers
3. **Shared Database**: Single PostgreSQL instance or cluster
4. **Shared Static Files**: Use S3 or CDN for static assets
5. **Redis Cache**: Add Redis for session storage and caching

### Vertical Scaling

- Increase server resources (CPU, RAM)
- Tune Gunicorn workers: `workers = (2 * CPU_cores) + 1`
- Optimize database (indexes, query optimization)
- Enable query caching in Django

---

## Support & Resources

- **Documentation**: `/docs/` directory
- **GitHub Issues**: https://github.com/brucedombrowski/OpenSourceHouseProject/issues
- **Django Docs**: https://docs.djangoproject.com/
- **Nginx Docs**: https://nginx.org/en/docs/
- **PostgreSQL Docs**: https://www.postgresql.org/docs/

---

**Last Updated**: December 6, 2025
**Version**: 1.0
**For**: OpenSourceHouseProject Production Deployment
