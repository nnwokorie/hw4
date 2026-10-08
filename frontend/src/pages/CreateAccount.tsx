import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth, type SignupData } from '../auth'

const empty: SignupData = { first_name: '', last_name: '', email: '', password: '', confirm_password: '' }

export default function CreateAccount() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState<SignupData>(empty)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const update = (field: keyof SignupData) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [field]: e.target.value }))

  const mismatch = form.confirm_password.length > 0 && form.password !== form.confirm_password

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (form.password.length < 8) return setError('Password must be at least 8 characters.')
    if (form.password !== form.confirm_password) return setError('Passwords do not match.')
    setSubmitting(true)
    try {
      await signup(form)
      navigate('/products')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="page narrow">
      <p className="eyebrow">Join Campus Customs</p>
      <h1>Create Account</h1>
      <form className="form" onSubmit={onSubmit}>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="row">
          <label>
            First name
            <input value={form.first_name} onChange={update('first_name')} required autoComplete="given-name" />
          </label>
          <label>
            Last name
            <input value={form.last_name} onChange={update('last_name')} required autoComplete="family-name" />
          </label>
        </div>
        <label>
          Email
          <input type="email" value={form.email} onChange={update('email')} required autoComplete="email" />
        </label>
        <label>
          Password
          <input type="password" value={form.password} onChange={update('password')} required minLength={8} autoComplete="new-password" />
          <span className="hint">At least 8 characters.</span>
        </label>
        <label>
          Confirm password
          <input type="password" value={form.confirm_password} onChange={update('confirm_password')} required autoComplete="new-password" />
          {mismatch && <span className="hint error">Passwords do not match.</span>}
        </label>
        <button type="submit" className="btn" disabled={submitting}>{submitting ? 'Creating account…' : 'Create Account'}</button>
      </form>
      <p className="muted">
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </section>
  )
}
