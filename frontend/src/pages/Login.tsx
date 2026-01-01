import { useState } from 'react'
import { GoogleButton } from '../components/GoogleButton'

export default function Login() {
    const [error, setError] = useState('')
    const [googleLoading, setGoogleLoading] = useState(false)

    const handleGoogleSignIn = async () => {
        setError('')
        setGoogleLoading(true)

        try {
            const { supabase } = await import('../services/supabase')
            const { error } = await supabase.auth.signInWithOAuth({
                provider: 'google',
                options: {
                    queryParams: {
                        access_type: 'offline',
                        prompt: 'consent',
                    },
                    scopes: 'email',
                },
            })

            if (error) {
                setError(error.message || 'Google登录失败')
                setGoogleLoading(false)
            }
            // If successful, user will be redirected to Google
            // and then back to the app
        } catch (err: any) {
            setError(err.message || '发生意外错误')
            setGoogleLoading(false)
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
            <div className="w-full max-w-md">
                <h1 className="text-3xl font-bold text-center mb-2">
                    Whisper Summarizer
                </h1>
                <p className="text-gray-600 dark:text-gray-400 text-center text-sm mb-8">
                    使用 Google 账号登录
                </p>

                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-8">
                    {error && (
                        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded">
                            <p className="text-red-600 dark:text-red-400 text-sm">
                                {error}
                            </p>
                        </div>
                    )}

                    <GoogleButton
                        onClick={handleGoogleSignIn}
                        disabled={googleLoading}
                        loading={googleLoading}
                    />

                    <p className="text-gray-500 dark:text-gray-400 text-xs text-center mt-6">
                        点击上方按钮使用 Google OAuth 登录
                    </p>
                </div>
            </div>
        </div>
    )
}
