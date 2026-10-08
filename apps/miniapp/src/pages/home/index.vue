<script setup lang="ts">
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import PageShell from '../../components/PageShell.vue'
import AppIcon from '../../components/AppIcon.vue'
import ProductCard from '../../components/ProductCard.vue'
import EmptyState from '../../components/EmptyState.vue'
import { games, filterProducts } from '../../domain'
import { go, detail } from '../../navigation'
import { request, mediaUrl } from '../../api/client'
import { loadCatalog, toProduct } from '../../services/catalog'
import type { ApiCategory, ApiGame, ApiProduct } from '../../api/types'
import type { Product } from '../../domain'
const selected=ref('推荐'), query=ref(''), searching=ref(false)
const list=computed(()=>filterProducts(selected.value,query.value))
const gameCategories=ref<ApiCategory[]>([]), gameProducts=ref<Product[]>([]), gameLoading=ref(false), gameError=ref('')
const gameList=computed(()=>gameProducts.value.filter(p=>!query.value.trim()||`${p.title}${p.tagline}`.toLowerCase().includes(query.value.trim().toLowerCase())))
const selectedCategory=ref(0)
const shortcuts=[{title:'活动抽奖',icon:'gift',id:'lottery'},{title:'下单流程',icon:'order',id:'process'},{title:'客服中心',icon:'headset',id:'support'},{title:'我要加入',icon:'assessment',id:'join'}]
const banners=[{eyebrow:'WEEKEND TOGETHER',title:'开黑，更有默契',sub:'发现你的下一位游戏搭子',cta:'探索好搭子',art:3},{eyebrow:'PLAY WITH FRIENDS',title:'找到你的同频玩家',sub:'聊聊热爱，一起快乐开局',cta:'进入频道',art:1},{eyebrow:'SPECIAL FOR YOU',title:'好价开局，快乐加倍',sub:'看看今天的精选特价服务',cta:'发现好价',art:2}]
function bannerClick(i:number){if(i===1)go('channel');else go('specials')}
let sequence=0
const homeEntries=ref<any[]>([])
const configuredSpecials=computed(()=>homeEntries.value.filter(e=>e.kind==='special'&&e.product_detail).map(e=>toProduct(e.product_detail)))
const configuredPopular=computed(()=>homeEntries.value.filter(e=>e.kind==='popular'&&e.product_detail).map(e=>toProduct(e.product_detail)))
const configuredBanners=computed(()=>homeEntries.value.filter(e=>e.kind==='banner'))
async function loadGame(gameName:string){
 const run=++sequence; const chosen=selectedCategory.value
 gameLoading.value=true; gameError.value=''
 try {
  const partitions=await request<ApiGame[]>('/games/')
  const game=partitions.find(item=>item.name===gameName)
  if(!game)throw new Error('游戏分区暂不可用')
  const cats=await request<ApiCategory[]>('/games/'+game.id+'/categories/')
  if(run!==sequence)return
  gameCategories.value=cats
  selectedCategory.value=cats.some(item=>item.id===chosen)?chosen:0
  const suffix=selectedCategory.value?'&category_id='+selectedCategory.value:''
  const data=await request<ApiProduct[]>('/products/?game='+encodeURIComponent(gameName)+suffix)
  if(run===sequence)gameProducts.value=data.map(toProduct)
 }catch(e){if(run===sequence){gameProducts.value=[];gameError.value=(e as Error).message}}
 finally{if(run===sequence)gameLoading.value=false}
}
function selectGame(game:string){++sequence;selected.value=game;query.value='';selectedCategory.value=0;gameCategories.value=[];gameProducts.value=[];if(game!=='推荐')void loadGame(game)}
function selectCategory(id:number){selectedCategory.value=id;if(selected.value!=='推荐')void loadGame(selected.value)}
function openBanner(entry:any){if(entry.target==='product'&&entry.product)detail('product',String(entry.product));else if(entry.target==='game')selectGame(entry.game_name)}
onShow(async()=>{try{await loadCatalog();homeEntries.value=await request<any[]>('/home/');if(selected.value!=='推荐')void loadGame(selected.value)}catch(e){gameError.value=(e as Error).message;uni.showToast({title:gameError.value,icon:'none'})}})

