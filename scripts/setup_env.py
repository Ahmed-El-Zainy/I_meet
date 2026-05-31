"""Generate secrets and JWT tokens for .env (run once after clone)."""
from __future__ import annotations

import re
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
EXAMPLE_PATH = ROOT / ".env.example"


def _set(content: str, key: str, value: str) -> str:
    pattern = rf"^{re.escape(key)}=.*$"
    line = f"{key}={value}"
    if re.search(pattern, content, flags=re.MULTILINE):
        return re.sub(pattern, line, content, count=1, flags=re.MULTILINE)
    return content.rstrip() + "\n" + line + "\n"


def main() -> None:
    if not ENV_PATH.exists():
        ENV_PATH.write_text(EXAMPLE_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    content = ENV_PATH.read_text(encoding="utf-8")

    if "<hex-string>" in content or re.search(r"FIELD_ENCRYPTION_KEY=<", content):
        content = _set(content, "FIELD_ENCRYPTION_KEY", secrets.token_hex(32))
    if re.search(r"FILE_ENCRYPTION_KEY=<", content):
        content = _set(content, "FILE_ENCRYPTION_KEY", secrets.token_hex(32))
    if re.search(r"JWT_SECRET_KEY=<", content):
        content = _set(content, "JWT_SECRET_KEY", secrets.token_urlsafe(32))
    if re.search(r"MYSQL_PASSWORD=<", content):
        content = _set(content, "MYSQL_PASSWORD", secrets.token_urlsafe(16))
    if re.search(r"MYSQL_ROOT_PASSWORD=<", content):
        content = _set(content, "MYSQL_ROOT_PASSWORD", secrets.token_urlsafe(16))

    # CPU defaults for Docker without GPU passthrough
    if "WHISPER_DEVICE=cuda" in content:
        content = _set(content, "WHISPER_DEVICE", "cpu")
    if "EMBEDDING_DEVICE=cuda" in content:
        content = _set(content, "EMBEDDING_DEVICE", "cpu")
    if "WHISPER_MODEL=large-v3" in content:
        content = _set(content, "WHISPER_MODEL", "medium")

    ENV_PATH.write_text(content, encoding="utf-8")

    # Generate JWT tokens only if placeholders remain
    if "<jwt-token" in content.lower():
        import os
        for line in content.splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

        from src.security.auth import create_token

        token_a = create_token("client_a")
        token_b = create_token("client_b")
        content = _set(content, "CLIENT_A_TOKEN", token_a)
        content = _set(content, "CLIENT_B_TOKEN", token_b)
        ENV_PATH.write_text(content, encoding="utf-8")

    print("Updated .env with generated keys and JWT tokens.")
    print("Set OPENAI_API_KEY and HF_TOKEN if not already configured.")


if __name__ == "__main__":
    main()
