import { useState, type FormEvent } from 'react'
import { api, errorMessage } from '../api/client'
import type { Address } from '../api/types'
import { Field, Modal } from './ui'

const EMPTY = { recipient: '', phone: '', street: '', district: '', city: '', post_code: '', is_default: false }

export default function AddressForm({ address, onSaved, onClose }: { address?: Address; onSaved: (a: Address) => void; onClose: () => void }) {
  const [f, setF] = useState(address ? { ...EMPTY, ...address, district: address.district ?? '', post_code: address.post_code ?? '' } : EMPTY)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const set = (k: keyof typeof EMPTY, v: string | boolean) => setF((s) => ({ ...s, [k]: v }))

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true); setErr(null)
    const body = { recipient: f.recipient, phone: f.phone, street: f.street, district: f.district || null, city: f.city, post_code: f.post_code || null, is_default: f.is_default }
    try {
      onSaved(address ? await api.put<Address>(`/me/addresses/${address.id}`, body) : await api.post<Address>('/me/addresses', body))
    } catch (e2) { setErr(errorMessage(e2)) } finally { setBusy(false) }
  }

  return (
    <Modal title={address ? 'Sửa địa chỉ' : 'Thêm địa chỉ giao hàng'} onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Người nhận *"><input className="input" required maxLength={100} value={f.recipient} onChange={(e) => set('recipient', e.target.value)} autoFocus /></Field>
          <Field label="Số điện thoại *"><input className="input" required inputMode="tel" maxLength={20} value={f.phone} onChange={(e) => set('phone', e.target.value)} /></Field>
        </div>
        <Field label="Số nhà, đường *"><input className="input" required maxLength={150} value={f.street} onChange={(e) => set('street', e.target.value)} /></Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Quận / Huyện"><input className="input" maxLength={80} value={f.district} onChange={(e) => set('district', e.target.value)} /></Field>
          <Field label="Tỉnh / Thành phố *"><input className="input" required maxLength={80} value={f.city} onChange={(e) => set('city', e.target.value)} /></Field>
        </div>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.is_default} onChange={(e) => set('is_default', e.target.checked)} /> Đặt làm địa chỉ mặc định</label>
        {err && <p className="rounded-lg bg-rose-50 p-2 text-sm text-rose-700" role="alert">{err}</p>}
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" className="btn-secondary" onClick={onClose}>Hủy</button>
          <button className="btn-primary" disabled={busy}>{busy ? 'Đang lưu…' : 'Lưu địa chỉ'}</button>
        </div>
      </form>
    </Modal>
  )
}
