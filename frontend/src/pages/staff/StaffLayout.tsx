import { useState } from 'react'
import { Link, NavLink, Navigate, Outlet, useNavigate } from 'react-router-dom'
import type { Role } from '../../api/types'
import { useAuth } from '../../context/AuthContext'
import { ROLE_LABEL } from '../../lib/format'
import Icon, { type IconName } from '../../components/Icon'

interface Item { to: string; label: string; icon: IconName; roles: Role[] }
export const STAFF_NAV: Item[] = [
  { to: '/quan-tri/bao-cao', label: 'Báo cáo kinh doanh', icon: 'chart', roles: ['MANAGER', 'ADMIN'] },
  { to: '/quan-tri/ai', label: 'Hiệu quả gợi ý AI', icon: 'sparkles', roles: ['MANAGER', 'MARKETING', 'ADMIN'] },
  { to: '/quan-tri/don-hang', label: 'Đơn hàng', icon: 'receipt', roles: ['SERVICE', 'WAREHOUSE', 'SALES', 'ADMIN', 'MANAGER'] },
  { to: '/quan-tri/kho', label: 'Kho & nhập hàng', icon: 'package', roles: ['WAREHOUSE', 'ADMIN', 'MANAGER'] },
  { to: '/quan-tri/san-pham', label: 'Sản phẩm & danh mục', icon: 'bag', roles: ['ADMIN'] },
  { to: '/quan-tri/khuyen-mai', label: 'Khuyến mại', icon: 'tag', roles: ['ADMIN', 'MARKETING', 'MANAGER'] },
  { to: '/quan-tri/ho-tro', label: 'Hỗ trợ khách hàng', icon: 'message', roles: ['SALES', 'ADMIN'] },
  { to: '/quan-tri/tai-khoan', label: 'Tài khoản & vai trò', icon: 'users', roles: ['ADMIN'] },
]

export function StaffHome() {
  const { user } = useAuth()
  const first = STAFF_NAV.find((n) => user && n.roles.includes(user.role))
  return <Navigate to={first?.to ?? '/'} replace />
}

export default function StaffLayout() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const [open, setOpen] = useState(false)
  if (!user) return null
  const items = STAFF_NAV.filter((n) => n.roles.includes(user.role))
  const links = (
    <nav className="space-y-1" aria-label="Quản trị">
      {items.map((n) => (
        <NavLink key={n.to} to={n.to} onClick={() => setOpen(false)}
          className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${isActive ? 'bg-brand-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>
          <Icon name={n.icon} size={18} />{n.label}
        </NavLink>
      ))}
    </nav>
  )
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[250px_1fr]">
      <aside className="hidden bg-slate-900 p-4 lg:block">
        <Link to="/quan-tri" className="mb-6 flex items-center gap-2 text-lg font-extrabold text-white"><span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600" aria-hidden><Icon name="cart" size={18} /></span>UniCart Admin</Link>
        {links}
      </aside>
      <div className="min-w-0">
        <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3">
          <button className="btn-ghost lg:hidden" onClick={() => setOpen(true)} aria-label="Mở menu"><Icon name="menu" size={22} /></button>
          <p className="hidden text-sm text-slate-500 sm:block">Vai trò: <b className="text-slate-800">{ROLE_LABEL[user.role]}</b></p>
          <div className="ml-auto flex items-center gap-2 text-sm">
            <span className="hidden text-slate-500 md:inline">{user.email}</span>
            <Link to="/" className="btn-secondary">Xem cửa hàng</Link>
            <button className="btn-ghost text-rose-600" onClick={() => { logout(); nav('/dang-nhap') }}>Đăng xuất</button>
          </div>
        </header>
        <main className="p-4 sm:p-6"><Outlet /></main>
      </div>
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden" onClick={() => setOpen(false)}>
          <div className="absolute inset-0 bg-slate-900/50" />
          <aside className="relative h-full w-64 bg-slate-900 p-4" onClick={(e) => e.stopPropagation()}>{links}</aside>
        </div>
      )}
    </div>
  )
}
