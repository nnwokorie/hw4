import type { Product } from './api'

const ALL_SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

// Honest urgency badge from real inventory (never invented).
export function stockBadge(p: Pick<Product, 'in_stock_sizes' | 'total_stock'>): { text: string; tone: 'out' | 'low' | 'info' } | null {
  if (!p.in_stock_sizes) return null
  if (p.in_stock_sizes.length === 0) return { text: 'Sold out', tone: 'out' }
  if (p.total_stock !== undefined && p.total_stock <= 20) return { text: `Only ${p.total_stock} left`, tone: 'low' }
  const soldOut = ALL_SIZES.filter((s) => !p.in_stock_sizes!.includes(s))
  if (soldOut.length === 1 || soldOut.length === 2) return { text: `Sold out in ${soldOut.join(', ')}`, tone: 'info' }
  if (soldOut.length > 2) return { text: 'Limited sizes', tone: 'info' }
  return null
}
