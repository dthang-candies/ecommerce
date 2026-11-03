import { useState, type FormEvent } from 'react'
import { api, errorMessage } from '../../api/client'
import type { Account } from '../../api/types'
import { ConfirmModal, ErrorBox, Field, Modal, PageTitle, Pill, Spinner } from '../../components/ui'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { ROLE_LABEL } from '../../lib/format'
import { useFetch } from '../../lib/useFetch'

const STAFF = ['ADMIN', 'SERVICE', 'SALES', 'WAREHOUSE', 'MARKETING', 'MANAGER']

export default function Accounts() {
  const { user } = useAuth()
  const toast = useToast()
  const [role, setRole] = useState('')
  const [q, setQ] = useState('')
  const [term, setTerm] = useState('')
  const [creating, setCreating] = useState(false)
  const [lock, setLock] = useState<Account | null>(null)
  const [busy, setBusy] = useState(false)
  const res = useFetch(() => api.get<Account[]>('/admin/accounts', { role, q: term }), [role, term])

  const changeRole = async (a: Account, next: string) => {
    try { await api.patch(`/admin/accounts/${a.id}/role`, { role: next }); toast.success('Đã đổi vai trò'); res.reload() } catch (e) { toast.error(errorMessage(e)); res.reload() }
  }
  const toggleLock = async () => {
    if (!lock) return
    setBusy(true)
    try { await api.patch(`/admin/accounts/${lock.id}/lock`, { locked: lock.status === 'ACTIVE' }); toast.success(lock.status === 'ACTIVE' ? 'Đã khóa tài khoản' : 'Đã mở khóa'); setLock(null); res.reload() }
    catch (e) { toast.error(errorMessage(e)); setLock(null) } finally { setBusy(false) }
  }

  return (
    <div>
      <PageTitle title="Tài khoản & vai trò" subtitle="Mỗi tài khoản có đúng một vai trò (BR-10, RBAC)" actions={<button className="btn-primary" onClick={() => setCreating(true)}>+ Tạo tài khoản nhân viên</button>} />
      <div className="mb-3 flex flex-wrap gap-2">
        <select className="input w-auto" value={role} onChange={(e) => setRole(e.target.value)} aria-label="Vai trò"><option value="">Mọi vai trò</option><option value="CUSTOMER">Khách hàng</option>{STAFF.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}</select>
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); setTerm(q.trim()) }}><input className="input w-56" placeholder="Tìm theo email…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Tìm tài khoản" /><button className="btn-secondary">Tìm</button></form>
      </div>
      {res.loading ? <Spinner /> : res.error ? <ErrorBox message={res.error} onRetry={res.reload} /> : (
        <div className="card overflow-x-auto"><table className="w-full">
          <thead><tr><th className="th">ID</th><th className="th">Email</th><th className="th">Vai trò</th><th className="th">Trạng thái</th><th className="th">Thao tác</th></tr></thead>
          <tbody>{res.data?.map((a) => (
            <tr key={a.id} className="border-t border-slate-100"><td className="td text-slate-400">#{a.id}</td><td className="td font-medium">{a.email}{a.id === user!.id && <span className="ml-2 text-xs text-slate-400">(bạn)</span>}</td>
              <td className="td">{a.role === 'CUSTOMER' || a.id === user!.id ? <Pill>{ROLE_LABEL[a.role]}</Pill> : <select className="input w-auto py-1" value={a.role} onChange={(e) => changeRole(a, e.target.value)} aria-label={`Vai trò của ${a.email}`}>{STAFF.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}</select>}</td>
              <td className="td">{a.status === 'ACTIVE' ? <Pill tone="green">Hoạt động</Pill> : <Pill tone="red">Đã khóa</Pill>}</td>
              <td className="td">{a.id !== user!.id && <button className={a.status === 'ACTIVE' ? 'btn-ghost text-rose-600' : 'btn-secondary'} onClick={() => setLock(a)}>{a.status === 'ACTIVE' ? 'Khóa' : 'Mở khóa'}</button>}</td></tr>))}</tbody></table></div>)}
      {creating && <CreateAccount onClose={() => setCreating(false)} onDone={() => { setCreating(false); toast.success('Đã tạo tài khoản'); res.reload() }} />}
      {lock && <ConfirmModal title={lock.status === 'ACTIVE' ? 'Khóa tài khoản?' : 'Mở khóa tài khoản?'} danger={lock.status === 'ACTIVE'} busy={busy} onConfirm={toggleLock} onClose={() => setLock(null)}
        message={lock.status === 'ACTIVE' ? <>Tài khoản <b>{lock.email}</b> sẽ không thể đăng nhập và mất quyền truy cập ngay lập tức.</> : <>Cho phép <b>{lock.email}</b> đăng nhập trở lại.</>} />}
    </div>
  )
}

function CreateAccount({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const toast = useToast()
  const [f, setF] = useState({ email: '', password: '', role: 'SERVICE' })
  const [busy, setBusy] = useState(false)
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true)
    try { await api.post('/admin/accounts', f); onDone() } catch (e2) { toast.error(errorMessage(e2)) } finally { setBusy(false) }
  }
  return (
    <Modal title="Tạo tài khoản nhân viên" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <Field label="Email *"><input className="input" type="email" required autoFocus value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
        <Field label="Mật khẩu ban đầu *" hint="Tối thiểu 8 ký tự, gồm chữ và số"><input className="input" type="password" autoComplete="new-password" required value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
        <Field label="Vai trò *"><select className="input" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>{STAFF.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}</select></Field>
        <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={onClose}>Hủy</button><button className="btn-primary" disabled={busy}>Tạo</button></div>
      </form>
    </Modal>
  )
}
