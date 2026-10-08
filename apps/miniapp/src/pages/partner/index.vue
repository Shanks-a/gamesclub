<script setup lang="ts">
import { ref, computed } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import PageShell from '../../components/PageShell.vue'
import { money } from '../../domain'
import { listPartnerOrders, partnerAction } from '../../services/partner'
import type { ApiOrder } from '../../api/types'
import { mediaUrl } from '../../api/client'
import { notify, requireLogin, confirmDemo } from '../../navigation'
import { demo, validateSession } from '../../store'
const rows = ref<ApiOrder[]>([]), tab = ref('待处理'), error = ref(''), busy = ref(false), loading = ref(false)
const states: Record<string,string> = { PENDING_ACCEPTANCE:'待陪玩确认', ACCEPTED:'已接单', IN_SERVICE:'服务中', PENDING_CONFIRMATION:'待验收', COMPLETED:'已完成', CANCELLED:'已取消' }
const slotLabel: Record<string,string> = { morning:'上午', afternoon:'下午', evening:'晚上' }
// 待处理 = 需要陪玩操作的；历史 = 其余
const pending = computed(() => rows.value.filter(o => ['PENDING_ACCEPTANCE','ACCEPTED','IN_SERVICE'].includes(o.status)))
const history = computed(() => rows.value.filter(o => ['PENDING_CONFIRMATION','COMPLETED','CANCELLED'].includes(o.status)))
const list = computed(() => tab.value === '待处理' ? pending.value : history.value)
const keys: Record<string,string> = {}
async function refresh() {
  loading.value = true; error.value = ''
  try {
    await validateSession()
    if (!demo.loggedIn) { rows.value = []; return }
    rows.value = await listPartnerOrders()
  } catch (e) { error.value = (e as Error).message; rows.value = [] }
  finally { loading.value = false }
}
async function act(order: ApiOrder, action: 'accept'|'reject'|'start'|'complete') {
  const label: Record<string,string> = { accept:'接单', reject:'拒单', start:'开始服务', complete:'完成服务' }
  const tip: Record<string,string> = { accept:'确认接下这单并开始准备服务？', reject:'拒单后该订单将回到待派单，由运营重新指派。', start:'确认已开始为该客户服务？', complete:'确认服务已完成，等待客户验收？' }
  if (busy.value || !await confirmDemo(label[action], tip[action])) return
  busy.value = true
  const identity = action + '-' + order.id
  const key = keys[identity] ||= identity + '-' + Date.now()
  try {
    const updated = await partnerAction(order.id, action, key)
    rows.value = rows.value.map(o => o.id === updated.id ? updated : o)
    delete keys[identity]
    notify('操作成功')
  } catch (e) { notify((e as Error).message) }
  finally { busy.value = false }
}
onLoad(options => { tab.value = options?.tab || '待处理' })
onShow(() => { void refresh() })
</script>
<template>
  <PageShell title="陪玩工作台" backable>
    <view class="body">
      <view v-if="demo.loggedIn && demo.me" class="status-banner" :class="demo.me.partner_active ? 'on' : 'off'">
        <view class="dot" />
        <text>{{ demo.me.partner_active ? '接单中' : '已暂停接单' }}</text>
        <text class="hint">{{ demo.me.partner_active ? '管理员为你开启了接单，可正常接单服务' : '接单权限已关闭，请联系管理员' }}</text>
      </view>
      <scroll-view scroll-x><view class="pills"><button v-for="t in ['待处理','历史']" :key="t" class="ui-btn pill" :class="{active:tab===t}" @click="tab=t">{{t}}</button></view></scroll-view>
      <view class="demo-note">运营派单后在此接单/拒单；开始与完成服务需你主动操作。</view>
      <button v-if="!demo.loggedIn" class="primary" @click="requireLogin('partner')">请先登录</button>
      <view v-else-if="loading" class="empty">加载中…</view>
      <view v-else-if="error" class="empty">{{error}}<button @click="refresh">重试</button></view>
      <view v-else>
        <view v-for="o in list" :key="o.id" class="card order">
          <text class="small">{{o.order_no}}</text>
          <view class="row gap"><image :src="mediaUrl(o.cover_url_snapshot)" class="cover"/><view><view>{{o.product_title_snapshot}}</view><text class="muted">{{o.game_name_snapshot}} × {{o.quantity}}</text></view></view>
          <view v-if="o.appointment_date" class="tiny muted">预约：{{o.appointment_date}} {{slotLabel[o.appointment_slot||'']||o.appointment_slot}}</view>
          <view>订单金额 ¥{{money(o.total_amount_cents)}}</view>
          <view class="tiny muted">{{o.created_at}} · {{states[o.status]||o.status}}</view>
          <view v-if="o.status==='PENDING_ACCEPTANCE'" class="row gap"><button class="secondary" :disabled="busy" @click="act(o,'reject')">拒单</button><button class="primary" :disabled="busy" @click="act(o,'accept')">接单</button></view>
          <view v-else-if="o.status==='ACCEPTED'" class="row gap"><button class="primary" :disabled="busy" @click="act(o,'start')">开始服务</button></view>
          <view v-else-if="o.status==='IN_SERVICE'" class="row gap"><button class="primary" :disabled="busy" @click="act(o,'complete')">完成服务</button></view>
        </view>
        <view v-if="!list.length" class="empty">{{ tab==='待处理' ? '暂无待处理订单' : '暂无历史订单' }}</view>
      </view>
    </view>
  </PageShell>
</template>
<style scoped>
.pills{padding:20rpx 0}.order{margin:24rpx 0;overflow-wrap:anywhere}.order .row{margin:20rpx 0}.cover{width:130rpx;height:130rpx;border-radius:20rpx}
.status-banner{display:flex;align-items:center;gap:16rpx;padding:24rpx 28rpx;border-radius:20rpx;margin-bottom:8rpx;font-size:27rpx;font-weight:600}.status-banner.on{background:#f0ecf7;color:#5d4a82}.status-banner.off{background:#f7ecec;color:#a25656}.status-banner .dot{width:14rpx;height:14rpx;border-radius:50%}.status-banner.on .dot{background:#80699e}.status-banner.off .dot{background:#c96a6a}.status-banner .hint{margin-left:auto;font-size:21rpx;font-weight:400;color:#999}
</style>
