'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { ProductCard } from '@/components/ProductCard'
import { CartWidget } from '@/components/CartWidget'
import { SearchBar } from '@/components/SearchBar'
import axios from 'axios'
import { getApiUrl } from '@/lib/api'

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
  const [allProducts, setAllProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState<string | null>(null)
  const [sortOption, setSortOption] = useState<string>('featured')
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    fetchProducts()
  }, [apiBase])

  const fetchProducts = async () => {
    try {
      setLoading(true)
      const response = await axios.get(`${apiBase}/api/products`)
      setAllProducts(response.data?.products || [])
    } catch (error) {
      console.error('Failed to fetch products:', error)
    } finally {
      setLoading(false)
    }
  }

  const categoryFiltered = useMemo(() => {
    if (!category) return allProducts
    return allProducts.filter((product) => product.category === category)
  }, [allProducts, category])

  const filteredProducts = useMemo(() => {
    const term = searchTerm.trim().toLowerCase()
    if (!term) return categoryFiltered
    return categoryFiltered.filter((product) => {
      const nameMatch = product.name.toLowerCase().includes(term)
      const categoryMatch = (product.category || '').toLowerCase().includes(term)
      return nameMatch || categoryMatch
    })
  }, [categoryFiltered, searchTerm])

  const sortedProducts = useMemo(() => {
    const items = [...filteredProducts]
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
  }, [filteredProducts, sortOption])

  const categories = ['Pokemon', 'One Piece', 'Yu-Gi-Oh', 'Magic: The Gathering', 'Dragon Ball']

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50">
      {/* Global Header */}
      <header className="sticky top-0 z-50 bg-white/90 backdrop-blur border-b border-gray-100 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between gap-6">
            <Link href="/" className="flex items-center gap-3">
              <span className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 text-white font-semibold flex items-center justify-center shadow-sm">
                GT
              </span>
              <div className="leading-tight">
                <p className="text-base font-bold text-gray-900">GeoCheapestTCG</p>
                <p className="text-xs text-gray-500">Canada&apos;s TCG marketplace</p>
              </div>
            </Link>
            <nav className="hidden md:flex items-center gap-6 text-sm text-gray-600">
              <Link href="#products" className="hover:text-gray-900">All products</Link>
            </nav>
            <div className="flex items-center gap-3">
              <Link
                href="/login/customer"
                className="hidden sm:inline-flex items-center rounded-full border border-gray-200 px-4 py-1.5 text-sm font-medium text-gray-700 hover:border-blue-500 hover:text-blue-600"
              >
                Customer sign in
              </Link>
              <Link
                href="/login/vendor"
                className="inline-flex items-center rounded-full bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white shadow hover:bg-blue-700"
              >
                Vendor sign in
              </Link>
              <CartWidget />
            </div>
          </div>
        </div>
      </header>

      {/* Slim hero */}
      <section className="bg-white border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
          <div className="max-w-3xl space-y-4">
            <p className="text-xs uppercase tracking-[0.3em] text-blue-500">GeoCheapestTCG</p>
            <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 leading-snug">
              Canada&apos;s TCG Marketplace
            </h1>
            <p className="text-base text-gray-600">
              Browse sealed-product inventory from verified vendors and affiliate partners in a single, simple feed.
            </p>
          </div>
        </div>
      </section>

      {/* Products Grid */}
      <section id="products" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-6">
        <div className="space-y-4">
          <SearchBar
            onSearch={(query) => setSearchTerm(query)}
            placeholder="Search for Pokemon, Yu-Gi-Oh, Magic cards..."
            className="w-full"
          />
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => setCategory(null)}
              className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                category === null
                  ? 'bg-blue-600 text-white shadow'
                  : 'bg-white text-gray-700 border border-gray-200 hover:border-blue-400'
              }`}
            >
              All products
            </button>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setCategory(cat)}
                className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                  category === cat
                    ? 'bg-blue-100 text-blue-700 border border-blue-300'
                    : 'bg-white text-gray-700 border border-gray-200 hover:border-blue-400'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-blue-500">Marketplace</p>
            <h2 className="text-2xl font-bold text-gray-900">
              Browse sealed product deals
            </h2>
            <p className="text-xs text-gray-500 mt-1">
              Showing {sortedProducts.length} {sortedProducts.length === 1 ? 'item' : 'items'}
            </p>
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
        ) : sortedProducts.length > 0 ? (
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
