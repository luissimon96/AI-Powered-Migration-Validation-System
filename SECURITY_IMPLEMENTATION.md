# Security Implementation Documentation

## Overview

This document outlines the comprehensive security implementation for the AI-Powered Migration Validation System. The security framework provides defense-in-depth protection with multiple layers of security controls.

## 🛡️ Security Architecture

### Core Security Components

1. **Input Validation & Sanitization** (`src/security/validation.py`, `src/security/schemas.py`)
2. **API Key Authentication & Authorization** (`src/security/api_keys.py`)
3. **Comprehensive Audit Logging** (`src/security/audit.py`)
4. **Security Middleware** (`src/api/middleware.py`)
5. **Database Security Models** (`src/database/security_models.py`)

## 🔐 API Key Authentication System

### Features
- **Secure Key Generation**: 256-bit keys with prefix `amvs_`
- **PBKDF2 Hashing**: Keys hashed with 100,000 iterations
- **Scope-Based Authorization**: Read-only, validation, admin, service scopes
- **Rate Limiting**: Per-key rate limits with customizable thresholds
- **Expiration Support**: Optional key expiration dates
- **Usage Tracking**: Last used timestamps and usage counters

### API Key Scopes

| Scope | Description | Permissions |
|-------|-------------|-------------|
| `read_only` | Read-only access | View validations, health checks |
| `validation` | Validation operations | Create/manage validations, file uploads |
| `admin` | Administrative access | Manage API keys, system stats |
| `service` | Service-to-service | Full system access for automation |

### Usage Example

```python
from src.security import require_validation_scope, get_api_key_metadata

@app.post("/api/v1/validation/migrate")
async def create_validation(
    api_key_metadata: APIKeyMetadata = Depends(require_validation_scope)
):
    # Endpoint automatically validates API key and required scope
    pass
```

## 🔍 Input Validation Framework

### Comprehensive Validation Rules

#### String Validation
- **Length Limits**: Configurable maximum lengths (default: 10,000 chars)
- **SQL Injection Protection**: Pattern detection for common SQL injection vectors
- **XSS Prevention**: Script tag and event handler detection
- **Path Traversal Protection**: Directory traversal pattern detection
- **Command Injection Prevention**: Shell metacharacter detection

#### File Upload Security
- **Magic Byte Validation**: MIME type detection using file headers
- **File Size Limits**: Configurable per-file and total size limits
- **Extension Whitelist**: Allowed file extensions for source code
- **Content Scanning**: Suspicious content pattern detection
- **Executable Detection**: Binary executable signature detection

#### Request Validation
- **Header Validation**: Security-focused header content validation
- **JSON Schema Validation**: Recursive JSON structure validation
- **URL Validation**: Scheme and format validation
- **Email Validation**: RFC-compliant email format validation

### Validation Schema Examples

```python
class MigrationValidationRequest(BaseModel):
    source_technology: str = Field(..., min_length=1, max_length=50)
    target_technology: str = Field(..., min_length=1, max_length=50)
    validation_scope: str = Field(..., min_length=1, max_length=50)
    timeout_seconds: int = Field(300, ge=30, le=3600)

    @validator('source_technology')
    def validate_technology(cls, v):
        security_validator = SecurityValidator()
        return security_validator.validate_string_input(v, "technology")
```

## 📊 Comprehensive Audit Logging

### Event Types Tracked

#### Authentication Events
- Login success/failure
- Token refresh/expiration
- Logout activities

#### API Key Events
- Key creation/revocation
- Key usage tracking
- Invalid key attempts
- Rate limit violations

#### Authorization Events
- Access granted/denied
- Permission escalation attempts
- Scope violations

#### Security Violations
- Input validation failures
- Attack pattern detection
- Suspicious activity
- Path traversal attempts

#### Data Access Events
- File uploads/downloads
- Data modifications
- Resource access

### Audit Log Structure

```python
class AuditEvent(BaseModel):
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    user_id: Optional[str]
    api_key_id: Optional[str]
    source_ip: Optional[str]
    user_agent: Optional[str]
    resource: Optional[str]
    action: str
    result: str
    details: Dict[str, Any]
    request_id: Optional[str]
    session_id: Optional[str]
```

### Usage Example

```python
from src.security import security_audit, AuditEventType, AuditSeverity

await security_audit.log_api_key_invalid(
    provided_key="amvs_invalid...",
    source_ip="192.168.1.100",
    user_agent="curl/7.68.0",
    request_id="req_123"
)
```

## 🛡️ Security Middleware

### Multi-Layer Protection

1. **Request ID Generation**: Unique tracking for all requests
2. **Client IP Extraction**: Proxy-aware IP detection
3. **Input Validation Pipeline**: Comprehensive request validation
4. **Attack Pattern Detection**: Real-time threat detection
5. **Audit Logging**: Automatic security event logging

### Attack Detection Patterns

```python
attack_patterns = {
    "sql_injection": [
        r"('|(\\'))|(;|--|\s+or\s+|\s+and\s+)",
        r"(union\s+select|insert\s+into|delete\s+from|drop\s+table)",
    ],
    "xss": [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
    ],
    "path_traversal": [
        r"\.\.[\\/]",
        r"[\\/]\.\.[\\/]",
    ],
    "command_injection": [
        r"[;&|`$\(\){}]",
        r"(rm\s|del\s|format\s|mkfs\s)",
    ]
}
```

## 🗄️ Database Security Models

### Security Tables

1. **API Keys** (`api_keys`): Secure key storage with metadata
2. **Audit Logs** (`audit_logs`): Comprehensive event logging
3. **File Uploads** (`file_uploads`): Upload tracking and validation
4. **Security Incidents** (`security_incidents`): Incident management
5. **Rate Limits** (`rate_limits`): Rate limiting tracking
6. **Compliance Logs** (`compliance_logs`): Regulatory compliance
7. **Security Metrics** (`security_metrics`): Aggregated metrics

### Indexing Strategy

- **Time-based**: Efficient audit log queries
- **User/API Key**: Fast access control lookups
- **IP Address**: Geographic and abuse detection
- **Event Type**: Security monitoring and alerting

## 🚨 Security Monitoring & Alerting

### Critical Event Detection

```python
async def _alert_critical_event(self, event: AuditEvent):
    """Alert on critical security events."""
    if event.severity == AuditSeverity.CRITICAL:
        # Production implementation would trigger:
        # - Email alerts
        # - Slack notifications
        # - SIEM integration
        # - Incident response workflows
        pass
