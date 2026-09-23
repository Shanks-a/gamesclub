import { request } from '../api/client'
import type { ApiProduct } from '../api/types'
import { toProduct } from './catalog'
export async function listFavorites(){return (await request<{product:ApiProduct}[]>('/me/favorites/')).map(f=>toProduct(f.product))}
export function addFavorite(id:string){return request('/me/favorites/',{method:'POST',data:{product_id:Number(id)}})}
export function removeFavorite(id:string){return request(`/me/favorites/${id}/`,{method:'DELETE'})}
