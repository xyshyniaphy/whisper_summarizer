import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import { isE2ETestMode } from './utils/e2e'
import { NavBar } from './components/NavBar'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import PendingActivation from './pages/PendingActivation'
import { TranscriptionList } from './pages/TranscriptionList'
import { TranscriptionDetail } from './pages/TranscriptionDetail'
import { SharedTranscription } from './pages/SharedTranscription'

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
function ProtectedRoute({ children, requireAdmin = false }: { children: React.ReactNode; requireAdmin?: boolean }) {
    const [{ user, is_active, is_admin, loading }] = useAuth()

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-gray-600 dark:text-gray-400">Loading...</div>
            </div>
        )
    }

    // E2E test mode bypass: skip auth check when running E2E tests
    // Only activates on localhost with e2e-test-mode flag (defense-in-depth)
    if (isE2ETestMode()) {
        return <ProtectedLayout>{children}</ProtectedLayout>
    }

    if (!user) {
        return <Navigate to="/login" replace />
    }

    // Check if account is active (except for the pending activation page itself)
    if (!is_active) {
        return <Navigate to="/pending-activation" replace />
    }

    // Check admin requirement
    if (requireAdmin && !is_admin) {
        return <Navigate to="/transcriptions" replace />
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

            {/* Public route - shared transcription (no auth required) */}
            <Route path="/shared/:shareToken" element={<SharedTranscription />} />

            {/* Pending activation page - authenticated but inactive users */}
            <Route
                path="/pending-activation"
                element={<PendingActivation />}
            />

            {/* Protected routes - require authentication AND active account */}
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
                    <ProtectedRoute requireAdmin={true}>
                        <Dashboard />
                    </ProtectedRoute>
                }
            />
        </Routes>
    )
}

export default App
