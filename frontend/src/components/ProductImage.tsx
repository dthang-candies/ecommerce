import Icon, { CATEGORY_ICON } from './Icon'
import type { Product } from '../api/types'

const LOOK: Record<number, { bg: string }> = {
  1: { bg: 'from-amber-100 to-orange-200' }, 2: { bg: 'from-sky-100 to-indigo-200' },
  3: { bg: 'from-rose-100 to-pink-200' }, 4: { bg: 'from-emerald-100 to-teal-200' },
  5: { bg: 'from-yellow-100 to-lime-200' }, 6: { bg: 'from-fuchsia-100 to-purple-200' },
  7: { bg: 'from-cyan-100 to-blue-200' }, 8: { bg: 'from-orange-100 to-amber-200' },
  9: { bg: 'from-lime-100 to-green-200' }, 10: { bg: 'from-sky-100 to-blue-200' },
  11: { bg: 'from-slate-100 to-zinc-300' },
}

/** Product photo, or a category-coloured placeholder when the product has no image yet. */
export default function ProductImage({ product, className = '' }: { product: Pick<Product, 'name' | 'image_url'> & { category?: { id: number }; category_id?: number }; className?: string }) {
  if (product.image_url) {
    return <img src={product.image_url} alt={product.name} loading="lazy" className={`bg-white object-contain ${className}`} />
  }
  const look = LOOK[product.category?.id ?? product.category_id ?? 0] ?? { bg: 'from-slate-100 to-slate-200' }
  return (
    <div className={`flex items-center justify-center bg-gradient-to-br ${look.bg} ${className}`} role="img" aria-label={product.name}>
      <Icon name={CATEGORY_ICON[product.category?.id ?? product.category_id ?? 0] ?? 'bag'} size={56} strokeWidth={1.5} className="text-slate-600/70" />
    </div>
  )
}
