<script setup lang="ts">
import { ref, computed } from 'vue'
import { onShow,onHide,onUnload } from '@dcloudio/uni-app'
import PageShell from '../../components/PageShell.vue'
import CommunityAvatar from '../../components/CommunityAvatar.vue'
import EmptyState from '../../components/EmptyState.vue'
import { demo, validateSession } from '../../store'
import { listSupportThreads,type SupportThread } from '../../services/support-chat'
import { requireLogin,go,detail } from '../../navigation'
import { listConversations } from '../../services/messages'
import type { ApiConversation } from '../../api/types'
const supportRows=ref<SupportThread[]>([])
const replyLabel=(state?:string)=>state==='needs_reply'?'待我回复':state==='awaiting_reply'?'已回复 · 等待对方':'尚无消息'
const rows = ref<ApiConversation[]>([])
const loading = ref(false), error = ref('')
const query = ref('')
interface ConversationRow {
  key:string;id:number;kind:'order'|'support';name:string;avatar:string;preview:string;
  time:string;context:string;searchText:string;unread:number;replyState?:string
}
const conversations=computed<ConversationRow[]>(()=>{
  const orders:ConversationRow[]=rows.value.map(c=>{
    const isCustomer=demo.me?.id===c.user
    const name=isCustomer?(c.partner_name||'陪玩'):(c.user_name||'客户')
    return {key:`order-${c.id}`,id:c.id,kind:'order',name,
      avatar:(isCustomer?c.partner_avatar:c.user_avatar)||'',
      preview:c.last_message?.content||c.product_title,time:c.last_message?.created_at||c.created_at,
      context:`${c.product_title} · ${c.order_no}`,searchText:`${c.partner_name} ${c.user_name} ${c.product_title} ${c.order_no} ${c.last_message?.content||''}`,
      unread:c.unread_count,replyState:c.reply_state}
  })
  const support:ConversationRow[]=supportRows.value.map(c=>({
    key:`support-${c.id}`,id:c.id,kind:'support',name:'在线客服',avatar:'',
    preview:c.last_message?.content||'发送消息开始咨询',time:c.last_message?.created_at||c.updated_at,
    context:c.order_no?`订单咨询 · ${c.order_no}`:'一般咨询',
    searchText:`在线客服 ${c.order_no} ${c.order_no?'订单咨询':'一般咨询'} ${c.last_message?.content||''}`,
    unread:c.unread_count,replyState:c.reply_state
  }))
  return [...orders,...support].sort((a,b)=>Date.parse(b.time)-Date.parse(a.time)||a.key.localeCompare(b.key))
})
const list=computed(()=>{
  const term=query.value.trim().toLowerCase()
  return conversations.value.filter(c=>c.searchText.toLowerCase().includes(term))
})
function displayTime(value:string){
  const date=new Date(value),now=new Date()
  if(Number.isNaN(date.getTime()))return ''
  const pad=(n:number)=>String(n).padStart(2,'0')
  if(date.toDateString()===now.toDateString())return `${pad(date.getHours())}:${pad(date.getMinutes())}`
  return `${date.getFullYear()===now.getFullYear()?'':date.getFullYear()+'/'}${pad(date.getMonth()+1)}/${pad(date.getDate())}`
}
function open(c:ConversationRow){go(c.kind==='support'?'support-chat':'chat',{id:String(c.id)})}
let timer:ReturnType<typeof setInterval>|undefined, active=false, reading=false, generation=0
async function refresh(silent=false) {
  if(reading)return
  const version=generation;reading=true
  if(!silent)loading.value=true
  try {
    await validateSession()
    if(!demo.loggedIn){rows.value=[];supportRows.value=[];return}
    const [orders,support]=await Promise.all([listConversations(),listSupportThreads()])
    if(!active||version!==generation)return
    rows.value=orders;supportRows.value=support;error.value=''
  }catch(e){if(active&&version===generation)error.value=(e as Error).message}
  finally{reading=false;loading.value=false}
}
function stop(){active=false;generation++;if(timer)clearInterval(timer);timer=undefined}
onShow(()=>{active=true;void refresh();timer=setInterval(()=>void refresh(true),5000)})
onHide(stop);onUnload(stop)
</script>
<template>
  <PageShell title="会话" subtitle="订单沟通和客服回复，都汇集在这里">
    <template #actions><button v-if="demo.loggedIn" class="ui-btn contact-link" @click="detail('support')">联系客服</button></template>
    <view class="body">
      <view v-if="!demo.loggedIn" class="login-hint row between"><text class="small muted">登录后查看会话</text><button class="ui-btn accent small" @click="requireLogin('messages')">登录 ›</button></view>
      <template v-else>
        <view class="search"><input v-model="query" placeholder="搜索联系人、订单或消息" confirm-type="search"/><button v-if="query" class="ui-btn clear" @click="query=''">清除</button></view>
        <view v-if="loading&&!conversations.length" class="empty muted">加载中…</view>
        <view v-else-if="error" class="load-error">{{error}}<button class="ui-btn small accent" @click="refresh()">重试</button></view>
        <view v-if="list.length" class="conversation-list">
          <button v-for="c in list" :key="c.key" class="ui-btn conversation" @click="open(c)">
            <view class="avatar-wrap"><view v-if="c.kind==='support'" class="support-avatar">客</view><CommunityAvatar v-else :name="c.name" :url="c.avatar" class="person-avatar"/><text v-if="c.unread>0" class="badge">{{c.unread>99?'99+':c.unread}}</text></view>
            <view class="message-text">
              <view class="message-heading"><text class="name">{{c.name}}</text><text class="time">{{displayTime(c.time)}}</text></view>
              <view class="preview">{{c.preview}}</view>
              <view class="message-footer"><text class="context">{{c.context}}</text><text class="reply-state" :class="{'needs-reply':c.replyState==='needs_reply'}">{{replyLabel(c.replyState)}}</text></view>
            </view>
          </button>
        </view>
        <EmptyState v-else-if="!loading&&!error" :title="query.trim()?'没有找到会话':'还没有会话'" :description="query.trim()?'试试联系人姓名、订单号或消息内容。':'联系客服或与接单陪玩沟通后，会话会显示在这里。'"/>
      </template>
    </view>
  </PageShell>
