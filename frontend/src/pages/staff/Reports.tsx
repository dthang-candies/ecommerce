import { useState } from 'react'
import { api } from '../../api/client'
import type { BusinessReport, OrderStatus, RecReport } from '../../api/types'
import { ErrorBox, PageTitle, Spinner, Stat } from '../../components/ui'
import { PLACEMENT_LABEL, STATUS_LABEL, compact, money, toDateInput } from '../../lib/format'
import { useFetch } from '../../lib/useFetch'

function useRange() {
  const [start, setStart] = useState(() => toDateInput(new Date(Date.now() - 29 * 864e5)))
  const [end, setEnd] = useState(() => toDateInput(new Date()))
  const bad = end < start
  const ui = (
    <div className="flex flex-wrap items-end gap-2 text-sm">
      <label>Từ ngày<input className="input mt-1" type="date" value={start} max={end} onChange={(e) => setStart(e.target.value)} /></label>
      <label>Đến ngày<input className="input mt-1" type="date" value={end} min={start} max={toDateInput(new Date())} onChange={(e) => setEnd(e.target.value)} /></label>
    </div>
  )
  return { start, end, bad, ui }
}

function BarChart({ data }: { data: { label: string; value: number; detail: string }[] }) {
  const max = Math.max(...data.map((d) => d.value), 1)
  const step = Math.ceil(data.length / 8)
  return (
    <figure>
      <div className="flex h-48 items-end gap-0.5 border-b border-l border-slate-200 pl-1" role="img" aria-label="Biểu đồ doanh số theo ngày">
        {data.map((d) => (
          <div key={d.label} className="group relative flex h-full min-w-0 flex-1 items-end" title={d.detail}>
            <div className="w-full rounded-t bg-brand-500 transition group-hover:bg-brand-700" style={{ height: `${(d.value / max) * 100}%`, minHeight: d.value ? 2 : 0 }} />
          </div>
        ))}
      </div>
      <div className="flex gap-0.5 pl-1 pt-1 text-[10px] text-slate-400">{data.map((d, i) => <span key={d.label} className="flex-1 truncate">{i % step === 0 ? d.label.slice(5) : ''}</span>)}</div>
      <figcaption className="mt-1 text-right text-xs text-slate-400">Cao nhất: {money(max)}</figcaption>
    </figure>
  )
}

export function BusinessReportPage() {
  const r = useRange()
  const res = useFetch(() => (r.bad ? Promise.resolve(null) : api.get<BusinessReport>('/reports/business', { start: r.start, end: r.end })), [r.start, r.end])
  const d = res.data
  return (
    <div>
      <PageTitle title="Báo cáo kinh doanh" subtitle="Doanh thu, đơn hàng, tồn kho theo kỳ (FR-17)" actions={r.ui} />
      {r.bad && <ErrorBox message="Ngày kết thúc phải sau ngày bắt đầu" />}
      {res.loading ? <Spinner /> : res.error ? <ErrorBox message={res.error} onRetry={res.reload} /> : d && (<>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Stat label="Doanh số ghi nhận" value={money(d.kpis.committed_sales)} hint={`${d.kpis.committed_orders} đơn hợp lệ`} />
          <Stat label="Doanh thu đã giao" value={money(d.kpis.delivered_revenue)} tone="good" />
          <Stat label="Giá trị đơn trung bình" value={money(d.kpis.average_order_value)} />
          <Stat label="Tỷ lệ hủy đơn" value={`${d.kpis.cancel_rate}%`} hint={`${d.by_status.CANCELLED} / ${d.kpis.total_orders} đơn`} tone={d.kpis.cancel_rate > 15 ? 'warn' : undefined} />
          <Stat label="Sản phẩm đã bán" value={d.kpis.units_sold} />
          <Stat label="Vòng quay tồn kho" value={d.kpis.stock_turnover} hint="Đã bán / tồn hiện tại" />
          <Stat label="Giá trị tồn kho" value={money(d.inventory.value)} hint={`${d.inventory.units} sản phẩm · ${d.inventory.skus} SKU`} />
          <Stat label="Sắp hết / hết hàng" value={`${d.inventory.low_stock} / ${d.inventory.out_of_stock}`} tone={d.inventory.low_stock ? 'warn' : undefined} />
        </div>
        <section className="card mt-5 p-5"><h2 className="mb-3 font-bold">Doanh số theo ngày</h2>
          <BarChart data={d.series.map((s) => ({ label: s.date, value: s.sales, detail: `${s.date}: ${money(s.sales)} · ${s.orders} đơn` }))} /></section>
        <div className="mt-5 grid gap-5 lg:grid-cols-2">
          <section className="card p-5"><h2 className="mb-3 font-bold">Đơn hàng theo trạng thái</h2>
            <ul className="space-y-2 text-sm">{(Object.keys(d.by_status) as OrderStatus[]).map((s) => {
              const total = Math.max(d.kpis.total_orders, 1)
              return <li key={s}><div className="flex justify-between"><span>{STATUS_LABEL[s]}</span><b>{d.by_status[s]}</b></div><div className="mt-1 h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-brand-500" style={{ width: `${(d.by_status[s] / total) * 100}%` }} /></div></li>
            })}</ul></section>
          <section className="card overflow-x-auto p-5"><h2 className="mb-3 font-bold">Sản phẩm bán chạy</h2>
            {d.top_products.length === 0 ? <p className="text-sm text-slate-500">Chưa có dữ liệu trong kỳ.</p> : (
              <table className="w-full text-sm"><thead><tr><th className="th">Sản phẩm</th><th className="th text-right">SL</th><th className="th text-right">Doanh thu</th></tr></thead>
                <tbody>{d.top_products.map((p) => <tr key={p.product_id} className="border-t border-slate-100"><td className="td"><p className="font-medium">{p.name}</p><p className="text-xs text-slate-400">{p.sku}</p></td><td className="td text-right">{p.quantity}</td><td className="td text-right">{compact(p.revenue)}</td></tr>)}</tbody></table>)}</section>
        </div>
        <p className="mt-4 text-xs text-slate-400">Doanh số ghi nhận = đơn đã thanh toán trực tuyến hoặc COD còn hiệu lực (từ Chờ xác nhận đến Đã giao), không gồm đơn hủy / chờ thanh toán.</p>
      </>)}
    </div>
  )
}

