"""
Encryption and secrets management module.

Provides secure encryption/decryption for sensitive data, secure key management,
and utilities for protecting data at rest and in transit.
"""

import base64
import hashlib
import os
import secrets
from typing import Any, Dict, Optional, Tuple

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..core.config import get_settings


class EncryptionError(Exception):
    """Encryption-related errors."""

    pass


class KeyManager:
    """Secure key management."""

    def __init__(self):
        self.settings = get_settings()
        self._master_key = None
        self._encryption_keys: Dict[str, bytes] = {}

    def get_master_key(self) -> bytes:
        """Get or generate master encryption key."""
        if self._master_key is None:
            # In production, load from secure key store (AWS KMS, Azure Key Vault, etc.)
            master_key_env = os.getenv("MASTER_ENCRYPTION_KEY")
            if master_key_env:
                self._master_key = base64.b64decode(master_key_env)
            else:
                # Generate new master key (for development only)
                self._master_key = secrets.token_bytes(32)
                if self.settings.environment == "development":
                    print(
                        f"Generated master key (save this!): {base64.b64encode(self._master_key).decode()}"
                    )

        return self._master_key

    def derive_key(self, context: str, salt: Optional[bytes] = None) -> bytes:
        """Derive encryption key from master key with context."""
        if context not in self._encryption_keys:
            master_key = self.get_master_key()

            if salt is None:
                salt = hashlib.sha256(context.encode()).digest()[:16]

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            self._encryption_keys[context] = kdf.derive(master_key)

        return self._encryption_keys[context]

    def generate_fernet_key(self, context: str) -> Fernet:
        """Generate Fernet key for symmetric encryption."""
        key = self.derive_key(context)
        fernet_key = base64.urlsafe_b64encode(key)
        return Fernet(fernet_key)

    def rotate_keys(self):
        """Rotate encryption keys (implement key rotation policy)."""
        # Clear cached keys to force regeneration
        self._encryption_keys.clear()
        # In production, implement proper key rotation with versioning


class SymmetricEncryption:
    """Symmetric encryption for data at rest."""

    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager

    def encrypt_data(self, data: str, context: str = "default") -> str:
        """Encrypt string data."""
        try:
            fernet = self.key_manager.generate_fernet_key(context)
            encrypted_bytes = fernet.encrypt(data.encode("utf-8"))
            return base64.b64encode(encrypted_bytes).decode("utf-8")
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {str(e)}")

    def decrypt_data(self, encrypted_data: str, context: str = "default") -> str:
        """Decrypt string data."""
        try:
            fernet = self.key_manager.generate_fernet_key(context)
            encrypted_bytes = base64.b64decode(encrypted_data.encode("utf-8"))
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode("utf-8")
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {str(e)}")

    def encrypt_file(self, file_path: str, context: str = "files") -> str:
        """Encrypt file and return path to encrypted file."""
        try:
            with open(file_path, "rb") as f:
                data = f.read()

            fernet = self.key_manager.generate_fernet_key(context)
            encrypted_data = fernet.encrypt(data)

            encrypted_path = f"{file_path}.encrypted"
            with open(encrypted_path, "wb") as f:
                f.write(encrypted_data)

            return encrypted_path
        except Exception as e:
            raise EncryptionError(f"File encryption failed: {str(e)}")

    def decrypt_file(self, encrypted_file_path: str, context: str = "files") -> str:
        """Decrypt file and return path to decrypted file."""
        try:
            with open(encrypted_file_path, "rb") as f:
                encrypted_data = f.read()

            fernet = self.key_manager.generate_fernet_key(context)
            decrypted_data = fernet.decrypt(encrypted_data)

            decrypted_path = encrypted_file_path.replace(".encrypted", ".decrypted")
            with open(decrypted_path, "wb") as f:
                f.write(decrypted_data)

            return decrypted_path
        except Exception as e:
            raise EncryptionError(f"File decryption failed: {str(e)}")


