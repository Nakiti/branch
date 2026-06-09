-- Seed for local dev — creates a test user and sample branch tree

DO $$
DECLARE
  test_user_id uuid := '00000000-0000-0000-0000-000000000001';
  root_thread_id uuid := gen_random_uuid();
  branch_thread_id uuid := gen_random_uuid();
  fork_message_id uuid := gen_random_uuid();
BEGIN
  -- Create test user if not present (local dev only — never run in prod)
  IF NOT EXISTS (SELECT 1 FROM auth.users WHERE id = test_user_id) THEN
    INSERT INTO auth.users (
      id, email, encrypted_password, email_confirmed_at,
      created_at, updated_at, raw_app_meta_data, raw_user_meta_data,
      aud, role
    ) VALUES (
      test_user_id,
      'test@example.com',
      crypt('password123', gen_salt('bf')),
      now(), now(), now(),
      '{"provider":"email","providers":["email"]}',
      '{}',
      'authenticated',
      'authenticated'
    );
  END IF;

  IF NOT EXISTS (SELECT 1 FROM threads LIMIT 1) THEN
    INSERT INTO threads (id, owner_id, label)
      VALUES (root_thread_id, test_user_id, 'Test Root Thread');
    INSERT INTO messages (id, thread_id, role, content) VALUES
      (gen_random_uuid(), root_thread_id, 'user', 'Explain transformer architecture'),
      (fork_message_id, root_thread_id, 'assistant', 'Transformers use self-attention to process sequences in parallel...'),
      (gen_random_uuid(), root_thread_id, 'user', 'How does training work?'),
      (gen_random_uuid(), root_thread_id, 'assistant', 'Training uses backpropagation through the attention layers...');
    INSERT INTO threads (id, owner_id, label, fork_source_message_id)
      VALUES (branch_thread_id, test_user_id, 'Attention deep dive', fork_message_id);
    INSERT INTO messages (thread_id, role, content) VALUES
      (branch_thread_id, 'user', 'Go deeper on the attention mechanism'),
      (branch_thread_id, 'assistant', 'Attention computes query, key, value matrices from the input...');
  END IF;
END $$;
