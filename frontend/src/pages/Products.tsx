import { useEffect, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Category, ProductPage, SearchResult } from '../api/types'
import ProductCard from '../components/ProductCard'
import { Empty, ErrorBox, Pagination, Spinner } from '../components/ui'
import { COLOR_LABEL, money } from '../lib/format'
import { useFetch } from '../lib/useFetch'
import Icon from '../components/Icon'

const SIZE = 12
const SORTS: [string, string][] = [['newest', 'Mới nhất'], ['price_asc', 'Giá tăng dần'], ['price_desc', 'Giá giảm dần'], ['name', 'Tên A → Z']]

type Result = (ProductPage | SearchResult) & Partial<Omit<SearchResult, keyof ProductPage>>

export default function Products() {
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const category_id = params.get('category_id') ?? ''
  const exact = params.get('exact') === '1'
  const via = params.get('via')
  const sort = params.get('sort') ?? (q ? 'relevance' : 'newest')
  const page = Number(params.get('page') ?? 1) || 1
  const min_price = params.get('min_price') ?? ''
  const max_price = params.get('max_price') ?? ''
  const [lo, setLo] = useState(min_price)
  const [hi, setHi] = useState(max_price)
  useEffect(() => { setLo(min_price); setHi(max_price) }, [min_price, max_price])

  const cats = useFetch(() => api.get<Category[]>('/categories'), [])
  // With a keyword the AI search (/search) understands the sentence; without one this is plain browsing (/products).
  const res = useFetch<Result>(() => q
    ? api.get<SearchResult>('/search', { q, category_id, sort: sort === 'newest' && !params.get('sort') ? 'relevance' : sort, page, size: SIZE, min_price, max_price, autocorrect: exact ? 'false' : undefined })
    : api.get<ProductPage>('/products', { category_id, sort: sort === 'relevance' ? 'newest' : sort, page, size: SIZE, min_price, max_price }),
  [q, category_id, sort, page, min_price, max_price, exact])

  const patch = (changes: Record<string, string | number | null>) => {
    const next = new URLSearchParams(params)
    Object.entries(changes).forEach(([k, v]) => (v === null || v === '' ? next.delete(k) : next.set(k, String(v))))
    if (!('page' in changes)) next.delete('page')
    setParams(next)
  }
  const applyPrice = (e: FormEvent) => { e.preventDefault(); patch({ min_price: lo, max_price: hi }) }
  const filtered = !!(q || category_id || min_price || max_price)
  const title = q ? `Kết quả cho “${q}”` : category_id ? cats.data?.find((c) => String(c.id) === category_id)?.name ?? 'Sản phẩm' : 'Tất cả sản phẩm'
  const sorts: [string, string][] = q ? [['relevance', 'Liên quan nhất'], ...SORTS] : SORTS
  const data = res.data
  const it = data?.interpreted
  const chips = it ? [
    it.min_price != null && `Giá từ ${money(it.min_price)}`, it.max_price != null && `Giá đến ${money(it.max_price)}`,
    ...it.brands.map((b) => `Thương hiệu: ${b}`), ...it.colors.map((c) => `Màu: ${COLOR_LABEL[c] ?? c}`), ...it.sizes.map((s) => `Size: ${s}`),
  ].filter(Boolean) as string[] : []

  return (
    <div className="grid gap-6 lg:grid-cols-[240px_1fr]">
      <aside className="card h-fit space-y-5 p-4" aria-label="Bộ lọc">
        <div>
          <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-500">Danh mục</h2>
          <ul className="space-y-0.5 text-sm">
            <li><button onClick={() => patch({ category_id: null })} className={`w-full rounded-lg px-2 py-1.5 text-left ${!category_id ? 'bg-brand-50 font-semibold text-brand-700' : 'hover:bg-slate-100'}`}>Tất cả</button></li>
            {cats.data?.map((c) => (
              <li key={c.id}><button onClick={() => patch({ category_id: c.id })} className={`flex w-full justify-between rounded-lg px-2 py-1.5 text-left ${String(c.id) === category_id ? 'bg-brand-50 font-semibold text-brand-700' : 'hover:bg-slate-100'}`}><span>{c.name}</span><span className="text-slate-400">{c.product_count}</span></button></li>
            ))}
          </ul>
        </div>
        <form onSubmit={applyPrice}>
          <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-500">Khoảng giá (đ)</h2>
          <div className="flex items-center gap-2">
            <input className="input" type="number" min={0} inputMode="numeric" placeholder="Từ" aria-label="Giá từ" value={lo} onChange={(e) => setLo(e.target.value)} />
            <span className="text-slate-400">–</span>
            <input className="input" type="number" min={0} inputMode="numeric" placeholder="Đến" aria-label="Giá đến" value={hi} onChange={(e) => setHi(e.target.value)} />
          </div>
          <button className="btn-secondary mt-2 w-full">Áp dụng</button>
        </form>
        {filtered && <button className="btn-ghost w-full" onClick={() => setParams(new URLSearchParams())}>Xóa bộ lọc</button>}
      </aside>

      <section aria-live="polite">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div><h1 className="text-xl font-bold">{title}</h1>{data && <p className="text-sm text-slate-500">{data.total} sản phẩm</p>}</div>
          <label className="flex items-center gap-2 text-sm text-slate-600">Sắp xếp
            <select className="input w-auto" value={sort} onChange={(e) => patch({ sort: e.target.value })}>{sorts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
          </label>
        </div>

        {via === 'voice' && q && <p className="mb-2 rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-700"><Icon name="mic" size={16} className="mr-1.5 inline" />Bạn đã nói: <b>“{q}”</b></p>}
        {data?.mode === 'ai' || data?.mode === 'filters' ? (
          <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-full bg-brand-100 px-2.5 py-1 font-semibold text-brand-700"><Icon name="sparkles" size={14} />Tìm kiếm AI</span>
            {chips.length > 0 && <span className="text-slate-500">Hiểu là:</span>}
            {chips.map((c) => <span key={c} className="rounded-full border border-slate-300 bg-white px-2.5 py-1 text-slate-700">{c}</span>)}
          </div>
        ) : null}
        {data?.degraded && <p className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800" role="status">Tìm kiếm thông minh đang tạm thời không khả dụng, UniCart hiển thị kết quả theo từ khóa.</p>}
        {data?.corrected && <p className="mb-3 rounded-lg bg-brand-50 px-3 py-2 text-sm text-slate-700" role="status">Hiển thị kết quả cho <b>“{data.corrected}”</b>. Tìm lại chính xác <button className="font-semibold text-brand-700 underline" onClick={() => patch({ exact: '1' })}>“{data.original}”</button></p>}

        {res.loading ? <Spinner /> : res.error ? <ErrorBox message={res.error} onRetry={res.reload} /> : data && (
          data.items.length === 0 ? (
            <Empty icon={<Icon name="search" size={40} strokeWidth={1.5} />} title="Không tìm thấy sản phẩm phù hợp"
              hint={it && (it.max_price != null || it.min_price != null) ? 'Không có sản phẩm liên quan trong khoảng giá này.' : 'Hãy thử từ khóa khác hoặc bỏ bớt bộ lọc.'}
              action={<div className="space-y-2 text-sm">
                {data.suggestion && <p>Có phải bạn muốn tìm: <Link className="font-semibold text-brand-700 underline" to={`/san-pham?q=${encodeURIComponent(data.suggestion)}`}>{data.suggestion}</Link>?</p>}
                {it && it.text && (it.max_price != null || it.min_price != null) && <p><Link className="font-semibold text-brand-700 underline" to={`/san-pham?q=${encodeURIComponent(it.text)}`}>Xem “{it.text}” không giới hạn giá</Link></p>}
              </div>} />
          ) : (<>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">{data.items.map((p) => <ProductCard key={p.id} product={p} />)}</div>
            <Pagination page={page} size={SIZE} total={data.total} onChange={(p) => { patch({ page: p }); window.scrollTo({ top: 0 }) }} />
          </>)
        )}
      </section>
    </div>
  )
}
