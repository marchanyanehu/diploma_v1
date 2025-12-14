# API Versioning and Changelog

## Overview

This document describes the API versioning strategy, backward compatibility guarantees, and tracks changes across API versions.

## Table of Contents

- [Versioning Strategy](#versioning-strategy)
- [Current Version](#current-version)
- [Backward Compatibility](#backward-compatibility)
- [Breaking Changes Policy](#breaking-changes-policy)
- [Deprecation Policy](#deprecation-policy)
- [Version Migration Guide](#version-migration-guide)
- [Changelog](#changelog)

## Versioning Strategy

### URL-Based Versioning

The API uses **URL path versioning** for clear, explicit version identification:

```
https://api.example.com/api/v1/process
                           ^^^
                           Version identifier
```

**Benefits**:
- Clear and explicit
- Easy to understand and implement
- Simple routing
- Version-specific documentation

### Version Format

Versions follow the format: `v{MAJOR}`

- `v1`: Current stable version
- `v2`: Future version (when breaking changes are introduced)

### Versioning Principles

1. **Semantic Versioning Spirit**: While we use `v{MAJOR}` in URLs, changes follow semantic versioning principles
2. **Backward Compatibility**: Non-breaking changes are added to existing versions
3. **Deprecation Warnings**: Features are deprecated before removal
4. **Migration Period**: Overlapping version support during transitions

## Current Version

### Version 1.0.0 (v1)

**Release Date**: December 2025

**Status**: Stable

**Base URL**: `/api/v1`

**Features**:
- User authentication (JWT)
- Task creation and management
- Scheduled jobs
- Status tracking
- Rate limiting
- Input sanitization

**Supported Until**: At least December 2026 (minimum 12 months)

## Backward Compatibility

### What is Considered Backward Compatible

The following changes are **NOT considered breaking** and may be added to v1:

#### 1. Adding New Endpoints
```
✓ Adding /api/v1/new-feature
✓ Adding /api/v1/users/{id}/preferences
```

#### 2. Adding Optional Fields to Requests
```json
// Before
{
  "url": "https://example.com",
  "prompt": "Extract data"
}

// After (backward compatible)
{
  "url": "https://example.com",
  "prompt": "Extract data",
  "options": {              // ← New optional field
    "cache": true
  }
}
```

#### 3. Adding New Fields to Responses
```json
// Before
{
  "task_id": "abc-123",
  "status": "SUCCESS"
}

// After (backward compatible)
{
  "task_id": "abc-123",
  "status": "SUCCESS",
  "estimated_cost": 0.05    // ← New field
}
```

#### 4. Adding New Optional Headers
```http
X-Request-Priority: high   ← New optional header
```

#### 5. Adding New Status Codes for New Scenarios
```
200 OK (existing)
201 Created (new, for different endpoint)
```

#### 6. Adding New Error Types
```json
{
  "error": "New Error Type",
  "message": "Description"
}
```

### What is Considered Breaking

The following changes are **breaking** and require a new API version:

#### 1. Removing Endpoints
```
✗ Removing /api/v1/deprecated-endpoint
```

#### 2. Removing Request/Response Fields
```json
// Breaking: Removing "message" field
{
  "task_id": "abc-123",
  "status": "SUCCESS"
  // "message" removed ← Breaking!
}
```

#### 3. Changing Required Fields
```json
// Breaking: Making optional field required
{
  "url": "https://example.com",
  "prompt": "Extract data",
  "format": "json"  // ← Now required (was optional)
}
```

#### 4. Changing Field Types
```json
// Breaking: Changing type
{
  "task_id": 123,      // ← Was string, now integer
  "status": "SUCCESS"
}
```

#### 5. Renaming Fields
```json
// Breaking: Renaming field
{
  "id": "abc-123",     // ← Renamed from "task_id"
  "status": "SUCCESS"
}
```

#### 6. Changing Authentication Mechanism
```
✗ Changing from JWT to OAuth2 without supporting both
```

#### 7. Changing URL Structure
```
✗ Moving from /api/v1/process to /api/v1/tasks/create
```

## Breaking Changes Policy

### Introduction of Breaking Changes

When breaking changes are necessary:

1. **New Version Released**: Create v2 with breaking changes
2. **Parallel Support**: Both v1 and v2 supported simultaneously
3. **Deprecation Notice**: v1 marked as deprecated with end-of-life date
4. **Migration Period**: Minimum 6-12 months for migration
5. **Sunset**: v1 removed after migration period

### Timeline Example

```
Month 0:  v2 released, v1 still supported
Month 1:  v1 marked deprecated
Month 6:  v1 sunset warning (6 months remaining)
Month 9:  v1 sunset warning (3 months remaining)
Month 12: v1 removed (sunset)
```

### Communication Channels

Breaking changes announced via:
1. **API Response Headers**: `X-API-Deprecation` header
2. **Documentation**: Updated versioning page
3. **Email**: Direct notification to registered users
4. **Status Page**: Public announcements
5. **Changelog**: Detailed version history

## Deprecation Policy

### Deprecation Process

1. **Announcement**
   - Feature marked as deprecated in documentation
   - Deprecation header added to responses
   - Minimum 6 months notice before removal

2. **Deprecation Headers**
   ```http
   X-API-Deprecated: true
   X-API-Sunset: 2026-12-31
   X-API-Deprecation-Info: https://docs.example.com/migration
   ```

3. **Migration Guide**
   - Detailed migration instructions published
   - Code examples provided
   - Alternative approaches documented

4. **Support During Transition**
   - Both old and new versions supported
   - Technical support for migration
   - Tools/scripts for migration (if applicable)

### Deprecation Example

**Scenario**: Deprecating a response field

```json
// Current (v1)
{
  "task_id": "abc-123",
  "status": "SUCCESS",
  "old_field": "value"  // ← To be removed in v2
}

// Deprecation phase (v1 with warning)
Headers:
X-API-Deprecated-Fields: old_field
X-API-Sunset-Fields: old_field=2026-12-31

Response:
{
  "task_id": "abc-123",
  "status": "SUCCESS",
  "old_field": "value",       // ← Still present
  "new_field": "value"        // ← New field available
}

// Future (v2)
{
  "task_id": "abc-123",
  "status": "SUCCESS",
  "new_field": "value"        // ← Only new field
}
```

## Version Migration Guide

### Migrating from v1 to v2 (When Available)

**Note**: v2 is not yet released. This section will be updated when v2 is available.

#### Planned Changes for v2

Potential breaking changes being considered:

1. **Authentication**
   - Add OAuth2 support alongside JWT
   - Longer token expiration options

2. **Response Format**
   - Consistent error format
   - Standardized pagination

3. **Rate Limiting**
   - Per-user limits instead of per-IP
   - Tier-based limits

4. **New Features**
   - Webhook notifications
   - Batch operations
   - Improved filtering

#### Migration Checklist

When v2 is released:

- [ ] Review v2 changelog
- [ ] Test v2 endpoints in development
- [ ] Update client code
- [ ] Update error handling
- [ ] Update tests
- [ ] Deploy to staging
- [ ] Monitor for issues
- [ ] Deploy to production
- [ ] Verify all functionality
- [ ] Remove v1 dependencies

## Changelog

### Version 1.0.0 (2025-12-14)

**Initial Release**

**Features**:
- ✨ User registration and authentication
- ✨ JWT-based authentication with 30-minute expiration
- ✨ Task creation endpoint (`POST /api/v1/process`)
- ✨ Task status tracking (`GET /api/v1/status/{task_id}`)
- ✨ Task result retrieval (`GET /api/v1/result/{task_id}`)
- ✨ Scheduled jobs (cron-based)
- ✨ User activity endpoint
- ✨ Rate limiting (per-IP)
- ✨ Input sanitization (prompt injection protection)
- ✨ Correlation ID support for request tracing
- ✨ Health check endpoints
- ✨ OpenAPI specification

**Technical Stack**:
- FastAPI web framework
- PostgreSQL database
- Redis for caching and rate limiting
- Celery for async task processing
- JWT authentication
- bcrypt password hashing

**Rate Limits**:
- Registration: 5 requests/minute
- Login: 10 requests/minute
- Task creation: 10 requests/minute
- Global: 100 requests/minute

**Security**:
- JWT token authentication
- bcrypt password hashing
- Input sanitization
- Rate limiting
- CORS support

### Version 1.0.1 (Planned - Q1 2026)

**Enhancements**:
- 🚀 Performance optimization for cached parsers
- 🐛 Bug fixes for edge cases in regex generation
- 📝 Documentation improvements
- ⚡ Faster response times for status queries

**No Breaking Changes**

### Version 1.1.0 (Planned - Q2 2026)

**New Features** (Backward Compatible):
- ✨ Webhook notifications for task completion
- ✨ Task filtering and search
- ✨ Export results in multiple formats (JSON, CSV)
- ✨ Batch task creation
- ✨ Task tags and categorization

**No Breaking Changes**

### Version 2.0.0 (Planned - Q4 2026)

**Breaking Changes**:
- 🔧 Per-user rate limiting (instead of per-IP)
- 🔧 Standardized pagination format
- 🔧 Updated error response format
- 🔧 OAuth2 support (JWT still supported)
- 🔧 Renamed some response fields for consistency

**New Features**:
- ✨ Real-time WebSocket support
- ✨ Advanced filtering and querying
- ✨ Custom parser templates
- ✨ Multi-region support
- ✨ API usage analytics

**Migration Period**: 12 months (v1 supported until Q4 2027)

## Version Header

### Checking Current Version

```bash
curl -I https://api.example.com/api/v1/health
```

**Response Headers**:
```http
HTTP/1.1 200 OK
X-API-Version: 1.0.0
X-API-Supported-Versions: v1
```

### Future: Version Negotiation

When multiple versions exist:

```http
Accept-Version: v1
```

**Response**:
```http
X-API-Version: 1.0.0
X-API-Latest-Version: 2.0.0
```

## Best Practices for Version Management

### For API Consumers

1. **Explicit Versioning**
   ```python
   BASE_URL = "https://api.example.com/api/v1"  # ← Explicit version
   ```

2. **Monitor Deprecation Headers**
   ```python
   if 'X-API-Deprecated' in response.headers:
       logger.warning(f"Using deprecated API: {response.headers.get('X-API-Sunset')}")
   ```

3. **Test Before Migrating**
   - Test new version in staging
   - Gradually roll out to production
   - Monitor for issues

4. **Stay Updated**
   - Subscribe to changelog
   - Follow deprecation notices
   - Plan migrations early

### For API Maintainers

1. **Minimize Breaking Changes**
   - Prefer additive changes
   - Use optional fields
   - Support multiple formats

2. **Clear Communication**
   - Document all changes
   - Provide migration guides
   - Give advance notice

3. **Support Overlap**
   - Run multiple versions simultaneously
   - Provide migration tools
   - Offer technical support

## Version Support Matrix

| Version | Release Date | Status | EOL Date | Support Level |
|---------|--------------|--------|----------|---------------|
| v1.0.0  | 2025-12-14  | Stable | 2026-12+ | Full support  |
| v1.0.1  | 2026-Q1     | Planned| TBD      | -             |
| v1.1.0  | 2026-Q2     | Planned| TBD      | -             |
| v2.0.0  | 2026-Q4     | Planned| TBD      | -             |

**Support Levels**:
- **Full Support**: Active development, bug fixes, security updates
- **Maintenance**: Security updates only
- **Deprecated**: No updates, sunset date announced
- **Sunset**: No longer supported

## Contact and Support

For version-related questions:
- **Email**: dadada.marchan@gmail.com
- **Documentation**: [API Reference](./API_REFERENCE.md)
- **Changelog**: This document
- **Migration Help**: Contact support team

## Related Documentation

- [API Reference](./API_REFERENCE.md) - Current endpoint documentation
- [Integration Tutorial](./INTEGRATION_TUTORIAL.md) - Getting started
- [Best Practices](./BEST_PRACTICES.md) - Implementation guidelines
- [Breaking Changes Policy](#breaking-changes-policy) - Change management
