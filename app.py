#!/usr/bin/env python3
"""Local xyock + Ollama server.

Place this file in the same folder as xyock.html and your static assets.
Run with: python3 app.py
Then open: http://127.0.0.1:8000/xyock.html
"""

from __future__ import annotations

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

HOST = "127.0.0.1"
PORT = 8000
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen3.5:4b"
ROOT = Path(__file__).resolve().parent
MAX_BODY_BYTES = 1_000_000

# Ensure common web file types get sensible content types.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/manifest+json", ".webmanifest")


class Handler(BaseHTTPRequestHandler):
    server_version = "xyock-local/1.0"

    def _send_json(self, status: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        # Same-origin local use does not need CORS; support preflight cleanly if used.
        self.send_response(204)
        self.send_header("Allow", "GET, HEAD, POST, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        path = unquote(parsed.path)

        if path == "/health":
            self._send_json(200, {"ok": True, "model": MODEL})
            return

        if path == "/":
            # Prefer the AI app's page if present; otherwise serve a standard homepage.
            preferred = ROOT / "xyock.html"
            path = "/xyock.html" if preferred.is_file() else "/index.html"

        # Keep requests inside the folder containing app.py.
        candidate = (ROOT / path.lstrip("/")).resolve()
        try:
            candidate.relative_to(ROOT)
        except ValueError:
            self._send_json(403, {"error": "Forbidden"})
            return

        if not candidate.is_file():
            self._send_json(404, {"error": f"File not found: {path}"})
            return

        content_type, _ = mimetypes.guess_type(str(candidate))
        content_type = content_type or "application/octet-stream"
        if content_type.startswith("text/") or content_type in ("application/javascript", "application/manifest+json"):
            content_type += "; charset=utf-8"

        data = candidate.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_HEAD(self) -> None:
        # Simple HEAD equivalent for static assets.
        parsed = urlsplit(self.path)
        path = unquote(parsed.path)
        if path == "/":
            path = "/xyock.html" if (ROOT / "xyock.html").is_file() else "/index.html"
        candidate = (ROOT / path.lstrip("/")).resolve()
        try:
            candidate.relative_to(ROOT)
        except ValueError:
            self.send_error(403)
            return
        if not candidate.is_file():
            self.send_error(404)
            return
        content_type, _ = mimetypes.guess_type(str(candidate))
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(candidate.stat().st_size))
        self.end_headers()

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/ask":
            self._send_json(404, {"error": "Unknown API endpoint. Use POST /ask."})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length"})
            return
        if length <= 0 or length > MAX_BODY_BYTES:
            self._send_json(413 if length > MAX_BODY_BYTES else 400, {"error": "Request body is empty or too large."})
            return

        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"error": "Request body must be valid JSON."})
            return

        question = payload.get("q") if isinstance(payload, dict) else None
        if not isinstance(question, str) or not question.strip():
            self._send_json(400, {"error": "질문을 입력해 주세요."})
            return
        question = question.strip()[:12000]

        request_body = json.dumps({
            "model": MODEL,
            "messages": [{"role": "user", "content": question}],
            "stream": False,
        }).encode("utf-8")
        request = Request(
            OLLAMA_CHAT_URL,
            data=request_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=180) as response:
                result = json.loads(response.read().decode("utf-8"))
            answer = result.get("message", {}).get("content", "")
            if not isinstance(answer, str) or not answer.strip():
                self._send_json(502, {"error": "Ollama가 빈 답변을 반환했습니다."})
                return
            self._send_json(200, {"answer": answer.strip()})
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            self._send_json(502, {"error": f"Ollama 오류 ({exc.code}): {detail}"})
        except (URLError, TimeoutError, ConnectionError) as exc:
            self._send_json(503, {
                "error": "Ollama 서버에 연결할 수 없습니다. Ollama가 실행 중인지와 qwen3.5:4b 모델 설치를 확인해 주세요."
            })
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(502, {"error": "Ollama에서 올바른 JSON 응답을 받지 못했습니다."})

    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def main() -> None:
    try:
        server = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as exc:
        raise SystemExit(
            f"포트 {PORT}를 열 수 없습니다. 다른 서버가 실행 중인지 확인하세요. ({exc})"
        ) from exc

    print(f"xyock 로컬 서버: http://{HOST}:{PORT}/xyock.html")
    print(f"모델: {MODEL} (Ollama: {OLLAMA_CHAT_URL})")
    print("종료하려면 Ctrl+C를 누르세요.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
