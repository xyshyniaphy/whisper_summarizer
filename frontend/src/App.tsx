import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import { NavBar } from './components/NavBar'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import { TranscriptionList } from './pages/TranscriptionList'
import { TranscriptionDetail } from './pages/TranscriptionDetail'

// Layout component for protected routes with navigation
function ProtectedLayout({ children }: { children: React.ReactNode }) {
    return (
        <>
            <NavBar />
            <main className="pt-16 min-h-screen bg-gray-50 dark:bg-gray-950">
                {children}
            </main>
        </>
    )
}

// Protected route wrapper component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
    const [{ user, loading }] = useAuth()

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-gray-600 dark:text-gray-400">Loading...</div>
            </div>
        )
    }

    if (!user) {
        return <Navigate to="/login" replace />
    }

    return <ProtectedLayout>{children}</ProtectedLayout>
}

function App() {
    const [{ user }] = useAuth()

    return (
        <Routes>
            {/* Public route - login */}
            <Route
                path="/login"
                element={user ? <Navigate to="/transcriptions" /> : <Login />}
            />

            {/* Protected routes - require authentication */}
            <Route
                path="/"
                element={
                    <ProtectedRoute>
                        <Navigate to="/transcriptions" />
                    </ProtectedRoute>
                }
            />
            <Route
                path="/transcriptions"
                element={
                    <ProtectedRoute>
                        <TranscriptionList />
                    </ProtectedRoute>
                }
            />
            <Route
                path="/transcriptions/:id"
                element={
                    <ProtectedRoute>
                        <TranscriptionDetail />
                    </ProtectedRoute>
                }
            />
            <Route
                path="/dashboard"
                element={
                    <ProtectedRoute>
                        <Dashboard />
                    </ProtectedRoute>
                }
            />
        </Routes>
    )
}

export default App
