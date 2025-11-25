'use client';

import React, { useState } from 'react';
import axios from 'axios';

export default function SuperAdminPage() {
    const [adminKey, setAdminKey] = useState('');
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [activeTab, setActiveTab] = useState('products');
    const [affiliateLink, setAffiliateLink] = useState('');
    const [game, setGame] = useState('Pokemon');
    const [loading, setLoading] = useState(false);

    const handleAuth = () => {
        if (adminKey === 'admin123') {
            setIsAuthenticated(true);
        } else {
            alert('Invalid admin key');
        }
    };

    const handleAddProduct = async () => {
        if (!affiliateLink.includes('amazon.ca') && !affiliateLink.includes('amzn.to')) {
            alert('Please enter a valid Amazon.ca affiliate link');
            return;
        }

        setLoading(true);
        try {
            const apiUrl = 'https://geocheapest-api-426387254338.us-central1.run.app';
            console.log('Using API URL:', apiUrl);
            console.log('Sending request to:', `${apiUrl}/api/admin/products/amazon/scrape`);

            const response = await axios.post(`${apiUrl}/api/admin/products/amazon/scrape`, {
                affiliate_url: affiliateLink,
                game: game,
                admin_key: adminKey
            }, {
                timeout: 30000
            });

            console.log('Response:', response.data);
            const detectedGame = response.data.detected_game || game;
            alert(`Product added successfully!\n\nASIN: ${response.data.asin}\nTitle: ${response.data.title}\nPrice: $${response.data.price}\nCategory: ${detectedGame}`);
            setAffiliateLink('');
        } catch (error: any) {
            console.error('Full error:', error);
            console.error('Error response:', error.response);
            const errorMsg = error.response?.data?.detail || error.message || 'Failed to add product. Make sure the link is valid.';
            alert(`Error: ${errorMsg}`);
        } finally {
            setLoading(false);
        }
    };

    const triggerAmazonSync = async () => {
        try {
            await axios.post(`/api/admin/amazon/sync?admin_key=${adminKey}`);
            alert('Amazon sync triggered!');
        } catch (error) {
            alert('Failed to trigger sync');
        }
    };

    if (!isAuthenticated) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 flex items-center justify-center p-4">
                <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
                    <div className="text-center mb-8">
                        <h1 className="text-3xl font-bold text-gray-900 mb-2">🔐 Super Admin</h1>
                        <p className="text-gray-600">GeoCheapest Control Panel</p>
                    </div>
                    <input
                        type="password"
                        value={adminKey}
                        onChange={(e) => setAdminKey(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleAuth()}
                        placeholder="Enter Admin Key"
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent mb-4"
                    />
                    <button
                        onClick={handleAuth}
                        className="w-full bg-purple-600 hover:bg-purple-700 text-white font-bold py-3 px-4 rounded-lg transition-colors"
                    >
                        Access Control Panel
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-6 shadow-lg">
                <div className="max-w-7xl mx-auto flex justify-between items-center">
                    <div>
                        <h1 className="text-3xl font-bold">⚡ Super Admin Portal</h1>
                        <p className="text-purple-100">GeoCheapest Master Control</p>
                    </div>
                    <button
                        onClick={() => setIsAuthenticated(false)}
                        className="bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg transition-colors"
                    >
                        Logout
                    </button>
                </div>
            </div>

            <div className="bg-white border-b border-gray-200">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="flex gap-8">
                        {['products', 'vendors', 'system'].map((tab) => (
                            <button
                                key={tab}
                                onClick={() => setActiveTab(tab)}
                                className={`py-4 px-2 border-b-2 font-medium transition-colors ${activeTab === tab
                                    ? 'border-purple-600 text-purple-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700'
                                    }`}
                            >
                                {tab.charAt(0).toUpperCase() + tab.slice(1)}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto p-6">
                {activeTab === 'products' && (
                    <div className="bg-white rounded-xl shadow-lg p-6">
                        <h2 className="text-2xl font-bold mb-6">📦 Add Amazon Product</h2>
                        <p className="text-gray-600 mb-4">Paste your Amazon link - category is auto-detected!</p>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Amazon Affiliate Link
                                </label>
                                <input
                                    type="url"
                                    placeholder="https://amzn.to/xxxxx or https://amazon.ca/dp/xxxxx"
                                    value={affiliateLink}
                                    onChange={(e) => setAffiliateLink(e.target.value)}
                                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 text-sm"
                                />
                                <p className="text-xs text-gray-500 mt-1">
                                    Supports both full links and shortened amzn.to links
                                </p>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    TCG Game <span className="text-gray-400 text-xs">(Auto-detected)</span>
                                </label>
                                <select
                                    value={game}
                                    onChange={(e) => setGame(e.target.value)}
                                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                                >
                                    <option value="Pokemon">Pokemon</option>
                                    <option value="Magic: The Gathering">Magic: The Gathering</option>
                                    <option value="Yu-Gi-Oh">Yu-Gi-Oh</option>
                                    <option value="One Piece">One Piece</option>
                                    <option value="Lorcana">Lorcana</option>
                                    <option value="Flesh and Blood">Flesh and Blood</option>
                                    <option value="Digimon">Digimon</option>
                                </select>
                                <p className="text-xs text-gray-500 mt-1">
                                    Fallback if auto-detection fails
                                </p>
                            </div>
                        </div>

                        <button
                            onClick={handleAddProduct}
                            disabled={loading}
                            className="mt-6 w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 text-white font-bold py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
                        >
                            {loading ? (
                                <>
                                    <span className="animate-spin">⏳</span>
                                    <span>Fetching Product Data...</span>
                                </>
                            ) : (
                                <>
                                    <span>🚀</span>
                                    <span>Add Product</span>
                                </>
                            )}
                        </button>
                    </div>
                )}

                {activeTab === 'system' && (
                    <div className="bg-white rounded-xl shadow-lg p-6">
                        <h2 className="text-2xl font-bold mb-4">🔄 Amazon Sync</h2>
                        <p className="text-gray-600 mb-4">Trigger automatic Amazon product sync (requires RapidAPI key)</p>
                        <button
                            onClick={triggerAmazonSync}
                            className="bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-lg transition-colors"
                        >
                            Trigger Amazon Sync Now
                        </button>
                    </div>
                )}

                {activeTab === 'vendors' && (
                    <div className="bg-white rounded-xl shadow-lg p-6">
                        <h2 className="text-2xl font-bold mb-4">🏪 Vendor Management</h2>
                        <p className="text-gray-600">Vendor oversight and management tools coming soon...</p>
                    </div>
                )}
            </div>
        </div>
    );
}
