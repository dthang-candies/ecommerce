import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, setUnauthorizedHandler, tokenStore } from '../api/client'
import type { Role, Session, User } from '../api/types'

interface AuthState {
  user: User | null
  ready: boolean
  login: (email: string, password: string) => Promise<User>
  register: (data: RegisterData) => Promise<User>
  logout: () => void
}
export interface RegisterData { email: string; password: string; first_name: string; middle_name?: string; last_name: string; phone?: string }

const Ctx = createContext<AuthState | null>(null)
export const STAFF_ROLES: Role[] = ['ADMIN', 'SERVICE', 'SALES', 'WAREHOUSE', 'MARKETING', 'MANAGER']

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  const clear = useCallback(() => { tokenStore.set(null); setUser(null) }, [])

  useEffect(() => {
    setUnauthorizedHandler(clear)
    if (!tokenStore.get()) { setReady(true); return }
    api.get<User & { profile?: { full_name: string } }>('/auth/me')
      .then((me) => setUser({ ...me, full_name: me.profile?.full_name }))
      .catch(clear)
      .finally(() => setReady(true))
  }, [clear])

  const start = (s: Session) => { tokenStore.set(s.access_token); setUser(s.user); return s.user }

  const value = useMemo<AuthState>(() => ({
    user, ready,
    login: async (email, password) => start(await api.post<Session>('/auth/login', { email, password })),
    register: async (data) => start(await api.post<Session>('/auth/register', data)),
    logout: () => { api.post('/auth/logout').catch(() => {}); clear() },
  }), [user, ready, clear])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAuth(): AuthState {
  const v = useContext(Ctx)
  if (!v) throw new Error('useAuth must be used inside AuthProvider')
  return v
}
export const isStaff = (u: User | null) => !!u && u.role !== 'CUSTOMER'
