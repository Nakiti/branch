'use client'

import { memo, useState, useRef, useEffect } from 'react'
import { Handle, Position, type NodeProps, useReactFlow } from 'reactflow'
import { GitBranch, GitMerge, Minus, Maximize2, Send } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useStore } from '@/store/useStore'
import { sendMessage, forkThread, mergeBack, getMessages } from '@/lib/api'
import { supabase } from '@/lib/supabase'
import type { ThreadNodeData, Message } from '@/types'

function MessageRow({
  message,
  sourceLabel,
  onBranch,
}: {
  message: Message
  sourceLabel?: string
  onBranch: (msgId: string) => void
}) {
  const isUser = message.role === 'user' && !message.is_merge_artifact
  const isMerge = message.is_merge_artifact

  return (
    <div
      className={cn(
        'group/msg relative flex w-full',
        isUser ? 'justify-end' : 'justify-start'
      )}
      data-message-id={message.id}
    >
      <div
        className={cn(
          'max-w-[90%] px-3.5 py-2.5 text-[13px] leading-relaxed relative',
          isUser &&
            'bg-user-bubble text-user-bubble-foreground rounded-2xl rounded-tr-md',
          !isUser &&
            !isMerge &&
            'bg-assistant-bubble text-assistant-bubble-foreground rounded-2xl rounded-tl-md',
          isMerge &&
            'bg-merge-bubble text-merge-bubble-foreground rounded-2xl rounded-tl-md border border-merge-bubble-foreground/15'
        )}
      >
        <div className="whitespace-pre-wrap">{message.content}</div>

        {isMerge && (
          <div className="mt-2 pt-2 border-t border-merge-bubble-foreground/15 flex items-center justify-between gap-2 text-[11px]">
            <span className="inline-flex items-center gap-1 font-medium">
              <GitMerge className="h-3 w-3" />
              Merged from: {sourceLabel ?? 'branch'}
            </span>
          </div>
        )}

        {!isUser && !isMerge && (
          <button
            onClick={() => onBranch(message.id)}
            className="absolute -bottom-2 -right-1 opacity-0 group-hover/msg:opacity-100 transition-opacity bg-card border border-border shadow-sm rounded-full px-2 py-0.5 text-[10px] font-medium text-primary hover:bg-accent flex items-center gap-1"
          >
            <GitBranch className="h-2.5 w-2.5" />
            Branch
          </button>
        )}

        <Handle
          type="source"
          position={Position.Right}
          id={`msg-${message.id}`}
          style={{ right: -4, top: '50%' }}
        />
      </div>
    </div>
  )
}

function MergePopover({
  onConfirm,
  onClose,
  isMerging,
}: {
  onConfirm: () => void
  onClose: () => void
  isMerging: boolean
}) {
  return (
    <div className="absolute top-full right-0 mt-2 w-64 bg-popover border border-border rounded-lg shadow-card-hover p-3 z-50">
      <div className="text-[13px] font-medium text-foreground mb-1">
        Synthesize back to parent?
      </div>
      <div className="text-[11px] text-muted-foreground mb-3">
        A merge artifact will appear in the parent thread.
      </div>
      <div className="flex justify-end gap-2">
        <button
          onClick={onClose}
          disabled={isMerging}
          className="px-2.5 py-1 text-[11px] rounded-md hover:bg-accent text-muted-foreground disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          onClick={onConfirm}
          disabled={isMerging}
          className="px-2.5 py-1 text-[11px] rounded-md bg-primary text-primary-foreground hover:bg-primary/90 font-medium disabled:opacity-50"
        >
          {isMerging ? 'Merging…' : 'Confirm'}
        </button>
      </div>
    </div>
  )
}

