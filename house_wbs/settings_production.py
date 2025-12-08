r"""
Production settings for house_wbs project.

This is a reference configuration for production deployments.
Copy relevant settings to your .env file and use the base settings.py
which reads from environment variables.

For deployment, ensure:
1. DEBUG = False (set in .env)
2. SECRET_KEY = <new random value> (set in .env)
3. ALLOWED_HOSTS = your domain (set in .env)
4. DATABASE_URL points to PostgreSQL (set in .env)
5. All SECURE_* settings are True (set in .env)

Production Deployment Checklist:
================================
1. Generate new SECRET_KEY:
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

2. Set environment variables in .env:
   DEBUG=False
   SECRET_KEY=<generated key>
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   DATABASE_URL=postgresql://user:password@localhost:5432/dbname
   SECURE_SSL_REDIRECT=True
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   SECURE_HSTS_SECONDS=31536000
   SECURE_HSTS_INCLUDE_SUBDOMAINS=True
   SECURE_HSTS_PRELOAD=True

3. Collect static files:
   python manage.py collectstatic --noinput

4. Run migrations:
   python manage.py migrate

5. Create superuser:
   python manage.py createsuperuser

6. Run tests to verify:
   python manage.py test wbs

7. Start with gunicorn:
   gunicorn house_wbs.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 60

Example .env File for Production:
==================================

# Security
DEBUG=False
SECRET_KEY=your-generated-secret-key-here-minimum-50-chars

# Database (PostgreSQL)
DATABASE_URL=postgresql://house_user:your_password@localhost:5432/house_project

# Hosts
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,localhost
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Security (HTTPS required for these to work)
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True

Example nginx Configuration:
============================

upstream house_project {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL certificates (use Let's Encrypt certbot)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL best practices
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # HSTS header
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    client_max_body_size 10M;

    location / {
        proxy_pass http://house_project;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    # Serve static files directly with caching
    location /static/ {
        alias /home/houseproject/app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Deny access to sensitive files
    location ~ r"/\.env" {
        deny all;
        access_log off;
        log_not_found off;
    }
}

Example Supervisor Configuration:
===================================

[program:house_project]
directory=/home/houseproject/app
command=/home/houseproject/app/venv/bin/gunicorn house_wbs.wsgi:application --bind 127.0.0.1:8000 --workers 4 --timeout 60
user=houseproject
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/houseproject/app/logs/gunicorn.log
environment=PATH="/home/houseproject/app/venv/bin"

See docs/DEPLOYMENT_GUIDE.md for full instructions.
"""

# This file serves as documentation only.
# Actual configuration uses environment variables in house_wbs/settings.py
