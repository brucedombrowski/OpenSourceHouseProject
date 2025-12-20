# Development Quick Start

## TL;DR - Just Want to Code?

```bash
# First time setup
./build.sh fresh

# After you make code/template changes
./build.sh quick

# If something breaks mysteriously
./build.sh rebuild

# If everything is on fire
./build.sh fresh
```

That's it! See `BUILD_PROCEDURES.md` for details.

## Common Development Tasks

### Making Changes to Views/Models
```bash
# 1. Edit your code
nano wbs/views.py

# 2. Test it
./build.sh quick

# 3. Check logs if something broke
docker compose logs -f web
```

### Making Changes to Templates/CSS/JS
```bash
# 1. Edit the file
nano wbs/templates/wbs/kanban.html

# 2. Test it
./build.sh quick

# 3. If you don't see changes, clear browser cache (Cmd+Shift+R on Mac)
```

### Working with the Database
```bash
# Run migrations
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

# Load fresh test data
docker compose exec web python manage.py load_test_data

# Access database directly
docker compose exec db psql -U house_user -d house_project
```

### Debugging
```bash
# View real-time logs
docker compose logs -f web

# Enter Django shell
docker compose exec web python manage.py shell

# Run Python snippet directly
docker compose exec web python -c "from wbs.models import WbsItem; print(WbsItem.objects.count())"
```

## Why Use `build.sh` Instead of `docker compose up`?

Direct docker commands can leave you with stale code/templates. The `build.sh` script:
- ✅ Properly rebuilds Docker images
- ✅ Clears cached static files when needed
- ✅ Handles template file syncing
- ✅ Waits for services to be healthy
- ✅ Provides clear feedback on what's happening

## Caching Gotchas You'll Encounter

### "I changed a template but don't see it"
→ Use `./build.sh quick` (not `docker compose restart`)

### "My CSS/JS changes aren't showing"
→ Hard refresh browser (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows)
→ If that doesn't work, use `./build.sh quick`

### "The kanban board loads but is really slow or times out"
→ Check for N+1 query problem in views
→ Look at: `docker compose logs -f web`

### "Something is definitely broken, tried everything"
→ Use `./build.sh fresh` to start completely clean

## Project URLs

- **Kanban Board**: http://localhost:8000/project-items/board/
- **Gantt Chart**: http://localhost:8000/gantt/
- **Admin Panel**: http://localhost:8000/admin/
- **Health Check**: http://localhost:8000/health/

## Important Files

| File | Purpose |
|------|---------|
| `build.sh` | Smart build script - USE THIS |
| `docker-compose.yml` | Service configuration |
| `Dockerfile` | Container setup |
| `BUILD_PROCEDURES.md` | Detailed build documentation |
| `wbs/views.py` | Kanban and other views |
| `wbs/templates/wbs/kanban.html` | Kanban UI |
| `wbs/static/wbs/kanban.js` | Kanban filtering logic |

## Getting Help

1. Check `BUILD_PROCEDURES.md` for known issues
2. Look at `docker compose logs -f web` for errors
3. Try the appropriate build level (quick → rebuild → fresh)

---

**Remember**: Always use `./build.sh` instead of direct docker commands. It saves hours of debugging! 🚀
