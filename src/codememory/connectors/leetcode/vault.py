"""Credential vault for encrypted LeetCookie storage using keyring and Fernet encryption."""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

try:
    import keyring
    from cryptography.fernet import Fernet
    HAS_CRYPTO_DEPS = True
except ImportError:
    keyring = None  # type: ignore[assignment]
    Fernet = None  # type: ignore[assignment]
    HAS_CRYPTO_DEPS = False

from codememory.connectors.leetcode.errors import LeetCodeError

logger = logging.getLogger(__name__)

# Constants for keyring storage
KEYRING_SERVICE = "CodeMemory"
KEYRING_USERNAME_PREFIX = "leetcode_encrypted_key_"

# Default vault file path (will be used if keyring is unavailable for master key)
VAULT_FILE_PATH = "data/accounts/leetcode_vault.json"


class CredentialVaultError(LeetCodeError):
    """Errors related to credential vault operations."""
    pass


class CredentialVault:
    """
    Secure credential storage for LeetCode session cookies.

    Uses system keyring to store a master encryption key, and Fernet symmetric
    encryption to protect LEETCODE_SESSION and csrftoken credentials.
    """

    def __init__(self, account_identifier: str = "default", vault_file_path: str = VAULT_FILE_PATH):
        """
        Initialize the credential vault.

        Args:
            account_identifier: Identifier for the account (used to isolate credentials)
            vault_file_path: Path to store encrypted credentials (fallback if keyring unavailable)
        """
        self.account_identifier = account_identifier
        # Make vault file path account-specific if using default path
        if vault_file_path == VAULT_FILE_PATH:
            # Insert account identifier before the file extension
            base_path, ext = os.path.splitext(vault_file_path)
            self.vault_file_path = f"{base_path}_{account_identifier}{ext}"
        else:
            self.vault_file_path = vault_file_path
        self._fernet: Optional[Fernet] = None

        # Ensure the directory exists for the vault file
        os.makedirs(os.path.dirname(self.vault_file_path), exist_ok=True)

        # Initialize encryption if crypto deps are available
        if HAS_CRYPTO_DEPS and keyring is not None and Fernet is not None:
            try:
                self._initialize_encryption()
            except Exception as e:
                logger.warning("Failed to initialize encryption during vault initialization: %s", e)
        else:
            logger.warning("Cryptography dependencies not available. Credential vault will not function.")

    def _initialize_encryption(self) -> None:
        """Initialize or retrieve the master encryption key from keyring."""
        if not HAS_CRYPTO_DEPS or keyring is None or Fernet is None:
            self._fernet = None
            raise CredentialVaultError("Cryptography dependencies missing")
        try:
            # Construct account-specific keyring username
            keyring_username = f"{KEYRING_USERNAME_PREFIX}{self.account_identifier}"

            # Try to get existing master key from keyring
            master_key = keyring.get_password(KEYRING_SERVICE, keyring_username)

            if master_key is None:
                # Generate a new master key
                master_key = Fernet.generate_key()
                # Store it in keyring
                keyring.set_password(KEYRING_SERVICE, keyring_username, master_key.decode('utf-8'))
                logger.info("Generated and stored new master encryption key in keyring for account %s", self.account_identifier)
            else:
                logger.info("Retrieved master encryption key from keyring for account %s", self.account_identifier)
                # Convert string back to bytes if needed
                if isinstance(master_key, str):
                    master_key = master_key.encode('utf-8')

            # Initialize Fernet with the master key
            self._fernet = Fernet(master_key)

        except Exception as e:
            logger.error("Failed to initialize encryption for account %s: %s", self.account_identifier, e)
            self._fernet = None
            raise CredentialVaultError(f"Could not initialize encryption: {e}")

    def _encrypt(self, data: str) -> str:
        """
        Encrypt sensitive data using Fernet.

        Args:
            data: Plaintext string to encrypt

        Returns:
            Base64-encoded encrypted string

        Raises:
            CredentialVaultError: If encryption fails or crypto not available
        """
        if not self._fernet:
            raise CredentialVaultError("Encryption not available - missing dependencies")

        try:
            encrypted_bytes = self._fernet.encrypt(data.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error("Encryption failed")
            raise CredentialVaultError(f"Failed to encrypt data: {e}")

    def _decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data using Fernet.

        Args:
            encrypted_data: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string

        Raises:
            CredentialVaultError: If decryption fails or crypto not available
        """
        if not self._fernet:
            raise CredentialVaultError("Decryption not available - missing dependencies")

        try:
            decrypted_bytes = self._fernet.decrypt(encrypted_data.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error("Decryption failed")
            raise CredentialVaultError(f"Failed to decrypt data: {e}")

    def store(self, session: str, csrf_token: str) -> None:
        """
        Store LEETCODE_SESSION and csrftoken credentials securely.

        Args:
            session: LEETCODE_SESSION cookie value
            csrf_token: csrftoken cookie value

        Raises:
            CredentialVaultError: If storage fails
        """
        if not HAS_CRYPTO_DEPS:
            raise CredentialVaultError("Cannot store credentials - cryptography dependencies missing")

        try:
            # Encrypt both credentials
            encrypted_session = self._encrypt(session)
            encrypted_csrf = self._encrypt(csrf_token)

            # Prepare vault data
            vault_data = {
                "leetcode_session": encrypted_session,
                "csrftoken": encrypted_csrf,
                "version": "1.0"
            }

            # Try to store in keyring first, fall back to file
            try:
                keyring.set_password(
                    KEYRING_SERVICE,
                    f"{KEYRING_USERNAME_PREFIX}{self.account_identifier}_vault",
                    json.dumps(vault_data)
                )
                logger.info("Stored encrypted credentials in keyring for account %s", self.account_identifier)
            except Exception as keyring_error:
                # Include the OS/backend reason so keyring failures can be
                # diagnosed, while never logging the encrypted or plaintext
                # credential payload.
                logger.warning(
                    "Keyring storage failed for account %s (%s): %s",
                    self.account_identifier,
                    type(keyring_error).__name__,
                    keyring_error,
                )
                # Fall back to file storage
                with open(self.vault_file_path, 'w') as f:
                    json.dump(vault_data, f)
                logger.info(f"Stored encrypted credentials in file: {self.vault_file_path}")

        except Exception as e:
            logger.error(f"Failed to store credentials: {e}")
            raise CredentialVaultError(f"Could not store credentials: {e}")

    def retrieve(self) -> tuple[Optional[str], Optional[str]]:
        """
        Retrieve stored LEETCODE_SESSION and csrftoken credentials.

        Returns:
            Tuple of (session, csrf_token) or (None, None) if not found

        Raises:
            CredentialVaultError: If retrieval fails but credentials exist
        """
        if not HAS_CRYPTO_DEPS:
            raise CredentialVaultError("Cannot retrieve credentials - cryptography dependencies missing")

        try:
            # Try to get from keyring first
            vault_json = None
            try:
                vault_json = keyring.get_password(
                    KEYRING_SERVICE,
                    f"{KEYRING_USERNAME_PREFIX}{self.account_identifier}_vault"
                )
            except Exception:
                pass  # Keyring might not be available or entry might not exist

            # Fall back to file storage if keyring didn't have it
            if vault_json is None:
                try:
                    with open(self.vault_file_path, 'r') as f:
                        vault_json = json.load(f)
                    vault_json = json.dumps(vault_json)  # Convert back to JSON string for consistency
                except FileNotFoundError:
                    logger.info("No credential vault found")
                    return None, None
                except Exception as e:
                    logger.error(f"Failed to read credential vault file: {e}")
                    raise CredentialVaultError(f"Could not read credential vault: {e}")

            # Parse vault data
            vault_data = json.loads(vault_json)

            # Decrypt credentials
            encrypted_session = vault_data.get("leetcode_session")
            encrypted_csrf = vault_data.get("csrftoken")

            if encrypted_session is None and encrypted_csrf is None:
                return None, None

            session = self._decrypt(encrypted_session) if encrypted_session else None
            csrf_token = self._decrypt(encrypted_csrf) if encrypted_csrf else None

            return session, csrf_token

        except CredentialVaultError:
            raise  # Re-raise vault-specific errors
        except Exception as e:
            logger.error(f"Failed to retrieve credentials: {e}")
            raise CredentialVaultError(f"Could not retrieve credentials: {e}")

    def revoke(self) -> None:
        """
        Remove stored credentials from both keyring and file storage.
        """
        try:
            # Remove from keyring
            if keyring is not None:
                try:
                    keyring.delete_password(KEYRING_SERVICE, f"{KEYRING_USERNAME_PREFIX}{self.account_identifier}_vault")
                    logger.info("Removed credentials from keyring for account %s", self.account_identifier)
                except Exception as e:
                    logger.warning("Failed to delete from keyring for account %s: %s", self.account_identifier, e)

            # Remove file if it exists
            if os.path.exists(self.vault_file_path):
                os.remove(self.vault_file_path)
                logger.info(f"Removed credential vault file: {self.vault_file_path}")

        except Exception as e:
            logger.error("Error during credential revocation")
            # Don't raise - best effort cleanup

    def validate(self, session: str, csrf_token: str) -> bool:
        """
        Validate that credentials appear to be valid format.
        Note: Actual validation requires making a request to LeetCode.

        Args:
            session: LEETCODE_SESSION cookie value
            csrf_token: csrftoken cookie value

        Returns:
            True if credentials appear valid, False otherwise
        """
        # Basic format validation - session should be reasonably long
        if not session or len(session) < 10:
            return False

        # CSRF token should also be reasonably sized
        if not csrf_token or len(csrf_token) < 10:
            return False

        return True
