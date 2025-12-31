import { useAuth } from '../hooks/useAuth'
import { Button } from '../components/ui/Button'

export default function Dashboard() {
    const [{ user }, { signOut }] = useAuth()

    const handleSignOut = async () => {
        const result = await signOut()
        if (result.error) {
            console.error('登出错误：', result.error.message)
        }
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold mt-10">仪表板</h1>

            <p className="mt-5">
                欢迎，{user?.email} 
            </p>

            <p className="mt-5 text-gray-500 dark:text-gray-400 text-sm">
                音频文件上传功能正在开发中。
            </p>

            <Button className="mt-8" onClick={handleSignOut}>
                退出登录
            </Button>
        </div>
    )
}
