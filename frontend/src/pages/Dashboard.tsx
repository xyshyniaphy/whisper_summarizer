import { Container, Title, Button, Text } from '@mantine/core'
import { useAuth } from '../hooks/useAuth'

export default function Dashboard() {
    const { user, signOut } = useAuth()

    const handleSignOut = async () => {
        try {
            await signOut()
        } catch (error) {
            console.error('ログアウトエラー:', error)
        }
    }

    return (
        <Container>
            <Title order={1} mt={40}>ダッシュボード</Title>

            <Text mt={20}>
                ようこそ、{user?.email} さん
            </Text>

            <Text mt={20} c="dimmed">
                音声ファイルのアップロード機能は現在実装中です。
            </Text>

            <Button mt={30} onClick={handleSignOut}>
                ログアウト
            </Button>
        </Container>
    )
}
