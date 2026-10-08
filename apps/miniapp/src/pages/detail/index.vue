<script setup lang="ts">
import { ref,computed,nextTick } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import PageShell from '../../components/PageShell.vue'
import ProductCard from '../../components/ProductCard.vue'
import AppIcon from '../../components/AppIcon.vue'
import EmptyState from '../../components/EmptyState.vue'
import { products,topics,conversations,money } from '../../domain'
import { demo,toggleFavorite,logoutDemo,appendMessage,updateProfile } from '../../store'
import { go,detail,requireLogin,confirmDemo,notify } from '../../navigation'
import { createOrder } from '../../services/orders'
import { getProduct } from '../../services/catalog'
import { listFavorites, addFavorite, removeFavorite } from '../../services/favorites'
import { submitApplication, listApplications } from '../../services/partner'
import { request, mediaUrl, BASE_URL } from '../../api/client'
import type { Product } from '../../domain'
const kind=ref(''),id=ref(''),quantity=ref(1),chatInput=ref(''),busy=ref(false)
const titles:Record<string,string>={product:'服务详情',topic:'频道话题',chat:'会话详情',favorites:'我的收藏',balance:'余额明细',points:'积分中心',join:'我要加入',lottery:'活动抽奖',process:'下单流程',support:'客服中心',membership:'会员中心',settings:'设置',notifications:'通知',account:'个人信息',terms:'用户协议',privacy:'隐私政策',games:'更多游戏',aftersale:'退款与售后'}
const protectedKinds=['chat','favorites','balance','points','join','notifications','account']
const blocked=computed(()=>protectedKinds.includes(kind.value)&&!demo.loggedIn)
onLoad(q=>{kind.value=q?.kind||'';id.value=q?.id||'';if(!blocked.value&&kind.value==='chat'&&!demo.read.includes(id.value))demo.read.push(id.value);if(kind.value==='notifications'&&demo.loggedIn&&!demo.read.includes('notice'))demo.read.push('notice')})
const product=ref<Product>()
const remoteFavorites=ref<Product[]>([])
const loadError=ref('')
const apptDate=ref(''); const apptSlot=ref('')
const slotOptions=[{value:'morning',label:'上午'},{value:'afternoon',label:'下午'},{value:'evening',label:'晚上'}]
function onApptDate(e:any){ apptDate.value=e?.detail?.value||'' }
function onApptSlot(e:any){ const idx=Number(e?.detail?.value); apptSlot.value=slotOptions[idx]?.value||'' }
onShow(async()=>{loadError.value='';try{if(kind.value==='product'){product.value=await getProduct(id.value);quantity.value=product.value.minQuantity||1}if(demo.loggedIn){remoteFavorites.value=await listFavorites();demo.favorites=remoteFavorites.value.map(p=>p.id)}if(kind.value==='account')onShowAccount();if(kind.value==='join')await loadJoin()}catch(e){loadError.value=(e as Error).message;notify(loadError.value)}})
const topic=computed(()=>topics.find(t=>t.id===id.value))
const chat=computed(()=>conversations.find(c=>c.id===id.value))
const chatMessages=computed(()=>demo.messages[id.value]||[])
const favoriteList=computed(()=>remoteFavorites.value)
const steps=[['01','选择游戏与服务','查看服务内容、计费单位及价格，选择适合自己的商品。'],['02','提交预约与付款','正式流程需填写预约时段与服务需求；付款仅代表提交申请。'],['03','运营安排 · 队友确认','人员足额接受后才预约成功，调整安排需与你确认。'],['04','完成服务 · 验收评价','服务结束后确认交付；如有问题，可联系工作人员处理。']]
const info:Record<string,{icon:string;title:string;body:string}>={
 lottery:{icon:'gift',title:'好玩的活动，正在准备',body:'活动抽奖入口已预留。参与条件、奖品和开奖规则尚未确定，目前不开放抽奖。'},
 membership:{icon:'star',title:'会员权益，敬请期待',body:'会员方案仍在设计中，当前不开放购买或自动续费。'},
 points:{icon:'gift',title:'860 积分 · 示例',body:'积分获取、兑换规则尚未开放。这里展示的是演示数值，不能兑换真实权益。'},
 balance:{icon:'wallet',title:'¥ 128.00 · 示例余额',body:'当前没有真实账户资金和流水。充值、消费抵扣、提现均未接入，不会发生真实扣款。'},
 games:{icon:'game',title:'更多游戏，陆续相遇',body:'当前演示支持王者荣耀、和平精英、无畏契约和英雄联盟。其他游戏分区敬请期待。'},
 aftersale:{icon:'aftersale',title:'服务遇到问题，我们一起解决',body:'正式业务由运营审核售后请求。当前仅演示售后入口，不会创建真实案件或执行退款。'},
 terms:{icon:'order',title:'用户协议 · 演示说明',body:'正式用户协议尚未发布。此页面用于验证协议阅读与勾选交互；不接受付款，不提供真实交易，不构成正式服务协议。'},
 privacy:{icon:'order',title:'隐私政策 · 演示说明',body:'正式隐私政策尚未发布。本地演示仅保存演示登录标记和收藏，不获取微信身份、手机号或通讯录，也不向服务器传输会话。'},
}
async function order(){if(!demo.loggedIn){requireLogin('detail',{kind:'product',id:id.value});return}if(busy.value||!product.value||!product.value.available)return;if(!await confirmDemo('创建订单','将按服务端当前价格创建订单，暂不涉及真实支付。'))return;busy.value=true;try{await createOrder(product.value.id,quantity.value,product.value.version||1,`create-${Date.now()}`, apptDate.value?{date:apptDate.value,slot:apptSlot.value}:undefined);go('orders',{tab:'待付款'})}catch(e){notify((e as Error).message)}finally{busy.value=false}}
async function favorite(){if(!demo.loggedIn){requireLogin('detail',{kind:'product',id:id.value});return}try{if(demo.favorites.includes(id.value))await removeFavorite(id.value);else await addFavorite(id.value);remoteFavorites.value=await listFavorites();demo.favorites=remoteFavorites.value.map(p=>p.id);notify('收藏已同步')}catch(e){notify((e as Error).message)}}
async function sendMessage(){const value=chatInput.value.trim();if(!value)return;appendMessage(id.value,value);chatInput.value='';await nextTick()}
async function logout(){if(await confirmDemo('退出演示账号','退出后清理本机登录会话、草稿和未读状态，服务端订单不会删除。')){try{await request('/auth/logout/',{method:'POST'})}catch(e){notify((e as Error).message)}finally{logoutDemo();go('profile')}}}

