import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import type { ProductDetail as Detail, Recommendation } from '../api/types'
import ProductImage from '../components/ProductImage'
import RecBlock from '../components/RecBlock'
import { Empty, ErrorBox, Pill, Spinner, Stars } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { useCart } from '../context/CartContext'
import { recSource, usePrefs } from '../context/PrefsContext'
import { useToast } from '../context/ToastContext'
import { dateOnly, money } from '../lib/format'
import { useFetch } from '../lib/useFetch'
import Icon from '../components/Icon'

const ATTR_LABEL: Record<string, string> = {
  isbn: 'ISBN', author: 'Tác giả', cpu: 'CPU', ram: 'RAM', storage: 'Bộ nhớ', screenSize: 'Màn hình (inch)', warrantyMonths: 'Bảo hành (tháng)',
  size: 'Kích cỡ', color: 'Màu sắc', material: 'Chất liệu', shoesSize: 'Cỡ giày', shoesType: 'Loại giày', volume: 'Dung tích', capacity: 'Dung lượng',
  warranty: 'Bảo hành', shipping: 'Giao hàng', return_policy: 'Đổi trả',
}

export default function ProductDetail() {
  const id = Number(useParams().id)
  const { user } = useAuth()
  const { add } = useCart()
  const { track } = usePrefs()
  const toast = useToast()
  const nav = useNavigate()
  const loc = useLocation()
  const [qty, setQty] = useState(1)
  const [busy, setBusy] = useState(false)

  const res = useFetch(() => api.get<Detail>(`/products/${id}`), [id])
  const recs = useFetch(() => api.get<{ similar: Recommendation[]; bought_together: Recommendation[] }>(`/recommendations/product/${id}`), [id])
  useEffect(() => { setQty(1); track('VIEW', { product_id: id }) }, [id, track])

  if (res.loading) return <Spinner />
  if (res.error || !res.data) return <Empty icon={<Icon name="searchX" size={40} strokeWidth={1.5} />} title="Sản phẩm không tồn tại" hint={res.error ?? undefined} action={<Link to="/san-pham" className="btn-primary">Về danh sách sản phẩm</Link>} />
  const p = res.data

  const addToCart = async (buyNow = false) => {
    if (!user) return nav('/dang-nhap', { state: { from: loc.pathname } })
    if (user.role !== 'CUSTOMER') return toast.info('Tài khoản nhân viên không thể mua hàng')
    setBusy(true)
    try {
      await add(p.id, qty, recSource.get(p.id))
      buyNow ? nav('/gio-hang') : toast.success('Đã thêm vào giỏ hàng')
    } catch (e) { toast.error(errorMessage(e)) } finally { setBusy(false) }
  }
  const attrs = Object.entries(p.attributes ?? {})

  return (
    <div>
      <nav className="mb-4 text-sm text-slate-500" aria-label="Breadcrumb">
        <Link to="/" className="hover:text-brand-700">Trang chủ</Link> / <Link to={`/san-pham?category_id=${p.category.id}`} className="hover:text-brand-700">{p.category.name}</Link> / <span className="text-slate-700">{p.name}</span>
      </nav>
      <div className="grid gap-8 md:grid-cols-2">
        <ProductImage product={p} className="aspect-square w-full overflow-hidden rounded-3xl border border-slate-200" />
        <div>
          <p className="text-sm font-medium text-brand-700">{p.brand ?? p.category.name}</p>
          <h1 className="mt-1 text-2xl font-extrabold tracking-tight sm:text-3xl">{p.name}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
            {p.rating && p.rating.count > 0 ? <span className="flex items-center gap-1"><Stars value={p.rating.average} /> <b>{p.rating.average}</b> <span className="text-slate-500">({p.rating.count} đánh giá)</span></span> : <span className="text-slate-500">Chưa có đánh giá</span>}
            <span className="text-slate-400">·</span><span className="text-slate-500">SKU: {p.sku}</span>
          </div>
          <p className="mt-4 text-3xl font-extrabold text-brand-700">{money(p.price)}</p>
          <div className="mt-3">{p.in_stock ? <Pill tone="green">Còn hàng{p.quantity <= 5 ? ` · chỉ còn ${p.quantity}` : ''}</Pill> : <Pill tone="red">Hết hàng</Pill>}</div>
          {p.description && <p className="mt-4 whitespace-pre-line text-slate-600">{p.description}</p>}
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <div className="flex items-center rounded-lg border border-slate-300" role="group" aria-label="Số lượng">
              <button className="px-3 py-2 text-lg disabled:opacity-40" onClick={() => setQty((q) => Math.max(1, q - 1))} disabled={qty <= 1} aria-label="Giảm">−</button>
              <input className="w-12 border-x border-slate-300 py-2 text-center text-sm" value={qty} inputMode="numeric" aria-label="Số lượng"
                onChange={(e) => setQty(Math.min(p.quantity || 1, Math.max(1, Number(e.target.value.replace(/\D/g, '')) || 1)))} />
              <button className="px-3 py-2 text-lg disabled:opacity-40" onClick={() => setQty((q) => Math.min(p.quantity, q + 1))} disabled={qty >= p.quantity} aria-label="Tăng">+</button>
            </div>
            <button className="btn-primary px-6 py-2.5" disabled={!p.in_stock || busy} onClick={() => addToCart(false)}>Thêm vào giỏ hàng</button>
            <button className="btn-secondary px-6 py-2.5" disabled={!p.in_stock || busy} onClick={() => addToCart(true)}>Mua ngay</button>
          </div>
          {attrs.length > 0 && (
            <table className="mt-8 w-full text-sm"><caption className="mb-2 text-left font-bold">Thông số</caption>
              <tbody>{attrs.map(([k, v]) => <tr key={k} className="border-t border-slate-100"><th scope="row" className="w-40 py-2 pr-3 text-left font-medium text-slate-500">{ATTR_LABEL[k] ?? k}</th><td className="py-2">{String(v)}</td></tr>)}</tbody>
            </table>
          )}
        </div>
      </div>

      {recs.data && <RecBlock title="Thường được mua cùng nhau" placement="product" items={recs.data.bought_together} />}

      <section className="mt-10" aria-label="Đánh giá">
        <h2 className="mb-3 text-xl font-bold">Đánh giá của khách hàng</h2>
        {p.reviews.length === 0 ? <p className="text-sm text-slate-500">Chưa có đánh giá. Chỉ khách đã nhận hàng mới có thể đánh giá sản phẩm.</p> : (
          <ul className="space-y-3">{p.reviews.map((r) => (
            <li key={r.id} className="card p-4"><div className="flex flex-wrap items-center gap-2"><Stars value={r.rating} /><b className="text-sm">{r.author}</b><span className="text-xs text-slate-400">{dateOnly(r.created_at)}</span></div>{r.comment && <p className="mt-1 text-sm text-slate-700">{r.comment}</p>}</li>
          ))}</ul>
        )}
      </section>

      {recs.data && <RecBlock title="Sản phẩm tương tự" placement="product" items={recs.data.similar} />}
      {recs.error && <div className="mt-6"><ErrorBox message={recs.error} /></div>}
    </div>
  )
}
