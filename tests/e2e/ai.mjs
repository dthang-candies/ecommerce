// Browser E2E of AI search (text, image, voice) against the running app with a real GEMINI_API_KEY.
// Run:  node tests/e2e/ai.mjs <assets-dir> [screenshot-dir]   (Playwright installed outside the project, see tests/e2e/run.mjs)
import { chromium } from 'playwright'
const S = process.argv[2] // folder with backpack.jpg, shoe.jpg and voice_vi.wav (16 kHz mono WAV of: 'tôi muốn tìm giày chạy bộ màu đen dưới 1 triệu')
const OUT = process.argv[3] ?? S
const BASE = 'http://localhost:8000', errors = []
const browser = await chromium.launch({ args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', `--use-file-for-fake-audio-capture=${S}/voice_vi.wav%noloop`] })
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: 'vi-VN', permissions: ['microphone'] })
const p = await ctx.newPage()
p.on('console', (m) => m.type() === 'error' && errors.push('console: ' + m.text()))
p.on('pageerror', (e) => errors.push('pageerror: ' + e.message))
p.on('response', (r) => r.status() >= 500 && errors.push(`HTTP ${r.status()} ${r.url()}`))
const ok = (n) => console.log('✔', n)
const shot = (n) => p.screenshot({ path: `${OUT}/${n}.png` })

await p.goto(BASE); await p.waitForSelector('button[aria-label="Tìm bằng giọng nói"]'); ok('mic + camera buttons shown (AI enabled)')

// ---- text
await p.fill('input[type=search]', 'giày chạy bộ màu đen dưới 2 triệu'); await p.press('input[type=search]', 'Enter')
await p.waitForSelector('text=Tìm kiếm AI'); await p.waitForSelector('text=Giá đến'); await p.waitForSelector('text=Màu: Đen'); await p.waitForSelector('text=Giay chay bo'); ok('text search: AI badge, understood price + colour, finds running shoes'); await shot('20-text-search')
await p.fill('input[type=search]', 'laptp'); await p.press('input[type=search]', 'Enter')
await p.waitForSelector('text=Hiển thị kết quả cho'); await p.waitForSelector('text=Laptop Pro 14'); ok('typo "laptp" auto-corrected, original can be re-searched')
await p.fill('input[type=search]', 'máy tính để chơi game'); await p.press('input[type=search]', 'Enter'); await p.waitForSelector('article:has-text("Laptop Gaming Z15")'); ok('semantic search: "máy tính để chơi game" -> Laptop Gaming')
await p.fill('input[type=search]', 'đồ ăn vặt'); await p.press('input[type=search]', 'Enter'); await p.waitForSelector('text=Không tìm thấy sản phẩm phù hợp'); ok('unrelated query -> clear empty state')

// ---- image
await p.click('button[aria-label="Tìm bằng hình ảnh"]'); await p.waitForSelector('[role=dialog] >> text=Tìm kiếm bằng hình ảnh')
await p.setInputFiles('[role=dialog] input[aria-label="Chọn ảnh"]', `${S}/backpack.jpg`)
await p.waitForURL('**/tim-kiem-anh'); await p.waitForSelector('text=Nhận diện:', { timeout: 60000 }); await p.waitForSelector('article:has-text("Ba lô laptop chống nước")'); ok('image search: backpack photo -> recognised + "Ba lô laptop" found'); await shot('21-image-search')
await p.setInputFiles('input[aria-label="Chọn ảnh"] >> nth=0', `${S}/shoe.jpg`); await p.waitForSelector('article:has-text("Giay chay bo")', { timeout: 60000 }); ok('second image replaces results: shoe -> running shoes')

// ---- voice
await p.goto(BASE); await p.click('button[aria-label="Tìm bằng giọng nói"]'); await p.click('button[aria-label="Bắt đầu ghi âm"]'); await p.waitForSelector('text=Đang nghe')
await p.waitForTimeout(6500); await shot('22-voice-recording'); await p.click('button[aria-label="Dừng ghi âm"]')
await p.waitForSelector('text=Bạn đã nói', { timeout: 60000 }); await p.waitForURL('**via=voice**', { timeout: 20000 })
const url = decodeURIComponent(p.url()); console.log('   transcript ->', url.split('q=')[1].split('&')[0])
await p.waitForSelector('text=Tìm kiếm AI'); await shot('23-voice-results'); ok('voice search: speech transcribed and searched')

// ---- mobile
const m = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'vi-VN' }); const mp = await m.newPage()
await mp.goto(BASE + '/san-pham?q=' + encodeURIComponent('áo thun nam dưới 300 nghìn')); await mp.waitForSelector('text=Tìm kiếm AI'); await mp.screenshot({ path: `${OUT}/24-mobile-search.png` })
if (await mp.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) errors.push('mobile overflow'); ok('mobile: no horizontal scroll')
await browser.close(); console.log(errors.length ? 'ERRORS:\n' + [...new Set(errors)].join('\n') : 'no console/page/5xx errors'); process.exit(errors.length ? 1 : 0)
