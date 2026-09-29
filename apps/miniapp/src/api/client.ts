// H5 走同源 vite dev server 代理（见 vite.config.ts），避免跨域；生产由部署同域名反代。
// 微信小程序等非 H5 平台默认直连本地后端；均可通过 VITE_API_BASE_URL 覆盖。
// 用运行时判断（H5 有 window，小程序无）替代编译期条件编译，保证 vue-tsc 可解析。
const isH5 = typeof window !== 'undefined'
export const BASE_URL = import.meta.env.VITE_API_BASE_URL || (isH5 ? '/api/v1' : 'http://127.0.0.1:8000/api/v1')

export function mediaUrl(path:string){return path.startsWith('/')?BASE_URL.replace(/\/api\/v1\/?$/,'')+path:path}
let accessToken = ''
export function setAccessToken(token:string){accessToken=token;try{uni.setStorageSync('gamesclub-access-token',token)}catch{}}
export function restoreAccessToken(){try{accessToken=uni.getStorageSync('gamesclub-access-token')||''}catch{accessToken=''};return accessToken}
export function clearAccessToken(){accessToken='';try{uni.removeStorageSync('gamesclub-access-token')}catch{}}
export function request<T>(path:string, options:Omit<UniApp.RequestOptions,'url'>={}) : Promise<T> {
 return new Promise((resolve,reject)=>{uni.request({timeout:15000,...options,url:`${BASE_URL}${path}`,header:{...(options.header||{}),...(accessToken?{Authorization:`Bearer ${accessToken}`}:{})},success:res=>{if(res.statusCode===401){clearAccessToken();uni.$emit('auth-expired')}if(res.statusCode>=200&&res.statusCode<300)resolve(res.data as T);else reject(new Error(((res.data as any)?.error?.message)||`请求失败(${res.statusCode})`))},fail:()=>reject(new Error('无法连接后端，请检查服务地址和网络'))})})
}
