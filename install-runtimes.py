#!/usr/bin/env python3
"""Install the runtimes used by xyock into the local Piston instance."""
import json, time, urllib.request, urllib.error
BASE="http://127.0.0.1:2000/api/v2"
WANTED=["python","node","typescript","gcc","java","csharp","go","rust","php","ruby","swift","kotlin","dart","r","sqlite3","bash","powershell","lua","perl","scala","haskell","nasm"]
def request(url, data=None, timeout=1800):
    req=urllib.request.Request(url,data=data,headers={"Content-Type":"application/json"} if data else {})
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.loads(r.read().decode())
def main():
    print("설치 가능한 언어 목록을 확인합니다…")
    packages=request(BASE+"/packages",timeout=180)
    installed={p["language"] for p in packages if p.get("installed")}
    by_name={}
    for p in packages: by_name.setdefault(p["language"],[]).append(p)
    for name in WANTED:
        if name in installed:
            print("이미 설치됨:",name); continue
        choices=by_name.get(name,[])
        if not choices:
            print("패키지 목록에 없음(건너뜀):",name); continue
        # Ask Piston for its latest available version.
        print("설치 중:",name,"(다운로드에 시간이 걸릴 수 있습니다)")
        try:
            result=request(BASE+"/packages",json.dumps({"language":name,"version":"*"}).encode(),timeout=1800)
            print("설치 완료:",result.get("language"),result.get("version"))
        except Exception as e: print("설치 실패:",name,str(e))
    runtimes=request(BASE+"/runtimes",timeout=180)
    print("\n사용 가능한 실행 환경:")
    print(", ".join(sorted(set(x["language"] for x in runtimes))))
    print("\n런타임 설치 절차가 끝났습니다.")
if __name__=="__main__": main()
