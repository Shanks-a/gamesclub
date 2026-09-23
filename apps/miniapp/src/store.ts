import { reactive } from 'vue'
import { clearAccessToken, request } from './api/client'
import { seedOrders, changeDemoOrder, products, conversations, type DemoOrder, type ChatMessage } from './domain'
const KEY = 'gamesclub-local-data-v2'
const defaultMessages:Record<string,ChatMessage[]> = Object.fromEntries(conversations.filter(c=>c.id!=='notice').map(c=>[c.id,[{id:`${c.id}-0`,mine:false,text:c.text,time:c.time}]]))
export const demo = reactive({ loggedIn:false, favorites:[] as string[], orders:[] as DemoOrder[], read:[] as string[], drafts:{} as Record<string,string>, messages:defaultMessages })
export function restore() {
 try {
  const saved = uni.getStorageSync(KEY)
  if (!saved || saved.version !== 2) return
  demo.loggedIn = false
  if (saved.messages && typeof saved.messages === 'object') demo.messages = saved.messages
 } catch { /* A disabled device store must not prevent browsing. */ }
}
export function persist() {
 try { uni.setStorageSync(KEY, {version:2, messages:demo.messages}) }
 catch { uni.showToast({ title:'设备存储不可用，本次操作仅在当前会话有效', icon:'none' }) }
}
export function loginDemo() { demo.loggedIn=true; persist() }
export function logoutDemo() { clearAccessToken(); demo.loggedIn=false; demo.favorites=[]; demo.orders=[]; demo.messages={}; demo.drafts={}; demo.read=[]; persist() }
export async function validateSession(){try{await request('/me/');demo.loggedIn=true}catch(e){logoutDemo();throw e}}
export function toggleFavorite(id: string) { if (!products.some(p=>p.id===id)) return; demo.favorites=demo.favorites.includes(id)?demo.favorites.filter(v=>v!==id):[...demo.favorites,id]; persist() }
export function actOrder(id: string, action: Parameters<typeof changeDemoOrder>[1]) {
 if (!demo.loggedIn) throw new Error('请先进入演示登录')
 const index=demo.orders.findIndex(o=>o.id===id)
 if (index<0) throw new Error('订单不存在')
 demo.orders[index]=changeDemoOrder(demo.orders[index],action)
 persist()
}
export function createDemoOrder(productId: string, quantity: number) {
 if (!demo.loggedIn || !products.some(p=>p.id===productId) || !Number.isInteger(quantity) || quantity<1 || quantity>5) throw new Error('订单信息无效')
 const order: DemoOrder={id:`DEMO-${Date.now()}`,productId,quantity,tab:'待付款'}
 demo.orders.unshift(order);persist();return order
}
export function appendMessage(conversationId:string, text:string) {
 const value=text.trim(); if(!value)return
 if(!demo.messages[conversationId]) demo.messages[conversationId]=[]
 demo.messages[conversationId].push({id:`${conversationId}-${Date.now()}`,mine:true,text:value,time:new Date().toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'})})
 persist()
}
