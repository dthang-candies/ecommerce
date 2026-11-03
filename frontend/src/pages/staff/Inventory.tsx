import { useState, type FormEvent } from 'react'
import { api, errorMessage } from '../../api/client'
import type { InventoryRow, Movement, Page, RestockRequest, Supplier } from '../../api/types'
import { Empty, ErrorBox, Field, Modal, PageTitle, Pagination, Pill, Spinner } from '../../components/ui'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { RESTOCK_LABEL, dateTime } from '../../lib/format'
import { useFetch } from '../../lib/useFetch'
import Icon from '../../components/Icon'

const SIZE = 15

export default function InventoryPage() {
  const [tab, setTab] = useState<'stock' | 'restock'>('stock')
  return (
    <div>
      <PageTitle title="Kho & nhập hàng" subtitle="Theo dõi tồn kho, cảnh báo hàng sắp hết và yêu cầu nhập hàng (BR-11)" />
      <div className="mb-4 flex gap-1" role="tablist">
        {([['stock', 'Tồn kho'], ['restock', 'Yêu cầu nhập hàng']] as const).map(([k, l]) => <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)} className={`rounded-lg px-3 py-1.5 text-sm font-medium ${tab === k ? 'bg-brand-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-100'}`}>{l}</button>)}
      </div>
      {tab === 'stock' ? <Stock /> : <Restock />}
    </div>
  )
}

function Stock() {
  const { user } = useAuth()
  const canEdit = user!.role === 'WAREHOUSE' || user!.role === 'ADMIN'
  const toast = useToast()
  const [q, setQ] = useState('')
  const [term, setTerm] = useState('')
  const [page, setPage] = useState(1)
  const [lowOnly, setLowOnly] = useState(false)
  const [edit, setEdit] = useState<{ row: InventoryRow; mode: 'restock' | 'threshold' } | null>(null)
  const [history, setHistory] = useState<InventoryRow | null>(null)
  const list = useFetch(() => api.get<Page<InventoryRow>>('/inventory', { q: term, page, size: SIZE }), [term, page])
  const low = useFetch(() => api.get<InventoryRow[]>('/inventory/low-stock'), [])
  const rows = lowOnly ? low.data ?? [] : list.data?.items ?? []
  const reload = () => { list.reload(); low.reload() }

  return (
    <div>
      {low.data && low.data.length > 0 && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" role="alert">
          <span className="inline-flex items-center gap-2"><Icon name="alert" size={18} /><b>{low.data.length}</b> sản phẩm dưới ngưỡng tồn kho tối thiểu.</span>
          <button className="font-semibold underline" onClick={() => setLowOnly((v) => !v)}>{lowOnly ? 'Xem tất cả' : 'Chỉ xem hàng sắp hết'}</button>
        </div>
      )}
      <form className="mb-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); setTerm(q.trim()); setPage(1); setLowOnly(false) }}>
        <input className="input max-w-xs" placeholder="Tìm theo tên hoặc SKU…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Tìm sản phẩm" /><button className="btn-secondary">Tìm</button></form>
      {list.loading ? <Spinner /> : list.error ? <ErrorBox message={list.error} onRetry={list.reload} /> : rows.length === 0 ? <Empty icon={<Icon name="package" size={40} strokeWidth={1.5} />} title="Không có dữ liệu" /> : (<>
        <div className="card overflow-x-auto"><table className="w-full">
          <thead><tr><th className="th">Sản phẩm</th><th className="th text-right">Tồn kho</th><th className="th text-right">Ngưỡng tối thiểu</th><th className="th">Tình trạng</th><th className="th">Thao tác</th></tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.product_id} className="border-t border-slate-100">
              <td className="td"><p className="font-medium">{r.name}</p><p className="text-xs text-slate-400">{r.sku}{r.status === 'HIDDEN' ? ' · đang ẩn' : ''}</p></td>
              <td className="td text-right font-bold">{r.quantity}</td><td className="td text-right">{r.min_threshold}</td>
              <td className="td">{r.quantity === 0 ? <Pill tone="red">Hết hàng</Pill> : r.low ? <Pill tone="amber">Sắp hết</Pill> : <Pill tone="green">Ổn định</Pill>}</td>
              <td className="td"><div className="flex flex-wrap gap-1.5"><button className="btn-ghost" onClick={() => setHistory(r)}>Lịch sử</button>
                {canEdit && <><button className="btn-secondary" onClick={() => setEdit({ row: r, mode: 'restock' })}>Nhập kho</button><button className="btn-ghost" onClick={() => setEdit({ row: r, mode: 'threshold' })}>Ngưỡng</button></>}</div></td>
            </tr>))}</tbody></table></div>
        {!lowOnly && list.data && <Pagination page={page} size={SIZE} total={list.data.total} onChange={setPage} />}
      </>)}
      {edit && <StockModal {...edit} onClose={() => setEdit(null)} onDone={() => { setEdit(null); toast.success('Đã cập nhật'); reload() }} />}
      {history && <HistoryModal row={history} onClose={() => setHistory(null)} />}
    </div>
  )
}

