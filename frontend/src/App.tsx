import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'

function App() {
    const { user, loading } = useAuth()

    if (loading) {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100vh'
            }}>
                読み込み中...
            </div>
        )
    }

    return (
        <Routes>
            <Route
                path="/login"
                element={user ? <Navigate to="/dashboard" /> : <Login />}
            />
            <Route
                path="/dashboard"
                element={user ? <Dashboard /> : <Navigate to="/login" />}
            />
            <Route
                path="/"
                element={<Navigate to={user ? "/dashboard" : "/login"} />}
            />
        </Routes>
    )
}

export default App
