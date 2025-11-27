'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { getApiUrl } from '@/lib/api'

interface User {
    email: string
    full_name?: string
    role: 'admin' | 'vendor' | 'user'
}

interface AuthContextType {
    user: User | null
    token: string | null
    loading: boolean
    login: (token: string, role: string) => void
    logout: () => void
}

const AuthContext = createContext<AuthContextType>({
    user: null,
    token: null,
    loading: true,
    login: () => { },
    logout: () => { },
})

export const useAuth = () => useContext(AuthContext)

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
    const [user, setUser] = useState<User | null>(null)
    const [token, setToken] = useState<string | null>(null)
    const [loading, setLoading] = useState(true)
    const router = useRouter()
    const apiBase = getApiUrl()

    useEffect(() => {
        const initAuth = async () => {
            const storedToken = localStorage.getItem('token')
            if (storedToken) {
                setToken(storedToken)
                try {
                    // Verify token and get user details
                    const response = await axios.get(`${apiBase}/api/users/me`, {
                        headers: { Authorization: `Bearer ${storedToken}` }
                    })
                    const userData = response.data
                    // Map backend fields to User interface
                    setUser({
                        email: userData.email,
                        full_name: userData.full_name,
                        role: userData.is_superuser ? 'admin' : userData.is_vendor ? 'vendor' : 'user'
                    })
                } catch (error) {
                    console.error('Token verification failed:', error)
                    localStorage.removeItem('token')
                    setToken(null)
                }
            }
            setLoading(false)
        }
        initAuth()
    }, [apiBase])

    const login = (newToken: string, role: string) => {
        localStorage.setItem('token', newToken)
        setToken(newToken)

        // Fetch user details immediately
        axios.get(`${apiBase}/api/users/me`, {
            headers: { Authorization: `Bearer ${newToken}` }
        }).then(res => {
            const userData = res.data
            setUser({
                email: userData.email,
                full_name: userData.full_name,
                role: userData.is_superuser ? 'admin' : userData.is_vendor ? 'vendor' : 'user'
            })

            if (role === 'admin') router.push('/admin/dashboard')
            else if (role === 'vendor') router.push('/vendor/dashboard')
            else router.push('/')
        }).catch(err => {
            console.error("Failed to fetch user profile after login", err)
        })
    }

    const logout = () => {
        localStorage.removeItem('token')
        setToken(null)
        setUser(null)
        router.push('/login')
    }

    return (
        <AuthContext.Provider value={{ user, token, loading, login, logout }}>
            {children}
        </AuthContext.Provider>
    )
}
