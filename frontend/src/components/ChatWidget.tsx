import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { fetchChatHistory, pageContext, sendChatMessage, type ChatTurn, type PageResults } from '../api'
import { useAuth } from '../auth'
import { useChatResults } from '../chatResults'

type Message = ChatTurn & { results?: PageResults | null; error?: boolean; verified?: boolean }

// Light Markdown: **bold** and line breaks / bullets.
function renderText(text: string) {
  return text.split('\n').map((line, i) => (
    <p key={i}>
      {line.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
        part.startsWith('**') && part.endsWith('**') ? <strong key={j}>{part.slice(2, -2)}</strong> : part,
      )}
    </p>
  ))
}

// Tappable starter questions that change with the page the shopper is on.
function suggestionsFor(pathname: string): string[] {
  if (/^\/products\/[^/]+/.test(pathname))
    return ['Is this in stock in M?', 'What colors does this come in?', 'Show me similar items', 'How much is this?']
  if (pathname.startsWith('/products'))
    return ['Navy crewnecks under $60', 'What’s in stock in XL?', 'Show me quarter-zips', 'Cheapest hoodies?']
  return ['What hoodies do you have?', 'Gifts under $40', 'Harvard–Yale game day gear', 'What’s in stock in XS?']
}

function greeting(firstName?: string): Message {
  return {
    role: 'assistant',
    content: firstName
      ? `Welcome back, ${firstName}! Ask me about merch, sizes, or stock. I’ll remember our chat.`
      : 'Woof! I’m Handsome Dan, the Campus Customs shop assistant. Ask me about merch, sizes, or stock. Log in and I’ll remember our chat.',
  }
}

export default function ChatWidget() {
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [messages, setMessages] = useState<Message[]>([greeting()])
  const endRef = useRef<HTMLDivElement>(null)
  const { show, clear } = useChatResults()
  const navigate = useNavigate()
  const { pathname } = useLocation()

  // Logged in: reload saved history from the database. Logged out: start fresh.
  useEffect(() => {
    let cancelled = false
    clear()
    if (!user) {
      setMessages([greeting()])
      return
    }
    fetchChatHistory().then((history) => {
      if (cancelled) return
      setMessages([greeting(user.first_name), ...history.map(({ role, content, results }) => ({ role, content, results }))])
    })
    return () => {
      cancelled = true
    }
  }, [user?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open, sending])

  function showResults(results: PageResults) {
    show(results)
    // Results render above page content; leave a single-item page so they're visible.
    if (/^\/products\/[^/]+/.test(pathname)) navigate('/products')
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    send(input)
  }

  async function send(raw: string) {
    const text = raw.trim()
    if (!text || sending) return
    const history: ChatTurn[] = messages.slice(1).filter((m) => !m.error).map(({ role, content }) => ({ role, content }))
    setInput('')
    setMessages((m) => [...m, { role: 'user', content: text }])
    setSending(true)
    try {
      const { reply, results, verified } = await sendChatMessage(text, history, pageContext(pathname))
      if (results) showResults(results)
      setMessages((m) => [...m, { role: 'assistant', content: reply, results, verified }])
    } catch (err) {
      setMessages((m) => [...m, { role: 'assistant', content: (err as Error).message, error: true }])
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="chat">
      {open && (
        <div className="chat-panel" role="dialog" aria-label="Campus Customs chat">
          <div className="chat-head">
            <div>
              <strong>🐶 Handsome Dan · Shop Assistant</strong>
              <small>{user ? `Chatting as ${user.first_name} · history saved` : 'Guest · history not saved'}</small>
            </div>
            <button onClick={() => setOpen(false)} aria-label="Close chat">×</button>
          </div>
          <div className="chat-body">
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                <div className={`bubble ${m.role} ${m.error ? 'error' : ''}`}>{renderText(m.content)}</div>
                {m.verified && <span className="verified">✓ Prices &amp; stock checked against live inventory</span>}
                {m.results && (
                  <button className="chat-shown" onClick={() => showResults(m.results!)}>
                    ↖ {m.results.products.length} item{m.results.products.length === 1 ? '' : 's'}: {m.results.title} · show on page
                  </button>
                )}
              </div>
            ))}
            {sending && <div className="bubble assistant typing">Thinking…</div>}
            <div ref={endRef} />
          </div>
          {!sending && (
            <div className="suggestions" aria-label="Suggested questions">
              {suggestionsFor(pathname).map((q) => (
                <button key={q} type="button" onClick={() => send(q)}>{q}</button>
              ))}
            </div>
          )}
          <form className="chat-input" onSubmit={onSubmit}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about hoodies, sizes, stock…"
              aria-label="Chat message"
              maxLength={1000}
            />
            <button type="submit" disabled={sending || !input.trim()}>Send</button>
          </form>
        </div>
      )}
      <button className="chat-toggle" onClick={() => setOpen((o) => !o)} aria-label="Toggle chat">
        {open ? '×' : '🐶 Ask Handsome Dan'}
      </button>
    </div>
  )
}
