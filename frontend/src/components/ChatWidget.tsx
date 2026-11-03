import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import type { ChatAction, ChatPromotion, ChatReply, Order, Product } from '../api/types'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { dateOnly, money } from '../lib/format'
import Icon from './Icon'
import ProductImage from './ProductImage'
import { StatusBadge } from './ui'

interface Msg {
  id: number
  role: 'user' | 'assistant'
  content: string
  products?: Product[]
  promotions?: ChatPromotion[]
  orders?: Order[]
  actions?: (ChatAction & { sent?: boolean })[]
  suggestions?: string[]
  notice?: string
  error?: boolean
}

const STORE_KEY = 'unicart.chat'
const GREETING = 'Xin chào! Mình là trợ lý mua sắm của UniCart. Mình giúp được: tìm sản phẩm, xem mã giảm giá hôm nay, tra cứu đơn hàng và hướng dẫn đổi trả.'
const START_CHIPS = ['Hôm nay có mã giảm giá nào?', 'Phí vận chuyển thế nào?', 'Chính sách đổi trả', 'Gợi ý laptop dưới 25 triệu']
const CUSTOMER_CHIPS = ['Hôm nay có mã giảm giá nào?', 'Đơn hàng của tôi đến đâu rồi?', 'Tôi muốn đổi trả hàng', 'Phí vận chuyển thế nào?']

let seq = Date.now()
const nextId = () => ++seq

const load = (owner: string): Msg[] => {
  try {
    const raw = sessionStorage.getItem(STORE_KEY)
    const saved = raw ? (JSON.parse(raw) as { owner: string; msgs: Msg[] }) : null
    return saved && saved.owner === owner && Array.isArray(saved.msgs) ? saved.msgs : []
  } catch { return [] }
}
const save = (owner: string, msgs: Msg[]) => {
  try { sessionStorage.setItem(STORE_KEY, JSON.stringify({ owner, msgs: msgs.slice(-30) })) } catch { /* private mode */ }
}

