import { useCallback, useEffect, useRef, useState } from 'react'
import { errorMessage } from '../api/client'

export interface Fetched<T> {
  data: T | null
  error: string | null
  loading: boolean
  reload: () => void
  setData: (v: T | null) => void
}

/** Loads data when `deps` change; ignores answers that arrive after a newer request (no stale flashes). */
export function useFetch<T>(fn: () => Promise<T>, deps: unknown[]): Fetched<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)
  const latest = useRef(0)

  useEffect(() => {
    const id = ++latest.current
    setLoading(true)
    setError(null)
    fn()
      .then((d) => { if (id === latest.current) setData(d) })
      .catch((e) => { if (id === latest.current) setError(errorMessage(e)) })
      .finally(() => { if (id === latest.current) setLoading(false) })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])

  const reload = useCallback(() => setTick((t) => t + 1), [])
  return { data, error, loading, reload, setData }
}
