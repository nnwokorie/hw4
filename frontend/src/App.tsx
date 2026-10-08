import { Link, Route, Routes, useLocation } from 'react-router-dom'
import NavBar from './components/NavBar'
import Home from './pages/Home'
import Products from './pages/Products'
import About from './pages/About'
import LogIn from './pages/LogIn'
import CreateAccount from './pages/CreateAccount'
import ProductDetail from './pages/ProductDetail'
import ChatWidget from './components/ChatWidget'
import ChatResultsPanel from './components/ChatResultsPanel'

export default function App() {
  // Chat results sit above the page content, except on a single-item page so the product is front and center.
  const onProductPage = /^\/products\/[^/]+/.test(useLocation().pathname)
  return (
    <>
      <div className="announce">Officially licensed Yale apparel · Live stock on every item · Questions? Ask Handsome Dan 🐶</div>
      <NavBar />
      <main>
        {!onProductPage && <ChatResultsPanel />}
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:id" element={<ProductDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<LogIn />} />
          <Route path="/create-account" element={<CreateAccount />} />
          <Route path="*" element={<Home />} />
        </Routes>
      </main>
      <footer className="site-footer">
        <div className="footer-grid">
          <div>
            <p className="footer-brand">Campus <span>Customs</span></p>
            <p>Classic collegiate style in Yale blue. Officially licensed apparel for students, alumni, families, and fans.</p>
          </div>
          <div>
            <h4>Shop</h4>
            <Link to="/products?category=hoodie">Hoodies</Link>
            <Link to="/products?category=crewneck">Crewnecks</Link>
            <Link to="/products?category=t-shirt">Tees</Link>
            <Link to="/products?category=quarter-zip">Quarter-Zips</Link>
          </div>
          <div>
            <h4>Help</h4>
            <Link to="/products">Check sizes &amp; stock</Link>
            <Link to="/login">Log in</Link>
            <Link to="/create-account">Create account</Link>
          </div>
          <div>
            <h4>About</h4>
            <Link to="/about">Our story</Link>
            <span>New Haven, CT</span>
          </div>
        </div>
        <p className="footer-bottom">© 2026 Campus Customs · Boola Boola!</p>
      </footer>
      <ChatWidget />
    </>
  )
}
