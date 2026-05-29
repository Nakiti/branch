# Demo — Branch

## Live Demo

Visit **https://branch-wheat.vercel.app/**

The app is fully deployed (frontend on Vercel, backend on Railway, database on Supabase). No install required.

### Walkthrough

1. **Sign up** — create an account with any email and password on the login page.
2. **Start a conversation** — click "New Conversation" in the left sidebar. Type a message and press Enter to chat with Claude.
3. **Fork a branch** — hover over any assistant message and click the branch button (⎇) that appears. A new thread node appears on the canvas, connected to the original by a bezier edge.
4. **Continue both threads independently** — click into either node and keep chatting. Each thread has its own context, but the branch inherits the full conversation history up to the fork point.
5. **Merge back** — in a branch node, click the merge button in the node header. Claude synthesizes the key insight from the branch and injects it as a highlighted merge artifact message in the parent thread.
6. **Navigate the canvas** — pan by dragging the background, zoom with scroll, drag nodes to rearrange. The minimap in the bottom-right shows the full tree.

## Building from Scratch

See `README.md` for full local setup instructions, including environment variable configuration and database schema setup.
