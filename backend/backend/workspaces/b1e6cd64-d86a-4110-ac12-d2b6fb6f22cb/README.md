# Secure Authentication System

This is a production-ready authentication backend service built with Node.js, Express, TypeScript, and JSON Web Tokens (JWT).

## Features & Requirements Met

- **R001**: User Registration via email and password with strict validation (minimum 8 characters for passwords).
- **R002**: Secure Password Hashing using `bcrypt` with work factor 12. Passwords are never stored in plain text.
- **R003**: Secure Authentication allowing users to log in with valid credentials, issuing a JWT session token.
- **R004**: Account Brute-Force Protection that locks user accounts for 15 minutes after 5 consecutive failed login attempts.

## Getting Started

### Prerequisites
- Node.js (v18+ recommended)
- npm

### Installation
```bash
npm install
```

### Running the Application

- Development mode:
  ```bash
  npm run dev
  ```

- Build and production mode:
  ```bash
  npm run build
  npm start
  ```

## API Endpoints

### 1. Register User
- **POST** `/api/auth/register`
- **Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "securePassword123"
  }
  ```

### 2. Login User
- **POST** `/api/auth/login`
- **Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "securePassword123"
  }
  ```
