'use client'

import { useState } from 'react'
import Link from 'next/link'

export default function VendorLoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    window.alert('Vendor login will be available once authentication is fully wired to the backend.')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-blue-50 py-12 px-4">
      <div className="max-w-md mx-auto bg-white rounded-2xl shadow-md border border-gray-100 p-8">
        <p className="text-xs uppercase tracking-[0.3em] text-blue-500">Vendors</p>
        <h1 className="mt-2 text-3xl font-bold text-gray-900">Sign in to manage your store</h1>
        <p className="mt-2 text-sm text-gray-600">
          Use your vendor credentials or connect a Shopify account from the signup page. OAuth/Google sign-in will be added next.
        </p>
        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="owner@yourstore.com"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent"
            required
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent"
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
          Need to connect Shopify or a private token?{' '}
          <Link href="/vendor/signup" className="text-blue-600 hover:text-blue-700 font-semibold">
            Go to vendor signup
          </Link>
        </p>
      </div>
    </div>
  )
}
