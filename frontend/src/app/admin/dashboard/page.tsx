'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { Store, DollarSign, ShoppingBag, Users, Trash2, Layers, Loader2 } from 'lucide-react'
import { getApiUrl } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'

export default function AdminDashboard() {
  const router = useRouter()
  const apiBase = useMemo(() => getApiUrl(), [])
  const { user, token, loading: authLoading } = useAuth()

  const [dashboardData, setDashboardData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [syncingAmazon, setSyncingAmazon] = useState(false)
  const [productUrl, setProductUrl] = useState('')
  const [addingProduct, setAddingProduct] = useState(false)
  const [productOverrides, setProductOverrides] = useState({
    title: '',
    price: '',
    image: '',
    description: '',
    rating: '',
    review_count: ''
  })
  const [deleteInputId, setDeleteInputId] = useState('')
  const [deletingProductId, setDeletingProductId] = useState<string | null>(null)
  const [deleteTextarea, setDeleteTextarea] = useState('')
  const [bulkDeleteResult, setBulkDeleteResult] = useState<{ deleted: any[]; not_found: string[] } | null>(null)
  const [storeInventory, setStoreInventory] = useState<{ shop: string; data: any } | null>(null)
  const [storeInventoryLoading, setStoreInventoryLoading] = useState<string | null>(null)
  const [bulkDeleting, setBulkDeleting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [selectedProducts, setSelectedProducts] = useState<Set<string>>(new Set())
  const [selectedCategory, setSelectedCategory] = useState<string>('all')

  useEffect(() => {
    if (!authLoading) {
      if (!user || user.role !== 'admin') {
        // Don't redirect immediately - show message instead
        if (user && user.role !== 'admin') {
          setErrorMessage('Your account does not have admin privileges. Please log in with an admin account.')
        }
        // router.push('/login')
      } else {
        fetchDashboardData()
      }
    }
  }, [user, authLoading, router])

  const getHeaders = () => {
    if (!token) {
      console.error('No token available - user not logged in')
      return {}
    }
    return {
      headers: { Authorization: `Bearer ${token}` }
    }
  }

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      const response = await axios.get(`${apiBase}/api/admin/dashboard`, getHeaders())
      setDashboardData(response.data)
    } catch (error: any) {
      setErrorMessage('Failed to load dashboard')
    } finally {
      setLoading(false)
    }
  }

  const buildMetadata = () => {
    const metadata: Record<string, string> = {}
    Object.entries(productOverrides).forEach(([key, value]) => {
      if (value.trim().length > 0) {
        metadata[key] = value.trim()
      }
    })
    return metadata
  }

  const handleAddProduct = async () => {
    setErrorMessage('')
    setSuccessMessage('')
    if (!productUrl) {
      setErrorMessage('Paste an Amazon or eBay link first.')
      return
    }

    if (!token) {
      setErrorMessage('You must be logged in to add products. Please log in first.')
      router.push('/login')
      return
    }

    if (!user || user.role !== 'admin') {
      setErrorMessage('Admin access required. Your account does not have admin privileges.')
      return
    }

    try {
      setAddingProduct(true)
      const headers = getHeaders()
      console.log('Adding product with headers:', headers)
      await axios.post(`${apiBase}/api/admin/products/add_from_url`, {
        url: productUrl.trim(),
        metadata: buildMetadata()
      }, headers)
      setSuccessMessage('Product added successfully!')
      setProductUrl('')
      setProductOverrides({
        title: '',
        price: '',
        image: '',
        description: '',
        rating: '',
        review_count: ''
      })
      fetchDashboardData()
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message || 'Unknown error'
      const status = error?.response?.status
      
      // Better error messages
      if (status === 403) {
        if (detail.includes('admin') || detail.includes('Admin')) {
          setErrorMessage(`Admin access required. Please log in as an admin user. If you don't have an admin account, run: python create_admin.py`)
        } else {
          setErrorMessage(`Access denied: ${detail}`)
        }
      } else if (status === 401) {
        setErrorMessage('Not logged in. Please log in first at /login')
      } else {
        setErrorMessage(`Failed to add product: ${detail}`)
      }
      
      console.error('Add product error:', { status, detail, error })
    } finally {
      setAddingProduct(false)
    }
  }

  const handleDeleteProduct = async (productId?: string) => {
    setErrorMessage('')
    setSuccessMessage('')
    const targetId = (productId || deleteInputId).trim()
    if (!targetId) {
      setErrorMessage('Enter a product ID first.')
      return
    }

    const confirmed = window.confirm(`Remove product ${targetId}? This action cannot be undone.`)
    if (!confirmed) {
      return
    }
    try {
      setDeletingProductId(targetId)
      await axios.delete(`${apiBase}/api/admin/products/${targetId}`, getHeaders())
      if (!productId) {
        setDeleteInputId('')
      }
      setSuccessMessage('Product removed.')
      fetchDashboardData()
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message || 'Unknown error'
      setErrorMessage(`Failed to delete product: ${detail}`)
    } finally {
      setDeletingProductId(null)
    }
  }

  const handleBulkDelete = async () => {
    setErrorMessage('')
    setSuccessMessage('')

    const ids = deleteTextarea
      .split(/[\s,;,]+/)
      .map((id) => id.trim())
      .filter((id) => id.length > 0)
    if (ids.length === 0) {
      setErrorMessage('Paste one or more product IDs (separated by commas or new lines).')
      return
    }
    const confirmed = window.confirm(`Delete ${ids.length} product(s)? This cannot be undone.`)
    if (!confirmed) {
      return
    }
    try {
      setBulkDeleting(true)
      setBulkDeleteResult(null)
      const response = await axios.post(
        `${apiBase}/api/admin/products/delete`,
        { product_ids: ids },
        getHeaders()
      )
      setBulkDeleteResult(response.data)
      setSuccessMessage('Bulk delete finished.')
      fetchDashboardData()
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message || 'Unable to delete products.'
      setErrorMessage(detail)
    } finally {
      setBulkDeleting(false)
    }
  }

  const fetchStoreInventory = async (shop: string) => {
    setErrorMessage('')
    try {
      setStoreInventoryLoading(shop)
      const response = await axios.get(`${apiBase}/api/admin/stores/${shop}/inventory`, getHeaders())
      setStoreInventory({ shop, data: response.data })
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message || 'Unable to load store inventory.'
      setErrorMessage(detail)
    } finally {
      setStoreInventoryLoading(null)
    }
  }

  const handleSyncAmazon = async () => {
    setErrorMessage('')
    setSuccessMessage('')
    try {
      setSyncingAmazon(true)
      const response = await axios.post(
        `${apiBase}/api/admin/amazon/sync`,
        null,
        getHeaders()
      )
      setSuccessMessage('Amazon sync started in background! This may take a few minutes. The page will refresh when complete.')
      // Refresh dashboard after a delay to show updated products
      setTimeout(() => {
        fetchDashboardData()
        setSyncingAmazon(false)
      }, 5000)
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message || 'Unknown error'
      setErrorMessage(`Failed to launch Amazon sync: ${detail}`)
      setSyncingAmazon(false)
    }
  }

  const handleToggleProduct = (productId: string) => {
    const newSelected = new Set(selectedProducts)
    if (newSelected.has(productId)) {
      newSelected.delete(productId)
    } else {
      newSelected.add(productId)
    }
    setSelectedProducts(newSelected)
  }

  const handleSelectAll = () => {
    if (selectedProducts.size === filteredProducts.length) {
      setSelectedProducts(new Set())
    } else {
      setSelectedProducts(new Set(filteredProducts.map((p: any) => p.id)))
    }
  }

  const handleDeleteSelected = async () => {
    if (selectedProducts.size === 0) {
      setErrorMessage('No products selected')
      return
    }
    const confirmed = window.confirm(`Delete ${selectedProducts.size} selected product(s)? This cannot be undone.`)
    if (!confirmed) {
      return
    }
    try {
      setBulkDeleting(true)
      const response = await axios.post(
        `${apiBase}/api/admin/products/delete`,
        { product_ids: Array.from(selectedProducts) },
        getHeaders()
      )
      setBulkDeleteResult(response.data)
      setSelectedProducts(new Set())
      setSuccessMessage(`Deleted ${response.data.deleted?.length || 0} product(s)`)
      fetchDashboardData()
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message || 'Unable to delete products.'
      setErrorMessage(detail)
    } finally {
      setBulkDeleting(false)
    }
  }

  const filteredProducts = useMemo(() => {
    if (!dashboardData?.top_products) return []
    if (selectedCategory === 'all') return dashboardData.top_products
    return dashboardData.top_products.filter((p: any) => p.category === selectedCategory)
  }, [dashboardData, selectedCategory])

  const handleApproveStore = async (shop: string) => {
    setErrorMessage('')
    setSuccessMessage('')
    try {
      await axios.post(
        `${apiBase}/api/admin/stores/${shop}/approve`,
        null,
        getHeaders()
      )
      setSuccessMessage(`Store ${shop} approved!`)
      fetchDashboardData() // Refresh data
    } catch (error) {
      setErrorMessage('Failed to approve store')
    }
  }

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="animate-spin h-8 w-8 text-blue-600" />
      </div>
    )
  }

  if (!user || user.role !== 'admin') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-md p-8 max-w-md text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Admin Access Required</h2>
          <p className="text-gray-600 mb-6">You need to be logged in as an admin to access this page.</p>
          <div className="space-y-3">
            <a
              href="/login"
              className="block w-full bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
            >
              Go to Login
            </a>
            <p className="text-sm text-gray-500 mt-4">
              Don't have an admin account? Use the backend script to create one:
              <br />
              <code className="text-xs bg-gray-100 px-2 py-1 rounded">python create_admin.py</code>
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Super Admin Dashboard</h1>
          <button
            onClick={handleSyncAmazon}
            disabled={syncingAmazon}
            className="flex items-center gap-2 bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors disabled:bg-gray-400"
          >
            {syncingAmazon ? 'Syncing Amazon...' : 'Sync Amazon Inventory'}
          </button>
        </div>

        {successMessage && (
          <div className="mb-4 p-3 bg-green-100 text-green-700 rounded-lg text-sm text-center">
            {successMessage}
          </div>
        )}
        {errorMessage && (
          <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-lg text-sm text-center">
            {errorMessage}
          </div>
        )}

        {/* Unified Add Product Form */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Add Affiliate Product</h2>
          <div className="space-y-4">
            <input
              type="text"
              value={productUrl}
              onChange={(e) => setProductUrl(e.target.value)}
              placeholder="Paste Amazon or eBay affiliate URL"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <input
                type="text"
                value={productOverrides.title}
                onChange={(e) => setProductOverrides({ ...productOverrides, title: e.target.value })}
                placeholder="Product title (optional override)"
                className="px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <input
                type="text"
                value={productOverrides.price}
                onChange={(e) => setProductOverrides({ ...productOverrides, price: e.target.value })}
                placeholder="Price (ex. 149.99)"
                className="px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <input
                type="text"
                value={productOverrides.image}
                onChange={(e) => setProductOverrides({ ...productOverrides, image: e.target.value })}
                placeholder="Image URL (optional)"
                className="px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <input
                type="text"
                value={productOverrides.rating}
                onChange={(e) => setProductOverrides({ ...productOverrides, rating: e.target.value })}
                placeholder="Rating (ex. 4.7)"
                className="px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <input
                type="text"
                value={productOverrides.review_count}
                onChange={(e) => setProductOverrides({ ...productOverrides, review_count: e.target.value })}
                placeholder="Review count"
                className="px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <textarea
              value={productOverrides.description}
              onChange={(e) => setProductOverrides({ ...productOverrides, description: e.target.value })}
              placeholder="Short description / key bullet points"
              className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={3}
            />
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-500">
                We’ll scrape Amazon/eBay for details automatically. Provide overrides if the scrape can’t find a price or image.
              </p>
              <button
                onClick={handleAddProduct}
                disabled={addingProduct}
                className="bg-green-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-green-700 transition-colors disabled:bg-gray-400"
              >
                {addingProduct ? 'Adding…' : 'Add Product'}
              </button>
            </div>
          </div>
        </div>

        {/* Delete Product */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8 border border-red-100 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900">Delete Products</h2>
            <Trash2 className="w-5 h-5 text-red-500" />
          </div>
          <p className="text-sm text-gray-500">
            Paste one or many product IDs (comma or newline separated). We’ll remove each product and its related listings.
          </p>
          <textarea
            value={deleteTextarea}
            onChange={(e) => setDeleteTextarea(e.target.value)}
            placeholder="d2464285-9c43-4823-ad64-88312dd8289f&#10;4a95582a-8842-4ed4-857c-8fe3fc01a22c"
            rows={4}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent font-mono text-sm"
          />
          <input
            type="text"
            value={deleteInputId}
            onChange={(e) => setDeleteInputId(e.target.value)}
            placeholder="Optional quick ID"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
          />
          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              onClick={handleBulkDelete}
              disabled={bulkDeleting}
              className="shrink-0 bg-red-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-red-700 transition-colors disabled:bg-gray-400"
            >
              {bulkDeleting ? 'Deleting…' : 'Delete selected'}
            </button>
            <button
              onClick={() => {
                setDeleteTextarea(deleteInputId)
                handleDeleteProduct()
              }}
              disabled={!!deletingProductId || !deleteInputId}
              className="shrink-0 border border-gray-300 px-6 py-2 rounded-lg text-sm font-semibold text-gray-700 hover:border-gray-500 transition-colors disabled:text-gray-400 disabled:border-gray-200"
            >
              Quick delete single ID
            </button>
          </div>
          {bulkDeleteResult && (
            <div className="text-sm text-gray-600">
              <p className="font-semibold">Deleted: {bulkDeleteResult.deleted.length}</p>
              {bulkDeleteResult.not_found.length > 0 && (
                <p className="text-red-600">Not found: {bulkDeleteResult.not_found.join(', ')}</p>
              )}
            </div>
          )}
        </div>

        {/* Platform Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center gap-4">
              <div className="bg-blue-100 p-3 rounded-lg">
                <Store className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Total Stores</p>
                <p className="text-2xl font-bold text-gray-900">
                  {dashboardData?.stats.total_stores || 0}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center gap-4">
              <div className="bg-green-100 p-3 rounded-lg">
                <DollarSign className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Total Revenue</p>
                <p className="text-2xl font-bold text-gray-900">
                  ${dashboardData?.stats.total_revenue?.toFixed(2) || '0.00'}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center gap-4">
              <div className="bg-purple-100 p-3 rounded-lg">
                <ShoppingBag className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Total Orders</p>
                <p className="text-2xl font-bold text-gray-900">
                  {dashboardData?.stats.total_orders || 0}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center gap-4">
              <div className="bg-orange-100 p-3 rounded-lg">
                <Users className="w-6 h-6 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Commission</p>
                <p className="text-2xl font-bold text-gray-900">
                  ${dashboardData?.stats.total_commission?.toFixed(2) || '0.00'}
                </p>
              </div>
            </div>
          </div>
        </div>

        {dashboardData?.category_summary && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-8 border border-gray-100">
            <div className="flex items-center gap-3 mb-4">
              <Layers className="w-5 h-5 text-blue-600" />
              <h2 className="text-xl font-bold text-gray-900">Category breakdown</h2>
            </div>
            <div className="flex flex-wrap gap-3 mb-4">
              <button
                onClick={() => setSelectedCategory('all')}
                className={`inline-flex items-center rounded-full border px-4 py-1.5 text-sm font-medium transition-colors ${
                  selectedCategory === 'all'
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
                }`}
              >
                All Products
              </button>
              {Object.entries(dashboardData.category_summary).map(([category, count]) => (
                <button
                  key={category}
                  onClick={() => setSelectedCategory(category)}
                  className={`inline-flex items-center rounded-full border px-4 py-1.5 text-sm font-medium transition-colors ${
                    selectedCategory === category
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  {category}: <span className="ml-1 font-semibold">{count as number}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Stores */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-6">Vendor Stores</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4">Store</th>
                  <th className="text-left py-3 px-4">Status</th>
                  <th className="text-left py-3 px-4">Products</th>
                  <th className="text-left py-3 px-4">Sales</th>
                  <th className="text-left py-3 px-4">Commission</th>
                  <th className="text-left py-3 px-4">Actions</th>
                  <th className="text-left py-3 px-4">Inventory</th>
                </tr>
              </thead>
              <tbody>
                {dashboardData?.stores.map((store: any) => (
                  <tr key={store.id} className="border-b hover:bg-gray-50">
                    <td className="py-3 px-4 font-medium">{store.shop_domain}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${store.status === 'active'
                          ? 'bg-green-100 text-green-800'
                          : store.status === 'pending_approval'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-gray-100 text-gray-800'
                          }`}
                      >
                        {store.status}
                      </span>
                    </td>
                    <td className="py-3 px-4">{store.total_products}</td>
                    <td className="py-3 px-4">${store.total_sales?.toFixed(2) || '0.00'}</td>
                    <td className="py-3 px-4">{(store.commission_rate * 100).toFixed(1)}%</td>
                    <td className="py-3 px-4">
                      {store.status === 'pending_approval' && (
                        <button
                          onClick={() => handleApproveStore(store.shop_domain)}
                          className="text-blue-600 hover:text-blue-700 font-medium"
                        >
                          Approve
                        </button>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() => fetchStoreInventory(store.shop_domain)}
                        className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                      >
                        {storeInventoryLoading === store.shop_domain ? 'Loading…' : 'View'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {storeInventory && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-8 border border-blue-100">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  Inventory · {storeInventory.data.store?.store_name || storeInventory.shop}
                </h2>
                <p className="text-sm text-gray-500">{storeInventory.shop}</p>
              </div>
              <button
                onClick={() => setStoreInventory(null)}
                className="text-sm text-gray-500 hover:text-gray-800"
              >
                Close
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              <div className="rounded-xl border border-gray-100 p-4">
                <p className="text-sm text-gray-500">Shopify listings</p>
                <p className="text-2xl font-bold text-gray-900">
                  {storeInventory.data.shopify_listings.length}
                </p>
              </div>
              <div className="rounded-xl border border-gray-100 p-4">
                <p className="text-sm text-gray-500">Affiliate listings</p>
                <p className="text-2xl font-bold text-gray-900">
                  {storeInventory.data.affiliate_products.length}
                </p>
              </div>
            </div>
            {storeInventory.data.shopify_listings.length > 0 && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Shopify products</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2 px-3">Product ID</th>
                        <th className="text-left py-2 px-3">Price</th>
                        <th className="text-left py-2 px-3">Qty</th>
                        <th className="text-left py-2 px-3">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {storeInventory.data.shopify_listings.map((listing: any) => (
                        <tr key={listing.id} className="border-b">
                          <td className="py-2 px-3 font-mono text-xs">{listing.product_id}</td>
                          <td className="py-2 px-3">${listing.price?.toFixed(2) ?? '0.00'}</td>
                          <td className="py-2 px-3">{listing.quantity ?? 0}</td>
                          <td className="py-2 px-3 capitalize">{listing.status || 'active'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            {storeInventory.data.affiliate_products.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Affiliate products</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2 px-3">Title</th>
                        <th className="text-left py-2 px-3">Game</th>
                        <th className="text-left py-2 px-3">Price</th>
                      </tr>
                    </thead>
                    <tbody>
                      {storeInventory.data.affiliate_products.map((item: any) => (
                        <tr key={item.id} className="border-b">
                          <td className="py-2 px-3">{item.title}</td>
                          <td className="py-2 px-3">{item.game || 'Other'}</td>
                          <td className="py-2 px-3">${item.price?.toFixed(2) ?? '0.00'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            {storeInventory.data.shopify_listings.length === 0 && storeInventory.data.affiliate_products.length === 0 && (
              <p className="text-sm text-gray-500">No listings yet for this store.</p>
            )}
          </div>
        )}

        {/* Top Products */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-gray-900">
              Products {selectedCategory !== 'all' && `(${selectedCategory})`}
            </h2>
            {selectedProducts.size > 0 && (
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-600">{selectedProducts.size} selected</span>
                <button
                  onClick={handleDeleteSelected}
                  disabled={bulkDeleting}
                  className="bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-red-700 transition-colors disabled:bg-gray-400"
                >
                  {bulkDeleting ? 'Deleting…' : `Delete Selected (${selectedProducts.size})`}
                </button>
              </div>
            )}
          </div>
          <div className="mb-4 flex items-center gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedProducts.size === filteredProducts.length && filteredProducts.length > 0}
                onChange={handleSelectAll}
                className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700 font-medium">Select All</span>
            </label>
          </div>
          <div className="space-y-4">
            {filteredProducts.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No products found in this category.</p>
            ) : (
              filteredProducts.map((product: any) => (
                <div key={product.id} className="flex flex-wrap items-start gap-3 justify-between border-b pb-4">
                  <div className="flex items-start gap-3 flex-1">
                    <input
                      type="checkbox"
                      checked={selectedProducts.has(product.id)}
                      onChange={() => handleToggleProduct(product.id)}
                      className="mt-1 w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                    />
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{product.name}</p>
                      <p className="text-sm text-gray-600">{product.category || 'Uncategorized'}</p>
                      <p className="text-xs text-gray-400 mt-1 break-all">ID: {product.id}</p>
                    </div>
                  </div>
                  <div className="text-right space-y-2">
                    <p className="font-bold text-gray-900">{product.total_sales || 0} sales</p>
                    <button
                      onClick={() => handleDeleteProduct(product.id)}
                      disabled={deletingProductId === product.id}
                      className="text-sm text-red-600 hover:text-red-700 disabled:text-gray-400"
                    >
                      {deletingProductId === product.id ? 'Deleting…' : 'Remove'}
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
