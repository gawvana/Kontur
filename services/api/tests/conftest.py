import os

# Test process only: these values never enter runtime deployment configuration.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "123456789:local-test-only-not-a-real-token")
os.environ.setdefault("JWT_SECRET", "local-test-only-" + "x" * 40)
os.environ.setdefault("DISABLE_RATE_LIMIT", "1")