function ThreadNodeImpl({ id, data }: NodeProps<ThreadNodeData>) {
  const [collapsed, setCollapsed] = useState(false)
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [isMerging, setIsMerging] = useState(false)
  const [mergePopover, setMergePopover] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const { getNode, setCenter } = useReactFlow()
  const nodePositions = useStore(s => s.nodePositions)
  const threads = useStore(s => s.threads)
  const messages = useStore(s => s.messages[id] ?? [])
  const streamingThreadId = useStore(s => s.streamingThreadId)
  const streamingContent = useStore(s => s.streamingContent)
  const addMessage = useStore(s => s.addMessage)
  const appendStreamChunk = useStore(s => s.appendStreamChunk)
  const finalizeStream = useStore(s => s.finalizeStream)
  const addThread = useStore(s => s.addThread)
  const addMergeArtifact = useStore(s => s.addMergeArtifact)

  const isStreaming = streamingThreadId === id
  const isRoot = data.thread.fork_source_message_id === null

  // Scroll to bottom when messages or streaming content changes
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, isStreaming, streamingContent])

  const handleSend = async () => {
    const content = input.trim()
    if (!content || isSending) return
    setInput('')
    setIsSending(true)

    addMessage({
      id: `optimistic-${Date.now()}`,
      thread_id: id,
      role: 'user',
      content,
      is_merge_artifact: false,
      merge_source_thread_ids: [],
      created_at: new Date().toISOString(),
    })

    try {
      for await (const chunk of sendMessage(id, content)) {
        appendStreamChunk(id, chunk)
      }
      const persisted = await getMessages(id)
      finalizeStream(id, persisted)
    } catch (e) {
      console.error('Send failed:', e)
    } finally {
      setIsSending(false)
    }
  }

  const handleBranch = async (msgId: string) => {
    try {
      const { thread_id } = await forkThread(msgId)
      const { data: { session } } = await supabase.auth.getSession()
      const parentPos = nodePositions[id] ?? { x: 0, y: 0 }

      addThread(
        {
          id: thread_id,
          owner_id: session?.user.id ?? '',
          label: null,
          fork_source_message_id: msgId,
          created_at: new Date().toISOString(),
        },
        id,
        msgId,
        parentPos
      )

      const newPos = { x: parentPos.x + 480, y: parentPos.y + 160 }
      setTimeout(
        () => setCenter(newPos.x + 180, newPos.y + 160, { zoom: 1, duration: 600 }),
        50
      )
    } catch (e) {
      console.error('Branch failed:', e)
    }
  }

  const handleMerge = async () => {
    setIsMerging(true)
    try {
      const artifact = await mergeBack(id)
      addMergeArtifact(artifact)
      setMergePopover(false)
    } catch (e) {
      console.error('Merge failed:', e)
    } finally {
      setIsMerging(false)
    }
  }

  return (
    <div
      className={cn(
        'w-[360px] bg-card border border-border rounded-xl overflow-hidden',
        'shadow-card hover:shadow-card-hover transition-shadow'
      )}
    >
      {/* Drag handle / header */}
      <div className="drag-handle cursor-grab active:cursor-grabbing px-3.5 py-2.5 border-b border-border bg-card flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div
            className={cn(
              'h-1.5 w-1.5 rounded-full shrink-0',
              isRoot ? 'bg-primary' : 'bg-primary/50'
            )}
          />
          <span className="text-[13px] font-semibold truncate">
            {data.thread.label ?? (isRoot ? 'Main' : 'Branch')}
          </span>
          {!isRoot && (
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
              branch
            </span>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0 relative">
          {!isRoot && (
            <>
              <button
                onClick={() => setMergePopover(v => !v)}
                className="text-[11px] flex items-center gap-1 px-2 py-0.5 rounded-md text-primary hover:bg-accent font-medium nodrag"
              >
                <GitMerge className="h-3 w-3" />
                Merge back
              </button>
              {mergePopover && (
                <MergePopover
                  onConfirm={handleMerge}
                  onClose={() => setMergePopover(false)}
                  isMerging={isMerging}
                />
              )}
            </>
          )}
          <button
            onClick={() => setCollapsed(v => !v)}
            className="p-1 rounded-md hover:bg-accent text-muted-foreground nodrag"
            title={collapsed ? 'Expand' : 'Collapse'}
          >
            {collapsed ? <Maximize2 className="h-3 w-3" /> : <Minus className="h-3 w-3" />}
          </button>
        </div>
      </div>

      {!collapsed && (
        <>
          <div className="max-h-[400px] overflow-y-auto px-3.5 py-3 space-y-3 nodrag nowheel">
            {messages.map(m => (
              <MessageRow
                key={m.id}
                message={m}
                sourceLabel={
                  m.is_merge_artifact && m.merge_source_thread_ids?.[0]
                    ? (threads[m.merge_source_thread_ids[0]]?.label ?? 'branch')
                    : undefined
                }
                onBranch={handleBranch}
              />
            ))}

            {/* Streaming in-progress indicator */}
            {isStreaming && streamingContent && (
              <div className="flex justify-start">
                <div className="max-w-[90%] px-3.5 py-2.5 text-[13px] leading-relaxed bg-assistant-bubble text-assistant-bubble-foreground rounded-2xl rounded-tl-md whitespace-pre-wrap opacity-80">
                  {streamingContent}
                  <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-current opacity-60 animate-pulse align-text-bottom" />
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          <div className="border-t border-border p-2.5 flex items-center gap-2 bg-card nodrag">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
              placeholder="Reply…"
              disabled={isSending || isStreaming}
              className="flex-1 bg-input/60 border border-border rounded-lg px-3 py-1.5 text-[13px] outline-none focus:border-ring focus:bg-card transition-colors disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isSending || isStreaming}
              className="h-8 w-8 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 flex items-center justify-center transition-colors shrink-0 disabled:opacity-50"
            >
              <Send className="h-3.5 w-3.5" />
            </button>
          </div>
        </>
      )}

      <Handle type="target" position={Position.Left} id="in" style={{ left: -4 }} />
    </div>
  )
}

export const ThreadNode = memo(ThreadNodeImpl)