// —— 个人信息编辑（微信头像昵称填写能力）——
const accountNickname=ref('')
const accountAvatar=ref('')
const accountSaving=ref(false)
const isWeixinAccount = typeof window === 'undefined'
function onShowAccount(){ accountNickname.value=demo.me?.nickname||''; accountAvatar.value=demo.me?.avatar_url||'' }
function onChooseAvatar(e:any){ const path=e?.detail?.avatarUrl; if(path) accountAvatar.value=path }
async function saveAccount(){
  if(accountSaving.value)return
  const nickname=accountNickname.value.trim()
  if(!nickname){ notify('请填写昵称'); return }
  accountSaving.value=true
  try{
    let avatarUrl=demo.me?.avatar_url||''
    // 微信端：临时头像路径需先上传到自有服务器持久化
    if(isWeixinAccount && accountAvatar.value && accountAvatar.value!==demo.me?.avatar_url){
      const up=await new Promise<{url:string}>((resolve,reject)=>{
        uni.uploadFile({url:`${BASE_URL}/me/avatar/`,filePath:accountAvatar.value,name:'file',header:{Authorization:`Bearer ${(uni.getStorageSync('gamesclub-access-token')||'')}`},success:r=>{try{resolve(JSON.parse(r.data))}catch(e){reject(new Error('上传响应异常'))}},fail:()=>reject(new Error('头像上传失败，请重试'))})
      })
      avatarUrl=up.url
    }
    await updateProfile({nickname, avatar_url:avatarUrl})
    notify('资料已更新')
  }catch(e){ notify((e as Error).message||'保存失败') }
  finally{ accountSaving.value=false }
}

