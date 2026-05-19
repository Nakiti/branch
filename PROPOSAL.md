
## Title: Branch

### One Sentence Description
Branch is a generative AI chat applicaiton where users can split a single threaded chat into independent conversations that can be merged to provide a more intuitive chat interface (Ship it with auth + live URL, Generation as the point (maybe))

### Past project reference
None

### Planned Technologies
Frontend: Next.js, React Flow for UI
Backend: FastAPI (Python)
Database: Supabase
AI: Anthropic Claude API
Deployment: Vercel (frontend), Railway (backend)


### First Deliverable
A logged in user can have a conversation with the LLM, fork any message into a new branch, continue both the original and new branches independently, and then trigger a "merge back" that synthesizes the the branch's conversation into a contextual message in the parent thread or new thread. 


### Architecture for First Deliverable
1. Auth & Session Management
2. Thread Storage in Supabase --> { id, owner_id, created_at, fork_source_message_id? }
3. Chat Completion Service --> Fetches full message history up to current point, call Claude API, stream response back
4. Fork Creation --> create a new thread and the context is supplied through walking up the fork chain (context reconstruction)
5. Context Reconstruction --> this is an ordered list of messages representing the full context, follow the chain up, and append this thread's own messages
6. Merge Synthesizer --> Calls Claude summarzing the new branch and the and then injecting it to the main thread
7. Chat UI --> Renders message history for a given thread, branch here button where user can branch from any point in any conversation, This will be an intuitive UI that will likely take several repitions of modification


### After First Deliverable Goals
- Visual tree view
- Auto suggested branch naming by Claude
- Conflict detection - where the conversation of one branch contradicts the conversation of another branch
- Eval harness
- Branch suggestion - Claude detects when a chat within a conversation is a tangent and prompts the user to branch