import { useState, type FormEvent } from 'react'
import { api, errorMessage } from '../api/client'
import type { Address, Profile } from '../api/types'
import AddressForm from '../components/AddressForm'
import { ConfirmModal, ErrorBox, Field, PageTitle, Pill, Spinner } from '../components/ui'
import { usePrefs } from '../context/PrefsContext'
import { useToast } from '../context/ToastContext'
import { useFetch } from '../lib/useFetch'

const TABS = [['profile', 'Hồ sơ'], ['addresses', 'Sổ địa chỉ'], ['password', 'Mật khẩu'], ['privacy', 'Quyền riêng tư']] as const
const TIER: Record<string, string> = { NEW: 'Thành viên mới', REGULAR: 'Thành viên thân thiết', VIP: 'Thành viên VIP' }

export default function Account() {
  const [tab, setTab] = useState<(typeof TABS)[number][0]>('profile')
  return (
    <div className="mx-auto max-w-3xl">
      <PageTitle title="Tài khoản của tôi" />
      <div className="mb-4 flex gap-1 overflow-x-auto" role="tablist">
        {TABS.map(([k, l]) => <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)} className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium ${tab === k ? 'bg-brand-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-100'}`}>{l}</button>)}
      </div>
      {tab === 'profile' && <ProfileTab />}{tab === 'addresses' && <AddressesTab />}{tab === 'password' && <PasswordTab />}{tab === 'privacy' && <PrivacyTab />}
    </div>
  )
}

function ProfileTab() {
  const toast = useToast()
  const res = useFetch(() => api.get<Profile>('/me/profile'), [])
  const [f, setF] = useState<Profile | null>(null)
  const [busy, setBusy] = useState(false)
  if (res.loading) return <Spinner />
  if (res.error || !res.data) return <ErrorBox message={res.error ?? 'Lỗi'} onRetry={res.reload} />
  const form = f ?? res.data
  const set = (k: keyof Profile, v: string) => setF({ ...form, [k]: v })
  const save = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true)
    try { const p = await api.put<Profile>('/me/profile', { first_name: form.first_name, middle_name: form.middle_name || null, last_name: form.last_name, phone: form.phone || null }); res.setData(p); setF(null); toast.success('Đã cập nhật hồ sơ') }
    catch (e2) { toast.error(errorMessage(e2)) } finally { setBusy(false) }
  }
  return (
    <form onSubmit={save} className="card space-y-4 p-5">
      <div className="flex flex-wrap items-center gap-2 text-sm"><Pill tone="blue">{TIER[res.data.loyalty_tier] ?? res.data.loyalty_tier}</Pill><span className="text-slate-500">{res.data.loyalty_point} điểm tích lũy</span></div>
      <Field label="Email"><input className="input" value={res.data.email} disabled /></Field>
      <div className="grid gap-3 sm:grid-cols-3">
        <Field label="Họ *"><input className="input" required maxLength={50} value={form.last_name} onChange={(e) => set('last_name', e.target.value)} /></Field>
        <Field label="Tên đệm"><input className="input" maxLength={50} value={form.middle_name ?? ''} onChange={(e) => set('middle_name', e.target.value)} /></Field>
        <Field label="Tên *"><input className="input" required maxLength={50} value={form.first_name} onChange={(e) => set('first_name', e.target.value)} /></Field>
      </div>
      <Field label="Số điện thoại"><input className="input" inputMode="tel" maxLength={20} value={form.phone ?? ''} onChange={(e) => set('phone', e.target.value)} /></Field>
      <div className="flex justify-end"><button className="btn-primary" disabled={busy || !f}>{busy ? 'Đang lưu…' : 'Lưu thay đổi'}</button></div>
    </form>
  )
}

function AddressesTab() {
  const toast = useToast()
  const res = useFetch(() => api.get<Address[]>('/me/addresses'), [])
  const [edit, setEdit] = useState<Address | 'new' | null>(null)
  const [del, setDel] = useState<Address | null>(null)
  const [busy, setBusy] = useState(false)
  if (res.loading) return <Spinner />
  if (res.error) return <ErrorBox message={res.error} onRetry={res.reload} />
  const remove = async () => {
    if (!del) return
    setBusy(true)
    try { await api.del(`/me/addresses/${del.id}`); toast.success('Đã xóa địa chỉ'); setDel(null); res.reload() } catch (e) { toast.error(errorMessage(e)) } finally { setBusy(false) }
  }
  return (
    <div className="space-y-3">
      <div className="flex justify-end"><button className="btn-primary" onClick={() => setEdit('new')}>+ Thêm địa chỉ</button></div>
      {res.data?.length === 0 && <p className="card p-6 text-center text-sm text-slate-500">Bạn chưa lưu địa chỉ nào.</p>}
      {res.data?.map((a) => (
        <div key={a.id} className="card flex flex-wrap items-start justify-between gap-3 p-4 text-sm">
          <div><p className="font-semibold">{a.recipient} · {a.phone} {a.is_default && <Pill tone="blue">Mặc định</Pill>}</p><p className="text-slate-600">{a.one_line}</p></div>
          <div className="flex gap-2"><button className="btn-secondary" onClick={() => setEdit(a)}>Sửa</button><button className="btn-ghost text-rose-600" onClick={() => setDel(a)}>Xóa</button></div>
        </div>
      ))}
      {edit && <AddressForm address={edit === 'new' ? undefined : edit} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); toast.success('Đã lưu địa chỉ'); res.reload() }} />}
      {del && <ConfirmModal title="Xóa địa chỉ?" danger confirmLabel="Xóa" busy={busy} message={<>Xóa địa chỉ <b>{del.one_line}</b>? Các đơn đã đặt không bị ảnh hưởng.</>} onConfirm={remove} onClose={() => setDel(null)} />}
    </div>
  )
}

function PasswordTab() {
  const toast = useToast()
  const [f, setF] = useState({ old_password: '', new_password: '', confirm: '' })
  const [busy, setBusy] = useState(false)
  const mismatch = f.confirm !== '' && f.confirm !== f.new_password
  const weak = f.new_password !== '' && (f.new_password.length < 8 || !/[A-Za-z]/.test(f.new_password) || !/\d/.test(f.new_password))
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true)
    try { await api.post('/auth/change-password', { old_password: f.old_password, new_password: f.new_password }); toast.success('Đã đổi mật khẩu'); setF({ old_password: '', new_password: '', confirm: '' }) }
    catch (e2) { toast.error(errorMessage(e2)) } finally { setBusy(false) }
  }
  return (
    <form onSubmit={submit} className="card max-w-md space-y-4 p-5">
      <Field label="Mật khẩu hiện tại"><input className="input" type="password" autoComplete="current-password" required value={f.old_password} onChange={(e) => setF({ ...f, old_password: e.target.value })} /></Field>
      <Field label="Mật khẩu mới" hint="Tối thiểu 8 ký tự, gồm chữ và số" error={weak ? 'Mật khẩu chưa đủ mạnh' : null}><input className="input" type="password" autoComplete="new-password" required value={f.new_password} onChange={(e) => setF({ ...f, new_password: e.target.value })} /></Field>
      <Field label="Nhập lại mật khẩu mới" error={mismatch ? 'Không khớp' : null}><input className="input" type="password" autoComplete="new-password" required value={f.confirm} onChange={(e) => setF({ ...f, confirm: e.target.value })} /></Field>
      <button className="btn-primary" disabled={busy || weak || mismatch || !f.old_password || !f.new_password}>Đổi mật khẩu</button>
    </form>
  )
}

function PrivacyTab() {
  const { personalize, setPersonalize } = usePrefs()
  return (
    <div className="card space-y-3 p-5 text-sm">
      <h2 className="text-base font-bold">Cá nhân hóa gợi ý</h2>
      <p className="text-slate-600">Để gợi ý sản phẩm phù hợp, UniCart ghi lại hành vi như sản phẩm đã xem, từ khóa tìm kiếm và nhấp vào gợi ý (chỉ mã sản phẩm, loại hành động và thời gian — không lưu nội dung nhạy cảm). Bạn có thể tắt bất cứ lúc nào; khi tắt, trình duyệt này sẽ không gửi dữ liệu hành vi và gợi ý chỉ dựa trên độ phổ biến.</p>
      <label className="flex cursor-pointer items-center gap-3 font-medium">
        <input type="checkbox" className="h-5 w-5" checked={personalize} onChange={(e) => setPersonalize(e.target.checked)} /> Bật cá nhân hóa gợi ý sản phẩm
      </label>
    </div>
  )
}
