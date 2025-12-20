# Build and Deployment Procedures

## Quick Start
Use the `build.sh` script for all builds. Never use `docker compose up` directly in development.

```bash
# Fast build for code changes (recommended for most work)
./build.sh quick

# Full rebuild without losing database
./build.sh rebuild

# Complete fresh start (wipes everything)
./build.sh fresh

# Development with hot reload
./build.sh dev
```

## Caching Issues Encountered and Solutions

### Issue 1: Template Changes Not Appearing
**Problem**: Updated Django templates weren't showing in the browser after `docker compose restart`
**Root Cause**: Docker caches the COPY instruction, so old template files were used in the container
**Solution**: Use `docker compose build --no-cache` to force re-copy of all files

### Issue 2: Static Files Not Updating
**Problem**: CSS/JS changes appeared stale in browser
**Root Cause**: Multiple issues:
1. Browser caching (solved with cache-busting query params `?v=timestamp`)
2. Docker volume mounting not syncing properly
3. collectstatic command running twice with conflicting options
**Solution**:
- Explicitly clean staticfiles directory before rebuild
- Use `collectstatic --noinput --clear` in Dockerfile
- Use `collectstatic --noinput` in docker-compose.yml (without clear, to preserve cache-busting)

### Issue 3: Worker Timeout on Kanban Load
**Problem**: N+1 query problem in views.py causing 30-second timeout
**Root Cause**: Loop querying database for each WbsItem phase extraction
**Solution**: Batch all queries:
- Get all codes in single query: `values_list("code", flat=True)`
- Extract phase numbers in Python using regex
- Fetch phase items in single query: `filter(code__in=sorted_phases)`

### Issue 4: Rebuilds Taking Too Long
**Problem**: Every small code change required full container rebuild
**Root Cause**: Docker layer caching wasn't being utilized effectively
**Solution**:
- Copy requirements.txt early (cached)
- Only rebuild on actual code changes
- Use `--no-cache` only when necessary (quick rebuild with fresh build layer)

## Build Strategy Decision Tree

```
"I changed..."
├── Python code, views, models, utils
│   └── Use: ./build.sh quick
│       (Rebuilds web container with new code)
│
├── HTML templates, CSS, JavaScript
│   └── Use: ./build.sh quick
│       (Rebuilds + collectstatic ensures templates picked up)
│
├── Django settings, imports, or dependencies
│   └── Use: ./build.sh rebuild
│       (Full rebuild to ensure clean state)
│
├── Database model structure
│   └── Use: ./build.sh rebuild
│       (Ensures migrations run cleanly)
│
└── I'm not sure what broke
    └── Use: ./build.sh fresh
        (Nuclear option - clean slate)
```

## Performance Benchmarks

| Command | Time | Use Case |
|---------|------|----------|
| `./build.sh quick` | 10-15s | Code/template/JS changes |
| `./build.sh rebuild` | 20-30s | Settings/models changes |
| `./build.sh fresh` | 45-60s | Deep debugging, complete reset |
| `docker compose restart` | 3-5s | (Don't use - causes caching issues) |

## Lessons Learned

1. **Always use `--no-cache` when copying code**: Templates and static files need to be fresh
2. **Batch database queries**: One 157-item query is vastly better than 157 individual queries
3. **Clear staticfiles before rebuilding**: Django's collectstatic can leave stale files
4. **Use cache-busting on static assets**: Add query params with timestamps to bust browser cache
5. **Document the build process**: Future developers (including yourself) will be grateful

## Troubleshooting

### "I see old code/templates running"
```bash
./build.sh quick
```

### "Database seems corrupted or migrations failed"
```bash
./build.sh rebuild
```

### "Nothing is working and I don't know why"
```bash
./build.sh fresh
./build.sh dev  # Start developing
```

### "Performance is slow or queries are hanging"
1. Check Docker logs: `docker compose logs web -f`
2. Look for N+1 query patterns in views
3. Verify using Django Debug Toolbar in development
4. Profile with: `docker compose exec web python -m cProfile manage.py shell`

## Development Workflow

```bash
# 1. Start developing (one-time setup)
./build.sh fresh

# 2. Make changes
# ... edit files ...

# 3. Test changes (90% of cases)
./build.sh quick

# 4. If tests fail mysteriously
./build.sh rebuild

# 5. Start from scratch if completely stuck
./build.sh fresh
```

## Production Deployment

For production, use a tagged Docker image:

```bash
docker build -t yourimage:v1.0.0 .
docker push yourimage:v1.0.0
# Deploy to production using tagged image
```

## CI/CD Integration

For automated builds:
```bash
# In GitHub Actions or similar
docker build --no-cache -t myapp:latest .
docker compose push
```

## Related Files
- `Dockerfile` - Base image and build instructions
- `docker-compose.yml` - Service composition and command overrides
- `build.sh` - Smart build orchestration script
- `house_wbs/settings.py` - Django settings including STATIC_ROOT, STATIC_URL
- `wbs/views.py` - View functions (check for N+1 queries)

## Common Commands Reference

```bash
# View live logs
docker compose logs -f web

# Enter Django shell
docker compose exec web python manage.py shell

# Run migrations
docker compose exec web python manage.py migrate

# Load test data
docker compose exec web python manage.py load_test_data

# Stop everything
docker compose down

# Inspect database
docker compose exec db psql -U house_user -d house_project
```

---

**Last Updated**: December 8, 2025
**Documented Issue**: N+1 query problem, template caching, static file sync issues
