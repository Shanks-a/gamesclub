<script setup lang="ts">
import { ref, computed } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import PageShell from '../../components/PageShell.vue'
import ProductCard from '../../components/ProductCard.vue'
import EmptyState from '../../components/EmptyState.vue'
import AppIcon from '../../components/AppIcon.vue'
import { request } from '../../api/client'
import type { ApiCategory, ApiGame, ApiProduct } from '../../api/types'
import type { Product } from '../../domain'
const gameName=ref(''); const query=ref(''); const categoryId=ref(0); const categories=ref<ApiCategory[]>([]); const products=ref<Product[]>([]); const loading=ref(true)
const filtered=computed(()=>products.value.filter(p=>!query.value.trim()||`${p.title}${p.tagline}`.toLowerCase().includes(query.value.trim().toLowerCase())))
const toProduct=(p:ApiProduct):Product=>({id:String(p.id),title:p.title,game:p.game.name as Product['game'],price:p.price_cents,original:p.original_price_cents,art:Number((p.cover_url.match(/product-(\d+)/)||[])[1]||0),tagline:p.description||'一起享受游戏的快乐',version:p.version})
let sequence=0
async function load(){const run=++sequence;loading.value=true;try{const gs=await request<ApiGame[]>('/games/');const game=gs.find(g=>g.name===gameName.value);if(!game)throw new Error('游戏不存在或已停用');const cats=await request<ApiCategory[]>(`/games/${game.id}/categories/`);if(run!==sequence)return;categories.value=cats;if(!cats.some(c=>c.id===categoryId.value))categoryId.value=0;const suffix=categoryId.value?`&category_id=${categoryId.value}`:'';const data=await request<ApiProduct[]>(`/products/?game=${encodeURIComponent(gameName.value)}${suffix}`);if(run===sequence)products.value=data.map(toProduct)}catch(e){if(run===sequence){products.value=[];uni.showToast({title:e instanceof Error?e.message:'加载失败，请重试',icon:'none'})}}finally{if(run===sequence)loading.value=false}}
function choose(id:number){categoryId.value=id;void load()}
onLoad(options=>{gameName.value=options?.game||''})
onShow(()=>{void load()})
</script>
<template><PageShell :title="gameName" backable><view class="body"><view class="search"><AppIcon name="search" :size="20"/><input v-model="query" placeholder="搜索商品"/></view><scroll-view scroll-x class="tabs-scroll"><view class="pills"><button class="ui-btn pill" :class="{active:categoryId===0}" @click="choose(0)">全部类型</button><button v-for="item in categories" :key="item.id" class="ui-btn pill" :class="{active:categoryId===item.id}" @click="choose(item.id)">{{item.name}}</button></view></scroll-view><view class="section-head"><text class="heading">{{gameName}}商品</text><text class="small muted">{{filtered.length}} 款</text></view><view v-if="!loading && filtered.length" class="grid"><ProductCard v-for="p in filtered" :key="p.id" :product="p"/></view><EmptyState v-else-if="!loading" title="暂无商品" description="请换一个商品类型或关键词。"/><view v-else class="empty muted">正在加载商品…</view></view></PageShell></template>
