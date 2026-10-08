import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts, type Product } from '../api'
import ProductCard from '../components/ProductCard'
import { stockBadge } from '../stock'

const HERO_IDS = ['basic-hoodie-big-yale', '2025-yale-vs-harvard-t-shirt', 'champion-reverse-weave-crewneck', 'big-yale-tri-blend-t-shirt']
const PICK_IDS = [
  '2025-yale-vs-harvard-t-shirt',
  'boola-boola-t-shirt',
  'champion-reverse-weave-hoodie-1',
  'champion-mens-triumph-raglan-crew',
  'basic-hoodie-big-yale',
  'champion-full-zip-hood',
  'big-yale-tri-blend-t-shirt',
  'champion-reverse-weave-crewneck',
]
const CATEGORY_TILES = [
  { id: 'hoodie', label: 'Hoodies', cover: 'basic-hoodie-big-yale' },
  { id: 'crewneck', label: 'Crewnecks', cover: 'champion-reverse-weave-crewneck' },
  { id: 't-shirt', label: 'Tees', cover: 'boola-boola-t-shirt' },
  { id: 'quarter-zip', label: 'Quarter-Zips', cover: '' },
]

export default function Home() {
  const [products, setProducts] = useState<Product[]>([])
  useEffect(() => {
    fetchProducts().then(setProducts).catch(() => setProducts([]))
  }, [])

  const byId = useMemo(() => new Map(products.map((p) => [p.product_id, p])), [products])
  const hero = HERO_IDS.map((id) => byId.get(id)).filter(Boolean) as Product[]
  const picks = PICK_IDS.map((id) => byId.get(id)).filter(Boolean) as Product[]
  const tiles = CATEGORY_TILES.map((t) => {
    const items = products.filter((p) => p.category === t.id)
    const cover = byId.get(t.cover) ?? items[0]
    return { ...t, count: items.length, image: cover?.image_url }
  })

  return (
    <>
      <section className="hero-band">
        <div className="hero-copy">
          <p className="eyebrow light">Officially licensed · Bulldog proud</p>
          <h1>Classic collegiate style, made clean.</h1>
          <p>
            Yale blue gear for campus and beyond: timeless crewnecks, cozy hoodies, and everyday tees that show your
            Bulldog pride from move-in day to reunion.
          </p>
          <div className="actions">
            <Link to="/products" className="btn light">Shop the collection</Link>
            <Link to="/about" className="btn ghost light">Our story</Link>
          </div>
        </div>
        <div className="hero-collage" aria-hidden="true">
          {hero.map((p, i) => (
            <Link key={p.product_id} to={`/products/${p.product_id}`} className={`collage-item c${i}`} tabIndex={-1}>
              <img src={p.image_url} alt="" />
            </Link>
          ))}
        </div>
      </section>

      <section className="home-section">
        <div className="section-head">
          <h2>Shop by category</h2>
          <Link to="/products">View all →</Link>
        </div>
        <div className="category-tiles">
          {tiles.map((t) => (
            <Link key={t.id} to={`/products?category=${t.id}`} className="category-tile">
              {t.image && <img src={t.image} alt="" loading="lazy" />}
              <div>
                <strong>{t.label}</strong>
                <span>{t.count} styles</span>
              </div>
            </Link>
          ))}
        </div>
      </section>

      <section className="home-section">
        <div className="section-head">
          <div>
            <p className="eyebrow">Staff picks</p>
            <h2>Game day ready</h2>
          </div>
          <Link to="/products">Shop all →</Link>
        </div>
        <div className="product-row">
          {picks.map((p) => (
            <ProductCard
              key={p.product_id}
              product_id={p.product_id}
              name={p.name}
              price={p.price}
              image_url={p.image_url}
              description={p.description}
              badge={stockBadge(p)}
            />
          ))}
        </div>
      </section>

      <section className="trust-strip">
        <div><strong>Officially licensed</strong><span>Authentic Yale apparel and marks</span></div>
        <div><strong>Live stock on every item</strong><span>Real counts by size, never guesses</span></div>
        <div><strong>Ask Handsome Dan</strong><span>Our assistant finds your fit in seconds</span></div>
      </section>
    </>
  )
}
