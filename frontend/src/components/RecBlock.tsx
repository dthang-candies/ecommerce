import { useEffect, useRef, type ReactNode } from 'react'
import type { Recommendation } from '../api/types'
import { usePrefs } from '../context/PrefsContext'
import ProductCard from './ProductCard'

/** A labelled recommendation block ("Gợi ý cho bạn", 3.5.2). Reports one impression when shown (FR-18). */
export default function RecBlock({ title, placement, items, cols = 'lg:grid-cols-4', footer }: { title: string; placement: string; items: Recommendation[]; cols?: string; footer?: ReactNode }) {
  const { track } = usePrefs()
  const reported = useRef(false)
  useEffect(() => {
    if (items.length && !reported.current) { reported.current = true; track('REC_IMPRESSION', { keyword: placement }) }
  }, [items.length, placement, track])
  if (!items.length) return null
  return (
    <section aria-label={title} className="mt-10">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="text-xl font-bold text-slate-900">{title}</h2>
        <span className="text-xs text-slate-400">Gợi ý cho bạn</span>
      </div>
      <div className={`grid grid-cols-2 gap-3 sm:grid-cols-3 ${cols}`}>
        {items.map((p) => <ProductCard key={p.id} product={p} placement={placement} />)}
      </div>
      {footer}
    </section>
  )
}
