import { createClient } from "npm:@supabase/supabase-js@2";

async function sha256Hex(text: string) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
const env = (k: string) => Deno.env.get(k) ?? "";
function html(message: string, status = 200, form = "") {
  return new Response(`<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>xyock 로그인 확인</title><body style="font-family:system-ui;background:#080b09;color:#f4f4f4;display:grid;place-items:center;min-height:90vh;padding:24px"><main style="max-width:420px;background:#141816;border:1px solid #29352e;border-radius:18px;padding:28px;text-align:center"><h2>${message}</h2>${form}<p style="color:#9aa79f">이 창은 닫으셔도 됩니다.</p></main></body></html>`, {status,headers:{"Content-Type":"text/html; charset=utf-8","Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}});
}
Deno.serve(async (req) => {
  const url = new URL(req.url);
  if (req.method !== "GET" && req.method !== "POST") return new Response("Method Not Allowed",{status:405,headers:{Allow:"GET, POST"}});
  let id="", action="", token="";
  if (req.method === "GET") {
    id=url.searchParams.get("id") ?? "";
    action=url.searchParams.get("a") ?? "";
    token=url.searchParams.get("t") ?? "";
  } else {
    const body=await req.formData().catch(()=>null);
    if (!body) return html("요청 형식이 올바르지 않습니다.",400);
    id=String(body.get("id") ?? "");
    action=String(body.get("a") ?? "");
    token=String(body.get("t") ?? "");
  }
  if (!/^[0-9a-f-]{36}$/i.test(id) || !/^[a-f0-9]{64}$/i.test(token) || !["approve","reject"].includes(action)) return html("잘못된 링크입니다.",400);
  const admin=createClient(env("SUPABASE_URL"),env("SUPABASE_SERVICE_ROLE_KEY"),{auth:{persistSession:false}});
  const {data:row,error}=await admin.from("login_requests").select("id,status,expires_at,approve_hash,reject_hash").eq("id",id).maybeSingle();
  if (error || !row || row.status!=="pending" || new Date(row.expires_at).getTime()<Date.now()) return html("만료되었거나 이미 처리된 요청입니다.",410);
  const expected=action==="approve"?row.approve_hash:row.reject_hash;
  if (!expected || (await sha256Hex(token))!==expected) return html("잘못된 링크입니다.",403);
  if (req.method === "GET") {
    const label=action==="approve"?"로그인 승인":"로그인 거절";
    return html("로그인 요청을 확인해 주세요.",200,`<p>직접 요청한 로그인인지 확인한 뒤 아래 버튼을 눌러 주세요.</p><form method="POST"><input type="hidden" name="id" value="${id}"><input type="hidden" name="a" value="${action}"><input type="hidden" name="t" value="${token}"><button style="background:#a7f3d0;color:#06120c;border:0;border-radius:999px;padding:13px 26px;font-size:16px;font-weight:700;cursor:pointer" type="submit">${label} 확인</button></form>`);
  }
  const {data:updated,error:updateError}=await admin.from("login_requests").update({status:action==="approve"?"approved":"rejected"}).eq("id",id).eq("status","pending").gt("expires_at",new Date().toISOString()).select("id").maybeSingle();
  if (updateError || !updated) return html("요청이 이미 처리되었거나 만료되었습니다.",409);
  return html(action==="approve"?"로그인을 승인했습니다.":"로그인을 거절했습니다.");
});