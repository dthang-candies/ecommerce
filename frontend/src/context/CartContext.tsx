import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api } from '../api/client'
import type { Cart } from '../api/types'
import { useAuth } from './AuthContext'
import { usePrefs } from './PrefsContext'

interface CartState {
  cart: Cart | null
  count: number
  loading: boolean
  refresh: () => Promise<void>
  add: (productId: number, quantity?: number, source?: string) => Promise<void>
  setQuantity: (productId: number, quantity: number) => Promise<void>
  remove: (productId: number) => Promise<void>
}
const Ctx = createContext<CartState | null>(null)

export function CartProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const { personalize } = usePrefs()
  const [cart, setCart] = useState<Cart | null>(null)
  const [loading, setLoading] = useState(false)
  const isCustomer = user?.role === 'CUSTOMER'

  const refresh = useCallback(async () => {
    if (!isCustomer) { setCart(null); return }
    setLoading(true)
    try { setCart(await api.get<Cart>('/cart')) } finally { setLoading(false) }
  }, [isCustomer])

  useEffect(() => { refresh().catch(() => {}) }, [refresh])

  const value = useMemo<CartState>(() => ({
    cart, loading, count: cart?.item_count ?? 0, refresh,
    add: async (productId, quantity = 1, source) => setCart(await api.post<Cart>('/cart/items', { product_id: productId, quantity, source, track: personalize })),
    setQuantity: async (productId, quantity) => setCart(await api.patch<Cart>(`/cart/items/${productId}`, { quantity })),
    remove: async (productId) => setCart(await api.del<Cart>(`/cart/items/${productId}`)),
  }), [cart, loading, refresh, personalize])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useCart(): CartState {
  const v = useContext(Ctx)
  if (!v) throw new Error('useCart must be used inside CartProvider')
  return v
}
