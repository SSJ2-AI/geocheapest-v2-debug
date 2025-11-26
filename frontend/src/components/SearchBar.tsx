'use client'

import { useState } from 'react'
import { Search } from 'lucide-react'

type SearchBarProps = {
  onSearch: (query: string) => void
  placeholder?: string
  className?: string
  inputClassName?: string
}

export function SearchBar({ onSearch, placeholder, className, inputClassName }: SearchBarProps) {
  const [query, setQuery] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSearch(query.trim())
  }

  return (
    <form onSubmit={handleSubmit} className={className ?? 'w-full'}>
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder || 'Search for Pokemon, Yu-Gi-Oh, Magic cards...'}
          className={`w-full px-6 py-4 rounded-full text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-4 focus:ring-blue-300 shadow-lg ${inputClassName ?? ''}`}
        />
        <button
          type="submit"
          className="absolute right-2 top-1/2 -translate-y-1/2 bg-blue-600 text-white p-3 rounded-full hover:bg-blue-700 transition-colors"
        >
          <Search className="w-5 h-5" />
        </button>
      </div>
    </form>
  )
}
