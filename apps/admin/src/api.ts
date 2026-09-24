import { defineStore } from 'pinia'
let csrfToken=''
export function setCsrfToken(value:string){csrfToken=value}
export const useSession=defineStore('session',{state:()=>({username:'',authenticated:false,csrf:''}),actions:{async restore(){const data=await api('session/');this.username=data.username;this.authenticated=data.authenticated;this.csrf=data.csrf_token;setCsrfToken(data.csrf_token)}}})
export async function api(path:string,method='GET',body?:unknown):Promise<any>{
 const csrf=csrfToken||decodeURIComponent(document.cookie.split('; ').find(v=>v.startsWith('csrftoken='))?.split('=')[1]||'')
 const upload=body instanceof FormData
 const response=await fetch('/api/v1/management/'+path,{method,credentials:'include',headers:{'X-CSRFToken':csrf,...(upload?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:upload?body:JSON.stringify(body)})
 const data=await response.json().catch(()=>({}))
 if(!response.ok){if(response.status===401){useSession().authenticated=false}throw new Error(response.status===409&&data.error?.code==='VERSION_CONFLICT'?'数据已被修改，请刷新列表后重试':data.error?.message||JSON.stringify(data.error?.details||data))}
 return data
}
