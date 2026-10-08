import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchProducts, type Product } from '../api'
import ProductCard from '../components/ProductCard'
import { stockBadge } from '../stock'

const CATEGORIES = [
  { id: 'all', label: 'All' },
  { id: 'hoodie', label: 'Hoodies' },
  { id: 'crewneck', label: 'Crewnecks' },
  { id: 't-shirt', label: 'Tees' },
  { id: 'quarter-zip', label: 'Quarter-Zips' },
  { id: 'jacket', label: 'Jackets' },
  { id: 'long-sleeve', label: 'Long Sleeve' },
]
const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
type Sort = 'featured' | 'price-asc' | 'price-desc'

export default function Products() {
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [params, setParams] = useSearchParams()
  const category = params.get('category') ?? 'all'
  const setCategory = (c: string) => setParams(c === 'all' ? {} : { category: c }, { replace: true })
  const [size, setSize] = useState('')
  const [sort, setSort] = useState<Sort>('featured')

  useEffect(() => {
    fetchProducts()
      .then(setProducts)
      .catch(() => setError('Could not load products. Is the backend running?'))
      .finally(() => setLoading(false))
  }, [])

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: products.length }
    products.forEach((p) => (c[p.category ?? 'other'] = (c[p.category ?? 'other'] ?? 0) + 1))
    return c
  }, [products])

  const shown = useMemo(() => {
    const words = query.toLowerCase().split(/\s+/).filter(Boolean)
    const list = products.filter((p) => {
      if (category !== 'all' && p.category !== category) return false
      if (size && !p.in_stock_sizes?.includes(size)) return false
      const text = [p.name, p.description, p.garment_type, ...p.colors, ...p.search_tags].join(' ').toLowerCase()
      return words.every((w) => text.includes(w))
    })
    if (sort === 'price-asc') list.sort((a, b) => a.price - b.price || a.name.localeCompare(b.name))
    if (sort === 'price-desc') list.sort((a, b) => b.price - a.price || a.name.localeCompare(b.name))
    return list
  }, [products, query, category, size, sort])

  const filtered = query || category !== 'all' || size || sort !== 'featured'
  const reset = () => {
    setQuery('')
    setCategory('all')
    setSize('')
    setSort('featured')
  }

  return (
    <section className="page">
      <p className="eyebrow">Products</p>
      <h1>The collection</h1>

      <div className="filters">
        <div className="filter-row">
          <input
            className="filter-search"
            type="search"
            placeholder="Search: “bulldog”, “navy”, “harvard”…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search products"
          />
          <select value={size} onChange={(e) => setSize(e.target.value)} aria-label="In stock in size">
            <option value="">Any size</option>
            {SIZES.map((s) => (
              <option key={s} value={s}>In stock in {s}</option>
            ))}
          </select>
          <select value={sort} onChange={(e) => setSort(e.target.value as Sort)} aria-label="Sort">
            <option value="featured">Sort: Featured</option>
            <option value="price-asc">Price: Low to High</option>
            <option value="price-desc">Price: High to Low</option>
          </select>
        </div>
        <div className="chips-row" role="group" aria-label="Category">
          {CATEGORIES.filter((c) => c.id === 'all' || counts[c.id]).map((c) => (
            <button
              key={c.id}
              className={`filter-chip ${category === c.id ? 'active' : ''}`}
              onClick={() => setCategory(c.id)}
              aria-pressed={category === c.id}
            >
              {c.label} <span>{counts[c.id] ?? 0}</span>
            </button>
          ))}
        </div>
        {!loading && (
          <p className="filter-count">
            Showing <strong>{shown.length}</strong> of {products.length} items
            {filtered && <button className="link-btn" onClick={reset}>Clear filters</button>}
          </p>
        )}
      </div>

      {loading && <p className="muted">Loading products…</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && shown.length === 0 && (
        <p className="muted empty">No items match. Try another size or search, or ask the chat assistant for ideas.</p>
      )}
      <div className="product-grid">
        {shown.map((p) => (
          <ProductCard
            key={p.product_id}
            product_id={p.product_id}
            name={p.name}
            price={p.price}
            image_url={p.image_url}
            description={p.description}
            inStockSizes={size ? p.in_stock_sizes : undefined}
            badge={stockBadge(p)}
          />
        ))}
      </div>
    </section>
  )
}
