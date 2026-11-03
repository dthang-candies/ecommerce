import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import type { Recommendation } from '../api/types'
import ProductImage from '../components/ProductImage'
import RecBlock from '../components/RecBlock'
import { Empty, PageTitle, Spinner } from '../components/ui'
import { useCart } from '../context/CartContext'
import { useToast } from '../context/ToastContext'
import { money } from '../lib/format'
import { useFetch } from '../lib/useFetch'
import Icon from '../components/Icon'

export default function CartPage() {
  const { cart, loading, setQuantity, remove } = useCart()
  const toast = useToast()
  const nav = useNavigate()
  const [busyId, setBusyId] = useState<number | null>(null)
  const recs = useFetch(() => api.get<Recommendation[]>('/recommendations/cart'), [cart?.item_count])

  const run = async (id: number, fn: () => Promise<void>) => {
    setBusyId(id)
    try { await fn() } catch (e) { toast.error(errorMessage(e)) } finally { setBusyId(null) }
  }
  if (loading && !cart) return <Spinner />
  if (!cart || cart.items.length === 0) {
    return <Empty icon={<Icon name="cart" size={40} strokeWidth={1.5} />} title="Giỏ hàng của bạn đang trống" hint="Hãy chọn vài sản phẩm bạn yêu thích." action={<Link to="/san-pham" className="btn-primary">Tiếp tục mua sắm</Link>} />
  }
  const blocked = cart.items.some((i) => !i.available)

  return (
    <div>
      <PageTitle title="Giỏ hàng" subtitle={`${cart.item_count} sản phẩm`} />
      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <ul className="space-y-3">
          {cart.items.map((i) => (
            <li key={i.product_id} className={`card flex gap-3 p-3 sm:gap-4 sm:p-4 ${i.available ? '' : 'border-rose-300 bg-rose-50/40'}`}>
              <Link to={`/san-pham/${i.product_id}`} className="shrink-0"><ProductImage product={i} className="h-20 w-20 rounded-xl sm:h-24 sm:w-24" /></Link>
              <div className="flex min-w-0 flex-1 flex-col">
                <Link to={`/san-pham/${i.product_id}`} className="line-clamp-2 font-semibold hover:text-brand-700">{i.name}</Link>
                <p className="text-sm text-slate-500">{money(i.unit_price)}</p>
                {!i.available && <p className="mt-1 text-sm font-medium text-rose-600" role="alert">{i.stock === 0 ? 'Sản phẩm đã hết hàng' : `Chỉ còn ${i.stock} sản phẩm — hãy giảm số lượng`}</p>}
                <div className="mt-auto flex flex-wrap items-center justify-between gap-2 pt-2">
                  <div className="flex items-center rounded-lg border border-slate-300" role="group" aria-label={`Số lượng ${i.name}`}>
                    <button className="px-3 py-1 disabled:opacity-40" disabled={busyId === i.product_id} onClick={() => run(i.product_id, () => setQuantity(i.product_id, i.quantity - 1))} aria-label="Giảm">−</button>
                    <span className="min-w-8 text-center text-sm" aria-live="polite">{i.quantity}</span>
                    <button className="px-3 py-1 disabled:opacity-40" disabled={busyId === i.product_id || i.quantity >= i.stock} onClick={() => run(i.product_id, () => setQuantity(i.product_id, i.quantity + 1))} aria-label="Tăng">+</button>
                  </div>
                  <p className="font-bold text-brand-700">{money(i.sub_total)}</p>
                  <button className="text-sm text-rose-600 hover:underline" disabled={busyId === i.product_id} onClick={() => run(i.product_id, async () => { await remove(i.product_id); toast.info('Đã xóa khỏi giỏ hàng') })}>Xóa</button>
                </div>
              </div>
            </li>
          ))}
        </ul>
        <aside className="card h-fit space-y-3 p-5 lg:sticky lg:top-32">
          <h2 className="text-lg font-bold">Tóm tắt</h2>
          <div className="flex justify-between text-sm"><span className="text-slate-500">Tạm tính</span><span className="font-semibold">{money(cart.subtotal)}</span></div>
          <p className="text-xs text-slate-500">Phí vận chuyển và mã giảm giá được tính ở bước thanh toán. Miễn phí giao hàng cho đơn từ 500.000đ.</p>
          <button className="btn-primary w-full py-3" disabled={blocked} onClick={() => nav('/thanh-toan')}>Tiến hành thanh toán</button>
          {blocked && <p className="text-xs text-rose-600">Vui lòng xử lý các sản phẩm hết hàng trước khi thanh toán.</p>}
          <Link to="/san-pham" className="btn-ghost w-full">← Tiếp tục mua sắm</Link>
        </aside>
      </div>
      {recs.data && <RecBlock title="Có thể bạn cần thêm" placement="cart" items={recs.data} cols="lg:grid-cols-6" />}
    </div>
  )
}
