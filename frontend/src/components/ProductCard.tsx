import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { errorMessage } from '../api/client'
import type { Product, Recommendation } from '../api/types'
import { useAuth } from '../context/AuthContext'
import { useCart } from '../context/CartContext'
import { recSource, usePrefs } from '../context/PrefsContext'
import { useToast } from '../context/ToastContext'
import { money } from '../lib/format'
import ProductImage from './ProductImage'
import { Stars } from './ui'

/** `placement` is set when the card is part of a recommendation block, so clicks and add-to-cart can be measured. */
export default function ProductCard({ product, placement }: { product: Product | Recommendation; placement?: string }) {
  const { user } = useAuth()
  const { add } = useCart()
  const { track } = usePrefs()
  const toast = useToast()
  const nav = useNavigate()
  const loc = useLocation()
  const [busy, setBusy] = useState(false)
  const reason = 'reason' in product ? product.reason : null

  const onOpen = () => {
    if (placement) { recSource.set(product.id, placement); track('CLICK_REC', { product_id: product.id, keyword: placement }) }
  }
  const onAdd = async () => {
    if (!user) return nav('/dang-nhap', { state: { from: loc.pathname + loc.search } })
    if (user.role !== 'CUSTOMER') return toast.info('Tài khoản nhân viên không thể mua hàng')
    setBusy(true)
    try { await add(product.id, 1, placement); toast.success('Đã thêm vào giỏ hàng') } catch (e) { toast.error(errorMessage(e)) } finally { setBusy(false) }
  }

  return (
    <article className="card group flex flex-col overflow-hidden transition hover:-translate-y-0.5 hover:shadow-md">
      <Link to={`/san-pham/${product.id}`} onClick={onOpen} className="relative block">
        <ProductImage product={product} className="aspect-[4/3] w-full transition group-hover:scale-[1.02]" />
        {!product.in_stock && <span className="absolute left-2 top-2 rounded-full bg-slate-900/80 px-2.5 py-0.5 text-xs font-semibold text-white">Hết hàng</span>}
        {reason && product.in_stock && <span className="absolute left-2 top-2 rounded-full bg-brand-600 px-2.5 py-0.5 text-xs font-semibold text-white shadow">{reason}</span>}
      </Link>
      <div className="flex flex-1 flex-col p-3">
        <p className="text-xs text-slate-500">{product.brand ?? product.category.name}</p>
        <Link to={`/san-pham/${product.id}`} onClick={onOpen} className="mt-0.5 line-clamp-2 min-h-10 text-sm font-semibold text-slate-900 hover:text-brand-700">{product.name}</Link>
        {product.rating && product.rating.count > 0 && (
          <div className="mt-1 flex items-center gap-1 text-xs text-slate-500"><Stars value={product.rating.average} size="text-sm" /> ({product.rating.count})</div>
        )}
        <div className="mt-auto flex items-end justify-between gap-2 pt-3">
          <p className="text-base font-bold text-brand-700">{money(product.price)}</p>
          <button className="btn-primary px-3 py-1.5" onClick={onAdd} disabled={busy || !product.in_stock} aria-label={`Thêm ${product.name} vào giỏ hàng`}>
            {busy ? '…' : 'Thêm'}
          </button>
        </div>
      </div>
    </article>
  )
}
