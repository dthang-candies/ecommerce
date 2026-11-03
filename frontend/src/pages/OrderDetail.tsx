import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import type { Order, OrderStatus } from '../api/types'
import ProductImage from '../components/ProductImage'
import { ConfirmModal, ErrorBox, Field, Modal, Pill, Spinner, StarInput, StatusBadge } from '../components/ui'
import { useToast } from '../context/ToastContext'
import { STATUS_LABEL, dateTime, money } from '../lib/format'
import { useFetch } from '../lib/useFetch'
import Icon from '../components/Icon'

const FLOW: OrderStatus[] = ['PENDING', 'CONFIRMED', 'PACKED', 'SHIPPING', 'DELIVERED']
const SHIP_LABEL: Record<string, string> = { CREATED: 'Đã tạo vận đơn', IN_TRANSIT: 'Đang vận chuyển', DELIVERED: 'Đã giao thành công', FAILED: 'Giao hàng thất bại' }

export default function OrderDetail() {
  const id = Number(useParams().id)
  const [params] = useSearchParams()
  const toast = useToast()
  const res = useFetch(() => api.get<Order>(`/orders/${id}`), [id])
  const [cancelling, setCancelling] = useState(false)
  const [busy, setBusy] = useState(false)
  const [review, setReview] = useState<{ product_id: number; name: string } | null>(null)

  if (res.loading) return <Spinner />
  if (res.error || !res.data) return <ErrorBox message={res.error ?? 'Không tìm thấy đơn hàng'} onRetry={res.reload} />
  const o = res.data

  const cancel = async () => {
    setBusy(true)
    try { res.setData(await api.post<Order>(`/orders/${id}/cancel`)); toast.success('Đã hủy đơn hàng'); setCancelling(false) }
    catch (e) { toast.error(errorMessage(e)); setCancelling(false); res.reload() } finally { setBusy(false) }
  }
  const at = (s: OrderStatus) => o.history?.find((h) => h.to_status === s)?.changed_at
  const reached = (s: OrderStatus) => FLOW.indexOf(o.status) >= FLOW.indexOf(s)
  const cancelled = o.status === 'CANCELLED'

  return (
    <div className="mx-auto max-w-4xl">
      {params.get('placed') && <div className="mb-4 rounded-xl bg-emerald-50 p-4 text-emerald-800"><span className="flex items-center gap-2"><Icon name="circleCheck" size={20} />Cảm ơn bạn! Đơn hàng đã được ghi nhận.</span></div>}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div><Link to="/don-hang" className="text-sm text-brand-700 hover:underline">← Đơn hàng của tôi</Link>
          <h1 className="mt-1 text-2xl font-bold">Đơn hàng #{o.id}</h1><p className="text-sm text-slate-500">Đặt lúc {dateTime(o.created_at)}</p></div>
        <StatusBadge status={o.status} />
      </div>

      {o.status === 'PENDING_PAYMENT' && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <span>Đơn hàng đang chờ thanh toán. Quá 15 phút kể từ lúc đặt, đơn sẽ tự động hủy.</span>
          <Link to={`/don-hang/${o.id}/thanh-toan`} className="btn-primary">Thanh toán ngay</Link>
        </div>
      )}

      <section className="card mb-4 p-5" aria-label="Tiến trình đơn hàng">
        {cancelled ? (
          <div><p className="font-semibold text-rose-700">Đơn hàng đã bị hủy{at('CANCELLED') ? ` lúc ${dateTime(at('CANCELLED'))}` : ''}.</p><p className="text-sm text-slate-500">Số lượng hàng đã được hoàn lại kho.</p></div>
        ) : (
          <ol className="grid grid-cols-5 gap-1 text-center text-xs sm:text-sm">
            {FLOW.map((s) => (
              <li key={s} className="flex flex-col items-center">
                <span className={`grid h-8 w-8 place-items-center rounded-full text-sm font-bold ${reached(s) ? 'bg-brand-600 text-white' : 'bg-slate-200 text-slate-500'}`}>{reached(s) ? <Icon name="check" size={16} strokeWidth={3} /> : FLOW.indexOf(s) + 1}</span>
                <span className={`mt-1 font-medium ${reached(s) ? 'text-slate-900' : 'text-slate-400'}`}>{STATUS_LABEL[s]}</span>
                <span className="text-[11px] text-slate-400">{dateTime(at(s))}</span>
              </li>
            ))}
          </ol>
        )}
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <section className="card p-5 text-sm"><h2 className="mb-2 font-bold">Giao hàng</h2>
          <p className="font-semibold">{o.ship_recipient} · {o.ship_phone}</p><p className="text-slate-600">{o.ship_address}</p>
          {o.shipment ? (<div className="mt-3 rounded-lg bg-slate-50 p-3"><p><span className="text-slate-500">Đơn vị vận chuyển:</span> {o.shipment.carrier}</p><p><span className="text-slate-500">Mã vận đơn:</span> <b>{o.shipment.tracking_number}</b></p>
            <p><span className="text-slate-500">Trạng thái:</span> {SHIP_LABEL[o.shipment.status] ?? o.shipment.status}</p></div>) : <p className="mt-3 text-slate-500">Mã vận đơn sẽ có sau khi kho đóng gói.</p>}
        </section>
        <section className="card p-5 text-sm"><h2 className="mb-2 font-bold">Thanh toán</h2>
          <p>{o.payment_method === 'COD' ? 'Thanh toán khi nhận hàng (COD)' : `Thanh toán trực tuyến${o.payment && o.payment.method !== 'CARD' ? ' · ' + (o.payment.method === 'WALLET' ? 'Ví điện tử' : o.payment.method) : ''}`}</p>
          <p className="mt-1">{o.payment?.status === 'SUCCESS' ? <Pill tone="green">Đã thanh toán</Pill> : o.payment?.status === 'FAILED' ? <Pill tone="red">Thanh toán thất bại</Pill> : <Pill tone="amber">Chưa thanh toán</Pill>}</p>
          {o.payment?.transaction_id && <p className="mt-2 text-slate-500">Mã giao dịch: {o.payment.transaction_id}</p>}
        </section>
      </div>

      <section className="card mt-4 p-5" aria-label="Sản phẩm">
        <h2 className="mb-2 font-bold">Sản phẩm</h2>
        <ul className="divide-y divide-slate-100">{o.items.map((i) => (
          <li key={i.product_id} className="flex items-center gap-3 py-3 text-sm">
            <ProductImage product={i} className="h-16 w-16 shrink-0 rounded-lg" />
            <div className="min-w-0 flex-1"><Link to={`/san-pham/${i.product_id}`} className="font-medium hover:text-brand-700">{i.name}</Link><p className="text-slate-500">{money(i.unit_price)} × {i.quantity}</p></div>
            <div className="text-right"><p className="font-semibold">{money(i.sub_total)}</p>
              {o.status === 'DELIVERED' && (i.reviewed ? <Pill tone="green">Đã đánh giá</Pill> : <button className="mt-1 text-brand-700 hover:underline" onClick={() => setReview({ product_id: i.product_id, name: i.name })}>Viết đánh giá</button>)}</div>
          </li>))}</ul>
        <dl className="mt-3 space-y-1 border-t border-slate-100 pt-3 text-sm">
          <Row l="Tạm tính" v={money(o.subtotal)} /><Row l="Giảm giá" v={o.discount ? `− ${money(o.discount)}` : money(0)} /><Row l="Phí vận chuyển" v={o.shipping_fee ? money(o.shipping_fee) : 'Miễn phí'} />
          <div className="flex justify-between pt-1 text-base font-bold"><dt>Tổng cộng</dt><dd className="text-brand-700">{money(o.total_amount)}</dd></div>
        </dl>
      </section>

      <div className="mt-4 flex flex-wrap justify-end gap-2">
        <Link to={`/ho-tro?order=${o.id}`} className="btn-secondary">Cần hỗ trợ về đơn này</Link>
        {o.can_cancel && <button className="btn-danger" onClick={() => setCancelling(true)}>Hủy đơn hàng</button>}
      </div>
      {!o.can_cancel && !cancelled && o.status !== 'DELIVERED' && <p className="mt-2 text-right text-xs text-slate-500">Đơn đã được đóng gói nên không thể hủy.</p>}

      {cancelling && <ConfirmModal title="Hủy đơn hàng?" danger confirmLabel="Hủy đơn" busy={busy} onConfirm={cancel} onClose={() => setCancelling(false)}
        message="Đơn hàng sẽ bị hủy và số lượng sản phẩm được hoàn lại kho. Thao tác này không thể hoàn tác." />}
      {review && <ReviewModal orderId={o.id} {...review} onClose={() => setReview(null)} onDone={() => { setReview(null); res.reload() }} />}
    </div>
  )
}

