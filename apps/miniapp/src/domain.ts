export type Game = '王者荣耀' | '和平精英' | '无畏契约' | '英雄联盟'
export const games: Game[] = ['王者荣耀', '和平精英', '无畏契约', '英雄联盟']
export interface Product { id: string; title: string; game: Game; price: number; original: number; art: number; tagline: string; version?: number }
export const products: Product[] = [
 { id:'duo', title:'双人默契上分', game:'王者荣耀', price:2900, original:3900, art:0, tagline:'默契配合，一起享受每一局' },
 { id:'chicken', title:'一起轻松吃鸡', game:'和平精英', price:2500, original:3500, art:1, tagline:'轻松交流，发现组队的快乐' },
 { id:'weekend', title:'周末欢乐五排', game:'王者荣耀', price:3500, original:4900, art:2, tagline:'叫上朋友，快乐开黑' },
 { id:'tactics', title:'战术默契双排', game:'无畏契约', price:3200, original:4500, art:3, tagline:'清晰报点，认真配合' },
 { id:'valley', title:'峡谷欢乐局', game:'英雄联盟', price:3900, original:4900, art:0, tagline:'轻松游戏，遇见新朋友' },
]
export const money = (cents: number) => (cents / 100).toFixed(2).replace(/\.00$/, '')
export function filterProducts(game: string, query = '', ascending?: boolean) {
 const q = query.trim().toLowerCase()
 const result = products.filter(p => (!game || game === '全部' || game === '推荐' || p.game === game) && `${p.title}${p.game}`.toLowerCase().includes(q))
 return ascending === undefined ? result : result.sort((a,b) => ascending ? a.price-b.price : b.price-a.price)
}
export const orderTabs = ['待付款','待发货','待收货','评价','退款/售后'] as const
export type OrderTab = typeof orderTabs[number]
// UI-only demonstration categories; not the backend order-state contract.
export interface DemoOrder { id: string; productId: string; quantity: number; tab: OrderTab; cancelled?: boolean; reviewed?: boolean }
export const seedOrders: DemoOrder[] = [
 { id:'DEMO-1001', productId:'duo', quantity:1, tab:'待付款' },
 { id:'DEMO-1002', productId:'chicken', quantity:1, tab:'待付款' },
 { id:'DEMO-1003', productId:'tactics', quantity:1, tab:'待发货' },
 { id:'DEMO-1004', productId:'weekend', quantity:1, tab:'待收货' },
 { id:'DEMO-1005', productId:'valley', quantity:1, tab:'评价' },
 { id:'DEMO-1006', productId:'duo', quantity:1, tab:'退款/售后' },
]
export function changeDemoOrder(order: DemoOrder, action: 'cancel' | 'pay' | 'receive' | 'review'): DemoOrder {
 if (order.cancelled) throw new Error('该演示订单已取消')
 if (action === 'cancel' && order.tab === '待付款') return {...order, cancelled:true}
 if (action === 'pay' && order.tab === '待付款') return {...order, tab:'待发货'}
 if (action === 'receive' && order.tab === '待收货') return {...order, tab:'评价'}
 if (action === 'review' && order.tab === '评价' && !order.reviewed) return {...order, reviewed:true}
 throw new Error('当前状态不支持此操作')
}
export const topics = games.flatMap((game, gi) => [
 { id:`${gi}-0`, game, title:'今晚排位，有人一起吗？', author:'小鹿', count:128, body:'想找几位同好一起轻松游戏，友好交流，不在意输赢。你通常几点上线？' },
 { id:`${gi}-1`, game, title:gi === 1 ? '分享你最喜欢的降落点' : '你最喜欢用哪个角色？', author:'阿澈', count:86, body:'每个人都有自己最拿手的角色，来聊聊你的选择和有趣的游戏经历吧。' },
 { id:`${gi}-2`, game, title:'分享你的新赛季上分心得', author:'橘子', count:42, body:'从团队配合到小技巧，记录自己的成长，也给其他玩家一点灵感。' },
 { id:`${gi}-3`, game, title:'晒晒今天的高光时刻', author:'小满', count:63, body:'不论是一场漂亮的配合，还是一次意想不到的翻盘，都值得记录。' },
])
export const conversations = [
 { id:'notice', name:'服务通知', text:'你的演示订单状态已更新，点击查看', time:'10:24', unread:1, color:'purple' },
 { id:'deer', name:'小鹿', text:'好呀，晚上八点见～', time:'09:42', unread:2, color:'green' },
 { id:'che', name:'阿澈', text:'我已经准备好啦，等你上线', time:'昨天', unread:0, color:'peach' },
 { id:'helper', name:'游伴小助手', text:'欢迎加入，一起发现更多乐趣', time:'昨天', unread:0, color:'purple' },
 { id:'group', name:'周末开黑小队', text:'橘子：今晚有人一起吗？', time:'周一', unread:0, color:'blue' },
]
