<script setup lang="ts">
import { ref, computed } from 'vue'
import { onLoad, onShow, onHide, onUnload } from '@dcloudio/uni-app'
import PageShell from '../../components/PageShell.vue'
import { demo, validateSession } from '../../store'
import { getConversation, sendMessage, serviceProgress } from '../../services/messages'
import { confirmOrder } from '../../services/orders'
import type { ApiConversationDetail } from '../../api/types'
import { notify, confirmDemo, detail } from '../../navigation'

const convId=ref(0), conversation=ref<ApiConversationDetail|null>(null), draft=ref('')
const busy=ref(false), loading=ref(false), error=ref(''), scrollTarget=ref('')
const title=computed(()=>!conversation.value?'订单对话':conversation.value.viewer_role==='USER'?conversation.value.partner_name:conversation.value.user_name)
const states:Record<string,string>={ACCEPTED:'已接单 · 待陪玩开始',IN_SERVICE:'服务中',PENDING_CONFIRMATION:'待用户确认完成',COMPLETED:'已完成',CANCELLED:'已取消'}
const eventTitles:Record<string,string>={SERVICE_STARTED:'服务已开始',COMPLETION_REQUEST:'服务完成申请',COMPLETION_CONFIRMED:'用户已确认完成'}
const action=computed(()=>{
  const c=conversation.value
  if(c?.viewer_role==='PARTNER' && c.service.status==='ACCEPTED')return 'start'
  if(c?.viewer_role==='PARTNER' && c.service.status==='IN_SERVICE')return 'complete'
  if(c?.viewer_role==='USER' && c.service.status==='PENDING_CONFIRMATION')return 'confirm'
  return null
})
const actionLabels={start:'开始服务',complete:'申请完成服务',confirm:'同意完成服务'}
let viewerId=0
let visible=false, refreshing=false, sequence=0, timer:ReturnType<typeof setInterval>|undefined
let pendingSend:{content:string;key:string}|undefined
const actionKeys:Record<string,string>={}
function timestamp(value:string|null){return value?new Date(value).toLocaleString():''}
async function refresh(silent=false){
  if(!visible||busy.value||refreshing||!convId.value)return
  refreshing=true
  const run=++sequence
  if(!silent)loading.value=true
  try{
    const data=await getConversation(convId.value)
    if(run!==sequence||!visible)return
    const previous=conversation.value?.messages
    const last=data.messages[data.messages.length-1]
    const changed=previous?.[previous.length-1]?.id!==last?.id
    conversation.value=data;error.value=''
    if(changed)scrollTarget.value=last?'message-'+last.id:''
  }catch(e){if(run===sequence)error.value=(e as Error).message}
  finally{refreshing=false;loading.value=false}
}
async function send(){
  const content=draft.value.trim()
  if(!content||busy.value||!conversation.value)return
  if(!pendingSend||pendingSend.content!==content)pendingSend={content,key:'chat-'+convId.value+'-'+Date.now()}
  busy.value=true;sequence++
  try{
    const msg=await sendMessage(convId.value,content,pendingSend.key)
    if(!conversation.value.messages.some(m=>m.id===msg.id))conversation.value.messages.push(msg)
    scrollTarget.value='message-'+msg.id
    draft.value='';pendingSend=undefined
  }catch(e){notify((e as Error).message)}
  finally{busy.value=false;void refresh(true)}
}
async function progress(){
  const c=conversation.value, kind=action.value
  if(!c||!kind||busy.value)return
  const version=c.service.version, order=c.order
  busy.value=true
  try{
    const accepted=await confirmDemo(actionLabels[kind],kind==='start'?'点击确认即记录开始服务时间。':kind==='complete'?'将在本对话中发送完成申请，用户同意后订单才会完成。':'请确认约定服务已完成。确认后订单完成并计入陪玩榜单。',kind==='start'?'确认开始':kind==='complete'?'发送申请':'同意完成')
    if(!accepted)return
    sequence++
    const identity=kind+'-'+order+'-'+version
    const key=actionKeys[identity]||=(identity+'-'+Date.now())
    if(kind==='confirm')await confirmOrder(order,key,version)
    else await serviceProgress(order,kind,version,key)
    delete actionKeys[identity]
    notify(kind==='confirm'?'订单已完成，榜单已同步':kind==='complete'?'已发送完成申请':'服务已开始')
  }catch(e){notify((e as Error).message)}
  finally{busy.value=false;void refresh(true)}
}
function stop(){visible=false;sequence++;if(timer)clearInterval(timer);timer=undefined}
onLoad(options=>{convId.value=Number(options?.id||0)})
onShow(async()=>{
  visible=true
  try{
    await validateSession()
    const id=demo.me?.id||0
    if(viewerId!==id){conversation.value=null;draft.value='';pendingSend=undefined;viewerId=id}
    if(!demo.loggedIn){conversation.value=null;error.value='请先登录';return}
    if(visible){void refresh();if(timer)clearInterval(timer);timer=setInterval(()=>void refresh(true),5000)}
  }
  catch(e){error.value=(e as Error).message}
})
onHide(stop);onUnload(stop)
</script>
<template>
  <PageShell :title="title||'订单对话'" backable compact fill>
    <template #actions><button v-if="conversation" class="ui-btn small accent" @click="detail('support',conversation.order_no)">联系客服</button><button class="ui-btn refresh" :disabled="loading||busy" @click="refresh()">刷新</button></template>
    <view class="chat">
      <view v-if="conversation" class="service-card">
        <view class="service-product">{{conversation.product_title}}</view>
        <view class="service-number">{{conversation.order_no}}</view>
        <view class="service-state">{{states[conversation.service.status]||conversation.service.status}}</view>
        <view v-if="conversation.service.started_at" class="service-time">开始：{{timestamp(conversation.service.started_at)}}</view>
        <view v-if="conversation.service.completion_requested_at" class="service-time">申请完成：{{timestamp(conversation.service.completion_requested_at)}}</view>
        <view v-if="conversation.service.completed_at" class="service-time">用户确认：{{timestamp(conversation.service.completed_at)}}</view>
        <view v-if="conversation.service.status==='PENDING_CONFIRMATION'" class="service-hint">{{conversation.viewer_role==='USER'?'请核实服务后确认；如有未完成内容，可先在下方沟通或联系客服。':'已发起完成申请，等待用户同意；确认前不计入完成榜单。'}}</view>
        <button v-if="action" class="ui-btn service-action" :disabled="busy" @click="progress">{{actionLabels[action]}}</button>
      </view>
      <view v-if="loading&&!conversation" class="chat-notice">加载中…</view>
      <view v-if="error" class="chat-notice">{{error}}<button class="ui-btn refresh" @click="refresh()">重试</button></view>
      <scroll-view scroll-y class="msg-list" :scroll-into-view="scrollTarget" :scroll-with-animation="true">
        <view v-for="m in conversation?.messages||[]" :id="'message-'+m.id" :key="m.id" class="msg-row" :class="m.kind!=='TEXT'?'event':m.sender===conversation?.viewer_role?'mine':'theirs'">
          <view v-if="m.kind!=='TEXT'" class="event-card"><view class="event-title">{{eventTitles[m.kind]}}</view><view>{{m.content}}</view><view class="event-time">{{timestamp(m.created_at)}}</view></view>
          <view v-else class="bubble">{{m.content}}</view>
        </view>
        <view v-if="conversation&&!conversation.messages.length" class="chat-notice">还没有消息，打个招呼吧</view>
      </scroll-view>
      <view class="input-bar">
        <view class="input-frame"><input v-model="draft" class="chat-input" placeholder="输入消息…" placeholder-class="chat-placeholder" maxlength="2000" confirm-type="send" :cursor-spacing="20" :adjust-position="true" :disabled="!demo.loggedIn||!conversation||busy" @confirm="send"/></view>
        <button class="ui-btn send" :disabled="busy||!draft.trim()||!conversation" @click="send">发送</button>
      </view>
    </view>
  </PageShell>
