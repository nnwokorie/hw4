import { Link } from 'react-router-dom'
import { formatPrice } from '../api'

type Props = {
  product_id: string
  name: string
  price: number
  image_url: string
  description: string
  inStockSizes?: string[]
  badge?: { text: string; tone: 'out' | 'low' | 'info' } | null
}

// One product tile. Used by Home, Products, chat results, and "You may also like"; always links to the single-item page.
export default function ProductCard({ product_id, name, price, image_url, description, inStockSizes, badge }: Props) {
  return (
    <Link to={`/products/${product_id}`} className="product-card">
      <div className="card-img">
        <img src={image_url} alt={name} loading="lazy" />
        {badge && <span className={`badge ${badge.tone}`}>{badge.text}</span>}
      </div>
      <div className="product-body">
        <h3>{name}</h3>
        <p className="price">{formatPrice(price)}</p>
        <p className="desc">{description}</p>
        {inStockSizes && <p className="sizes-line">{inStockSizes.length ? `In stock: ${inStockSizes.join(' · ')}` : 'Sold out'}</p>}
      </div>
    </Link>
  )
}
