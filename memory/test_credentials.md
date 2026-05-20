# RAX AI - Test Credentials

## Owner Admin Account (auto-seeded on backend startup + via POST /api/admin/seed-admin)
- **Email**: rascsarango12345@gmail.com
- **Password**: Rasc2026!RaxAI
- **Role**: Owner Admin (is_admin=true), Plan: pro
- This is the ONLY admin account. Only this email gets admin privileges.

## How to (re)seed
Auto-seeded on backend startup. Or manually:
```
POST /api/admin/seed-admin
```
Idempotent — safe to call multiple times. Resets the password to the value above.

## Test User
- Use POST /api/auth/register with any valid email + password (>= 6 chars)
- Or POST /api/auth/guest for guest mode

## Google OAuth
Uses Emergent-managed Google Auth. No app-managed password.
- Test by clicking the Google button on /login.
