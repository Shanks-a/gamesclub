<script setup lang="ts">
import { ref,computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import PageShell from '../../components/PageShell.vue'
import ProductCard from '../../components/ProductCard.vue'
import AppIcon from '../../components/AppIcon.vue'
import EmptyState from '../../components/EmptyState.vue'
import { products,topics,conversations,money } from '../../domain'
import { demo,toggleFavorite,logoutDemo,createDemoOrder } from '../../store'
import { go,detail,requireLogin,confirmDemo,notify } from '../../navigation'
const kind=ref(''),id=ref(''),quantity=ref(1),draft=ref(''),busy=ref(false)
const titles:Record<string,string>={product:'服务详情',topic:'频道话题',chat:'会话详情',favorites:'我的收藏',balance:'余额明细',points:'积分中心',join:'我要加入',lottery:'活动抽奖',process:'下单流程',support:'客服中心',assessment:'考核中心',membership:'会员中心',settings:'设置',notifications:'通知',account:'个人信息',terms:'用户协议',privacy:'隐私政策',games:'更多游戏',aftersale:'退款与售后'}
const protectedKinds=['chat','favorites','balance','points','join','notifications','account']
const blocked=computed(()=>protectedKinds.includes(kind.value)&&!demo.loggedIn)
onLoad(q=>{kind.value=q?.kind||'';id.value=q?.id||'';draft.value=demo.drafts[id.value]||'';if(!blocked.value&&kind.value==='chat'&&!demo.read.includes(id.value))demo.read.push(id.value);if(kind.value==='notifications'&&demo.loggedIn&&!demo.read.includes('notice'))demo.read.push('notice')})
const product=computed(()=>products.find(p=>p.id===id.value))
const topic=computed(()=>topics.find(t=>t.id===id.value))
const chat=computed(()=>conversations.find(c=>c.id===id.value))
const favoriteList=computed(()=>products.filter(p=>demo.favorites.includes(p.id)))
const steps=[['01','选择游戏与服务','查看服务内容、计费单位及价格，选择适合自己的商品。'],['02','提交预约与付款','正式流程需填写预约时段与服务需求；付款仅代表提交申请。'],['03','运营安排 · 队友确认','人员足额接受后才预约成功，调整安排需与你确认。'],['04','完成服务 · 验收评价','服务结束后确认交付；如有问题，可联系工作人员处理。']]
const info:Record<string,{icon:string;title:string;body:string}>={
 lottery:{icon:'gift',title:'好玩的活动，正在准备',body:'活动抽奖入口已预留。参与条件、奖品和开奖规则尚未确定，目前不开放抽奖。'},
 assessment:{icon:'assessment',title:'考核中心筹备中',body:'考核内容、报名条件及审核流程将另行公布，当前不会提交考核或授予接单资格。'},
 membership:{icon:'star',title:'会员权益，敬请期待',body:'会员方案仍在设计中，当前不开放购买或自动续费。'},
 join:{icon:'user',title:'让热爱，成为更多人的快乐',body:'加入申请流程正在准备。陪玩须绑定一个游戏分区，并经管理员审核授权，当前不采集个人申请资料。'},
 points:{icon:'gift',title:'860 积分 · 示例',body:'积分获取、兑换规则尚未开放。这里展示的是演示数值，不能兑换真实权益。'},
 balance:{icon:'wallet',title:'¥ 128.00 · 示例余额',body:'当前没有真实账户资金和流水。充值、消费抵扣、提现均未接入，不会发生真实扣款。'},
 games:{icon:'game',title:'更多游戏，陆续相遇',body:'当前演示支持王者荣耀、和平精英、无畏契约和英雄联盟。其他游戏分区敬请期待。'},
 aftersale:{icon:'aftersale',title:'服务遇到问题，我们一起解决',body:'正式业务由运营审核售后请求。当前仅演示售后入口，不会创建真实案件或执行退款。'},
 terms:{icon:'order',title:'用户协议 · 演示说明',body:'正式用户协议尚未发布。此页面用于验证协议阅读与勾选交互；不接受付款，不提供真实交易，不构成正式服务协议。'},
 privacy:{icon:'order',title:'隐私政策 · 演示说明',body:'正式隐私政策尚未发布。本地演示仅保存演示登录标记和收藏，不获取微信身份、手机号或通讯录，也不向服务器传输会话。'},
}
async function order(){if(!demo.loggedIn){requireLogin('detail',{kind:'product',id:id.value});return}if(busy.value||!product.value)return;if(!await confirmDemo('创建演示订单','只创建本地示例记录，不提交预约或真实订单；实际预约表单将在业务接入阶段补充。'))return;busy.value=true;try{createDemoOrder(product.value.id,quantity.value);go('orders',{tab:'待付款'})}catch(e){notify((e as Error).message)}finally{busy.value=false}}
function favorite(){if(!demo.loggedIn){requireLogin('detail',{kind:'product',id:id.value});return}toggleFavorite(id.value);notify(demo.favorites.includes(id.value)?'已加入演示收藏':'已取消收藏')}
function saveDraft(){if(!draft.value.trim()){notify('请先输入草稿内容');return}demo.drafts[id.value]=draft.value.trim();notify('草稿仅保存在本次会话中，未发送')}
async function logout(){if(await confirmDemo('退出演示账号','退出后清空本次演示订单修改、会话草稿及演示收藏。')){logoutDemo();go('profile')}}
</script>
<template><PageShell :title="titles[kind]||'页面未找到'" backable><view class="body safe-bottom">
 <view v-if="blocked" class="blank-page"><text class="muted">请先登录演示账号查看</text><button class="ui-btn primary" @click="requireLogin('detail',{kind,id})">演示登录</button></view>
 <template v-else-if="kind==='product'&&product"><image :src="`/static/art/product-${product.art}.png`" class="detail-cover" mode="aspectFill"/><view class="section-head"><view><view class="title">{{product.title}}</view><view class="small muted">{{product.game}} · 1小时</view></view><button class="ui-btn" :aria-label="demo.favorites.includes(id)?'取消收藏':'收藏商品'" @click="favorite"><AppIcon name="star" :active="demo.favorites.includes(id)"/></button></view><view class="price">¥{{money(product.price)}}<text class="old">¥{{money(product.original)}}</text></view><view class="card description"><view class="heading">一起享受游戏的快乐</view><view class="muted paragraph">{{product.tagline}}。服务内容、人员安排与预约时段需在正式下单前确认。</view><view class="between"><text>演示购买数量</text><view class="row gap"><button class="ui-btn quantity" :disabled="quantity<=1" @click="quantity--">−</button><text>{{quantity}}</text><button class="ui-btn quantity" :disabled="quantity>=5" @click="quantity++">＋</button></view></view></view><view class="demo-note">这里只验证商品到订单的页面流程，不创建真实预约，不保证上分结果。</view><button class="ui-btn primary wide" :disabled="busy" @click="order">创建演示订单 · ¥{{money(product.price*quantity)}}</button></template>
 <template v-else-if="kind==='favorites'"><view class="demo-note">收藏会保存在当前设备，退出演示账号后重置。</view><view class="grid"><ProductCard v-for="p in favoriteList" :key="p.id" :product="p"/></view><EmptyState v-if="!favoriteList.length" title="还没有收藏" description="在服务详情中点击星标，留下你喜欢的商品。"/></template>
 <template v-else-if="kind==='topic'&&topic"><view class="topic-detail"><text class="small accent"># {{topic.game}}</text><view class="title">{{topic.title}}</view><view class="small muted">{{topic.author}} · {{topic.count}} 条讨论 · 示例</view><view class="paragraph">{{topic.body}}</view><view class="divider"/><view class="heading">讨论预览</view><view class="sample-comment"><text class="accent">小满</text><view>一起友好交流，快乐游戏～</view></view><view class="demo-note">话题与回复均为示例，发布和实时互动尚未开放。</view></view></template>
 <template v-else-if="kind==='chat'&&chat"><view class="row gap chat-header"><view :class="['avatar',chat.color]">{{chat.name.slice(0,1)}}</view><view><view class="heading">{{chat.name}}</view><view class="small muted">示例会话 · 不连接真实联系人</view></view></view><view class="chat-bubble">{{chat.text}}</view><view class="form-label">会话草稿（不会发送）</view><textarea v-model="draft" class="card draft" placeholder="写下一句问候，试试保存草稿…" :maxlength="300"/><view class="between small muted draft-count"><text>仅本次会话内保留</text><text>{{draft.length}}/300</text></view><button class="ui-btn primary wide" @click="saveDraft">保存草稿</button></template>
 <template v-else-if="kind==='process'"><view class="demo-note">了解从下单到完成服务的四个步骤。</view><view class="stack"><view v-for="step in steps" :key="step[0]" class="card"><text class="step-number">{{step[0]}}</text><view class="heading">{{step[1]}}</view><view class="muted paragraph">{{step[2]}}</view></view></view></template>
 <template v-else-if="kind==='support'"><view class="soft support-banner"><AppIcon name="headset" active :size="44"/><view class="title">很高兴为你解答</view><view class="muted small">这里整理了常见问题，帮助你快速了解游伴。</view></view><view class="stack"><button class="ui-btn card faq" @click="detail('process')">如何下单与预约？<text>›</text></button><button class="ui-btn card faq" @click="detail('aftersale')">服务问题与退款如何处理？<text>›</text></button><button class="ui-btn card faq" @click="detail('join')">如何加入成为游戏搭子？<text>›</text></button></view><view class="demo-note">人工客服尚未接入；以上为说明入口，不会发起真实客服会话。</view></template>
 <template v-else-if="kind==='settings'"><view class="card setting"><text>当前模式</text><text class="muted small">本地交互演示</text></view><button class="ui-btn card faq" @click="detail('terms')">用户协议<text>›</text></button><button class="ui-btn card faq" @click="detail('privacy')">隐私政策<text>›</text></button><button v-if="demo.loggedIn" class="ui-btn secondary wide logout" @click="logout">退出演示账号</button><button v-else class="ui-btn primary wide logout" @click="go('login')">进入演示登录</button></template>
 <template v-else-if="kind==='notifications'"><view class="card notification"><view class="heading">订单状态提醒</view><view class="muted paragraph">你的演示订单已更新，可前往订单页查看当前分类。</view><button class="ui-btn secondary button-small" @click="go('orders')">查看演示订单</button></view><view class="card notification"><view class="heading">欢迎来到游伴</view><view class="muted paragraph">找到同好，一起快乐开局。本页消息仅用于交互预览。</view></view></template>
 <template v-else-if="kind==='account'"><view class="card stack"><view class="avatar">游</view><view class="between"><text>名称</text><text>快乐玩家</text></view><view class="between"><text>ID</text><text>100086</text></view><view class="demo-note">本地演示账号，不对应真实微信身份。</view></view></template>
 <template v-else-if="info[kind]"><view class="info-panel"><view class="info-icon"><AppIcon :name="info[kind].icon" active :size="46"/></view><view class="title">{{info[kind].title}}</view><view class="muted paragraph">{{info[kind].body}}</view><button class="ui-btn secondary" @click="go('home')">返回首页</button></view></template>
 <EmptyState v-else title="没有找到这项内容" description="内容可能不存在，请返回上一页重新选择。"/>
</view></PageShell></template>
<style scoped>.detail-cover{width:100%;height:350rpx;border-radius:30rpx;margin-top:22rpx}.description{margin-top:30rpx}.paragraph{font-size:27rpx;line-height:1.9;margin:22rpx 0 32rpx}.quantity{background:#eeebf3;width:60rpx;height:60rpx;border-radius:18rpx;line-height:60rpx}.topic-detail{padding-top:28rpx}.topic-detail .title{margin:26rpx 0}.sample-comment{margin-top:30rpx;font-size:27rpx}.sample-comment view{margin-top:14rpx}.chat-header{margin:32rpx 0}.chat-bubble{padding:28rpx;background:#e6deef;border-radius:0 30rpx 30rpx;margin:46rpx 30rpx 76rpx 0}.draft{height:250rpx;padding:26rpx}.draft-count{margin:20rpx 0 34rpx}.step-number{display:block;font-size:40rpx;color:#8875aa;margin-bottom:14rpx}.support-banner{padding:40rpx 30rpx;margin:22rpx 0 36rpx}.support-banner .title{margin:24rpx 0 16rpx}.faq{width:100%;display:flex;justify-content:space-between;text-align:left;margin:24rpx 0}.setting{display:flex;justify-content:space-between;margin:24rpx 0}.logout{margin-top:60rpx}.notification{margin-top:30rpx}.info-panel{text-align:center;padding:72rpx 18rpx}.info-icon{display:flex;align-items:center;justify-content:center;margin:0 auto 36rpx;background:#e6deef;width:160rpx;height:160rpx;border-radius:48rpx}.info-panel .title{font-size:38rpx}.info-panel .secondary{margin-top:50rpx}</style>