function StockModal({ row, mode, onClose, onDone }: { row: InventoryRow; mode: 'restock' | 'threshold'; onClose: () => void; onDone: () => void }) {
  const toast = useToast()
  const [n, setN] = useState(mode === 'threshold' ? String(row.min_threshold) : '')
  const [busy, setBusy] = useState(false)
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true)
    try {
      mode === 'restock' ? await api.post(`/inventory/${row.product_id}/restock`, { quantity: Number(n) }) : await api.put(`/inventory/${row.product_id}/threshold`, { min_threshold: Number(n) })
      onDone()
    } catch (e2) { toast.error(errorMessage(e2)) } finally { setBusy(false) }
  }
  return (
    <Modal title={mode === 'restock' ? 'Nhập kho trực tiếp' : 'Đặt ngưỡng tồn kho tối thiểu'} onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <p className="text-sm"><b>{row.name}</b> — hiện có {row.quantity}</p>
        {mode === 'restock' && <p className="rounded-lg bg-slate-50 p-2 text-xs text-slate-500">Dùng khi hàng đã thực tế về kho. Quy trình thông thường: tạo yêu cầu nhập hàng gửi nhà cung cấp.</p>}
        <Field label={mode === 'restock' ? 'Số lượng nhập thêm' : 'Ngưỡng tối thiểu'}><input className="input" type="number" min={mode === 'restock' ? 1 : 0} required autoFocus value={n} onChange={(e) => setN(e.target.value)} /></Field>
        <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={onClose}>Hủy</button><button className="btn-primary" disabled={busy || n === ''}>Lưu</button></div>
      </form>
    </Modal>
  )
}

function HistoryModal({ row, onClose }: { row: InventoryRow; onClose: () => void }) {
  const res = useFetch(() => api.get<Movement[]>(`/inventory/${row.product_id}/movements`), [row.product_id])
  const T: Record<string, string> = { IN: 'Nhập', OUT: 'Xuất', RETURN: 'Hoàn kho', ADJUST: 'Điều chỉnh' }
  return (
    <Modal title={`Lịch sử kho — ${row.name}`} onClose={onClose} wide>
      {res.loading ? <Spinner /> : res.error ? <ErrorBox message={res.error} /> : res.data?.length === 0 ? <p className="text-sm text-slate-500">Chưa có biến động.</p> : (
        <table className="w-full text-sm"><thead><tr><th className="th">Thời gian</th><th className="th">Loại</th><th className="th text-right">SL</th><th className="th">Lý do</th></tr></thead>
          <tbody>{res.data?.map((m) => <tr key={m.id} className="border-t border-slate-100"><td className="td whitespace-nowrap">{dateTime(m.created_at)}</td><td className="td">{T[m.type] ?? m.type}</td><td className="td text-right">{m.type === 'OUT' ? '−' : '+'}{m.quantity}</td><td className="td text-slate-500">{m.reason}{m.order_id ? ` · đơn #${m.order_id}` : ''}</td></tr>)}</tbody></table>)}
    </Modal>
  )
}

