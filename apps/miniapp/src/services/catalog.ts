import { request } from '../api/client'
import { products, type Product, type Game } from '../domain'
import type { ApiProduct } from '../api/types'
const toProduct=(p:ApiProduct):Product=>({id:String(p.id),title:p.title,game:p.game.name as Game,price:p.price_cents,original:p.original_price_cents,art:Number((p.cover_url.match(/product-(\d+)/)||[])[1]||0),tagline:p.description||'一起享受游戏的快乐',version:p.version})
export async function loadCatalog(){const data=await request<ApiProduct[]>('/products/');products.splice(0,products.length,...data.map(toProduct));return products}
