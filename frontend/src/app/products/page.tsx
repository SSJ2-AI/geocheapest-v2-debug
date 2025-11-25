'use client';

import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface Product {
    id: string;
    name: string;
    category: string;
    image_url: string;
    best_price?: number;
    source_name?: string;
    in_stock?: boolean;
    rating?: number;
    review_count?: number;
    affiliate_url?: string;
    asin?: string;
}

export default function ProductsPage() {
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchProducts();
    }, []);

    const fetchProducts = async () => {
        try {
            const apiUrl = 'https://geocheapest-api-426387254338.us-central1.run.app';
            const response = await axios.get(`${apiUrl}/api/products`);
            setProducts(response.data.products || []);
        } catch (err: any) {
            setError('Failed to load products');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 flex items-center justify-center">
                <div className="text-white text-2xl">Loading products...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 p-8">
            <div className="max-w-7xl mx-auto">
                <h1 className="text-5xl font-bold text-white mb-8 text-center">
                    GeoCheapest Products
                </h1>

                {error && (
                    <div className="bg-red-500/20 border border-red-500 text-white p-4 rounded-lg mb-6">
                        {error}
                    </div>
                )}

                {products.length === 0 ? (
                    <div className="text-center text-white text-xl">
                        No products found. Add some products via the Super Admin portal!
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                        {products.map((product) => (
                            <div
                                key={product.id}
                                className="bg-white/10 backdrop-blur-lg rounded-xl p-6 border border-white/20 hover:border-white/40 transition-all hover:scale-105"
                            >
                                {product.image_url && (
                                    <img
                                        src={product.image_url}
                                        alt={product.name}
                                        className="w-full h-48 object-contain mb-4 rounded-lg bg-white/5"
                                    />
                                )}
                                <h3 className="text-white font-semibold text-lg mb-2 line-clamp-2 min-h-[56px]">
                                    {product.name}
                                </h3>

                                <div className="flex items-center gap-2 mb-2">
                                    <span className="text-blue-300 text-sm font-medium px-2 py-1 bg-blue-500/20 rounded">
                                        {product.category}
                                    </span>
                                    {product.in_stock !== undefined && (
                                        <span className={`text-xs px-2 py-1 rounded ${product.in_stock ? 'bg-green-500/30 text-green-300' : 'bg-red-500/30 text-red-300'}`}>
                                            {product.in_stock ? 'In Stock' : 'Out of Stock'}
                                        </span>
                                    )}
                                </div>

                                {product.rating && product.rating > 0 && (
                                    <div className="flex items-center gap-2 mb-2">
                                        <div className="flex text-yellow-400">
                                            {[...Array(5)].map((_, i) => (
                                                <span key={i}>{i < Math.floor(product.rating!) ? '★' : '☆'}</span>
                                            ))}
                                        </div>
                                        <span className="text-gray-300 text-sm">
                                            {product.rating.toFixed(1)}
                                        </span>
                                        {product.review_count && product.review_count > 0 && (
                                            <span className="text-gray-400 text-xs">
                                                ({product.review_count.toLocaleString()} reviews)
                                            </span>
                                        )}
                                    </div>
                                )}

                                <div className="flex items-center justify-between mt-4">
                                    {product.best_price !== undefined && product.best_price > 0 ? (
                                        <span className="text-green-400 font-bold text-2xl">
                                            ${product.best_price.toFixed(2)}
                                        </span>
                                    ) : (
                                        <span className="text-gray-400 text-sm">Price unavailable</span>
                                    )}
                                </div>

                                {product.source_name && (
                                    <div className="mt-2 text-xs text-gray-300">
                                        From: {product.source_name}
                                    </div>
                                )}

                                {product.affiliate_url && (
                                    <a
                                        href={product.affiliate_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="mt-4 w-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-bold py-3 px-4 rounded-lg transition-all flex items-center justify-center gap-2"
                                    >
                                        <span>🛒</span>
                                        <span>Buy Now</span>
                                    </a>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