// —— 陪玩入驻申请（我要加入）——
interface GameOption { id:number; name:string }
const joinGames=ref<GameOption[]>([])
const joinGameId=ref<number|null>(null)
const joinReason=ref('')
const joinSaving=ref(false)
const myApplications=ref<any[]>([])
async function loadJoin(){
  try{
    joinGames.value = await request<GameOption[]>('/games/')
    if(!demo.loggedIn) return
    myApplications.value = await listApplications()
  }catch(e){ notify((e as Error).message) }
}
function onJoinGame(e:any){ const idx=Number(e?.detail?.value); joinGameId.value = joinGames.value[idx]?.id ?? null }
async function submitJoin(){
  if(!demo.loggedIn){ requireLogin('detail',{kind:'join'}); return }
  if(!joinGameId.value){ notify('请选择游戏分区'); return }
  if(!joinReason.value.trim()){ notify('请填写申请说明'); return }
  joinSaving.value=true
  try{ await submitApplication(joinGameId.value, joinReason.value.trim()); notify('申请已提交，等待审核'); myApplications.value=await listApplications() }
  catch(e){ notify((e as Error).message) }
  finally{ joinSaving.value=false }
}
</script>
<template><PageShell :title="titles[kind]||'页面未找到'" backable><view class="body safe-bottom">
 <view v-if="blocked" class="blank-page"><text class="muted">请先登录演示账号查看</text><button class="ui-btn primary" @click="requireLogin('detail',{kind,id})">演示登录</button></view>
 <template v-else-if="kind==='product'&&product"><image :src="product.cover" class="detail-cover" mode="aspectFill"/><view class="section-head"><view><view class="title">{{product.title}}</view><view class="small muted">{{product.game}} · 1小时</view></view><button class="ui-btn" :aria-label="demo.favorites.includes(id)?'取消收藏':'收藏商品'" @click="favorite"><AppIcon name="star" :active="demo.favorites.includes(id)"/></button></view><view class="price">¥{{money(product.price)}}<text class="old">¥{{money(product.original)}}</text></view><view class="card description"><view class="heading">一起享受游戏的快乐</view><view class="muted paragraph">{{product.tagline}}。服务内容、人员安排与预约时段需在正式下单前确认。</view><view class="between"><text>演示购买数量</text><view class="row gap"><button class="ui-btn quantity" :disabled="quantity<=(product.minQuantity||1)" @click="quantity--">−</button><text>{{quantity}}</text><button class="ui-btn quantity" :disabled="quantity>=(product.maxQuantity||1)" @click="quantity++">＋</button></view></view><view class="between appt-row"><text>预约日期</text><picker mode="date" :value="apptDate" @change="onApptDate"><view class="picker-inline">{{apptDate||'请选择日期'}}<text class="muted">›</text></view></picker></view><view class="between appt-row"><text>预约时段</text><picker :range="slotOptions" range-key="label" @change="onApptSlot"><view class="picker-inline">{{slotOptions.find(s=>s.value===apptSlot)?.label||'请选择时段'}}<text class="muted">›</text></view></picker></view></view><view class="demo-note">这里只验证商品到订单的页面流程，不创建真实预约，不保证上分结果。</view><button class="ui-btn primary wide" :disabled="busy||!product.available" @click="order">{{product.available?'创建模拟订单':'商品不可售'}} · ¥{{money(product.price*quantity)}}</button></template>
 <template v-else-if="kind==='favorites'"><view class="demo-note">收藏保存在服务端，重新登录仍可查看。</view><view class="grid"><ProductCard v-for="p in favoriteList" :key="p.id" :product="p"/></view><EmptyState v-if="!favoriteList.length" title="还没有收藏" description="在服务详情中点击星标，留下你喜欢的商品。"/></template>
 <template v-else-if="kind==='topic'&&topic"><view class="topic-detail"><text class="small accent"># {{topic.game}}</text><view class="title">{{topic.title}}</view><view class="small muted">{{topic.author}} · {{topic.count}} 条讨论 · 示例</view><view class="paragraph">{{topic.body}}</view><view class="divider"/><view class="heading">讨论预览</view><view class="sample-comment"><text class="accent">小满</text><view>一起友好交流，快乐游戏～</view></view><view class="demo-note">话题与回复均为示例，发布和实时互动尚未开放。</view></view></template>
 <template v-else-if="kind==='chat'&&chat"><view class="chat-page"><view class="row gap chat-header"><view :class="['avatar',chat.color]">{{chat.name.slice(0,1)}}</view><view><view class="heading">{{chat.name}}</view><view class="small muted">示例会话 · 消息仅保存在本机</view></view></view><scroll-view scroll-y class="chat-list"><view v-for="message in chatMessages" :key="message.id" :class="['message-row',message.mine?'mine':'theirs']"><view class="message-time">{{message.time}}</view><view class="message-bubble">{{message.text}}</view></view><view v-if="!chatMessages.length" class="chat-empty muted">开始和{{chat.name}}聊天吧</view></scroll-view><view class="chat-composer"><input v-model="chatInput" class="chat-input" confirm-type="send" placeholder="输入消息" maxlength="300" @confirm="sendMessage"/><button class="ui-btn send-button" :disabled="!chatInput.trim()" @click="sendMessage">发送</button></view></view></template>
 <template v-else-if="kind==='process'"><view class="demo-note">了解从下单到完成服务的四个步骤。</view><view class="stack"><view v-for="step in steps" :key="step[0]" class="card"><text class="step-number">{{step[0]}}</text><view class="heading">{{step[1]}}</view><view class="muted paragraph">{{step[2]}}</view></view></view></template>
 <template v-else-if="kind==='support'"><view class="soft support-banner"><AppIcon name="headset" active :size="44"/><view class="title">很高兴为你解答</view><view class="muted small">这里整理了常见问题，帮助你快速了解游伴。</view></view><view class="stack"><button class="ui-btn card faq" @click="detail('process')">如何下单与预约？<text>›</text></button><button class="ui-btn card faq" @click="detail('aftersale')">服务问题与退款如何处理？<text>›</text></button><button class="ui-btn card faq" @click="detail('join')">如何加入成为游戏搭子？<text>›</text></button></view><view class="demo-note">人工客服尚未接入；以上为说明入口，不会发起真实客服会话。</view></template>
 <template v-else-if="kind==='settings'"><view class="card setting"><text>当前模式</text><text class="muted small">本地交互演示</text></view><button class="ui-btn card faq" @click="detail('terms')">用户协议<text>›</text></button><button class="ui-btn card faq" @click="detail('privacy')">隐私政策<text>›</text></button><button v-if="demo.loggedIn" class="ui-btn secondary wide logout" @click="logout">退出演示账号</button><button v-else class="ui-btn primary wide logout" @click="go('login')">进入演示登录</button></template>
 <template v-else-if="kind==='notifications'"><view class="card notification"><view class="heading">订单状态提醒</view><view class="muted paragraph">你的演示订单已更新，可前往订单页查看当前分类。</view><button class="ui-btn secondary button-small" @click="go('orders')">查看演示订单</button></view><view class="card notification"><view class="heading">欢迎来到游伴</view><view class="muted paragraph">找到同好，一起快乐开局。本页消息仅用于交互预览。</view></view></template>
 <template v-else-if="kind==='account'"><view class="card stack account-edit">
  <view class="avatar-wrap">
    <image v-if="accountAvatar" :src="isWeixinAccount?accountAvatar:mediaUrl(accountAvatar)" class="account-avatar" mode="aspectFill"/>
    <view v-else class="account-avatar placeholder">游</view>
    <!-- #ifdef MP-WEIXIN -->
    <button class="ui-btn secondary avatar-btn" open-type="chooseAvatar" @chooseavatar="onChooseAvatar">更换头像</button>
    <!-- #endif -->
    <!-- #ifndef MP-WEIXIN -->
    <view class="muted small">演示环境暂不支持上传头像</view>
    <!-- #endif -->
  </view>
  <view class="field">
    <text class="field-label">昵称</text>
    <!-- #ifdef MP-WEIXIN -->
    <input type="nickname" v-model="accountNickname" class="field-input" placeholder="填写或选择微信昵称" maxlength="40"/>
    <!-- #endif -->
    <!-- #ifndef MP-WEIXIN -->
    <input v-model="accountNickname" class="field-input" placeholder="填写昵称" maxlength="40"/>
    <!-- #endif -->
  </view>
  <button class="ui-btn primary wide" :loading="accountSaving" @click="saveAccount">保存资料</button>
  <view class="demo-note">昵称与头像用于订单、派单中的身份展示；首次填写后由你主动提交。</view>
 </view></template>
 <template v-else-if="kind==='join'"><view class="card stack join-edit">
  <view class="heading">申请成为游戏搭子</view>
  <view class="muted small">提交申请后由管理员审核，通过即可绑定游戏分区、开启接单。</view>
  <view class="field"><text class="field-label">意向游戏分区</text><picker :range="joinGames" range-key="name" @change="onJoinGame"><view class="picker-box">{{joinGames.find(g=>g.id===joinGameId)?.name||'请选择游戏分区'}}<text class="muted">›</text></view></picker></view>
  <view class="field"><text class="field-label">申请说明</text><textarea v-model="joinReason" class="field-textarea" placeholder="介绍你的游戏水平、擅长位置、可服务时段等" maxlength="500"/></view>
  <button v-if="demo.loggedIn" class="ui-btn primary wide" :loading="joinSaving" @click="submitJoin">提交申请</button>
  <button v-else class="ui-btn primary wide" @click="requireLogin('detail',{kind:'join'})">登录后申请</button>
  <view v-if="myApplications.length" class="app-list"><view class="heading small">我的申请</view><view v-for="a in myApplications" :key="a.id" class="app-item between"><text>{{a.game?.name||''}}</text><text class="accent small">{{a.status==='PENDING'?'审核中':a.status==='APPROVED'?'已通过':'已驳回'}}</text></view></view>
 </view></template>
 <template v-else-if="info[kind]"><view class="info-panel"><view class="info-icon"><AppIcon :name="info[kind].icon" active :size="46"/></view><view class="title">{{info[kind].title}}</view><view class="muted paragraph">{{info[kind].body}}</view><button class="ui-btn secondary" @click="go('home')">返回首页</button></view></template>
 <EmptyState v-else title="没有找到这项内容" description="内容可能不存在，请返回上一页重新选择。"/>
