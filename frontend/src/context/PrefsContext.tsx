import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { api } from '../api/client'

const KEY = 'unicart.personalize'
const read = () => { try { return localStorage.getItem(KEY) !== 'off' } catch { return true } }

interface Prefs {
  personalize: boolean
  setPersonalize: (on: boolean) => void
  /** Reports an interaction for the recommender (UC-16). Does nothing when the user switched personalisation off (NFR-13). */
  track: (event_type: 'VIEW' | 'SEARCH' | 'CLICK_REC' | 'REC_IMPRESSION', data?: { product_id?: number; keyword?: string }) => void
}
const Ctx = createContext<Prefs | null>(null)

export function PrefsProvider({ children }: { children: ReactNode }) {
  const [personalize, set] = useState(read)
  const setPersonalize = useCallback((on: boolean) => {
    set(on)
    try { localStorage.setItem(KEY, on ? 'on' : 'off') } catch { /* ignore */ }
  }, [])
  const track = useCallback<Prefs['track']>((event_type, data) => {
    if (!personalize) return
    api.post('/events', { event_type, ...data }).catch(() => {})
  }, [personalize])
  const value = useMemo(() => ({ personalize, setPersonalize, track }), [personalize, setPersonalize, track])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function usePrefs(): Prefs {
  const v = useContext(Ctx)
  if (!v) throw new Error('usePrefs must be used inside PrefsProvider')
  return v
}

/** Remember which recommendation block led to a product so "add to cart" can be attributed (FR-18). */
export const recSource = {
  set(productId: number, placement: string) { try { sessionStorage.setItem(`rec.${productId}`, placement) } catch { /* ignore */ } },
  get(productId: number): string | undefined { try { return sessionStorage.getItem(`rec.${productId}`) ?? undefined } catch { return undefined } },
}
