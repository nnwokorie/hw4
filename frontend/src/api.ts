export type Product = {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  image_url: string
  price: number
  total_stock?: number
  category?: string
  in_stock_sizes?: string[]
  sizes?: { size: string; quantity: number }[]
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const fetchProducts = () => getJson<Product[]>('/api/products')
export const fetchProduct = (id: string) => getJson<Product>(`/api/products/${encodeURIComponent(id)}`)

export const formatPrice = (n: number) => `$${n.toFixed(2)}`

export type ChatProduct = {
  product_id: string
  name: string
  garment_type: string
  price: number
  image_url: string
  description: string
  colors: string[]
  in_stock_sizes: string[]
}

export type ChatTurn = { role: 'user' | 'assistant'; content: string }
export type PageResults = { title: string; products: ChatProduct[] }

// API contract for POST /api/chat: the agent's reply plus structured product matches for the page.
export type ChatReply = { reply: string; results: PageResults | null; verified?: boolean }

export type PageContext = { path: string; product_id: string | null }

// Which page the shopper is on, so the agent knows what "this" means on a product page.
export function pageContext(pathname: string): PageContext {
  const m = pathname.match(/^\/products\/([\w-]+)/)
  return { path: pathname, product_id: m ? m[1] : null }
}

// Sends the shopper's message to the PydanticAI agent behind FastAPI.
// `history` is only used for guests; logged-in history is loaded from the database by the server.
export async function sendChatMessage(message: string, history: ChatTurn[], page: PageContext): Promise<ChatReply> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ message, history: history.slice(-20), page }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'The assistant is unavailable right now.')
  return data as ChatReply
}

export type HistoryMessage = ChatTurn & { id: number; created_at: string; results: PageResults | null }

export async function fetchChatHistory(): Promise<HistoryMessage[]> {
  const res = await fetch('/api/chat/history', { credentials: 'include' })
  return res.ok ? res.json() : []
}
