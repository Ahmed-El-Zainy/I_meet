import pytest
from src.security.encryption import encrypt_field, decrypt_field, encrypt_bytes, decrypt_bytes

KEY = "a" * 64  # 32-byte hex key for testing


def test_field_roundtrip():
    plaintext = "Hello, مرحبا!"
    assert decrypt_field(encrypt_field(plaintext, KEY), KEY) == plaintext


def test_field_encrypted_is_not_plaintext():
    plaintext = "sensitive data"
    enc = encrypt_field(plaintext, KEY)
    assert plaintext not in enc
    assert len(enc) > 0


def test_field_different_iv_each_call():
    plaintext = "same text"
    assert encrypt_field(plaintext, KEY) != encrypt_field(plaintext, KEY)


def test_bytes_roundtrip():
    data = b"binary PDF content \x00\x01\x02"
    ct, iv_hex = encrypt_bytes(data, KEY)
    assert decrypt_bytes(ct, KEY, iv_hex) == data


def test_tampered_ciphertext_raises():
    enc = encrypt_field("test", KEY)
    import base64
    raw = bytearray(base64.b64decode(enc))
    raw[-1] ^= 0xFF  # flip last byte
    tampered = base64.b64encode(bytes(raw)).decode()
    with pytest.raises(Exception):
        decrypt_field(tampered, KEY)


def test_wrong_key_raises():
    enc = encrypt_field("test", KEY)
    wrong_key = "b" * 64
    with pytest.raises(Exception):
        decrypt_field(enc, wrong_key)
