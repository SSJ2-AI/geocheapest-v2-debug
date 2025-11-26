'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { ProductCard } from '@/components/ProductCard'
import { CartWidget } from '@/components/CartWidget'
import { SearchBar } from '@/components/SearchBar'
import { useCartStore } from '@/store/cartStore'
import axios from 'axios'
import { useMemo } from 'react'
import { getApiUrl } from '@/lib/api'

const marketplaceHighlights = [
  {
    title: 'Verified Partner Stores',
    description: 'Canadian hobby shops and vetted Amazon/eBay partners with transparent ratings and stock data.'
  },
  {
    title: 'Best Price Engine',
    description: 'Real-time price comparison across Shopify vendors and affiliate listings, including ship cost optimization.'
  },
  {
    title: 'Secure Checkout',
    description: 'Stripe-powered split checkout for multi-vendor carts plus instant affiliate redirects when needed.'
  }
]

const experienceTiles = [
  {
    title: 'Customers',
    description: 'Create a free profile to save carts, compare shipping, and get alerted when sealed product prices drop.',
    action: 'Customer portal',
    href: '/signup'
  },
  {
    title: 'Vendors',
    description: 'Connect Shopify or upload affiliate links, sync Shippo labels, and manage payouts from one dashboard.',
    action: 'Vendor onboarding',
    href: '/vendor/signup'
  },
  {
    title: 'Admins',
    description: 'Monitor ingestion, approve stores, and push price updates with the protected super-admin workspace.',
    action: 'Admin access',
    href: '/admin/dashboard'
  }
]
const sortOptions = [
  { value: 'featured', label: 'Featured' },
  { value: 'price_low', label: 'Price: Low to High' },
  { value: 'price_high', label: 'Price: High to Low' },
  { value: 'rating', label: 'Customer rating' },
  { value: 'alpha', label: 'Alphabetical' },
]

interface Product {
  id: string
  name: string
  description: string
  category: string
  image_url: string
  best_price: number
  source: string
  source_name: string
  in_stock: boolean
  is_preorder: boolean
  url?: string  // Product page URL (Amazon, Shopify store, etc.)
  rating?: number  // Product rating (0-5)
  review_count?: number  // Number of reviews
}

