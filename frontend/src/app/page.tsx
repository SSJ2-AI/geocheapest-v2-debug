'use client'

import { useEffect, useRef, useState } from 'react'
import { ProductCard } from '@/components/ProductCard'
import { CartWidget } from '@/components/CartWidget'
import { SearchBar } from '@/components/SearchBar'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const PAGE_SIZE = 24
const DEFAULT_CATEGORIES = ['Pokemon', 'One Piece', 'Yu-Gi-Oh', 'Magic: The Gathering', 'Dragon Ball']

interface Product {
  id: string
  name: string
  description: string
  category: string
  image_url: string
  best_price: number
  source?: string
  source_name?: string
  in_stock: boolean
  is_preorder: boolean
  url?: string
  rating?: number
  review_count?: number
  asin?: string
  upc?: string
  tags?: string[]
}

const normalizeKey = (product: Product) => {
  if (product.asin) {
    return `asin:${product.asin.trim().toLowerCase()}`
  }
  if (product.upc) {
    return `upc:${product.upc.trim()}`
  }
  return product.name
    ? `name:${product.name.toLowerCase().replace(/[^a-z0-9\s]/g, '').replace(/\s+/g, ' ').trim()}`
    : `id:${product.id}`
}

const pickPreferredProduct = (current: Product, challenger: Product) => {
  const score = (product: Product) => {
    let total = 0
    if (product.in_stock) total += 3
    if (product.best_price != null) total += 2
    if (product.source === 'affiliate') total += 1
    if (product.is_preorder) total -= 0.5
    if (product.best_price != null) {
      total -= product.best_price / 1000
    }
    return total
  }

  return score(challenger) > score(current) ? challenger : current
}

const deduplicateProducts = (items: Product[]) => {
  const map = new Map<string, Product>()

  items.forEach((item) => {
    const key = normalizeKey(item)
    if (!map.has(key)) {
      map.set(key, item)
    } else {
      map.set(key, pickPreferredProduct(map.get(key)!, item))
    }
  })

  return Array.from(map.values())
}

export default function Home() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [category, setCategory] = useState<string | null>(null)
  const [availableCategories, setAvailableCategories] = useState<string[]>(DEFAULT_CATEGORIES)
  const [totalAvailable, setTotalAvailable] = useState(0)
  const [offset, setOffset] = useState(0)
  const randomOrderRef = useRef<Record<string, number>>({})

  const ensureCategoryList = (items: Product[]) => {
    if (!items.length) return

    setAvailableCategories((prev) => {
      const baseSet = new Set(prev.length ? prev : DEFAULT_CATEGORIES)
      items.forEach((item) => {
        if (item.category) {
          baseSet.add(item.category)
        }
      })

      const prioritized = DEFAULT_CATEGORIES.filter((cat) => baseSet.has(cat))
      const additional = Array.from(baseSet)
        .filter((cat) => !DEFAULT_CATEGORIES.includes(cat))
        .sort((a, b) => a.localeCompare(b))

      return [...prioritized, ...additional]
    })
  }

  const applyRandomOrder = (items: Product[]) => {
    if (category !== null) return items

    return [...items].sort((a, b) => {
      if (!randomOrderRef.current[a.id]) {
        randomOrderRef.current[a.id] = Math.random()
      }
      if (!randomOrderRef.current[b.id]) {
        randomOrderRef.current[b.id] = Math.random()
      }
      return randomOrderRef.current[a.id] - randomOrderRef.current[b.id]
    })
  }

  const fetchProducts = async (reset = false) => {
    try {
      if (reset) {
        setLoading(true)
        randomOrderRef.current = {}
      } else {
        setIsLoadingMore(true)
      }

      const currentOffset = reset ? 0 : offset
      const params: Record<string, string | number> = {
        limit: PAGE_SIZE,
        offset: currentOffset,
      }

      if (category) {
        params.category = category
      }

      const response = await axios.get(`${API_URL}/api/products`, { params })
      const incoming: Product[] = response.data?.products || []
      const totalFromApi = typeof response.data?.total === 'number'
        ? response.data.total
        : incoming.length + (reset ? 0 : products.length)

      ensureCategoryList(incoming)
      setTotalAvailable(totalFromApi)
      setOffset(currentOffset + incoming.length)

      if (!incoming.length && !reset) {
        return
      }

      setProducts((prev) => {
        const merged = reset ? incoming : [...prev, ...incoming]
        const deduped = deduplicateProducts(merged)
        return applyRandomOrder(deduped)
      })
    } catch (error) {
      console.error('Failed to fetch products:', error)
    } finally {
      if (reset) {
        setLoading(false)
      }
      setIsLoadingMore(false)
    }
  }

  useEffect(() => {
    setProducts([])
    setOffset(0)
    setTotalAvailable(0)
    randomOrderRef.current = {}
    fetchProducts(true)
  }, [category])

  const handleLoadMore = () => {
    if (isLoadingMore || products.length >= totalAvailable) return
    fetchProducts()
  }

  const remainingCount = Math.max(totalAvailable - products.length, 0)

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="bg-white shadow-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 text-transparent bg-clip-text">
                GeoCheapest
              </h1>
              <span className="ml-2 text-sm text-gray-500">Canada's TCG Marketplace</span>
            </div>
            <CartWidget />
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="bg-gradient-to-r from-blue-600 to-purple-600 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-4xl font-bold mb-4">
            Find the Best TCG Prices in Canada
          </h2>
          <p className="text-xl mb-8 text-blue-100">
            We compare prices from multiple vendors to save you money
          </p>
          <SearchBar onSearch={(query) => console.log('Search:', query)} />
        </div>
      </section>

      {/* Category Filter */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-3 overflow-x-auto pb-2">
          <button
            onClick={() => setCategory(null)}
            className={`px-4 py-2 rounded-full whitespace-nowrap transition-all ${category === null
              ? 'bg-blue-600 text-white shadow-lg'
              : 'bg-white text-gray-700 hover:bg-gray-100'
              }`}
          >
            All Products
          </button>
          {availableCategories.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={`px-4 py-2 rounded-full whitespace-nowrap transition-all ${category === cat
                ? 'bg-blue-600 text-white shadow-lg'
                : 'bg-white text-gray-700 hover:bg-gray-100'
                }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </section>

      {/* Products Grid */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {products.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
            {products.length < totalAvailable && (
              <div className="text-center mt-10">
                <button
                  onClick={handleLoadMore}
                  disabled={isLoadingMore}
                  className="px-6 py-3 rounded-full bg-blue-600 text-white font-semibold shadow-md hover:bg-blue-700 transition-colors disabled:opacity-60"
                >
                  {isLoadingMore
                    ? 'Loading more products...'
                    : remainingCount > 0
                      ? `Load more (${remainingCount} remaining)`
                      : 'Load more'}
                </button>
              </div>
            )}
          </>
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
