'use client'

import { useCartStore } from '@/store/cartStore'
import { ShoppingCart, Tag } from 'lucide-react'

interface Product {
  id: string
  name: string
  description: string
  category: string
  image_url: string
  best_price?: number
  source?: string
  source_name?: string
  in_stock?: boolean
  is_preorder?: boolean
  url?: string
}

export function ProductCard({ product }: { product: Product }) {
  const addItem = useCartStore((state) => state.addItem)
  const isInStock = product.in_stock ?? true
  const isPreorder = Boolean(product.is_preorder)

  const handleAddToCart = () => {
    addItem({
      product_id: product.id,
      name: product.name,
      price: product.best_price,
      quantity: 1,
      image_url: product.image_url,
    })
  }

  const isAffiliateLink = Boolean(
    product.url &&
    (
      product.source?.toLowerCase().includes('affiliate') ||
      product.source?.toLowerCase().includes('amazon') ||
      product.source?.toLowerCase().includes('ebay')
    )
  )

  const isAmazonPartner = isAffiliateLink && product.source_name?.toLowerCase().includes('amazon')

  return (
    <div className="bg-white rounded-lg shadow-md hover:shadow-xl transition-shadow duration-300 overflow-hidden group">
      <div className="relative">
        {product.url ? (
          <a href={product.url} target="_blank" rel="noopener noreferrer">
            <img
              src={product.image_url || '/placeholder-product.jpg'}
              alt={product.name}
              className="w-full h-64 object-cover group-hover:scale-105 transition-transform duration-300 cursor-pointer"
            />
          </a>
        ) : (
          <img
            src={product.image_url || '/placeholder-product.jpg'}
            alt={product.name}
            className="w-full h-64 object-cover group-hover:scale-105 transition-transform duration-300"
          />
        )}
        {isPreorder && (
          <span className="absolute top-2 left-2 bg-yellow-500 text-white px-3 py-1 rounded-full text-sm font-semibold">
            Pre-Order
          </span>
        )}
        {!isPreorder && product.source === 'affiliate' && (
          <span className="absolute top-2 left-2 bg-purple-600 text-white px-2 py-1 rounded text-xs font-medium">
            Partner Seller
          </span>
        )}
        <span className="absolute top-2 right-2 bg-blue-600 text-white px-3 py-1 rounded-full text-xs font-medium">
          {product.category}
        </span>
      </div>

      <div className="p-4">
        {product.url ? (
          <a href={product.url} target="_blank" rel="noopener noreferrer" className="block hover:text-blue-600 transition-colors">
            <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2 h-14">
              {product.name}
            </h3>
          </a>
        ) : (
          <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2 h-14">
            {product.name}
          </h3>
        )}

        <div className="flex items-center gap-2 mb-3">
          <Tag className="w-4 h-4 text-gray-500" />
          <span className="text-sm text-gray-600">{product.source_name || 'Partner Source'}</span>
        </div>

        <div className="flex items-center justify-between">
          <div>
            {product.best_price != null ? (
              <>
                <span className="text-2xl font-bold text-blue-600">
                  ${product.best_price.toFixed(2)}
                </span>
                <span className="text-sm text-gray-500 ml-1">CAD</span>
              </>
            ) : (
              <span className="text-sm text-gray-500">Price unavailable</span>
            )}
          </div>
          {/* Show affiliate "Buy" button if product has a URL and is from an affiliate source */}
          {isAffiliateLink ? (
            <a
              href={product.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
            >
              <ShoppingCart className="w-4 h-4" />
              {isAmazonPartner ? 'Buy from Amazon.ca' : `Buy on ${product.source_name || 'partner site'}`}
            </a>
          ) : (
            <button
              onClick={handleAddToCart}
              disabled={!isInStock && !isPreorder}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${isInStock || isPreorder
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }`}
            >
              <ShoppingCart className="w-4 h-4" />
              {isPreorder ? 'Pre-Order' : 'Add to Cart'}
            </button>
          )}
        </div>

        {!isInStock && !isPreorder && (
          <p className="text-red-500 text-sm mt-2 font-medium">Out of Stock</p>
        )}
      </div>
    </div>
  )
}
