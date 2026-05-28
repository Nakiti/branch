'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'

export default function AuthPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handle = async (mode: 'signin' | 'signup') => {
    setError(null)
    setLoading(true)
    try {
      const { error } =
        mode === 'signin'
          ? await supabase.auth.signInWithPassword({ email, password })
          : await supabase.auth.signUp({ email, password })
      if (error) {
        setError(error.message)
      } else {
        router.push('/canvas')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-sm bg-white rounded-xl shadow-sm border border-gray-100 p-8 space-y-5">
        <div className="flex items-center gap-2 mb-1">
          <div className="h-7 w-7 rounded-md bg-indigo-500/15 flex items-center justify-center">
            <span className="text-indigo-500 text-base">⎇</span>
          </div>
          <span className="text-base font-semibold tracking-tight">Branch</span>
        </div>

        <div className="space-y-3">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-indigo-400 transition-colors"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handle('signin')}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-indigo-400 transition-colors"
          />
        </div>

        {error && (
          <p className="text-xs text-red-500">{error}</p>
        )}

        <div className="flex gap-2">
          <button
            onClick={() => handle('signin')}
            disabled={loading || !email || !password}
            className="flex-1 py-2 text-sm font-medium bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 disabled:opacity-50 transition-colors"
          >
            Sign in
          </button>
          <button
            onClick={() => handle('signup')}
            disabled={loading || !email || !password}
            className="flex-1 py-2 text-sm font-medium border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            Sign up
          </button>
        </div>
      </div>
    </div>
  )
}
