# Supabase Setup

1. Create a project at supabase.com
2. Go to Project Settings → API, copy Project URL, anon key, and service_role key
3. Add them to backend/.env and frontend/.env.local (see .env.example files)
4. Go to SQL Editor and run schema.sql
5. Go to Authentication → URL Configuration, set Site URL to http://localhost:3000
6. (Optional) Run seed.sql in SQL Editor to get test data