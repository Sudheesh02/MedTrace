"""
Pytest global configuration and fixtures (tests/conftest.py).
Ensures unit and integration tests run offline with sample mode enabled by default.
"""

import os
import pytest

@pytest.fixture(autouse=True, scope="session")
def default_test_environment():
    """Forces SAMPLE_MODE=true and USE_ZETARIS=false across test sessions for complete isolation."""
    old_sample = os.environ.get("SAMPLE_MODE")
    old_zetaris = os.environ.get("USE_ZETARIS")

    os.environ["SAMPLE_MODE"] = "true"
    os.environ["USE_ZETARIS"] = "false"

    yield

    if old_sample is not None:
        os.environ["SAMPLE_MODE"] = old_sample
    else:
        os.environ.pop("SAMPLE_MODE", None)

    if old_zetaris is not None:
        os.environ["USE_ZETARIS"] = old_zetaris
    else:
        os.environ.pop("USE_ZETARIS", None)
