import os

# Base paths
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.dirname(_THIS_DIR)
_PROJECT_ROOT = os.path.dirname(_SRC_DIR)

# Data directory
DATA_DIR = os.path.join(_PROJECT_ROOT, "data")

# CA certificate paths
CA_DIR = os.path.join(DATA_DIR, "ca")
CA_KEY_FILE = os.path.join(CA_DIR, "ca.key")
CA_CERT_FILE = os.path.join(CA_DIR, "ca.crt")
