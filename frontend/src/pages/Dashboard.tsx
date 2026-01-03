/**
 * Admin Dashboard with sidebar navigation
 * Only accessible to admin users
 */

import { useAtom } from 'jotai'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { dashboardActiveTabAtom, persistSidebarCollapseAtom, type DashboardTab } from '../atoms/dashboard'
import { useAuth } from '../hooks/useAuth'
import { ChevronRight, ChevronLeft, Users, FolderOpen, Music, Loader2 } from 'lucide-react'
import { UserManagementTab } from '../components/dashboard/UserManagementTab'
import { ChannelManagementTab } from '../components/dashboard/ChannelManagementTab'
import { AudioManagementTab } from '../components/dashboard/AudioManagementTab'

interface SidebarItemProps {
  tab: DashboardTab
  activeTab: DashboardTab
  onClick: () => void
  collapsed: boolean
  label: string
  icon: React.ReactNode
}

function SidebarItem({ tab, activeTab, onClick, collapsed, label, icon }: SidebarItemProps) {
  const isActive = activeTab === tab

  return (
    <button
      onClick={onClick}
      className={`
        w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors
        ${isActive
          ? 'bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-200'
          : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300'
        }
      `}
      title={collapsed ? label : undefined}
    >
      {icon}
      {!collapsed && <span className="font-medium">{label}</span>}
    </button>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [{ user, is_admin, loading }] = useAuth()
  const [activeTab, setActiveTab] = useAtom(dashboardActiveTabAtom)
  const [sidebarCollapsed, setSidebarCollapsed] = useAtom(persistSidebarCollapseAtom)

  // Redirect non-admins to home page
  useEffect(() => {
    if (!loading && !is_admin) {
      navigate('/', { replace: true })
    }
  }, [loading, is_admin, navigate])

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

  // Don't render if not admin (will redirect via useEffect)
  if (!is_admin) {
    return null
  }

  const tabs: { key: DashboardTab; label: string; icon: React.ReactNode }[] = [
    { key: 'users', label: '用户管理', icon: <Users className="w-5 h-5" /> },
    { key: 'channels', label: '频道管理', icon: <FolderOpen className="w-5 h-5" /> },
    { key: 'audio', label: '音频管理', icon: <Music className="w-5 h-5" /> },
  ]

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed)
  }

  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Sidebar */}
      <aside className={`
        fixed left-0 top-16 h-[calc(100vh-4rem)] bg-white dark:bg-gray-800 border-r dark:border-gray-700
        transition-all duration-300 ease-in-out z-40
        ${sidebarCollapsed ? 'w-16' : 'w-64'}
      `}>
        <div className="flex flex-col h-full">
          {/* Collapse button */}
          <div className="flex items-center justify-between p-4 border-b dark:border-gray-700">
            {!sidebarCollapsed && (
              <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                管理面板
              </h2>
            )}
            <button
              onClick={toggleSidebar}
              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              aria-label={sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'}
            >
              {sidebarCollapsed ? (
                <ChevronRight className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              ) : (
                <ChevronLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              )}
            </button>
          </div>

          {/* Navigation items */}
          <nav className="flex-1 p-3 space-y-2 overflow-y-auto">
            {tabs.map((tab) => (
              <SidebarItem
                key={tab.key}
                tab={tab.key}
                activeTab={activeTab}
                onClick={() => setActiveTab(tab.key)}
                collapsed={sidebarCollapsed}
                label={tab.label}
                icon={tab.icon}
              />
            ))}
          </nav>

          {/* User info */}
          <div className={`
            p-4 border-t dark:border-gray-700
            ${sidebarCollapsed ? 'text-center' : ''}
          `}>
            <div className={`
              ${sidebarCollapsed ? 'w-10 h-10 mx-auto' : 'flex items-center gap-3'}
              rounded-full bg-primary-100 dark:bg-primary-900
              text-primary-700 dark:text-primary-200
              font-semibold
            `}>
              {sidebarCollapsed ? (
                <span className="text-lg">
                  {user?.email?.[0].toUpperCase()}
                </span>
              ) : (
                <>
                  <span className="w-10 h-10 flex items-center justify-center rounded-full bg-primary-200 dark:bg-primary-800">
                    {user?.email?.[0].toUpperCase()}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{user?.email}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">管理员</p>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className={`
        flex-1 transition-all duration-300 ease-in-out
        ${sidebarCollapsed ? 'ml-16' : 'ml-64'}
      `}>
        <div className="container mx-auto px-4 py-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              {tabs.find(t => t.key === activeTab)?.label || '仪表板'}
            </h1>
            <p className="mt-2 text-gray-600 dark:text-gray-400">
              管理用户、频道和音频内容
            </p>
          </div>

          {/* Tab content */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            {activeTab === 'users' && <UserManagementTab />}
            {activeTab === 'channels' && <ChannelManagementTab />}
            {activeTab === 'audio' && <AudioManagementTab />}
          </div>
        </div>
      </main>
    </div>
  )
}
