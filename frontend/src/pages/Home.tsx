import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { Category, ProductPage, Recommendation } from '../api/types'
import ProductCard from '../components/ProductCard'
import RecBlock from '../components/RecBlock'
import { ErrorBox, Spinner } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { usePrefs } from '../context/PrefsContext'
import { useFetch } from '../lib/useFetch'
import HeroCarousel from '../components/HeroCarousel'
import Icon, { CATEGORY_ICON, type IconName } from '../components/Icon'

const SIDE = [
  { partner: 'OLAY · VASELINE', title: 'Chăm sóc da mỗi ngày', cta: 'Mua sắm ngay', to: '/san-pham?category_id=6', bg: 'from-fuchsia-600 to-pink-500', images: ['/images/products/dj-119.webp', '/images/products/dj-120.webp'] },
  { partner: 'THỜI TRANG', title: 'Thời trang mới về', cta: 'Xem bộ sưu tập', to: '/san-pham?category_id=3', bg: 'from-violet-600 to-blue-500', images: ['/images/products/dj-181.webp', '/images/products/dj-189.webp'] },
]
const PERKS: { icon: IconName; label: string; hint: string; to: string; tone: string }[] = [
  { icon: 'truck', label: 'Freeship từ 500.000đ', hint: 'Giao nhanh toàn quốc', to: '/san-pham', tone: 'bg-orange-50 text-orange-600' },
  { icon: 'shield', label: 'Thanh toán an toàn', hint: 'COD hoặc trực tuyến', to: '/san-pham', tone: 'bg-emerald-50 text-emerald-600' },
  { icon: 'undo', label: 'Hủy đơn dễ dàng', hint: 'Trước khi đóng gói', to: '/don-hang', tone: 'bg-sky-50 text-sky-600' },
  { icon: 'sparkles', label: 'Tìm kiếm bằng AI', hint: 'Giọng nói & hình ảnh', to: '/tim-kiem-anh', tone: 'bg-violet-50 text-violet-600' },
  { icon: 'message', label: 'Hỗ trợ khách hàng', hint: 'Gửi yêu cầu cho UniCart', to: '/ho-tro', tone: 'bg-rose-50 text-rose-600' },
]
const BRANDS = ['Samsung', 'Olay', 'Vaseline', 'Pearson', 'Nhã Nam', 'Pampi', 'SpeedMaster', 'ScootMaster']

