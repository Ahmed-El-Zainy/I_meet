import os


def get_field_key() -> str:
    """Return the AES-256 hex key for database field encryption.

    In production, replace this with a call to AWS KMS or HashiCorp Vault.
    The key must be a 64-character hex string (32 bytes).
    """
    key = os.environ.get("FIELD_ENCRYPTION_KEY", "")
    if len(key) != 64:
        raise RuntimeError("FIELD_ENCRYPTION_KEY must be a 64-char hex string (32 bytes)")
    return key


def get_file_key() -> str:
    """Return the AES-256 hex key for PDF file encryption.

    In production, replace this with a call to AWS KMS or HashiCorp Vault.
    """
    key = os.environ.get("FILE_ENCRYPTION_KEY", "")
    if len(key) != 64:
        raise RuntimeError("FILE_ENCRYPTION_KEY must be a 64-char hex string (32 bytes)")
    return key
