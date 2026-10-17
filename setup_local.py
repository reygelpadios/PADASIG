"""Create a local .env once, with a generated secret; never overwrite settings."""
import secrets
from pathlib import Path

root = Path(__file__).resolve().parent
destination = root / ".env"
if destination.exists():
    print(".env already exists; kept unchanged.")
else:
    content = (root / ".env.example").read_text()
    content = content.replace("replace-with-a-random-development-secret", secrets.token_urlsafe(50))
    destination.write_text(content)
    destination.chmod(0o600)
    print("Created local .env with a generated secret. Do not share or commit it.")
