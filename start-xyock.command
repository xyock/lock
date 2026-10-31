#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "xyock 실행 환경을 준비합니다."
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker Desktop이 필요합니다. Docker Desktop을 설치하고 실행한 뒤 다시 실행하세요."
  open "https://www.docker.com/products/docker-desktop/" 2>/dev/null || true
  read -r -p "종료하려면 Enter..."
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker Desktop을 먼저 실행해 주세요."
  read -r -p "종료하려면 Enter..."
  exit 1
fi
docker compose up -d
echo "Piston 실행 엔진이 시작될 때까지 대기합니다…"
for i in {1..90}; do
  if curl -fsS http://127.0.0.1:2000/api/v2/packages >/dev/null 2>&1; then break; fi
  sleep 2
done
if ! curl -fsS http://127.0.0.1:2000/api/v2/packages >/dev/null 2>&1; then
  echo "Piston 시작에 실패했습니다. Docker 로그를 확인하세요: docker logs xyock-piston"
  read -r -p "종료하려면 Enter..."
  exit 1
fi
python3 install-runtimes.py
echo "xyock 서버를 시작합니다."
open "http://127.0.0.1:8000/"
python3 app.py
