# PRE-FLIGHT CHECKLIST — Run Before Declaring Any Task Complete

**Every code change must pass ALL items below before committing.**
No exceptions. No "I'll fix it later."

---

## 1. ERROR HANDLING
- [ ] No bare `except Exception: pass` — every catch block logs or re-raises
- [ ] No bare `except:` — always catch specific exceptions
- [ ] Every DB write has rollback on failure
- [ ] Every external call (API, file I/O) has timeout and error handling
- [ ] Error messages are human-readable, not Python tracebacks

## 2. INPUT VALIDATION
- [ ] All user inputs validated before use
- [ ] No unvalidated data reaches the DB
- [ ] Edge cases tested: empty, None, negative, zero, very large, special chars
- [ ] File uploads validated (extension, size, content)

## 3. SECURITY
- [ ] No SQL injection vectors (use parameterized queries)
- [ ] No path traversal in file operations
- [ ] No sensitive data in error messages or logs
- [ ] CSRF tokens on all forms
- [ ] Role checks on all protected routes
- [ ] Tenant isolation on all tenant-scoped queries

## 4. TESTS
- [ ] Every new function has at least one test
- [ ] Every new route has at least one test
- [ ] Edge cases tested, not just happy path
- [ ] Tests actually ASSERT something (not just "no exception")
- [ ] Full test suite passes (`pytest tests/ -q`)

## 5. CODE QUALITY
- [ ] No duplicate code — if it appears twice, extract it
- [ ] No dead code — remove unused imports, functions, variables
- [ ] No TODO/FIXME without a tracking issue
- [ ] Docstrings on all public functions
- [ ] Type hints on function signatures

## 6. USER EXPERIENCE
- [ ] Error messages are in Tigist's language, not developer language
- [ ] Every action has feedback (flash message, notification, redirect)
- [ ] Loading states shown for slow operations
- [ ] Confirmation dialogs for destructive actions
- [ ] Mobile-responsive layout checked

## 7. PERFORMANCE
- [ ] No N+1 queries — batch-fetch related data
- [ ] No unbounded queries — always paginate or limit
- [ ] No blocking operations in request handlers
- [ ] DB indexes on frequently queried columns

## 8. INTEGRATION
- [ ] New code works with existing routes (no broken links)
- [ ] Template variables match what the route passes
- [ ] New model fields have migrations
- [ ] Sidebar/navigation updated if new pages added
- [ ] i18n keys added for new user-facing strings

## 9. REVIEW YOUR OWN DIFF
- [ ] Read every line you changed
- [ ] Check for copy-paste errors
- [ ] Check for off-by-one errors
- [ ] Check for missing imports
- [ ] Check for variable name mismatches

---

## HOW TO USE

Before saying "done":
1. Go through each item above
2. For each unchecked item, either fix it or document why it's not applicable
3. Run `pytest tests/ -q` — must pass
4. Read your own diff one more time
5. Then and only then commit

**If you find an issue during review, fix it BEFORE committing.
Don't commit and then fix in a separate "improvements" commit.**
