-- Explicit deny policies document that these service-only tables are never client-readable/writable.
-- service_role bypasses RLS; anon/authenticated remain denied even if table grants are changed later.
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['login_requests','xyock_ai_rate_limits','xyock_guest_daily_usage']
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS "deny client access" ON public.%I', t);
    EXECUTE format(
      'CREATE POLICY "deny client access" ON public.%I FOR ALL TO anon, authenticated USING (false) WITH CHECK (false)',
      t
    );
  END LOOP;
END $$;
