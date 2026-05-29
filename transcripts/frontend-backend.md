The frontend UI is complete (built in Lovable) and the backend is fully implemented. Read CLAUDE.md, frontend/CLAUDE.md, and backend/CLAUDE.md before touching any code.
The goal is to replace all dummy/static data in the frontend with real API calls to the backend, wire up Supabase auth, and get the full user flow working end to end.
Before starting: audit the frontend
Before writing any new code, do the following:

Read every file in frontend/components/
Read frontend/app/canvas/page.tsx (or equivalent main page)
Find every place where dummy/hardcoded data is defined — look for hardcoded message arrays, fake thread objects, placeholder labels, mock user state
List them all out as a comment before proceeding — this is your replacement checklist


Step 1: Install dependencies
bashcd frontend
npm install @supabase/supabase-js @supabase/ssr zustand
If React Flow is not already installed:
bashnpm install reactflow

Step 2: Supabase client setup
Create frontend/lib/supabase.ts:
typescriptimport { createBrowserClient } from '@supabase/ssr'

export const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)
Create frontend/lib/supabase-server.ts (for server components):
typescriptimport { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function createSupabaseServerClient() {
  const cookieStore = await cookies()
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return cookieStore.getAll() },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options))
        },
      },
    }
  )
}

Step 3: Types
Create frontend/types/index.ts with the exact types from frontend/CLAUDE.md. Do not deviate from these — they must match the backend Pydantic schemas exactly.

Step 4: API client
Create frontend/lib/api.ts. All backend calls go through this file — no component should ever call fetch directly.
typescriptconst BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

async function getAuthHeader(): Promise<Record<string, string>> {
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) throw new Error('Not authenticated')
  return { Authorization: `Bearer ${session.access_token}` }
}

// Send a message — returns an async generator of string chunks
export async function* sendMessage(
  thread_id: string,
  content: string
): AsyncGenerator<string> {
  const headers = await getAuthHeader()
  const response = await fetch(`${BACKEND_URL}/api/chat`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id, content })
  })
  if (!response.ok) throw new Error(`Chat failed: ${response.statusText}`)
  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const text = decoder.decode(value)
    const lines = text.split('\n')
    for (const line of lines) {
      if (line.startsWith('data: ') && line !== 'data: [DONE]') {
        yield line.slice(6)
      }
    }
  }
}

export async function forkThread(message_id: string): Promise<{ thread_id: string }> {
  const headers = await getAuthHeader()
  const res = await fetch(`${BACKEND_URL}/api/fork`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ message_id })
  })
  if (!res.ok) throw new Error(`Fork failed: ${res.statusText}`)
  return res.json()
}

export async function getTree(root_thread_id: string): Promise<TreeNode> {
  const headers = await getAuthHeader()
  const res = await fetch(
    `${BACKEND_URL}/api/tree?root_thread_id=${root_thread_id}`,
    { headers }
  )
  if (!res.ok) throw new Error(`Tree fetch failed: ${res.statusText}`)
  return res.json()
}

export async function mergeBack(branch_thread_id: string): Promise<Message> {
  const headers = await getAuthHeader()
  const res = await fetch(`${BACKEND_URL}/api/merge`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ branch_thread_id })
  })
  if (!res.ok) throw new Error(`Merge failed: ${res.statusText}`)
  const data = await res.json()
  return data.message
}

// Create a new root thread (no fork)
export async function createThread(label?: string): Promise<Thread> {
  const headers = await getAuthHeader()
  const res = await fetch(`${BACKEND_URL}/api/threads`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ label: label || 'New Conversation' })
  })
  if (!res.ok) throw new Error(`Create thread failed: ${res.statusText}`)
  return res.json()
}

// Fetch all root threads for the current user (for sidebar)
export async function getRootThreads(): Promise<Thread[]> {
  const headers = await getAuthHeader()
  const res = await fetch(`${BACKEND_URL}/api/threads`, { headers })
  if (!res.ok) throw new Error(`Fetch threads failed: ${res.statusText}`)
  return res.json()
}

// Fetch messages for a thread
export async function getMessages(thread_id: string): Promise<Message[]> {
  const headers = await getAuthHeader()
  const res = await fetch(`${BACKEND_URL}/api/threads/${thread_id}/messages`, { headers })
  if (!res.ok) throw new Error(`Fetch messages failed: ${res.statusText}`)
  return res.json()
}
Note: createThread, getRootThreads, and getMessages require two additional backend routes not in the original spec. Add them to the backend now:
backend/routes/threads.py — add these routes:
pythonGET  /api/threads                    # returns all root threads for current user
POST /api/threads                    # creates a new root thread
GET  /api/threads/{thread_id}/messages  # returns messages for a thread
Register this router in backend/main.py.

