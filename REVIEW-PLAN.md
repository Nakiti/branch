Feedback:
- Application doesn't work, API requests result in 401 error
    - Claude API token was regenerated and replaced the expired one

- Implement auto naming feature
    - Branch nodes are named at fork time — when you fork off a message, the backend generates a 2-5 word title using Claude Haiku based on the conversation context up to that point and stores it immediately. Root conversations are named after the first message is sent: the backend detects that it's the first message in a root thread, generates a label after the response finishes streaming, and sends it back as a special SSE event that the frontend intercepts and updates the node header and sidebar live.

- Improve UI to be more user friendly
    - Made each node larger by default (600x500 instead of 480x380) so more of the conversation is visible without scrolling. Added an empty state placeholder inside nodes that have no messages yet so it's clear where to start typing. On initial load, the app now always shows at least one empty node instead of a blank canvas.

- Deleting nodes/chats
    - Added a trash icon to the sidebar for deleting entire conversations and a trash icon in each node header for deleting branch nodes. Both have a confirmation step before anything is deleted. Deleting a node also deletes all of its child branches recursively, since those branches depend on the deleted node's context.