```

### Security Metrics

- **Failed Authentication Attempts**: Brute force detection
- **API Key Violations**: Abuse pattern identification
- **Input Validation Failures**: Attack attempt tracking
- **File Upload Anomalies**: Malware upload detection

## 🔒 Security Headers

### Implemented Headers

```python
def create_security_headers() -> Dict[str, str]:
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
    }
```

## 📋 Security Configuration

### Environment Variables

```bash
# Security Settings
SECRET_KEY=your-256-bit-secret-key
MAX_UPLOAD_FILE_SIZE=10485760  # 10MB
MAX_UPLOAD_FILES_PER_REQUEST=20
RATE_LIMIT_PER_MINUTE=60

# Database Security
DB_ENCRYPT_SENSITIVE_DATA=true
DB_CONNECTION_POOL_SIZE=10
DB_CONNECTION_TIMEOUT=30

# Audit Logging
AUDIT_LOG_LEVEL=INFO
AUDIT_RETENTION_DAYS=90
SECURITY_INCIDENT_ALERT_EMAIL=security@company.com
```

## 🧪 Security Testing

### Test Coverage Areas

1. **Input Validation Tests**
   - SQL injection attempts
   - XSS payload validation
   - Path traversal prevention
   - File upload security

2. **Authentication Tests**
   - API key validation
   - Scope enforcement
   - Rate limiting
   - Expiration handling

3. **Audit Logging Tests**
   - Event creation
   - Query functionality
   - Retention policies
   - Alert triggering

### Example Security Test

```python
async def test_sql_injection_detection():
    """Test SQL injection pattern detection."""
    malicious_inputs = [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "admin'/**/OR/**/1=1/**/--"
    ]

    for payload in malicious_inputs:
        with pytest.raises(SecurityValidationError):
            security_validator.validate_string_input(payload, "test_field")
```

## 🚀 Deployment Security

### Production Checklist

- [ ] **Environment Variables**: All secrets in environment variables
- [ ] **HTTPS Only**: TLS 1.2+ with strong cipher suites
- [ ] **Database Encryption**: Encryption at rest enabled
- [ ] **Log Monitoring**: SIEM integration configured
- [ ] **Backup Security**: Encrypted backups with access controls
- [ ] **Network Security**: VPC/firewall rules configured
- [ ] **Container Security**: Minimal base images, non-root users
- [ ] **Dependency Scanning**: Regular vulnerability scans

### Security Monitoring

1. **Real-time Alerts**
   - Critical security events
   - Failed authentication spikes
   - Unusual API usage patterns

2. **Daily Reports**
   - Security metrics summary
   - Top attack sources
   - Failed validation attempts

3. **Weekly Reviews**
   - Security incident analysis
   - Access pattern review
   - Configuration compliance check

## 🆘 Incident Response

### Automatic Response Actions

1. **Rate Limiting**: Automatic IP/key blocking
2. **Account Lockout**: Temporary API key deactivation
3. **Audit Trail**: Complete event logging
4. **Alert Generation**: Immediate notification system

### Manual Response Procedures

1. **Incident Triage**: Severity assessment and classification
2. **Containment**: Isolate affected systems/accounts
3. **Investigation**: Analyze logs and determine impact
4. **Recovery**: Restore normal operations
5. **Post-Incident**: Document lessons learned

## 📚 Security Best Practices

### Development Guidelines

1. **Input Validation**: Validate all user inputs at multiple layers
2. **Least Privilege**: Grant minimum necessary permissions
3. **Defense in Depth**: Multiple security controls for each threat
4. **Fail Secure**: Default to denying access when errors occur
5. **Audit Everything**: Log all security-relevant events

### API Security

1. **Authentication Required**: No anonymous access to sensitive endpoints
2. **Scope Validation**: Verify permissions for each operation
3. **Rate Limiting**: Prevent abuse with request throttling
4. **Request Validation**: Validate all request parameters
5. **Response Sanitization**: Remove sensitive data from responses

## 🔄 Maintenance & Updates

### Regular Security Tasks

1. **API Key Rotation**: Encourage regular key rotation
2. **Log Cleanup**: Automated old log purging
3. **Security Updates**: Keep dependencies current
4. **Configuration Review**: Periodic security setting audits
5. **Penetration Testing**: Regular security assessments

### Security Metrics Tracking

- **Authentication Success Rate**: Monitor for anomalies
- **Input Validation Failure Rate**: Track attack attempts
- **API Key Usage Patterns**: Identify unusual activity
- **File Upload Rejection Rate**: Monitor for malware attempts

---

## ⚠️ Security Considerations

This implementation provides enterprise-grade security controls but should be customized based on your specific:

- **Threat Model**: Identify specific risks to your deployment
- **Compliance Requirements**: GDPR, HIPAA, SOX, etc.
- **Performance Requirements**: Balance security with performance needs
- **Operational Constraints**: Consider monitoring and maintenance overhead

Regular security reviews and updates are essential to maintain effectiveness against evolving threats.