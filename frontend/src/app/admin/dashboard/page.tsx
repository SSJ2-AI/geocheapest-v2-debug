'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { Store, DollarSign, ShoppingBag, Users, Trash2, Layers, Loader2 } from 'lucide-react'
import { getApiUrl } from '@/lib/api'

export default function AdminDashboard() {
  const router = useRouter()
  const apiBase = useMemo(() => getApiUrl(), [])
  const [adminKey, setAdminKey] = useState('')
  const [dashboardData, setDashboardData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [authenticated, setAuthenticated] = useState(false)
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
    if (!productUrl) {
      window.alert('Paste an Amazon or eBay link first.')
      return
    }

    try {
      setAddingProduct(true)
      await axios.post(`${apiBase}/api/admin/products/add_from_url`, {
        url: productUrl.trim(),
        admin_key: adminKey,
        metadata: buildMetadata()
      })
      window.alert('Product added successfully!')
      setProductUrl('')
      setProductOverrides({
        title: '',
        price: '',
        image: '',
        description: '',
        rating: '',
        review_count: ''
      })
      handleLogin()
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message || 'Unknown error'
      window.alert(`Failed to add product: ${detail}`)
    } finally {
      setAddingProduct(false)
    }
  }

  const handleDeleteProduct = async (productId?: string) => {
    const targetId = (productId || deleteInputId).trim()
    if (!targetId) {
      window.alert('Enter a product ID first.')
      return
    }
    if (!adminKey) {
      window.alert('Enter the admin key before deleting products.')
      return
    }
    const confirmed = window.confirm(`Remove product ${targetId}? This action cannot be undone.`)
    if (!confirmed) {
      return
    }
    try {
      setDeletingProductId(targetId)
      await axios.delete(`${apiBase}/api/admin/products/${targetId}`, {
        params: { admin_key: adminKey },
      })
      if (!productId) {
        setDeleteInputId('')
      }
      window.alert('Product removed.')
      handleLogin()
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message || 'Unknown error'
      window.alert(`Failed to delete product: ${detail}`)
    } finally {
      setDeletingProductId(null)
    }
  }

  const handleBulkDelete = async () => {
    if (!adminKey) {
      window.alert('Enter the admin key before deleting products.')
      return
    }
    const ids = deleteTextarea
      .split(/[\s,;,]+/)
      .map((id) => id.trim())
      .filter((id) => id.length > 0)
    if (ids.length === 0) {
      window.alert('Paste one or more product IDs (separated by commas or new lines).')
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
        { params: { admin_key: adminKey } }
      )
      setBulkDeleteResult(response.data)
      window.alert('Bulk delete finished.')
      handleLogin()
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message || 'Unable to delete products.'
      window.alert(detail)
    } finally {
      setBulkDeleting(false)
    }
  }

  const fetchStoreInventory = async (shop: string) => {
    if (!adminKey) {
      window.alert('Enter the admin key first.')
      return
    }
    try {
      setStoreInventoryLoading(shop)
      const response = await axios.get(`${apiBase}/api/admin/stores/${shop}/inventory`, {
        params: { admin_key: adminKey },
      })
      setStoreInventory({ shop, data: response.data })
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message || 'Unable to load store inventory.'
      window.alert(detail)
    } finally {
      setStoreInventoryLoading(null)
    }
  }

  const handleLogin = async () => {
    if (!adminKey) {
      window.alert('Please enter admin key')
      return
    }

    try {
      setLoading(true)
      const response = await axios.get(`${apiBase}/api/admin/dashboard`, {
        params: { admin_key: adminKey },
      })
      setDashboardData(response.data)
      setAuthenticated(true)
    } catch (error: any) {
      if (error.response?.status === 403) {
        window.alert('Invalid admin key')
      } else {
        window.alert('Failed to load dashboard')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSyncAmazon = async () => {
    try {
      setSyncingAmazon(true)
      await axios.post(
        `${apiBase}/api/admin/amazon/sync`,
        null,
        { params: { admin_key: adminKey } }
      )
      window.alert('Amazon ingest triggered')
    } catch (error) {
      window.alert('Failed to launch Amazon sync')
    } finally {
      setSyncingAmazon(false)
    }
  }

  const handleApproveStore = async (shop: string) => {
    try {
      await axios.post(
        `${apiBase}/api/admin/stores/${shop}/approve`,
        null,
        { params: { admin_key: adminKey } }
      )
      window.alert(`Store ${shop} approved!`)
      handleLogin() // Refresh data
    } catch (error) {
      window.alert('Failed to approve store')
    }
  }

  if (!authenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-md p-8 max-w-md w-full">
          <h1 className="text-2xl font-bold text-gray-900 mb-6 text-center">
            Admin Portal
          </h1>
          <input
            type="password"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleLogin()}
            placeholder="Enter admin key"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent mb-4"
          />
          <p className="text-xs text-gray-500 mb-4 text-center">
            Use the admin key from your backend env (try <span className="font-semibold">admin123</span> if you enabled
            legacy keys).
          </p>
          <button
            onClick={handleLogin}
            disabled={loading}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors disabled:bg-gray-400"
          >
            {loading ? 'Loading...' : 'Login'}
          </button>
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
            <div className="flex flex-wrap gap-3">
              {Object.entries(dashboardData.category_summary).map(([category, count]) => (
                <span key={category} className="inline-flex items-center rounded-full border border-gray-200 px-4 py-1.5 text-sm text-gray-700">
                  {category}: <span className="ml-1 font-semibold text-gray-900">{count as number}</span>
                </span>
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
          <h2 className="text-xl font-bold text-gray-900 mb-6">Top Products</h2>
          <div className="space-y-4">
            {dashboardData?.top_products.map((product: any) => (
              <div key={product.id} className="flex flex-wrap items-start gap-3 justify-between border-b pb-4">
                <div>
                  <p className="font-medium text-gray-900">{product.name}</p>
                  <p className="text-sm text-gray-600">{product.category}</p>
                  <p className="text-xs text-gray-400 mt-1 break-all">ID: {product.id}</p>
                </div>
                <div className="text-right space-y-2">
                  <p className="font-bold text-gray-900">{product.total_sales} sales</p>
                  <button
                    onClick={() => handleDeleteProduct(product.id)}
                    disabled={deletingProductId === product.id}
                    className="text-sm text-red-600 hover:text-red-700 disabled:text-gray-400"
                  >
                    {deletingProductId === product.id ? 'Deleting…' : 'Remove'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