Step 5: Zustand store
Create frontend/store/useStore.ts exactly matching the shape in frontend/CLAUDE.md. Key behaviors:

setActiveConversation loads the tree and all message lists for every thread in that tree
appendStreamChunk appends to a temporary streaming buffer keyed by thread_id
finalizeStream replaces the streaming buffer with the real persisted message
addThread adds the thread to the store AND adds it as a new React Flow node at an auto-calculated position (offset from its parent node)


Step 6: Auth page
Create frontend/app/auth/page.tsx — a simple centered card with:

Email + password inputs
Sign in button → supabase.auth.signInWithPassword()
Sign up button → supabase.auth.signUp()
On success: router.push('/canvas')
Show error message inline if auth fails


Step 7: Auth middleware
Create frontend/middleware.ts at the root of the frontend:
typescriptimport { createServerClient } from '@supabase/ssr'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  // Redirect to /auth if no session, except for /auth itself
  const { pathname } = request.nextUrl
  if (pathname.startsWith('/auth')) return NextResponse.next()

  // Check session — redirect to /auth if missing
  // ... standard Supabase SSR middleware pattern
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
Use the standard Supabase SSR middleware pattern from their docs exactly.

Step 8: Wire the Canvas page
This is the main wiring step. In frontend/app/canvas/page.tsx:

On mount: call getRootThreads() and populate the sidebar
On conversation select: call getTree(root_thread_id) to get the full branch tree, then call getMessages(thread_id) for every thread in the tree, store everything in Zustand
Replace all hardcoded React Flow nodes/edges with nodes derived from the Zustand store
"New Conversation" button: calls createThread(), adds to sidebar, sets as active, creates root node on canvas


Step 9: Wire ThreadNode component
In frontend/components/ThreadNode.tsx, replace dummy data with store data:

Messages come from useStore(state => state.messages[thread.id])
Send button handler:

typescriptconst handleSend = async () => {
  if (!input.trim()) return
  setInput('')
  // optimistically add user message to store
  store.addMessage({ role: 'user', content: input, thread_id: thread.id, ... })
  // stream response
  for await (const chunk of sendMessage(thread.id, input)) {
    store.appendStreamChunk(thread.id, chunk)
  }
  // finalize — re-fetch the last message to get the persisted version with real id
  const messages = await getMessages(thread.id)
  store.finalizeStream(thread.id, messages[messages.length - 1])
}

Branch button handler:

typescriptconst handleBranch = async (message_id: string) => {
  const { thread_id } = await forkThread(message_id)
  // fetch the new thread object
  // add to store with position offset from current node
  // React Flow will auto-render the new node + edge
}

Merge button handler:

typescriptconst handleMerge = async () => {
  const mergeMessage = await mergeBack(thread.id)
  // add mergeMessage to parent thread's messages in store
  // close confirmation popover
}

Step 10: Wire edges in React Flow
Edges must be derived from the thread tree, not hardcoded. In Canvas.tsx:
typescript// Derive edges from store
const edges = Object.values(store.threads)
  .filter(t => t.fork_source_message_id !== null)
  .map(t => ({
    id: `edge-${t.id}`,
    source: getParentThreadId(t, store.threads), // find parent by message ownership
    target: t.id,
    type: 'smoothstep',
    label: '⎇',
    style: { stroke: '#6366f1' }
  }))

Step 11: Add NEXT_PUBLIC_BACKEND_URL to frontend env
Add to frontend/.env.local:
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

Step 12: End-to-end verification checklist
Work through this in order. Do not skip steps.

 npm run dev starts without errors
 /auth page renders, can sign up with a new email
 After sign in, redirects to /canvas
 Sidebar shows "New Conversation" button, clicking it creates a thread
 Typing a message and hitting send calls the backend, streams a response into the node
 Hovering an assistant message shows the Branch button
 Clicking Branch creates a new node on the canvas connected by a line
 Typing in the branch node sends a message with correct context (only messages up to fork point + branch messages)
 Clicking Merge Back in a branch node header synthesizes the branch and injects a merge artifact into the parent node
 Merge artifact message renders with green tint and provenance badge
 Refreshing the page reloads the same conversation tree from the backend (state is persisted)

Fix any failing check before moving on. If the context check (7th bullet) is wrong — the branch is getting the full parent history instead of truncated — the bug is in the Context Reconstructor in the backend, not the frontend.
What NOT to do

Do not call fetch directly from any component — always go through api.ts
Do not store auth tokens in localStorage — Supabase SSR handles cookies automatically
Do not define nodeTypes inside the Canvas component body — define outside or memoize, or React Flow will infinitely re-render
Do not update React Flow node dimensions during streaming — only update message content in the Zustand store
Do not skip the auth middleware — every canvas route must be protected