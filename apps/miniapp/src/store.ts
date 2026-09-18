import { reactive } from 'vue'
import { seedOrders, changeDemoOrder, products, type DemoOrder } from './domain'
const KEY = 'gamesclub-ui-demo-v1'
export const demo = reactive({ loggedIn:false, favorites:['duo'] as string[], orders:seedOrders.map(o=>({...o})), read:[] as string[], drafts:{} as Record<string,string> })
export function restore() {
 try {
  const saved = uni.getStorageSync(KEY)
  if (!saved || saved.version !== 1) return
  demo.loggedIn = saved.loggedIn === true
  if (Array.isArray(saved.favorites)) demo.favorites = saved.favorites.filter((id: unknown) => products.some(p=>p.id===id))
  // Order/session mutations deliberately stay in memory; never restore business state as authoritative.
 } catch { /* A disabled device store must not prevent browsing. */ }
}
export function persist() { try { uni.setStorageSync(KEY, {version:1, loggedIn:demo.loggedIn, favorites:demo.favorites}) } catch { uni.showToast({ title:'设备存储不可用，本次操作仅在当前会话有效', icon:'none' }) } }
export function loginDemo() { demo.loggedIn=true; persist() }
export function logoutDemo() { demo.loggedIn=false; demo.drafts={}; demo.read=[]; demo.orders=seedOrders.map(o=>({...o})); demo.favorites=['duo']; persist() }
export function toggleFavorite(id: string) { if (!products.some(p=>p.id===id)) return; demo.favorites=demo.favorites.includes(id)?demo.favorites.filter(v=>v!==id):[...demo.favorites,id]; persist() }
export function actOrder(id: string, action: Parameters<typeof changeDemoOrder>[1]) {
 if (!demo.loggedIn) throw new Error('请先进入演示登录')
 const index=demo.orders.findIndex(o=>o.id===id)
 if (index<0) throw new Error('订单不存在')
 demo.orders[index]=changeDemoOrder(demo.orders[index],action)
}
export function createDemoOrder(productId: string, quantity: number) {
 if (!demo.loggedIn || !products.some(p=>p.id===productId) || !Number.isInteger(quantity) || quantity<1 || quantity>5) throw new Error('订单信息无效')
 const order: DemoOrder={id:`DEMO-${Date.now()}`,productId,quantity,tab:'待付款'}
 demo.orders.unshift(order);return order
}
