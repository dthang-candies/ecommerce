import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import type { Dashboard, OrderStatus, Role } from '../../api/types'
import Icon, { type IconName } from '../../components/Icon'
import { ErrorBox, PageTitle, Spinner, Stat, StatusBadge } from '../../components/ui'
import { useAuth } from '../../context/AuthContext'
import { ROLE_LABEL, dateOnly, dateTime, money } from '../../lib/format'
import { useFetch } from '../../lib/useFetch'
import { BarChart } from './Reports'
import { STAFF_NAV } from './StaffLayout'

interface Todo { label: string; count: number; to: string; icon: IconName; roles: Role[] }

/** Things that are waiting for someone, each linked to the page where this role can act on it. */
function todos(d: Dashboard): Todo[] {
  const w = d.orders?.waiting
  const all: Todo[] = [
    { label: 'Đơn chờ xác nhận', count: w?.PENDING ?? 0, to: '/quan-tri/don-hang?status=PENDING', icon: 'receipt', roles: ['SERVICE', 'ADMIN', 'MANAGER', 'SALES'] },
    { label: 'Đơn chờ đóng gói', count: w?.CONFIRMED ?? 0, to: '/quan-tri/don-hang?status=CONFIRMED', icon: 'package', roles: ['WAREHOUSE', 'ADMIN', 'MANAGER'] },
    { label: 'Đơn chờ bàn giao vận chuyển', count: w?.PACKED ?? 0, to: '/quan-tri/don-hang?status=PACKED', icon: 'truck', roles: ['WAREHOUSE', 'ADMIN', 'MANAGER'] },
    { label: 'Yêu cầu hỗ trợ mới', count: d.support?.open ?? 0, to: '/quan-tri/ho-tro', icon: 'message', roles: ['SALES', 'ADMIN'] },
    { label: 'Sản phẩm sắp hết / hết hàng', count: d.inventory?.low_stock ?? 0, to: '/quan-tri/kho', icon: 'alert', roles: ['WAREHOUSE', 'ADMIN', 'MANAGER'] },
    { label: 'Yêu cầu nhập hàng đang mở', count: d.inventory?.open_restock_requests ?? 0, to: '/quan-tri/kho', icon: 'truck', roles: ['WAREHOUSE', 'ADMIN', 'MANAGER'] },
  ]
  return all
}

function change(now: number, before: number): string {
  if (!before) return now ? 'Chưa có dữ liệu 7 ngày trước' : 'Chưa có đơn'
  const pct = Math.round(((now - before) / before) * 100)
  return `${pct >= 0 ? '+' : ''}${pct}% so với 7 ngày trước`
}

function Section({ title, link, children }: { title: string; link?: { to: string; label: string }; children: ReactNode }) {
  return (
    <section className="card p-5">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-bold">{title}</h2>
        {link && <Link to={link.to} className="text-sm font-medium text-brand-700 hover:underline">{link.label}</Link>}
      </div>
      {children}
    </section>
  )
}

