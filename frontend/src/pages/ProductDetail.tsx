import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, fetchProducts, formatPrice, type Product } from '../api'
import ProductCard from '../components/ProductCard'
import { stockBadge } from '../stock'

const CATEGORY_LABELS: Record<string, string> = {
  hoodie: 'Hoodies', crewneck: 'Crewnecks', 't-shirt': 'Tees', 'quarter-zip': 'Quarter-Zips', jacket: 'Jackets', 'long-sleeve': 'Long Sleeve',
}

export default function ProductDetail() {
  const { id = '' } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [all, setAll] = useState<Product[]>([])
  const [size, setSize] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    setProduct(null)
    setError('')
    setSize('')
    window.scrollTo(0, 0)
    fetchProduct(id)
      .then(setProduct)
      .catch(() => setError('Product not found.'))
  }, [id])

  useEffect(() => {
    fetchProducts().then(setAll).catch(() => setAll([]))
  }, [])

  if (error) return <p className="error">{error} <Link to="/products">Back to products</Link></p>
  if (!product) return <p className="muted">Loading…</p>

  const listing = all.find((p) => p.product_id === product.product_id)
  const category = listing?.category
  // Same category first, closest price first, skipping sold-out items.
  const related = all
    .filter((p) => p.product_id !== product.product_id && p.category === category && p.in_stock_sizes?.length)
    .sort((a, b) => Math.abs(a.price - product.price) - Math.abs(b.price - product.price) || a.name.localeCompare(b.name))
    .slice(0, 4)
  const selected = product.sizes?.find((s) => s.size === size)

  return (
    <>
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link to="/">Home</Link> / <Link to="/products">Products</Link>
        {category && <> / <Link to={`/products?category=${category}`}>{CATEGORY_LABELS[category] ?? category}</Link></>}
        {' / '}<span>{product.name}</span>
      </nav>
      <section className="detail">
        <div className="detail-media">
          <img src={product.image_url} alt={product.name} className="detail-img" />
          {listing && stockBadge(listing) && <span className={`badge ${stockBadge(listing)!.tone}`}>{stockBadge(listing)!.text}</span>}
        </div>
        <div className="detail-info">
          <p className="eyebrow">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="price big">{formatPrice(product.price)}</p>
          <p>{product.description}</p>

          <h3>Colors</h3>
          <div className="chips">
            {product.colors.map((c) => <span key={c} className="chip">{c}</span>)}
          </div>

          <h3>Size</h3>
          <div className="size-picker" role="radiogroup" aria-label="Choose a size">
            {product.sizes?.map((s) => (
              <button
                key={s.size}
                role="radio"
                aria-checked={size === s.size}
                disabled={s.quantity === 0}
                className={`size-btn ${size === s.size ? 'selected' : ''}`}
                onClick={() => setSize(s.size)}
                title={s.quantity === 0 ? 'Sold out' : `${s.quantity} in stock`}
              >
                {s.size}
              </button>
            ))}
          </div>
          <p className="size-status" aria-live="polite">
            {!selected && 'Select a size to see live stock.'}
            {selected && selected.quantity <= 5 && <strong className="low">Only {selected.quantity} left in {selected.size}. Don’t wait!</strong>}
            {selected && selected.quantity > 5 && <strong className="ok">✓ {selected.quantity} in stock in {selected.size}</strong>}
          </p>
          {product.sizes?.some((s) => s.quantity === 0) && (
            <p className="muted small">Sold out: {product.sizes.filter((s) => s.quantity === 0).map((s) => s.size).join(', ')}. Ask Handsome Dan for similar items in your size.</p>
          )}
        </div>
      </section>

      {related.length > 0 && (
        <section className="home-section">
          <div className="section-head">
            <h2>You may also like</h2>
            {category && <Link to={`/products?category=${category}`}>More {CATEGORY_LABELS[category] ?? ''} →</Link>}
          </div>
          <div className="product-row four">
            {related.map((p) => (
              <ProductCard key={p.product_id} product_id={p.product_id} name={p.name} price={p.price} image_url={p.image_url} description={p.description} badge={stockBadge(p)} />
            ))}
          </div>
        </section>
      )}
    </>
  )
}
