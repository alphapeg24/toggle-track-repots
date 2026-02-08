from datetime import datetime, timezone

print("Hello from GitHub Actions!")
print("UTC now:", datetime.now(timezone.utc).isoformat())
