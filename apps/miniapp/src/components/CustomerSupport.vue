<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getSupportConfig, type SupportConfig } from '../services/support'
import { demo } from '../store'
import { openSupportThread } from '../services/support-chat'
import { notify, go, requireLogin } from '../navigation'
const props=defineProps<{orderNo?:string}>()
const config=ref<SupportConfig>(), loading=ref(true), error=ref('')
const path='/pages/orders/index?tab='+encodeURIComponent('待派单')
const title=computed(()=>props.orderNo?`订单咨询 ${props.orderNo}`:'联系客服')
async function load(){loading.value=true;error.value='';try{config.value=await getSupportConfig()}catch(e){error.value=(e as Error).message}finally{loading.value=false}}
function copyOrder(){if(props.orderNo)uni.setClipboardData({data:props.orderNo,fail:()=>notify('复制失败，请手动记录订单号')})}
function enterprise(){
  if(!config.value||config.value.mode!=='enterprise')return
  // #ifdef MP-WEIXIN
  if(typeof uni.openCustomerServiceChat!=='function'){notify('请更新微信后重试');return}
  uni.openCustomerServiceChat({corpId:config.value.corp_id,extInfo:{url:config.value.url},
    showMessageCard:!!props.orderNo,sendMessageTitle:title.value,sendMessagePath:path,
    fail:()=>notify('暂时无法打开客服，请稍后重试')})
  // #endif
  // #ifdef H5
  window.open(config.value.url,'_blank','noopener,noreferrer')
  // #endif
}
const opening=ref(false)
async function openChat(){
  if(!demo.loggedIn){requireLogin('detail',{kind:'support',id:props.orderNo||''});return}
  if(opening.value)return
  opening.value=true
  try{const thread=await openSupportThread(props.orderNo);go('support-chat',{id:String(thread.id)})}catch(e){notify((e as Error).message)}finally{opening.value=false}
}
onMounted(load)
</script>
<template>
  <view class="support-card">
    <button class="primary" :disabled="opening" @click="openChat">{{opening?'正在连接…':'进入在线客服'}}</button>
    <view class="small muted description">支持文字沟通，回复会保存在「消息」中。</view>
    <view v-if="orderNo" class="order-context"><text>咨询订单：{{orderNo}}</text><button class="ui-btn copy" @click="copyOrder">复制订单号</button></view>
    <view v-if="loading" class="muted small">正在加载客服信息…</view>
    <view v-else-if="error" class="small">{{error}}<button class="secondary" @click="load">重新加载</button></view>
    <template v-else-if="config">
      <view v-if="config.mode==='disabled'" class="notice">可直接使用上方在线客服。</view>
      <template v-else-if="config.mode==='wechat'">
        <!-- #ifdef MP-WEIXIN -->
        <button class="primary" open-type="contact" :session-from="orderNo?'order:'+orderNo:'support'" :show-message-card="!!orderNo" :send-message-title="title" :send-message-path="path">联系微信客服</button>
        <!-- #endif -->
        <!-- #ifndef MP-WEIXIN -->
        <view class="notice">请在微信小程序内联系在线客服。</view>
        <!-- #endif -->
      </template>
      <button v-else-if="config.mode==='enterprise'" class="primary" @click="enterprise">联系企业微信客服</button>
      <view v-if="config.notice" class="small muted description">{{config.notice}}</view>
      <view v-if="config.mode!=='disabled'&&orderNo" class="small muted description">进入客服后可发送订单卡片，或粘贴订单号，方便客服查询。</view>
    </template>
  </view>
</template>
<style scoped>
.support-card{padding:28rpx;background:#fff;border-radius:24rpx;margin:24rpx 0}.order-context{display:flex;flex-direction:column;align-items:flex-start;gap:12rpx;font-size:24rpx;overflow-wrap:anywhere;margin-bottom:24rpx}.copy{color:#80699e;font-size:24rpx;padding:8rpx 0}.notice{font-size:27rpx;line-height:1.7;color:#60586d}.description{margin-top:18rpx;white-space:pre-wrap;line-height:1.7}
</style>
