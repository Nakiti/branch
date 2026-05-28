'use client'

import { useEffect } from 'react'
import { ConversationSidebar } from './conversation-sidebar'
import { BranchCanvas } from './branch-canvas'
import { useStore } from '@/store/useStore'

export default function BranchApp() {
  const loadConversations = useStore(s => s.loadConversations)

  useEffect(() => {
    loadConversations().catch(console.error)
  }, [loadConversations])

  return (
    <div className="flex h-screen w-full bg-background text-foreground">
      <ConversationSidebar />
      <BranchCanvas />
    </div>
  )
}
