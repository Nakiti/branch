'use client'

import { Plus, MessageSquare, LogOut } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useStore } from '@/store/useStore'
import { supabase } from '@/lib/supabase'
import { useRouter } from 'next/navigation'

export function ConversationSidebar() {
  const router = useRouter()
  const conversations = useStore(s => s.conversations)
  const activeId = useStore(s => s.activeConversationId)
  const setActive = useStore(s => s.setActiveConversation)
  const createConversation = useStore(s => s.createConversation)

  const handleNew = async () => {
    try {
      await createConversation()
    } catch (e) {
      console.error('Failed to create conversation:', e)
    }
  }

  const handleSignOut = async () => {
    await supabase.auth.signOut()
    router.push('/auth')
  }

  return (
    <aside className="w-[260px] shrink-0 border-r border-sidebar-border bg-sidebar flex flex-col">
      <div className="px-4 py-4 border-b border-sidebar-border">
        <div className="flex items-center gap-2 mb-3">
          <div className="h-6 w-6 rounded-md bg-primary/15 flex items-center justify-center">
            <span className="text-primary text-sm">⎇</span>
          </div>
          <span className="text-sm font-semibold tracking-tight">Branch</span>
        </div>
        <button
          onClick={handleNew}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium"
        >
          <Plus className="h-4 w-4" />
          New Conversation
        </button>
      </div>

      <div className="px-3 pt-3 pb-1 text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
        Conversations
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-0.5">
        {conversations.map(c => (
          <button
            key={c.id}
            onClick={() => setActive(c.id)}
            className={cn(
              'w-full text-left px-3 py-2 rounded-lg flex items-start gap-2.5 transition-colors group',
              activeId === c.id
                ? 'bg-accent text-accent-foreground'
                : 'hover:bg-accent/60 text-sidebar-foreground'
            )}
          >
            <MessageSquare className="h-4 w-4 mt-0.5 shrink-0 opacity-70" />
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium truncate">
                {c.label ?? 'Untitled'}
              </div>
              <div className="text-[11px] text-muted-foreground mt-0.5">
                {new Date(c.created_at).toLocaleDateString()}
              </div>
            </div>
          </button>
        ))}
      </div>

      <div className="px-3 py-3 border-t border-sidebar-border">
        <button
          onClick={handleSignOut}
          className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
        >
          <LogOut className="h-3.5 w-3.5" />
          Sign out
        </button>
      </div>
    </aside>
  )
}
