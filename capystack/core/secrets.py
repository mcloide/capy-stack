"""
Secrets management with encryption for CapyStack.

This module provides secure encryption and decryption of sensitive data
using Fernet symmetric encryption.

Author: Cristiano Diniz da Silva <cristiano@zyraeng.com>
"""

import base64
from cryptography.fernet import Fernet
from core.settings import get_config

config = get_config()


class SecretsManager:
    """Manage encrypted secrets."""
    
    def __init__(self):
        self.fernet = Fernet(config.FERNET_KEY.encode())
    
    def encrypt_secret(self, value: str) -> bytes:
        """Encrypt a secret value."""
        return self.fernet.encrypt(value.encode())
    
    def decrypt_secret(self, encrypted_value: bytes) -> str:
        """Decrypt a secret value."""
        return self.fernet.decrypt(encrypted_value).decode()
    
    def encrypt_secret_to_string(self, value: str) -> str:
        """Encrypt a secret and return as base64 string."""
        encrypted = self.encrypt_secret(value)
        return base64.b64encode(encrypted).decode()
    
    def decrypt_secret_from_string(self, encrypted_string: str) -> str:
        """Decrypt a secret from base64 string."""
        encrypted = base64.b64decode(encrypted_string.encode())
        return self.decrypt_secret(encrypted)


# Global instance
secrets_manager = SecretsManager()
