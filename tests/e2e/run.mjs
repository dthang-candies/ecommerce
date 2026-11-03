// Browser end-to-end journey (customer -> staff -> reports). Needs the API running with the built SPA and the demo seed.
// Setup (outside the project):  mkdir e2e && cd e2e && npm i playwright && npx playwright install chromium
// Run:  node path/to/tests/e2e/run.mjs <screenshot-dir>      NOTE: it creates a real customer and an order in the dev DB.
import { chromium } from 'playwright'
const BASE = 'http://localhost:8000', OUT = process.argv[2]
const email = `e2e${Date.now()}@example.com`
const errors = []
const browser = await chromium.launch()
const mk = async (viewport = { width: 1280, height: 900 }) => {
  const ctx = await browser.newContext({ viewport, locale: 'vi-VN' })
  const page = await ctx.newPage()
  page.on('console', (m) => m.type() === 'error' && errors.push(`console: ${m.text()}`))
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`))
  page.on('response', (r) => r.status() >= 500 && errors.push(`HTTP ${r.status()} ${r.url()}`))
  return page
}
const step = (n) => console.log('✔', n)
const shot = (p, n) => p.screenshot({ path: `${OUT}/${n}.png`, fullPage: false })

// ---------- customer journey
const p = await mk()
await p.goto(BASE); await p.waitForSelector('text=Danh mục nổi bật'); await p.waitForSelector('text=Bán chạy & nổi bật'); await shot(p, '01-home'); step('home renders with recommendations')
await p.fill('input[type=search]', 'ao khoac'); await p.press('input[type=search]', 'Enter')
await p.waitForSelector('text=Áo khoác gió unisex'); step('accent-insensitive search finds "Áo khoác"'); await shot(p, '02-search')
await p.fill('input[type=search]', 'Laptp'); await p.press('input[type=search]', 'Enter')
await p.waitForSelector('text=Hiển thị kết quả cho'); step('typo auto-corrected and announced')
await p.goto(`${BASE}/dang-ky`)
await p.fill('input[autocomplete=email]', email)
const [last, mid, first] = await p.locator('form input[maxlength="50"]').all()
await last.fill('Nguyễn'); await first.fill('Kiểm'); 
const pw = await p.locator('input[type=password]').all(); await pw[0].fill('Passw0rd1'); await pw[1].fill('Passw0rd1')
await p.click('button:has-text("Đăng ký")'); await p.waitForURL(BASE + '/'); step('registered + logged in')
await p.goto(`${BASE}/san-pham?q=khoac`); await p.click(`article:has-text("Áo khoác gió unisex") a >> nth=0`); await p.waitForSelector('h1:has-text("Áo khoác gió unisex")'); await shot(p, '03-detail')
await p.click('button:has-text("Thêm vào giỏ hàng")'); await p.waitForSelector('text=Đã thêm vào giỏ hàng'); step('add to cart')
await p.goto(`${BASE}/gio-hang`); await p.waitForSelector('text=Tiến hành thanh toán'); await shot(p, '04-cart')
await p.click('text=Tiến hành thanh toán'); await p.waitForSelector('text=Thêm địa chỉ giao hàng'); 
await p.click('button:has-text("Thêm địa chỉ giao hàng")')
await p.fill('[role=dialog] input >> nth=0', 'Nguyễn Kiểm'); await p.fill('[role=dialog] input[inputmode=tel]', '0911222333')
const dlg = await p.locator('[role=dialog] input[type=text], [role=dialog] input:not([type])').all()
await dlg[2].fill('12 Tràng Tiền'); await dlg[4].fill('Hà Nội')
await p.click('[role=dialog] button:has-text("Lưu địa chỉ")'); await p.waitForSelector('text=12 Tràng Tiền'); step('address added in checkout')
await p.fill('input[aria-label="Mã giảm giá"]', 'WELCOME10'); await p.click('button:has-text("Áp dụng")'); await p.waitForSelector('text=Đã áp dụng mã WELCOME10'); await shot(p, '05-checkout'); step('promo applied')
await p.click('label:has-text("Thanh toán trực tuyến")'); await p.click('button:has-text("Đặt hàng & thanh toán")')
await p.waitForSelector('text=Thanh toán đơn hàng'); const orderUrl = p.url(); const oid = orderUrl.match(/don-hang\/(\d+)/)[1]; step(`online order #${oid} created, payment page`)
await p.click('label:has-text("Thẻ ngân hàng")'); await p.fill('input[autocomplete=cc-number]', '4242424242420000'); await p.click('button:has-text("Thanh toán")')
await p.waitForSelector('text=bị từ chối'); step('declined card shows failure'); await shot(p, '06-pay-fail')
await p.fill('input[autocomplete=cc-number]', '4242424242424242'); await p.click('button:has-text("Thanh toán")')
await p.waitForURL(`**/don-hang/${oid}`); await p.waitForSelector('text=Đã thanh toán'); step('retry succeeds -> order paid'); await shot(p, '07-order-paid')

// ---------- staff fulfils the order
const staff = async (mail, path) => { const s = await mk(); await s.goto(`${BASE}/dang-nhap`); await s.fill('input[type=email]', mail); await s.fill('input[type=password]', 'Abc@12345'); await s.click('button:has-text("Đăng nhập")'); await s.waitForURL('**/quan-tri/**'); if (path) await s.goto(BASE + path); return s }
const svc = await staff('service@abc.vn', '/quan-tri/don-hang'); await svc.fill('input[aria-label="Tìm đơn hàng"]', oid); await svc.press('input[aria-label="Tìm đơn hàng"]', 'Enter')
await svc.waitForSelector(`tr:has-text("#${oid}")`); await svc.click(`tr:has-text("#${oid}") button:has-text("Xác nhận")`); await svc.click('[role=dialog] button:has-text("Xác nhận")'); await svc.waitForSelector('text=Đã cập nhật đơn'); step('service staff confirmed order'); await shot(svc, '08-staff-orders')
const wh = await staff('warehouse@abc.vn', '/quan-tri/don-hang'); await wh.fill('input[aria-label="Tìm đơn hàng"]', oid); await wh.press('input[aria-label="Tìm đơn hàng"]', 'Enter')
await wh.waitForSelector(`tr:has-text("#${oid}")`); await wh.click(`tr:has-text("#${oid}") button:has-text("Đã đóng gói")`); await wh.click('[role=dialog] button:has-text("Xác nhận")'); await wh.waitForSelector('text=Đã cập nhật đơn'); step('warehouse packed order')
await wh.selectOption('select[aria-label="Trạng thái"]', 'PACKED'); await wh.waitForSelector(`tr:has-text("#${oid}")`); await wh.click(`tr:has-text("#${oid}") button:has-text("Bàn giao vận chuyển")`); await wh.click('[role=dialog] button:has-text("Xác nhận")'); await wh.waitForSelector('text=Đã cập nhật đơn')
await wh.selectOption('select[aria-label="Trạng thái"]', 'SHIPPING'); await wh.waitForSelector(`tr:has-text("#${oid}")`); await wh.click(`tr:has-text("#${oid}") button:has-text("Đã giao")`); await wh.click('[role=dialog] button:has-text("Xác nhận")'); await wh.waitForSelector('text=Đã cập nhật đơn'); step('carrier simulated: in transit -> delivered')

// ---------- customer reviews
await p.goto(`${BASE}/don-hang/${oid}`); await p.waitForSelector('text=Viết đánh giá'); await shot(p, '09-order-delivered')
await p.click('text=Viết đánh giá'); await p.click('[role=radio][aria-label="4 sao"]'); await p.fill('[role=dialog] textarea', 'Áo đẹp, giao nhanh'); await p.click('button:has-text("Gửi đánh giá")'); await p.waitForSelector('text=Đã đánh giá'); step('review submitted')
await p.goto(`${BASE}/ho-tro?order=${oid}`); await p.fill('textarea', 'Tôi muốn đổi size áo này'); await p.click('button:has-text("Gửi yêu cầu")'); await p.waitForSelector('text=Yêu cầu #'); step('support request created')

// ---------- sales replies, manager/admin pages
const sales = await staff('sales@abc.vn', '/quan-tri/ho-tro'); await sales.click('li button:has-text("Xử lý") >> nth=0'); await sales.fill('[role=dialog] textarea', 'Shop sẽ đổi size cho bạn nhé'); await sales.click('button:has-text("Gửi & giải quyết")'); await sales.waitForSelector('text=Đã phản hồi'); step('sales replied to support request')
const mgr = await staff('manager@abc.vn', '/quan-tri/bao-cao'); await mgr.waitForSelector('text=Doanh số theo ngày'); await shot(mgr, '10-report'); step('manager report renders')
await mgr.goto(`${BASE}/quan-tri/ai`); await mgr.waitForSelector('text=Conversion'); await shot(mgr, '11-ai'); step('AI report renders')
const adm = await staff('admin@abc.vn', '/quan-tri/san-pham'); await adm.waitForSelector('text=Thêm sản phẩm'); await shot(adm, '12-catalogue')
for (const [path, text] of [['/quan-tri/kho', 'Tồn kho'], ['/quan-tri/khuyen-mai', 'Khuyến mại'], ['/quan-tri/tai-khoan', 'Tài khoản & vai trò']]) { await adm.goto(BASE + path); await adm.waitForSelector(`h1:has-text("${text}"), h1:has-text("Kho")`) }
step('admin inventory / promotions / accounts pages render')
await adm.goto(`${BASE}/quan-tri/kho`); await adm.click('button[role=tab]:has-text("Yêu cầu nhập hàng")'); await adm.waitForSelector('text=Gửi yêu cầu'); await shot(adm, '13-restock')

// ---------- RBAC in UI + mobile
const cust = await mk({ width: 390, height: 844 }); await cust.goto(`${BASE}/dang-nhap`); await cust.fill('input[type=email]', 'an@gmail.com'); await cust.fill('input[type=password]', 'Abc@12345'); await cust.click('button:has-text("Đăng nhập")'); await cust.waitForURL(BASE + '/')
await cust.goto(`${BASE}/quan-tri/bao-cao`); await cust.waitForSelector('text=Bạn không có quyền truy cập'); step('customer blocked from admin area')
await cust.goto(BASE); await cust.waitForSelector('text=Danh mục nổi bật'); await shot(cust, '14-mobile-home')
const overflow = await cust.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1); if (overflow) errors.push('mobile: horizontal overflow on home')
await cust.goto(`${BASE}/san-pham`); await cust.waitForSelector('article'); if (await cust.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)) errors.push('mobile: horizontal overflow on products')
step('mobile layout: no horizontal scroll')
await browser.close()
console.log(errors.length ? 'ERRORS:\n' + [...new Set(errors)].join('\n') : 'no console/page/5xx errors')
process.exit(errors.length ? 1 : 0)
