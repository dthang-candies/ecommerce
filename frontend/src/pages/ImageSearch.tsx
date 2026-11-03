import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import type { SearchResult } from '../api/types'
import ImagePicker from '../components/ImagePicker'
import ProductCard from '../components/ProductCard'
import { Empty, PageTitle } from '../components/ui'
import { prepareImage } from '../lib/media'
import Icon from '../components/Icon'

type State = { phase: 'idle' } | { phase: 'working' } | { phase: 'error'; message: string } | { phase: 'done'; result: SearchResult }

/** Visual search: Gemini recognises the product in the photo, then the normal AI search finds similar items. */
export default function ImageSearch() {
  const first = (useLocation().state as { file?: File } | null)?.file
  const [preview, setPreview] = useState<string | null>(null)
  const [state, setState] = useState<State>({ phase: first ? 'working' : 'idle' })
  const current = useRef(0)

  const run = useCallback(async (file: File) => {
    const id = ++current.current
    setPreview((old) => { if (old) URL.revokeObjectURL(old); return URL.createObjectURL(file) })
    setState({ phase: 'working' })
    try {
      const jpeg = await prepareImage(file)
      const result = await api.upload<SearchResult>('/search/image', jpeg, { size: 12 })
      if (id === current.current) setState({ phase: 'done', result })
    } catch (e) { if (id === current.current) setState({ phase: 'error', message: errorMessage(e) }) }
  }, [])

  useEffect(() => { if (first) void run(first) }, [first, run])
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])

  const result = state.phase === 'done' ? state.result : null
  const seen = result?.recognized

  return (
    <div>
      <PageTitle title="Tìm kiếm bằng hình ảnh" subtitle="Tải ảnh một sản phẩm, UniCart sẽ tìm các sản phẩm tương tự" />
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <aside className="space-y-3">
          {preview && <img src={preview} alt="Ảnh bạn đã chọn" className="aspect-square w-full rounded-2xl border border-slate-200 object-cover" />}
          <ImagePicker compact onPick={run} />
        </aside>
        <section aria-live="polite">
          {state.phase === 'idle' && <Empty icon={<Icon name="camera" size={40} strokeWidth={1.5} />} title="Chọn một bức ảnh để bắt đầu" hint="Ảnh rõ nét, một sản phẩm chính, nền đơn giản sẽ cho kết quả tốt nhất." />}
          {state.phase === 'working' && (
            <div className="flex flex-col items-center gap-3 py-20 text-slate-500" role="status">
              <span className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" aria-hidden />
              <p className="text-sm">Gemini đang nhận diện sản phẩm trong ảnh…</p>
            </div>
          )}
          {state.phase === 'error' && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert">
              <p>{state.message}</p>
              <p className="mt-2 text-rose-700">Bạn có thể thử ảnh khác, hoặc <Link to="/san-pham" className="font-semibold underline">tìm bằng từ khóa</Link>.</p>
            </div>
          )}
          {result && (<>
            {seen && (
              <div className="mb-4 rounded-xl border border-brand-200 bg-brand-50 p-4 text-sm">
                <p className="flex items-center gap-1.5"><Icon name="sparkles" size={16} />Nhận diện: <b>{seen.query}</b>{seen.color ? <> · màu <b>{seen.color}</b></> : null}{seen.brand ? <> · thương hiệu <b>{seen.brand}</b></> : null}</p>
                <p className="mt-1 text-slate-600">Không đúng ý? <Link className="font-semibold text-brand-700 underline" to={`/san-pham?q=${encodeURIComponent(seen.query)}`}>Sửa từ khóa và tìm lại</Link></p>
              </div>
            )}
            {result.items.length === 0 ? (
              <Empty icon={<Icon name="search" size={40} strokeWidth={1.5} />} title="Chưa có sản phẩm tương tự trong cửa hàng" hint="Hãy thử ảnh khác hoặc tìm bằng từ khóa." action={<Link to="/san-pham" className="btn-primary">Xem tất cả sản phẩm</Link>} />
            ) : (<>
              <h2 className="mb-3 text-lg font-bold">{result.total} sản phẩm tương tự</h2>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-3">{result.items.map((p) => <ProductCard key={p.id} product={p} />)}</div>
            </>)}
          </>)}
        </section>
      </div>
    </div>
  )
}
