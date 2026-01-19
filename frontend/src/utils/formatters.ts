/**
 * Format duration in seconds to human-readable format
 * @param seconds - Duration in seconds
 * @returns Formatted string (e.g., "5分钟", "1小时30分钟")
 */
export function formatDuration(seconds: number): string {
    if (seconds < 60) return `${seconds}秒`
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes}分钟`
    const hours = Math.floor(minutes / 60)
    const remainingMinutes = minutes % 60
    return remainingMinutes > 0 ? `${hours}小时${remainingMinutes}分钟` : `${hours}小时`
}

/**
 * Format ISO date string to locale string
 * @param isoDate - ISO date string
 * @returns Formatted date string (e.g., "2026/01/19 14:30")
 */
export function formatDate(isoDate: string): string {
    return new Date(isoDate).toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    })
}

/**
 * Get language label from language code
 * @param language - Language code (e.g., "zh", "en")
 * @returns Language label (e.g., "中文", "English")
 */
export function getLanguageLabel(language: string): string {
    const labels: Record<string, string> = {
        'zh': '中文',
        'en': 'English',
        'ja': '日本語',
        'ko': '한국어'
    }
    return labels[language] || language.toUpperCase()
}
