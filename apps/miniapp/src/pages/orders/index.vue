<script setup lang="ts">
import { ref, computed } from 'vue'
import { onLoad,onShow } from '@dcloudio/uni-app'
import PageShell from '../../components/PageShell.vue'
import { money } from '../../domain'
import { listOrders,mockPay,cancelOrder } from '../../services/orders'
import type { ApiOrder } from '../../api/types'
import { mediaUrl } from '../../api/client'
import { notify,requireLogin,confirmDemo } from '../../navigation'
import { demo,validateSession } from '../../store'
const rows=ref<ApiOrder[]>([]),tab=ref('待付款'),error=ref(''),busy=ref(false),loading=ref(false)
const states:Record<string,string>={PENDING_PAYMENT:'待付款',PENDING_ARRANGEMENT:'待发货',CANCELLED:'已取消'}
const list=computed(()=>rows.value.filter(o=>states[o.status]===tab.value))
const keys:Record<string,string>={}
async function refresh(){loading.value=true;error.value='';try{await validateSession();if(demo.loggedIn)rows.value=await listOrders();else rows.value=[]}catch(e){error.value=(e as Error).message;rows.value=[]}finally{loading.value=false}}
async function act(order:ApiOrder,kind:'pay'|'cancel'){if(busy.value||!await confirmDemo(kind==='pay'?'模拟付款':'取消订单','将更新服务端订单，不涉及真实扣款。'))return;busy.value=true;const identity=kind+'-'+order.id;const key=keys[identity] ||= identity+'-'+Date.now();try{const updated=kind==='pay'?await mockPay(order.id,key):await cancelOrder(order.id,key);rows.value=rows.value.map(o=>o.id===updated.id?updated:o);delete keys[identity];tab.value=states[updated.status]}catch(e){notify((e as Error).message)}finally{busy.value=false}}
onLoad(options=>{tab.value=options?.tab||'待付款'});onShow(()=>{void refresh()})
</script>
<template><PageShell title="我的订单" backable><view class="body"><scroll-view scroll-x><view class="pills"><button v-for="t in ['待付款','待发货','已取消','待收货','评价','退款/售后']" :key="t" class="ui-btn pill" :class="{active:tab===t}" @click="tab=t">{{t}}</button></view></scroll-view><view class="demo-note">模拟订单；“待发货”指待安排服务，不是物流发货。收货、评价、退款暂未开放。</view><button v-if="!demo.loggedIn" class="primary" @click="requireLogin('orders')">请先登录</button><view v-else-if="loading" class="empty">加载中…</view><view v-else-if="error" class="empty">{{error}}<button @click="refresh">重试</button></view><view v-else><view v-for="o in list" :key="o.id" class="card order"><text class="small">{{o.order_no}}</text><view class="row gap"><image :src="mediaUrl(o.cover_url_snapshot)" class="cover"/><view><view>{{o.product_title_snapshot}}</view><text class="muted">{{o.game_name_snapshot}} × {{o.quantity}}</text></view></view><view>订单金额 ¥{{money(o.total_amount_cents)}}</view><view class="tiny muted">{{o.created_at}} · {{states[o.status]}}</view><view v-if="o.status==='PENDING_PAYMENT'" class="row gap"><button class="secondary" :disabled="busy" @click="act(o,'cancel')">取消订单</button><button class="primary" :disabled="busy" @click="act(o,'pay')">模拟付款</button></view></view><view v-if="!list.length" class="empty">暂无订单或该功能未开放</view></view></view></PageShell></template>
<style scoped>.pills{padding:20rpx 0}.order{margin:24rpx 0;overflow-wrap:anywhere}.order .row{margin:20rpx 0}.cover{width:130rpx;height:130rpx;border-radius:20rpx}</style>
