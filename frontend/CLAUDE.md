# Frontend CLAUDE.md

## Stack
- Next.js 14 (app router)
- React Flow — canvas, nodes, edges, minimap, zoom controls
- Tailwind CSS — styling
- Supabase JS client — auth only (no direct DB queries)
- Zustand — client state (active thread, canvas node positions, UI state)

## Directory structure
```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx              # redirects to /canvas
│   ├── auth/
│   │   └── page.tsx          # login / signup
│   └── canvas/
│       └── page.tsx          # main app — sidebar + canvas
├── components/
│   ├── Sidebar.tsx           # left sidebar, conversation list
│   ├── Canvas.tsx            # React Flow canvas wrapper
│   ├── ThreadNode.tsx        # individual chat thread node (React Flow custom node)
│   ├── MessageList.tsx       # scrollable message history inside a node
│   ├── MessageBubble.tsx     # single message — user / assistant / merge artifact
│   ├── ChatInput.tsx         # input box + send button at bottom of node
│   ├── BranchButton.tsx      # hover button on assistant messages
│   ├── MergeButton.tsx       # merge back button in node header
│   └── MergeConfirmPopover.tsx
├── lib/
│   ├── supabase.ts           # supabase client (anon key, browser)
│   ├── api.ts                # typed fetch wrappers for all backend routes
│   └── stream.ts             # SSE streaming helper for chat responses
├── store/
│   └── useStore.ts           # zustand store
└── types/
    └── index.ts              # shared TypeScript types
```

## Types (source of truth: /frontend/types/index.ts)
```typescript
type Message = {
  id: string
  thread_id: string
  role: 'user' | 'assistant'
  content: string
  is_merge_artifact: boolean
  merge_source_thread_ids: string[]
  created_at: string
}

type Thread = {
  id: string
  owner_id: string
  label: string | null
  fork_source_message_id: string | null
  created_at: string
}

type TreeNode = {
  thread: Thread
  fork_message_id: string | null
  children: TreeNode[]
}

// React Flow node data
type ThreadNodeData = {
  thread: Thread
  messages: Message[]
  isStreaming: boolean
}
```

## Zustand store shape
```typescript
{
  // conversations (root threads shown in sidebar)
  conversations: Thread[]
  activeConversationId: string | null

  // canvas state for active conversation
  threads: Record<string, Thread>         // thread_id -> Thread
  messages: Record<string, Message[]>     // thread_id -> Message[]
  nodePositions: Record<string, {x,y}>    // thread_id -> canvas position

  // streaming
  streamingThreadId: string | null
  streamingContent: string

  // actions
  setActiveConversation: (id: string) => void
  addThread: (thread: Thread) => void
  addMessage: (message: Message) => void
  appendStreamChunk: (thread_id: string, chunk: string) => void
  finalizeStream: (thread_id: string, message: Message) => void
  setNodePosition: (thread_id: string, pos: {x,y}) => void
}
```

## React Flow setup rules
- Use thread UUIDs directly as React Flow node `id` values
- Custom node type: `threadNode` → maps to `ThreadNode` component
- Edges connect parent thread node to child thread node (not message to node)
  - Edge `source` = parent thread_id
  - Edge `target` = child thread_id
  - Edge label position: midpoint, show ⎇ icon
- Node dragging: on drag stop, update `nodePositions` in store
- Initial layout: root node at {x: 100, y: 200}, children offset {x: +450, y: +100} per branch
- Always call `fitView()` after loading a new conversation

## API calls (all in /frontend/lib/api.ts)
```typescript
// never call backend directly from components — always go through api.ts
sendMessage(thread_id: string, content: string): AsyncIterable<string>  // streaming
forkThread(message_id: string): Promise<{ thread_id: string }>
getTree(root_thread_id: string): Promise<TreeNode>
mergeBack(branch_thread_id: string): Promise<Message>  // returns merge artifact
```

## Streaming pattern
- Backend sends SSE (`text/event-stream`)
- `stream.ts` wraps the fetch with a ReadableStream reader
- On each chunk: call `appendStreamChunk` in store → MessageList re-renders
- On stream end: call `finalizeStream` → replaces streaming content with persisted message

## Auth rules
- All pages except `/auth` require a session — redirect to `/auth` if no session
- Use Supabase `onAuthStateChange` in layout to handle session expiry
- Never use the Supabase service key in the frontend — anon key only

## Component rules
- `ThreadNode` is a React Flow custom node — it must forward the `ref` and spread `...props` correctly or React Flow breaks
- `MessageList` scrolls to bottom on new message — use a `useEffect` with a ref on the bottom sentinel div
- `BranchButton` only renders on `role === 'assistant'` messages and only on hover (`group-hover` Tailwind pattern)
- Merge artifact messages (`is_merge_artifact: true`) get a green-tinted background and a provenance badge showing source branch label

## Styling conventions
- Light theme: white cards, `bg-gray-50` canvas, subtle dot grid via SVG background-image
- Accent: indigo-500 (`#6366f1`) for buttons, active states, React Flow edges
- Card: `rounded-xl shadow-sm border border-gray-100` — no heavy borders
- Font: Inter (next/font), message text at `text-sm`, UI chrome at `text-xs`
- Never hardcode colors — always use Tailwind tokens

## Known gotchas
- React Flow requires a parent div with explicit width/height — use `w-full h-full` on a flex container that fills the viewport
- React Flow `nodeTypes` must be defined OUTSIDE the component or memoized — defining inline causes infinite re-renders
- Streaming + React Flow: do NOT update node dimensions during streaming — it causes layout thrashing. Only update message content in the store, not the node metadata
- Supabase auth cookies: use `@supabase/ssr` package, not the legacy `@supabase/auth-helpers-nextjs`
- Next.js app router: all components using React Flow must be `'use client'`