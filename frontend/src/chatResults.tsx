import { createContext, useContext, useState, type ReactNode } from 'react'
import type { PageResults } from './api'

// Shared state so the chat widget can put the agent's product matches on the page.
type ChatResultsValue = {
  results: (PageResults & { id: number }) | null
  show: (results: PageResults) => void
  clear: () => void
}

const ChatResultsContext = createContext<ChatResultsValue | null>(null)

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ChatResultsValue['results']>(null)
  const value: ChatResultsValue = {
    results,
    show: (r) => setResults({ ...r, id: Date.now() }),
    clear: () => setResults(null),
  }
  return <ChatResultsContext.Provider value={value}>{children}</ChatResultsContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useChatResults() {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside ChatResultsProvider')
  return ctx
}
