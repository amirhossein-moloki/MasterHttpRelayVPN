import os

# Base directories
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CORE_DIR)
PROJECT_ROOT = os.path.dirname(SRC_DIR)

# Data directory
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# MITM CA paths
CA_DIR = os.path.join(DATA_DIR, "ca")
CA_KEY_FILE = os.path.join(CA_DIR, "ca.key")
CA_CERT_FILE = os.path.join(CA_DIR, "ca.crt")

# Usage statistics database
USAGE_DB_PATH = os.path.join(DATA_DIR, "usage_stats.db")

def ensure_dirs():
    """Ensure all required directories exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(CA_DIR, exist_ok=True)
