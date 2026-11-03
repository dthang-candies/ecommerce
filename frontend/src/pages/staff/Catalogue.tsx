import { useState, type FormEvent } from 'react'
import { api, errorMessage } from '../../api/client'
import type { Category, Page, Product } from '../../api/types'
import ProductImage from '../../components/ProductImage'
import { ConfirmModal, Empty, ErrorBox, Field, Modal, PageTitle, Pagination, Pill, Spinner } from '../../components/ui'
import { useToast } from '../../context/ToastContext'
import { money } from '../../lib/format'
import { useFetch } from '../../lib/useFetch'
import Icon from '../../components/Icon'

const SIZE = 12

export default function Catalogue() {
  const [tab, setTab] = useState<'products' | 'categories'>('products')
  return (
    <div>
      <PageTitle title="Sản phẩm & danh mục" subtitle="Chuẩn hóa dữ liệu catalogue tập trung (FR-13)" />
      <div className="mb-4 flex gap-1" role="tablist">
        {([['products', 'Sản phẩm'], ['categories', 'Danh mục']] as const).map(([k, l]) => <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)} className={`rounded-lg px-3 py-1.5 text-sm font-medium ${tab === k ? 'bg-brand-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-100'}`}>{l}</button>)}
      </div>
      {tab === 'products' ? <Products /> : <Categories />}
    </div>
  )
}

function Products() {
  const toast = useToast()
  const [q, setQ] = useState('')
  const [term, setTerm] = useState('')
  const [status, setStatus] = useState('')
  const [cat, setCat] = useState('')
  const [page, setPage] = useState(1)
  const [edit, setEdit] = useState<Product | 'new' | null>(null)
  const [del, setDel] = useState<Product | null>(null)
  const [busy, setBusy] = useState(false)
  const cats = useFetch(() => api.get<Category[]>('/categories'), [])
  const res = useFetch(() => api.get<Page<Product>>('/admin/products', { q: term, status, category_id: cat, page, size: SIZE }), [term, status, cat, page])

  const toggle = async (p: Product) => {
    try { await api.post(`/admin/products/${p.id}/visibility`, { visible: p.status !== 'ACTIVE' }); toast.success(p.status === 'ACTIVE' ? 'Đã ẩn sản phẩm' : 'Đã hiển thị sản phẩm'); res.reload() } catch (e) { toast.error(errorMessage(e)) }
  }
  const remove = async () => {
    if (!del) return
    setBusy(true)
    try { const r = await api.del<{ result: string }>(`/admin/products/${del.id}`); toast.success(r.result === 'HIDDEN' ? 'Sản phẩm đã có lịch sử nên được ẩn thay vì xóa' : 'Đã xóa sản phẩm'); setDel(null); res.reload() }
    catch (e) { toast.error(errorMessage(e)) } finally { setBusy(false) }
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); setTerm(q.trim()); setPage(1) }}>
          <input className="input w-52" placeholder="Tên, thương hiệu, SKU…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Tìm sản phẩm" />
          <select className="input w-auto" value={cat} onChange={(e) => { setCat(e.target.value); setPage(1) }} aria-label="Danh mục"><option value="">Mọi danh mục</option>{cats.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select>
          <select className="input w-auto" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }} aria-label="Trạng thái"><option value="">Mọi trạng thái</option><option value="ACTIVE">Đang bán</option><option value="HIDDEN">Đang ẩn</option></select>
          <button className="btn-secondary">Tìm</button>
        </form>
        <button className="btn-primary" onClick={() => setEdit('new')}>+ Thêm sản phẩm</button>
      </div>
      {res.loading ? <Spinner /> : res.error ? <ErrorBox message={res.error} onRetry={res.reload} /> : res.data?.items.length === 0 ? <Empty icon={<Icon name="bag" size={40} strokeWidth={1.5} />} title="Không có sản phẩm" /> : res.data && (<>
        <div className="card overflow-x-auto"><table className="w-full">
          <thead><tr><th className="th">Sản phẩm</th><th className="th">Danh mục</th><th className="th text-right">Giá</th><th className="th text-right">Tồn</th><th className="th">Trạng thái</th><th className="th">Thao tác</th></tr></thead>
          <tbody>{res.data.items.map((p) => (
            <tr key={p.id} className="border-t border-slate-100">
              <td className="td"><div className="flex items-center gap-3"><ProductImage product={p} className="h-10 w-10 shrink-0 rounded-lg" /><div><p className="font-medium">{p.name}</p><p className="text-xs text-slate-400">{p.sku} · {p.brand ?? '—'}</p></div></div></td>
              <td className="td">{p.category.name}</td><td className="td text-right font-semibold">{money(p.price)}</td><td className="td text-right">{p.quantity}</td>
              <td className="td">{p.status === 'ACTIVE' ? <Pill tone="green">Đang bán</Pill> : <Pill>Đang ẩn</Pill>}</td>
              <td className="td"><div className="flex flex-wrap gap-1.5"><button className="btn-secondary" onClick={() => setEdit(p)}>Sửa</button><button className="btn-ghost" onClick={() => toggle(p)}>{p.status === 'ACTIVE' ? 'Ẩn' : 'Hiện'}</button><button className="btn-ghost text-rose-600" onClick={() => setDel(p)}>Xóa</button></div></td>
            </tr>))}</tbody></table></div>
        <Pagination page={page} size={SIZE} total={res.data.total} onChange={setPage} />
      </>)}
      {edit && cats.data && <ProductForm product={edit === 'new' ? undefined : edit} categories={cats.data} onClose={() => setEdit(null)} onDone={() => { setEdit(null); toast.success('Đã lưu sản phẩm'); res.reload() }} />}
      {del && <ConfirmModal title="Xóa sản phẩm?" danger confirmLabel="Xóa" busy={busy} onConfirm={remove} onClose={() => setDel(null)}
        message={<>Xóa <b>{del.name}</b>? Nếu sản phẩm đã phát sinh đơn hàng hoặc biến động kho, hệ thống sẽ chuyển sang <b>ẩn</b> thay vì xóa vật lý (BR-01).</>} />}
    </div>
  )
}

