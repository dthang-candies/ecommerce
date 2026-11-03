import { useState } from 'react'
import { api, errorMessage } from '../../api/client'
import type { Order, OrderStatus, Page } from '../../api/types'
import { ConfirmModal, Empty, ErrorBox, Modal, PageTitle, Pagination, Spinner, StatusBadge } from '../../components/ui'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { STATUS_LABEL, dateTime, money } from '../../lib/format'
import { useFetch } from '../../lib/useFetch'
import Icon from '../../components/Icon'

const STATUSES: OrderStatus[] = ['PENDING_PAYMENT', 'PENDING', 'CONFIRMED', 'PACKED', 'SHIPPING', 'DELIVERED', 'CANCELLED']
const SIZE = 15
type Act = { kind: 'confirm' | 'cancel' | 'pack' | 'transit' | 'deliver' | 'fail'; order: Order }

export default function StaffOrders() {
  const { user } = useAuth()
  const toast = useToast()
  const role = user!.role
  const initial: OrderStatus = role === 'SERVICE' ? 'PENDING' : role === 'WAREHOUSE' ? 'CONFIRMED' : 'PENDING'
  const [status, setStatus] = useState<OrderStatus | ''>(initial)
  const [q, setQ] = useState('')
  const [term, setTerm] = useState('')
  const [page, setPage] = useState(1)
  const [act, setAct] = useState<Act | null>(null)
  const [detail, setDetail] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const res = useFetch(() => api.get<Page<Order>>('/staff/orders', { status, q: term, page, size: SIZE }), [status, term, page])

  const run = async () => {
    if (!act) return
    setBusy(true)
    const { kind, order } = act
    try {
      if (kind === 'confirm') await api.patch(`/orders/${order.id}/status`, { status: 'CONFIRMED' })
      else if (kind === 'cancel') await api.patch(`/orders/${order.id}/status`, { status: 'CANCELLED' })
      else if (kind === 'pack') await api.patch(`/orders/${order.id}/status`, { status: 'PACKED' })
      else await api.post(`/staff/sandbox/carrier/${order.id}`, { status: kind === 'transit' ? 'IN_TRANSIT' : kind === 'deliver' ? 'DELIVERED' : 'FAILED' })
      toast.success(`Đã cập nhật đơn #${order.id}`)
      setAct(null); res.reload()
    } catch (e) { toast.error(errorMessage(e)); setAct(null); res.reload() } finally { setBusy(false) }
  }
  const actions = (o: Order): { kind: Act['kind']; label: string; danger?: boolean }[] => {
    const a: { kind: Act['kind']; label: string; danger?: boolean }[] = []
    if (role === 'SERVICE') {
      if (o.status === 'PENDING') a.push({ kind: 'confirm', label: 'Xác nhận' }, { kind: 'cancel', label: 'Hủy', danger: true })
      if (o.status === 'CONFIRMED') a.push({ kind: 'cancel', label: 'Hủy', danger: true })
    }
    if (role === 'WAREHOUSE' || role === 'ADMIN') {
      if (o.status === 'CONFIRMED' && role === 'WAREHOUSE') a.push({ kind: 'pack', label: 'Đã đóng gói' })
      if (o.status === 'PACKED') a.push({ kind: 'transit', label: 'Bàn giao vận chuyển' })
      if (o.status === 'SHIPPING') a.push({ kind: 'deliver', label: 'Đã giao' }, { kind: 'fail', label: 'Giao thất bại', danger: true })
    }
    return a
  }
  const labels: Record<Act['kind'], string> = { confirm: 'Xác nhận đơn hàng', cancel: 'Hủy đơn hàng', pack: 'Xác nhận đã đóng gói', transit: 'Bàn giao cho đơn vị vận chuyển', deliver: 'Xác nhận giao thành công', fail: 'Đánh dấu giao thất bại' }

  return (
    <div>
      <PageTitle title="Đơn hàng" subtitle={role === 'WAREHOUSE' ? 'Đóng gói đơn đã xác nhận và bàn giao vận chuyển' : role === 'SERVICE' ? 'Kiểm tra và xác nhận đơn chờ xử lý' : 'Tra cứu đơn hàng'} />
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <select className="input w-auto" value={status} onChange={(e) => { setStatus(e.target.value as OrderStatus | ''); setPage(1) }} aria-label="Trạng thái">
          <option value="">Mọi trạng thái</option>{STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}</select>
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); setTerm(q.trim()); setPage(1) }}>
          <input className="input w-56" placeholder="Mã đơn, tên, SĐT…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Tìm đơn hàng" /><button className="btn-secondary">Tìm</button></form>
      </div>
      {res.loading ? <Spinner /> : res.error ? <ErrorBox message={res.error} onRetry={res.reload} /> : res.data && (res.data.items.length === 0 ? <Empty icon={<Icon name="receipt" size={40} strokeWidth={1.5} />} title="Không có đơn hàng" hint="Không có đơn nào khớp bộ lọc hiện tại." /> : (<>
        <div className="card overflow-x-auto"><table className="w-full">
          <thead><tr><th className="th">Mã</th><th className="th">Khách nhận</th><th className="th">Thời gian</th><th className="th">Thanh toán</th><th className="th text-right">Tổng tiền</th><th className="th">Trạng thái</th><th className="th">Thao tác</th></tr></thead>
          <tbody>{res.data.items.map((o) => (
            <tr key={o.id} className="border-t border-slate-100 align-top">
              <td className="td font-bold"><button className="text-brand-700 hover:underline" onClick={() => setDetail(o.id)}>#{o.id}</button></td>
              <td className="td"><p className="font-medium">{o.ship_recipient}</p><p className="text-xs text-slate-500">{o.ship_phone}</p></td>
              <td className="td whitespace-nowrap text-slate-500">{dateTime(o.created_at)}</td>
              <td className="td">{o.payment_method === 'COD' ? 'COD' : 'Online'}<p className="text-xs text-slate-500">{o.payment?.status === 'SUCCESS' ? 'Đã thanh toán' : 'Chưa thanh toán'}</p></td>
              <td className="td text-right font-semibold">{money(o.total_amount)}</td>
              <td className="td"><StatusBadge status={o.status} /></td>
              <td className="td"><div className="flex flex-wrap gap-1.5">{actions(o).map((a) => <button key={a.kind} className={a.danger ? 'btn-secondary text-rose-600' : 'btn-primary'} onClick={() => setAct({ kind: a.kind, order: o })}>{a.label}</button>)}
                <button className="btn-ghost" onClick={() => setDetail(o.id)}>Chi tiết</button></div></td>
            </tr>))}</tbody></table></div>
        <Pagination page={page} size={SIZE} total={res.data.total} onChange={setPage} />
      </>))}
      {act && <ConfirmModal title={labels[act.kind]} danger={act.kind === 'cancel' || act.kind === 'fail'} busy={busy} onConfirm={run} onClose={() => setAct(null)}
        message={<>Đơn hàng <b>#{act.order.id}</b> — {act.order.ship_recipient}, {money(act.order.total_amount)}.{(act.kind === 'cancel' || act.kind === 'fail') && ' Hàng trong đơn sẽ được hoàn lại kho.'}{(act.kind === 'transit' || act.kind === 'deliver' || act.kind === 'fail') && ' (Mô phỏng cập nhật từ đơn vị vận chuyển.)'}</>} />}
      {detail && <OrderDetailModal id={detail} onClose={() => setDetail(null)} />}
    </div>
  )
}

