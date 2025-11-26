'use client'

import { useEffect, useState, Suspense, type ReactNode } from 'react'
import { useSearchParams } from 'next/navigation'
import axios from 'axios'
import { Package, DollarSign, TrendingUp, RefreshCw, Truck, Shield } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function VendorDashboardContent() {
  const searchParams = useSearchParams()
  const shop = searchParams.get('shop')
  const [dashboardData, setDashboardData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [labelLoading, setLabelLoading] = useState(false)
  const [labelCount, setLabelCount] = useState(1)
  const [labelForm, setLabelForm] = useState({
    order_id: '',
    name: '',
    street: '',
    city: '',
    province: 'ON',
    postal_code: '',
    country: 'CA',
  })

  useEffect(() => {
    if (shop) {
      fetchDashboardData()
    }
  }, [shop])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      const response = await axios.get(`${API_URL}/api/vendor/dashboard`, {
        params: { shop },
      })
      setDashboardData(response.data)
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleLabelSubmit = async () => {
    if (!labelForm.order_id || !labelForm.name || !labelForm.street || !labelForm.postal_code) {
      alert('Complete the label form before submitting.')
      return
    }
    try {
      setLabelLoading(true)
      await axios.post(`${API_URL}/api/vendor/shipping-label`, {
        shop,
        order_id: labelForm.order_id,
        shipping_address: labelForm,
        items: Array.from({ length: Math.max(labelCount, 1) }).map(() => ({
          name: 'Sealed Product',
          weight: 2,
        })),
      })
      alert('Label submitted! Check your email for the Shippo download link.')
    } catch (error) {
      console.error('Label generation failed:', error)
      alert('Unable to create label. Try again shortly.')
    } finally {
      setLabelLoading(false)
    }
  }

  const handleSyncProducts = async () => {
    try {
      setSyncing(true)
      await axios.post(`${API_URL}/api/vendor/sync-products`, null, {
        params: { shop },
      })
      alert('Product sync started! This may take a few minutes.')
      setTimeout(fetchDashboardData, 3000)
    } catch (error) {
      console.error('Sync failed:', error)
      alert('Failed to sync products')
    } finally {
      setSyncing(false)
    }
  }

  if (!shop) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-blue-50 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-xl p-10 max-w-2xl text-center border border-indigo-100">
          <h2 className="text-3xl font-bold text-gray-900 mb-3">
            Connect Your Shopify Store
          </h2>
          <p className="text-gray-600 mb-6">
            Sync your catalog in minutes, accept Stripe payouts, and get instant access to our national buyer base.
          </p>
          <a
            href={`${API_URL}/api/shopify/install?shop=YOUR_STORE.myshopify.com`}
            className="inline-flex items-center justify-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors shadow-lg shadow-blue-200"
          >
            Connect Shopify
          </a>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="space-y-4 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="text-gray-500 font-medium">Loading your dashboard…</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <p className="text-sm uppercase tracking-wide text-blue-600 font-semibold">Vendor Command Center</p>
            <h1 className="text-3xl font-bold text-gray-900 mt-1">{dashboardData?.store?.store_name || 'Vendor Dashboard'}</h1>
            <p className="text-gray-500">{shop}</p>
          </div>
          <button
            onClick={handleSyncProducts}
            disabled={syncing}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400"
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
            {syncing ? 'Syncing...' : 'Sync Products'}
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <StatCard
            icon={<Package className="w-6 h-6" />}
            label="Active Products"
            value={dashboardData?.stats.total_products || 0}
            accent="bg-blue-100 text-blue-600"
          />
          <StatCard
            icon={<DollarSign className="w-6 h-6" />}
            label="Lifetime Sales"
            value={`$${dashboardData?.store.total_sales?.toFixed(2) || '0.00'}`}
            accent="bg-green-100 text-green-600"
          />
          <StatCard
            icon={<TrendingUp className="w-6 h-6" />}
            label="Commission Rate"
            value={`${(dashboardData?.store.commission_rate * 100).toFixed(1)}%`}
            accent="bg-purple-100 text-purple-600"
          />
          <StatCard
            icon={<Shield className="w-6 h-6" />}
            label="Subscription"
            value={dashboardData?.store.subscription_status || 'not subscribed'}
            accent="bg-yellow-100 text-yellow-700"
          />
        </div>

        {/* Products */}
        <div className="bg-white rounded-2xl shadow-md p-6 mb-8 border border-gray-100">
          <h2 className="text-xl font-bold text-gray-900 mb-6">Your Products</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4">Product</th>
                  <th className="text-left py-3 px-4">Price</th>
                  <th className="text-left py-3 px-4">Quantity</th>
                  <th className="text-left py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody>
                {dashboardData?.products?.map((product: any) => (
                  <tr key={product.id} className="border-b hover:bg-gray-50">
                    <td className="py-3 px-4">{product.product_id}</td>
                    <td className="py-3 px-4">${product.price.toFixed(2)}</td>
                    <td className="py-3 px-4">{product.quantity}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${product.status === 'active'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-800'
                          }`}
                      >
                        {product.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Recent Orders */}
          <div className="bg-white rounded-2xl shadow-md p-6 border border-gray-100">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-900">Recent Orders</h2>
              <span className="text-sm text-gray-500">{dashboardData?.recent_orders?.length || 0} orders</span>
            </div>
            {dashboardData?.recent_orders?.length > 0 ? (
              <div className="space-y-4">
                {dashboardData.recent_orders.map((order: any) => (
                  <div key={order.id} className="border-b pb-4">
                    <div className="flex justify-between">
                      <span className="font-medium">Order #{order.id}</span>
                      <span className="text-blue-600 font-bold">
                        ${order.total_price.toFixed(2)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">
                      {new Date(order.created_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">No orders yet</p>
            )}
          </div>

          {/* Shippo Label */}
          <div className="bg-white rounded-2xl shadow-md p-6 border border-gray-100">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-900">Generate Shipping Label</h2>
              <Truck className="w-6 h-6 text-blue-600" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <input
                type="text"
                placeholder="Order ID"
                value={labelForm.order_id}
                onChange={(e) => setLabelForm({ ...labelForm, order_id: e.target.value })}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <input
                type="text"
                placeholder="Customer Name"
                value={labelForm.name}
                onChange={(e) => setLabelForm({ ...labelForm, name: e.target.value })}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <input
                type="text"
                placeholder="Street Address"
                value={labelForm.street}
                onChange={(e) => setLabelForm({ ...labelForm, street: e.target.value })}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <input
                type="text"
                placeholder="City"
                value={labelForm.city}
                onChange={(e) => setLabelForm({ ...labelForm, city: e.target.value })}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <select
                value={labelForm.province}
                onChange={(e) => setLabelForm({ ...labelForm, province: e.target.value })}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {['AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'NT', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT'].map((prov) => (
                  <option key={prov} value={prov}>
                    {prov}
                  </option>
                ))}
              </select>
              <input
                type="text"
                placeholder="Postal Code"
                value={labelForm.postal_code}
                onChange={(e) => setLabelForm({ ...labelForm, postal_code: e.target.value })}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <input
                type="number"
                min={1}
                value={labelCount}
                onChange={(e) => setLabelCount(parseInt(e.target.value) || 1)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="# of sealed items"
              />
            </div>
            <button
              onClick={handleLabelSubmit}
              disabled={labelLoading}
              className="mt-6 w-full bg-purple-600 text-white py-3 rounded-lg font-semibold hover:bg-purple-700 transition-colors disabled:bg-gray-400"
            >
              {labelLoading ? 'Submitting...' : 'Generate Shippo Label'}
            </button>
            <p className="text-xs text-gray-500 mt-3">
              Labels are created via Shippo with Canada Post / UPS / FedEx rates. A PDF link will be emailed to your vendor inbox.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function VendorDashboard() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    }>
      <VendorDashboardContent />
    </Suspense>
  )
}

function StatCard({ icon, label, value, accent }: { icon: ReactNode; label: string; value: string | number; accent: string }) {
  return (
    <div className="bg-white rounded-2xl shadow-md p-6 border border-gray-100">
      <div className="flex items-center gap-4">
        <div className={`w-12 h-12 rounded-full flex items-center justify-center ${accent}`}>
          {icon}
        </div>
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  )
}
