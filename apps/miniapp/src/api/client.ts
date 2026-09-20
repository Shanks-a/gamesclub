const BASE_URL = 'http://127.0.0.1:8000/api/v1'
let accessToken = ''
export function setAccessToken(token:string){accessToken=token;try{uni.setStorageSync('gamesclub-access-token',token)}catch{}}
export function restoreAccessToken(){try{accessToken=uni.getStorageSync('gamesclub-access-token')||''}catch{accessToken=''};return accessToken}
export function clearAccessToken(){accessToken='';try{uni.removeStorageSync('gamesclub-access-token')}catch{}}
export function request<T>(path:string, options:Omit<UniApp.RequestOptions,'url'>={}) : Promise<T> {
 return new Promise((resolve,reject)=>{uni.request({...options,url:`${BASE_URL}${path}`,header:{...(options.header||{}),...(accessToken?{Authorization:`Bearer ${accessToken}`}:{})},success:res=>{if(res.statusCode>=200&&res.statusCode<300)resolve(res.data as T);else reject(new Error(((res.data as any)?.error?.message)||`请求失败(${res.statusCode})`))},fail:reject})})
}
