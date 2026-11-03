import { Navigate, Route, Routes } from 'react-router-dom'
import { RequireAuth } from './components/Guards'
import Layout from './components/Layout'
import Account from './pages/Account'
import { Login, Register } from './pages/Auth'
import Cart from './pages/Cart'
import Checkout from './pages/Checkout'
import Home from './pages/Home'
import ImageSearch from './pages/ImageSearch'
import OrderDetail from './pages/OrderDetail'
import Orders from './pages/Orders'
import Payment from './pages/Payment'
import ProductDetail from './pages/ProductDetail'
import Products from './pages/Products'
import StaffAccounts from './pages/staff/Accounts'
import StaffCatalogue from './pages/staff/Catalogue'
import StaffInventory from './pages/staff/Inventory'
import StaffLayout, { StaffHome } from './pages/staff/StaffLayout'
import StaffOrders from './pages/staff/Orders'
import StaffPromotions from './pages/staff/Promotions'
import { AiReportPage, BusinessReportPage } from './pages/staff/Reports'
import SupportDesk from './pages/staff/SupportDesk'
import Support from './pages/Support'
import Icon from './components/Icon'

const NotFound = () => (
  <div className="py-20 text-center"><p className="flex justify-center text-slate-400" aria-hidden><Icon name="compass" size={56} strokeWidth={1.5} /></p><h1 className="mt-3 text-xl font-bold">Không tìm thấy trang</h1><a href="/" className="mt-3 inline-block text-brand-700 underline">Về trang chủ</a></div>
)

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="san-pham" element={<Products />} />
        <Route path="san-pham/:id" element={<ProductDetail />} />
        <Route path="tim-kiem-anh" element={<ImageSearch />} />
        <Route path="dang-nhap" element={<Login />} />
        <Route path="dang-ky" element={<Register />} />
        <Route element={<RequireAuth roles={['CUSTOMER']} />}>
          <Route path="gio-hang" element={<Cart />} />
          <Route path="thanh-toan" element={<Checkout />} />
          <Route path="don-hang" element={<Orders />} />
          <Route path="don-hang/:id" element={<OrderDetail />} />
          <Route path="don-hang/:id/thanh-toan" element={<Payment />} />
          <Route path="tai-khoan" element={<Account />} />
          <Route path="ho-tro" element={<Support />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Route>

      <Route path="quan-tri" element={<RequireAuth roles={['ADMIN', 'SERVICE', 'SALES', 'WAREHOUSE', 'MARKETING', 'MANAGER']} />}>
        <Route element={<StaffLayout />}>
          <Route index element={<StaffHome />} />
          <Route element={<RequireAuth roles={['MANAGER', 'ADMIN']} />}><Route path="bao-cao" element={<BusinessReportPage />} /></Route>
          <Route element={<RequireAuth roles={['MANAGER', 'MARKETING', 'ADMIN']} />}><Route path="ai" element={<AiReportPage />} /></Route>
          <Route element={<RequireAuth roles={['SERVICE', 'WAREHOUSE', 'SALES', 'ADMIN', 'MANAGER']} />}><Route path="don-hang" element={<StaffOrders />} /></Route>
          <Route element={<RequireAuth roles={['WAREHOUSE', 'ADMIN', 'MANAGER']} />}><Route path="kho" element={<StaffInventory />} /></Route>
          <Route element={<RequireAuth roles={['ADMIN']} />}><Route path="san-pham" element={<StaffCatalogue />} /><Route path="tai-khoan" element={<StaffAccounts />} /></Route>
          <Route element={<RequireAuth roles={['ADMIN', 'MARKETING', 'MANAGER']} />}><Route path="khuyen-mai" element={<StaffPromotions />} /></Route>
          <Route element={<RequireAuth roles={['SALES', 'ADMIN']} />}><Route path="ho-tro" element={<SupportDesk />} /></Route>
          <Route path="*" element={<Navigate to="/quan-tri" replace />} />
        </Route>
      </Route>
    </Routes>
  )
}