function Restock() {
  const { user } = useAuth()
  const canEdit = user!.role === 'WAREHOUSE' || user!.role === 'ADMIN'
  const toast = useToast()
  const list = useFetch(() => api.get<RestockRequest[]>('/restock-requests'), [])
  const products = useFetch(() => api.get<Page<InventoryRow>>('/inventory', { size: 100 }), [])
  const suppliers = useFetch(() => (canEdit ? api.get<Supplier[]>('/suppliers') : Promise.resolve([])), [canEdit])
  const [form, setForm] = useState({ product_id: '', supplier_id: '', quantity: '' })
  const [busy, setBusy] = useState<number | 'new' | null>(null)
  const name = (id: number) => products.data?.items.find((p) => p.product_id === id)?.name ?? `#${id}`
  const supplier = (id: number) => suppliers.data?.find((s) => s.id === id)?.name ?? `NCC #${id}`

  const create = async (e: FormEvent) => {
    e.preventDefault(); setBusy('new')
    try { await api.post('/restock-requests', { product_id: Number(form.product_id), supplier_id: Number(form.supplier_id), quantity: Number(form.quantity) }); toast.success('Đã gửi yêu cầu nhập hàng'); setForm({ product_id: '', supplier_id: '', quantity: '' }); list.reload() }
    catch (e2) { toast.error(errorMessage(e2)) } finally { setBusy(null) }
  }
  const act = async (id: number, fn: () => Promise<unknown>, ok: string) => {
    setBusy(id)
    try { await fn(); toast.success(ok) } catch (e) { toast.error(errorMessage(e)) } finally { setBusy(null); list.reload() }
  }
  const tone = { REQUESTED: 'amber', CONFIRMED: 'blue', RECEIVED: 'green', REJECTED: 'red' } as const

  return (
    <div className="space-y-5">
      {canEdit && (
        <form onSubmit={create} className="card grid gap-3 p-4 sm:grid-cols-[1fr_1fr_120px_auto] sm:items-end">
          <Field label="Sản phẩm"><select className="input" required value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })}><option value="">Chọn sản phẩm…</option>{products.data?.items.map((p) => <option key={p.product_id} value={p.product_id}>{p.name} (tồn {p.quantity})</option>)}</select></Field>
          <Field label="Nhà cung cấp"><select className="input" required value={form.supplier_id} onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}><option value="">Chọn NCC…</option>{suppliers.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></Field>
          <Field label="Số lượng"><input className="input" type="number" min={1} required value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} /></Field>
          <button className="btn-primary" disabled={busy === 'new'}>Gửi yêu cầu</button>
        </form>
      )}
      {list.loading ? <Spinner /> : list.error ? <ErrorBox message={list.error} onRetry={list.reload} /> : list.data?.length === 0 ? <Empty icon={<Icon name="truck" size={40} strokeWidth={1.5} />} title="Chưa có yêu cầu nhập hàng" /> : (
        <div className="card overflow-x-auto"><table className="w-full">
          <thead><tr><th className="th">Mã</th><th className="th">Sản phẩm</th><th className="th">Nhà cung cấp</th><th className="th text-right">SL</th><th className="th">Trạng thái</th><th className="th">Thời gian</th>{canEdit && <th className="th">Thao tác</th>}</tr></thead>
          <tbody>{list.data?.map((r) => (
            <tr key={r.id} className="border-t border-slate-100"><td className="td">#{r.id}</td><td className="td font-medium">{name(r.product_id)}</td><td className="td">{suppliers.data ? supplier(r.supplier_id) : `#${r.supplier_id}`}</td><td className="td text-right">{r.quantity}</td>
              <td className="td"><Pill tone={tone[r.status]}>{RESTOCK_LABEL[r.status]}</Pill></td><td className="td whitespace-nowrap text-slate-500">{dateTime(r.created_at)}</td>
              {canEdit && <td className="td"><div className="flex flex-wrap gap-1.5">
                {r.status === 'REQUESTED' && <><button className="btn-secondary" disabled={busy === r.id} onClick={() => act(r.id, () => api.post(`/staff/sandbox/supplier/${r.id}`, { accept: true }), 'NCC đã xác nhận (mô phỏng)')}>NCC xác nhận</button>
                  <button className="btn-ghost text-rose-600" disabled={busy === r.id} onClick={() => act(r.id, () => api.post(`/staff/sandbox/supplier/${r.id}`, { accept: false }), 'NCC đã từ chối (mô phỏng)')}>NCC từ chối</button></>}
                {r.status === 'CONFIRMED' && <button className="btn-primary" disabled={busy === r.id} onClick={() => act(r.id, () => api.post(`/restock-requests/${r.id}/receive`), 'Đã nhập kho')}>Nhập kho</button>}
              </div></td>}
            </tr>))}</tbody></table></div>
      )}
      <p className="text-xs text-slate-400">Tồn kho chỉ tăng khi yêu cầu được nhà cung cấp xác nhận và nhân viên kho ghi nhận nhập kho (BR-11). Nút “NCC xác nhận” mô phỏng phản hồi của nhà cung cấp trong môi trường thử nghiệm.</p>
    </div>
  )
}