function OrderDetailModal({ id, onClose }: { id: number; onClose: () => void }) {
  const res = useFetch(() => api.get<Order>(`/staff/orders/${id}`), [id])
  const o = res.data
  return (
    <Modal title={`Đơn hàng #${id}`} onClose={onClose} wide>
      {res.loading ? <Spinner /> : res.error || !o ? <ErrorBox message={res.error ?? 'Lỗi'} /> : (
        <div className="space-y-4 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2"><StatusBadge status={o.status} /><span className="text-slate-500">{dateTime(o.created_at)}</span></div>
          <div><p className="font-semibold">{o.ship_recipient} · {o.ship_phone}</p><p className="text-slate-600">{o.ship_address}</p>
            {o.shipment && <p className="mt-1 text-slate-600">Vận đơn <b>{o.shipment.tracking_number}</b> ({o.shipment.carrier}) — {o.shipment.status}</p>}</div>
          <table className="w-full"><tbody>{o.items.map((i) => <tr key={i.product_id} className="border-t border-slate-100"><td className="py-2">{i.name}<span className="text-slate-400"> · {i.sku}</span></td><td className="py-2 text-right">{i.quantity} × {money(i.unit_price)}</td></tr>)}
            <tr className="border-t border-slate-200 font-bold"><td className="py-2">Tổng ({o.payment_method === 'COD' ? 'COD' : 'Online'})</td><td className="py-2 text-right">{money(o.total_amount)}</td></tr></tbody></table>
          <div><p className="mb-1 font-semibold">Lịch sử trạng thái</p><ul className="space-y-1 text-slate-600">{o.history?.map((h, i) => <li key={i}>{dateTime(h.changed_at)} — {h.from_status ? `${STATUS_LABEL[h.from_status as OrderStatus]} → ` : ''}<b>{STATUS_LABEL[h.to_status]}</b>{h.changed_by ? ` (TK #${h.changed_by})` : ' (hệ thống)'}</li>)}</ul></div>
        </div>)}
    </Modal>
  )
}
