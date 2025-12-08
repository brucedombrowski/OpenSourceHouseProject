# Authentication & Authorization Strategy

## Current Status (Development)

**All views are now publicly accessible with no login required.**

This makes development consistent and fast:
- ✅ Kanban board: No login
- ✅ Gantt chart: No login
- ✅ Admin panel: Still protected (Django built-in)
- ✅ Health checks: No login

### Why This Approach?

1. **Development consistency**: All app features accessible
2. **Faster iteration**: No login fatigue during development
3. **Therapist-approved**: All-or-nothing is simpler than mixed auth
4. **Easy to switch**: Comments mark where to add auth back

## Future Production Strategy

When ready for production, implement role-based access control:

### Proposed User Roles

```
┌─────────────┬────────────┬──────────┬──────────┬──────────┐
│ Feature     │ Viewer     │ Editor   │ Manager  │ Admin    │
├─────────────┼────────────┼──────────┼──────────┼──────────┤
│ Gantt View  │ ✅ Read    │ ✅ Read  │ ✅ Read  │ ✅ Read  │
│ Gantt Edit  │ ❌         │ ✅ Edit  │ ✅ Edit  │ ✅ Edit  │
│ Kanban View │ ✅ Read    │ ✅ Read  │ ✅ Read  │ ✅ Read  │
│ Kanban Edit │ ❌         │ ✅ Edit  │ ✅ Edit  │ ✅ Edit  │
│ Admin Panel │ ❌         │ ❌       │ ✅ Mgmt  │ ✅ Full  │
│ User Mgmt   │ ❌         │ ❌       │ ❌       │ ✅ Full  │
└─────────────┴────────────┴──────────┴──────────┴──────────┘
```

### Implementation Plan

1. **Phase 1**: Add Django login page
   ```python
   from django.contrib.auth.decorators import login_required
   ```

2. **Phase 2**: Add permission decorators to views
   ```python
   @login_required
   def gantt_chart(request):
       # User can view
       ...

   @permission_required('wbs.change_wbsitem')
   def gantt_set_task_dates(request):
       # User can edit
       ...
   ```

3. **Phase 3**: Create custom permission groups
   ```python
   # In Django admin, create groups:
   # - Viewers (view_wbsitem, view_projectitem)
   # - Editors (change_wbsitem, change_projectitem, add_projectitem)
   # - Managers (all WBS/Project permissions)
   # - Admins (all permissions)
   ```

4. **Phase 4**: Add user management UI
   - Create users in admin
   - Assign to groups
   - Set per-project access (optional, future phase)

### Quick Reference: Where Auth Is Defined

| File | Location | Status |
|------|----------|--------|
| `wbs/views_gantt.py` | Line 133+ | Removed `@staff_member_required` - add back for production |
| `wbs/views.py` | Lines 72, 129 | Only has `@ensure_csrf_cookie` (no auth) |
| `house_wbs/urls.py` | Line 22 | Admin path inherits Django auth |
| `house_wbs/settings.py` | Line 57-89 | Django auth middleware enabled |

### How to Re-Enable Auth for Production

When switching to production mode:

1. **Step 1**: Add `@login_required` to sensitive views
   ```python
   from django.contrib.auth.decorators import login_required

   @login_required
   def gantt_chart(request):
       ...
   ```

2. **Step 2**: Create permission groups in Django shell
   ```bash
   docker compose exec web python manage.py shell

   from django.contrib.auth.models import Group, Permission

   # Create Viewers group
   viewers = Group.objects.create(name='Viewers')
   viewers.permissions.add(...)  # view permissions
   ```

3. **Step 3**: Add login URL to settings
   ```python
   # In house_wbs/settings.py
   LOGIN_URL = 'admin:login'
   LOGIN_REDIRECT_URL = '/'
   ```

### Security Checklist for Production

- [ ] `DEBUG = False` in settings
- [ ] `ALLOWED_HOSTS` configured
- [ ] `SECRET_KEY` changed
- [ ] `@login_required` on all app views
- [ ] Permission groups created and assigned
- [ ] Database backups configured
- [ ] HTTPS enabled (via reverse proxy)
- [ ] CSRF protection enabled (already is)
- [ ] SQL injection prevention (Django ORM handles this)
- [ ] XSS protection (Django templates handle this)

### Current Decorators in Code

These are marked with `# NOTE:` comments:

```python
# Search for these to add auth back:
# - gantt_chart (line 133)
# - gantt_shift_task (line 451)
# - gantt_set_task_dates (line 532)
# - gantt_optimize_schedule (line 577)
# - update_task_name (line 717)
# - search_autocomplete (line 743)
```

### Testing Without Auth (Development)

All endpoints work without login:

```bash
# Gantt chart
curl http://localhost:8000/gantt/

# Kanban board
curl http://localhost:8000/project-items/board/

# Kanban API
curl http://localhost:8000/project-items/status/
```

### Testing With Auth (Production - Future)

```bash
# First, log in via admin
curl -c cookies.txt http://localhost:8000/admin/login/

# Then access protected views
curl -b cookies.txt http://localhost:8000/gantt/

# Or use Django test client
./manage.py shell
>>> from django.test import Client
>>> c = Client()
>>> c.login(username='user', password='pass')
>>> response = c.get('/gantt/')
```

## Migration Path

### Step 1: Current (Development)
- No auth
- All users have full access
- Fast development

### Step 2: Session Auth (Near-term)
- Add `@login_required` decorators
- Use Django built-in user auth
- Simple permission groups

### Step 3: OAuth Integration (Long-term, optional)
- Add Google/GitHub login
- Single sign-on (SSO)
- No password management

## Related Files

- `house_wbs/settings.py` - AUTH_PASSWORD_VALIDATORS, auth middleware
- `house_wbs/urls.py` - URL routing (admin auth still works)
- `wbs/views_gantt.py` - All Gantt endpoints (marked for auth)
- `wbs/views.py` - Kanban endpoints (no auth markers)
- `BUILD_PROCEDURES.md` - Dev/prod build process

---

**Key Insight**: Your therapist is right - consistency (all or nothing) is better than mixing auth and non-auth views. This approach keeps development fast while documenting exactly where to add auth for production. 🎯
