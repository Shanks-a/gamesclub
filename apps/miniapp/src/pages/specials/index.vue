<script setup lang="ts">
import { ref,computed } from 'vue'
import { onLoad,onShow } from '@dcloudio/uni-app'
import PageShell from '../../components/PageShell.vue'
import ProductCard from '../../components/ProductCard.vue'
import EmptyState from '../../components/EmptyState.vue'
import { games, type Product } from '../../domain'
import { request } from '../../api/client'
import { toProduct,loadCatalog } from '../../services/catalog'
const configured=ref<Product[]>([])
onShow(async()=>{try{await loadCatalog();const entries=await request<any[]>('/home/');configured.value=entries.filter(e=>e.kind==='special'&&e.product_detail).map(e=>toProduct(e.product_detail))}catch(e){configured.value=[];uni.showToast({title:(e as Error).message,icon:'none'})}})
const game=ref('全部'),ascending=ref<boolean|undefined>(undefined)
onLoad((q)=>{if(q?.game&&games.includes(q.game as any))game.value=q.game})
const list=computed(()=>configured.value.filter(p=>game.value==='全部'||p.game===game.value).sort((a,b)=>ascending.value===undefined?0:ascending.value?a.price-b.price:b.price-a.price))
</script>
<template><PageShell title="限时特价" backable><view class="body"><view class="soft promo"><view class="title">好价开局，快乐加倍</view><view class="between"><text class="small muted">精选游戏服务 · 限时优惠</text><text class="small accent">SPECIAL</text></view></view><scroll-view scroll-x class="tabs-scroll"><view class="pills filters"><button v-for="item in ['全部',...games]" :key="item" class="ui-btn pill" :class="{active:game===item}" @click="game=item">{{item}}</button></view></scroll-view><view class="between sort-row"><text class="small muted">{{list.length}} 款精选服务</text><button class="ui-btn small accent" @click="ascending=ascending===true?false:true">价格 {{ascending===undefined?'↑↓':ascending?'↑':'↓'}}</button></view><view class="grid"><ProductCard v-for="p in list" :key="p.id" :product="p"/></view><EmptyState v-if="!list.length"/><view class="footnote">演示价格 · 优惠以正式下单页面为准</view></view></PageShell></template>
<style scoped>.promo{padding:32rpx;margin:20rpx 0 28rpx}.promo .between{margin-top:26rpx}.filters{padding:12rpx 0}.sort-row{padding:20rpx 0 24rpx}</style>
