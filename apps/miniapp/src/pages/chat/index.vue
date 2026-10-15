<script setup lang="ts">
import { ref, computed } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import PageShell from '../../components/PageShell.vue'
import { demo, validateSession } from '../../store'
import { listMessages, sendMessage, listConversations } from '../../services/messages'
import type { ApiMessage } from '../../api/types'
import { notify } from '../../navigation'
const convId = ref(0)
const title = ref('会话')
const msgs = ref<ApiMessage[]>([])
const draft = ref('')
const busy = ref(false), loading = ref(false), error = ref('')
const keys: Record<string,string> = {}
const myId = computed(() => demo.me?.id ?? 0)
const currentCustomer = ref(0)
function isMine(m: ApiMessage) {
  const iAmCustomer = myId.value === currentCustomer.value
  return (m.sender === 'USER') === iAmCustomer
}
async function refresh() {
  loading.value = true; error.value = ''
  try {
    await validateSession()
    msgs.value = await listMessages(convId.value)
    // 从会话列表取标题与客户 id
    const convs = await listConversations()
    const c = convs.find(x => x.id === convId.value)
    if (c) {
      currentCustomer.value = c.user
      title.value = myId.value === c.user ? (c.partner_name || '陪玩') : (c.user_name || '客户')
    }
  } catch (e) { error.value = (e as Error).message; msgs.value = [] }
  finally { loading.value = false }
}
async function send() {
  const text = draft.value.trim()
  if (!text || busy.value) return
  busy.value = true
  const key = keys[convId.value] ||= convId.value + '-' + Date.now()
  try {
    const msg = await sendMessage(convId.value, text, key)
    msgs.value = [...msgs.value, msg]
    draft.value = ''
    delete keys[convId.value]
  } catch (e) { notify((e as Error).message) }
  finally { busy.value = false }
}
onLoad(options => { convId.value = Number(options?.id || 0) })
onShow(() => { if (convId.value) void refresh() })
</script>
<template>
  <PageShell :title="title" backable>
    <view class="chat">
      <view v-if="loading" class="empty muted">加载中…</view>
      <view v-else-if="error" class="empty muted">{{error}}<button class="ui-btn small" @click="refresh">重试</button></view>
      <scroll-view v-else scroll-y class="msg-list">
        <view v-for="m in msgs" :key="m.id" class="msg-row" :class="isMine(m)?'mine':'theirs'">
          <view class="bubble">{{m.content}}</view>
        </view>
        <view v-if="!msgs.length" class="empty muted">还没有消息，打个招呼吧</view>
      </scroll-view>
      <view class="input-bar">
        <input v-model="draft" class="input" placeholder="输入消息…" confirm-type="send" @confirm="send" :disabled="!demo.loggedIn"/>
        <button class="ui-btn accent send" :disabled="busy || !draft.trim()" @click="send">发送</button>
      </view>
    </view>
  </PageShell>
</template>
<style scoped>
.chat{display:flex;flex-direction:column;height:calc(100vh - 220rpx);padding:0 30rpx}.msg-list{flex:1;overflow:hidden;padding:20rpx 0}.msg-row{display:flex;margin:16rpx 0}.msg-row.mine{justify-content:flex-end}.msg-row.theirs{justify-content:flex-start}.bubble{max-width:70%;padding:20rpx 26rpx;border-radius:22rpx;font-size:28rpx;line-height:1.5;word-break:break-word}.mine .bubble{background:#80699e;color:#fff;border-bottom-right-radius:6rpx}.theirs .bubble{background:#fff;color:#3c3644;border-bottom-left-radius:6rpx}.input-bar{display:flex;gap:16rpx;align-items:center;padding:16rpx 0 24rpx}.input{flex:1;background:#fff;border-radius:40rpx;padding:18rpx 28rpx;font-size:27rpx}.send{flex-shrink:0}.empty{padding:40rpx 0;text-align:center}
</style>
