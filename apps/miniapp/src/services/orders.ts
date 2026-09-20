import { request } from '../api/client'
import type { ApiOrder } from '../api/types'
export function createOrder(productId:string,quantity:number,version:number,key:string){return request<ApiOrder>('/me/orders/',{method:'POST',data:{product_id:Number(productId),quantity,expected_product_version:version},header:{'Idempotency-Key':key}})}
export function listOrders(){return request<ApiOrder[]>('/me/orders/')}
export function mockPay(id:number,key:string){return request<ApiOrder>(`/me/orders/${id}/mock-pay/`,{method:'POST',data:{},header:{'Idempotency-Key':key}})}
export function cancelOrder(id:number){return request<ApiOrder>(`/me/orders/${id}/cancel/`,{method:'POST',data:{}})}
