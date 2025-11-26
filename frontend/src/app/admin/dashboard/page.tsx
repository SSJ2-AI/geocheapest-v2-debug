'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { Store, DollarSign, ShoppingBag, Users } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function AdminDashboard() {
  const router = useRouter()
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
      await axios.post(`${API_URL}/api/admin/products/add_from_url`, {
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

  const handleLogin = async () => {
    if (!adminKey) {
      window.alert('Please enter admin key')
      return
    }

    try {
      setLoading(true)
      const response = await axios.get(`${API_URL}/api/admin/dashboard`, {
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
        `${API_URL}/api/admin/amazon/sync`,
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
        `${API_URL}/api/admin/stores/${shop}/approve`,
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
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Top Products */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-6">Top Products</h2>
          <div className="space-y-4">
            {dashboardData?.top_products.map((product: any) => (
              <div key={product.id} className="flex justify-between items-center border-b pb-4">
                <div>
                  <p className="font-medium text-gray-900">{product.name}</p>
                  <p className="text-sm text-gray-600">{product.category}</p>
                </div>
                <div className="text-right">
                  <p className="font-bold text-gray-900">{product.total_sales} sales</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
