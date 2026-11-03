import { useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import type { Order, Support } from '../api/types'
import { Empty, ErrorBox, Field, PageTitle, Pill, Spinner } from '../components/ui'
import { useToast } from '../context/ToastContext'
import { SUPPORT_LABEL, dateTime } from '../lib/format'
import { useFetch } from '../lib/useFetch'
import Icon from '../components/Icon'

export const supportTone = (s: Support['status']) => (s === 'RESOLVED' ? 'green' : s === 'IN_PROGRESS' ? 'blue' : 'amber') as 'green' | 'blue' | 'amber'

export default function SupportPage() {
  const [params] = useSearchParams()
  const toast = useToast()
  const list = useFetch(() => api.get<Support[]>('/me/support-requests'), [])
  const orders = useFetch(() => api.get<Order[]>('/orders'), [])
  const [content, setContent] = useState('')
  const [orderId, setOrderId] = useState(params.get('order') ?? '')
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true)
    try { await api.post('/me/support-requests', { content, order_id: orderId ? Number(orderId) : null }); toast.success('Đã gửi yêu cầu. Chúng tôi sẽ phản hồi sớm.'); setContent(''); list.reload() }
    catch (e2) { toast.error(errorMessage(e2)) } finally { setBusy(false) }
  }
  return (
    <div className="mx-auto max-w-3xl">
      <PageTitle title="Hỗ trợ khách hàng" subtitle="Hỏi đáp, đổi trả, khiếu nại — theo dõi phản hồi tại một nơi" />
      <form onSubmit={submit} className="card mb-6 space-y-3 p-5">
        <Field label="Đơn hàng liên quan (không bắt buộc)">
          <select className="input" value={orderId} onChange={(e) => setOrderId(e.target.value)}><option value="">— Không chọn —</option>{orders.data?.map((o) => <option key={o.id} value={o.id}>Đơn #{o.id} · {dateTime(o.created_at)}</option>)}</select>
        </Field>
        <Field label="Nội dung yêu cầu *"><textarea className="input min-h-28" required minLength={5} maxLength={4000} value={content} onChange={(e) => setContent(e.target.value)} placeholder="Mô tả vấn đề bạn gặp phải…" /></Field>
        <div className="flex justify-end"><button className="btn-primary" disabled={busy || content.trim().length < 5}>{busy ? 'Đang gửi…' : 'Gửi yêu cầu'}</button></div>
      </form>
      <h2 className="mb-3 text-lg font-bold">Yêu cầu của tôi</h2>
      {list.loading ? <Spinner /> : list.error ? <ErrorBox message={list.error} onRetry={list.reload} /> : list.data?.length === 0 ? <Empty icon={<Icon name="message" size={40} strokeWidth={1.5} />} title="Chưa có yêu cầu nào" /> : (
        <ul className="space-y-3">{list.data?.map((s) => (
          <li key={s.id} className="card p-4 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2"><span className="font-semibold">Yêu cầu #{s.id}{s.order_id ? ` · Đơn #${s.order_id}` : ''}</span><Pill tone={supportTone(s.status)}>{SUPPORT_LABEL[s.status]}</Pill></div>
            <p className="mt-1 text-xs text-slate-400">{dateTime(s.created_at)}</p>
            <p className="mt-2 whitespace-pre-line">{s.content}</p>
            {s.response && <div className="mt-3 rounded-lg bg-brand-50 p-3"><p className="text-xs font-semibold text-brand-700">Phản hồi từ UniCart</p><p className="mt-0.5 whitespace-pre-line">{s.response}</p></div>}
          </li>))}</ul>
      )}
    </div>
  )
}