/** Floating shopping assistant: promotions of today, products, order tracking and return help. */
export default function ChatWidget() {
  const { user } = useAuth()
  const owner = user ? `u${user.id}` : 'guest'            // a conversation never follows a login change
  const [open, setOpen] = useState(false)
  const [conv, setConv] = useState<{ owner: string; msgs: Msg[] }>(() => ({ owner, msgs: load(owner) }))
  const msgs = conv.owner === owner ? conv.msgs : []         // after a login / logout the old conversation is not shown
  const update = useCallback((fn: (m: Msg[]) => Msg[]) => setConv((c) => ({ owner, msgs: fn(c.owner === owner ? c.msgs : []) })), [owner])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [slow, setSlow] = useState(false)
  const end = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLInputElement>(null)

  useEffect(() => { if (conv.owner === owner) save(owner, conv.msgs) }, [conv, owner])
  useEffect(() => { if (open) end.current?.scrollIntoView({ block: 'end' }) }, [msgs, busy, open])
  useEffect(() => { if (open) input.current?.focus() }, [open])
  useEffect(() => {                                           // the AI can take a while: tell the shopper it is still working
    if (!busy) { setSlow(false); return }
    const t = setTimeout(() => setSlow(true), 6000)
    return () => clearTimeout(t)
  }, [busy])
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  const send = useCallback(async (raw: string) => {
    const content = raw.trim().slice(0, 500)
    if (!content || busy) return
    const history = [...msgs, { id: nextId(), role: 'user' as const, content }]
    update(() => history); setText(''); setBusy(true)
    try {
      const r = await api.post<ChatReply>('/chat', { messages: history.slice(-12).map(({ role, content: c }) => ({ role, content: c })) })
      update((m) => [...m, {
        id: nextId(), role: 'assistant', content: r.reply, products: r.products, promotions: r.promotions, orders: r.orders,
        actions: r.actions, suggestions: r.suggestions,
        notice: r.degraded ? 'Trợ lý AI đang bận nên mình trả lời ở chế độ cơ bản.' : undefined,
      }])
    } catch (e) {
      update((m) => [...m, { id: nextId(), role: 'assistant', content: errorMessage(e), error: true }])
    } finally { setBusy(false) }
  }, [busy, msgs, update])

  const submit = (e: FormEvent) => { e.preventDefault(); void send(text) }
  const markSent = (id: number, i: number) => update((m) => m.map((x) => (x.id === id ? { ...x, actions: x.actions?.map((a, j) => (j === i ? { ...a, sent: true } : a)) } : x)))
  const reset = () => { update(() => []); setText('') }

  const last = [...msgs].reverse().find((m) => m.role === 'assistant' && !m.error)
  const lastAsked = [...msgs].reverse().find((m) => m.role === 'user')?.content.trim().toLowerCase()
  const chips = (msgs.length === 0 ? (user?.role === 'CUSTOMER' ? CUSTOMER_CHIPS : START_CHIPS) : (last?.suggestions ?? []))
    .filter((c) => c.toLowerCase() !== lastAsked)                // do not offer the question that was just asked

  return (
    <>
      {open && (
        <section role="dialog" aria-label="Trợ lý mua sắm UniCart"
          className="fixed inset-x-3 bottom-20 z-50 flex h-[min(34rem,calc(100dvh-6rem))] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl sm:inset-x-auto sm:right-5 sm:w-[24rem]">
          <header className="flex items-center gap-2 bg-brand-600 px-4 py-3 text-white">
            <Icon name="sparkles" size={20} />
            <div className="min-w-0 flex-1"><p className="text-sm font-bold leading-tight">Trợ lý UniCart</p><p className="text-xs text-brand-100">Khuyến mại · đơn hàng · đổi trả</p></div>
            {msgs.length > 0 && <button type="button" onClick={reset} className="rounded-lg px-2 py-1 text-xs font-medium text-brand-100 hover:bg-white/15">Làm mới</button>}
            <button type="button" onClick={() => setOpen(false)} aria-label="Đóng trợ lý" className="rounded-lg p-1.5 hover:bg-white/15"><Icon name="x" size={18} /></button>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50 p-3" role="log" aria-live="polite" aria-relevant="additions">
            <Bubble role="assistant">{GREETING}</Bubble>
            {msgs.map((m) => (
              <div key={m.id} className={m.role === 'user' ? 'flex justify-end' : 'space-y-2'}>
                <Bubble role={m.role} error={m.error}>{m.content}</Bubble>
                {m.notice && <p className="px-1 text-xs text-amber-700">{m.notice}</p>}
                {m.promotions?.map((p) => <PromoCard key={p.id} promo={p} />)}
                {m.products?.slice(0, 5).map((p) => <ProductCard key={p.id} product={p} onOpen={() => setOpen(window.innerWidth >= 640)} />)}
                {m.orders?.map((o) => <OrderCard key={o.id} order={o} onOpen={() => setOpen(window.innerWidth >= 640)} />)}
                {m.actions?.map((a, i) => <ActionCard key={i} action={a} onSent={() => markSent(m.id, i)} />)}
              </div>
            ))}
            {busy && <Bubble role="assistant">{slow ? <span className="text-slate-500">Mình đang tra cứu, có thể mất vài chục giây…</span> : <span className="inline-flex gap-1" aria-label="Đang trả lời"><Dot /><Dot d="150ms" /><Dot d="300ms" /></span>}</Bubble>}
            <div ref={end} />
          </div>

          {chips.length > 0 && !busy && (
            <div className="flex gap-2 overflow-x-auto border-t border-slate-100 bg-white px-3 py-2">
              {chips.map((c) => <button key={c} type="button" onClick={() => void send(c)} className="whitespace-nowrap rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700 hover:bg-brand-100">{c}</button>)}
            </div>
          )}

          <form onSubmit={submit} className="border-t border-slate-200 bg-white p-3">
            <div className="flex gap-2">
              <input ref={input} className="input" value={text} onChange={(e) => setText(e.target.value)} maxLength={500} disabled={busy}
                placeholder="Nhập câu hỏi của bạn…" aria-label="Nhập câu hỏi" autoComplete="off" />
              <button className="btn-primary px-3" disabled={busy || !text.trim()} aria-label="Gửi"><Icon name="send" size={18} /></button>
            </div>
            <p className="mt-1.5 text-[11px] leading-snug text-slate-400">Đừng nhập mật khẩu hay số thẻ vào khung chat. Trợ lý chỉ tra cứu, không tự đổi/hủy đơn.</p>
          </form>
        </section>
      )}
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-label={open ? 'Đóng trợ lý mua sắm' : 'Mở trợ lý mua sắm'}
        className="fixed bottom-5 right-4 z-50 flex h-14 items-center gap-2 rounded-full bg-brand-600 px-4 text-sm font-semibold text-white shadow-lg transition hover:bg-brand-700 sm:right-5">
        <Icon name={open ? 'x' : 'message'} size={22} /><span className="hidden sm:inline">{open ? 'Đóng' : 'Hỏi trợ lý'}</span>
      </button>
    </>
  )
}

function Dot({ d = '0ms' }: { d?: string }) {
  return <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: d }} />
}

function Bubble({ role, error, children }: { role: 'user' | 'assistant'; error?: boolean; children: ReactNode }) {
  const style = role === 'user' ? 'bg-brand-600 text-white' : error ? 'border border-rose-200 bg-rose-50 text-rose-800' : 'border border-slate-200 bg-white text-slate-800'
  return <div className={`inline-block max-w-[88%] whitespace-pre-line break-words rounded-2xl px-3.5 py-2 text-sm leading-relaxed ${style}`}>{children}</div>
}