function ProductForm({ product, categories, onClose, onDone }: { product?: Product; categories: Category[]; onClose: () => void; onDone: () => void }) {
  const toast = useToast()
  const [f, setF] = useState({
    sku: product?.sku ?? '', name: product?.name ?? '', category_id: String(product?.category.id ?? categories[0]?.id ?? ''), price: String(product?.price ?? ''),
    brand: product?.brand ?? '', description: product?.description ?? '', image_url: product?.image_url ?? '',
    attributes: JSON.stringify(product?.attributes ?? {}, null, 2), quantity: '0', min_threshold: '5',
  })
  const [attrErr, setAttrErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const set = (k: keyof typeof f, v: string) => setF((s) => ({ ...s, [k]: v }))

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    let attributes: Record<string, unknown>
    try { attributes = JSON.parse(f.attributes || '{}'); if (attributes === null || typeof attributes !== 'object' || Array.isArray(attributes)) throw new Error() } catch { return setAttrErr('Thuộc tính phải là một đối tượng JSON hợp lệ, ví dụ {"size":"M"}') }
    setAttrErr(null); setBusy(true)
    const common = { name: f.name, category_id: Number(f.category_id), price: Number(f.price), brand: f.brand || null, description: f.description || null, image_url: f.image_url || null, attributes }
    try {
      product ? await api.put(`/admin/products/${product.id}`, common) : await api.post('/admin/products', { ...common, sku: f.sku, quantity: Number(f.quantity), min_threshold: Number(f.min_threshold) })
      onDone()
    } catch (e2) { toast.error(errorMessage(e2)) } finally { setBusy(false) }
  }
  return (
    <Modal title={product ? 'Sửa sản phẩm' : 'Thêm sản phẩm'} onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="SKU *"><input className="input" required maxLength={40} disabled={!!product} value={f.sku} onChange={(e) => set('sku', e.target.value)} /></Field>
          <Field label="Danh mục *"><select className="input" required value={f.category_id} onChange={(e) => set('category_id', e.target.value)}>{categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
        </div>
        <Field label="Tên sản phẩm *"><input className="input" required maxLength={200} value={f.name} onChange={(e) => set('name', e.target.value)} /></Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Giá bán (VND) *"><input className="input" type="number" min={0} step={1000} required value={f.price} onChange={(e) => set('price', e.target.value)} /></Field>
          <Field label="Thương hiệu"><input className="input" maxLength={80} value={f.brand} onChange={(e) => set('brand', e.target.value)} /></Field>
        </div>
        {!product && <div className="grid gap-3 sm:grid-cols-2"><Field label="Số lượng ban đầu"><input className="input" type="number" min={0} value={f.quantity} onChange={(e) => set('quantity', e.target.value)} /></Field><Field label="Ngưỡng tồn tối thiểu"><input className="input" type="number" min={0} value={f.min_threshold} onChange={(e) => set('min_threshold', e.target.value)} /></Field></div>}
        <Field label="Ảnh (URL)"><input className="input" type="url" maxLength={255} placeholder="https://…" value={f.image_url} onChange={(e) => set('image_url', e.target.value)} /></Field>
        <Field label="Mô tả"><textarea className="input min-h-20" value={f.description} onChange={(e) => set('description', e.target.value)} /></Field>
        <Field label="Thuộc tính (JSON)" hint='Ví dụ: {"size":"M","color":"đen"}' error={attrErr}><textarea className="input min-h-20 font-mono text-xs" value={f.attributes} onChange={(e) => set('attributes', e.target.value)} /></Field>
        <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={onClose}>Hủy</button><button className="btn-primary" disabled={busy}>{busy ? 'Đang lưu…' : 'Lưu'}</button></div>
      </form>
    </Modal>
  )
}

function Categories() {
  const toast = useToast()
  const res = useFetch(() => api.get<Category[]>('/categories'), [])
  const [edit, setEdit] = useState<Category | 'new' | null>(null)
  const [del, setDel] = useState<Category | null>(null)
  const [busy, setBusy] = useState(false)
  const remove = async () => {
    if (!del) return
    setBusy(true)
    try { await api.del(`/admin/categories/${del.id}`); toast.success('Đã xóa danh mục'); setDel(null); res.reload() } catch (e) { toast.error(errorMessage(e)); setDel(null) } finally { setBusy(false) }
  }
  return (
    <div>
      <div className="mb-3 flex justify-end"><button className="btn-primary" onClick={() => setEdit('new')}>+ Thêm danh mục</button></div>
      {res.loading ? <Spinner /> : res.error ? <ErrorBox message={res.error} onRetry={res.reload} /> : (
        <div className="card overflow-x-auto"><table className="w-full"><thead><tr><th className="th">Tên</th><th className="th">Mô tả</th><th className="th text-right">Sản phẩm đang bán</th><th className="th">Thao tác</th></tr></thead>
          <tbody>{res.data?.map((c) => <tr key={c.id} className="border-t border-slate-100"><td className="td font-medium">{c.name}</td><td className="td text-slate-500">{c.description}</td><td className="td text-right">{c.product_count}</td>
            <td className="td"><div className="flex gap-1.5"><button className="btn-secondary" onClick={() => setEdit(c)}>Sửa</button><button className="btn-ghost text-rose-600" onClick={() => setDel(c)}>Xóa</button></div></td></tr>)}</tbody></table></div>)}
      {edit && <CategoryForm category={edit === 'new' ? undefined : edit} onClose={() => setEdit(null)} onDone={() => { setEdit(null); toast.success('Đã lưu danh mục'); res.reload() }} />}
      {del && <ConfirmModal title="Xóa danh mục?" danger confirmLabel="Xóa" busy={busy} onConfirm={remove} onClose={() => setDel(null)} message={<>Xóa danh mục <b>{del.name}</b>? Chỉ xóa được khi không còn sản phẩm nào thuộc danh mục.</>} />}
    </div>
  )
}

function CategoryForm({ category, onClose, onDone }: { category?: Category; onClose: () => void; onDone: () => void }) {
  const toast = useToast()
  const [name, setName] = useState(category?.name ?? '')
  const [description, setDescription] = useState(category?.description ?? '')
  const [busy, setBusy] = useState(false)
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true)
    try { const body = { name, description: description || null }; category ? await api.put(`/admin/categories/${category.id}`, body) : await api.post('/admin/categories', body); onDone() }
    catch (e2) { toast.error(errorMessage(e2)) } finally { setBusy(false) }
  }
  return (
    <Modal title={category ? 'Sửa danh mục' : 'Thêm danh mục'} onClose={onClose}>
      <form onSubmit={submit} className="space-y-3"><Field label="Tên danh mục *"><input className="input" required maxLength={100} autoFocus value={name} onChange={(e) => setName(e.target.value)} /></Field>
        <Field label="Mô tả"><input className="input" maxLength={255} value={description} onChange={(e) => setDescription(e.target.value)} /></Field>
        <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={onClose}>Hủy</button><button className="btn-primary" disabled={busy}>Lưu</button></div></form>
    </Modal>
  )
}
