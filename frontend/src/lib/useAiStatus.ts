import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { AiStatus } from '../api/types'

let cached: Promise<AiStatus> | null = null

/** Whether AI search is switched on (so the microphone / camera buttons are shown only when they can work). */
export function useAiStatus(): AiStatus | null {
  const [status, setStatus] = useState<AiStatus | null>(null)
  useEffect(() => {
    cached ??= api.get<AiStatus>('/search/status')
    let live = true
    cached.then((s) => live && setStatus(s)).catch(() => { cached = null })
    return () => { live = false }
  }, [])
  return status
}