</view></PageShell></template>
<style scoped>.account-edit{display:flex;flex-direction:column;gap:30rpx;padding:40rpx}.join-edit{display:flex;flex-direction:column;gap:28rpx;padding:40rpx}.join-edit .heading{margin-bottom:0}.picker-box{display:flex;justify-content:space-between;align-items:center;background:#fff;border-radius:22rpx;padding:24rpx;font-size:28rpx}.field-textarea{background:#fff;border-radius:22rpx;padding:24rpx;font-size:28rpx;min-height:160rpx;width:100%;box-sizing:border-box}.app-list{margin-top:8rpx}.app-list .heading{font-size:26rpx}.app-item{padding:20rpx 0;font-size:26rpx;border-bottom:1rpx solid #eee}.appt-row{margin-top:24rpx}.picker-inline{display:flex;align-items:center;gap:8rpx;background:#eeebf3;border-radius:18rpx;padding:12rpx 20rpx;font-size:25rpx}.avatar-wrap{display:flex;flex-direction:column;align-items:center;gap:24rpx}.account-avatar{width:160rpx;height:160rpx;border-radius:48rpx;background:#e6deef}.account-avatar.placeholder{display:flex;align-items:center;justify-content:center;font-size:58rpx;color:#80699e}.avatar-btn{margin:0}.field{display:flex;flex-direction:column;gap:14rpx}.field-label{font-size:25rpx;color:#747486}.field-input{background:#fff;border-radius:22rpx;padding:24rpx;font-size:28rpx;height:46rpx}.detail-cover{width:100%;height:350rpx;border-radius:30rpx;margin-top:22rpx}.description{margin-top:30rpx}.paragraph{font-size:27rpx;line-height:1.9;margin:22rpx 0 32rpx}.quantity{background:#eeebf3;width:60rpx;height:60rpx;border-radius:18rpx;line-height:60rpx}.topic-detail{padding-top:28rpx}.topic-detail .title{margin:26rpx 0}.sample-comment{margin-top:30rpx;font-size:27rpx}.sample-comment view{margin-top:14rpx}.chat-header{margin:20rpx 0}.chat-page{display:flex;flex-direction:column;height:calc(100vh - 170rpx)}.chat-list{flex:1;background:#f2f1f3;border-radius:26rpx;padding:20rpx 18rpx}.message-row{display:flex;flex-direction:column;margin:24rpx 0}.message-row.mine{align-items:flex-end}.message-row.theirs{align-items:flex-start}.message-time{font-size:19rpx;color:#9a98a3;margin-bottom:8rpx}.message-bubble{max-width:74%;padding:20rpx 24rpx;font-size:27rpx;line-height:1.55;border-radius:24rpx;background:#fff;color:#303345}.mine .message-bubble{background:#d8cee7}.chat-empty{text-align:center;padding:80rpx 0}.chat-composer{display:flex;gap:16rpx;align-items:center;padding:20rpx 0 8rpx}.chat-input{flex:1;background:#fff;border-radius:22rpx;padding:20rpx 24rpx;height:42rpx;font-size:26rpx}.send-button{background:#80699e;color:#fff;padding:15rpx 24rpx;border-radius:22rpx}.send-button[disabled]{opacity:.45}.draft{height:250rpx;padding:26rpx}.draft-count{margin:20rpx 0 34rpx}.step-number{display:block;font-size:40rpx;color:#8875aa;margin-bottom:14rpx}.support-banner{padding:40rpx 30rpx;margin:22rpx 0 36rpx}.support-banner .title{margin:24rpx 0 16rpx}.faq{width:100%;display:flex;justify-content:space-between;text-align:left;margin:24rpx 0}.setting{display:flex;justify-content:space-between;margin:24rpx}.logout{margin-top:60rpx}.notification{margin-top:30rpx}.info-panel{text-align:center;padding:72rpx 18rpx}.info-icon{display:flex;align-items:center;justify-content:center;margin:0 auto 36rpx;background:#e6deef;width:160rpx;height:160rpx;border-radius:48rpx}.info-panel .title{font-size:38rpx}.info-panel .secondary{margin-top:50rpx}</style>