export function AiReportPage() {
  const r = useRange()
  const res = useFetch(() => (r.bad ? Promise.resolve(null) : api.get<RecReport>('/reports/recommendations', { start: r.start, end: r.end })), [r.start, r.end])
  const d = res.data
  return (
    <div>
      <PageTitle title="Hiệu quả gợi ý AI" subtitle="CTR, Add-to-Cart và Conversion theo vị trí hiển thị (FR-18)" actions={r.ui} />
      {res.loading ? <Spinner /> : res.error ? <ErrorBox message={res.error} onRetry={res.reload} /> : d && (<>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Stat label="Lượt hiển thị" value={d.total.impressions} /><Stat label="CTR" value={`${d.total.ctr}%`} hint={`${d.total.clicks} lượt nhấp`} tone="good" />
          <Stat label="Add-to-Cart" value={`${d.total.add_to_cart_rate}%`} hint={`${d.total.add_to_cart} lượt thêm giỏ`} /><Stat label="Conversion" value={`${d.total.conversion_rate}%`} hint={`${d.total.purchases} dòng hàng được mua`} />
        </div>
        <section className="card mt-5 overflow-x-auto p-5">
          <table className="w-full text-sm"><thead><tr><th className="th">Vị trí</th><th className="th text-right">Hiển thị</th><th className="th text-right">Nhấp</th><th className="th text-right">CTR</th><th className="th text-right">Thêm giỏ</th><th className="th text-right">Add-to-Cart</th><th className="th text-right">Mua</th><th className="th text-right">Conversion</th></tr></thead>
            <tbody>{d.placements.length === 0 ? <tr><td className="td text-slate-500" colSpan={8}>Chưa có dữ liệu trong kỳ.</td></tr> : d.placements.map((p) => (
              <tr key={p.placement} className="border-t border-slate-100"><td className="td font-medium">{PLACEMENT_LABEL[p.placement] ?? p.placement}</td><td className="td text-right">{p.impressions}</td><td className="td text-right">{p.clicks}</td><td className="td text-right font-semibold">{p.ctr}%</td><td className="td text-right">{p.add_to_cart}</td><td className="td text-right font-semibold">{p.add_to_cart_rate}%</td><td className="td text-right">{p.purchases}</td><td className="td text-right font-semibold">{p.conversion_rate}%</td></tr>))}</tbody></table>
          <p className="mt-3 text-xs text-slate-400">CTR = nhấp / hiển thị; Add-to-Cart = thêm giỏ từ gợi ý / nhấp; Conversion = dòng hàng mua từ gợi ý / lượt hiển thị (xấp xỉ theo công thức 3.3–3.5; chưa có A/B test).</p>
        </section>
      </>)}
    </div>
  )
}
