# Production-Ready Authentication Service

An enterprise-grade TypeScript/Node.js authentication service implementing robust security controls.

## Features & Compliance
- **[R001] JWT & Opaque Tokens**: Issues short-lived RS256/HS256 Access JWTs (15m) and long-lived opaque Refresh Tokens (7d).
- **[R002] Token Rotation & Theft Detection**: Implements strict refresh token rotation. Re-use of an invalidated token triggers immediate revocation of the entire token family/session tree.
- **[R003] Sliding Window Rate Limiting**: Redis-backed IP rate limiter protecting `/login` and `/refresh` endpoints against brute-force attacks.
- **[R004] Secure Password Hashing**: Passwords are securely hashed via `bcrypt` with cost factor $\ge 12$.
- **[R005] Revocation & Logout**: Authenticated logout endpoint purges active sessions and invalidates active tokens.

## Quickstart
1. Ensure Redis is running locally on `redis://localhost:6379`.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run in development mode:
   ```bash
   npm run dev
   ```
