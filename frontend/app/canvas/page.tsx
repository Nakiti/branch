import dynamic from 'next/dynamic'

const BranchApp = dynamic(() => import('@/components/branch-app'), { ssr: false })

export default function CanvasPage() {
  return <BranchApp />
}
