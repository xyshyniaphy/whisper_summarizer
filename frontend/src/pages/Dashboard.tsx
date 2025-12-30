import { useAuth } from '../hooks/useAuth'
import { Button } from '../components/ui/Button'

export default function Dashboard() {
    const [{ user }, { signOut }] = useAuth()

    const handleSignOut = async () => {
        const result = await signOut()
        if (result.error) {
            console.error('ログアウトエラー:', result.error.message)
        }
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold mt-10">ダッシュボード</h1>

            <p className="mt-5">
                ようこそ、{user?.email} さん
            </p>

            <p className="mt-5 text-gray-500 dark:text-gray-400 text-sm">
                音声ファイルのアップロード機能は現在実装中です。
            </p>

            <Button className="mt-8" onClick={handleSignOut}>
                ログアウト
            </Button>
        </div>
    )
}