export default function StaffDashboard() {
  const { user } = useAuth()
  const res = useFetch(() => api.get<Dashboard>('/staff/dashboard'), [])
  const role = user!.role
  const d = res.data
  const allowed = (to: string) => STAFF_NAV.some((n) => n.to === to.split('?')[0] && n.roles.includes(role))
  const work = d ? todos(d).filter((t) => t.roles.includes(role) && allowed(t.to)) : []
  const shortcuts = STAFF_NAV.filter((n) => n.to !== '/quan-tri' && n.roles.includes(role))

  return (
    <div>
      <PageTitle title="Tổng quan" subtitle={`${ROLE_LABEL[role]}${d ? ` · ${dateOnly(d.date)}` : ''}`}
        actions={<button className="btn-secondary" onClick={res.reload} disabled={res.loading}>Làm mới</button>} />
      {res.loading && !d ? <Spinner /> : res.error ? <ErrorBox message={res.error} onRetry={res.reload} /> : d && (
        <div className="space-y-5">
          {d.sales && (
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <Stat label="Doanh số hôm nay" value={money(d.sales.today.sales)} hint={`Hôm qua: ${money(d.sales.yesterday.sales)}`} tone="good" />
              <Stat label="Đơn hôm nay" value={d.sales.today.orders} hint={`Hôm qua: ${d.sales.yesterday.orders} đơn`} />
              <Stat label="Doanh số 7 ngày" value={money(d.sales.last_7_days.sales)} hint={change(d.sales.last_7_days.sales, d.sales.previous_7_days.sales)} />
              <Stat label="Đơn 7 ngày" value={d.sales.last_7_days.orders} hint={change(d.sales.last_7_days.orders, d.sales.previous_7_days.orders)} />
            </div>
          )}

          {work.length > 0 && (
            <Section title="Việc cần xử lý">
              <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {work.map((t) => (
                  <li key={t.label}>
                    <Link to={t.to} className={`flex items-center gap-3 rounded-xl border p-3 transition hover:border-brand-400 hover:bg-brand-50 ${t.count ? 'border-amber-200 bg-amber-50' : 'border-slate-200'}`}>
                      <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-lg ${t.count ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-400'}`} aria-hidden><Icon name={t.icon} size={20} /></span>
                      <span className="min-w-0 flex-1 text-sm text-slate-600">{t.label}</span>
                      <b className={`text-2xl ${t.count ? 'text-slate-900' : 'text-slate-300'}`}>{t.count}</b>
                    </Link>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {d.sales && (
            <Section title="Doanh số 7 ngày gần nhất" link={{ to: '/quan-tri/bao-cao', label: 'Xem báo cáo' }}>
              <BarChart data={d.sales.series.map((s) => ({ label: s.date, value: s.sales, detail: `${s.date}: ${money(s.sales)} · ${s.orders} đơn` }))} />
            </Section>
          )}

          <div className="grid gap-5 lg:grid-cols-2">
            {d.orders && (
              <Section title="Đơn hàng mới nhất" link={{ to: '/quan-tri/don-hang', label: 'Tất cả đơn hàng' }}>
                {d.orders.recent.length === 0 ? <p className="text-sm text-slate-500">Chưa có đơn hàng nào.</p> : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm"><thead><tr><th className="th">Đơn</th><th className="th">Người nhận</th><th className="th text-right">Tổng tiền</th><th className="th">Trạng thái</th></tr></thead>
                      <tbody>{d.orders.recent.map((o) => (
                        <tr key={o.id} className="border-t border-slate-100">
                          <td className="td"><p className="font-medium">#{o.id}</p><p className="text-xs text-slate-400">{dateTime(o.created_at)}</p></td>
                          <td className="td">{o.recipient}</td><td className="td text-right">{money(o.total_amount)}</td>
                          <td className="td"><StatusBadge status={o.status as OrderStatus} /></td>
                        </tr>))}</tbody></table>
                  </div>)}
              </Section>
            )}
            {d.inventory && (
              <Section title="Tồn kho thấp nhất" link={{ to: '/quan-tri/kho', label: 'Quản lý kho' }}>
                {d.inventory.lowest.length === 0 ? <p className="text-sm text-slate-500">Không có sản phẩm nào dưới ngưỡng tồn.</p> : (
                  <ul className="divide-y divide-slate-100 text-sm">{d.inventory.lowest.map((p) => (
                    <li key={p.product_id} className="flex items-center justify-between gap-3 py-2.5">
                      <div className="min-w-0"><p className="truncate font-medium">{p.name}</p><p className="text-xs text-slate-400">{p.sku} · ngưỡng {p.min_threshold}</p></div>
                      <b className={p.quantity === 0 ? 'text-rose-600' : 'text-amber-600'}>{p.quantity === 0 ? 'Hết hàng' : `Còn ${p.quantity}`}</b>
                    </li>))}</ul>)}
              </Section>
            )}
          </div>

          {(d.accounts || d.promotions) && (
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              {d.accounts && <>
                <Stat label="Khách hàng" value={d.accounts.customers} hint={`+${d.accounts.new_customers} trong 7 ngày`} />
                <Stat label="Tài khoản nhân viên" value={d.accounts.staff} />
                <Stat label="Tài khoản bị khóa" value={d.accounts.locked} tone={d.accounts.locked ? 'warn' : undefined} />
              </>}
              {d.promotions && <Stat label="Khuyến mại đang chạy" value={d.promotions.active} />}
            </div>
          )}

          <Section title="Truy cập nhanh">
            <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {shortcuts.map((n) => (
                <li key={n.to}><Link to={n.to} className="flex items-center gap-3 rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-medium text-slate-700 hover:border-brand-400 hover:bg-brand-50">
                  <span className="text-brand-600" aria-hidden><Icon name={n.icon} size={18} /></span>{n.label}</Link></li>
              ))}
            </ul>
          </Section>
        </div>
      )}
    </div>
  )
}
