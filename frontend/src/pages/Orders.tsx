import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { Order, OrderStatus } from '../api/types'
import ProductImage from '../components/ProductImage'
import { Empty, ErrorBox, PageTitle, Spinner, StatusBadge } from '../components/ui'
import { dateTime, money } from '../lib/format'
import { useFetch } from '../lib/useFetch'
import Icon from '../components/Icon'

const TABS: [string, string, OrderStatus[] | null][] = [
  ['all', 'Tất cả', null], ['pay', 'Chờ thanh toán', ['PENDING_PAYMENT']], ['wait', 'Chờ xác nhận', ['PENDING']],
  ['prep', 'Đang chuẩn bị', ['CONFIRMED', 'PACKED']], ['ship', 'Đang giao', ['SHIPPING']], ['done', 'Đã giao', ['DELIVERED']], ['cancel', 'Đã hủy', ['CANCELLED']],
]

export default function Orders() {
  const res = useFetch(() => api.get<Order[]>('/orders'), [])
  const [tab, setTab] = useState('all')
  if (res.loading) return <Spinner />
  if (res.error) return <ErrorBox message={res.error} onRetry={res.reload} />
  const filter = TABS.find((t) => t[0] === tab)?.[2]
  const orders = (res.data ?? []).filter((o) => !filter || filter.includes(o.status))

  return (
    <div>
      <PageTitle title="Đơn hàng của tôi" subtitle="Theo dõi trạng thái và hành trình giao hàng" />
      <div className="mb-4 flex gap-1 overflow-x-auto" role="tablist">
        {TABS.map(([k, label, st]) => {
          const n = st ? res.data?.filter((o) => st.includes(o.status)).length : res.data?.length
          return <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)} className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium ${tab === k ? 'bg-brand-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-100'}`}>{label}{n ? ` (${n})` : ''}</button>
        })}
      </div>
      {orders.length === 0 ? <Empty icon={<Icon name="package" size={40} strokeWidth={1.5} />} title="Chưa có đơn hàng" hint="Các đơn hàng của bạn sẽ hiển thị ở đây." action={<Link to="/san-pham" className="btn-primary">Mua sắm ngay</Link>} /> : (
        <ul className="space-y-3">{orders.map((o) => (
          <li key={o.id} className="card p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div><Link to={`/don-hang/${o.id}`} className="font-bold text-brand-700 hover:underline">Đơn #{o.id}</Link><span className="ml-2 text-sm text-slate-500">{dateTime(o.created_at)}</span></div>
              <StatusBadge status={o.status} />
            </div>
            <div className="mt-3 flex items-center gap-2 overflow-x-auto">
              {o.items.slice(0, 4).map((i) => <ProductImage key={i.product_id} product={i} className="h-14 w-14 shrink-0 rounded-lg" />)}
              {o.items.length > 4 && <span className="text-sm text-slate-500">+{o.items.length - 4}</span>}
              <p className="ml-2 min-w-0 flex-1 truncate text-sm text-slate-600">{o.items[0]?.name}{o.items.length > 1 ? ` và ${o.items.length - 1} sản phẩm khác` : ''}</p>
            </div>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3">
              <p className="text-sm text-slate-500">{o.item_count} sản phẩm · Tổng <b className="text-base text-slate-900">{money(o.total_amount)}</b></p>
              <div className="flex gap-2">
                {o.status === 'PENDING_PAYMENT' && <Link to={`/don-hang/${o.id}/thanh-toan`} className="btn-primary">Thanh toán</Link>}
                <Link to={`/don-hang/${o.id}`} className="btn-secondary">Chi tiết</Link>
              </div>
            </div>
          </li>
        ))}</ul>
      )}
    </div>
  )
}
