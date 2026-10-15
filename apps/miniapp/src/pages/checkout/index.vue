<script setup lang="ts">
import { ref, computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import PageShell from '../../components/PageShell.vue'
import PartnerPicker from '../../components/PartnerPicker.vue'
import { money } from '../../domain'
import { getProduct } from '../../services/catalog'
import { createOrder } from '../../services/orders'
import type { Product } from '../../domain'
import type { ApiGamePartner } from '../../api/types'
import { demo } from '../../store'
import { go, notify } from '../../navigation'
const productId=ref(''), platform=ref<'mobile'|'pc'>('mobile'), quantity=ref(1)
const product=ref<Product>(), loadError=ref('')
const role=ref(''), roleId=ref(''), message=ref(''), remark=ref('')
const partnerMode=ref<'auto'|'specified'>('auto')
const pickedPartner=ref<{id:number;name:string}|null>(null)
const busy=ref(false)
const total=computed(()=>(product.value?.price||0)*quantity.value)
const platformLabel=computed(()=>platform.value==='pc'?'电脑端':'手机端')
// 选择陪陪弹窗
const pickerOpen=ref(false)
onLoad(async q=>{
  productId.value=q?.productId||''
  platform.value=(q?.platform as 'mobile'|'pc')||'mobile'
  quantity.value=Math.max(1,Number(q?.quantity||1))
  try{product.value=await getProduct(productId.value)}catch(e){loadError.value=(e as Error).message;return}
})
function openPicker(){
  if(!product.value?.gameId)return
  pickerOpen.value=true
}
function pick(p:ApiGamePartner){
  pickedPartner.value={id:p.id,name:p.nickname}
  partnerMode.value='specified'
  pickerOpen.value=false
}
async function submit(){
  if(!demo.loggedIn){go('login');return}
  if(!product.value)return
  if(!role.value.trim()){notify('请填写游戏角色名称');return}
  if(!roleId.value.trim()){notify('请填写游戏角色ID');return}
  if(partnerMode.value==='specified'&&!pickedPartner.value){notify('请选择指定陪陪');return}
  if(busy.value)return
  busy.value=true
  const key='checkout-'+Date.now()
  try{
    await createOrder(product.value.id,quantity.value,product.value.version||1,key,undefined,{
      platform:platform.value,
      role_name:role.value.trim(),
      role_id:roleId.value.trim(),
      message:message.value.trim(),
      remark:remark.value.trim(),
      ...(partnerMode.value==='specified'&&pickedPartner.value?{preferred_partner_id:pickedPartner.value.id}:{})
    })
    notify('订单已提交')
    go('orders',{tab:'待付款'})
  }catch(e){notify((e as Error).message)}
  finally{busy.value=false}
}
</script>
<template>
<page-meta :page-style="pickerOpen ? 'overflow: hidden;' : ''" />
<PageShell title="提交订单" backable><view class="body ck">
  <view v-if="loadError" class="empty muted">{{loadError}}</view>
  <template v-else-if="product">
    <view class="card ck-goods">
      <image :src="product.cover" class="ck-cover" mode="aspectFill"/>
      <view class="grow">
        <view class="ck-title">{{product.title}}</view>
        <text class="tiny muted">{{platformLabel}}</text>
        <view class="between ck-price-row"><text class="ck-price">¥{{money(product.price)}}</text>
          <view class="row gap"><button class="ui-btn ck-step" :disabled="quantity<=(product.minQuantity||1)" @click="quantity--">−</button><text class="ck-num">{{quantity}}</text><button class="ui-btn ck-step" :disabled="quantity>=(product.maxQuantity||1)" @click="quantity++">＋</button></view>
        </view>
      </view>
    </view>
    <view class="card ck-partner-row">
      <view class="between ck-partner-heading">
        <text class="ck-partner-label">接单陪陪</text>
        <view class="row ck-partner-options">
          <button class="ui-btn ck-chip" :class="{active:partnerMode==='auto'}" @click="partnerMode='auto'">自动安排</button>
          <button class="ui-btn ck-chip" :class="{active:partnerMode==='specified'}" @click="openPicker">指定陪陪</button>
        </view>
      </view>
      <button class="ui-btn ck-picker-entry" @click="openPicker">
        <view class="grow"><view class="ck-picker-title">{{partnerMode==='specified'&&pickedPartner?pickedPartner.name:'选择陪陪'}}</view><view class="ck-picker-hint">{{partnerMode==='specified'?'点击可重新选择':'可按名称或 ID 指定，未选择则自动安排'}}</view></view>
        <text class="ck-picker-arrow">›</text>
      </button>
    </view>
    <view class="card ck-form">
      <view class="ck-field"><text class="ck-label">留言</text><input v-model="message" class="ck-input" placeholder="请先与商家沟通一致再留言哦～" maxlength="255"/></view>
    </view>
    <view class="card ck-form">
      <view class="ck-field"><text class="ck-label ck-req">游戏平台</text>
        <view class="row gap"><button class="ui-btn ck-chip" :class="{active:platform==='mobile'}" @click="platform='mobile'">手游</button><button class="ui-btn ck-chip" :class="{active:platform==='pc'}" @click="platform='pc'">端游</button></view>
      </view>
      <view class="ck-field"><text class="ck-label ck-req">游戏角色名称</text><input v-model="role" class="ck-input" placeholder="输入你的游戏角色名字" maxlength="80"/></view>
      <view class="ck-field"><text class="ck-label ck-req">游戏角色ID</text><input v-model="roleId" class="ck-input" placeholder="输入你的游戏角色ID" maxlength="80"/></view>
      <view class="ck-field"><text class="ck-label">发单备注</text><input v-model="remark" class="ck-input" placeholder="仅限接单陪陪看得到（选填）" maxlength="255"/></view>
      <view class="tiny muted ck-note">注意事项：指定陪陪5分钟没接自动安排</view>
    </view>
    <view class="card between"><text class="ck-label">商品总价</text><text class="ck-total">¥{{money(total)}}</text></view>
    <view class="ck-footer safe-bottom between">
      <text>合计 <text class="ck-total">¥{{money(total)}}</text></text>
      <button class="ui-btn ck-submit" :loading="busy" @click="submit">提交订单</button>
    </view>

    <PartnerPicker v-if="pickerOpen && product.gameId" :game-id="product.gameId" :selected-id="partnerMode==='specified' ? pickedPartner?.id : undefined" @close="pickerOpen=false" @select="pick" />
  </template>
</view></PageShell></template>
<style scoped>
.ck{padding-bottom:160rpx}.ck .card{margin-bottom:24rpx}.ck-goods{display:flex;gap:22rpx;padding:26rpx}.ck-cover{width:150rpx;height:150rpx;border-radius:20rpx;background:#eee;flex-shrink:0}.ck-title{font-size:28rpx;font-weight:600;line-height:1.5}.ck-price-row{margin-top:16rpx}.ck-price{font-size:34rpx;font-weight:700;color:#e8932c}.ck-step{width:56rpx;height:56rpx;border-radius:16rpx;background:#f2f0f4;font-size:30rpx;line-height:56rpx}.ck-num{min-width:70rpx;text-align:center;font-size:28rpx}.ck-form{padding:10rpx 26rpx}.ck-field{display:flex;align-items:center;gap:20rpx;padding:22rpx 0;border-bottom:1rpx solid #f2f0f4}.ck-field:last-child{border-bottom:none}.ck-label{flex-shrink:0;width:190rpx;font-size:26rpx;color:#5a5560}.ck-req::before{content:'*';color:#e05a5a;margin-right:6rpx}.ck-input{flex:1;font-size:26rpx;text-align:right}.ck-chip{font-size:24rpx;padding:10rpx 28rpx;border-radius:30rpx;background:#f2f0f4;color:#5a5560}.ck-chip.active{background:#fdf3e3;color:#e8932c;border:1rpx solid #e8a23c}.ck-note{padding:16rpx 0}.ck-partner-row{padding:26rpx}.ck-total{font-size:34rpx;font-weight:700;color:#e8932c}.ck-footer{position:fixed;left:0;right:0;bottom:0;background:#fff;padding:20rpx 30rpx;padding-bottom:calc(20rpx + env(safe-area-inset-bottom));box-shadow:0 -4rpx 20rpx rgba(0,0,0,.06);z-index:20}.ck-submit{background:#e8a23c;color:#fff;height:84rpx;padding:0 56rpx;border-radius:42rpx;font-size:29rpx}
.ck-price-row{flex-wrap:wrap;gap:12rpx}.ck-price-row .row{gap:12rpx}.ck-chip{white-space:nowrap;flex-shrink:0}
.ck-partner-heading{gap:16rpx;flex-wrap:wrap}.ck-partner-label{font-size:28rpx;font-weight:600}.ck-partner-options{gap:12rpx}
.ck-picker-entry{width:100%;display:flex;align-items:center;gap:16rpx;text-align:left;margin-top:22rpx;padding-top:22rpx;border-top:1rpx solid #eee}
.ck-picker-title{font-size:28rpx;color:#9a6714;overflow-wrap:anywhere}.ck-picker-hint{font-size:22rpx;color:#747486;margin-top:6rpx;line-height:1.5}.ck-picker-arrow{font-size:38rpx;color:#9a6714}
/* #ifdef H5 */
@media(min-width:700px){
  .ck{padding:0 20px 110px}.ck .card{border-radius:20px;margin-bottom:16px}.ck-goods{padding:16px;gap:14px}
  .ck-cover{width:88px;height:88px;border-radius:12px}.ck-title{font-size:17px}.ck .tiny{font-size:12px}
  .ck-price-row{gap:8px;margin-top:10px}.ck-price{font-size:22px}.ck-step{width:32px;height:32px;line-height:32px;font-size:20px;border-radius:10px}.ck-num{min-width:28px;font-size:16px}
  .ck-form{padding:6px 16px}.ck-field{padding:16px 0;gap:12px}.ck-label{width:110px;font-size:14px}.ck-input{font-size:14px}.ck-field .gap{gap:12px}
  .ck-chip{font-size:13px;padding:6px 14px}.ck-partner-row{padding:18px}.ck-partner-label{font-size:16px}.ck-partner-options{gap:8px}
  .ck-picker-entry{margin-top:14px;padding-top:14px;gap:10px}.ck-picker-title{font-size:16px}.ck-picker-hint{font-size:12px}.ck-picker-arrow{font-size:24px}
  .ck-footer{max-width:480px;margin:auto;padding:14px 20px;padding-bottom:calc(14px + env(safe-area-inset-bottom));font-size:16px}.ck-total{font-size:22px}.ck-submit{height:48px;padding:0 30px;font-size:16px;display:flex;align-items:center;justify-content:center}
}
/* #endif */
</style>
