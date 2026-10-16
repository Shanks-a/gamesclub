import { request } from '../api/client'
export interface SupportConfig { mode:'disabled'|'wechat'|'enterprise'; corp_id:string; url:string; notice:string }
export function getSupportConfig(){return request<SupportConfig>('/support/')}
