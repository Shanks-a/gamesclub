import { request } from '../api/client'
import type { ApiOrder } from '../api/types'
export function createOrder(productId:string,quantity:number,version:number,key:string,appointment?:{date:string;slot:string}){return request<ApiOrder>('/me/orders/',{method:'POST',data:{product_id:Number(productId),quantity,expected_product_version:version,...(appointment?.date?{appointment_date:appointment.date,appointment_slot:appointment.slot}:{})},header:{'Idempotency-Key':key}})}
export function listOrders(){return request<ApiOrder[]>('/me/orders/')}
export function mockPay(id:number,key:string){return request<ApiOrder>(`/me/orders/${id}/mock-pay/`,{method:'POST',data:{},header:{'Idempotency-Key':key}})}
export function cancelOrder(id:number,key:string){return request<ApiOrder>(`/me/orders/${id}/cancel/`,{method:'POST',data:{},header:{'Idempotency-Key':key}})}
export function confirmOrder(id:number,key:string){return request<ApiOrder>(`/me/orders/${id}/confirm/`,{method:'POST',data:{},header:{'Idempotency-Key':key}})}
// 陪玩工作台
export function listPartnerOrders(){return request<ApiOrder[]>('/me/partner/orders/')}
export function partnerAccept(id:number,key:string){return request<ApiOrder>(`/me/partner/orders/${id}/accept/`,{method:'POST',data:{},header:{'Idempotency-Key':key}})}
export function partnerReject(id:number,key:string){return request<ApiOrder>(`/me/partner/orders/${id}/reject/`,{method:'POST',data:{},header:{'Idempotency-Key':key}})}
export function partnerStart(id:number,key:string){return request<ApiOrder>(`/me/partner/orders/${id}/start/`,{method:'POST',data:{},header:{'Idempotency-Key':key}})}
export function partnerComplete(id:number,key:string){return request<ApiOrder>(`/me/partner/orders/${id}/complete/`,{method:'POST',data:{},header:{'Idempotency-Key':key}})}
