"""Opt-in real single-worker HTTP acceptance (one full 50-second idle poll)."""

import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import pytest


@pytest.mark.skipif(
    os.getenv("CODIFICA_HTTP_ACCEPTANCE") != "1",
    reason="Run explicitly: real 50-second HTTP acceptance",
)
def test_real_http_full_idle_wakeup_and_process_restart(tmp_path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    environment = {
        **os.environ,
        "CODIFICA_DATABASE_PATH": str(tmp_path / "live.sqlite"),
        "CODIFICA_SECRET_KEY": secrets.token_urlsafe(40),
        "CODIFICA_ORIGIN": origin,
        "CODIFICA_DEV_AUTH": "1",
        "CODIFICA_PILOT_EMAILS": "owner@example.com",
    }

    def start():
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "server.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--no-access-log",
            ],
            cwd=Path(__file__).resolve().parents[1],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(100):
            try:
                if httpx.get(origin + "/health", timeout=0.2).status_code == 200:
                    return process
            except httpx.HTTPError:
                pass
            if process.poll() is not None:
                pytest.fail("Local API process exited before becoming healthy")
            time.sleep(0.05)
        process.terminate()
        process.wait(timeout=5)
        pytest.fail("Local API process did not become healthy")

    process = start()
    try:
        with httpx.Client(base_url=origin, timeout=60) as browser:
            login = browser.post(
                "/api/v1/auth/dev-login",
                json={"email": "owner@example.com", "name": "Owner"},
            ).json()
            browser.headers.update(
                {"Origin": origin, "X-CSRF-Token": login["csrfToken"]}
            )
            channel = browser.post(
                "/api/v1/channels", json={"name": "Real HTTP acceptance"}
            ).json()["id"]
            invitation = browser.post(
                f"/api/v1/channels/{channel}/invites", json={"kind": "agent"}
            ).json()
            secret = invitation["url"].rsplit("/", 1)[-1]
            joined = browser.post(
                f"/api/v1/invites/{secret}/join",
                json={"name": "Transport test", "requestId": str(uuid4())},
            ).json()
            with httpx.Client(
                base_url=origin,
                headers={"Authorization": "Bearer " + joined["token"]},
                timeout=60,
            ) as agent:
                path = f"/api/v1/channels/{channel}/activity"
                started = time.monotonic()
                response = agent.get(path, params={"wait": 50})
                idle = time.monotonic() - started
                assert response.status_code == 200 and response.json() == {
                    "batchId": None,
                    "activities": [],
                    "remainingUnread": 0,
                }
                assert 49 <= idle < 56
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(agent.get, path, params={"wait": 50})
                    time.sleep(0.2)
                    sent_at = time.monotonic()
                    posted = browser.post(
                        f"/api/v1/channels/{channel}/messages",
                        json={
                            "body": "Wake the held HTTP request",
                            "mentions": [joined["participant"]["id"]],
                            "requestId": str(uuid4()),
                        },
                    )
                    assert posted.status_code == 200
                    delivery = future.result(timeout=3)
                    wake = time.monotonic() - sent_at
                assert (
                    delivery.status_code == 200
                    and delivery.json()["activities"][0]["id"] == posted.json()["id"]
                )
                assert wake < 2
                batch = delivery.json()
                process.terminate()
                process.wait(timeout=5)
                process = start()
                assert agent.get(path, params={"wait": 0}).json() == batch
                assert browser.get("/api/v1/me").status_code == 200
                print(
                    f"HTTP acceptance: idle={idle:.3f}s, wake={wake:.3f}s, outstanding batch + cookie session survived process restart"
                )
    finally:
        process.terminate()
        process.wait(timeout=5)
