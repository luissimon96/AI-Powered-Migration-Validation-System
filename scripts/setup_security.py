#!/usr/bin/env python3
"""Security setup script for AI-Powered Migration Validation System.

Configures security settings, generates keys, and validates the security setup.
"""

import base64
import os
import secrets
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from src.security.auth import AuthManager
    from src.security.config import get_security_config
    from src.security.encryption import EncryptionManager
except ImportError as e:
    print(f"Error importing security modules: {e}")
    print("Please ensure the security modules are properly installed.")
    sys.exit(1)


def generate_secure_keys():
    """Generate secure keys for the application."""
    print("🔐 Generating secure keys...")

    # Generate JWT secret key
    jwt_secret = secrets.token_urlsafe(32)

    # Generate master encryption key
    encryption_key = base64.b64encode(secrets.token_bytes(32)).decode()

    # Generate API keys (examples)
    api_keys = {
        "internal_api": secrets.token_urlsafe(32),
        "monitoring_key": secrets.token_urlsafe(16),
    }

    return {
        "JWT_SECRET_KEY": jwt_secret,
        "MASTER_ENCRYPTION_KEY": encryption_key,
        **{f"API_KEY_{k.upper()}": v for k, v in api_keys.items()},
    }


def create_security_env_file(keys):
    """Create security environment file."""
    print("📝 Creating security environment configuration...")

    env_path = Path(__file__).parent.parent / ".env.security"

    env_content = """# Security Configuration - AI-Powered Migration Validation System
# Generated automatically - DO NOT COMMIT TO VERSION CONTROL

# ═══════════════════════════════════════════════════════════
# AUTHENTICATION & JWT
# ═══════════════════════════════════════════════════════════

# JWT Secret Key (32+ characters)
JWT_SECRET_KEY={jwt_secret}

# Access token expiry (minutes)
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Refresh token expiry (days)
REFRESH_TOKEN_EXPIRE_DAYS=30

# ═══════════════════════════════════════════════════════════
# ENCRYPTION
# ═══════════════════════════════════════════════════════════

# Master encryption key (base64 encoded)
MASTER_ENCRYPTION_KEY={encryption_key}

# ═══════════════════════════════════════════════════════════
# SECURITY CONFIGURATION
# ═══════════════════════════════════════════════════════════

# Security level: LOW, MEDIUM, HIGH, CRITICAL
SECURITY_LEVEL=HIGH

# CORS origins (comma-separated)
CORS_ORIGINS=["https://localhost:3000","https://127.0.0.1:3000"]

# Enable security monitoring
ENABLE_SECURITY_MONITORING=true

# Enable rate limiting
ENABLE_RATE_LIMITING=true

# ═══════════════════════════════════════════════════════════
# API KEYS
# ═══════════════════════════════════════════════════════════

# Internal API key
{api_key_internal}

# Monitoring API key
{api_key_monitoring}

# ═══════════════════════════════════════════════════════════
# PRODUCTION OVERRIDES
# ═══════════════════════════════════════════════════════════

# Set these for production deployment:
# ENVIRONMENT=production
# API_HOST=0.0.0.0
# CORS_ORIGINS=["https://yourdomain.com"]
# HTTPS_ONLY=true
""".format(
        jwt_secret=keys["JWT_SECRET_KEY"],
        encryption_key=keys["MASTER_ENCRYPTION_KEY"],
        api_key_internal=f"API_KEY_INTERNAL={keys['API_KEY_INTERNAL']}",
        api_key_monitoring=f"API_KEY_MONITORING={keys['API_KEY_MONITORING']}",
    )

    with open(env_path, "w") as f:
        f.write(env_content)

    # Set secure permissions
    os.chmod(env_path, 0o600)

    print(f"✅ Security environment file created: {env_path}")
    print("⚠️  IMPORTANT: Do not commit this file to version control!")


def validate_security_setup():
    """Validate the security setup."""
    print("🔍 Validating security setup...")

    try:
        # Test encryption manager
        encryption_manager = EncryptionManager()
        test_data = "test_security_data"
        encrypted = encryption_manager.encrypt_sensitive_data(test_data)
        decrypted = encryption_manager.decrypt_sensitive_data(encrypted)
        assert decrypted == test_data
        print("✅ Encryption manager working correctly")

        # Test security config
        config = get_security_config()
        assert len(config.jwt_secret_key) >= 32
        print("✅ Security configuration validated")

        # Test auth manager
        AuthManager()
        print("✅ Authentication manager initialized")

        print("✅ All security components validated successfully!")
        return True

    except Exception as e:
        print(f"❌ Security validation failed: {e}")
        return False


