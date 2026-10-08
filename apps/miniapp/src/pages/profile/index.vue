<script setup lang="ts">
import PageShell from '../../components/PageShell.vue'
import AppIcon from '../../components/AppIcon.vue'
import { orderTabs } from '../../domain'
import { demo } from '../../store'
import { detail, requireLogin, go } from '../../navigation'
import { mediaUrl } from '../../api/client'
const services=[{icon:'wallet',title:'余额查看',sub:'演示 ¥ 128.00',kind:'balance'},{icon:'star',title:'我的收藏',sub:'查看喜欢的商品',kind:'favorites'},{icon:'gift',title:'积分中心',sub:'演示 860 积分',kind:'points'},{icon:'user',title:'我要加入',sub:'成为游戏搭子',kind:'join'}]
</script>
<template><PageShell title="我的"><template #actions><button class="ui-btn" aria-label="设置" @click="detail('settings')"><AppIcon name="settings"/></button><button class="ui-btn" aria-label="通知" @click="requireLogin('detail',{kind:'notifications'})"><AppIcon name="notification"/></button></template>
 <view class="body"><button class="ui-btn profile row" @click="requireLogin('detail',{kind:'account'})"><image v-if="demo.me?.avatar_url" :src="mediaUrl(demo.me.avatar_url)" class="avatar avatar-img" mode="aspectFill"/><view v-else class="avatar">游</view><view class="grow profile-text"><view class="profile-name">{{demo.me?.nickname||(demo.loggedIn?'微信玩家':'点击登录游伴')}}</view><view class="muted small">{{demo.me?('ID：'+demo.me.id+(demo.me.nickname&&demo.me.nickname!=='微信玩家'?'':' · 完善资料')):(demo.loggedIn?'ID：100086 · 演示账号':'与同好相遇，发现游戏乐趣')}}</view></view><text class="muted">›</text></button>
  <button class="ui-btn member soft" @click="detail('membership')"><view class="eyebrow">CLUB MEMBERSHIP</view><view class="between"><text class="title">会员中心</text><text class="accent small">筹备中</text></view><view class="small muted">更多专属权益，敬请期待</view></button>
  <view class="section-head"><text class="heading">我的订单</text><button class="ui-btn link" @click="requireLogin('orders')">全部订单 ›</button></view>
  <view class="order-shortcuts card"><button class="ui-btn" v-for="(tab,i) in orderTabs" :key="tab" @click="requireLogin('orders',{tab})"><AppIcon :name="['wallet','order','game','headset','star'][i]" active :size="23"/><text>{{tab}}</text></button></view>
  <view class="section-head"><text class="heading">我的服务</text><button class="ui-btn link" @click="requireLogin('services')">全部服务 ›</button></view>
  <view class="service-grid card"><button v-for="item in services" :key="item.kind" class="ui-btn row" @click="requireLogin('detail',{kind:item.kind})"><AppIcon :name="item.icon" active/><view><view class="service-name">{{item.title}}</view><view class="tiny muted">{{demo.loggedIn?item.sub:'登录后查看'}}</view></view></button></view>
  <button v-if="demo.me?.is_partner" class="ui-btn partner-entry row" @click="go('partner')"><AppIcon name="user" active/><view><view class="service-name">陪玩工作台</view><view class="tiny muted">{{demo.me.partner_active?'接单中 · 处理派单与服务':'已暂停接单'}}</view></view><text class="muted">›</text></button>
  <view class="footnote">热爱游戏，也热爱相遇</view>
 </view>
</PageShell></template>
<style scoped>
.profile{text-align:left;width:100%;padding:32rpx 0 44rpx;gap:28rpx}.profile .avatar{width:130rpx;height:130rpx;border-radius:44rpx;font-size:58rpx}.avatar-img{object-fit:cover}.profile-name{font-size:42rpx;font-weight:700;margin-bottom:12rpx}.member{display:block;width:100%;padding:30rpx;text-align:left}.eyebrow{font-size:19rpx;letter-spacing:1rpx;color:#8875aa;font-weight:700;margin-bottom:18rpx}.member .small{margin-top:8rpx}.order-shortcuts{display:flex;padding:34rpx 8rpx}.order-shortcuts button{flex:1;display:flex;flex-direction:column;align-items:center;gap:22rpx;white-space:nowrap;font-size:21rpx}.service-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:40rpx 22rpx;padding:32rpx}.service-grid button{gap:19rpx;text-align:left}.service-name{font-size:25rpx;font-weight:600;margin-bottom:8rpx}
.partner-entry{width:100%;margin-top:24rpx;padding:28rpx 32rpx;gap:19rpx;text-align:left;border:1rpx solid #e6e0f0;background:#f7f4fb;border-radius:20rpx}
</style>
