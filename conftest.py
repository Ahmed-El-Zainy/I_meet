import os
import pytest

# Minimal env vars so modules can be imported without a running stack
os.environ.setdefault("FIELD_ENCRYPTION_KEY", "a" * 64)
os.environ.setdefault("FILE_ENCRYPTION_KEY", "b" * 64)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")
os.environ.setdefault("MYSQL_HOST", "localhost")
os.environ.setdefault("MYSQL_PORT", "3306")
os.environ.setdefault("MYSQL_DATABASE", "meeting_intelligence")
os.environ.setdefault("MYSQL_USER", "app_user")
os.environ.setdefault("MYSQL_PASSWORD", "password")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("QDRANT_HOST", "localhost")
os.environ.setdefault("QDRANT_PORT", "6333")
os.environ.setdefault("QDRANT_COLLECTION", "meetings")
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("OPENAI_API_KEY", "test")
