import { useState } from 'react'
import { api, errorMessage } from '../../api/client'
import type { Page, Support } from '../../api/types'
import { Empty, ErrorBox, Field, Modal, PageTitle, Pagination, Pill, Spinner } from '../../components/ui'
import { useToast } from '../../context/ToastContext'
import { SUPPORT_LABEL, dateTime } from '../../lib/format'
import { useFetch } from '../../lib/useFetch'
import { supportTone } from '../Support'
import Icon from '../../components/Icon'

const SIZE = 15

export default function SupportDesk() {
  const [status, setStatus] = useState('OPEN')
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState<Support | null>(null)
  const res = useFetch(() => api.get<Page<Support>>('/staff/support-requests', { status, page, size: SIZE }), [status, page])
  return (
    <div>
      <PageTitle title="Hỗ trợ khách hàng" subtitle="Tiếp nhận, phản hồi và đóng yêu cầu đổi trả, khiếu nại, tư vấn (FR-32)" />
      <div className="mb-4 flex gap-1 overflow-x-auto" role="tablist">
        {[['OPEN', 'Mới'], ['IN_PROGRESS', 'Đang xử lý'], ['RESOLVED', 'Đã giải quyết'], ['', 'Tất cả']].map(([k, l]) => (
          <button key={k} role="tab" aria-selected={status === k} onClick={() => { setStatus(k); setPage(1) }} className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium ${status === k ? 'bg-brand-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-100'}`}>{l}</button>))}
      </div>
      {res.loading ? <Spinner /> : res.error ? <ErrorBox message={res.error} onRetry={res.reload} /> : res.data?.items.length === 0 ? <Empty icon={<Icon name="message" size={40} strokeWidth={1.5} />} title="Không có yêu cầu" hint="Chưa có yêu cầu nào ở trạng thái này." /> : res.data && (<>
        <ul className="space-y-3">{res.data.items.map((s) => (
          <li key={s.id} className="card flex flex-wrap items-start justify-between gap-3 p-4 text-sm">
            <div className="min-w-0 flex-1"><p className="font-semibold">#{s.id} · Khách #{s.customer_id}{s.order_id ? ` · Đơn #${s.order_id}` : ''} <Pill tone={supportTone(s.status)}>{SUPPORT_LABEL[s.status]}</Pill></p>
              <p className="text-xs text-slate-400">{dateTime(s.created_at)}</p><p className="mt-1 line-clamp-2 whitespace-pre-line text-slate-700">{s.content}</p></div>
            <button className={s.status === 'RESOLVED' ? 'btn-secondary' : 'btn-primary'} onClick={() => setOpen(s)}>{s.status === 'RESOLVED' ? 'Xem' : 'Xử lý'}</button>
          </li>))}</ul>
        <Pagination page={page} size={SIZE} total={res.data.total} onChange={setPage} />
      </>)}
      {open && <Handle req={open} onClose={() => setOpen(null)} onDone={() => { setOpen(null); res.reload() }} />}
    </div>
  )
}

function Handle({ req, onClose, onDone }: { req: Support; onClose: () => void; onDone: () => void }) {
  const toast = useToast()
  const [text, setText] = useState(req.response ?? '')
  const [busy, setBusy] = useState(false)
  const done = req.status === 'RESOLVED'
  const send = async (resolve: boolean) => {
    setBusy(true)
    try { await api.post(`/staff/support-requests/${req.id}/reply`, { response: text, resolve }); toast.success(resolve ? 'Đã phản hồi và đóng yêu cầu' : 'Đã gửi phản hồi'); onDone() } catch (e) { toast.error(errorMessage(e)) } finally { setBusy(false) }
  }
  const close = async () => {
    setBusy(true)
    try { await api.post(`/staff/support-requests/${req.id}/resolve`); toast.success('Đã đóng yêu cầu'); onDone() } catch (e) { toast.error(errorMessage(e)) } finally { setBusy(false) }
  }
  return (
    <Modal title={`Yêu cầu #${req.id}`} onClose={onClose} wide>
      <div className="space-y-3 text-sm">
        <p className="text-slate-500">Khách #{req.customer_id}{req.order_id ? ` · Đơn #${req.order_id}` : ''} · {dateTime(req.created_at)}</p>
        <p className="whitespace-pre-line rounded-lg bg-slate-50 p-3">{req.content}</p>
        <Field label="Phản hồi cho khách hàng"><textarea className="input min-h-28" disabled={done} maxLength={4000} value={text} onChange={(e) => setText(e.target.value)} /></Field>
        {!done && <div className="flex flex-wrap justify-end gap-2">
          <button className="btn-secondary" disabled={busy} onClick={close}>Đóng không phản hồi</button>
          <button className="btn-secondary" disabled={busy || !text.trim()} onClick={() => send(false)}>Gửi phản hồi</button>
          <button className="btn-primary" disabled={busy || !text.trim()} onClick={() => send(true)}>Gửi & giải quyết</button></div>}
      </div>
    </Modal>
  )
}
