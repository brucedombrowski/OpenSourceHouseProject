# Quick Start: Deploy to Production

**Last Updated**: December 8, 2025

This is a simplified 5-minute deployment guide. For detailed instructions, see `DEPLOYMENT_GUIDE.md`.

## Prerequisites

- Linux server (Ubuntu 22.04+) with sudo access
- Domain name (optional, can use IP)
- Let's Encrypt account (free SSL certificates)

## 5-Minute Deployment

### Step 1: Install System Dependencies (2 min)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python, Git, PostgreSQL, Nginx
sudo apt install -y python3.10 python3.10-venv python3-pip git \
    nginx postgresql postgresql-contrib

# Verify installations
python3 --version
psql --version
nginx -v
```

### Step 2: Create Database (1 min)

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# In PostgreSQL shell (psql prompt):
CREATE DATABASE house_project;
CREATE USER house_user WITH PASSWORD 'your_secure_password_here';
ALTER ROLE house_user SET client_encoding TO 'utf8';
ALTER ROLE house_user SET default_transaction_isolation TO 'read committed';
GRANT ALL PRIVILEGES ON DATABASE house_project TO house_user;
\q
```

### Step 3: Clone & Setup Application (1 min)

```bash
# Create app directory
sudo mkdir -p /var/www/house_project
cd /var/www/house_project

# Clone repository
sudo git clone https://github.com/brucedombrowski/OpenSourceHouseProject.git .

# Create virtual environment
sudo python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Generate SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Step 4: Configure Environment (1 min)

```bash
# Create .env file with your values
sudo tee .env > /dev/null << 'EOF'
DEBUG=False
SECRET_KEY=YOUR_GENERATED_SECRET_KEY_HERE
ALLOWED_HOSTS=yourdomain.com,localhost
DATABASE_URL=postgresql://house_user:your_password@localhost:5432/house_project
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
EOF

# Make sure only app user can read .env (security!)
sudo chmod 600 .env
sudo chown www-data:www-data .env

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Step 5: Configure Nginx & Start (1 min)

```bash
# Create nginx config
sudo tee /etc/nginx/sites-available/house_project > /dev/null << 'EOF'
upstream house_wsgi {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL - use certbot to generate these
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    client_max_body_size 10M;

    location / {
        proxy_pass http://house_wsgi;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        alias /var/www/house_project/staticfiles/;
        expires 30d;
    }
}
EOF

# Enable the site
sudo ln -s /etc/nginx/sites-available/house_project /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test and reload nginx
sudo nginx -t
sudo systemctl reload nginx

# Start gunicorn
cd /var/www/house_project
source venv/bin/activate
gunicorn house_wbs.wsgi:application --bind 127.0.0.1:8000 --workers 4 &
```

### Step 6: Setup SSL Certificate (Optional but Recommended)

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate (automatic!)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal is automatic with certbot
```

## Verify Deployment

```bash
# Check that Gantt view works
curl -I https://yourdomain.com/wbs/gantt/

# Check static files are served
curl -I https://yourdomain.com/static/wbs/gantt.js

# Check admin panel
# Visit: https://yourdomain.com/admin
```

## Troubleshooting

**502 Bad Gateway?**
- Check gunicorn is running: `ps aux | grep gunicorn`
- Check logs: `tail -f /var/www/house_project/gunicorn.log`
- Verify database connection: `python manage.py dbshell`

**Static files not loading?**
- Run: `python manage.py collectstatic --noinput`
- Check nginx path: `ls -la /var/www/house_project/staticfiles/`

**SSL certificate errors?**
- Renew certificate: `sudo certbot renew`
- Check expiration: `sudo certbot certificates`

## Performance Tuning

For larger deployments (> 50 users), consider:

1. **PostgreSQL Optimization**:
   ```bash
   sudo -u postgres psql house_project
   ANALYZE;
   ```

2. **Gunicorn Workers**: Adjust based on CPU cores
   ```bash
   --workers $(nproc)
   ```

3. **Redis Caching** (replace LocMemCache):
   ```bash
   pip install redis django-redis
   # Update CACHES in settings.py
   ```

4. **Database Backups**:
   ```bash
   pg_dump house_project > backup.sql
   ```

## Next Steps

- Monitor application: `tail -f /var/var/house_project/logs/gunicorn.log`
- Set up automated backups: See `DEPLOYMENT_GUIDE.md`
- Configure monitoring/alerts: Use New Relic, DataDog, or similar
- Setup supervisor for process management: See `DEPLOYMENT_GUIDE.md`

## Full Documentation

For detailed information, see `docs/DEPLOYMENT_GUIDE.md`.

---

**Deployed successfully!** 🎉

Your application is now running on `https://yourdomain.com`
Admin panel: `https://yourdomain.com/admin`