export default function Home() {
  const apiBase = useMemo(() => getApiUrl(), [])
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState<string | null>(null)
  const [sortOption, setSortOption] = useState<string>('featured')

  useEffect(() => {
    fetchProducts()
  }, [category, apiBase])

  const fetchProducts = async () => {
    try {
      setLoading(true)
      const params = category ? { category } : {}
      const response = await axios.get(`${apiBase}/api/products`, { params })
      console.log('Products from API:', response.data.products)
      setProducts(response.data.products || [])
    } catch (error) {
      console.error('Failed to fetch products:', error)
    } finally {
      setLoading(false)
    }
  }

  const sortedProducts = useMemo(() => {
    const items = [...products]
    switch (sortOption) {
      case 'price_low':
        items.sort((a, b) => (a.best_price ?? 0) - (b.best_price ?? 0))
        break
      case 'price_high':
        items.sort((a, b) => (b.best_price ?? 0) - (a.best_price ?? 0))
        break
      case 'rating':
        items.sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0))
        break
      case 'alpha':
        items.sort((a, b) => a.name.localeCompare(b.name))
        break
      default:
        break
    }
    return items
  }, [products, sortOption])

  const categories = ['Pokemon', 'One Piece', 'Yu-Gi-Oh', 'Magic: The Gathering', 'Dragon Ball']

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50">
      {/* Global Header */}
      <header className="sticky top-0 z-50 bg-white/90 backdrop-blur border-b border-gray-100 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between gap-6">
            <Link href="/" className="flex items-center gap-3">
              <span className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 text-white font-semibold flex items-center justify-center shadow-sm">
                GC
              </span>
              <div className="leading-tight">
                <p className="text-base font-bold text-gray-900">GeoCheapest</p>
                <p className="text-xs text-gray-500">Canada&apos;s TCG marketplace</p>
              </div>
            </Link>
            <nav className="hidden md:flex items-center gap-6 text-sm text-gray-600">
              <Link href="#marketplace" className="hover:text-gray-900">Marketplace</Link>
              <Link href="/products" className="hover:text-gray-900">All products</Link>
              <Link href="/help" className="hover:text-gray-900">Help</Link>
              <Link href="/contact" className="hover:text-gray-900">Support</Link>
            </nav>
            <div className="flex items-center gap-3">
              <Link
                href="/signup"
                className="hidden sm:inline-flex items-center rounded-full border border-gray-200 px-4 py-1.5 text-sm font-medium text-gray-700 hover:border-blue-500 hover:text-blue-600"
              >
                Customer sign in
              </Link>
              <Link
                href="/vendor/signup"
                className="inline-flex items-center rounded-full bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white shadow hover:bg-blue-700"
              >
                Vendor sign in
              </Link>
              <CartWidget />
            </div>
          </div>
        </div>
        <div className="border-t border-gray-100 bg-gray-50/80">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center gap-3 overflow-x-auto py-3 text-sm">
            <button
              onClick={() => setCategory(null)}
              className={`rounded-full px-4 py-1.5 transition ${
                category === null ? 'bg-blue-600 text-white shadow' : 'bg-white text-gray-700 border border-gray-200'
              }`}
            >
              All products
            </button>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setCategory(cat)}
                className={`rounded-full px-4 py-1.5 transition ${
                  category === cat ? 'bg-blue-100 text-blue-700 border border-blue-300' : 'bg-white text-gray-700 border border-gray-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Slim hero */}
      <section className="bg-white border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-2xl space-y-4">
            <p className="text-xs uppercase tracking-[0.3em] text-blue-500">Canada&apos;s TCG marketplace</p>
            <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 leading-snug">
              Canada&apos;s TCG Marketplace
            </h1>
            <p className="text-base text-gray-600">
              Compare sealed products from Shopify vendors and affiliate partners, all in one clean feed.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row">
              <SearchBar onSearch={(query) => console.log('Search:', query)} />
              <div className="flex gap-3">
                <Link
                  href="/products"
                  className="inline-flex items-center justify-center rounded-full border border-blue-200 px-4 py-2 text-sm font-semibold text-blue-700 hover:border-blue-400"
                >
                  Browse catalog
                </Link>
                <Link
                  href="/vendor/dashboard"
                  className="inline-flex items-center justify-center rounded-full bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-blue-700"
                >
                  Vendor tools
                </Link>
              </div>
            </div>
          </div>
          <div className="grid w-full grid-cols-1 gap-4 sm:grid-cols-3">
            {marketplaceHighlights.map((card) => (
              <div key={card.title} className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-blue-500">{card.title}</p>
                <p className="mt-2 text-sm text-gray-600">{card.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Role-specific entry points */}
      <section id="marketplace" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {experienceTiles.map((tile) => (
            <div key={tile.title} className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
              <p className="text-xs uppercase tracking-[0.3em] text-gray-400">{tile.title}</p>
              <h3 className="mt-2 text-lg font-semibold text-gray-900">{tile.description}</h3>
              <Link
                href={tile.href}
                className="mt-6 inline-flex items-center text-sm font-semibold text-blue-700 hover:text-blue-900"
              >
                {tile.action} →
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* Products Grid */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-blue-500">Marketplace</p>
            <h2 className="text-2xl font-bold text-gray-900">Browse sealed product deals</h2>
          </div>
          <select
            value={sortOption}
            onChange={(e) => setSortOption(e.target.value)}
            className="w-full md:w-60 rounded-full border border-gray-200 px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {sortOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="bg-white rounded-lg shadow-md animate-pulse">
                <div className="h-64 bg-gray-200 rounded-t-lg"></div>
                <div className="p-4 space-y-3">
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                </div>
              </div>
            ))}
          </div>
        ) : products.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {sortedProducts.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-gray-500 text-lg">No products found</p>
          </div>
        )}
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12 mt-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <h3 className="text-lg font-bold mb-4">GeoCheapest</h3>
              <p className="text-gray-400">
                Canada's best TCG marketplace. We find you the lowest prices from trusted vendors.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-bold mb-4">For Vendors</h3>
              <ul className="space-y-2 text-gray-400">
                <li><a href="/vendor/signup" className="hover:text-white">Sell on GeoCheapest</a></li>
                <li><a href="/vendor/dashboard" className="hover:text-white">Vendor Dashboard</a></li>
                <li><a href="/portal" className="hover:text-white">Portals</a></li>
              </ul>
            </div>
            <div>
              <h3 className="text-lg font-bold mb-4">Support</h3>
              <ul className="space-y-2 text-gray-400">
                <li><a href="/help" className="hover:text-white">Help Center</a></li>
                <li><a href="/returns" className="hover:text-white">Returns</a></li>
                <li><a href="/contact" className="hover:text-white">Contact Us</a></li>
              </ul>
            </div>
          </div>
          <div className="mt-8 pt-8 border-t border-gray-800 text-center text-gray-400">
            <p>&copy; 2024 GeoCheapest. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
