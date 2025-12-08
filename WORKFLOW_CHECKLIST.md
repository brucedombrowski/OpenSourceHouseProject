# Development Workflow Checklist

Use this checklist for each feature/bug to ensure proper tracking.

## Before You Start Work

- [ ] Create GitHub issue with clear description
- [ ] Label the issue appropriately (enhancement, bug, task, etc.)
- [ ] Set milestone if applicable
- [ ] Mark issue as "in-progress"
- [ ] Create a branch if needed: `git checkout -b feature/<issue-number>-description`

## While Working

- [ ] Make frequent commits with clear messages
- [ ] Link commits to issue: `git commit -m "Description (fixes #123)"`
- [ ] Update issue with progress if work takes multiple days
- [ ] Add comments if blocked or need feedback

## Code Changes

- [ ] Follow existing code patterns
- [ ] Run `./build.sh quick` to test
- [ ] Check `docker compose logs web -f` for errors
- [ ] Update relevant documentation

## Before Merging

- [ ] All tests passing (if applicable)
- [ ] No breaking changes to existing features
- [ ] Updated CHANGELOG or docs if needed
- [ ] PR references the issue: "closes #123"

## After Merging

- [ ] GitHub issue auto-closes (via commit message)
- [ ] Update GITHUB_ISSUES_LOG.md with final status
- [ ] Tag or mark as done
- [ ] Verify feature works in main branch

## Issue Templates for GitHub

### Bug Report
```markdown
**Description**: [Clear description of the bug]

**Steps to Reproduce**:
1. [First step]
2. [Second step]

**Expected Behavior**: [What should happen]

**Actual Behavior**: [What actually happens]

**Environment**:
- Docker: Yes/No
- Browser: Chrome/Firefox/Safari
- OS: macOS/Linux/Windows

**Logs**: [Relevant error messages]
```

### Feature Request
```markdown
**Description**: [What feature, why it's needed]

**Acceptance Criteria**:
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

**Related Issues**: [If any]

**Files to Modify**: [Best guess]
```

### Task
```markdown
**Description**: [What needs to be done]

**Subtasks**:
- [ ] Subtask 1
- [ ] Subtask 2

**Time Estimate**: [Rough estimate]

**Depends On**: [Other issues/tasks]
```

---

## Key Principle

**Everything that takes more than 15 minutes should have a GitHub issue.** This includes:
- Feature development
- Bug fixes
- Performance optimizations
- Documentation updates
- Infrastructure improvements

Small things (typos, obvious small fixes) can skip issues.

---

**Purpose**: Maintain clear audit trail and prevent losing track of work.
**Responsibility**: Update at start and end of each work session.
