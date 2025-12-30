import { useState } from 'react'
import { TextInput, PasswordInput, Button, Paper, Title, Text, Container } from '@mantine/core'
import { useAuth } from '../hooks/useAuth'

export default function Login() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [isSignUp, setIsSignUp] = useState(false)
    const [fullName, setFullName] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    const { signIn, signUp } = useAuth()

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            const result = isSignUp
                ? await signUp(email, password, fullName)
                : await signIn(email, password)

            if (result.error) {
                setError(result.error.message || 'エラーが発生しました')
            }
            // If successful, the auth state change will trigger a redirect via App.tsx
        } catch (err: any) {
            setError(err.message || '予期しないエラーが発生しました')
        } finally {
            setLoading(false)
        }
    }

    return (
        <Container size={420} my={40}>
            <Title ta="center">
                Whisper Summarizer
            </Title>
            <Text c="dimmed" size="sm" ta="center" mt={5}>
                {isSignUp ? '新規アカウント作成' : 'ログイン'}
            </Text>

            <Paper withBorder shadow="md" p={30} mt={30} radius="md">
                <form onSubmit={handleSubmit}>
                    {isSignUp && (
                        <TextInput
                            label="氏名"
                            placeholder="山田 太郎"
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                            mb="md"
                        />
                    )}

                    <TextInput
                        label="メールアドレス"
                        placeholder="you@example.com"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        mb="md"
                    />

                    <PasswordInput
                        label="パスワード"
                        placeholder="パスワード"
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        mb="md"
                    />

                    {error && (
                        <Text c="red" size="sm" mb="md">
                            {error}
                        </Text>
                    )}

                    <Button fullWidth mt="xl" type="submit" loading={loading}>
                        {isSignUp ? 'サインアップ' : 'ログイン'}
                    </Button>
                </form>

                <Text c="dimmed" size="sm" ta="center" mt={20}>
                    {isSignUp ? 'アカウントをお持ちですか？' : 'アカウントをお持ちでないですか？'}
                    {' '}
                    <Text
                        component="a"
                        size="sm"
                        style={{ cursor: 'pointer', color: '#228be6' }}
                        onClick={() => setIsSignUp(!isSignUp)}
                    >
                        {isSignUp ? 'ログイン' : 'サインアップ'}
                    </Text>
                </Text>
            </Paper>
        </Container>
    )
}
