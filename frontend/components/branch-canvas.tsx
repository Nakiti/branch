'use client'

import { useCallback, useEffect, useRef } from 'react'
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  ReactFlowProvider,
  useNodesState,
  useEdgesState,
  useReactFlow,
  type Node,
  type NodeChange,
} from 'reactflow'
import { ThreadNode } from './thread-node'
import { BranchEdge } from './branch-edge'
import { useStore } from '@/store/useStore'
import type { ThreadNodeData } from '@/types'

// Defined outside the component — inline nodeTypes causes infinite re-renders
const nodeTypes = { thread: ThreadNode }
const edgeTypes = { branch: BranchEdge }

function CanvasInner() {
  const { fitView } = useReactFlow()

  const activeConversationId = useStore(s => s.activeConversationId)
  const threads = useStore(s => s.threads)
  const nodePositions = useStore(s => s.nodePositions)
  const flowEdges = useStore(s => s.flowEdges)
  const setNodePosition = useStore(s => s.setNodePosition)
  const isLoading = useStore(s => s.isLoadingConversation)

  const [nodes, setNodes, onNodesChange] = useNodesState<ThreadNodeData>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  const prevActiveId = useRef<string | null>(null)
  const prevThreadIds = useRef(new Set<string>())

  // Rebuild nodes when conversation changes OR when new threads are forked in
  useEffect(() => {
    const threadValues = Object.values(threads)
    const currentIds = new Set(threadValues.map(t => t.id))

    if (activeConversationId !== prevActiveId.current) {
      // Full reload on conversation switch
      prevActiveId.current = activeConversationId
      prevThreadIds.current = currentIds
      setNodes(
        threadValues.map(t => ({
          id: t.id,
          type: 'thread' as const,
          position: nodePositions[t.id] ?? { x: 100, y: 300 },
          data: { thread: t },
          dragHandle: '.drag-handle',
          width: 360,
        }))
      )
      setTimeout(() => fitView({ padding: 0.15, duration: 400, minZoom: 0.75 }), 80)
    } else {
      // Only add nodes that weren't present before (from fork)
      const newThreads = threadValues.filter(t => !prevThreadIds.current.has(t.id))
      if (newThreads.length > 0) {
        prevThreadIds.current = currentIds
        setNodes(prev => [
          ...prev,
          ...newThreads.map(t => ({
            id: t.id,
            type: 'thread' as const,
            position: nodePositions[t.id] ?? { x: 100, y: 300 },
            data: { thread: t },
            dragHandle: '.drag-handle',
            width: 360,
          })),
        ])
      }
    }
  }, [threads, activeConversationId, nodePositions, setNodes, fitView])

  useEffect(() => {
    setEdges(flowEdges)
  }, [flowEdges, setEdges])

  // Intercept position changes and persist to store; let React Flow handle the rest
  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      onNodesChange(changes)
      changes.forEach(c => {
        if (c.type === 'position' && c.position && !c.dragging) {
          setNodePosition(c.id, c.position)
        }
      })
    },
    [onNodesChange, setNodePosition]
  )

  return (
    <div className="flex-1 h-full bg-canvas relative">
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
          <span className="text-sm text-muted-foreground animate-pulse">Loading…</span>
        </div>
      )}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.15, minZoom: 0.75 }}
        minZoom={0.4}
        maxZoom={1.75}
        proOptions={{ hideAttribution: true }}
        nodesDraggable
        panOnDrag
        selectionOnDrag={false}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1.5}
          color="var(--canvas-dot)"
        />
        <Controls position="bottom-right" showInteractive={false} />
      </ReactFlow>
    </div>
  )
}

export function BranchCanvas() {
  return (
    <ReactFlowProvider>
      <CanvasInner />
    </ReactFlowProvider>
  )
}
