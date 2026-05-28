-- Run manually in SQL editor for local dev only
-- Creates a test tree to verify context reconstruction is working

DO $$
DECLARE
  root_thread_id uuid := gen_random_uuid();
  branch_thread_id uuid := gen_random_uuid();
  fork_message_id uuid := gen_random_uuid();
BEGIN
  IF NOT EXISTS (SELECT 1 FROM threads LIMIT 1) THEN
    INSERT INTO threads (id, owner_id, label)
      VALUES (root_thread_id, auth.uid(), 'Test Root Thread');
    INSERT INTO messages (id, thread_id, role, content) VALUES
      (gen_random_uuid(), root_thread_id, 'user', 'Explain transformer architecture'),
      (fork_message_id, root_thread_id, 'assistant', 'Transformers use self-attention to process sequences in parallel...'),
      (gen_random_uuid(), root_thread_id, 'user', 'How does training work?'),
      (gen_random_uuid(), root_thread_id, 'assistant', 'Training uses backpropagation through the attention layers...');
    INSERT INTO threads (id, owner_id, label, fork_source_message_id)
      VALUES (branch_thread_id, auth.uid(), 'Attention deep dive', fork_message_id);
    INSERT INTO messages (thread_id, role, content) VALUES
      (branch_thread_id, 'user', 'Go deeper on the attention mechanism'),
      (branch_thread_id, 'assistant', 'Attention computes query, key, value matrices from the input...');
  END IF;
END $$;