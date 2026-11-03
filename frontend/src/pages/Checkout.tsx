import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import type { Address, Order, Quote } from '../api/types'
import AddressForm from '../components/AddressForm'
import ProductImage from '../components/ProductImage'
import { Empty, ErrorBox, Spinner } from '../components/ui'
import { useCart } from '../context/CartContext'
import { usePrefs } from '../context/PrefsContext'
import { useToast } from '../context/ToastContext'
import { money } from '../lib/format'
import { useFetch } from '../lib/useFetch'
import Icon from '../components/Icon'

type Method = 'COD' | 'ONLINE'

export default function Checkout() {
  const { cart, refresh } = useCart()
  const { personalize } = usePrefs()
  const toast = useToast()
  const nav = useNavigate()
  const addresses = useFetch(() => api.get<Address[]>('/me/addresses'), [])
  const [addressId, setAddressId] = useState<number | null>(null)
  const [method, setMethod] = useState<Method>('COD')
  const [codeInput, setCodeInput] = useState('')
  const [code, setCode] = useState('')
  const [quote, setQuote] = useState<Quote | null>(null)
  const [quoteErr, setQuoteErr] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)
  const [placing, setPlacing] = useState(false)
  const [done, setDone] = useState(false)

  useEffect(() => { // pick the default address once loaded
    if (addressId === null && addresses.data?.length) setAddressId((addresses.data.find((a) => a.is_default) ?? addresses.data[0]).id)
  }, [addresses.data, addressId])

  useEffect(() => { // Validate Shopping Cart + Calculate Order Total (UC-06 include steps)
    let live = true
    api.post<Quote>('/checkout/quote', { promo_code: code || null })
      .then((q) => live && (setQuote(q), setQuoteErr(null)))
      .catch((e) => live && setQuoteErr(errorMessage(e)))
    return () => { live = false }
  }, [code, cart?.item_count])

  if (quoteErr) return <ErrorBox message={quoteErr} />
  if (!quote || addresses.loading) return <Spinner />
  if (quote.lines.length === 0 && !done) return <Empty icon={<Icon name="cart" size={40} strokeWidth={1.5} />} title="Giỏ hàng đang trống" action={<Link to="/san-pham" className="btn-primary">Mua sắm ngay</Link>} />

  const place = async () => {
    if (!addressId) return
    setPlacing(true)
    try {
      const order = await api.post<Order>('/orders', { address_id: addressId, payment_method: method, promo_code: quote.promo_code, track: personalize })
      setDone(true)
      await refresh()
      toast.success(`Đặt hàng thành công — mã đơn #${order.id}`)
      nav(method === 'ONLINE' ? `/don-hang/${order.id}/thanh-toan` : `/don-hang/${order.id}`, { replace: true })
    } catch (e) {
      toast.error(errorMessage(e))
      await refresh().catch(() => {})
      api.post<Quote>('/checkout/quote', { promo_code: code || null }).then(setQuote).catch(() => {})
    } finally { setPlacing(false) }
  }

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold">Thanh toán</h1>
      <p className="mb-5 text-sm text-slate-500">Hoàn tất đơn hàng chỉ với 3 bước.</p>
      {quote.issues.length > 0 && (
        <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert">
          <p className="font-semibold">Giỏ hàng có sản phẩm không còn đủ hàng:</p>
          <ul className="ml-5 list-disc">{quote.issues.map((i) => <li key={i}>{i}</li>)}</ul>
          <Link to="/gio-hang" className="mt-2 inline-block font-semibold underline">Quay lại giỏ hàng để điều chỉnh</Link>
        </div>
      )}
      <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
        <div className="space-y-5">
          <Step n={1} title="Địa chỉ giao hàng" action={<button className="text-sm font-semibold text-brand-700 hover:underline" onClick={() => setAdding(true)}>+ Thêm địa chỉ</button>}>
            {addresses.data && addresses.data.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 p-5 text-center text-sm text-slate-500">Bạn chưa có địa chỉ nào. <button className="font-semibold text-brand-700 underline" onClick={() => setAdding(true)}>Thêm địa chỉ giao hàng</button></div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2" role="radiogroup" aria-label="Địa chỉ giao hàng">
                {addresses.data?.map((a) => (
                  <label key={a.id} className={`cursor-pointer rounded-xl border p-3 text-sm transition ${addressId === a.id ? 'border-brand-600 bg-brand-50 ring-1 ring-brand-600' : 'border-slate-200 hover:border-slate-300'}`}>
                    <input type="radio" name="address" className="sr-only" checked={addressId === a.id} onChange={() => setAddressId(a.id)} />
                    <p className="font-semibold">{a.recipient} · {a.phone} {a.is_default && <span className="ml-1 rounded bg-slate-200 px-1.5 py-0.5 text-xs">Mặc định</span>}</p>
                    <p className="mt-0.5 text-slate-600">{a.one_line}</p>
                  </label>
                ))}
              </div>
            )}
          </Step>

          <Step n={2} title="Phương thức thanh toán & ưu đãi">
            <div className="grid gap-3 sm:grid-cols-2" role="radiogroup" aria-label="Phương thức thanh toán">
              {([['COD', 'banknote', 'Thanh toán khi nhận hàng (COD)', 'Trả tiền mặt cho nhân viên giao hàng.'], ['ONLINE', 'card', 'Thanh toán trực tuyến', 'Ví điện tử hoặc thẻ. Cần thanh toán trong 15 phút.']] as const).map(([v, ic, t, d]) => (
                <label key={v} className={`cursor-pointer rounded-xl border p-3 text-sm ${method === v ? 'border-brand-600 bg-brand-50 ring-1 ring-brand-600' : 'border-slate-200 hover:border-slate-300'}`}>
                  <input type="radio" name="method" className="sr-only" checked={method === v} onChange={() => setMethod(v)} />
                  <p className="flex items-center gap-2 font-semibold"><Icon name={ic} size={18} />{t}</p><p className="mt-0.5 text-slate-500">{d}</p>
                </label>
              ))}
            </div>
            <form className="mt-4 flex gap-2" onSubmit={(e) => { e.preventDefault(); setCode(codeInput.trim().toUpperCase()) }}>
              <input className="input uppercase" placeholder="Mã giảm giá (ví dụ WELCOME10)" aria-label="Mã giảm giá" value={codeInput} maxLength={30} onChange={(e) => setCodeInput(e.target.value)} />
              <button className="btn-secondary shrink-0">Áp dụng</button>
              {code && <button type="button" className="btn-ghost shrink-0" onClick={() => { setCode(''); setCodeInput('') }}>Bỏ mã</button>}
            </form>
            {quote.promo_error && <p className="mt-2 text-sm text-rose-600" role="alert">{quote.promo_error}</p>}
            {quote.promo_code && <p className="mt-2 text-sm text-emerald-700"><Icon name="check" size={14} strokeWidth={3} className="mr-1 inline" />Đã áp dụng mã {quote.promo_code}: giảm {money(quote.discount)}</p>}
          </Step>

          <Step n={3} title="Kiểm tra đơn hàng">
            <ul className="divide-y divide-slate-100">
              {quote.lines.map((l) => (
                <li key={l.product_id} className="flex items-center gap-3 py-2.5 text-sm">
                  <ProductImage product={l} className="h-14 w-14 shrink-0 rounded-lg" />
                  <div className="min-w-0 flex-1"><p className="truncate font-medium">{l.name}</p><p className="text-slate-500">{money(l.unit_price)} × {l.quantity}</p>{l.problem && <p className="font-medium text-rose-600">{l.problem}</p>}</div>
                  <p className="font-semibold">{money(l.sub_total)}</p>
                </li>
              ))}
            </ul>
          </Step>
        </div>

        <aside className="card h-fit space-y-2 p-5 text-sm lg:sticky lg:top-32">
          <h2 className="mb-1 text-lg font-bold">Tổng thanh toán</h2>
          <Row label="Tạm tính" value={money(quote.subtotal)} />
          <Row label="Giảm giá" value={quote.discount ? `− ${money(quote.discount)}` : money(0)} />
          <Row label="Phí vận chuyển" value={quote.shipping_fee ? money(quote.shipping_fee) : 'Miễn phí'} />
          <div className="flex items-baseline justify-between border-t border-slate-200 pt-3"><span className="font-semibold">Tổng cộng</span><span className="text-2xl font-extrabold text-brand-700">{money(quote.total)}</span></div>
          <button className="btn-primary mt-2 w-full py-3" disabled={!quote.can_checkout || !addressId || placing} onClick={place}>
            {placing ? 'Đang đặt hàng…' : method === 'ONLINE' ? 'Đặt hàng & thanh toán' : 'Đặt hàng'}
          </button>
          {!addressId && <p className="text-xs text-rose-600">Vui lòng chọn địa chỉ giao hàng.</p>}
          <p className="text-xs text-slate-500">Bằng việc đặt hàng, bạn đồng ý với chính sách mua hàng của UniCart. Đơn có thể hủy miễn phí trước khi đóng gói.</p>
        </aside>
      </div>
      {adding && <AddressForm onClose={() => setAdding(false)} onSaved={(a) => { setAdding(false); setAddressId(a.id); addresses.reload() }} />}
    </div>
  )
}

function Step({ n, title, children, action }: { n: number; title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <section className="card p-5">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-base font-bold"><span className="grid h-7 w-7 place-items-center rounded-full bg-brand-600 text-sm text-white">{n}</span>{title}</h2>{action}
      </div>
      {children}
    </section>
  )
}
const Row = ({ label, value }: { label: string; value: string }) => <div className="flex justify-between"><span className="text-slate-500">{label}</span><span className="font-medium">{value}</span></div>
