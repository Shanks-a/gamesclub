import { BASE_URL, mediaUrl, request } from '../api/client'

export interface CommunityAuthor { id: number; nickname: string; avatar_url: string }
export interface CommunityImage { id: number; url: string }
export interface CommunityPost {
  id: number; game_id: number; author: CommunityAuthor; content: string; created_at: string
  images: CommunityImage[]; like_count: number; comment_count: number; liked: boolean; can_delete: boolean
}
export interface CommunityComment {
  id: number; author: CommunityAuthor; content: string; created_at: string; can_delete: boolean
}
export interface RankedPartner {
  id: number; rank: number; nickname: string; avatar_url: string; intro: string
  completed_orders: number; recent_orders: number
}
export type RankingSort = 'heat' | 'orders'
export interface Leaderboard {
  sort: RankingSort; generated_at: string; count: number; top_three: RankedPartner[]
  results: RankedPartner[]; next_offset: number | null
}
export const getPosts = (game: number, before?: number) => request<{results: CommunityPost[]; next_before: number | null}>(`/games/${game}/posts/${before ? `?before=${before}` : ''}`)
export const publishPost = (game: number, content: string, imageIds: number[], key: string) => request<CommunityPost>(`/games/${game}/posts/`, {method:'POST', data:{content, image_ids:imageIds}, header:{'Idempotency-Key':key}})
export const removePost = (id: number) => request<void>(`/community/posts/${id}/`, {method:'DELETE'})
export const setPostLike = (id: number, liked: boolean) => request<{liked: boolean; like_count: number}>(`/community/posts/${id}/like/`, {method:'PUT', data:{liked}})
export const getComments = (post: number, after?: number) => request<{results: CommunityComment[]; next_after: number | null}>(`/community/posts/${post}/comments/${after ? `?after=${after}` : ''}`)
export const publishComment = (post: number, content: string, key: string) => request<CommunityComment>(`/community/posts/${post}/comments/`, {method:'POST', data:{content}, header:{'Idempotency-Key':key}})
export const removeComment = (id: number) => request<void>(`/community/comments/${id}/`, {method:'DELETE'})
export const getLeaderboard = (game: number, sort: RankingSort, offset = 0) => request<Leaderboard>(`/games/${game}/leaderboard/?sort=${sort}&offset=${offset}`)

export function uploadCommunityImage(path: string): Promise<CommunityImage> {
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: `${BASE_URL}/community/images/`, filePath: path, name: 'file',
      header: {Authorization: `Bearer ${uni.getStorageSync('gamesclub-access-token') || ''}`},
      success(response) {
        try {
          const data = JSON.parse(response.data)
          if (response.statusCode >= 200 && response.statusCode < 300) resolve(data)
          else reject(new Error(data.error?.message || '图片上传失败，请重新选择'))
        } catch { reject(new Error('图片上传响应异常')) }
      },
      fail: () => reject(new Error('图片上传失败，请检查网络')),
    })
  })
}

export function previewImages(images: CommunityImage[], current: number) {
  uni.previewImage({urls: images.map(image => mediaUrl(image.url)), current})
}

export function communityTime(value: string) {
  const date = new Date(value)
  return `${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

// Reuse the same key for a retry, and start a new operation when the payload changes.
export function createSubmissionKey(prefix: string) {
  let previous = '', key = ''
  const getKey = (payload: string) => {
    if (payload !== previous || !key) {
      previous = payload
      key = `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`
    }
    return key
  }
  return Object.assign(getKey, {reset: () => { previous = ''; key = '' }})
}
