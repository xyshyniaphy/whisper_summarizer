import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Button } from '../components/ui/Button'
import { Card, CardContent } from '../components/ui/Card'
import { GoogleButton } from '../components/GoogleButton'

export default function Login() {
    const navigate = useNavigate()
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [isSignUp, setIsSignUp] = useState(false)
    const [fullName, setFullName] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const [googleLoading, setGoogleLoading] = useState(false)

    const [, { signIn, signUp, signInWithGoogle }] = useAuth()

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            const result = isSignUp
                ? await signUp(email, password, fullName)
                : await signIn(email, password)

            if (result.error) {
                setError(result.error.message || '发生错误')
            } else if (result.user) {
                // 成功后导航到转录列表
                navigate('/transcriptions')
            }
        } catch (err: any) {
            setError(err.message || '发生意外错误')
        } finally {
            setLoading(false)
        }
    }

    const handleGoogleSignIn = async () => {
        setError('')
        setGoogleLoading(true)

        try {
            const { error } = await signInWithGoogle()
            if (error) {
                setError(error.message || 'Google登录失败')
                setGoogleLoading(false)
            }
            // If successful, user will be redirected to Google
            // and then back to the app, so we don't setGoogleLoading(false) here
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
                    {isSignUp ? '创建新账户' : '登录'}
                </p>

                <Card>
                    <CardContent className="pt-6">
                        <form onSubmit={handleSubmit} className="space-y-4">
                            {isSignUp && (
                                <div>
                                    <label className="block text-sm font-medium mb-1">
                                        姓名
                                    </label>
                                    <input
                                        type="text"
                                        placeholder="张三"
                                        value={fullName}
                                        onChange={(e) => setFullName(e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                    />
                                </div>
                            )}

                            <div>
                                <label className="block text-sm font-medium mb-1">
                                    电子邮箱
                                </label>
                                <input
                                    type="email"
                                    placeholder="you@example.com"
                                    required
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-1">
                                    密码
                                </label>
                                <input
                                    type="password"
                                    placeholder="密码"
                                    required
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                />
                            </div>

                            {error && (
                                <p className="text-red-600 text-sm">
                                    {error}
                                </p>
                            )}

                            <Button type="submit" className="w-full" disabled={loading || googleLoading}>
                                {loading ? '处理中...' : (isSignUp ? '注册' : '登录')}
                            </Button>
                        </form>

                        {/* Divider */}
                        <div className="relative my-6">
                            <div className="absolute inset-0 flex items-center">
                                <div className="w-full border-t border-gray-300 dark:border-gray-600"></div>
                            </div>
                            <div className="relative flex justify-center text-sm">
                                <span className="px-2 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                                    或
                                </span>
                            </div>
                        </div>

                        {/* Google OAuth Button */}
                        <GoogleButton
                            onClick={handleGoogleSignIn}
                            disabled={loading || googleLoading}
                            loading={googleLoading}
                        />

                        <p className="text-gray-600 dark:text-gray-400 text-sm text-center mt-5">
                            {isSignUp ? '已有账户？' : '没有账户？'}
                            {' '}
                            <button
                                type="button"
                                className="text-primary-600 hover:underline"
                                onClick={() => setIsSignUp(!isSignUp)}
                            >
                                {isSignUp ? '登录' : '注册'}
                            </button>
                        </p>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
