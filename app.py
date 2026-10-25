
import json
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

HOST = "127.0.0.1"
PORT = 8000

MODEL = "qwen3.5:4b"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
BASE_DIR = Path(__file__).resolve().parent
MAX_REQUEST_SIZE = 100_000


class LockAIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def send_json(self, status, data):
        body = json.dumps(
            data, ensure_ascii=False
        ).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type", "application/json; charset=utf-8"
        )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            self.path = "/index.html"

        return super().do_GET()

    def do_POST(self):
        if self.path != "/ask":
            self.send_json(404, {
                "error": "요청한 주소를 찾을 수 없습니다."
            })
            return

        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )

            if content_length <= 0:
                self.send_json(400, {
                    "error": "질문을 입력해 주세요."
                })
                return

            if content_length > MAX_REQUEST_SIZE:
                self.send_json(413, {
                    "error": "요청 크기가 너무 큽니다."
                })
                return

            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8"))
            question = payload.get("q", "")

            if not isinstance(question, str) or not question.strip():
                self.send_json(400, {
                    "error": "질문을 입력해 주세요."
                })
                return

            if len(question) > 20_000:
                self.send_json(413, {
                    "error": "질문이 너무 깁니다."
                })
                return

            ollama_payload = {
                "model": MODEL,
                "stream": False,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "너는 lock AI의 한국어 AI 도우미야. "
                            "질문에 정확하고 친절하게 답해. "
                            "코드를 요청받으면 코드와 설명을 "
                            "읽기 쉽게 제공해."
                        )
                    },
                    {
                        "role": "user",
                        "content": question.strip()
                    }
                ]
            }

            request = Request(
                OLLAMA_URL,
                data=json.dumps(
                    ollama_payload,
                    ensure_ascii=False
                ).encode("utf-8"),
                headers={
                    "Content-Type": "application/json"
                },
                method="POST"
            )

            with urlopen(request, timeout=300) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )

            answer = result.get("message", {}).get("content", "")

            if not answer:
                self.send_json(502, {
                    "error": "AI가 답변을 반환하지 않았습니다."
                })
                return

            self.send_json(200, {"answer": answer})

        except HTTPError as error:
            print("Ollama HTTP 오류:", error.code)
            self.send_json(502, {
                "error": "Ollama에서 오류가 발생했습니다."
            })

        except URLError:
            self.send_json(503, {
                "error": (
                    "Ollama에 연결할 수 없습니다. "
                    "Ollama가 실행 중인지 확인해 주세요."
                )
            })

        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(400, {
                "error": "요청 형식이 올바르지 않습니다."
            })

        except TimeoutError:
            self.send_json(504, {
                "error": "AI 응답 시간이 초과되었습니다."
            })

        except Exception as error:
            print("서버 오류:", repr(error))
            try:
                self.send_json(500, {
                    "error": "서버 내부 오류가 발생했습니다."
                })
            except OSError:
                pass


if __name__ == "__main__":
    if not (BASE_DIR / "index.html").is_file():
        print("오류: app.py와 같은 폴더에 index.html이 필요합니다.")
        raise SystemExit(1)

    server = ThreadingHTTPServer((HOST, PORT), LockAIHandler)

    print("lock AI 서버가 시작되었습니다.")
    print("주소: http://localhost:8000")
    print("모델:", MODEL)
    print("종료: Ctrl+C")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.")
    finally:
        server.server_close()
