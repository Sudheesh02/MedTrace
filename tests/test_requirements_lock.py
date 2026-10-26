"""requirements.lock hygiene."""


def test_requirements_lock_pins_every_runtime_dependency_exactly():
    """The lock must stay installable on the Docker base (python 3.11): guard against unpinned or wheel-less pins."""
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parents[1]
    lock = [l.strip() for l in (root / "requirements.lock").read_text().splitlines() if l.strip() and not l.startswith("#")]
    assert lock and all(re.match(r"^[A-Za-z0-9_.-]+==\d", l) for l in lock)
    names = {l.split("==")[0].lower() for l in lock}
    reqs = {re.split(r"[<>=!~ ]", l.strip())[0].lower() for l in (root / "requirements.txt").read_text().splitlines() if l.strip() and not l.startswith("#")}
    assert reqs <= names, f"requirements.txt packages missing from lock: {reqs - names}"
    assert dict(l.split("==") for l in lock)["numpy"].startswith("2.4."), "numpy 2.5+ has no Python 3.11 wheels (Docker image)"
