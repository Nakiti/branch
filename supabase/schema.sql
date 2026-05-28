-- Branch data model
-- A Thread is either a root conversation (fork_source_message_id IS NULL)
-- or a branch that forked from a specific message in another thread.
-- Context is reconstructed at query time by walking the fork chain —
-- messages are never copied between threads.

CREATE TABLE IF NOT EXISTS threads (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  label text,
  fork_source_message_id uuid,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  thread_id uuid NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('user', 'assistant')),
  content text NOT NULL,
  is_merge_artifact boolean NOT NULL DEFAULT false,
  merge_source_thread_ids uuid[] NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE threads
  ADD CONSTRAINT threads_fork_source_message_id_fkey
  FOREIGN KEY (fork_source_message_id)
  REFERENCES messages(id)
  ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_messages_thread_id_created_at
  ON messages(thread_id, created_at ASC);

CREATE INDEX IF NOT EXISTS idx_threads_owner_id
  ON threads(owner_id);

CREATE INDEX IF NOT EXISTS idx_threads_fork_source_message_id
  ON threads(fork_source_message_id);

ALTER TABLE threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "threads_owner_select" ON threads FOR SELECT USING (owner_id = auth.uid());
CREATE POLICY "threads_owner_insert" ON threads FOR INSERT WITH CHECK (owner_id = auth.uid());
CREATE POLICY "threads_owner_update" ON threads FOR UPDATE USING (owner_id = auth.uid());
CREATE POLICY "threads_owner_delete" ON threads FOR DELETE USING (owner_id = auth.uid());

CREATE POLICY "messages_owner_select" ON messages FOR SELECT
  USING (EXISTS (
    SELECT 1 FROM threads WHERE threads.id = messages.thread_id AND threads.owner_id = auth.uid()
  ));

CREATE POLICY "messages_owner_insert" ON messages FOR INSERT
  WITH CHECK (EXISTS (
    SELECT 1 FROM threads WHERE threads.id = messages.thread_id AND threads.owner_id = auth.uid()
  ));