const Row = ({ l, v }: { l: string; v: string }) => <div className="flex justify-between"><dt className="text-slate-500">{l}</dt><dd>{v}</dd></div>

function ReviewModal({ orderId, product_id, name, onClose, onDone }: { orderId: number; product_id: number; name: string; onClose: () => void; onDone: () => void }) {
  const toast = useToast()
  const [rating, setRating] = useState(5)
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async () => {
    setBusy(true)
    try { await api.post(`/orders/${orderId}/reviews`, { product_id, rating, comment: comment || null }); toast.success('Cảm ơn bạn đã đánh giá!'); onDone() }
    catch (e) { toast.error(errorMessage(e)) } finally { setBusy(false) }
  }
  return (
    <Modal title="Đánh giá sản phẩm" onClose={onClose}>
      <p className="mb-3 text-sm font-medium">{name}</p>
      <StarInput value={rating} onChange={setRating} />
      <div className="mt-3"><Field label="Nhận xét (không bắt buộc)"><textarea className="input min-h-24" maxLength={2000} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Chất lượng, đóng gói, giao hàng…" /></Field></div>
      <div className="mt-4 flex justify-end gap-2"><button className="btn-secondary" onClick={onClose}>Hủy</button><button className="btn-primary" disabled={busy} onClick={submit}>{busy ? 'Đang gửi…' : 'Gửi đánh giá'}</button></div>
    </Modal>
  )
}
