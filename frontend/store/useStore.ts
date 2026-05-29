import { create } from 'zustand'
import type { Thread, Message, TreeNode } from '@/types'
import {
  getRootThreads,
  getTree,
  getMessages,
  createThread as apiCreateThread,
} from '@/lib/api'

interface FlowEdge {
  id: string
  source: string
  target: string
  sourceHandle: 'out'
  type: 'branch'
}

interface StoreState {
  conversations: Thread[]
  activeConversationId: string | null
  threads: Record<string, Thread>
  messages: Record<string, Message[]>
  nodePositions: Record<string, { x: number; y: number }>
  flowEdges: FlowEdge[]
  streamingThreadId: string | null
  streamingContent: string
  isLoadingConversation: boolean

  loadConversations: () => Promise<void>
  setActiveConversation: (id: string) => Promise<void>
  createConversation: (label?: string) => Promise<Thread>
  addThread: (
    thread: Thread,
    parentThreadId: string,
    forkMessageId: string,
    parentPos: { x: number; y: number }
  ) => void
  addMessage: (message: Message) => void
  appendStreamChunk: (thread_id: string, chunk: string) => void
  finalizeStream: (thread_id: string, messages: Message[]) => void
  setNodePosition: (thread_id: string, pos: { x: number; y: number }) => void
  addMergeArtifact: (message: Message) => void
}

// Recursive tree layout: root at (100, 300), children spread around parent y.
function layoutNode(
  node: TreeNode,
  x: number,
  y: number,
  positions: Record<string, { x: number; y: number }>
) {
  positions[node.thread.id] = { x, y }
  const childX = x + 480
  const n = node.children.length
  node.children.forEach((child, i) => {
    const childY = y + (i - (n - 1) / 2) * 340
    layoutNode(child, childX, childY, positions)
  })
}

export const useStore = create<StoreState>((set, get) => ({
  conversations: [],
  activeConversationId: null,
  threads: {},
  messages: {},
  nodePositions: {},
  flowEdges: [],
  streamingThreadId: null,
  streamingContent: '',
  isLoadingConversation: false,

  loadConversations: async () => {
    const convos = await getRootThreads()
    set({ conversations: convos })
  },

  setActiveConversation: async (id: string) => {
    set({
      activeConversationId: id,
      isLoadingConversation: true,
      threads: {},
      messages: {},
      nodePositions: {},
      flowEdges: [],
      streamingThreadId: null,
      streamingContent: '',
    })
    try {
      const tree = await getTree(id)

      const threads: Record<string, Thread> = {}
      const flowEdges: FlowEdge[] = []
      const nodePositions: Record<string, { x: number; y: number }> = {}

      const flatten = (node: TreeNode, parentId: string | null) => {
        threads[node.thread.id] = node.thread
        if (parentId && node.thread.fork_source_message_id) {
          flowEdges.push({
            id: `edge-${node.thread.id}`,
            source: parentId,
            target: node.thread.id,
            sourceHandle: 'out',
            type: 'branch',
          })
        }
        node.children.forEach(child => flatten(child, node.thread.id))
      }
      flatten(tree, null)
      layoutNode(tree, 100, 300, nodePositions)

      const messageEntries = await Promise.all(
        Object.keys(threads).map(async tid => {
          const msgs = await getMessages(tid)
          return [tid, msgs] as [string, Message[]]
        })
      )

      set({
        threads,
        nodePositions,
        flowEdges,
        messages: Object.fromEntries(messageEntries),
        isLoadingConversation: false,
      })
    } catch (err) {
      console.error('Failed to load conversation tree:', err)
      set({ isLoadingConversation: false })
    }
  },

  createConversation: async (label?: string) => {
    const thread = await apiCreateThread(label)
    set(state => ({
      conversations: [thread, ...state.conversations],
      activeConversationId: thread.id,
      threads: { [thread.id]: thread },
      messages: { [thread.id]: [] },
      nodePositions: { [thread.id]: { x: 100, y: 300 } },
      flowEdges: [],
      streamingThreadId: null,
      streamingContent: '',
    }))
    return thread
  },

  addThread: (thread, parentThreadId, forkMessageId, parentPos) => {
    set(state => ({
      threads: { ...state.threads, [thread.id]: thread },
      messages: { ...state.messages, [thread.id]: [] },
      nodePositions: {
        ...state.nodePositions,
        [thread.id]: { x: parentPos.x + 480, y: parentPos.y + 160 },
      },
      flowEdges: [
        ...state.flowEdges,
        {
          id: `edge-${thread.id}`,
          source: parentThreadId,
          target: thread.id,
          sourceHandle: 'out' as const,
          type: 'branch' as const,
        },
      ],
    }))
  },

  addMessage: (message: Message) => {
    set(state => ({
      messages: {
        ...state.messages,
        [message.thread_id]: [
          ...(state.messages[message.thread_id] ?? []),
          message,
        ],
      },
    }))
  },

  appendStreamChunk: (thread_id: string, chunk: string) => {
    set(state => ({
      streamingThreadId: thread_id,
      streamingContent:
        state.streamingThreadId === thread_id
          ? state.streamingContent + chunk
          : chunk,
    }))
  },

  // Replace the full message list for a thread once streaming is complete.
  finalizeStream: (thread_id: string, messages: Message[]) => {
    set(state => ({
      messages: { ...state.messages, [thread_id]: messages },
      streamingThreadId: null,
      streamingContent: '',
    }))
  },

  setNodePosition: (thread_id: string, pos: { x: number; y: number }) => {
    set(state => ({
      nodePositions: { ...state.nodePositions, [thread_id]: pos },
    }))
  },

  addMergeArtifact: (message: Message) => {
    set(state => ({
      messages: {
        ...state.messages,
        [message.thread_id]: [
          ...(state.messages[message.thread_id] ?? []),
          message,
        ],
      },
    }))
  },
}))
