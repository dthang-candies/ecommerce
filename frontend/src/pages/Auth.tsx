import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { errorMessage } from '../api/client'
import { Field } from '../components/ui'
import { useAuth, isStaff, type RegisterData } from '../context/AuthContext'
import Icon from '../components/Icon'

function Shell({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-md py-6">
      <div className="card p-6 sm:p-8">
        <div className="mb-6 text-center"><div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-brand-600 text-white" aria-hidden><Icon name="cart" size={24} /></div>
          <h1 className="text-2xl font-extrabold">{title}</h1><p className="mt-1 text-sm text-slate-500">{subtitle}</p></div>
        {children}
      </div>
    </div>
  )
}

export function Login() {
  const { user, login } = useAuth()
  const nav = useNavigate()
  const from = (useLocation().state as { from?: string } | null)?.from
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  if (user && !busy) return <Navigate to={from ?? (isStaff(user) ? '/quan-tri' : '/')} replace />

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true); setErr(null)
    try { const u = await login(email, password); nav(from ?? (isStaff(u) ? '/quan-tri' : '/'), { replace: true }) }
    catch (e2) { setErr(errorMessage(e2)); setBusy(false) }
  }
  return (
    <Shell title="Đăng nhập" subtitle="Chào mừng bạn quay lại UniCart">
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field label="Email"><input className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoFocus /></Field>
        <Field label="Mật khẩu"><input className="input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
        {err && <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700" role="alert">{err}</p>}
        <button className="btn-primary w-full py-2.5" disabled={busy || !email || !password}>{busy ? 'Đang đăng nhập…' : 'Đăng nhập'}</button>
      </form>
      <p className="mt-5 text-center text-sm text-slate-500">Chưa có tài khoản? <Link to="/dang-ky" state={{ from }} className="font-semibold text-brand-700 hover:underline">Đăng ký ngay</Link></p>
    </Shell>
  )
}

export function Register() {
  const { user, register } = useAuth()
  const nav = useNavigate()
  const from = (useLocation().state as { from?: string } | null)?.from
  const [f, setF] = useState<RegisterData & { confirm: string }>({ email: '', password: '', confirm: '', first_name: '', last_name: '', middle_name: '', phone: '' })
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  if (user && !busy) return <Navigate to={from ?? '/'} replace />
  const set = (k: keyof typeof f, v: string) => setF((s) => ({ ...s, [k]: v }))
  const mismatch = f.confirm !== '' && f.confirm !== f.password
  const weak = f.password !== '' && (f.password.length < 8 || !/[A-Za-z]/.test(f.password) || !/\d/.test(f.password))

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true); setErr(null)
    const { confirm: _c, ...data } = f
    try { await register({ ...data, middle_name: data.middle_name || undefined, phone: data.phone || undefined }); nav(from ?? '/', { replace: true }) }
    catch (e2) { setErr(errorMessage(e2)); setBusy(false) }
  }
  return (
    <Shell title="Tạo tài khoản" subtitle="Mua sắm nhanh hơn, theo dõi đơn dễ hơn">
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Họ *"><input className="input" required maxLength={50} value={f.last_name} onChange={(e) => set('last_name', e.target.value)} autoFocus /></Field>
          <Field label="Tên đệm"><input className="input" maxLength={50} value={f.middle_name} onChange={(e) => set('middle_name', e.target.value)} /></Field>
          <Field label="Tên *"><input className="input" required maxLength={50} value={f.first_name} onChange={(e) => set('first_name', e.target.value)} /></Field>
        </div>
        <Field label="Email *"><input className="input" type="email" autoComplete="email" required maxLength={150} value={f.email} onChange={(e) => set('email', e.target.value)} /></Field>
        <Field label="Số điện thoại"><input className="input" inputMode="tel" maxLength={20} value={f.phone} onChange={(e) => set('phone', e.target.value)} /></Field>
        <Field label="Mật khẩu *" hint="Tối thiểu 8 ký tự, gồm chữ và số" error={weak ? 'Mật khẩu chưa đủ mạnh' : null}><input className="input" type="password" autoComplete="new-password" required value={f.password} onChange={(e) => set('password', e.target.value)} /></Field>
        <Field label="Nhập lại mật khẩu *" error={mismatch ? 'Mật khẩu nhập lại không khớp' : null}><input className="input" type="password" autoComplete="new-password" required value={f.confirm} onChange={(e) => set('confirm', e.target.value)} /></Field>
        {err && <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700" role="alert">{err}</p>}
        <button className="btn-primary w-full py-2.5" disabled={busy || weak || mismatch || !f.password || !f.confirm}>{busy ? 'Đang tạo…' : 'Đăng ký'}</button>
      </form>
      <p className="mt-5 text-center text-sm text-slate-500">Đã có tài khoản? <Link to="/dang-nhap" state={{ from }} className="font-semibold text-brand-700 hover:underline">Đăng nhập</Link></p>
    </Shell>
  )
}
