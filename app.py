#!/usr/bin/env python3
"""Local xyock editor server with a Piston execution backend."""
from __future__ import annotations
import json, mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

HOST, PORT = "127.0.0.1", 8000
PISTON = "http://127.0.0.1:2000"
ROOT = Path(__file__).resolve().parent
MAX_BODY_BYTES = 100_000
ALLOWED = {"python","javascript","typescript","c","c++","java","csharp","go","rust","php","ruby","swift","kotlin","dart","rscript","sqlite3","bash","powershell","lua","perl","scala","haskell","nasm"}
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")

class Handler(BaseHTTPRequestHandler):
    server_version = "xyock-local/2.0"
    def send_json(self, status, data):
        body=json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store")
        self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        path=unquote(urlsplit(self.path).path)
        if path == "/health":
            self.send_json(200,{"ok":True,"runner":"piston"}); return
        if path == "/":
            path="/index.html"
        candidate=(ROOT/path.lstrip("/")).resolve()
        try: candidate.relative_to(ROOT)
        except ValueError: self.send_json(403,{"error":"Forbidden"}); return
        if not candidate.is_file(): self.send_json(404,{"error":"File not found"}); return
        ctype=mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript",): ctype+="; charset=utf-8"
        data=candidate.read_bytes()
        self.send_response(200); self.send_header("Content-Type",ctype)
        self.send_header("Content-Length",str(len(data))); self.send_header("X-Content-Type-Options","nosniff")
        self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        # Prevent cross-site requests and DNS-rebinding attempts against the local runner.
        host = (self.headers.get("Host") or "").lower()
        if host not in {"127.0.0.1:8000", "localhost:8000"}:
            self.send_json(403,{"error":"Invalid host"}); return
        origin = self.headers.get("Origin")
        if origin and origin not in {"http://127.0.0.1:8000", "http://localhost:8000"}:
            self.send_json(403,{"error":"Cross-origin requests are not allowed"}); return
        if self.headers.get_content_type() != "application/json":
            self.send_json(415,{"error":"Content-Type must be application/json"}); return
        if urlsplit(self.path).path != "/api/run":
            self.send_json(404,{"error":"Unknown endpoint"}); return
        try: length=int(self.headers.get("Content-Length","0"))
        except ValueError: self.send_json(400,{"error":"Invalid content length"}); return
        if length <= 0 or length > MAX_BODY_BYTES:
            self.send_json(413,{"error":"코드 크기는 100KB 이하여야 합니다."}); return
        try: payload=json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception: self.send_json(400,{"error":"올바른 JSON 요청이 아닙니다."}); return
        language, code=payload.get("language"), payload.get("code")
        if language not in ALLOWED or not isinstance(code,str):
            self.send_json(400,{"error":"지원하지 않는 언어 또는 코드 형식입니다."}); return
        if len(code.encode("utf-8")) > MAX_BODY_BYTES:
            self.send_json(413,{"error":"코드 크기는 100KB 이하여야 합니다."}); return
        try:
            with urlopen(PISTON+"/api/v2/runtimes",timeout=8) as r: runtimes=json.loads(r.read())
            matches=[x for x in runtimes if x.get("language")==language or language in x.get("aliases",[])]
            if not matches:
                self.send_json(503,{"error":f"{language} 런타임이 설치되지 않았습니다. start-xyock.command를 다시 실행해 런타임 설치를 완료해 주세요."}); return
            version=matches[0]["version"]
            ext={"python":"py","javascript":"js","typescript":"ts","c":"c","c++":"cpp","java":"java","csharp":"cs","go":"go","rust":"rs","php":"php","ruby":"rb","swift":"swift","kotlin":"kt","dart":"dart","rscript":"r","sqlite3":"sql","bash":"sh","powershell":"ps1","lua":"lua","perl":"pl","scala":"scala","haskell":"hs","nasm":"asm"}[language]
            body=json.dumps({"language":language,"version":version,"files":[{"name":"main."+ext,"content":code}],"stdin":"","compile_timeout":20000,"run_timeout":5000,"compile_memory_limit":536870912,"run_memory_limit":268435456}).encode()
            req=Request(PISTON+"/api/v2/execute",data=body,headers={"Content-Type":"application/json"},method="POST")
            with urlopen(req,timeout=35) as r: result=json.loads(r.read())
            self.send_json(200,result)
        except HTTPError as e:
            detail=e.read().decode("utf-8",errors="replace")[:800]
            self.send_json(502,{"error":"실행 엔진 오류: "+detail})
        except (URLError,TimeoutError,ConnectionError) as e:
            self.send_json(503,{"error":"실행 엔진에 연결할 수 없습니다. Docker Desktop과 Piston 컨테이너가 실행 중인지 확인하세요."})
        except Exception as e:
            self.send_json(500,{"error":"실행 처리 오류: "+str(e)[:300]})
    def log_message(self, fmt, *args): print("[%s] %s"%(self.log_date_time_string(),fmt%args))

def main():
    server=ThreadingHTTPServer((HOST,PORT),Handler)
    print(f"xyock 코드 편집기: http://{HOST}:{PORT}/")
    print("종료: Ctrl+C")
    try: server.serve_forever()
    except KeyboardInterrupt: print("\n서버 종료")
    finally: server.server_close()
if __name__=="__main__": main()
