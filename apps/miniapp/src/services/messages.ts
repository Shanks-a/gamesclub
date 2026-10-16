import { request } from '../api/client'
import type { ApiConversation, ApiConversationDetail, ApiMessage } from '../api/types'
export function listConversations(){return request<ApiConversation[]>('/me/conversations/')}
export function listMessages(id:number){return request<ApiMessage[]>(`/me/conversations/${id}/messages/`)}
export function sendMessage(id:number, content:string, key:string){return request<ApiMessage>(`/me/conversations/${id}/send/`,{method:'POST',data:{content},header:{'Idempotency-Key':key}})}

export function getConversation(id:number){return request<ApiConversationDetail>(`/me/conversations/${id}/`)}
export function serviceProgress(id:number, action:'start'|'complete', version:number, key:string){return request(`/me/partner/orders/${id}/${action}/`,{method:'POST',data:{version},header:{'Idempotency-Key':key}})}
