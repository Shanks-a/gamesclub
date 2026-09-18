<script setup lang="ts">
import { ref,computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import PageShell from '../../components/PageShell.vue'
import EmptyState from '../../components/EmptyState.vue'
import { orderTabs, products, money, type OrderTab } from '../../domain'
import { demo,actOrder } from '../../store'
import { requireLogin,detail,confirmDemo,notify } from '../../navigation'
const tab=ref<OrderTab>('待付款')
onLoad(q=>{if(orderTabs.includes(q?.tab as OrderTab))tab.value=q!.tab as OrderTab})
const list=computed(()=>demo.orders.filter(o=>!o.cancelled&&o.tab===tab.value).map(o=>({...o,product:products.find(p=>p.id===o.productId)!})))
async function action(id:string,kind:'cancel'|'pay'|'receive'|'review') {
 const copy={cancel:['取消演示订单','仅取消本地示例订单，不影响任何真实订单。'],pay:['模拟付款','不会扣款；仅演示付款后的订单页面。该分类不代表正式后端状态映射。'],receive:['模拟确认完成','仅更新演示订单，不代表真实服务交付或验收。'],review:['提交演示评价','将此示例标记为已评价，不会发布到任何平台。']}
 if(!await confirmDemo(copy[kind][0],copy[kind][1]))return
 try{actOrder(id,kind);if(kind==='pay')tab.value='待发货';if(kind==='receive')tab.value='评价';notify('演示状态已更新')}catch(e){notify((e as Error).message)}
}
</script>
<template><PageShell title="我的订单" backable><view class="body">
 <view class="order-tabs"><button class="ui-btn" v-for="item in orderTabs" :key="item" :class="{active:tab===item}" @click="tab=item">{{item}}</button></view>
 <view v-if="!demo.loggedIn" class="blank-page"><text class="muted">登录演示后查看示例订单</text><button class="ui-btn primary" @click="requireLogin('orders',{tab})">进入演示登录</button></view>
 <template v-else><view class="muted small count">{{tab}}订单 · {{list.length}}</view><view v-if="tab==='待发货'||tab==='待收货'" class="demo-note">此分类仅演示界面，不涉及实物物流；正式服务状态映射待确认。</view>
 <view class="stack"><view v-for="order in list" :key="order.id" class="card order"><view class="between"><text class="small">游伴自营 · 演示</text><text class="small accent">{{order.reviewed?'已评价':order.tab}}</text></view><view class="divider"/>
  <view class="row gap" @click="detail('product',order.productId)"><image :src="`/static/art/product-${order.product.art}.png`" class="order-cover"/><view><view class="order-name">{{order.product.title}}</view><view class="muted small">{{order.product.game}} · 1小时</view><view class="muted small">数量 ×{{order.quantity}}</view></view></view>
  <view class="total">{{tab==='待付款'?'应付款':'演示金额'}} <text>¥ {{money(order.product.price*order.quantity)}}</text></view>
  <view class="order-actions"><template v-if="tab==='待付款'"><button class="ui-btn secondary button-small" @click="action(order.id,'cancel')">取消订单</button><button class="ui-btn primary button-small" @click="action(order.id,'pay')">模拟付款</button></template><button v-else-if="tab==='待发货'" class="ui-btn secondary button-small" @click="detail('process')">查看服务流程</button><button v-else-if="tab==='待收货'" class="ui-btn primary button-small" @click="action(order.id,'receive')">模拟确认完成</button><button v-else-if="tab==='评价'" class="ui-btn secondary button-small" :disabled="order.reviewed" @click="action(order.id,'review')">{{order.reviewed?'已评价':'模拟评价'}}</button><button v-else class="ui-btn secondary button-small" @click="detail('aftersale')">查看售后说明</button></view>
 </view></view><EmptyState v-if="!list.length" :title="`暂无${tab}订单`" description="浏览精选服务，找到适合自己的游戏搭子。"/><view class="footnote">示例订单仅在本次会话内更新</view></template>
</view></PageShell></template>
<style scoped>.order-tabs{display:flex;justify-content:space-between;margin:22rpx -6rpx 0}.order-tabs button{font-size:23rpx;padding:16rpx 0 22rpx;color:#747486;border-bottom:5rpx solid transparent;white-space:nowrap}.order-tabs .active{color:#8875aa;border-bottom-color:#8875aa}.count{margin:26rpx 0}.order-cover{width:145rpx;height:145rpx;border-radius:22rpx;flex-shrink:0}.order-name{font-weight:600;font-size:29rpx;margin-bottom:12rpx}.order .small+.small{margin-top:9rpx}.total{text-align:right;font-size:25rpx;margin:26rpx 0}.total text{font-weight:600;font-size:30rpx}.order-actions{display:flex;justify-content:flex-end;gap:16rpx}</style>
