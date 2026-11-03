import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from './Icon'

/** Banner quảng cáo của đối tác / thương hiệu. Chỉnh nội dung tại đây. */
export interface Banner {
  partner: string; eyebrow: string; title: string; sub: string; cta: string; to: string
  bg: string; images: string[]
}

export const SLIDES: Banner[] = [
  { partner: 'SAMSUNG', eyebrow: 'Đối tác công nghệ', title: 'Máy tính bảng & điện thoại chính hãng', sub: 'Hiệu năng mạnh, bảo hành rõ ràng, giao nhanh tận nhà.', cta: 'Mua ngay', to: '/san-pham?q=Samsung',
    bg: 'from-indigo-700 via-indigo-600 to-sky-500', images: ['/images/products/dj-161.webp', '/images/products/dj-160.webp'] },
  { partner: 'Nhà & Đời sống', eyebrow: 'Góc nhà xinh', title: 'Nội thất, đồ gia dụng cho tổ ấm', sub: 'Từ đèn bàn, chậu cây đến đồ bếp tiện dụng.', cta: 'Khám phá', to: '/san-pham?category_id=8',
    bg: 'from-amber-500 via-orange-500 to-rose-500', images: ['/images/products/dj-047.webp', '/images/products/dj-046.webp'] },
  { partner: 'SPEEDMASTER', eyebrow: 'Xe máy & phụ kiện', title: 'Lên đời xế yêu, lăn bánh tự tin', sub: 'Xe tay ga, xe thể thao và phụ kiện chính hãng.', cta: 'Xem xe', to: '/san-pham?category_id=11',
    bg: 'from-slate-800 via-slate-700 to-emerald-600', images: ['/images/products/dj-117.webp', '/images/products/dj-116.webp'] },
]

export default function HeroCarousel() {
  const [i, setI] = useState(0)
  const [paused, setPaused] = useState(false)
  const n = SLIDES.length
  useEffect(() => {
    if (paused || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const t = setInterval(() => setI((x) => (x + 1) % n), 5000)
    return () => clearInterval(t)
  }, [paused, n])

  return (
    <div className="group relative overflow-hidden rounded-2xl shadow-sm" role="region" aria-roledescription="carousel" aria-label="Quảng cáo nổi bật"
      onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocus={() => setPaused(true)} onBlur={() => setPaused(false)}>
      <div className="flex transition-transform duration-500 ease-out motion-reduce:transition-none" style={{ transform: `translateX(-${i * 100}%)` }}>
        {SLIDES.map((s, k) => (
          <div key={s.partner} className={`relative grid min-h-[260px] w-full shrink-0 items-center gap-4 bg-gradient-to-br ${s.bg} px-6 py-8 text-white sm:min-h-[340px] sm:grid-cols-[1.1fr_1fr] sm:px-12`}
            role="group" aria-roledescription="slide" aria-label={`${k + 1} trên ${n}`} aria-hidden={k !== i}>
            <div className="pointer-events-none absolute -right-16 -top-16 h-72 w-72 rounded-full bg-white/10" aria-hidden />
            <div className="pointer-events-none absolute -bottom-24 left-1/3 h-64 w-64 rounded-full bg-white/10" aria-hidden />
            <div className="relative">
              <span className="inline-block rounded-md bg-white px-3 py-1 text-sm font-black tracking-widest text-slate-900">{s.partner}</span>
              <p className="mt-3 text-xs font-semibold uppercase tracking-widest text-white/80">{s.eyebrow}</p>
              <h2 className="mt-1 text-2xl font-extrabold leading-tight sm:text-4xl">{s.title}</h2>
              <p className="mt-2 max-w-md text-sm text-white/90 sm:text-base">{s.sub}</p>
              <Link to={s.to} tabIndex={k === i ? 0 : -1} className="btn mt-5 bg-white px-5 py-2.5 text-slate-900 shadow-lg hover:bg-slate-100">{s.cta}<Icon name="arrowRight" size={16} /></Link>
            </div>
            <div className="relative hidden h-full items-center justify-center sm:flex" aria-hidden>
              <div className="absolute h-56 w-56 rounded-full bg-white/15 blur-sm" />
              <img src={s.images[0]} alt="" className="relative z-10 h-48 w-48 -rotate-6 rounded-3xl bg-white object-contain p-3 shadow-2xl" loading={k === 0 ? 'eager' : 'lazy'} />
              <img src={s.images[1]} alt="" className="relative -ml-10 mt-14 h-36 w-36 rotate-6 rounded-3xl bg-white object-contain p-3 shadow-xl" loading="lazy" />
            </div>
          </div>
        ))}
      </div>
      {(['chevronLeft', 'chevronRight'] as const).map((d, k) => (
        <button key={d} type="button" aria-label={k === 0 ? 'Banner trước' : 'Banner sau'} onClick={() => setI((x) => (x + (k === 0 ? n - 1 : 1)) % n)}
          className={`absolute top-1/2 hidden h-10 w-10 -translate-y-1/2 place-items-center rounded-full bg-white/90 text-slate-800 opacity-0 shadow transition hover:bg-white group-hover:opacity-100 focus-visible:opacity-100 sm:grid ${k === 0 ? 'left-3' : 'right-3'}`}>
          <Icon name={d} size={20} />
        </button>
      ))}
      <div className="absolute inset-x-0 bottom-3 flex justify-center gap-2">
        {SLIDES.map((s, k) => (
          <button key={s.partner} type="button" aria-label={`Đến banner ${k + 1}`} aria-current={k === i} onClick={() => setI(k)}
            className={`h-2 rounded-full transition-all ${k === i ? 'w-6 bg-white' : 'w-2 bg-white/50 hover:bg-white/80'}`} />
        ))}
      </div>
    </div>
  )
}
