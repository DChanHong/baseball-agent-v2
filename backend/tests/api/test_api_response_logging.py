from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.api_response_logging import ApiResponseLoggingMiddleware


def test_api_response_logging_persists_json_response(tmp_path):
    app = FastAPI()
    app.add_middleware(
        ApiResponseLoggingMiddleware,
        enabled=True,
        log_dir=str(tmp_path),
        max_body_bytes=1_000_000,
    )

    @app.post("/echo")
    async def echo(payload: dict[str, str]):
        return {"received": payload}

    response = TestClient(app).post(
        "/echo",
        json={"message": "hello"},
        headers={"authorization": "Bearer secret"},
    )

    assert response.status_code == 200
    assert response.json() == {"received": {"message": "hello"}}

    [log_file] = list(tmp_path.glob("*.json"))
    record = json.loads(log_file.read_text(encoding="utf-8"))

    assert record["request"]["method"] == "POST"
    assert record["request"]["path"] == "/echo"
    assert record["request"]["headers"]["authorization"] == "[REDACTED]"
    assert record["request"]["body"] == {"message": "hello"}
    assert record["response"]["status_code"] == 200
    assert record["response"]["body"] == {"received": {"message": "hello"}}
