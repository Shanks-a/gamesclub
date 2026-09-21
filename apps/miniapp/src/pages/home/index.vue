<script setup lang="ts">
import { ref, computed } from 'vue'
import PageShell from '../../components/PageShell.vue'
import AppIcon from '../../components/AppIcon.vue'
import ProductCard from '../../components/ProductCard.vue'
import EmptyState from '../../components/EmptyState.vue'
import { games, filterProducts } from '../../domain'
import { go, detail } from '../../navigation'
const selected=ref('推荐'), query=ref(''), searching=ref(false)
const list=computed(()=>filterProducts(selected.value,query.value))
const shortcuts=[{title:'活动抽奖',icon:'gift',id:'lottery'},{title:'下单流程',icon:'order',id:'process'},{title:'客服中心',icon:'headset',id:'support'},{title:'考核中心',icon:'assessment',id:'assessment'}]
const banners=[{eyebrow:'WEEKEND TOGETHER',title:'开黑，更有默契',sub:'发现你的下一位游戏搭子',cta:'探索好搭子',art:3},{eyebrow:'PLAY WITH FRIENDS',title:'找到你的同频玩家',sub:'聊聊热爱，一起快乐开局',cta:'进入频道',art:1},{eyebrow:'SPECIAL FOR YOU',title:'好价开局，快乐加倍',sub:'看看今天的精选特价服务',cta:'发现好价',art:2}]
function bannerClick(i:number){if(i===1)go('channel');else go('specials')}
</script>
<template>
 <PageShell title="游伴 CLUB"><template #actions><button class="ui-btn" aria-label="搜索商品" @click="searching=!searching"><AppIcon name="search"/></button></template>
  <view class="body">
   <view v-if="searching" class="search"><AppIcon name="search" :size="20"/><input v-model="query" placeholder="搜索商品或游戏" :focus="searching"/><button v-if="query" class="ui-btn clear" @click="query=''">清除</button></view>
   <scroll-view scroll-x class="tabs-scroll"><view class="pills game-tabs"><button v-for="game in ['推荐',...games]" :key="game" class="ui-btn pill" :class="{active:selected===game}" @click="selected=game">{{game}}</button></view></scroll-view>
   <swiper class="hero-swiper" circular autoplay :interval="4500" indicator-dots indicator-color="#c6bccf" indicator-active-color="#756784">
    <swiper-item v-for="(banner,i) in banners" :key="banner.title"><view class="hero soft" @click="bannerClick(i)"><image :src="`/static/art/product-${banner.art}.png`" class="hero-art" mode="aspectFill"/><view class="hero-copy"><view class="eyebrow">{{banner.eyebrow}}</view><view class="hero-title">{{banner.title}}</view><view class="hero-sub">{{banner.sub}}</view><button class="ui-btn hero-button">{{banner.cta}}<text> →</text></button></view></view></swiper-item>
   </swiper>
   <view class="shortcuts"><button class="ui-btn" v-for="item in shortcuts" :key="item.id" @click="detail(item.id)"><AppIcon :name="item.icon" active/><text>{{item.title}}</text></button></view>
   <view class="section-head"><text class="heading">限时特价</text><button class="ui-btn link" @click="go('specials',{game:selected==='推荐'?'全部':selected})">更多 ›</button></view>
   <view v-if="list.length" class="grid"><ProductCard v-for="p in list.slice(0,2)" :key="p.id" :product="p"/></view><EmptyState v-else title="没有找到相关商品" description="换个关键词，或选择其他游戏试试。"/>
   <view class="section-head"><text class="heading">人气热选</text><button class="ui-btn link" @click="go('popular')">查看全部 ›</button></view>
   <view class="stack"><ProductCard v-for="p in list.slice(-2)" :key="p.id" :product="p" horizontal/></view>
   <view class="footnote">热爱游戏，也热爱相遇</view>
  </view>
 </PageShell>
</template>
<style scoped>
.game-tabs{padding:14rpx 0 22rpx}.hero-swiper{height:330rpx;margin:10rpx 0 26rpx}.hero{height:100%;position:relative;overflow:hidden}.hero-art{position:absolute;right:0;width:39%;height:100%;opacity:.8}.hero-copy{position:relative;padding:35rpx 32rpx;width:76%}.eyebrow{font-size:19rpx;letter-spacing:1rpx;color:#8875aa;font-weight:700}.hero-title{font-size:43rpx;font-weight:700;margin:23rpx 0 10rpx;letter-spacing:-1rpx}.hero-sub{font-size:23rpx;color:#756784}.hero-button{background:#80699e;color:#fff;display:inline-block;font-size:23rpx;padding:14rpx 23rpx;border-radius:28rpx;margin-top:26rpx}.shortcuts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16rpx}.shortcuts button{width:100%;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:15rpx;padding:20rpx 0;background:#fff;border-radius:26rpx;font-size:23rpx;white-space:nowrap}
</style>
