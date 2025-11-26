'use client'

import { useState } from 'react'
import Link from 'next/link'

export default function CustomerLoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    window.alert('Customer login is not wired yet. Please use the vendor/admin credentials once provided.')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50 py-12 px-4">
      <div className="max-w-md mx-auto bg-white rounded-2xl shadow-md border border-gray-100 p-8">
        <p className="text-xs uppercase tracking-[0.3em] text-blue-500">Customers</p>
        <h1 className="mt-2 text-3xl font-bold text-gray-900">Sign in to GeoCheapestTCG</h1>
        <p className="mt-2 text-sm text-gray-600">Use your email or continue with Google. Account creation will be available soon.</p>
        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
          >
            Continue with email
          </button>
        </form>
        <button
          onClick={() => window.alert('Google sign-in will be connected once OAuth credentials are provisioned.')}
          className="mt-4 w-full border border-gray-300 text-gray-700 py-3 rounded-lg font-semibold hover:border-gray-500 transition-colors"
        >
          Continue with Google
        </button>
        <p className="mt-4 text-sm text-gray-500">
          New here?{' '}
          <Link href="/signup" className="text-blue-600 hover:text-blue-700 font-semibold">
            Create a customer account
          </Link>
        </p>
      </div>
    </div>
  )
}
