import { useEffect, useId, type ReactNode } from 'react'
import type { OrderStatus } from '../api/types'
import { STATUS_LABEL, STATUS_TONE } from '../lib/format'
import Icon from './Icon'

export function Spinner({ label = 'Đang tải…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-slate-500" role="status">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" aria-hidden />
      <span className="text-sm">{label}</span>
    </div>
  )
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert">
      <p>{message}</p>
      {onRetry && <button className="btn-secondary mt-3" onClick={onRetry}>Thử lại</button>}
    </div>
  )
}

export function Empty({ icon = <Icon name="package" size={40} strokeWidth={1.5} />, title, hint, action }: { icon?: ReactNode; title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
      <div className="text-4xl text-slate-400" aria-hidden>{icon}</div>
      <h3 className="mt-3 text-base font-semibold text-slate-800">{title}</h3>
      {hint && <p className="mt-1 max-w-sm text-sm text-slate-500">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function StatusBadge({ status }: { status: OrderStatus }) {
  return <span className={`inline-flex whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_TONE[status]}`}>{STATUS_LABEL[status]}</span>
}

export function Pill({ tone = 'slate', children }: { tone?: 'slate' | 'green' | 'red' | 'amber' | 'blue'; children: ReactNode }) {
  const tones = { slate: 'bg-slate-100 text-slate-700', green: 'bg-emerald-100 text-emerald-800', red: 'bg-rose-100 text-rose-800', amber: 'bg-amber-100 text-amber-800', blue: 'bg-sky-100 text-sky-800' }
  return <span className={`inline-flex whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ${tones[tone]}`}>{children}</span>
}

export function Stars({ value, size = 'text-base' }: { value: number; size?: string }) {
  return (
    <span className={`${size} text-amber-400`} role="img" aria-label={`${value} trên 5 sao`}>
      {[1, 2, 3, 4, 5].map((i) => <span key={i} className={i <= Math.round(value) ? '' : 'text-slate-300'}><Icon name="star" size={16} fill="currentColor" strokeWidth={1} className="inline" /></span>)}
    </span>
  )
}

export function StarInput({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex gap-1" role="radiogroup" aria-label="Số sao">
      {[1, 2, 3, 4, 5].map((i) => (
        <button key={i} type="button" role="radio" aria-checked={value === i} aria-label={`${i} sao`} onClick={() => onChange(i)}
          className={`leading-none transition ${i <= value ? 'text-amber-400' : 'text-slate-300 hover:text-amber-200'}`}><Icon name="star" size={30} fill="currentColor" strokeWidth={1} /></button>
      ))}
    </div>
  )
}

export function Pagination({ page, size, total, onChange }: { page: number; size: number; total: number; onChange: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / size))
  if (pages <= 1) return null
  const around = Array.from({ length: pages }, (_, i) => i + 1).filter((p) => p === 1 || p === pages || Math.abs(p - page) <= 1)
  return (
    <nav className="mt-6 flex flex-wrap items-center justify-center gap-1" aria-label="Phân trang">
      <button className="btn-secondary" disabled={page <= 1} onClick={() => onChange(page - 1)}>‹ Trước</button>
      {around.map((p, i) => (
        <span key={p} className="flex items-center gap-1">
          {i > 0 && p - around[i - 1] > 1 && <span className="px-1 text-slate-400">…</span>}
          <button onClick={() => onChange(p)} aria-current={p === page ? 'page' : undefined}
            className={`h-9 min-w-9 rounded-lg px-2 text-sm font-medium ${p === page ? 'bg-brand-600 text-white' : 'text-slate-600 hover:bg-slate-100'}`}>{p}</button>
        </span>
      ))}
      <button className="btn-secondary" disabled={page >= pages} onClick={() => onChange(page + 1)}>Sau ›</button>
    </nav>
  )
}

export function Modal({ title, onClose, children, wide }: { title: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
  const id = useId()
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.removeEventListener('keydown', onKey); document.body.style.overflow = prev }
  }, [onClose])
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/50 p-0 sm:items-center sm:p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div role="dialog" aria-modal="true" aria-labelledby={id}
        className={`max-h-[92vh] w-full overflow-y-auto rounded-t-2xl bg-white p-5 shadow-xl sm:rounded-2xl ${wide ? 'sm:max-w-2xl' : 'sm:max-w-md'}`}>
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 id={id} className="text-lg font-bold text-slate-900">{title}</h2>
          <button className="rounded-lg p-1 text-slate-500 hover:bg-slate-100" onClick={onClose} aria-label="Đóng"><Icon name="x" size={20} /></button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function ConfirmModal({ title, message, confirmLabel = 'Xác nhận', danger, busy, onConfirm, onClose }:
  { title: string; message: ReactNode; confirmLabel?: string; danger?: boolean; busy?: boolean; onConfirm: () => void; onClose: () => void }) {
  return (
    <Modal title={title} onClose={onClose}>
      <div className="text-sm text-slate-600">{message}</div>
      <div className="mt-5 flex justify-end gap-2">
        <button className="btn-secondary" onClick={onClose} disabled={busy}>Hủy</button>
        <button className={danger ? 'btn-danger' : 'btn-primary'} onClick={onConfirm} disabled={busy}>{busy ? 'Đang xử lý…' : confirmLabel}</button>
      </div>
    </Modal>
  )
}

export function Field({ label, error, hint, children }: { label: string; error?: string | null; hint?: string; children: ReactNode }) {
  return (
    <div>
      <label className="label">{label}</label>
      {children}
      {hint && !error && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
      {error && <p className="mt-1 text-xs text-rose-600" role="alert">{error}</p>}
    </div>
  )
}

export function PageTitle({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions}
    </div>
  )
}

export function Stat({ label, value, hint, tone }: { label: string; value: ReactNode; hint?: string; tone?: 'warn' | 'good' }) {
  return (
    <div className="card p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${tone === 'warn' ? 'text-rose-600' : tone === 'good' ? 'text-emerald-600' : 'text-slate-900'}`}>{value}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}