function ProductCard({ product: p, onOpen }: { product: Product; onOpen: () => void }) {
  return (
    <Link to={`/san-pham/${p.id}`} onClick={onOpen} className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-2 hover:border-brand-300">
      <ProductImage product={p} className="h-14 w-14 shrink-0 rounded-lg" />
      <div className="min-w-0 flex-1">
        <p className="line-clamp-2 text-sm font-medium leading-snug text-slate-800">{p.name}</p>
        <p className="mt-0.5 text-sm font-bold text-brand-700">{money(p.price)}</p>
        <p className={`text-xs ${p.in_stock ? 'text-emerald-600' : 'text-rose-600'}`}>{p.in_stock ? `Còn hàng${p.quantity <= 5 ? ` (chỉ còn ${p.quantity})` : ''}` : 'Hết hàng'}</p>
      </div>
    </Link>
  )
}

function PromoCard({ promo }: { promo: ChatPromotion }) {
  const toast = useToast()
  const copy = async () => {
    try { await navigator.clipboard.writeText(promo.code); toast.success(`Đã sao chép mã ${promo.code}`) }
    catch { toast.info(`Mã của bạn: ${promo.code}`) }
  }
  return (
    <div className="flex items-center gap-3 rounded-xl border border-dashed border-amber-300 bg-amber-50 p-3">
      <span className="text-amber-600"><Icon name="tag" size={22} /></span>
      <div className="min-w-0 flex-1"><p className="font-mono text-sm font-bold tracking-wide text-amber-900">{promo.code}</p><p className="text-xs text-amber-800">{promo.description}</p></div>
      <button type="button" onClick={() => void copy()} className="rounded-lg border border-amber-300 bg-white px-2.5 py-1 text-xs font-semibold text-amber-800 hover:bg-amber-100">Sao chép</button>
    </div>
  )
}

function OrderCard({ order: o, onOpen }: { order: Order; onOpen: () => void }) {
  return (
    <Link to={`/don-hang/${o.id}`} onClick={onOpen} className="block rounded-xl border border-slate-200 bg-white p-3 hover:border-brand-300">
      <div className="flex items-center justify-between gap-2"><span className="text-sm font-semibold">Đơn #{o.id}</span><StatusBadge status={o.status} /></div>
      <p className="mt-1 text-xs text-slate-500">{dateOnly(o.created_at)} · {o.item_count} sản phẩm · <span className="font-semibold text-slate-700">{money(o.total_amount)}</span></p>
      {o.shipment?.tracking_number && <p className="mt-0.5 text-xs text-slate-500">Vận đơn {o.shipment.tracking_number}{o.shipment.carrier ? ` · ${o.shipment.carrier}` : ''}</p>}
    </Link>
  )
}

/** The bot only drafts the request; nothing is sent until the customer edits (if needed) and presses the button. */
function ActionCard({ action, onSent }: { action: ChatAction & { sent?: boolean }; onSent: () => void }) {
  const toast = useToast()
  const [content, setContent] = useState(action.content)
  const [busy, setBusy] = useState(false)
  const done = !!action.sent
  const submit = async () => {
    setBusy(true)
    try {
      await api.post('/me/support-requests', { content: content.trim(), order_id: action.order_id })
      toast.success('Đã gửi yêu cầu. Nhân viên sẽ phản hồi sớm.'); onSent()
    } catch (e) { toast.error(errorMessage(e)) } finally { setBusy(false) }
  }
  return (
    <div className="rounded-xl border border-brand-200 bg-white p-3">
      <p className="text-xs font-semibold text-brand-700">Yêu cầu hỗ trợ{action.order_id ? ` · Đơn #${action.order_id}` : ''}</p>
      {done ? (
        <p className="mt-2 flex items-center gap-1.5 text-sm text-emerald-700"><Icon name="check" size={16} />Đã gửi. <Link to="/ho-tro" className="underline">Xem phản hồi</Link></p>
      ) : (<>
        <label className="sr-only" htmlFor="chat-request">Nội dung yêu cầu</label>
        <textarea id="chat-request" className="input mt-2 min-h-20 text-sm" value={content} maxLength={1000} onChange={(e) => setContent(e.target.value)} />
        <div className="mt-2 flex justify-end"><button type="button" className="btn-primary px-3 py-1.5 text-xs" disabled={busy || content.trim().length < 5} onClick={() => void submit()}>{busy ? 'Đang gửi…' : 'Gửi yêu cầu'}</button></div>
      </>)}
    </div>
  )
}
