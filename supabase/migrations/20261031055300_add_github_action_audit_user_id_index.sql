-- Index the nullable audit user reference for user-scoped audit lookups.
CREATE INDEX IF NOT EXISTS idx_github_action_audit_user_id
  ON public.github_action_audit (user_id);