</template>
<style scoped>
.chat{flex:1!important;min-height:0;display:flex;flex-direction:column;padding:0 16px;overflow:hidden}.refresh{font-size:13px;color:#80699e;padding:8px}.service-card{flex-shrink:0;background:#eee8f4;border-radius:14px;padding:12px 14px;margin:4px 0 8px}.service-product{font-size:14px;font-weight:600}.service-number{font-size:10px;color:#82758c;overflow-wrap:anywhere;margin:3px 0}.service-state{font-size:13px;color:#71528d;font-weight:600;margin:5px 0}.service-time{font-size:11px;color:#756c7b;line-height:1.6}.service-hint{font-size:11px;color:#756c7b;margin-top:6px}.service-action{font-size:14px;background:#80699e;color:#fff;border-radius:20px;padding:9px 16px;margin-top:10px}.msg-list{flex:1;height:0;min-height:0;overflow:hidden}.msg-row{display:flex;margin:12px 0}.mine{justify-content:flex-end}.theirs{justify-content:flex-start}.bubble{max-width:80%;padding:10px 14px;border-radius:14px;font-size:15px;line-height:1.6;white-space:pre-wrap;overflow-wrap:anywhere}.mine .bubble{background:#80699e;color:#fff}.theirs .bubble{background:#fff;color:#3c3644}.event{justify-content:center}.event-card{width:100%;padding:12px 14px;background:#fff;border:1px solid #e6dfed;border-radius:12px;color:#65576f;font-size:12px;line-height:1.7}.event-title{font-weight:600;color:#71528d;font-size:14px}.event-time{font-size:10px;color:#94879e;margin-top:4px}.input-bar{display:flex;flex-shrink:0;gap:12px;align-items:center;padding:10px 0;padding-bottom:calc(10px + env(safe-area-inset-bottom));background:#f6f5f2}.input-frame{flex:1;min-width:0;background:#fff;border:1px solid #e5deeb;border-radius:24px;padding:0 14px}.chat-input{display:block;width:100%;height:44px;min-height:44px;padding:0;color:#303345;font-size:16px;line-height:44px}.chat-input :deep(.uni-input-input){height:100%;line-height:normal;color:#303345}.chat-placeholder{color:#9b90a4}.send{flex-shrink:0;color:#80699e;font-size:15px;min-height:44px;display:flex;align-items:center}.chat-notice{text-align:center;font-size:13px;color:#82758c;padding:16px 0;flex-shrink:0}
</style>
