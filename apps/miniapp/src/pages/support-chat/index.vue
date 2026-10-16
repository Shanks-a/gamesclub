<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { onLoad,onShow,onHide,onUnload } from '@dcloudio/uni-app'
import PageShell from '../../components/PageShell.vue'
import { getSupportThread,sendSupportMessage,messageKey,type SupportDetail } from '../../services/support-chat'
import { notify } from '../../navigation'
import { demo } from '../../store'
const displayTime=(value:string)=>new Date(value).toLocaleString('zh-CN',{hour12:false})
const id=ref(0), thread=ref<SupportDetail|null>(null), draft=ref(''), error=ref(''), sending=ref(false), anchor=ref('')
let timer:ReturnType<typeof setInterval>|undefined, active=false, reading=false, generation=0
let retry:{content:string;key:string}|undefined, owner:number|undefined
async function refresh(){
  if(!id.value||reading||!active)return
  const version=generation;reading=true
  try{const data=await getSupportThread(id.value);if(!active||version!==generation)return
    const changed=thread.value?.messages.at(-1)?.id!==data.messages.at(-1)?.id
    thread.value=data;error.value='';if(changed){anchor.value='';await nextTick();anchor.value='support-end'}
  }catch(e){if(active&&version===generation)error.value=(e as Error).message}finally{reading=false}
}
async function send(){
  const content=draft.value.trim();if(!content||sending.value)return
  sending.value=true;retry=retry?.content===content?retry:{content,key:messageKey()}
  const version=generation
  try{await sendSupportMessage(id.value,content,retry.key);if(version!==generation)return
    if(draft.value.trim()===content)draft.value='';retry=undefined;await refresh()
  }catch(e){if(version===generation)notify((e as Error).message)}finally{sending.value=false}
}
function stop(){active=false;generation++;if(timer)clearInterval(timer);timer=undefined}
onLoad(options=>{id.value=Number(options?.id||0)})
onShow(()=>{if(owner!==demo.me?.id){thread.value=null;draft.value='';retry=undefined;owner=demo.me?.id}active=true;void refresh();timer=setInterval(()=>void refresh(),5000)})
onHide(stop);onUnload(stop)
</script>
<template>
  <PageShell title="在线客服" backable fill>
    <view class="context">{{thread?.order_no?`订单 ${thread.order_no}`:'一般咨询'}} · 客服将在此回复</view>
    <view v-if="error" class="error" @click="refresh">{{error}} · 点击重试</view>
    <scroll-view scroll-y class="history" :scroll-into-view="anchor">
      <view v-if="thread&&!thread.messages.length" class="empty">{{thread.order_no?'请描述您遇到的问题，客服可以查看本次咨询的订单。':'请描述您遇到的问题，回复将保存在这里。'}}</view>
      <view v-for="m in thread?.messages||[]" :key="m.id" class="message" :class="{mine:!m.from_staff}">
        <text class="meta">{{m.from_staff?'客服':'我'}} · {{displayTime(m.created_at)}}</text>
        <view class="bubble">{{m.content}}</view>
        <text v-if="!m.from_staff" class="meta">{{m.read_at?'客服已读':'未读'}}</text>
      </view><view id="support-end" class="end"/>
    </scroll-view>
    <view class="composer"><view class="input-wrap"><input v-model="draft" class="text-input" placeholder="输入消息" maxlength="2000" confirm-type="send" :adjust-position="true" @confirm="send"/></view><button class="ui-btn send" :disabled="sending||!draft.trim()" @click="send">{{sending?'发送中':'发送'}}</button></view>
  </PageShell>
</template>
<style scoped>
.context,.error{padding:16rpx 32rpx;font-size:24rpx;color:#756582;overflow-wrap:anywhere}.error{color:#b34747}.history{flex:1;min-height:0;height:0}.empty{padding:40rpx;color:#888;font-size:26rpx}.message{display:flex;flex-direction:column;align-items:flex-start;padding:12rpx 28rpx}.message.mine{align-items:flex-end}.meta{font-size:21rpx;color:#827789;margin:6rpx 0}.bubble{max-width:85%;white-space:pre-wrap;overflow-wrap:anywhere;background:white;border-radius:18rpx;padding:20rpx;font-size:29rpx;line-height:1.5}.mine .bubble{background:#e7dff3}.end{height:16rpx}.composer{display:flex;align-items:center;gap:20rpx;padding:16rpx 28rpx calc(16rpx + env(safe-area-inset-bottom));background:#f6f5f2}.input-wrap{flex:1;min-width:0;background:white;border-radius:22px;padding:0 16px}.text-input{height:44px;line-height:44px;font-size:16px;color:#302937;width:100%}.send{font-size:28rpx;color:#80699e;flex-shrink:0}.send[disabled]{opacity:.5}
</style>
