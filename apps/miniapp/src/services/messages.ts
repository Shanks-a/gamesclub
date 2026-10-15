import { request } from '../api/client'
import type { ApiConversation, ApiMessage } from '../api/types'
export function listConversations(){return request<ApiConversation[]>('/me/conversations/')}
export function listMessages(id:number){return request<ApiMessage[]>(`/me/conversations/${id}/messages/`)}
export function sendMessage(id:number, content:string, key:string){return request<ApiMessage>(`/me/conversations/${id}/send/`,{method:'POST',data:{content},header:{'Idempotency-Key':key}})}
