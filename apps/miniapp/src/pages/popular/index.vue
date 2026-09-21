<script setup lang="ts">
import { ref, computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import PageShell from '../../components/PageShell.vue'
import ProductCard from '../../components/ProductCard.vue'
import EmptyState from '../../components/EmptyState.vue'
import { games, filterProducts } from '../../domain'
const game=ref('全部')
onLoad(q=>{if(q?.game&&games.includes(q.game as any))game.value=q.game})
const list=computed(()=>filterProducts(game.value))
</script>
<template><PageShell title="人气热选" backable><view class="body"><view class="soft promo"><view class="title">大家都在玩的热门服务</view><view class="between"><text class="small muted">人气商品 · 轻松找到合拍搭子</text><text class="small accent">POPULAR</text></view></view><scroll-view scroll-x class="tabs-scroll"><view class="pills filters"><button v-for="item in ['全部',...games]" :key="item" class="ui-btn pill" :class="{active:game===item}" @click="game=item">{{item}}</button></view></scroll-view><view class="small muted count">{{list.length}} 款热门服务</view><view class="grid"><ProductCard v-for="p in list" :key="p.id" :product="p"/></view><EmptyState v-if="!list.length" title="暂无热门服务" description="换个游戏分区试试。"/><view class="footnote">热门排序将以服务端数据为准</view></view></PageShell></template>
<style scoped>.promo{padding:32rpx;margin:20rpx 0 28rpx}.promo .between{margin-top:26rpx}.filters{padding:12rpx 0}.count{padding:20rpx 0 24rpx}</style>
