<script setup lang="ts">
import { ref, computed } from 'vue'
import { onLoad,onShow,onHide,onUnload,onBackPress } from '@dcloudio/uni-app'
import PageShell from '../../components/PageShell.vue'
import CommunityAvatar from '../../components/CommunityAvatar.vue'
import { money } from '../../domain'
import { listOrders,mockPay,cancelOrder,confirmOrder,submitReview,applyAftersale } from '../../services/orders'
import type { ApiOrder } from '../../api/types'
import { mediaUrl } from '../../api/client'
import { notify,requireLogin,confirmDemo,detail,go } from '../../navigation'
import { demo,validateSession } from '../../store'
const rows=ref<ApiOrder[]>([]),tab=ref('待付款'),error=ref(''),busy=ref(false),loading=ref(false)
const states:Record<string,string>={PENDING_PAYMENT:'待付款',PENDING_ARRANGEMENT:'待派单',PENDING_ACCEPTANCE:'待派单',ACCEPTED:'已接单',IN_SERVICE:'服务中',PENDING_CONFIRMATION:'待验收',COMPLETED:'已完成',CANCELLED:'已取消'}
const slotLabel:Record<string,string>={morning:'上午',afternoon:'下午',evening:'晚上'}
const list=computed(()=>rows.value.filter(o=>states[o.status]===tab.value))
const keys:Record<string,string>={}
const reviewDialog=ref(false),reviewOrder=ref<ApiOrder|null>(null),reviewRating=ref(5),reviewContent=ref('')
const aftersaleDialog=ref(false),aftersaleOrder=ref<ApiOrder|null>(null),aftersaleAmount=ref<number>(0),aftersaleReason=ref('')
function canAftersale(o:ApiOrder):boolean{
  if(o.payment_status!=='PAID'||o.aftersale?.reapplication_blocked||o.total_amount_cents-(o.refunded_amount_cents||0)-(o.reserved_refund_cents||0)<=0)return false
  if(o.status==='IN_SERVICE'||o.status==='PENDING_CONFIRMATION')return true
  if(o.status==='COMPLETED'&&o.aftersale_deadline){return new Date(o.aftersale_deadline).getTime()>=Date.now()}
  return false
}
async function refresh(silent=false){if(reading)return;reading=true;const version=generation;if(!silent)loading.value=true;error.value='';try{await validateSession();if(demo.loggedIn){const data=await listOrders();if(active&&version===generation)rows.value=data}else rows.value=[]}catch(e){error.value=(e as Error).message;}finally{reading=false;loading.value=false}}
async function act(order:ApiOrder,kind:'pay'|'cancel'|'confirm'){if(busy.value||!await confirmDemo(kind==='pay'?'模拟付款':kind==='confirm'?'确认验收':'取消订单','将更新服务端订单，不涉及真实扣款。'))return;busy.value=true;const identity=kind+'-'+order.id;const key=keys[identity] ||= identity+'-'+Date.now();try{const updated=kind==='pay'?await mockPay(order.id,key):kind==='confirm'?await confirmOrder(order.id,key):await cancelOrder(order.id,key);generation++;rows.value=rows.value.map(o=>o.id===updated.id?updated:o);delete keys[identity];tab.value=states[updated.status];if(kind==='pay')paidReturn.value=true}catch(e){notify((e as Error).message)}finally{busy.value=false}}
function openReview(o:ApiOrder){reviewOrder.value=o;reviewRating.value=5;reviewContent.value='';reviewDialog.value=true}
async function saveReview(){const o=reviewOrder.value;if(!o)return;if(busy.value)return;busy.value=true;const identity='review-'+o.id;const key=keys[identity] ||= identity+'-'+Date.now();try{const r=await submitReview(o.id,key,reviewRating.value,reviewContent.value.trim());generation++;rows.value=rows.value.map(x=>x.id===o.id?{...x,review:r}:x);delete keys[identity];reviewDialog.value=false;notify('评价成功')}catch(e){notify((e as Error).message)}finally{busy.value=false}}
function openAftersale(o:ApiOrder){aftersaleOrder.value=o;aftersaleAmount.value=o.total_amount_cents-(o.refunded_amount_cents||0)-(o.reserved_refund_cents||0);aftersaleReason.value='';aftersaleDialog.value=true}
async function saveAftersale(){const o=aftersaleOrder.value;if(!o)return;if(busy.value)return;const amt=Math.floor(Number(aftersaleAmount.value)||0);if(amt<=0){notify('退款金额须大于0');return}busy.value=true;const identity='aftersale-'+o.id;const key=keys[identity] ||= identity+'-'+Date.now();try{await applyAftersale(o.id,key,amt,aftersaleReason.value.trim());delete keys[identity];aftersaleDialog.value=false;notify('售后申请已提交，等待审核');await refresh(true)}catch(e){notify((e as Error).message)}finally{busy.value=false}}
const paidReturn=ref(false)
let timer:ReturnType<typeof setInterval>|undefined,active=false,reading=false,generation=0
function stop(){active=false;generation++;if(timer)clearInterval(timer);timer=undefined}
function aftersaleLabel(o:ApiOrder){const a=o.aftersale;if(!a)return '';if(a.refund_status==='SUCCEEDED')return '售后已通过 · 退款已完成';if(a.refund_status==='FAILED')return '售后已通过 · 退款失败，请联系客服';if(a.refund_status==='UNKNOWN')return '售后已通过 · 退款结果待客服核实';return ({OPEN:'售后审核中',APPROVED:'售后已通过 · 等待退款',REJECTED:'售后已驳回，可在期限内重新申请',CLOSED:'售后已处理'} as Record<string,string>)[a.status]||''}
onLoad(options=>{tab.value=options?.tab==='待陪玩确认'?'待派单':options?.tab||'待付款'})
onShow(()=>{active=true;void refresh();timer=setInterval(()=>{if(!busy.value&&!reviewDialog.value&&!aftersaleDialog.value)void refresh(true)},5000)})
onHide(stop);onUnload(stop)
onBackPress(()=>{if(paidReturn.value){go('home');return true}return false})
</script>
<template>
  <PageShell title="我的订单" backable :back-home="paidReturn">
    <view class="body">
      <scroll-view scroll-x><view class="pills"><button v-for="t in ['待付款','待派单','已接单','服务中','待验收','已完成','已取消']" :key="t" class="ui-btn pill" :class="{active:tab===t}" @click="tab=t">{{t}}</button></view></scroll-view>
      <button v-if="demo.loggedIn" class="ui-btn refresh-orders" :disabled="loading||busy" @click="refresh()">刷新订单状态</button>
      <view class="demo-note">付款后客服确认接单人，陪玩在对话中开始服务、申请完成，由您确认验收。当前付款为模拟。</view>
      <button v-if="!demo.loggedIn" class="primary" @click="requireLogin('orders')">请先登录</button>
      <view v-else-if="loading" class="empty">加载中…</view>
      <view v-else-if="error" class="empty">{{error}}<button @click="refresh()">重试</button></view>
      <view v-else>
        <view v-for="o in list" :key="o.id" class="card order">
          <view class="order-heading"><text class="order-number">{{o.order_no}}</text><text class="order-status">{{states[o.status]}}</text></view>
          <view class="order-product"><image :src="mediaUrl(o.cover_url_snapshot)" class="cover" mode="aspectFill"/><view class="grow"><view class="product-title">{{o.product_title_snapshot}}</view><text class="small muted">{{o.game_name_snapshot}} · 数量 {{o.quantity}}</text></view></view>
          <view v-if="o.appointment_date" class="order-meta">预约：{{o.appointment_date}} {{slotLabel[o.appointment_slot||'']||o.appointment_slot}}</view>
          <view v-if="o.partner_info && !['PENDING_ARRANGEMENT','PENDING_ACCEPTANCE'].includes(o.status)" class="assigned-partner"><CommunityAvatar :url="o.partner_info.avatar_url" :name="o.partner_info.nickname"/><text class="small muted">接单陪玩</text><text class="partner-name">{{o.partner_info.nickname}}</text></view>
          <view v-else-if="o.preferred_partner_info" class="order-meta">意向陪玩：{{o.preferred_partner_info.nickname}} · 等待客服确认</view>
          <view class="order-total"><text class="small muted">订单金额</text><text class="amount">¥{{money(o.total_amount_cents)}}</text></view>
          <view v-if="['PENDING_ARRANGEMENT','PENDING_ACCEPTANCE'].includes(o.status)" class="processing">{{o.preferred_partner?'订单正在处理中，客服正在确认指定陪玩是否可以接单。':'订单正在处理中，客服正在为您安排陪玩。'}}</view>
          <view v-if="o.aftersale" class="processing"><view>{{aftersaleLabel(o)}}</view><view v-if="o.aftersale.resolution" class="resolution">处理说明：{{o.aftersale.resolution}}</view></view>
          <view v-if="(o.refunded_amount_cents||0)>0" class="refund-result">已退款 ¥{{money(o.refunded_amount_cents||0)}}</view>
          <view v-if="o.review" class="order-meta">已评价：{{o.review.rating}} 星</view>
          <view class="order-meta order-time">{{o.created_at.replace('T',' ').slice(0,19)}}</view>
          <view v-if="o.status==='PENDING_PAYMENT'||o.payment_status==='PAID'" class="order-actions">
            <button v-if="o.status==='PENDING_PAYMENT'" class="ui-btn order-action" :disabled="busy" @click="act(o,'cancel')">取消订单</button>
            <button v-if="o.payment_status==='PAID'" class="ui-btn order-action" @click="detail('support',o.order_no)">联系客服</button>
            <button v-if="canAftersale(o)" class="ui-btn order-action" :disabled="busy" @click="openAftersale(o)">申请售后</button>
            <button v-if="o.status==='PENDING_PAYMENT'" class="ui-btn order-action action-primary" :disabled="busy" @click="act(o,'pay')">模拟付款</button>
            <button v-else-if="o.status==='PENDING_CONFIRMATION'" class="ui-btn order-action action-primary" :disabled="busy" @click="act(o,'confirm')">确认验收</button>
            <button v-else-if="o.status==='COMPLETED'&&!o.review" class="ui-btn order-action action-primary" :disabled="busy" @click="openReview(o)">评价</button>
          </view>
        </view>
        <view v-if="!list.length" class="empty">暂无订单</view>
      </view>
    </view>
  </PageShell>