def setup_default_admin():
    """Set up default admin user."""
    print("👤 Setting up default admin user...")

    try:
        AuthManager()

        # The AuthManager already creates a default admin
        # We just need to get the password that was printed
        print("✅ Default admin user created")
        print("📝 Check the console output above for the admin password")
        print("⚠️  Change the admin password immediately after first login!")

    except Exception as e:
        print(f"❌ Failed to setup admin user: {e}")


def create_security_checklist():
    """Create security deployment checklist."""
    print("📋 Creating security deployment checklist...")

    checklist_path = Path(__file__).parent.parent / "docs" / "SECURITY_CHECKLIST.md"

    checklist_content = """# Security Deployment Checklist

## Pre-Deployment Security Checklist

### ✅ Authentication & Authorization
- [ ] JWT secret key changed from default (32+ characters)
- [ ] Default admin password changed
- [ ] User roles properly configured
- [ ] Authentication endpoints tested
- [ ] Token expiry times appropriate for environment

### ✅ Encryption & Data Protection
- [ ] Master encryption key generated and secured
- [ ] API keys encrypted in storage
- [ ] HTTPS enforced in production
- [ ] TLS certificates valid and properly configured

### ✅ Input Validation & Sanitization
- [ ] File upload limits configured
- [ ] MIME type validation enabled
- [ ] Input sanitization tested
- [ ] XSS protection verified

### ✅ Rate Limiting & DDoS Protection
- [ ] Rate limits configured for all endpoints
- [ ] Rate limiting tested under load
- [ ] IP blocking configured if needed
- [ ] User-based rate limiting enabled

### ✅ Security Headers & CORS
- [ ] Security headers enabled
- [ ] CORS origins configured for production
- [ ] CSP policy appropriate for application
- [ ] HSTS enabled for HTTPS

### ✅ Monitoring & Logging
- [ ] Security event logging enabled
- [ ] Log rotation configured
- [ ] Monitoring alerts set up
- [ ] Incident response plan in place

### ✅ Dependencies & Updates
- [ ] Security dependencies installed
- [ ] Vulnerability scanning completed
- [ ] Dependencies up to date
- [ ] Security patches applied

### ✅ Environment Configuration
- [ ] Production environment variables set
- [ ] Development debug modes disabled
- [ ] Sensitive data not in version control
- [ ] Database connections secured

## Post-Deployment Verification

### ✅ Security Testing
- [ ] Authentication endpoints tested
- [ ] Authorization controls verified
- [ ] Rate limiting tested
- [ ] File upload security tested
- [ ] Security headers verified

### ✅ Monitoring Setup
- [ ] Security logs being generated
- [ ] Monitoring alerts functional
- [ ] Performance metrics available
- [ ] Error tracking configured

### ✅ Backup & Recovery
- [ ] Encryption keys backed up securely
- [ ] Database backups encrypted
- [ ] Recovery procedures tested
- [ ] Key rotation schedule set

## Emergency Contacts

- Security Team: security@company.com
- Operations Team: ops@company.com
- Emergency Hotline: +1-XXX-XXX-XXXX

---
Generated: {timestamp}
"""

    from datetime import datetime

    with open(checklist_path, "w") as f:
        f.write(checklist_content.format(timestamp=datetime.now().isoformat()))

    print(f"✅ Security checklist created: {checklist_path}")


def main():
    """Main setup function."""
    print("🚀 AI-Powered Migration Validation System - Security Setup")
    print("=" * 60)

    try:
        # Generate secure keys
        keys = generate_secure_keys()

        # Create security environment file
        create_security_env_file(keys)

        # Set environment variables for validation
        for key, value in keys.items():
            os.environ[key] = value

        # Validate security setup
        if not validate_security_setup():
            print("❌ Security setup validation failed!")
            sys.exit(1)

        # Setup default admin
        setup_default_admin()

        # Create security checklist
        create_security_checklist()

        print("\n" + "=" * 60)
        print("✅ Security setup completed successfully!")
        print("\n📋 Next Steps:")
        print("1. Review the generated .env.security file")
        print("2. Change the default admin password")
        print("3. Configure production environment variables")
        print("4. Review the security checklist in docs/SECURITY_CHECKLIST.md")
        print("5. Test the security features")
        print("\n⚠️  Security Reminders:")
        print("- Never commit .env.security to version control")
        print("- Regularly rotate encryption keys")
        print("- Monitor security logs")
        print("- Keep dependencies updated")

    except Exception as e:
        print(f"❌ Security setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
