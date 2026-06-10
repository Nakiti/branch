'use client'

import { memo, useState, useRef, useEffect } from 'react'
import { Handle, Position, type NodeProps, useReactFlow } from 'reactflow'
import { GitBranch, GitMerge, Minus, Maximize2, Send, Trash2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { cn } from '@/lib/utils'
import { useStore } from '@/store/useStore'
import { sendMessage, forkThread, mergeBack, multiMergeBack, getMessages } from '@/lib/api'
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
        {isUser ? (
          <div className="whitespace-pre-wrap">{message.content}</div>
        ) : (
          <div className="prose prose-sm max-w-none prose-p:my-1 prose-pre:my-1 prose-ul:my-1 prose-ol:my-1 prose-headings:my-1 prose-code:before:content-none prose-code:after:content-none">
            <ReactMarkdown
              components={{
                code({ className, children, ...props }) {
                  const isBlock = className?.startsWith('language-')
                  return isBlock ? (
                    <pre className="bg-black/10 rounded-md px-3 py-2 overflow-x-auto text-[12px]">
                      <code className={className} {...props}>{children}</code>
                    </pre>
                  ) : (
                    <code className="bg-black/10 rounded px-1 text-[12px]" {...props}>{children}</code>
                  )
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {isMerge && (
          <div className="mt-2 pt-2 border-t border-merge-bubble-foreground/15 flex items-center gap-2 text-[11px]">
            <span className="inline-flex items-center gap-1 font-medium">
              <GitMerge className="h-3 w-3" />
              {(message.merge_source_thread_ids?.length ?? 0) > 1
                ? `Merged from ${message.merge_source_thread_ids!.length} branches`
                : `Merged from: ${sourceLabel ?? 'branch'}`}
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

function MultiMergePopover({
  branchIds,
  onConfirm,
  onClose,
  isMerging,
}: {
  branchIds: string[]
  onConfirm: (selectedIds: string[]) => void
  onClose: () => void
  isMerging: boolean
}) {
  const threads = useStore(s => s.threads)
  const [selected, setSelected] = useState<Set<string>>(new Set(branchIds))

  const toggle = (id: string) =>
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  return (
    <div className="absolute top-full right-0 mt-2 w-72 bg-popover border border-border rounded-lg shadow-card-hover p-3 z-50">
      <div className="text-[13px] font-medium text-foreground mb-1">Compare branches</div>
      <div className="text-[11px] text-muted-foreground mb-2">
        Select branches to synthesize into this thread:
      </div>
      <div className="space-y-1.5 mb-3">
        {branchIds.map(id => (
          <label key={id} className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={selected.has(id)}
              onChange={() => toggle(id)}
              disabled={isMerging}
              className="accent-primary"
            />
            <span className="text-[12px] truncate">{threads[id]?.label ?? 'Branch'}</span>
          </label>
        ))}
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
          onClick={() => onConfirm([...selected])}
          disabled={isMerging || selected.size < 2}
          className="px-2.5 py-1 text-[11px] rounded-md bg-primary text-primary-foreground hover:bg-primary/90 font-medium disabled:opacity-50"
        >
          {isMerging ? 'Merging…' : 'Synthesize'}
        </button>
      </div>
    </div>
  )
}

function DeletePopover({
  label,
  onConfirm,
  onClose,
  isDeleting,
}: {
  label: string
  onConfirm: () => void
  onClose: () => void
  isDeleting: boolean
}) {
  return (
    <div className="absolute top-full right-0 mt-2 w-56 bg-popover border border-border rounded-lg shadow-card-hover p-3 z-50">
      <div className="text-[13px] font-medium text-foreground mb-1">{label}</div>
      <div className="text-[11px] text-muted-foreground mb-3">This cannot be undone.</div>
      <div className="flex justify-end gap-2">
        <button
          onClick={onClose}
          disabled={isDeleting}
          className="px-2.5 py-1 text-[11px] rounded-md hover:bg-accent text-muted-foreground disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          onClick={onConfirm}
          disabled={isDeleting}
          className="px-2.5 py-1 text-[11px] rounded-md bg-destructive text-destructive-foreground hover:bg-destructive/90 font-medium disabled:opacity-50"
        >
          {isDeleting ? 'Deleting…' : 'Delete'}
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
  const [deletePopover, setDeletePopover] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [multiMergePopover, setMultiMergePopover] = useState(false)
  const [isMultiMerging, setIsMultiMerging] = useState(false)
  const [size, setSize] = useState({ width: 600, height: 500 })
  const bottomRef = useRef<HTMLDivElement>(null)

  const { setCenter } = useReactFlow()
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
  const deleteThread = useStore(s => s.deleteThread)
  const updateThreadLabel = useStore(s => s.updateThreadLabel)

  const liveThread = useStore(s => s.threads[id])
  const flowEdges = useStore(s => s.flowEdges)
  const isStreaming = streamingThreadId === id
  const isRoot = data.thread.fork_source_message_id === null
  const label = liveThread?.label ?? data.thread.label
  const branchChildIds = flowEdges.filter(e => e.source === id).map(e => e.target)
  const hasMultipleBranches = branchChildIds.length >= 2

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length, isStreaming, streamingContent])

  const startResize = (e: React.MouseEvent) => {
    e.stopPropagation()
    e.preventDefault()
    const x0 = e.clientX
    const y0 = e.clientY
    const w0 = size.width
    const h0 = size.height
    const onMove = (ev: MouseEvent) => setSize({
      width: Math.max(280, w0 + ev.clientX - x0),
      height: Math.max(80, h0 + ev.clientY - y0),
    })
    const onUp = () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

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
      for await (const chunk of sendMessage(id, content, label => updateThreadLabel(id, label))) {
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
      const { thread_id, label } = await forkThread(msgId)
      const { data: { session } } = await supabase.auth.getSession()
      const parentPos = nodePositions[id] ?? { x: 0, y: 0 }

      addThread(
        {
          id: thread_id,
          owner_id: session?.user.id ?? '',
          label: label ?? null,
          fork_source_message_id: msgId,
          created_at: new Date().toISOString(),
        },
        id,
        msgId,
        parentPos
      )

      const newPos = { x: parentPos.x + 600, y: parentPos.y + 160 }
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

  const handleMultiMerge = async (selectedIds: string[]) => {
    setIsMultiMerging(true)
    try {
      const artifact = await multiMergeBack(selectedIds)
      addMergeArtifact(artifact)
      setMultiMergePopover(false)
    } catch (e) {
      console.error('Multi-merge failed:', e)
    } finally {
      setIsMultiMerging(false)
    }
  }

  const handleDelete = async () => {
    setIsDeleting(true)
    try {
      await deleteThread(id)
    } catch (e) {
      console.error('Delete failed:', e)
      setIsDeleting(false)
      setDeletePopover(false)
    }
  }

  return (
    <div
      style={{ width: size.width }}
      className={cn(
        'relative bg-card border border-border rounded-xl overflow-hidden flex flex-col',
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
            {label ?? (isRoot ? 'Main' : 'Branch')}
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
          {hasMultipleBranches && (
            <>
              <button
                onClick={() => { setMultiMergePopover(v => !v); setMergePopover(false); setDeletePopover(false) }}
                className="text-[11px] flex items-center gap-1 px-2 py-0.5 rounded-md text-primary hover:bg-accent font-medium nodrag"
              >
                <GitMerge className="h-3 w-3" />
                Compare
              </button>
              {multiMergePopover && (
                <MultiMergePopover
                  branchIds={branchChildIds}
                  onConfirm={handleMultiMerge}
                  onClose={() => setMultiMergePopover(false)}
                  isMerging={isMultiMerging}
                />
              )}
            </>
          )}
          <button
            onClick={() => { setDeletePopover(v => !v); setMergePopover(false) }}
            className="p-1 rounded-md hover:bg-destructive/10 hover:text-destructive text-muted-foreground nodrag"
            title={isRoot ? 'Delete conversation' : 'Delete branch'}
          >
            <Trash2 className="h-3 w-3" />
          </button>
          {deletePopover && (
            <DeletePopover
              label={isRoot ? 'Delete this conversation?' : 'Delete this branch?'}
              onConfirm={handleDelete}
              onClose={() => setDeletePopover(false)}
              isDeleting={isDeleting}
            />
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
          <div
            style={{ height: size.height }}
            className="overflow-y-auto px-3.5 py-3 space-y-3 nodrag nowheel"
          >
            {messages.length === 0 && !isStreaming && (
              <div className="flex flex-col items-center justify-center h-full gap-2 text-center py-8 select-none pointer-events-none">
                <div className="text-2xl opacity-30">⎇</div>
                <p className="text-[13px] font-medium text-muted-foreground">
                  {isRoot ? 'Start a new conversation' : 'Continue this branch'}
                </p>
                <p className="text-[11px] text-muted-foreground/60">
                  Type a message below to get started
                </p>
              </div>
            )}

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

            {(isSending && !isStreaming) || (isStreaming && !streamingContent) ? (
              <div className="flex justify-start">
                <div className="px-3.5 py-3 bg-assistant-bubble text-assistant-bubble-foreground rounded-2xl rounded-tl-md flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-current opacity-50 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-current opacity-50 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-current opacity-50 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            ) : null}

            {isStreaming && streamingContent && (
              <div className="flex justify-start">
                <div className="max-w-[90%] px-3.5 py-2.5 text-[13px] leading-relaxed bg-assistant-bubble text-assistant-bubble-foreground rounded-2xl rounded-tl-md opacity-80">
                  <div className="prose prose-sm max-w-none prose-p:my-1 prose-pre:my-1 prose-ul:my-1 prose-ol:my-1 prose-headings:my-1 prose-code:before:content-none prose-code:after:content-none">
                    <ReactMarkdown
                      components={{
                        code({ className, children, ...props }) {
                          const isBlock = className?.startsWith('language-')
                          return isBlock ? (
                            <pre className="bg-black/10 rounded-md px-3 py-2 overflow-x-auto text-[12px]">
                              <code className={className} {...props}>{children}</code>
                            </pre>
                          ) : (
                            <code className="bg-black/10 rounded px-1 text-[12px]" {...props}>{children}</code>
                          )
                        },
                      }}
                    >
                      {streamingContent}
                    </ReactMarkdown>
                  </div>
                  <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-current opacity-60 animate-pulse align-text-bottom" />
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="p-2.5 flex items-center gap-2 bg-card nodrag">
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

      {/* Diagonal resize handle */}
      <div
        onMouseDown={startResize}
        className="nodrag absolute bottom-0 right-0 w-5 h-5 flex items-end justify-end p-1 cursor-nwse-resize opacity-25 hover:opacity-60 transition-opacity"
      >
        <svg width="8" height="8" viewBox="0 0 8 8" fill="currentColor" className="text-foreground">
          <circle cx="6.5" cy="6.5" r="1.1" />
          <circle cx="3.5" cy="6.5" r="1.1" />
          <circle cx="6.5" cy="3.5" r="1.1" />
        </svg>
      </div>

      <Handle type="target" position={Position.Left} id="in" style={{ left: -5, top: '50%' }} />
      <Handle type="source" position={Position.Right} id="out" style={{ right: -5, top: '50%' }} />
    </div>
  )
}

export const ThreadNode = memo(ThreadNodeImpl)
