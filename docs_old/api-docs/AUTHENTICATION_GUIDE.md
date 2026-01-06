# Authentication Guide

## Overview

The Intelligent Web Data Aggregator API uses **JSON Web Tokens (JWT)** for stateless authentication. This guide provides comprehensive details on authentication mechanisms, security best practices, and troubleshooting.

## Table of Contents

- [Authentication Flow](#authentication-flow)
- [Registration](#registration)
- [Login and Token Generation](#login-and-token-generation)
- [Using Access Tokens](#using-access-tokens)
- [Token Management](#token-management)
- [Security Best Practices](#security-best-practices)
- [Password Requirements](#password-requirements)
- [Error Handling](#error-handling)
- [Advanced Topics](#advanced-topics)

## Authentication Flow

```
┌─────────────┐                                    ┌─────────────┐
│   Client    │                                    │   API       │
└──────┬──────┘                                    └──────┬──────┘
       │                                                  │
       │  1. POST /auth/register                         │
       │     (username, password, email)                 │
       ├─────────────────────────────────────────────────>│
       │                                                  │
       │  2. User Created (200 OK)                       │
       │<─────────────────────────────────────────────────┤
       │                                                  │
       │  3. POST /auth/token                            │
       │     (username, password)                        │
       ├─────────────────────────────────────────────────>│
       │                                                  │
       │  4. JWT Access Token (200 OK)                   │
       │<─────────────────────────────────────────────────┤
       │                                                  │
       │  5. API Request with Bearer Token               │
       │     Authorization: Bearer <token>               │
       ├─────────────────────────────────────────────────>│
       │                                                  │
       │  6. Protected Resource (200 OK)                 │
       │<─────────────────────────────────────────────────┤
       │                                                  │
```

## Registration

### Endpoint: `POST /auth/register`

Create a new user account with username, password, and optional email.

**Rate Limit**: 5 requests per minute per IP address

**Request**:
```http
POST /auth/register HTTP/1.1
Host: api.example.com
Content-Type: application/json

{
  "username": "john_doe",
  "password": "SecureP@ssw0rd!",
  "email": "john@example.com"
}
```

**Success Response** (200 OK):
```json
{
  "id": 42,
  "username": "john_doe",
  "email": "john@example.com",
  "is_active": true
}
```

**Error Responses**:

| Status | Error | Description |
|--------|-------|-------------|
| 400 | Username already registered | The username is already taken |
| 400 | Password too long | Password exceeds 72 bytes (bcrypt limit) |
| 422 | Validation Error | Invalid request format |
| 429 | Rate Limit Exceeded | Too many registration attempts |

**Example Error**:
```json
{
  "detail": "Username already registered"
}
```

### Registration Best Practices

1. **Unique Usernames**: Ensure usernames are unique across your application
2. **Strong Passwords**: Enforce password complexity requirements on the client side
3. **Email Verification**: Consider implementing email verification for production systems
4. **Rate Limiting**: The API automatically rate-limits registration to prevent abuse

## Login and Token Generation

### Endpoint: `POST /auth/token`

Authenticate with username and password to receive a JWT access token.

**Rate Limit**: 10 requests per minute per IP address

**Request**:
```http
POST /auth/token HTTP/1.1
Host: api.example.com
Content-Type: application/x-www-form-urlencoded

username=john_doe&password=SecureP@ssw0rd!
```

**cURL Example**:
```bash
curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=john_doe&password=SecureP@ssw0rd!"
```

**Python Example**:
```python
import requests

response = requests.post(
    "http://localhost:8000/auth/token",
    data={
        "username": "john_doe",
        "password": "SecureP@ssw0rd!"
    }
)
token_data = response.json()
access_token = token_data["access_token"]
```

**Success Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqb2huX2RvZSIsImV4cCI6MTY5MzQ4MjAwMH0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
  "token_type": "bearer"
}
```

**Error Responses**:

| Status | Error | Description |
|--------|-------|-------------|
| 401 | Incorrect username or password | Invalid credentials |
| 400 | Inactive user | User account is deactivated |
| 429 | Rate Limit Exceeded | Too many login attempts |

**Example Error**:
```json
{
  "detail": "Incorrect username or password"
}
```

### JWT Token Structure

The JWT token consists of three parts separated by dots:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9    ← Header
.
eyJzdWIiOiJqb2huX2RvZSIsImV4cCI6MTY5M...  ← Payload
.
SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQ... ← Signature
```

**Header**:
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

**Payload**:
```json
{
  "sub": "john_doe",
  "exp": 1693482000
}
```

- `sub`: Subject (username)
- `exp`: Expiration time (Unix timestamp)

**Token Expiration**: Tokens expire after **30 minutes** by default.

## Using Access Tokens

### Authorization Header

Include the access token in the `Authorization` header for all protected endpoints:

```http
GET /api/v1/status/123e4567-e89b-12d3-a456-426614174000 HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Header Format**:
```
Authorization: Bearer <access_token>
```

### Example Implementations

#### cURL
```bash
curl -X GET "http://localhost:8000/api/v1/process" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "prompt": "Extract headings"}'
```

#### Python (requests)
```python
import requests

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

response = requests.post(
    "http://localhost:8000/api/v1/process",
    headers=headers,
    json={
        "url": "https://example.com",
        "prompt": "Extract all headings"
    }
)
```

#### JavaScript (fetch)
```javascript
const response = await fetch('http://localhost:8000/api/v1/process', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    url: 'https://example.com',
    prompt: 'Extract all headings'
  })
});
```

#### Python (httpx - async)
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/process",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"url": "https://example.com", "prompt": "Extract headings"}
    )
```

## Token Management

### Token Expiration

- **Default Expiration**: 30 minutes
- **Configuration**: Set via `ACCESS_TOKEN_EXPIRE_MINUTES` environment variable
- **Behavior**: Expired tokens return `401 Unauthorized`

### Token Refresh Strategy

Since tokens are stateless and expire after 30 minutes, implement one of these strategies:

#### 1. Proactive Refresh (Recommended)
```python
import time
from datetime import datetime, timedelta

class AuthClient:
    def __init__(self):
        self.access_token = None
        self.token_expires_at = None
    
    def login(self, username, password):
        response = requests.post(
            f"{self.base_url}/auth/token",
            data={"username": username, "password": password}
        )
        self.access_token = response.json()["access_token"]
        # Token expires in 30 minutes
        self.token_expires_at = datetime.now() + timedelta(minutes=30)
    
    def ensure_valid_token(self):
        """Refresh token if it expires in less than 5 minutes"""
        if not self.token_expires_at or \
           datetime.now() >= self.token_expires_at - timedelta(minutes=5):
            self.login(self.username, self.password)
    
    def make_request(self, method, endpoint, **kwargs):
        self.ensure_valid_token()
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f"Bearer {self.access_token}"
        kwargs['headers'] = headers
        return requests.request(method, f"{self.base_url}{endpoint}", **kwargs)
```

#### 2. Reactive Refresh (Simple)
```python
def make_authenticated_request(url, method='GET', **kwargs):
    """Make request, re-authenticate on 401"""
    headers = kwargs.get('headers', {})
    headers['Authorization'] = f"Bearer {access_token}"
    kwargs['headers'] = headers
    
    response = requests.request(method, url, **kwargs)
    
    if response.status_code == 401:
        # Token expired, re-authenticate
        new_token = login(username, password)
        headers['Authorization'] = f"Bearer {new_token}"
        response = requests.request(method, url, **kwargs)
    
    return response
```

### Storing Tokens Securely

#### Web Browsers
**DO NOT** store tokens in:
- `localStorage` (vulnerable to XSS attacks)
- `sessionStorage` (same XSS vulnerability)

**RECOMMENDED** approach:
1. **httpOnly Cookies**: Store token in secure, httpOnly cookie
2. **Memory**: Store token in JavaScript memory (lost on refresh)
3. **Secure Storage API**: Use browser's credential management API

#### Mobile Applications
- **iOS**: Use Keychain
- **Android**: Use EncryptedSharedPreferences or KeyStore
- **React Native**: Use `react-native-keychain`

#### Server-to-Server
- **Environment Variables**: Store credentials in environment
- **Secret Management**: Use AWS Secrets Manager, HashiCorp Vault, etc.

**Example (Environment Variables)**:
```python
import os
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("API_USERNAME")
PASSWORD = os.getenv("API_PASSWORD")
```

## Security Best Practices

### 1. Password Security

**Hashing Algorithm**: bcrypt with salt (work factor: 12)

**Password Requirements**:
- Minimum length: 8 characters (client-side validation recommended)
- Maximum length: 72 bytes (bcrypt limitation)
- Recommended: Mix of uppercase, lowercase, numbers, and symbols

**Password Validation Example**:
```python
import re

def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if len(password.encode('utf-8')) > 72:
        return False, "Password too long (max 72 bytes)"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain lowercase letters"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain uppercase letters"
    
    if not re.search(r"\d", password):
        return False, "Password must contain numbers"
    
    return True, "Password is valid"
```

### 2. HTTPS/TLS Enforcement

**ALWAYS** use HTTPS in production to prevent token interception:

```python
# Development
BASE_URL = "http://localhost:8000"

# Production
BASE_URL = "https://api.example.com"
```

### 3. Token Storage

**Never**:
- Log tokens in application logs
- Commit tokens to version control
- Share tokens between users
- Store tokens in URL parameters

**Always**:
- Use secure storage mechanisms
- Implement token rotation
- Clear tokens on logout
- Handle token expiration gracefully

### 4. Rate Limiting Compliance

Respect rate limits to avoid account suspension:

| Endpoint | Rate Limit |
|----------|------------|
| `/auth/register` | 5 requests/minute |
| `/auth/token` | 10 requests/minute |
| `/api/v1/process` | 10 requests/minute |

**Implement exponential backoff**:
```python
import time

def make_request_with_backoff(func, max_retries=3):
    """Retry with exponential backoff on rate limit"""
    for retry in range(max_retries):
        try:
            return func()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait_time = 2 ** retry
                print(f"Rate limited, waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise
    raise Exception("Max retries exceeded")
```

### 5. User Authorization

The API implements **user-scoped authorization**:
- Users can only access their own tasks
- Users can only manage their own scheduled jobs
- Attempting to access another user's resources returns `403 Forbidden`

## Password Requirements

### Technical Constraints

1. **Maximum Length**: 72 bytes (bcrypt limitation)
   - UTF-8 encoding means some characters consume multiple bytes
   - Example: "café" = 5 characters but 6 bytes

2. **Encoding**: UTF-8

### Recommended Client-Side Validation

```javascript
function validatePassword(password) {
  const errors = [];
  
  if (password.length < 8) {
    errors.push("Password must be at least 8 characters");
  }
  
  if (new Blob([password]).size > 72) {
    errors.push("Password too long (max 72 bytes)");
  }
  
  if (!/[a-z]/.test(password)) {
    errors.push("Must contain lowercase letters");
  }
  
  if (!/[A-Z]/.test(password)) {
    errors.push("Must contain uppercase letters");
  }
  
  if (!/\d/.test(password)) {
    errors.push("Must contain numbers");
  }
  
  if (!/[^a-zA-Z0-9]/.test(password)) {
    errors.push("Must contain special characters");
  }
  
  return {
    valid: errors.length === 0,
    errors: errors
  };
}
```

## Error Handling

### Common Authentication Errors

#### 401 Unauthorized

**Causes**:
- Token expired (>30 minutes old)
- Invalid token signature
- Token not provided
- User not found

**Response**:
```json
{
  "detail": "Could not validate credentials"
}
```

**Solution**: Re-authenticate with `/auth/token`

#### 403 Forbidden

**Cause**: User attempting to access another user's resources

**Response**:
```json
{
  "detail": "Not authorized to access this task"
}
```

**Solution**: Ensure you're accessing your own resources

#### 429 Rate Limit Exceeded

**Response**:
```json
{
  "error": "Too Many Requests"
}
```

**Solution**: Implement exponential backoff and respect rate limits

### Debugging Authentication Issues

#### 1. Verify Token Format
```python
import jwt

def decode_token(token):
    """Decode JWT without verification (for debugging only)"""
    try:
        header, payload, signature = token.split('.')
        decoded_payload = jwt.decode(
            token, 
            options={"verify_signature": False}
        )
        print(f"Username: {decoded_payload['sub']}")
        print(f"Expires: {decoded_payload['exp']}")
    except Exception as e:
        print(f"Invalid token: {e}")
```

#### 2. Check Token Expiration
```python
from datetime import datetime

def is_token_expired(token):
    """Check if token is expired"""
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp_timestamp = decoded['exp']
        return datetime.now().timestamp() > exp_timestamp
    except:
        return True
```

#### 3. Test Authentication Flow
```bash
# 1. Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test123!@#"}'

# 2. Login
curl -X POST http://localhost:8000/auth/token \
  -d "username=testuser&password=Test123!@#"

# 3. Use token (replace YOUR_TOKEN)
curl -X GET http://localhost:8000/api/v1/health \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Advanced Topics

### Custom Token Expiration

While the API defaults to 30 minutes, administrators can configure token lifetime:

```bash
# .env file
ACCESS_TOKEN_EXPIRE_MINUTES=60  # 1 hour
```

### Multi-Device Authentication

The stateless JWT approach means:
- Users can be logged in on multiple devices simultaneously
- Each login creates an independent token
- Logging out on one device doesn't affect other devices
- Token revocation is not supported (by design)

### Security Considerations for Production

1. **Secret Key Rotation**: Periodically rotate `SECRET_KEY`
2. **HTTPS Only**: Enforce TLS 1.2+ in production
3. **IP Whitelisting**: Consider IP restrictions for sensitive operations
4. **Audit Logging**: Log all authentication attempts
5. **Account Lockout**: Implement temporary lockout after failed attempts
6. **Two-Factor Authentication**: Consider adding 2FA for enhanced security

### Future Authentication Features

Planned enhancements:
- Refresh tokens for extended sessions
- OAuth2 integration (Google, GitHub)
- API keys for server-to-server authentication
- Role-based access control (RBAC)
- Session management and revocation

## Support

For authentication-related issues:

1. **Check Logs**: Review API logs for detailed error messages
2. **Verify Configuration**: Ensure `SECRET_KEY` is set correctly
3. **Test Locally**: Use Swagger UI at `/docs` for interactive testing
4. **Contact Support**: Email dadada.marchan@gmail.com

## Related Documentation

- [API Reference](./API_REFERENCE.md) - Complete endpoint documentation
- [Error Handling](./ERROR_HANDLING.md) - Error codes and troubleshooting
- [Rate Limiting](./RATE_LIMITING.md) - Rate limit details and strategies
- [Security Best Practices](./BEST_PRACTICES.md) - Comprehensive security guide
