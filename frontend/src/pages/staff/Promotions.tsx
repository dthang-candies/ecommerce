import { useState, type FormEvent } from 'react'
import { api, errorMessage } from '../../api/client'
import type { Promotion } from '../../api/types'
import { ConfirmModal, Empty, ErrorBox, Field, Modal, PageTitle, Pill, Spinner } from '../../components/ui'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { dateOnly, money } from '../../lib/format'
import { useFetch } from '../../lib/useFetch'
import Icon from '../../components/Icon'

const local = (iso: string) => iso.slice(0, 16)          // datetime-local value from the API's naive ISO string

export default function Promotions() {
  const { user } = useAuth()
  const canEdit = user!.role === 'ADMIN'
  const toast = useToast()
  const res = useFetch(() => api.get<Promotion[]>('/admin/promotions'), [])
  const [edit, setEdit] = useState<Promotion | 'new' | null>(null)
  const [del, setDel] = useState<Promotion | null>(null)
  const [busy, setBusy] = useState(false)
  const now = new Date().toISOString().slice(0, 19)

  const remove = async () => {
    if (!del) return
    setBusy(true)
    try { const r = await api.del<{ result: string }>(`/admin/promotions/${del.id}`); toast.success(r.result === 'DISABLED' ? 'Mã đã được dùng nên chỉ bị vô hiệu hóa' : 'Đã xóa mã'); setDel(null); res.reload() } catch (e) { toast.error(errorMessage(e)) } finally { setBusy(false) }
  }
  const state = (p: Promotion) => !p.active ? <Pill>Tạm dừng</Pill> : p.end_at < now ? <Pill tone="red">Hết hạn</Pill> : p.start_at > now ? <Pill tone="blue">Sắp diễn ra</Pill> : <Pill tone="green">Đang chạy</Pill>

  return (
    <div>
      <PageTitle title="Khuyến mại" subtitle="Mã giảm giá áp dụng ở bước thanh toán (BR-05)" actions={canEdit ? <button className="btn-primary" onClick={() => setEdit('new')}>+ Tạo mã</button> : undefined} />
      {res.loading ? <Spinner /> : res.error ? <ErrorBox message={res.error} onRetry={res.reload} /> : res.data?.length === 0 ? <Empty icon={<Icon name="tag" size={40} strokeWidth={1.5} />} title="Chưa có mã khuyến mại" /> : (
        <div className="card overflow-x-auto"><table className="w-full">
          <thead><tr><th className="th">Mã</th><th className="th">Ưu đãi</th><th className="th text-right">Đơn tối thiểu</th><th className="th">Hiệu lực</th><th className="th text-right">Đã dùng</th><th className="th">Trạng thái</th>{canEdit && <th className="th">Thao tác</th>}</tr></thead>
          <tbody>{res.data?.map((p) => (
            <tr key={p.id} className="border-t border-slate-100"><td className="td font-mono font-bold">{p.code}</td>
              <td className="td">{p.discount_type === 'PERCENT' ? `Giảm ${p.discount_value}%` : `Giảm ${money(p.discount_value)}`}</td><td className="td text-right">{money(p.min_order_value)}</td>
              <td className="td whitespace-nowrap text-slate-500">{dateOnly(p.start_at)} – {dateOnly(p.end_at)}</td><td className="td text-right">{p.used_count ?? 0}</td><td className="td">{state(p)}</td>
              {canEdit && <td className="td"><div className="flex gap-1.5"><button className="btn-secondary" onClick={() => setEdit(p)}>Sửa</button><button className="btn-ghost text-rose-600" onClick={() => setDel(p)}>Xóa</button></div></td>}
            </tr>))}</tbody></table></div>)}
      {edit && <PromoForm promo={edit === 'new' ? undefined : edit} onClose={() => setEdit(null)} onDone={() => { setEdit(null); toast.success('Đã lưu khuyến mại'); res.reload() }} />}
      {del && <ConfirmModal title="Xóa mã khuyến mại?" danger confirmLabel="Xóa" busy={busy} onConfirm={remove} onClose={() => setDel(null)} message={<>Xóa mã <b>{del.code}</b>? Nếu mã đã được dùng trong đơn hàng, nó sẽ chỉ bị vô hiệu hóa để giữ lịch sử.</>} />}
    </div>
  )
}

function PromoForm({ promo, onClose, onDone }: { promo?: Promotion; onClose: () => void; onDone: () => void }) {
  const toast = useToast()
  const [f, setF] = useState({
    code: promo?.code ?? '', discount_type: promo?.discount_type ?? 'PERCENT', discount_value: String(promo?.discount_value ?? ''), min_order_value: String(promo?.min_order_value ?? 0),
    start_at: promo ? local(promo.start_at) : new Date().toISOString().slice(0, 10) + 'T00:00', end_at: promo ? local(promo.end_at) : new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10) + 'T23:59', active: promo?.active ?? true,
  })
  const [busy, setBusy] = useState(false)
  const set = (k: keyof typeof f, v: string | boolean) => setF((s) => ({ ...s, [k]: v }))
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true)
    const body = { ...f, discount_value: Number(f.discount_value), min_order_value: Number(f.min_order_value || 0), start_at: f.start_at + ':00', end_at: f.end_at + ':00' }
    try { promo ? await api.put(`/admin/promotions/${promo.id}`, body) : await api.post('/admin/promotions', body); onDone() } catch (e2) { toast.error(errorMessage(e2)) } finally { setBusy(false) }
  }
  return (
    <Modal title={promo ? 'Sửa khuyến mại' : 'Tạo mã khuyến mại'} onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <Field label="Mã *"><input className="input font-mono uppercase" required maxLength={30} value={f.code} onChange={(e) => set('code', e.target.value.toUpperCase())} autoFocus /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Loại giảm"><select className="input" value={f.discount_type} onChange={(e) => set('discount_type', e.target.value)}><option value="PERCENT">Phần trăm (%)</option><option value="AMOUNT">Số tiền (đ)</option></select></Field>
          <Field label={f.discount_type === 'PERCENT' ? 'Phần trăm giảm *' : 'Số tiền giảm *'}><input className="input" type="number" min={1} max={f.discount_type === 'PERCENT' ? 100 : undefined} required value={f.discount_value} onChange={(e) => set('discount_value', e.target.value)} /></Field>
        </div>
        <Field label="Giá trị đơn tối thiểu (đ)"><input className="input" type="number" min={0} value={f.min_order_value} onChange={(e) => set('min_order_value', e.target.value)} /></Field>
        <div className="grid grid-cols-2 gap-3"><Field label="Bắt đầu"><input className="input" type="datetime-local" required value={f.start_at} onChange={(e) => set('start_at', e.target.value)} /></Field><Field label="Kết thúc"><input className="input" type="datetime-local" required value={f.end_at} min={f.start_at} onChange={(e) => set('end_at', e.target.value)} /></Field></div>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.active} onChange={(e) => set('active', e.target.checked)} /> Đang kích hoạt</label>
        <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={onClose}>Hủy</button><button className="btn-primary" disabled={busy}>Lưu</button></div>
      </form>
    </Modal>
  )
}
