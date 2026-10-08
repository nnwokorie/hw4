import { useEffect, useRef } from 'react'
import { useChatResults } from '../chatResults'
import ProductCard from './ProductCard'

// Renders the agent's structured product matches on the page as product cards.
export default function ChatResultsPanel() {
  const { results, clear } = useChatResults()
  const ref = useRef<HTMLElement>(null)

  useEffect(() => {
    if (results) ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [results?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!results) return null

  return (
    <section ref={ref} key={results.id} className="chat-results" aria-live="polite">
      <div className="chat-results-head">
        <div>
          <p className="eyebrow">From your chat</p>
          <h2>{results.title}</h2>
          <p className="muted">{results.products.length} item{results.products.length === 1 ? '' : 's'} · tap one to see full details</p>
        </div>
        <button className="btn ghost small" onClick={clear}>Clear results</button>
      </div>
      <div className="product-grid">
        {results.products.map((p) => (
          <ProductCard key={p.product_id} {...p} inStockSizes={p.in_stock_sizes} />
        ))}
      </div>
    </section>
  )
}
