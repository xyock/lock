-- Restrict trigger helper execution to trusted database roles.
REVOKE EXECUTE ON FUNCTION public.handle_new_user() FROM PUBLIC, anon, authenticated;

-- Keep one SELECT policy for authenticated users reading their own conversations.
DROP POLICY IF EXISTS "Users can view own conversations" ON public.chat_conversations;
