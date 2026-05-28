export type Message = {
  id: string
  thread_id: string
  role: 'user' | 'assistant'
  content: string
  is_merge_artifact: boolean
  merge_source_thread_ids: string[]
  created_at: string
}

export type Thread = {
  id: string
  owner_id: string
  label: string | null
  fork_source_message_id: string | null
  created_at: string
}

export type TreeNode = {
  thread: Thread
  fork_message_id: string | null
  children: TreeNode[]
}

// Data carried in each React Flow node — messages are read from the Zustand
// store by thread id, not stored in the node itself, so streaming never
// triggers a React Flow layout recalculation.
export type ThreadNodeData = {
  thread: Thread
}
