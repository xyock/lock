import { createClient } from "npm:@supabase/supabase-js@2.49.1";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS, GET",
};
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { ...cors, "Content-Type": "application/json" } });
const enc = new TextEncoder();
const b64 = (bytes: Uint8Array) => {
  let s = ""; for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s);
};
const unb64 = (s: string) => Uint8Array.from(atob(s), c => c.charCodeAt(0));
const hex = (bytes: Uint8Array) => [...bytes].map(x => x.toString(16).padStart(2, "0")).join("");
const randomHex = (n: number) => {
  const b = crypto.getRandomValues(new Uint8Array(n)); return hex(b);
};
async function sha256(value: string) {
  return hex(new Uint8Array(await crypto.subtle.digest("SHA-256", enc.encode(value))));
}
function config() {
  const url = Deno.env.get("SUPABASE_URL");
  const service = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  const clientId = Deno.env.get("SUPABASE_OAUTH_CLIENT_ID");
  const clientSecret = Deno.env.get("SUPABASE_OAUTH_CLIENT_SECRET");
  const encryptionKey = Deno.env.get("XYOCK_TOKEN_ENCRYPTION_KEY");
  const appUrl = Deno.env.get("XYOCK_APP_URL");
  if (!url || !service || !clientId || !clientSecret || !encryptionKey || !appUrl)
    throw new Error("OAuth server configuration is incomplete");
  return { url, service, clientId, clientSecret, encryptionKey, appUrl: appUrl.replace(/\/$/, "") };
}
function adminClient() {
  const c = config();
  return createClient(c.url, c.service, { auth: { persistSession: false, autoRefreshToken: false } });
}
async function aesKey() {
  const raw = config().encryptionKey;
  let bytes: Uint8Array;
  try { bytes = raw.length === 64 ? Uint8Array.from(raw.match(/.{2}/g)!, x => parseInt(x, 16)) : unb64(raw); }
  catch { throw new Error("XYOCK_TOKEN_ENCRYPTION_KEY must be 32 random bytes encoded as hex or base64"); }
  if (bytes.length !== 32) throw new Error("XYOCK_TOKEN_ENCRYPTION_KEY must decode to exactly 32 bytes");
  return crypto.subtle.importKey("raw", bytes, "AES-GCM", false, ["encrypt", "decrypt"]);
}
async function encrypt(value: string) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const cipher = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, await aesKey(), enc.encode(value));
  return b64(new Uint8Array([...iv, ...new Uint8Array(cipher)]));
}
async function decrypt(value: string) {
  const all = unb64(value);
  const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: all.slice(0, 12) }, await aesKey(), all.slice(12));
  return new TextDecoder().decode(plain);
}
async function tokenRequest(params: Record<string, string>) {
  const c = config();
  const response = await fetch("https://api.supabase.com/v1/oauth/token", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Accept: "application/json",
      Authorization: "Basic " + btoa(c.clientId + ":" + c.clientSecret),
    },
    body: new URLSearchParams(params),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error("Supabase OAuth token exchange failed (" + response.status + ")");
  return data;
}
async function getValidAccessToken(userId: string) {
  const db = adminClient();
  const { data, error } = await db.from("supabase_oauth_connections").select("*").eq("user_id", userId).maybeSingle();
  if (error) throw error;
  if (!data) throw new Error("Supabase account is not connected");
  if (new Date(data.token_expires_at).getTime() > Date.now() + 60_000) return await decrypt(data.access_token_ciphertext);
  const refresh = await decrypt(data.refresh_token_ciphertext);
  const tokens = await tokenRequest({ grant_type: "refresh_token", refresh_token: refresh });
  const expiresAt = new Date(Date.now() + Number(tokens.expires_in || 3600) * 1000).toISOString();
  const { error: updateError } = await db.from("supabase_oauth_connections").update({
    access_token_ciphertext: await encrypt(tokens.access_token),
    refresh_token_ciphertext: await encrypt(tokens.refresh_token || refresh),
    token_expires_at: expiresAt,
    updated_at: new Date().toISOString(),
  }).eq("user_id", userId);
  if (updateError) throw updateError;
  return tokens.access_token as string;
}
async function management(userId: string, path: string) {
  const token = await getValidAccessToken(userId);
  const res = await fetch("https://api.supabase.com/v1" + path, {
    headers: { Authorization: "Bearer " + token, Accept: "application/json" },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error("Supabase Management API error (" + res.status + ")");
  return data;
}
async function authenticate(req: Request) {
  const auth = req.headers.get("Authorization") || "";
  const match = auth.match(/^Bearer\s+(.+)$/i);
  if (!match) return null;
  const c = config();
  const userClient = createClient(c.url, Deno.env.get("SUPABASE_ANON_KEY") || "", {
    auth: { persistSession: false }, global: { headers: { Authorization: auth } },
  });
  const { data, error } = await userClient.auth.getUser(match[1]);
  return error || !data.user ? null : data.user;
}
Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  const url = new URL(req.url);
  const c = (() => { try { return config(); } catch { return null; } })();
  if (!c) return json({ error: "OAuth server configuration is incomplete. Configure the required Edge Function secrets." }, 503);

  // Supabase redirects here without the XYOCK session header. The one-time state binds the callback to its owner.
  if (req.method === "GET" && url.pathname.endsWith("/callback")) {
    const code = url.searchParams.get("code");
    const state = url.searchParams.get("state");
    const denied = url.searchParams.get("error");
    const fallback = c.appUrl + "?supabase_connection=failed";
    if (denied || !code || !state) return Response.redirect(fallback, 302);
    const db = adminClient();
    const { data: stateRow, error } = await db.from("supabase_oauth_states").select("*")
      .eq("state_hash", await sha256(state)).gt("expires_at", new Date().toISOString()).maybeSingle();
    if (error || !stateRow) return Response.redirect(fallback, 302);
    await db.from("supabase_oauth_states").delete().eq("id", stateRow.id);
    try {
      const redirectUri = Deno.env.get("SUPABASE_URL") + "/functions/v1/supabase-connect/callback";
      const tokens = await tokenRequest({
        grant_type: "authorization_code", code, redirect_uri: redirectUri, code_verifier: stateRow.code_verifier,
      });
      if (!tokens.access_token || !tokens.refresh_token) throw new Error("OAuth token response incomplete");
      const { error: saveError } = await db.from("supabase_oauth_connections").upsert({
        user_id: stateRow.user_id,
        access_token_ciphertext: await encrypt(tokens.access_token),
        refresh_token_ciphertext: await encrypt(tokens.refresh_token),
        token_expires_at: new Date(Date.now() + Number(tokens.expires_in || 3600) * 1000).toISOString(),
        scope: tokens.scope || null,
        connected_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      if (saveError) throw saveError;
      return Response.redirect(stateRow.return_to + (stateRow.return_to.includes("?") ? "&" : "?") + "supabase_connection=connected", 302);
    } catch {
      return Response.redirect(stateRow.return_to + (stateRow.return_to.includes("?") ? "&" : "?") + "supabase_connection=failed", 302);
    }
  }

  if (req.method !== "POST") return json({ error: "POST required" }, 405);
  const user = await authenticate(req);
  if (!user) return json({ error: "Sign in to XYOCK first" }, 401);
  const body = await req.json().catch(() => ({}));
  const op = body?.op;
  const db = adminClient();

  try {
    if (op === "start") {
      const verifier = b64(crypto.getRandomValues(new Uint8Array(32))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
      const challenge = b64(new Uint8Array(await crypto.subtle.digest("SHA-256", enc.encode(verifier))))
        .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
      const state = randomHex(32);
      const redirectUri = c.url + "/functions/v1/supabase-connect/callback";
      const returnTo = c.appUrl;
      await db.from("supabase_oauth_states").delete().lt("expires_at", new Date().toISOString());
      const { error } = await db.from("supabase_oauth_states").insert({
        user_id: user.id, state_hash: await sha256(state), code_verifier: verifier,
        return_to: returnTo, expires_at: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
      });
      if (error) throw error;
      const authorize = new URL("https://api.supabase.com/v1/oauth/authorize");
      authorize.search = new URLSearchParams({
        client_id: c.clientId, redirect_uri: redirectUri, response_type: "code",
        state, code_challenge: challenge, code_challenge_method: "S256",
      }).toString();
      return json({ authorize_url: authorize.toString() });
    }
    if (op === "status") {
      const { data, error } = await db.from("supabase_oauth_connections").select("connected_at,token_expires_at,scope")
        .eq("user_id", user.id).maybeSingle();
      if (error) throw error;
      return json({ connected: !!data, connection: data || null });
    }
    if (op === "organizations") return json({ organizations: await management(user.id, "/organizations") });
    if (op === "projects") {
      const org = typeof body.organization_id === "string" ? body.organization_id : "";
      const path = org ? "/projects?organization_id=" + encodeURIComponent(org) : "/projects";
      return json({ projects: await management(user.id, path) });
    }
    if (op === "disconnect") {
      const { error } = await db.from("supabase_oauth_connections").delete().eq("user_id", user.id);
      if (error) throw error;
      return json({ disconnected: true });
    }
    return json({ error: "Unsupported operation" }, 400);
  } catch (e) {
    return json({ error: e instanceof Error ? e.message : "Request failed" }, 400);
  }
});
