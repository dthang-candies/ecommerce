import { Navigate, Outlet, useLocation } from 'react-router-dom'
import type { Role } from '../api/types'
import { useAuth } from '../context/AuthContext'
import { Spinner } from './ui'
import Icon from './Icon'

/** Requires a signed-in user, optionally with one of `roles` (the server enforces the same rules: NFR-06). */
export function RequireAuth({ roles }: { roles?: Role[] }) {
  const { user, ready } = useAuth()
  const loc = useLocation()
  if (!ready) return <Spinner />
  if (!user) return <Navigate to="/dang-nhap" replace state={{ from: loc.pathname + loc.search }} />
  if (roles && !roles.includes(user.role)) {
    return (
      <div className="mx-auto max-w-md py-20 text-center">
        <p className="flex justify-center text-slate-400" aria-hidden><Icon name="lock" size={56} strokeWidth={1.5} /></p>
        <h1 className="mt-3 text-xl font-bold">Bạn không có quyền truy cập</h1>
        <p className="mt-1 text-sm text-slate-500">Chức năng này chỉ dành cho vai trò khác.</p>
      </div>
    )
  }
  return <Outlet />
}
