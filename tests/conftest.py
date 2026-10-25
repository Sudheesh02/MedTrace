"""
Pytest global configuration and fixtures (tests/conftest.py).
Ensures unit and integration tests run offline with sample mode enabled by default.
"""

import os
import tempfile
import pytest

# Collection-time isolation: ensure SAMPLE_MODE=true and USE_ZETARIS=false
# before any test module (e.g. tests/test_api.py importing run.py) is imported.
os.environ.setdefault("SAMPLE_MODE", "true")
os.environ.setdefault("USE_ZETARIS", "false")
# Isolate persisted H-MEM officer memory so test runs never pollute logs/hmem_store.json (the real demo memory).
os.environ.setdefault("MEDTRACE_HMEM_FILE", os.path.join(tempfile.mkdtemp(prefix="medtrace_test_hmem_"), "hmem_store.json"))

def pytest_configure(config):
    """Enforce offline sample mode during test collection and configuration."""
    os.environ.setdefault("SAMPLE_MODE", "true")
    os.environ.setdefault("USE_ZETARIS", "false")

@pytest.fixture(autouse=True, scope="session")
def default_test_environment():
    """Forces SAMPLE_MODE=true and USE_ZETARIS=false across test sessions for complete isolation."""
    old_sample = os.environ.get("SAMPLE_MODE")
    old_zetaris = os.environ.get("USE_ZETARIS")
    old_out = os.environ.get("MEDTRACE_OUTPUT_DIR")

    test_out = tempfile.mkdtemp(prefix="medtrace_test_output_")
    os.environ["SAMPLE_MODE"] = "true"
    os.environ["USE_ZETARIS"] = "false"
    os.environ["MEDTRACE_OUTPUT_DIR"] = test_out

    yield

    if old_sample is not None:
        os.environ["SAMPLE_MODE"] = old_sample
    else:
        os.environ.pop("SAMPLE_MODE", None)

    if old_zetaris is not None:
        os.environ["USE_ZETARIS"] = old_zetaris
    else:
        os.environ.pop("USE_ZETARIS", None)

    if old_out is not None:
        os.environ["MEDTRACE_OUTPUT_DIR"] = old_out
    else:
        os.environ.pop("MEDTRACE_OUTPUT_DIR", None)