<view v-if="reviewDialog" class="mask"><view class="sheet"><view class="sheet-title">评价订单</view><view class="stars"><button v-for="s in 5" :key="s" class="ui-btn star" :class="{on:s<=reviewRating}" @click="reviewRating=s">★</button></view><textarea v-model="reviewContent" class="input" placeholder="说说这次服务体验（可选）" maxlength="2000"/><view class="row gap"><button class="secondary" @click="reviewDialog=false">取消</button><button class="primary" :disabled="busy" @click="saveReview">提交评价</button></view></view></view>
<view v-if="aftersaleDialog" class="mask"><view class="sheet"><view class="sheet-title">申请售后</view><view class="tiny muted" style="margin-bottom:16rpx">可退金额上限 ¥{{money((aftersaleOrder?.total_amount_cents||0)-(aftersaleOrder?.refunded_amount_cents||0)-(aftersaleOrder?.reserved_refund_cents||0))}}</view><view class="field-label">退款金额（分）</view><input v-model.number="aftersaleAmount" type="number" class="input short" placeholder="输入退款金额（分）"/><view class="field-label">申请说明</view><textarea v-model="aftersaleReason" class="input" placeholder="说明售后原因（可选）" maxlength="2000"/><view class="row gap"><button class="secondary" @click="aftersaleDialog=false">取消</button><button class="primary" :disabled="busy" @click="saveAftersale">提交申请</button></view></view></view></template>
<style scoped>.assigned-partner{display:flex;gap:14rpx;align-items:center;padding:20rpx 0}.partner-name{font-size:26rpx;flex:1;min-width:0}.order-heading{display:flex;align-items:center;gap:20rpx;padding-bottom:22rpx;border-bottom:1rpx solid #efedf2}.order-number{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:21rpx;color:#92909c}.order-status{flex-shrink:0;font-size:24rpx;font-weight:600;color:#80699e}.order-product{display:flex;align-items:center;gap:22rpx;margin:24rpx 0}.product-title{font-size:29rpx;font-weight:600;line-height:1.5;margin-bottom:8rpx}.order-total{display:flex;align-items:baseline;justify-content:space-between;margin-top:16rpx}.amount{font-size:34rpx;font-weight:700;color:#303345}.order-meta{font-size:23rpx;line-height:1.6;color:#88828f}.order-time{font-size:21rpx;margin-top:14rpx}.resolution{margin-top:8rpx;font-size:23rpx;white-space:pre-wrap}.refund-result{font-size:26rpx;color:#537866;margin-top:16rpx}.order-actions{display:flex;justify-content:flex-end;align-items:center;flex-wrap:wrap;gap:12rpx;margin-top:24rpx;padding-top:24rpx;border-top:1rpx solid #efedf2}.order-action{display:flex;align-items:center;justify-content:center;box-sizing:border-box;min-width:148rpx;min-height:72rpx;margin:0;padding:14rpx 22rpx;border:1rpx solid #e4dfea;border-radius:40rpx;background:#fff;color:#756784;font-size:25rpx;line-height:1.4;white-space:nowrap}.order-action.action-primary{background:#80699e;border-color:#80699e;color:#fff;font-weight:600}.refresh-orders{color:#80699e;font-size:26rpx;margin:16rpx 0}.pills{padding:20rpx 0}.order{margin:24rpx 0;overflow-wrap:anywhere}.processing{margin:16rpx 0;padding:20rpx;background:#f7f4fb;border:1rpx solid #e6e0f0;border-radius:16rpx;color:#6b5a8a;font-size:26rpx}.cover{width:130rpx;height:130rpx;border-radius:20rpx}.mask{position:fixed;inset:0;background:rgba(0,0,0,.4);display:flex;align-items:flex-end;z-index:999}.sheet{background:#fff;width:100%;border-radius:24rpx 24rpx 0 0;padding:32rpx;box-sizing:border-box}.sheet-title{font-size:32rpx;font-weight:600;text-align:center;margin-bottom:24rpx}.stars{display:flex;justify-content:center;gap:12rpx;margin-bottom:24rpx}.star{font-size:48rpx;color:#ddd}.star.on{color:#f5a623}.input{width:100%;min-height:160rpx;border:1rpx solid #e6e0f0;border-radius:16rpx;padding:20rpx;margin-bottom:24rpx;box-sizing:border-box}.input.short{min-height:auto;height:80rpx}.field-label{font-size:26rpx;color:#747486;margin-bottom:8rpx}</style>
