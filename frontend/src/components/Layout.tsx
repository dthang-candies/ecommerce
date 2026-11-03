import { useEffect, useState, type FormEvent } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Category } from '../api/types'
import { isStaff, useAuth } from '../context/AuthContext'
import { useCart } from '../context/CartContext'
import { usePrefs } from '../context/PrefsContext'
import { useAiStatus } from '../lib/useAiStatus'
import { useFetch } from '../lib/useFetch'
import ChatWidget from './ChatWidget'
import ImageSearchModal from './ImageSearchModal'
import VoiceSearch from './VoiceSearch'
import { ROLE_LABEL } from '../lib/format'
import Icon from './Icon'

export default function Layout() {
  const { user, logout } = useAuth()
  const { count } = useCart()
  const { track } = usePrefs()
  const nav = useNavigate()
  const loc = useLocation()
  const [params] = useSearchParams()
  const [q, setQ] = useState(params.get('q') ?? '')
  const [menu, setMenu] = useState(false)
  const [tool, setTool] = useState<'voice' | 'image' | null>(null)
  const ai = useAiStatus()
  const cats = useFetch(() => api.get<Category[]>('/categories'), [])

  useEffect(() => { setMenu(false); window.scrollTo({ top: 0 }) }, [loc.pathname])
  useEffect(() => { setQ(params.get('q') ?? '') }, [params])

  const search = (e: FormEvent) => {
    e.preventDefault()
    const term = q.trim()
    if (term) track('SEARCH', { keyword: term })
    nav(term ? `/san-pham?q=${encodeURIComponent(term)}` : '/san-pham')
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-3">
          <Link to="/" className="flex shrink-0 items-center gap-2 text-xl font-extrabold tracking-tight text-brand-700">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 text-white" aria-hidden><Icon name="cart" size={20} /></span>
            <span className="hidden sm:inline">UniCart</span>
          </Link>
          <form onSubmit={search} role="search" className="flex min-w-0 flex-1">
            <input className="input rounded-r-none" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Tìm sản phẩm, thương hiệu…" aria-label="Tìm kiếm sản phẩm" maxLength={100} />
            {ai?.enabled && (<>
              <button type="button" className="border-y border-slate-300 bg-white px-3 text-slate-600 hover:bg-slate-50 hover:text-brand-700" onClick={() => setTool('voice')} aria-label="Tìm bằng giọng nói" title="Tìm bằng giọng nói"><Icon name="mic" size={20} /></button>
              <button type="button" className="border-y border-l border-slate-300 bg-white px-3 text-slate-600 hover:bg-slate-50 hover:text-brand-700" onClick={() => setTool('image')} aria-label="Tìm bằng hình ảnh" title="Tìm bằng hình ảnh"><Icon name="camera" size={20} /></button>
            </>)}
            <button className="btn-primary rounded-l-none" aria-label="Tìm kiếm">Tìm</button>
          </form>
          <nav className="flex shrink-0 items-center gap-1 text-sm" aria-label="Tài khoản">
            {user?.role === 'CUSTOMER' && (
              <Link to="/gio-hang" className="btn-ghost relative" aria-label={`Giỏ hàng, ${count} sản phẩm`}>
                <Icon name="cart" size={20} /><span className="hidden md:inline">Giỏ hàng</span>
                {count > 0 && <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-rose-600 px-1 text-xs font-bold text-white">{count}</span>}
              </Link>
            )}
            {!user && (<><Link to="/dang-nhap" className="btn-ghost">Đăng nhập</Link><Link to="/dang-ky" className="btn-primary hidden sm:inline-flex">Đăng ký</Link></>)}
            {user && (
              <div className="relative">
                <button className="btn-ghost max-w-40" onClick={() => setMenu((m) => !m)} aria-expanded={menu} aria-haspopup="menu">
                  <Icon name="user" size={20} /><span className="hidden truncate md:inline">{user.full_name ?? user.email}</span>
                </button>
                {menu && (
                  <div role="menu" className="absolute right-0 mt-2 w-60 overflow-hidden rounded-xl border border-slate-200 bg-white py-1 shadow-lg">
                    <div className="border-b border-slate-100 px-4 py-2"><p className="truncate text-sm font-semibold">{user.full_name ?? user.email}</p><p className="text-xs text-slate-500">{ROLE_LABEL[user.role]}</p></div>
                    {user.role === 'CUSTOMER' && (<>
                      <MenuLink to="/don-hang">Đơn hàng của tôi</MenuLink><MenuLink to="/tai-khoan">Tài khoản & địa chỉ</MenuLink><MenuLink to="/ho-tro">Hỗ trợ</MenuLink></>)}
                    {isStaff(user) && <MenuLink to="/quan-tri">Trang quản trị</MenuLink>}
                    <button role="menuitem" className="block w-full px-4 py-2 text-left text-sm text-rose-600 hover:bg-slate-50" onClick={() => { logout(); nav('/') }}>Đăng xuất</button>
                  </div>
                )}
              </div>
            )}
          </nav>
        </div>
        <div className="border-t border-slate-100">
          <nav className="mx-auto flex max-w-7xl gap-1 overflow-x-auto px-4 py-1.5 text-sm" aria-label="Danh mục">
            <NavLink to="/san-pham" end className={({ isActive }) => `whitespace-nowrap rounded-lg px-3 py-1.5 font-medium ${isActive && !params.get('category_id') ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-100'}`}>Tất cả</NavLink>
            {cats.data?.map((c) => (
              <Link key={c.id} to={`/san-pham?category_id=${c.id}`} className={`whitespace-nowrap rounded-lg px-3 py-1.5 font-medium ${params.get('category_id') === String(c.id) ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-100'}`}>{c.name}</Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6"><Outlet /></main>
      {tool === 'voice' && <VoiceSearch onClose={() => setTool(null)} />}
      {tool === 'image' && <ImageSearchModal onClose={() => setTool(null)} />}
      {!isStaff(user) && <ChatWidget />}
      <footer className="mt-8 border-t border-slate-200 bg-white">
        <div className="mx-auto grid max-w-7xl gap-6 px-4 py-8 text-sm text-slate-500 sm:grid-cols-3">
          <div><p className="font-bold text-slate-800">UniCart</p><p className="mt-1">Mua sắm thông minh, thanh toán an toàn, giao hàng minh bạch.</p></div>
          <div><p className="font-semibold text-slate-700">Chính sách</p><ul className="mt-1 space-y-1"><li>Miễn phí vận chuyển cho đơn từ 500.000đ</li><li>Thanh toán khi nhận hàng (COD) hoặc trực tuyến</li><li>Hủy đơn miễn phí trước khi đóng gói</li></ul></div>
          <div><p className="font-semibold text-slate-700">Hỗ trợ</p><ul className="mt-1 space-y-1"><li><Link to="/ho-tro" className="hover:text-brand-700">Gửi yêu cầu hỗ trợ</Link></li><li><Link to="/don-hang" className="hover:text-brand-700">Tra cứu đơn hàng</Link></li></ul></div>
        </div>
        <p className="border-t border-slate-100 py-3 text-center text-xs text-slate-400">© 2026 UniCart · Đồ án Phân tích & Thiết kế Hệ thống thông tin – PTIT</p>
      </footer>
    </div>
  )
}

function MenuLink({ to, children }: { to: string; children: string }) {
  return <Link role="menuitem" to={to} className="block px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">{children}</Link>
}
