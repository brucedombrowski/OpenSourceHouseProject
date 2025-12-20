# Docker Deployment Guide

**Project**: Open Source House Project
**Last Updated**: December 8, 2025
**Version**: 1.0.0

## Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Local Development with Docker](#local-development-with-docker)
4. [Production Deployment](#production-deployment)
5. [Scaling & Optimization](#scaling--optimization)
6. [Troubleshooting](#troubleshooting)
7. [Backup & Restore](#backup--restore)

---

## Quick Start

### 1-Minute Setup (Development)

```bash
# Clone repository
git clone https://github.com/brucedombrowski/OpenSourceHouseProject.git
cd OpenSourceHouseProject

# Copy environment file
cp .env.docker .env

# Start services
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Access application
# Web: http://localhost:8000
# Admin: http://localhost:8000/admin
```

---

## Prerequisites

### System Requirements

- **Docker**: 20.10+ (install from https://docs.docker.com/get-docker/)
- **Docker Compose**: 1.29+ (included with Docker Desktop)
- **Disk Space**: 5GB minimum (for images and data)
- **RAM**: 2GB minimum (4GB+ recommended)

### Verify Installation

```bash
# Check Docker
docker --version
# Expected: Docker version 20.10+

# Check Docker Compose
docker-compose --version
# Expected: Docker Compose version 1.29+

# Test Docker
docker run hello-world
# Should print: "Hello from Docker!"
```

---

## Local Development with Docker

### Setup Development Environment

```bash
# 1. Copy environment file
cp .env.docker .env

# Edit .env with your settings (optional for dev)
nano .env

# 2. Build images
docker-compose build

# 3. Start services (first time takes 1-2 minutes)
docker-compose up -d

# 4. Check status
docker-compose ps
# All services should show "healthy"

# 5. Run migrations
docker-compose exec web python manage.py migrate

# 6. Create superuser
docker-compose exec web python manage.py createsuperuser

# 7. Load sample data (optional)
docker-compose exec web python manage.py import_wbs_csv data/wbs_items_template.csv --update
docker-compose exec web python manage.py import_dependencies_csv data/wbs_dependencies_template.csv --update
```

### Access Application

```
Web Interface: http://localhost:8000
Admin Panel:   http://localhost:8000/admin
Database:      localhost:5432 (from your machine)
```

### Common Development Commands

```bash
# View logs
docker-compose logs -f web          # Django logs
docker-compose logs -f db           # Database logs
docker-compose logs -f nginx        # Nginx logs

# Run Django management commands
docker-compose exec web python manage.py test wbs
docker-compose exec web python manage.py collectstatic
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate

# Access Python shell
docker-compose exec web python manage.py shell

# Access database shell
docker-compose exec db psql -U house_user -d house_project

# Rebuild after code changes
docker-compose build web
docker-compose up -d web

# Stop services
docker-compose down

# Stop and remove all data
docker-compose down -v
```

---

## Production Deployment

### 1. Prepare Environment

```bash
# Generate new SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Create .env file with production values
cat > .env << 'EOF'
DEBUG=False
SECRET_KEY=<generated_secret_key_here>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
DB_PASSWORD=<secure_database_password>
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
EOF

# Set strict permissions
chmod 600 .env
```

### 2. Obtain SSL Certificate

Using Let's Encrypt (recommended):

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy to ssl directory
sudo mkdir -p ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem
sudo chown $USER:$USER ssl/*
chmod 600 ssl/*
```

### 3. Deploy with Docker

```bash
# Pull latest code
git clone https://github.com/brucedombrowski/OpenSourceHouseProject.git
cd OpenSourceHouseProject

# Copy environment and SSL
cp .env.docker .env
# Edit .env with your production values

mkdir -p ssl
cp /path/to/cert.pem ssl/
cp /path/to/key.pem ssl/

# Build and start services
docker-compose build
docker-compose up -d

# Verify services
docker-compose ps
# All should show "healthy"

# Check logs
docker-compose logs -f
```

### 4. Post-Deployment Verification

```bash
# Test web application
curl https://yourdomain.com

# Test admin panel
curl https://yourdomain.com/admin

# Check database
docker-compose exec web python manage.py dbshell
\l  # List databases
\q  # Quit

# Run tests
docker-compose exec web python manage.py test wbs
```

---

## Scaling & Optimization

### Increase Web Workers

Edit `docker-compose.yml`, increase workers:

```yaml
web:
  command: >
    sh -c "python manage.py migrate &&
           python manage.py collectstatic --noinput &&
           gunicorn house_wbs.wsgi:application --bind 0.0.0.0:8000 --workers 8"
```

Workers = 2 × CPU cores (recommended).

### Add Redis Cache (Optional)

```bash
# Add to docker-compose.yml:
# cache:
#   image: redis:7-alpine
#   command: redis-server --appendonly yes
#   volumes:
#     - redis_data:/data
#   healthcheck:
#     test: ["CMD", "redis-cli", "ping"]
#
# Then update CACHES in settings.py to use Redis
```

### Database Optimization

```bash
# Connect to database
docker-compose exec db psql -U house_user -d house_project

# Analyze tables
ANALYZE;

# View table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Monitor Resource Usage

```bash
# Real-time stats
docker stats

# Detailed container info
docker-compose ps

# Container logs with timestamps
docker-compose logs --timestamps
```

---

## Troubleshooting

### Services Won't Start

```bash
# Check for port conflicts
sudo lsof -i :80,443,8000,5432

# View detailed logs
docker-compose logs --tail=50

# Rebuild images
docker-compose down
docker system prune -a
docker-compose build --no-cache
docker-compose up -d
```

### Database Connection Issues

```bash
# Test connection from web container
docker-compose exec web python manage.py dbshell

# Check database logs
docker-compose logs db

# Verify network connectivity
docker-compose exec web ping db

# Check database health
docker-compose exec db pg_isready -U house_user
```

### Static Files Not Loading

```bash
# Rebuild static files
docker-compose exec web python manage.py collectstatic --noinput --clear

# Check file permissions
docker-compose exec web ls -la staticfiles/

# Verify nginx configuration
docker-compose exec nginx nginx -t
```

### Memory Issues

```bash
# Check memory usage
docker stats

# View image sizes
docker images

# Clean up old images
docker image prune

# Set memory limits in docker-compose.yml:
# mem_limit: 1g
```

### Permission Denied Errors

```bash
# Fix SSL certificate permissions
sudo chown $USER:$USER ssl/*
chmod 600 ssl/*

# Fix volume permissions
sudo chown 1000:1000 staticfiles logs
```

---

## Backup & Restore

### Database Backup

```bash
# Backup to file
docker-compose exec -T db pg_dump -U house_user -d house_project > backup.sql

# Automated daily backup
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=/backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T db pg_dump -U house_user -d house_project > \
  $BACKUP_DIR/house_project_$TIMESTAMP.sql
# Keep only last 7 days
find $BACKUP_DIR -name "house_project_*.sql" -mtime +7 -delete
EOF

chmod +x backup.sh
# Add to crontab: 0 2 * * * /path/to/backup.sh
```

### Database Restore

```bash
# Restore from backup
docker-compose exec -T db psql -U house_user -d house_project < backup.sql

# Or from within container
docker-compose exec db psql -U house_user -d house_project < /backup.sql
```

### Full Application Backup

```bash
# Backup database and volumes
docker-compose exec -T db pg_dump -U house_user -d house_project > backup.sql
docker run --rm -v house_project_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/database_volume.tar.gz -C /data .
tar czf staticfiles_backup.tar.gz staticfiles/

# Create full backup
tar czf house_project_backup_$(date +%Y%m%d).tar.gz \
  backup.sql database_volume.tar.gz staticfiles_backup.tar.gz .env
```

### Restore Full Backup

```bash
# Extract backup
tar xzf house_project_backup_YYYYMMDD.tar.gz

# Start services
docker-compose up -d

# Restore database
docker-compose exec -T db psql -U house_user -d house_project < backup.sql

# Verify
docker-compose exec web python manage.py check
```

---

## Docker Hub Deployment

### Push to Registry

```bash
# Build image
docker build -t yourusername/house-project:1.0.0 .

# Login to Docker Hub
docker login

# Push image
docker push yourusername/house-project:1.0.0

# Or use docker-compose
docker-compose -f docker-compose.yml -f docker-compose.prod.yml push
```

### Deploy from Registry

Update `docker-compose.yml`:

```yaml
web:
  image: yourusername/house-project:1.0.0
  # ... rest of config
```

---

## Docker Compose File Structure

**Services**:
- **web**: Django application (Gunicorn)
- **db**: PostgreSQL database
- **nginx**: Reverse proxy and static file server

**Volumes**:
- `postgres_data`: Database files
- `staticfiles`: Collected static files
- `logs`: Application logs

**Networks**: Automatically created for inter-container communication

---

## Security Best Practices

1. **Environment Variables**: Never commit `.env` files
2. **Secret Key**: Generate new one for production
3. **SSL Certificates**: Always use HTTPS in production
4. **Database Password**: Use strong, random password
5. **Regular Updates**: Keep Docker images updated
6. **Backups**: Automate daily database backups
7. **Logs**: Monitor logs for suspicious activity
8. **Permissions**: Restrict file access appropriately

---

## Support & Documentation

- **Docker Docs**: https://docs.docker.com
- **Docker Compose Docs**: https://docs.docker.com/compose
- **Django Docs**: https://docs.djangoproject.com
- **PostgreSQL Docs**: https://www.postgresql.org/docs
- **Nginx Docs**: https://nginx.org/en/docs

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Port already in use | Change port in docker-compose.yml or `docker-compose down` |
| Migrations not applied | Run `docker-compose exec web python manage.py migrate` |
| Static files not loading | Run `docker-compose exec web python manage.py collectstatic --noinput` |
| Database won't start | Check logs with `docker-compose logs db` and ensure disk space |
| 502 Bad Gateway | Check web container logs: `docker-compose logs web` |
| Permission denied | Fix SSL cert permissions: `chmod 600 ssl/*` |

---

**Next Steps**: See PRODUCTION_DEPLOYMENT.md for additional details.
