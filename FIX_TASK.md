You are fixing bugs in the hermes-active Vue 3 frontend. Read the files, understand the issues, and fix them directly.

## Bug 1: Router error on second menu click
Error: `Cannot read properties of null (reading 'component')` at `locateNonHydratedAsyncRoot`
This happens because the router uses lazy imports that fail on second navigation. Check `frontend/src/router/index.js`.

## Bug 2: Session ID is undefined
URL shows `/api/sessions/undefined/context` — the session ID is not being passed.
Check `frontend/src/views/Test.vue` — the `latestSession` object field name might be wrong.
The backend `/api/sessions/latest/weixin` returns `{"id": "...", "source": "...", ...}` not `session_id`.

## Bug 3: Messages page has no data
The session selector shows no options. Check `frontend/src/views/Messages.vue`:
- The API `/api/sessions` returns `{"items": [...], "total": N}` 
- The session options need to use `item.id` not `item.session_id`
- Also check the messages API response format

## Bug 4: Context endpoint uses undefined
`/api/sessions/undefined/context` — check Test.vue where it reads `latestSession.session_id` but the field is `latestSession.id`

## Steps:
1. Read `frontend/src/router/index.js` — check if routes have proper lazy loading
2. Read `frontend/src/views/Test.vue` — fix session_id references  
3. Read `frontend/src/views/Messages.vue` — fix session list and message queries
4. Read `frontend/src/views/SessionDetail.vue` — fix session_id param
5. Read `frontend/src/views/Dashboard.vue` — verify field names
6. Read `backend/routers/sessions.py` — confirm response field names
7. Read `backend/routers/messages.py` — confirm response field names
8. Fix all issues and run: `cd ~/.hermes/hermes-active/frontend && npx vite build 2>&1 | tail -10`

After fixing, sync to /tmp/hermes-active/ and commit:
```bash
cd ~/.hermes/hermes-active
rsync -av --exclude='.git' --exclude='node_modules' --exclude='__pycache__' --exclude='data/*.db' --exclude='*.pyc' --exclude='logs' ./ /tmp/hermes-active/
cd /tmp/hermes-active && git add -A && git commit -m "fix: 修复前端路由/Session ID/消息列表等多个bug" && git push origin main
```
