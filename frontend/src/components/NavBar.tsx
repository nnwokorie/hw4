import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const mainLinks = [
  { to: '/', label: 'Home' },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

const guestLinks = [
  { to: '/login', label: 'Log In' },
  { to: '/create-account', label: 'Create Account' },
]

export default function NavBar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const links = user ? mainLinks : [...mainLinks, ...guestLinks]

  return (
    <header className="nav">
      <NavLink to="/" className="brand">
        Campus <span>Customs</span>
      </NavLink>
      <nav>
        {links.map((l) => (
          <NavLink key={l.to} to={l.to} end={l.to === '/'} className={({ isActive }) => (isActive ? 'active' : '')}>
            {l.label}
          </NavLink>
        ))}
        {user && (
          <>
            <span className="nav-user">Hi, {user.first_name}</span>
            <button
              className="nav-logout"
              onClick={async () => {
                await logout()
                navigate('/')
              }}
            >
              Log Out
            </button>
          </>
        )}
      </nav>
    </header>
  )
}
