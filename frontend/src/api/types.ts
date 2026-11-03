export type Role = 'CUSTOMER' | 'ADMIN' | 'SERVICE' | 'SALES' | 'WAREHOUSE' | 'MARKETING' | 'MANAGER'
export type OrderStatus = 'PENDING_PAYMENT' | 'PENDING' | 'CONFIRMED' | 'PACKED' | 'SHIPPING' | 'DELIVERED' | 'CANCELLED'

export interface User { id: number; email: string; role: Role; status: string; full_name?: string }
export interface Session { access_token: string; user: User }

export interface Category { id: number; name: string; description: string | null; product_count?: number }
export interface Product {
  id: number; sku: string; name: string; brand: string | null; description: string | null; price: number
  image_url: string | null; attributes: Record<string, unknown>; category: Category
  in_stock: boolean; quantity: number; created_at: string
  rating?: { average: number; count: number }
  status?: 'ACTIVE' | 'HIDDEN'; min_threshold?: number
}
export interface Review { id: number; rating: number; comment: string | null; author: string; created_at: string }
export interface ProductDetail extends Product { reviews: Review[] }
export interface Recommendation extends Product { reason: string }
export interface Page<T> { total: number; page: number; size: number; items: T[] }
export interface ProductPage extends Page<Product> { suggestion: string | null }

export interface CartItem {
  product_id: number; name: string; sku: string; image_url: string | null; category_id: number
  unit_price: number; quantity: number; sub_total: number; stock: number; available: boolean
}
export interface Cart { id: number; items: CartItem[]; item_count: number; subtotal: number }

export interface QuoteLine { product_id: number; name: string; image_url: string | null; quantity: number; unit_price: number; sub_total: number; problem: string | null }
export interface Quote {
  lines: QuoteLine[]; subtotal: number; discount: number; shipping_fee: number; total: number
  promo_code: string | null; promo_error: string | null; issues: string[]; can_checkout: boolean
}

export interface Address { id: number; recipient: string; phone: string; street: string; district: string | null; city: string; post_code: string | null; is_default: boolean; one_line: string }
export interface Profile { id: number; email: string; first_name: string; middle_name: string | null; last_name: string; full_name: string; phone: string | null; loyalty_tier: string; loyalty_point: number }

export interface Payment { method: string; amount: number; status: string; transaction_id: string | null; paid_at: string | null }
export interface Shipment { carrier: string | null; tracking_number: string | null; status: string; delivery_date: string | null }
export interface OrderItem { product_id: number; name: string; sku: string; image_url: string | null; quantity: number; unit_price: number; sub_total: number; reviewed: boolean }
export interface HistoryEntry { from_status: string | null; to_status: OrderStatus; changed_by: number | null; changed_at: string }
export interface Order {
  id: number; status: OrderStatus; payment_method: 'COD' | 'ONLINE'; customer_id: number
  subtotal: number; discount: number; shipping_fee: number; total_amount: number; item_count: number; created_at: string
  ship_recipient: string; ship_phone: string; ship_address: string; can_cancel: boolean
  pay_seconds_left: number | null
  payment: Payment | null; shipment: Shipment | null; items: OrderItem[]; history?: HistoryEntry[]
}
export interface PayResult { success: boolean; message: string; payment: Payment; order: Order }

export interface Support { id: number; customer_id: number; order_id: number | null; content: string; status: 'OPEN' | 'IN_PROGRESS' | 'RESOLVED'; response: string | null; handled_by: number | null; created_at: string }
export interface InventoryRow { product_id: number; quantity: number; min_threshold: number; low: boolean; name?: string; sku?: string; status?: string }
export interface Movement { id: number; type: string; quantity: number; reason: string | null; order_id: number | null; created_at: string }
export interface RestockRequest { id: number; product_id: number; supplier_id: number; quantity: number; status: 'REQUESTED' | 'CONFIRMED' | 'RECEIVED' | 'REJECTED'; created_by: number | null; created_at: string }
export interface Supplier { id: number; name: string; contact: string | null }
export interface Promotion { id: number; code: string; discount_type: 'PERCENT' | 'AMOUNT'; discount_value: number; min_order_value: number; start_at: string; end_at: string; active: boolean; used_count?: number }
export interface Account { id: number; email: string; role: Role; status: 'ACTIVE' | 'LOCKED' }

export interface BusinessReport {
  period: { start: string; end: string }
  kpis: { total_orders: number; committed_orders: number; committed_sales: number; delivered_revenue: number; average_order_value: number; cancel_rate: number; units_sold: number; stock_turnover: number }
  series: { date: string; orders: number; sales: number }[]
  by_status: Record<OrderStatus, number>
  top_products: { product_id: number; name: string; sku: string; quantity: number; revenue: number }[]
  inventory: { skus: number; units: number; value: number; out_of_stock: number; low_stock: number }
}
export interface RecRow { placement: string; impressions: number; clicks: number; add_to_cart: number; purchases: number; ctr: number; add_to_cart_rate: number; conversion_rate: number }
export interface RecReport { period: { start: string; end: string }; total: RecRow; placements: RecRow[] }

export interface SearchInterpretation { text: string; min_price: number | null; max_price: number | null; brands: string[]; colors: string[]; sizes: string[] }
export interface SearchResult extends Page<Product & { score?: number | null }> {
  mode: 'ai' | 'filters' | 'keyword'; degraded: boolean; suggestion: string | null; corrected: string | null; original: string
  interpreted: SearchInterpretation
  recognized: { query: string; category: string; color: string; brand: string } | null
}
export interface AiStatus { enabled: boolean; ready: boolean; indexed: number; model: string; syncing: boolean }

export interface ChatAction { type: 'create_support_request'; content: string; order_id: number | null }
export interface ChatPromotion extends Promotion { description: string }
export interface ChatReply {
  reply: string; mode: 'ai' | 'rules'; degraded: boolean; suggestions: string[]
  products: Product[]; promotions: ChatPromotion[]; orders: Order[]; actions: ChatAction[]
}
