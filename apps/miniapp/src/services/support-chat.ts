import { request } from '../api/client'
export interface SupportMessage {id:number;content:string;from_staff:boolean;sender_name:string;read_at:string|null;created_at:string}
export interface SupportThread {id:number;name:string;role:string;order_no:string;updated_at:string;unread_count:number;reply_state:string;last_message:SupportMessage|null}
export interface SupportDetail extends SupportThread {messages:SupportMessage[]}
export const listSupportThreads=()=>request<SupportThread[]>('/me/support-conversations/')
export const openSupportThread=(order_no='')=>request<{id:number}>('/me/support-conversations/',{method:'POST',data:{order_no}})
export const getSupportThread=(id:number)=>request<SupportDetail>(`/me/support-conversations/${id}/`)
export const sendSupportMessage=(id:number,content:string,client_key:string)=>request<SupportMessage>(`/me/support-conversations/${id}/`,{method:'POST',data:{content,client_key}})
// Retry identity only; never used for authentication.
export const messageKey=()=> 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,c=>{const r=Math.floor(Math.random()*16);return(c==='x'?r:(r&3)|8).toString(16)})
