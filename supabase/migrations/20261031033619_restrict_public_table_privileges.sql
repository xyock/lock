-- Remove broad default table privileges. RLS does not protect TRUNCATE, REFERENCES, or TRIGGER.
REVOKE ALL PRIVILEGES ON TABLE
  public.terms,
  public.profiles,
  public.chat_conversations,
  public.login_requests,
  public.xyock_ai_rate_limits,
  public.xyock_guest_daily_usage
FROM anon, authenticated;

-- Public term dictionary: readable by guests; writes remain PRO-only through RLS.
GRANT SELECT ON TABLE public.terms TO anon, authenticated;
GRANT INSERT, UPDATE, DELETE ON TABLE public.terms TO authenticated;

-- User-owned data: authenticated users only; row ownership remains enforced by RLS.
GRANT SELECT ON TABLE public.profiles TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.chat_conversations TO authenticated;

-- Login tokens and rate-limit counters remain server-only.
