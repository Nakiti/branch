import { supabase } from './supabase'
import type { Message, Thread, TreeNode } from '@/types'

const BACKEND_URL = (process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000').replace(/\/$/, '')

async function getAuthHeader(): Promise<Record<string, string>> {
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) throw new Error('Not authenticated')
  return { Authorization: `Bearer ${session.access_token}` }
}

/** Stream a chat response — yields text chunks as they arrive from the SSE endpoint.
 *  If the backend sends a [LABEL:...] event (first message of a root thread),
 *  onLabel is called with the generated label instead of yielding it as text. */
export async function* sendMessage(
  thread_id: string,
  content: string,
  onLabel?: (label: string) => void
): AsyncGenerator<string> {
  const headers = await getAuthHeader()
  const response = await fetch(`${BACKEND_URL}/api/chat`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id, content }),
  })
  if (!response.ok) throw new Error(`Chat failed: ${response.statusText}`)

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    for (const line of decoder.decode(value).split('\n')) {
      if (!line.startsWith('data: ')) continue
      const data = line.slice(6)
      if (data === '[DONE]') continue
      if (data.startsWith('[LABEL:') && data.endsWith(']')) {
        onLabel?.(data.slice(7, -1))
        continue
      }
      yield data
    }
  }
}

export async function forkThread(message_id: string): Promise<{ thread_id: string; label: string | null }> {
  const headers = await getAuthHeader()
  const res = await fetch(`${BACKEND_URL}/api/fork`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ message_id }),
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
    body: JSON.stringify({ branch_thread_id }),
  })
  if (!res.ok) throw new Error(`Merge failed: ${res.statusText}`)
  const data = await res.json()
  return data.message
}

export async function createThread(label?: string): Promise<Thread> {
  const headers = await getAuthHeader()
  const res = await fetch(`${BACKEND_URL}/api/threads`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ label: label ?? 'New Conversation' }),
  })
  if (!res.ok) throw new Error(`Create thread failed: ${res.statusText}`)
  return res.json()
}

export async function getRootThreads(): Promise<Thread[]> {
  const headers = await getAuthHeader()
  const res = await fetch(`${BACKEND_URL}/api/threads`, { headers })
  if (!res.ok) throw new Error(`Fetch threads failed: ${res.statusText}`)
  return res.json()
}

export async function getMessages(thread_id: string): Promise<Message[]> {
  const headers = await getAuthHeader()
  const res = await fetch(`${BACKEND_URL}/api/threads/${thread_id}/messages`, { headers })
  if (!res.ok) throw new Error(`Fetch messages failed: ${res.statusText}`)
  return res.json()
}

export async function deleteThread(thread_id: string): Promise<{ deleted: string[] }> {
  const headers = await getAuthHeader()
  const res = await fetch(`${BACKEND_URL}/api/threads/${thread_id}`, {
    method: 'DELETE',
    headers,
  })
  if (!res.ok) throw new Error(`Delete thread failed: ${res.statusText}`)
  return res.json()
}
