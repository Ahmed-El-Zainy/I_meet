import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt_field(plaintext: str, key_hex: str) -> str:
    """AES-256-GCM encrypt a string. Returns base64(iv + ciphertext+tag)."""
    key = bytes.fromhex(key_hex)
    iv = os.urandom(12)          # 96-bit IV, fresh per call
    ct = AESGCM(key).encrypt(iv, plaintext.encode("utf-8"), None)
    return base64.b64encode(iv + ct).decode("ascii")


def decrypt_field(encoded: str, key_hex: str) -> str:
    """Inverse of encrypt_field."""
    raw = base64.b64decode(encoded)
    iv, ct = raw[:12], raw[12:]
    return AESGCM(bytes.fromhex(key_hex)).decrypt(iv, ct, None).decode("utf-8")


def encrypt_bytes(data: bytes, key_hex: str) -> tuple[bytes, str]:
    """Encrypt raw bytes. Returns (ciphertext_bytes, iv_hex)."""
    key = bytes.fromhex(key_hex)
    iv = os.urandom(12)
    ct = AESGCM(key).encrypt(iv, data, None)
    return ct, iv.hex()


def decrypt_bytes(ct: bytes, key_hex: str, iv_hex: str) -> bytes:
    """Decrypt raw bytes encrypted with encrypt_bytes."""
    return AESGCM(bytes.fromhex(key_hex)).decrypt(bytes.fromhex(iv_hex), ct, None)
