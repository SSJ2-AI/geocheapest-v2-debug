'use client'

import { useMemo, useState } from 'react'
import axios from 'axios'
import { getApiUrl } from '@/lib/api'
import Link from 'next/link'

export default function VendorSignup() {
  const apiBase = useMemo(() => getApiUrl(), [])
  const [form, setForm] = useState({
    shop: '',
    access_token: '',
    store_name: '',
    owner_email: '',
  })
  const [connecting, setConnecting] = useState(false)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!form.shop || !form.access_token) {
      setStatusMessage('Enter your Shopify domain and a private app access token.')
      return
    }
    setStatusMessage(null)
    try {
      setConnecting(true)
      const payload = {
        shop: form.shop,
        access_token: form.access_token,
        store_name: form.store_name || undefined,
        owner_email: form.owner_email || undefined,
      }
      const response = await axios.post(`${apiBase}/api/vendor/shopify/manual-connect`, payload)
      setStatusMessage(
        `Connected ${response.data.shop}. We started the first sync – check the vendor dashboard in a few minutes.`
      )
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message || 'Unable to connect store.'
      setStatusMessage(detail)
    } finally {
      setConnecting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50 py-12 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-8">
          <p className="text-sm uppercase tracking-[0.3em] text-blue-500">Vendors</p>
          <h1 className="mt-3 text-3xl font-bold text-gray-900">Connect your Shopify store</h1>
          <p className="mt-2 text-gray-600">
            Install the OAuth app or paste a private app token below and we&apos;ll pull your catalog automatically.
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-md border border-gray-100 p-6 mb-10">
          <h2 className="text-xl font-semibold text-gray-900 mb-3">Option 1: One-click OAuth</h2>
          <p className="text-sm text-gray-600 mb-4">
            If you have the Partner access, start the standard Shopify OAuth flow and finish onboarding in Stripe.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <input
              type="text"
              placeholder="your-store.myshopify.com"
              value={form.shop}
              onChange={(e) => setForm((prev) => ({ ...prev, shop: e.target.value }))}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <a
              href={`${apiBase}/api/shopify/install?shop=${form.shop || 'your-store.myshopify.com'}`}
              className="inline-flex items-center justify-center rounded-full bg-blue-600 px-5 py-2 text-white font-semibold hover:bg-blue-700 transition-colors"
            >
              Launch OAuth
            </a>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-md border border-gray-100 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-3">Option 2: Private app token</h2>
          <p className="text-sm text-gray-600 mb-4">
            Paste a Shopify Admin API access token (read_products, read_inventory). We&apos;ll validate it, create webhooks,
            and start syncing immediately.
          </p>
          <form className="space-y-4" onSubmit={handleSubmit}>
            <input
              type="text"
              value={form.shop}
              onChange={(e) => setForm((prev) => ({ ...prev, shop: e.target.value }))}
              placeholder="your-store.myshopify.com"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
            <input
              type="password"
              value={form.access_token}
              onChange={(e) => setForm((prev) => ({ ...prev, access_token: e.target.value }))}
              placeholder="Admin API access token"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <input
                type="text"
                value={form.store_name}
                onChange={(e) => setForm((prev) => ({ ...prev, store_name: e.target.value }))}
                placeholder="Store display name (optional)"
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <input
                type="email"
                value={form.owner_email}
                onChange={(e) => setForm((prev) => ({ ...prev, owner_email: e.target.value }))}
                placeholder="Owner email (optional)"
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <button
              type="submit"
              disabled={connecting}
              className="w-full bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 transition-colors disabled:bg-gray-400"
            >
              {connecting ? 'Connecting…' : 'Connect store & sync products'}
            </button>
          </form>
          {statusMessage && (
            <p className="mt-4 text-sm text-gray-600">
              {statusMessage}
            </p>
          )}
        </div>

        <p className="mt-8 text-center text-sm text-gray-500">
          Already connected?{' '}
          <Link href="/vendor/dashboard" className="text-blue-600 hover:text-blue-700 font-semibold">
            Open the vendor dashboard
          </Link>
        </p>
      </div>
    </div>
  )
}