</script>
<template>
 <PageShell title="游伴 CLUB"><template #actions><button class="ui-btn" aria-label="搜索商品" @click="searching=!searching"><AppIcon name="search"/></button></template>
  <view class="body">
   <view v-if="searching" class="search"><AppIcon name="search" :size="20"/><input v-model="query" placeholder="搜索商品或游戏" :focus="searching"/><button v-if="query" class="ui-btn clear" @click="query=''">清除</button></view>
   <scroll-view scroll-x class="tabs-scroll"><view class="pills game-tabs"><button v-for="game in ['推荐',...games]" :key="game" class="ui-btn pill" :class="{active:selected===game}" @click="selectGame(game)">{{game}}</button></view></scroll-view>
   <swiper v-if="selected==='推荐' && configuredBanners.length" class="hero-swiper" circular autoplay indicator-dots><swiper-item v-for="entry in configuredBanners" :key="entry.id"><view class="hero soft" @click="openBanner(entry)"><image v-if="entry.image_url" :src="mediaUrl(entry.image_url)" class="hero-art" mode="aspectFill"/><view class="hero-copy"><view class="hero-title">{{entry.title}}</view></view></view></swiper-item></swiper>
   <view v-if="selected==='推荐'" class="shortcuts"><button class="ui-btn" v-for="item in shortcuts" :key="item.id" @click="detail(item.id)"><AppIcon :name="item.icon" active/><text>{{item.title}}</text></button></view>
   <template v-if="selected!=='推荐'">
    <view class="game-view-head"><view><view class="title">{{selected}}</view><view class="small muted">选择服务类型，直接浏览商品</view></view><text class="small muted">{{gameList.length}} 款</text></view>
    <scroll-view scroll-x class="tabs-scroll category-tabs"><view class="pills"><button class="ui-btn pill" :class="{active:selectedCategory===0}" @click="selectCategory(0)">全部类型</button><button v-for="item in gameCategories" :key="item.id" class="ui-btn pill" :class="{active:selectedCategory===item.id}" @click="selectCategory(item.id)">{{item.name}}</button></view></scroll-view>
    <view v-if="gameError" class="empty"><text class="empty-title">商品暂时无法加载</text><text class="muted">{{gameError}}</text><button class="ui-btn secondary retry" @click="loadGame(selected)">重新加载</button></view>
    <view v-else-if="gameLoading" class="empty muted">正在加载商品…</view>
    <view v-else-if="gameList.length" class="grid"><ProductCard v-for="p in gameList" :key="p.id" :product="p"/></view>
    <EmptyState v-else title="暂无商品" description="请先在后台为该游戏配置商品。"/>
   </template>
   <template v-else>
   <view class="section-head"><text class="heading">限时特价</text><button class="ui-btn link" @click="go('specials',{game:selected==='推荐'?'全部':selected})">更多 ›</button></view>
   <view v-if="configuredSpecials.length" class="grid"><ProductCard v-for="p in configuredSpecials" :key="p.id" :product="p"/></view><EmptyState v-else title="没有找到相关商品" description="换个关键词，或选择其他游戏试试。"/>
   <view class="section-head"><text class="heading">人气热选</text><button class="ui-btn link" @click="go('popular')">查看全部 ›</button></view>
   <view class="stack"><ProductCard v-for="p in configuredPopular" :key="p.id" :product="p" horizontal/></view>
   <view class="footnote">热爱游戏，也热爱相遇</view>
   </template>
  </view>
 </PageShell>
</template>
<style scoped>
.game-tabs{padding:14rpx 0 22rpx}.hero-swiper{height:330rpx;margin:10rpx 0 26rpx}.hero{height:100%;position:relative;overflow:hidden}.hero-art{position:absolute;right:0;width:39%;height:100%;opacity:.8}.hero-copy{position:relative;padding:35rpx 32rpx;width:76%}.eyebrow{font-size:19rpx;letter-spacing:1rpx;color:#8875aa;font-weight:700}.hero-title{font-size:43rpx;font-weight:700;margin:23rpx 0 10rpx;letter-spacing:-1rpx}.hero-sub{font-size:23rpx;color:#756784}.hero-button{background:#80699e;color:#fff;display:inline-block;font-size:23rpx;padding:14rpx 23rpx;border-radius:28rpx;margin-top:26rpx}.shortcuts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16rpx}.shortcuts button{width:100%;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:15rpx;padding:20rpx 0;background:#fff;border-radius:26rpx;font-size:23rpx;white-space:nowrap}.game-view-head{display:flex;align-items:flex-end;justify-content:space-between;margin:18rpx 0 8rpx}.category-tabs{margin-bottom:16rpx}.retry{display:block;margin:24rpx auto 0}
</style>
