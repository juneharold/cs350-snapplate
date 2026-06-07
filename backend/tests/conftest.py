import os
import re
import socket
import subprocess
import time
from pathlib import Path

import httpx
import pytest

_ROOT = Path(__file__).resolve().parent.parent
_LOG = Path("/tmp/snapplate_test_server.log")


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="session")
def server() -> str:
    port = _free_port()
    env = {
        **os.environ,
        "ALGORITHM_PROVIDER": "deterministic",
    }
    log = _LOG.open("w")
    proc = subprocess.Popen(
        [
            str(_ROOT / ".venv/bin/python"),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "info",
        ],
        cwd=str(_ROOT),
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(40):
        try:
            if httpx.get(f"{base}/health", timeout=1).status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError("server did not start")
    yield base
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture
def client(server: str):
    with httpx.Client(base_url=server, timeout=30) as c:
        yield c


def auth_headers(client: httpx.Client, email: str) -> dict:
    """Sign in via magic-link → verify, return Authorization headers."""
    client.post("/v1/auth/magic-link", json={"email": email})
    tokens = re.findall(r"token=([A-Za-z0-9_-]+)", _LOG.read_text())
    token = tokens[-1]
    r = client.post("/v1/auth/verify", json={"token": token})
    jwt = r.json()["response"]["access_token"]
    return {"Authorization": f"Bearer {jwt}"}
