import { demo } from './store'
const tabs=['home','channel','messages','profile']
export function go(page: string, params: Record<string,string> = {}) {
 const query=Object.entries(params).map(([k,v])=>`${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&')
 const url=`/pages/${page}/index${query?'?'+query:''}`
 if(tabs.includes(page)) uni.switchTab({url:`/pages/${page}/index`})
 else uni.navigateTo({url})
}
export function back() { if(getCurrentPages().length>1) uni.navigateBack();else go('home') }
export function detail(kind:string,id='') { go('detail',{kind,id}) }
export function requireLogin(page:string,params:Record<string,string>={}) {
 if(demo.loggedIn) {go(page,params);return}
 go('login',{next:encodeURIComponent(JSON.stringify({page,params}))})
}
export function notify(title:string) { uni.showToast({title,icon:'none'}) }
export function confirmDemo(title:string, content:string): Promise<boolean> {
 return new Promise(resolve=>uni.showModal({title,content,confirmText:'确认演示',confirmColor:'#80699E',success:r=>resolve(r.confirm),fail:()=>resolve(false)}))
}
