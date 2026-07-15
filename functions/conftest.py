import os

# Set default test environment variables before modules import config.py
os.environ.setdefault("PROJECT_ID", "test-project")
os.environ.setdefault("ZONE", "us-central1-a")
os.environ.setdefault("INSTANCE_NAME", "test-minecraft")
os.environ.setdefault("DNS_ZONE_NAME", "test-dns-zone")
os.environ.setdefault("DOMAIN_NAME", "mc.example.com")
os.environ.setdefault("DNS_PROVIDER", "google")
os.environ.setdefault("ADMIN_PASSCODE", "testpasscode")
os.environ.setdefault("WHITELIST_SECRET", "testsecret")
