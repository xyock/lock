-- Reconstructed from the existing production schema so Supabase Preview can
-- reproduce the GitHub action request and audit tables on a fresh preview branch.
CREATE TABLE IF NOT EXISTS public.github_action_requests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  repo text NOT NULL DEFAULT 'xyock/lock'
    CONSTRAINT github_action_requests_repo_check
    CHECK (repo ~ '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$'),
  action_type text NOT NULL
    CONSTRAINT github_action_requests_action_type_check
    CHECK (action_type = ANY (ARRAY[
      'read_file', 'create_file', 'update_file', 'create_pull_request', 'deploy_pages'
    ])),
  target_path text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  payload_hash text NOT NULL,
  approval_token_hash text,
  status text NOT NULL DEFAULT 'pending'
    CONSTRAINT github_action_requests_status_check
    CHECK (status = ANY (ARRAY[
      'pending', 'approved', 'rejected', 'executing', 'completed', 'failed', 'expired'
    ])),
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL DEFAULT (now() + interval '10 minutes'),
  approved_at timestamptz,
  executed_at timestamptz,
  result jsonb
);

CREATE INDEX IF NOT EXISTS idx_github_action_status_expiry
  ON public.github_action_requests (status, expires_at);
CREATE INDEX IF NOT EXISTS idx_github_action_user_created
  ON public.github_action_requests (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS public.github_action_audit (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id uuid REFERENCES public.github_action_requests(id) ON DELETE SET NULL,
  user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  event_type text NOT NULL
    CONSTRAINT github_action_audit_event_type_check
    CHECK (event_type = ANY (ARRAY[
      'requested', 'approved', 'rejected', 'execution_started',
      'execution_completed', 'execution_failed', 'expired'
    ])),
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_github_audit_request
  ON public.github_action_audit (request_id, created_at DESC);

ALTER TABLE public.github_action_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.github_action_audit ENABLE ROW LEVEL SECURITY;

-- These tables are accessed only by the trusted Edge Function using service_role.
REVOKE ALL PRIVILEGES ON TABLE
  public.github_action_requests,
  public.github_action_audit
FROM PUBLIC, anon, authenticated;
GRANT ALL PRIVILEGES ON TABLE
  public.github_action_requests,
  public.github_action_audit
TO service_role;
