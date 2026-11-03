import { useEffect, useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import type { Order, PayResult } from '../api/types'
import { ErrorBox, Field, Spinner } from '../components/ui'
import { useToast } from '../context/ToastContext'
import { money } from '../lib/format'
import { useFetch } from '../lib/useFetch'
import Icon from '../components/Icon'

type Channel = 'WALLET' | 'CARD'

/** UC-07 Make Online Payment against the sandbox gateway. Card numbers never leave this form: only an opaque token is sent. */
export default function Payment() {
  const id = Number(useParams().id)
  const nav = useNavigate()
  const toast = useToast()
  const res = useFetch(() => api.get<Order>(`/orders/${id}`), [id])
  const [channel, setChannel] = useState<Channel>('WALLET')
  const [card, setCard] = useState('')
  const [phone, setPhone] = useState('')
  const [busy, setBusy] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)
  const [left, setLeft] = useState<number | null>(null)

  useEffect(() => { if (res.data?.pay_seconds_left != null) setLeft(res.data.pay_seconds_left) }, [res.data])
  useEffect(() => {
    if (left === null) return
    const t = setInterval(() => setLeft((s) => (s === null ? s : Math.max(s - 1, 0))), 1000)
    return () => clearInterval(t)
  }, [left === null])

  if (res.loading) return <Spinner />
  if (res.error || !res.data) return <ErrorBox message={res.error ?? 'Không tìm thấy đơn hàng'} />
  const order = res.data
  if (order.status !== 'PENDING_PAYMENT' || order.payment_method !== 'ONLINE') return <Navigate to={`/don-hang/${id}`} replace />

  const digits = card.replace(/\D/g, '')
  const valid = channel === 'WALLET' ? phone.replace(/\D/g, '').length >= 9 : digits.length >= 12
  const expired = left === 0
  const mm = String(Math.floor((left ?? 0) / 60)).padStart(2, '0'), ss = String((left ?? 0) % 60).padStart(2, '0')

  const pay = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true); setFailure(null)
    const token = channel === 'CARD' ? `tok_card_${digits.slice(-4)}` : `tok_wallet_${phone.replace(/\D/g, '').slice(-4)}`
    try {
      const r = await api.post<PayResult>(`/payments/orders/${id}/pay`, { channel, token })
      if (r.success) { toast.success('Thanh toán thành công'); nav(`/don-hang/${id}`, { replace: true }) }
      else setFailure(r.message)
    } catch (e2) {
      setFailure(errorMessage(e2))
      res.reload()
    } finally { setBusy(false) }
  }

  return (
    <div className="mx-auto max-w-xl">
      <div className="card p-6">
        <h1 className="text-xl font-bold">Thanh toán đơn hàng #{order.id}</h1>
        <p className="mt-1 text-3xl font-extrabold text-brand-700">{money(order.total_amount)}</p>
        <div className={`mt-3 rounded-lg px-3 py-2 text-sm ${expired ? 'bg-rose-50 text-rose-700' : 'bg-amber-50 text-amber-800'}`} role="timer">
          {expired ? 'Đơn hàng đã quá hạn thanh toán 15 phút và sẽ tự động hủy.' : <>Vui lòng thanh toán trong <b>{mm}:{ss}</b> — quá hạn đơn sẽ tự động hủy và hoàn lại hàng.</>}
        </div>
        <form onSubmit={pay} className="mt-5 space-y-4">
          <div className="grid grid-cols-2 gap-3" role="radiogroup" aria-label="Phương thức">
            {([['WALLET', 'phone', 'Ví điện tử'], ['CARD', 'card', 'Thẻ ngân hàng']] as const).map(([v, ic, t]) => (
              <label key={v} className={`cursor-pointer rounded-xl border p-3 text-center text-sm font-semibold ${channel === v ? 'border-brand-600 bg-brand-50 ring-1 ring-brand-600' : 'border-slate-200'}`}>
                <input type="radio" className="sr-only" name="channel" checked={channel === v} onChange={() => { setChannel(v); setFailure(null) }} /><span className="inline-flex items-center justify-center gap-2"><Icon name={ic} size={18} />{t}</span>
              </label>
            ))}
          </div>
          {channel === 'WALLET' ? (
            <Field label="Số điện thoại ví"><input className="input" inputMode="tel" autoComplete="tel" placeholder="09xx xxx xxx" value={phone} onChange={(e) => setPhone(e.target.value)} /></Field>
          ) : (
            <Field label="Số thẻ" hint="Môi trường thử nghiệm: thẻ kết thúc bằng 0000 sẽ bị từ chối, các thẻ khác thành công. UniCart không lưu số thẻ.">
              <input className="input tracking-wider" inputMode="numeric" autoComplete="cc-number" placeholder="4242 4242 4242 4242" maxLength={23}
                value={card} onChange={(e) => setCard(e.target.value.replace(/[^\d ]/g, '').replace(/(\d{4})(?=\d)/g, '$1 ').trim())} />
            </Field>
          )}
          {failure && <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700" role="alert"><span className="inline-flex items-center gap-2"><Icon name="circleX" size={16} />{failure}.</span> Bạn có thể thử lại hoặc đổi phương thức.</p>}
          <button className="btn-primary w-full py-3" disabled={busy || !valid || expired}>{busy ? 'Đang xử lý…' : `Thanh toán ${money(order.total_amount)}`}</button>
        </form>
        <div className="mt-4 flex justify-between text-sm"><Link to={`/don-hang/${id}`} className="text-brand-700 hover:underline">Xem chi tiết đơn</Link><span className="inline-flex items-center gap-1.5 text-slate-400"><Icon name="lock" size={14} />Giao dịch được mã hóa</span></div>
      </div>
    </div>
  )
}
