<script setup lang="ts">
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import PageShell from '../../components/PageShell.vue'
import EmptyState from '../../components/EmptyState.vue'
import { demo, validateSession } from '../../store'
import { requireLogin } from '../../navigation'
import { listConversations } from '../../services/messages'
import type { ApiConversation } from '../../api/types'
const rows = ref<ApiConversation[]>([])
const loading = ref(false), error = ref('')
const query = ref('')
const list = computed(() => rows.value.filter(c => `${c.partner_name}${c.user_name}${c.product_title}${c.last_message?.content||''}`.includes(query.value.trim())))
function otherName(c: ApiConversation) {
  // 当前用户是客户（c.user == me.id）则显示陪玩名，否则显示客户名
  const isCustomer = demo.me?.id === c.user
  return isCustomer ? (c.partner_name || '陪玩') : (c.user_name || '客户')
}
function preview(c: ApiConversation) { return c.last_message ? c.last_message.content : c.product_title }
function open(c: ApiConversation) { uni.navigateTo({ url: `/pages/chat/index?id=${c.id}` }) }
async function refresh() {
  loading.value = true; error.value = ''
  try {
    await validateSession()
    if (!demo.loggedIn) { rows.value = []; return }
    rows.value = await listConversations()
  } catch (e) { error.value = (e as Error).message; rows.value = [] }
  finally { loading.value = false }
}
onShow(() => { void refresh() })
</script>
<template>
  <PageShell title="会话" subtitle="与陪玩的订单沟通，都汇集在这里">
    <view class="body">
      <view v-if="!demo.loggedIn" class="login-hint row between">
        <text class="small muted">登录后查看订单会话</text>
        <button class="ui-btn accent small" @click="requireLogin('messages')">登录 ›</button>
      </view>
      <template v-else>
        <view v-if="loading" class="empty muted">加载中…</view>
        <view v-else-if="error" class="empty muted">{{error}}<button class="ui-btn small" @click="refresh">重试</button></view>
        <view v-else-if="!rows.length" class="empty">
          <EmptyState title="还没有会话" description="陪玩接单后，你和陪玩就能在这里沟通。"/>
        </view>
        <template v-else>
          <view class="search"><input v-model="query" placeholder="搜索会话"/><button v-if="query" class="ui-btn clear" @click="query=''">清除</button></view>
          <button v-for="c in list" :key="c.id" class="ui-btn conversation" @click="open(c)">
            <view class="avatar">{{otherName(c).slice(0,1)}}</view>
            <view class="message-text grow">
              <view class="between"><text class="name">{{otherName(c)}}</text><text class="tiny muted">{{c.created_at}}</text></view>
              <view class="between message-bottom">
                <text class="preview">{{preview(c)}}</text>
                <text v-if="c.unread_count>0" class="badge">{{c.unread_count}}</text>
              </view>
              <text class="tiny muted order">{{c.order_no}} · {{c.product_title}}</text>
            </view>
          </button>
          <EmptyState v-if="!list.length" title="没有找到会话" description="试试搜索联系人姓名。"/>
        </template>
      </template>
    </view>
  </PageShell>
</template>
<style scoped>
.login-hint{padding:22rpx;background:#eae4f1;border-radius:24rpx}.search{display:flex;align-items:center;gap:16rpx;padding:16rpx 22rpx;background:#fff;border-radius:16rpx;margin-bottom:8rpx}.conversation{display:flex;gap:28rpx;text-align:left;width:100%;padding:28rpx 0 0}.avatar{width:84rpx;height:84rpx;border-radius:50%;background:#80699e;color:#fff;display:flex;align-items:center;justify-content:center;font-size:34rpx;font-weight:600;flex-shrink:0}.message-text{padding:2rpx 0 32rpx;border-bottom:1px solid #e6e3ea;min-height:130rpx}.name{font-size:30rpx;font-weight:600}.message-bottom{margin-top:12rpx;gap:12rpx}.preview{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:23rpx;color:#747486}.order{font-size:20rpx;color:#b3aeb8;margin-top:8rpx}.badge{width:34rpx;height:34rpx;border-radius:50%;background:#80699e;color:white;font-size:20rpx;text-align:center;line-height:34rpx;flex-shrink:0}.empty{padding:40rpx 0;text-align:center}
</style>
