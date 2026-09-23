export const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'
export function mediaUrl(path:string){return path.startsWith('/')?BASE_URL.replace(/\/api\/v1\/?$/,'')+path:path}
let accessToken = ''
export function setAccessToken(token:string){accessToken=token;try{uni.setStorageSync('gamesclub-access-token',token)}catch{}}
export function restoreAccessToken(){try{accessToken=uni.getStorageSync('gamesclub-access-token')||''}catch{accessToken=''};return accessToken}
export function clearAccessToken(){accessToken='';try{uni.removeStorageSync('gamesclub-access-token')}catch{}}
export function request<T>(path:string, options:Omit<UniApp.RequestOptions,'url'>={}) : Promise<T> {
 return new Promise((resolve,reject)=>{uni.request({timeout:15000,...options,url:`${BASE_URL}${path}`,header:{...(options.header||{}),...(accessToken?{Authorization:`Bearer ${accessToken}`}:{})},success:res=>{if(res.statusCode===401){clearAccessToken();uni.$emit('auth-expired')}if(res.statusCode>=200&&res.statusCode<300)resolve(res.data as T);else reject(new Error(((res.data as any)?.error?.message)||`请求失败(${res.statusCode})`))},fail:()=>reject(new Error('无法连接后端，请检查服务地址和网络'))})})
}