export default function Home() {
  const { user } = useAuth()
  const { personalize } = usePrefs()
  const cats = useFetch(async () => {
    const list = await api.get<Category[]>('/categories')
    // ảnh đại diện của danh mục = ảnh sản phẩm đầu tiên có ảnh trong danh mục đó
    return Promise.all(list.map(async (c): Promise<Category & { cover?: string }> => {
      try {
        const page = await api.get<ProductPage>('/products', { category_id: c.id, size: 12 })
        return { ...c, cover: page.items.find((p) => p.image_url)?.image_url ?? undefined }
      } catch { return c }
    }))
  }, [])
  const rec = useFetch(() => api.get<Recommendation[]>('/recommendations/home', { personalize, limit: 8 }), [user?.id, personalize])
  const latest = useFetch(() => api.get<ProductPage>('/products', { size: 8 }), [])
  const personal = rec.data?.some((r) => r.reason === 'Dành cho bạn')

  return (
    <div>
      {/* Banner đối tác */}
      <section aria-label="Ưu đãi nổi bật" className="grid gap-3 lg:grid-cols-3">
        <div className="lg:col-span-2"><HeroCarousel /></div>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-1">
          {SIDE.map((b) => (
            <Link key={b.title} to={b.to} className={`group relative flex min-h-[150px] items-center overflow-hidden rounded-2xl bg-gradient-to-br ${b.bg} p-4 text-white shadow-sm transition hover:shadow-lg sm:p-5`}>
              <div className="relative z-10 max-w-[55%]">
                <span className="rounded bg-white px-2 py-0.5 text-[11px] font-black tracking-widest text-slate-900">{b.partner}</span>
                <p className="mt-2 text-base font-extrabold leading-snug sm:text-lg">{b.title}</p>
                <p className="mt-1 inline-flex items-center gap-1 text-xs font-semibold text-white/90 group-hover:gap-2">{b.cta}<Icon name="arrowRight" size={14} /></p>
              </div>
              <div className="absolute -right-3 top-1/2 flex -translate-y-1/2 items-center" aria-hidden>
                {b.images.map((src, k) => <img key={src} src={src} alt="" loading="lazy" className={`h-24 w-24 rounded-2xl bg-white object-contain p-1.5 shadow-xl sm:h-28 sm:w-28 ${k === 0 ? '-rotate-6' : '-ml-8 rotate-6'}`} />)}
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Lối tắt dịch vụ */}
      <section aria-label="Dịch vụ" className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-slate-200 bg-slate-200 shadow-sm sm:grid-cols-3 lg:grid-cols-5">
        {PERKS.map((p) => (
          <Link key={p.label} to={p.to} className="group flex flex-col items-center gap-2 bg-white px-3 py-4 text-center transition hover:bg-brand-50">
            <span className={`grid h-12 w-12 place-items-center rounded-2xl ${p.tone} transition group-hover:scale-110`}><Icon name={p.icon} size={24} strokeWidth={1.75} /></span>
            <span className="text-sm font-semibold leading-tight text-slate-800">{p.label}</span>
            <span className="-mt-1 text-xs text-slate-500">{p.hint}</span>
          </Link>
        ))}
      </section>

      {/* Danh mục */}
      <section className="mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm" aria-label="Danh mục">
        <div className="flex items-baseline justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="text-lg font-bold uppercase tracking-wide text-slate-600">Danh mục</h2>
          <Link to="/san-pham" className="inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:underline">Tất cả sản phẩm<Icon name="arrowRight" size={14} /></Link>
        </div>
        {cats.loading ? <div className="p-6"><Spinner /></div> : cats.error ? <div className="p-6"><ErrorBox message={cats.error} onRetry={cats.reload} /></div> : (
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6">
            {cats.data?.map((c) => (
              <Link key={c.id} to={`/san-pham?category_id=${c.id}`} className="group flex flex-col items-center gap-3 border-b border-r border-slate-100 px-2 py-5 text-center transition hover:z-10 hover:bg-brand-50/60 hover:shadow-[0_0_14px_rgba(79,70,229,0.18)]">
                <span className="grid h-20 w-20 place-items-center overflow-hidden rounded-full bg-slate-100 text-brand-600 transition group-hover:scale-105 sm:h-24 sm:w-24">
                  {c.cover
                    ? <img src={c.cover} alt="" loading="lazy" className="h-full w-full object-contain p-2.5 mix-blend-multiply" />
                    : <Icon name={CATEGORY_ICON[c.id] ?? 'bag'} size={34} strokeWidth={1.5} />}
                </span>
                <span className="line-clamp-2 min-h-10 text-sm font-medium text-slate-800 group-hover:text-brand-700">{c.name}</span>
                <span className="-mt-3 text-xs text-slate-400">{c.product_count} sản phẩm</span>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Thương hiệu đối tác */}
      <section className="mt-4 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm" aria-label="Thương hiệu đối tác">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">Thương hiệu đối tác</h2>
          <ul className="flex flex-1 flex-wrap items-center gap-2">
            {BRANDS.map((b) => (
              <li key={b}><Link to={`/san-pham?q=${encodeURIComponent(b)}`} className="inline-block rounded-lg border border-slate-200 px-3.5 py-1.5 text-sm font-extrabold tracking-wide text-slate-600 transition hover:border-brand-500 hover:bg-brand-50 hover:text-brand-700">{b}</Link></li>
            ))}
          </ul>
        </div>
      </section>

      {rec.loading ? <Spinner /> : rec.data && <RecBlock title={personal ? 'Dành cho bạn' : 'Bán chạy & nổi bật'} placement="home" items={rec.data} />}

      <section className="mt-10" aria-label="Sản phẩm mới">
        <div className="mb-3 flex items-baseline justify-between"><h2 className="text-xl font-bold">Sản phẩm mới</h2><Link to="/san-pham" className="text-sm font-medium text-brand-700 hover:underline">Xem tất cả →</Link></div>
        {latest.loading ? <Spinner /> : latest.error ? <ErrorBox message={latest.error} onRetry={latest.reload} /> : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">{latest.data?.items.map((p) => <ProductCard key={p.id} product={p} />)}</div>
        )}
      </section>
    </div>
  )
}
