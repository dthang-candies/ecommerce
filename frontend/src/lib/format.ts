import type { OrderStatus } from '../api/types'

const vnd = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 })
export const money = (n: number) => vnd.format(n)
export const compact = (n: number) => new Intl.NumberFormat('vi-VN', { notation: 'compact', maximumFractionDigits: 1 }).format(n)

// Timestamps from the API are local (UTC+7) wall-clock times without a zone (NFR-18).
const dt = new Intl.DateTimeFormat('vi-VN', { dateStyle: 'short', timeStyle: 'short' })
const d = new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium' })
export const dateTime = (iso: string | null | undefined) => (iso ? dt.format(new Date(iso)) : '—')
export const dateOnly = (iso: string | null | undefined) => (iso ? d.format(new Date(iso)) : '—')
export const toDateInput = (date: Date) => {
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${m}-${day}`
}

export const STATUS_LABEL: Record<OrderStatus, string> = {
  PENDING_PAYMENT: 'Chờ thanh toán', PENDING: 'Chờ xác nhận', CONFIRMED: 'Đã xác nhận', PACKED: 'Đã đóng gói',
  SHIPPING: 'Đang giao', DELIVERED: 'Đã giao', CANCELLED: 'Đã hủy',
}
export const STATUS_TONE: Record<OrderStatus, string> = {
  PENDING_PAYMENT: 'bg-amber-100 text-amber-800', PENDING: 'bg-sky-100 text-sky-800', CONFIRMED: 'bg-indigo-100 text-indigo-800',
  PACKED: 'bg-violet-100 text-violet-800', SHIPPING: 'bg-blue-100 text-blue-800', DELIVERED: 'bg-emerald-100 text-emerald-800',
  CANCELLED: 'bg-rose-100 text-rose-800',
}
export const ROLE_LABEL: Record<string, string> = {
  CUSTOMER: 'Khách hàng', ADMIN: 'Quản trị hệ thống', SERVICE: 'Nhân viên xử lý đơn', SALES: 'Nhân viên bán hàng / CSKH',
  WAREHOUSE: 'Nhân viên kho', MARKETING: 'Nhân viên marketing', MANAGER: 'Ban quản lý',
}
export const SUPPORT_LABEL = { OPEN: 'Mới', IN_PROGRESS: 'Đang xử lý', RESOLVED: 'Đã giải quyết' } as const
export const RESTOCK_LABEL = { REQUESTED: 'Chờ nhà cung cấp', CONFIRMED: 'Đã xác nhận', RECEIVED: 'Đã nhập kho', REJECTED: 'Bị từ chối' } as const
export const PLACEMENT_LABEL: Record<string, string> = { home: 'Trang chủ', product: 'Chi tiết sản phẩm', cart: 'Giỏ hàng', other: 'Khác', all: 'Tổng' }
export const COLOR_LABEL: Record<string, string> = {
  black: 'Đen', white: 'Trắng', red: 'Đỏ', blue: 'Xanh dương', green: 'Xanh lá', yellow: 'Vàng', pink: 'Hồng', grey: 'Xám',
  brown: 'Nâu', cream: 'Kem', purple: 'Tím', orange: 'Cam', navy: 'Xanh navy',
}
