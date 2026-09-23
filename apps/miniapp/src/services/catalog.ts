import { request, mediaUrl } from '../api/client'
import { products, games, type Product } from '../domain'
import type { ApiProduct, ApiGame } from '../api/types'
export const toProduct=(p:ApiProduct):Product=>({id:String(p.id),title:p.title,game:p.game.name,price:p.price_cents,original:p.original_price_cents,art:0,cover:mediaUrl(p.cover_url),minQuantity:p.min_quantity,maxQuantity:p.max_quantity,available:p.is_available,tagline:p.description,version:p.version})
export async function loadCatalog(){const [data,partitions]=await Promise.all([request<ApiProduct[]>('/products/'),request<ApiGame[]>('/games/')]);games.splice(0,games.length,...partitions.map(g=>g.name));products.splice(0,products.length,...data.map(toProduct));return products}
export async function getProduct(id:string){return toProduct(await request<ApiProduct>(`/products/${id}/`))}
