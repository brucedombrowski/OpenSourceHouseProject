# Production Deployment Guide

This guide covers deploying the Open Source House Project to production environments.

## Pre-Deployment Checklist

### 1. Code Quality
- [ ] All code follows PEP 8 standards (enforced via `ruff`)
- [ ] Code formatted with `black`
- [ ] No unused imports (checked via `source.unusedImports`)
- [ ] All critical functions have type hints and docstrings
- [ ] No hardcoded values (use `wbs/constants.py`)

Validation command:
```bash
python manage.py validate_imports
```

### 2. Database Readiness
- [ ] All migrations applied and tested locally
- [ ] Database backup taken (for migrations on production)
- [ ] Indexes verified on key tables

Verify migrations:
```bash
python manage.py migrate --check
```

Key indexes created:
- ProjectItem: status, type, priority, wbs_item_id, created_at, status+type
- TaskDependency: predecessor_id, successor_id, predecessor+successor
- WbsItem: status, code
- Tag: name

### 3. Environment Configuration
- [ ] `.env` file created with production values (copy from `.env.example`)
- [ ] `DEBUG=False` set in production environment
- [ ] `SECRET_KEY` generated and stored securely
- [ ] Database URL pointing to production database
- [ ] Static files collected (`collectstatic`)
- [ ] Email backend configured for alerts
- [ ] CORS/CSRF settings appropriate for your domain

### 4. Security
- [ ] `ALLOWED_HOSTS` set to production domain(s)
- [ ] HTTPS enabled (SSL certificate installed)
- [ ] Session cookies marked as secure (`SESSION_COOKIE_SECURE=True`)
- [ ] CSRF settings configured correctly (`CSRF_TRUSTED_ORIGINS`)
- [ ] X-Frame-Options header set (click-jacking protection)
- [ ] Regular security headers enabled

### 5. Monitoring & Health Checks
- [ ] Health check endpoints configured in load balancer
- [ ] Log aggregation configured (if applicable)
- [ ] Performance monitoring in place

## Health Check Endpoints

The application provides three health check endpoints for monitoring:

### 1. Lightweight Health Check
```
GET /health/
Response: 200 OK (cached for 60 seconds)
Body: {"status": "ok", "service": "wbs"}
```
**Use case**: Load balancer health checks, quick availability tests
**Performance**: Minimal - no database queries, uses cache

### 2. Detailed Health Check
```
GET /health/detailed/
Response: 200 OK or 503 Service Unavailable
Body: {"status": "ok|error", "database": "ok|error", "timestamp": "ISO datetime"}
```
**Use case**: Monitoring dashboards, detailed diagnostics
**Performance**: Includes database connectivity test

### 3. Readiness Check
```
GET /readiness/
Response: 200 OK or 503 Service Unavailable
Body: {"ready": true|false, "checks": {...}}
```
**Use case**: Kubernetes/container orchestration, startup checks
**Performance**: Comprehensive system checks including migrations status

### Response Codes
- **200 OK**: System is healthy
- **503 Service Unavailable**: System has issues (database down, migrations pending, etc.)

## Deployment Steps

### 1. Prepare Environment
```bash
# Create production environment file
cp .env.example .env
# Edit .env with production values
nano .env
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Apply Migrations
```bash
python manage.py migrate
```

### 4. Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### 5. Validate System
```bash
python manage.py check
python manage.py validate_imports
```

### 6. Run Gunicorn/WSGI Server
```bash
gunicorn house_wbs.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

### 7. Configure Web Server (Nginx/Apache)
Ensure:
- Static files served directly from `/static/` path
- Media files served from `/media/` path (if used)
- HTTPS enabled with valid certificate
- Security headers configured

### 8. Set Up Load Balancer
Configure health check:
```
Health Check URL: /health/
Check Interval: 30 seconds
Timeout: 5 seconds
Healthy Threshold: 2 consecutive checks
Unhealthy Threshold: 3 consecutive failures
```

## Configuration Reference

### Critical Settings (in .env)

```env
# Django
DEBUG=False
SECRET_KEY=your-very-long-random-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname
# Or for SQLite in production (not recommended for high traffic):
# DATABASE_URL=sqlite:///./db.sqlite3

# Security
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000

# Static/Media Files
STATIC_ROOT=/path/to/static
STATIC_URL=/static/
MEDIA_ROOT=/path/to/media
MEDIA_URL=/media/

# Email (for notifications)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.your-provider.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-password

# Logging
LOG_LEVEL=INFO
```

## Performance Optimization

### Database Optimization
- Indexes applied on all frequently-filtered fields (see migrations/0014)
- QuerySet optimization with `select_related()` and `prefetch_related()`
- Gantt view uses optimized queries via `for_gantt_view()` manager method

### Caching
- Health check endpoint cached for 60 seconds
- Consider adding Redis for session/template caching in high-traffic environments

### Static Files
- Minify CSS/JavaScript in production build process
- Consider CDN for static asset delivery

## Troubleshooting

### Health Check Fails
```bash
# Check database connectivity
python manage.py dbshell
# Run detailed health check for diagnostics
curl http://localhost:8000/health/detailed/
```

### Migrations Pending
```bash
# Check migration status
python manage.py showmigrations
# Apply any pending migrations
python manage.py migrate
```

### Performance Issues
1. Check database indexes are applied:
   ```sql
   -- SQLite example
   .indices wbs_projectitem
   .indices wbs_wbsitem
   .indices wbs_taskdependency
   ```

2. Monitor slow queries in Django debug toolbar (development only) or enable query logging

3. Consider increasing worker processes if CPU is bottleneck

### Common Issues

#### Static Files Not Serving
- Ensure `collectstatic` was run
- Check `STATIC_ROOT` and `STATIC_URL` configuration
- Verify web server is configured to serve static path

#### Database Locked (SQLite)
- Not recommended for production - migrate to PostgreSQL
- If using SQLite, ensure only one process accesses database
- Increase timeout: `DATABASES['default']['OPTIONS'] = {'timeout': 20}`

#### Import Validation Fails
Run diagnostic:
```bash
python manage.py validate_imports
```
This will identify which module is causing issues.

## Monitoring & Maintenance

### Regular Checks
- Monitor health check endpoints: `/health/` and `/health/detailed/`
- Check error logs for exceptions
- Monitor database performance and size
- Review application logs for warnings

### Scheduled Tasks
- Consider adding periodic backup of SQLite database (if used)
- Monitor disk space for logs and media files
- Update Python dependencies periodically

## Rollback Procedures

### Database Rollback
```bash
# See available migrations
python manage.py showmigrations wbs
# Rollback to specific migration
python manage.py migrate wbs 0013
```

### Code Rollback
```bash
# If deployed via git
git revert <commit-hash>
```

## Support & Diagnostics

### Validate System Health
```bash
# Complete system validation
python manage.py check
python manage.py migrate --check
python manage.py validate_imports

# Test health endpoints
curl http://localhost:8000/health/
curl http://localhost:8000/health/detailed/
curl http://localhost:8000/readiness/
```

### Enable Debug Logging
Temporarily enable in .env for investigation:
```env
DEBUG=True
LOG_LEVEL=DEBUG
```
**IMPORTANT**: Only for debugging - disable in production!

## Testing Production Configuration Locally

```bash
# Copy production .env template
cp .env.example .env.test

# Set DEBUG=False to test production config
DEBUG=False python manage.py check

# Test health endpoints
DEBUG=False python manage.py runserver
# Then in another terminal:
curl http://127.0.0.1:8000/health/
```

---

**Last Updated**: December 8, 2025
**Version**: 1.0
**Author**: Development Team
