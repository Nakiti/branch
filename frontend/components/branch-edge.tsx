'use client'

import { BaseEdge, getBezierPath, type EdgeProps, EdgeLabelRenderer } from 'reactflow'

export function BranchEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
}: EdgeProps) {
  const [path, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  })

  return (
    <>
      <BaseEdge id={id} path={path} markerEnd={markerEnd} />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            pointerEvents: 'all',
          }}
          className="bg-card border border-border shadow-sm rounded-full h-6 w-6 flex items-center justify-center text-primary text-[12px] font-medium"
        >
          ⎇
        </div>
      </EdgeLabelRenderer>
    </>
  )
}
