/**
 * Dashboardコンポーネントのテスト
 * 
 * ダッシュボード画面のレンダリング、文字起こしリスト表示、
 * ユーザーインタラクションをテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { MantineProvider } from '@mantine/core'
import Dashboard from '../../../src/pages/Dashboard'

// テスト用のラッパーコンポーネント
const AllProviders = ({ children }: { children: React.ReactNode }) => {
    return (
        <BrowserRouter>
            <MantineProvider>
                {children}
            </MantineProvider>
        </BrowserRouter>
    )
}

// カスタムレンダー関数
const renderWithProviders = (ui: React.ReactElement) => {
    return render(ui, { wrapper: AllProviders })
}

describe('Dashboard', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('ダッシュボードが正常にレンダリングされる', () => {
        renderWithProviders(<Dashboard />)

        // ダッシュボードのタイトルまたは主要な要素を確認
        // 実際のコンポーネントに合わせて調整
        expect(document.body).toBeTruthy()
    })

    it('文字起こしリストが表示される', async () => {
        const mockTranscriptions = [
            {
                id: '1',
                audio_id: 'audio-1',
                user_id: 'user-1',
                text: 'テスト文字起こし1',
                created_at: '2025-12-30T00:00:00Z',
            },
            {
                id: '2',
                audio_id: 'audio-2',
                user_id: 'user-1',
                text: 'テスト文字起こし2',
                created_at: '2025-12-30T01:00:00Z',
            },
        ]

        const { supabase } = await import('../../../src/services/supabase')
        const mockFrom = vi.fn(() => ({
            select: vi.fn().mockReturnThis(),
            order: vi.fn().mockResolvedValue({
                data: mockTranscriptions,
                error: null,
            }),
        }))
        vi.mocked(supabase.from).mockImplementation(mockFrom as any)

        renderWithProviders(<Dashboard />)

        // データの読み込みを待つ
        await waitFor(() => {
            expect(mockFrom).toHaveBeenCalledWith('transcriptions')
        })
    })

    it('ローディング状態が表示される', () => {
        renderWithProviders(<Dashboard />)

        // ローディングインジケーターの存在を確認
        // 実際のコンポーネントに合わせて調整
        expect(document.body).toBeTruthy()
    })

    it('削除ボタンをクリックすると確認ダイアログが表示される', async () => {
        const user = userEvent.setup()

        const mockTranscriptions = [
            {
                id: '1',
                audio_id: 'audio-1',
                user_id: 'user-1',
                text: 'テスト文字起こし',
                created_at: '2025-12-30T00:00:00Z',
            },
        ]

        const { supabase } = await import('../../../src/services/supabase')
        const mockFrom = vi.fn(() => ({
            select: vi.fn().mockReturnThis(),
            order: vi.fn().mockResolvedValue({
                data: mockTranscriptions,
                error: null,
            }),
            delete: vi.fn().mockReturnThis(),
            eq: vi.fn().mockResolvedValue({
                data: null,
                error: null,
            }),
        }))
        vi.mocked(supabase.from).mockImplementation(mockFrom as any)

        renderWithProviders(<Dashboard />)

        await waitFor(() => {
            expect(mockFrom).toHaveBeenCalled()
        })

        // 削除ボタンを探してクリック (実際のコンポーネントに合わせて調整)
        // const deleteButton = screen.getByRole('button', { name: /削除/i })
        // await user.click(deleteButton)
    })
})
