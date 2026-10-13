import { request } from '../api/client'
import type { ApiOrder, ApiReview, ApiAfterSaleCase } from '../api/types'
export function createOrder(productId:string,quantity:number,version:number,key:string,appointment?:{date:string;slot:string}){return request<ApiOrder>('/me/orders/',{method:'POST',data:{product_id:Number(productId),quantity,expected_product_version:version,...(appointment?.date?{appointment_date:appointment.date,appointment_slot:appointment.slot}:{})},header:{'Idempotency-Key':key}})}
export function listOrders(){return request<ApiOrder[]>('/me/orders/')}
export function mockPay(id:number,key:string){return request<ApiOrder>(`/me/orders/${id}/mock-pay/`,{method:'POST',data:{},header:{'Idempotency-Key':key}})}
export function cancelOrder(id:number,key:string){return request<ApiOrder>(`/me/orders/${id}/cancel/`,{method:'POST',data:{},header:{'Idempotency-Key':key}})}
export function confirmOrder(id:number,key:string){return request<ApiOrder>(`/me/orders/${id}/confirm/`,{method:'POST',data:{},header:{'Idempotency-Key':key}})}
export function submitReview(id:number,key:string,rating:number,content:string){return request<ApiReview>(`/me/orders/${id}/review/`,{method:'POST',data:{rating,content},header:{'Idempotency-Key':key}})}
export function applyAftersale(id:number,key:string,amountCents:number,reason:string){return request<ApiAfterSaleCase>(`/me/orders/${id}/aftersale/`,{method:'POST',data:{amount_cents:amountCents,reason},header:{'Idempotency-Key':key}})}
export function listAftersales(id:number){return request<ApiAfterSaleCase[]>(`/me/orders/${id}/aftersale/`)}
// 陪玩工作台
export function listPartnerOrders(){return request<ApiOrder[]>('/me/partner/orders/')}
export function partnerAccept(id:number,key:string){return request<ApiOrder>(`/me/partner/orders/${id}/accept/`,{method:'POST',data:{},header:{'Idempotency-Key':key}})}
export function partnerReject(id:number,key:string){return request<ApiOrder>(`/me/partner/orders/${id}/reject/`,{method:'POST',data:{},header:{'Idempotency-Key':key}})}
export function partnerStart(id:number,key:string){return request<ApiOrder>(`/me/partner/orders/${id}/start/`,{method:'POST',data:{},header:{'Idempotency-Key':key}})}
export function partnerComplete(id:number,key:string){return request<ApiOrder>(`/me/partner/orders/${id}/complete/`,{method:'POST',data:{},header:{'Idempotency-Key':key}})}