</template>
<style scoped>
.login-hint{padding:22rpx;background:#eae4f1;border-radius:24rpx;margin-top:24rpx}.contact-link{font-size:24rpx;color:#80699e;padding:12rpx 0}.search{margin:26rpx 0 24rpx;height:84rpx;padding:0 24rpx;border-radius:24rpx}.search input{min-width:0;font-size:26rpx;height:84rpx}.load-error{display:flex;align-items:center;justify-content:space-between;gap:16rpx;font-size:24rpx;color:#947272;margin-bottom:20rpx}.conversation-list{background:#fff;border-radius:26rpx;padding:0 24rpx;overflow:hidden}.conversation{display:flex;align-items:center;gap:22rpx;width:100%;text-align:left;padding:28rpx 0;border-bottom:1rpx solid #f0edf3}.conversation:last-child{border-bottom:0}.avatar-wrap{position:relative;flex-shrink:0}.support-avatar,.person-avatar{width:84rpx;height:84rpx;border-radius:26rpx}.support-avatar{display:flex;align-items:center;justify-content:center;background:#80699e;color:#fff;font-size:34rpx;font-weight:600}.badge{position:absolute;top:-8rpx;right:-8rpx;min-width:30rpx;height:30rpx;box-sizing:border-box;padding:0 7rpx;border:3rpx solid #fff;border-radius:20rpx;background:#c56e79;color:#fff;font-size:18rpx;line-height:24rpx;text-align:center}.message-text{flex:1;min-width:0}.message-heading{display:flex;align-items:center;gap:16rpx}.name{flex:1;min-width:0;font-size:29rpx;font-weight:600;color:#303345;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.time{flex-shrink:0;font-size:21rpx;color:#a19aa8}.preview{margin-top:10rpx;font-size:25rpx;color:#77707f;line-height:1.5;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.message-footer{display:flex;align-items:center;gap:12rpx;margin-top:12rpx}.context{flex:1;min-width:0;font-size:20rpx;color:#a19aa8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.reply-state{flex-shrink:0;font-size:20rpx;color:#96909c}.reply-state.needs-reply{color:#80699e;font-weight:500}.empty{padding:40rpx 0;text-align:center}
</style>