class AsymmetricEncryption:
    """Asymmetric encryption for key exchange and secure communication."""

    def __init__(self):
        self._private_key = None
        self._public_key = None

    def generate_key_pair(self) -> Tuple[bytes, bytes]:
        """Generate RSA key pair."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        self._private_key = private_key
        self._public_key = public_key

        return private_pem, public_pem

    def encrypt_with_public_key(self, data: str, public_key_pem: bytes) -> str:
        """Encrypt data with public key."""
        try:
            public_key = serialization.load_pem_public_key(public_key_pem)

            encrypted = public_key.encrypt(
                data.encode("utf-8"),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            return base64.b64encode(encrypted).decode("utf-8")
        except Exception as e:
            raise EncryptionError(f"Public key encryption failed: {str(e)}")

    def decrypt_with_private_key(self, encrypted_data: str, private_key_pem: bytes) -> str:
        """Decrypt data with private key."""
        try:
            private_key = serialization.load_pem_private_key(private_key_pem, password=None)

            encrypted_bytes = base64.b64decode(encrypted_data.encode("utf-8"))

            decrypted = private_key.decrypt(
                encrypted_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            return decrypted.decode("utf-8")
        except Exception as e:
            raise EncryptionError(f"Private key decryption failed: {str(e)}")


class SecureStorage:
    """Secure storage for sensitive configuration and data."""

    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager
        self.symmetric_crypto = SymmetricEncryption(key_manager)
        self._secure_store: Dict[str, str] = {}

    def store_secret(self, key: str, value: str, context: str = "secrets"):
        """Store encrypted secret."""
        encrypted_value = self.symmetric_crypto.encrypt_data(value, context)
        self._secure_store[f"{context}:{key}"] = encrypted_value

    def retrieve_secret(self, key: str, context: str = "secrets") -> Optional[str]:
        """Retrieve and decrypt secret."""
        encrypted_value = self._secure_store.get(f"{context}:{key}")
        if encrypted_value:
            return self.symmetric_crypto.decrypt_data(encrypted_value, context)
        return None

    def store_api_key(self, provider: str, api_key: str):
        """Store API key securely."""
        self.store_secret(f"api_key_{provider}", api_key, "api_keys")

    def retrieve_api_key(self, provider: str) -> Optional[str]:
        """Retrieve API key securely."""
        return self.retrieve_secret(f"api_key_{provider}", "api_keys")

    def list_stored_keys(self, context: str = None) -> list:
        """List stored keys (without values)."""
        if context:
            prefix = f"{context}:"
            return [
                key[len(prefix) :] for key in self._secure_store.keys() if key.startswith(prefix)
            ]
        return list(self._secure_store.keys())

    def delete_secret(self, key: str, context: str = "secrets"):
        """Delete stored secret."""
        full_key = f"{context}:{key}"
        if full_key in self._secure_store:
            del self._secure_store[full_key]


class EncryptionManager:
    """Main encryption manager orchestrating all encryption services."""

    def __init__(self):
        self.key_manager = KeyManager()
        self.symmetric_crypto = SymmetricEncryption(self.key_manager)
        self.asymmetric_crypto = AsymmetricEncryption()
        self.secure_storage = SecureStorage(self.key_manager)

        # Initialize with existing API keys if available
        self._migrate_existing_api_keys()

    def _migrate_existing_api_keys(self):
        """Migrate existing plaintext API keys to encrypted storage."""
        settings = get_settings()

        # Migrate API keys to secure storage
        if settings.openai_api_key and settings.openai_api_key != "your-openai-api-key-here":
            self.secure_storage.store_api_key("openai", settings.openai_api_key)

        if (
            settings.anthropic_api_key
            and settings.anthropic_api_key != "your-anthropic-api-key-here"
        ):
            self.secure_storage.store_api_key("anthropic", settings.anthropic_api_key)

        if settings.google_api_key and settings.google_api_key != "your-google-api-key-here":
            self.secure_storage.store_api_key("google", settings.google_api_key)

    def encrypt_sensitive_data(self, data: str, data_type: str = "general") -> str:
        """Encrypt sensitive data with appropriate context."""
        return self.symmetric_crypto.encrypt_data(data, data_type)

    def decrypt_sensitive_data(self, encrypted_data: str, data_type: str = "general") -> str:
        """Decrypt sensitive data with appropriate context."""
        return self.symmetric_crypto.decrypt_data(encrypted_data, data_type)

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key securely."""
        # First try secure storage
        api_key = self.secure_storage.retrieve_api_key(provider)

        # Fallback to environment variables for backwards compatibility
        if not api_key:
            env_key = f"{provider.upper()}_API_KEY"
            api_key = os.getenv(env_key)

            # If found in env, migrate to secure storage
            if api_key and api_key not in ["your-{provider}-api-key-here"]:
                self.secure_storage.store_api_key(provider, api_key)

        return api_key

    def hash_password_secure(self, password: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
        """Securely hash password with salt."""
        if salt is None:
            salt = secrets.token_bytes(32)

        # Use PBKDF2 with high iteration count
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )

        key = kdf.derive(password.encode("utf-8"))

        return (base64.b64encode(key).decode("utf-8"), base64.b64encode(salt).decode("utf-8"))

    def verify_password_secure(self, password: str, hashed: str, salt: str) -> bool:
        """Verify password against secure hash."""
        try:
            salt_bytes = base64.b64decode(salt.encode("utf-8"))
            expected_hash = base64.b64decode(hashed.encode("utf-8"))

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt_bytes,
                iterations=100000,
            )

            kdf.verify(password.encode("utf-8"), expected_hash)
            return True
        except Exception:
            return False

    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure random token."""
        return secrets.token_urlsafe(length)

    def secure_compare(self, a: str, b: str) -> bool:
        """Constant-time string comparison to prevent timing attacks."""
        return secrets.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


# Global encryption manager instance
encryption_manager = EncryptionManager()
