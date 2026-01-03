/**
 * Pending Activation Page
 * Shows to users whose accounts are not yet activated by an administrator
 */

import { useAuth } from '../hooks/useAuth'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { Loader2, Clock, Mail, LogOut } from 'lucide-react'
import { Button } from '../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'

export default function PendingActivation() {
  const navigate = useNavigate()
  const [{ user, is_active, loading }, { signOut }] = useAuth()

  // Redirect to home if user is active
  useEffect(() => {
    if (!loading && is_active) {
      navigate('/', { replace: true })
    }
  }, [loading, is_active, navigate])

  const handleSignOut = async () => {
    const result = await signOut()
    if (result.error) {
      console.error('登出错误：', result.error.message)
    }
  }

  // Show loading state while checking auth
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-10 h-10 text-primary-600 animate-spin" />
          <p className="text-gray-600 dark:text-gray-400">加载中...</p>
        </div>
      </div>
    )
  }

  // Don't render if active (will redirect via useEffect)
  if (is_active) {
    return null
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-blue-50 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        <Card>
          <CardHeader className="text-center">
            <div className="w-16 h-16 bg-yellow-100 dark:bg-yellow-900 rounded-full flex items-center justify-center mx-auto mb-4">
              <Clock className="w-8 h-8 text-yellow-600 dark:text-yellow-400" />
            </div>
            <CardTitle className="text-2xl">账户待激活</CardTitle>
          </CardHeader>

          <CardContent className="space-y-6">
            <div className="text-center space-y-2">
              <p className="text-gray-700 dark:text-gray-300">
                您的账户 <span className="font-semibold">{user?.email}</span> 尚未激活。
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                请联系管理员激活您的账户。激活后即可使用所有功能。
              </p>
            </div>

            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 space-y-3">
              <div className="flex items-start gap-3">
                <Mail className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                <div className="text-sm">
                  <p className="font-medium text-blue-900 dark:text-blue-100">如何激活账户？</p>
                  <p className="text-blue-700 dark:text-blue-300 mt-1">
                    联系系统管理员并提供您的邮箱地址。管理员将在审核后激活您的账户。
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <Button
                onClick={() => navigate('/login')}
                variant="secondary"
                className="w-full"
              >
                返回登录页
              </Button>
              <Button
                onClick={handleSignOut}
                variant="ghost"
                className="w-full flex items-center justify-center gap-2"
              >
                <LogOut className="w-4 h-4" />
                退出登录
              </Button>
            </div>

            <p className="text-xs text-center text-gray-500 dark:text-gray-400">
              如有疑问，请联系技术支持。
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
