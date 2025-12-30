import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import { TranscriptionList } from './pages/TranscriptionList'
import { TranscriptionDetail } from './pages/TranscriptionDetail'

function App() {
    const { user, loading } = useAuth()

    // Auth loading state is less critical now as we allow anonymous access to main features
    // but we can still keep it for the login route logic if needed.

    return (
        <Routes>
            {/* Public Routes for Transcription Feature */}
            <Route path="/transcriptions" element={<TranscriptionList />} />
            <Route path="/transcriptions/:id" element={<TranscriptionDetail />} />

            {/* Redirect root to transcriptions for now */}
            <Route path="/" element={<Navigate to="/transcriptions" />} />

            {/* Auth Routes (preserved) */}
            <Route
                path="/login"
                element={user ? <Navigate to="/dashboard" /> : <Login />}
            />
            <Route
                path="/dashboard"
                element={user ? <Dashboard /> : <Navigate to="/login" />}
            />
        </Routes>
    )
}

export default App
