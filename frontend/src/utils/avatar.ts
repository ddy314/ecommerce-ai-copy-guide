const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * 将相对头像地址解析为可访问的完整 URL。
 * 后端通常返回 `/uploads/avatars/xxx.jpg`，需要拼接 API_BASE。
 */
export function resolveAvatarUrl(url: string | undefined | null): string {
  if (!url) return ''
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  if (url.startsWith('/uploads/')) return `${API_BASE}${url}`
  return url
}
