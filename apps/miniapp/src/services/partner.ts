import { request } from '../api/client'
import type { ApiPartnerApplication, ApiOrder } from '../api/types'
export function submitApplication(game:number, reason:string){return request<ApiPartnerApplication>('/me/partner-application/',{method:'POST',data:{game,reason}})}
export function listApplications(){return request<ApiPartnerApplication[]>('/me/partner-application/')}
export function listPartnerOrders(){return request<ApiOrder[]>('/me/partner/orders/')}
export function partnerAction(id:number, action:'accept'|'reject'|'start'|'complete', key:string){return request<ApiOrder>(`/me/partner/orders/${id}/${action}/`,{method:'POST',data:{},header:{'Idempotency-Key':key}})}
