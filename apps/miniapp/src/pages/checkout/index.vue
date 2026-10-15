<script setup lang="ts">
import { ref, computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import PageShell from '../../components/PageShell.vue'
import { money } from '../../domain'
import { getProduct, getGamePartners } from '../../services/catalog'
import { createOrder } from '../../services/orders'
import type { Product } from '../../domain'
import type { ApiGamePartner } from '../../api/types'
import { mediaUrl } from '../../api/client'
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
const pickerOpen=ref(false), partners=ref<ApiGamePartner[]>([]), partnersLoading=ref(false), keyword=ref('')
const filtered=computed(()=>{
  const k=keyword.value.trim().toLowerCase()
  if(!k)return partners.value
  return partners.value.filter(p=>p.nickname.toLowerCase().includes(k)||String(p.id).includes(k))
})
onLoad(async q=>{
  productId.value=q?.productId||''
  platform.value=(q?.platform as 'mobile'|'pc')||'mobile'
  quantity.value=Math.max(1,Number(q?.quantity||1))
  try{product.value=await getProduct(productId.value)}catch(e){loadError.value=(e as Error).message;return}
})
async function openPicker(){
  if(!product.value?.gameId)return
  pickerOpen.value=true
  keyword.value=''
  if(!partners.value.length){
    partnersLoading.value=true
    try{partners.value=await getGamePartners(product.value.gameId)}catch(e){notify((e as Error).message)}
    finally{partnersLoading.value=false}
  }
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
<template><PageShell title="提交订单" backable><view class="body ck">
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
    <view class="card between ck-partner-row">
      <text class="ck-label">接单陪陪</text>
      <view class="row gap">
        <button class="ui-btn ck-chip" :class="{active:partnerMode==='auto'}" @click="partnerMode='auto'">自动安排</button>
        <button class="ui-btn ck-chip" :class="{active:partnerMode==='specified'}" @click="openPicker">指定陪陪</button>
      </view>
    </view>
    <view v-if="partnerMode==='specified'" class="card between ck-picked">
      <text class="small">{{pickedPartner?('已选：'+pickedPartner.name):'未选择陪陪'}}</text>
      <button class="ui-btn small accent" @click="openPicker">{{pickedPartner?'重新选择':'去选择'}}</button>
    </view>
    <view class="card between"><text class="ck-label">商品总价</text><text class="ck-total">¥{{money(total)}}</text></view>
    <view class="ck-footer safe-bottom between">
      <text>合计 <text class="ck-total">¥{{money(total)}}</text></text>
      <button class="ui-btn ck-submit" :loading="busy" @click="submit">提交订单</button>
    </view>

    <!-- 选择陪陪底部弹窗 -->
    <view v-if="pickerOpen" class="pk-mask" @click="pickerOpen=false"/>
    <view v-if="pickerOpen" class="pk-sheet">
      <view class="pk-head between">
        <text class="pk-title">选择陪陪</text>
        <text class="pk-fold" @click="pickerOpen=false">︾</text>
      </view>
      <view class="pk-search row">
        <view class="pk-search-box row grow">
          <text class="pk-mag">🔍</text>
          <input v-model="keyword" class="grow" placeholder="请输入用户名称/ID" confirm-type="search"/>
        </view>
        <button class="ui-btn pk-search-btn">搜索</button>
      </view>
      <scroll-view scroll-y class="pk-list">
        <view v-if="partnersLoading" class="pk-empty muted">加载中…</view>
        <view v-else-if="!filtered.length" class="pk-empty muted">没有找到匹配的陪陪</view>
        <view v-for="p in filtered" :key="p.id" class="pk-row" :class="{active:p.id===pickedPartner?.id}" @click="pick(p)">
          <image v-if="p.avatar_url" :src="mediaUrl(p.avatar_url)" class="pk-avatar" mode="aspectFill"/>
          <view v-else class="pk-avatar pk-avatar-ph">{{p.nickname.slice(0,1)}}</view>
          <view class="grow">
            <view class="pk-name">{{p.nickname}}</view>
            <view class="tiny muted">ID: {{p.id}}</view>
          </view>
          <text class="tiny muted">总接单：{{p.completed_orders}}</text>
        </view>
        <view class="pk-bottom-space"/>
      </scroll-view>
    </view>
  </template>
</view></PageShell></template>
<style scoped>
.ck{padding-bottom:160rpx}.ck .card{margin-bottom:24rpx}.ck-goods{display:flex;gap:22rpx;padding:26rpx}.ck-cover{width:150rpx;height:150rpx;border-radius:20rpx;background:#eee;flex-shrink:0}.ck-title{font-size:28rpx;font-weight:600;line-height:1.5}.ck-price-row{margin-top:16rpx}.ck-price{font-size:34rpx;font-weight:700;color:#e8932c}.ck-step{width:56rpx;height:56rpx;border-radius:16rpx;background:#f2f0f4;font-size:30rpx;line-height:56rpx}.ck-num{min-width:70rpx;text-align:center;font-size:28rpx}.ck-form{padding:10rpx 26rpx}.ck-field{display:flex;align-items:center;gap:20rpx;padding:22rpx 0;border-bottom:1rpx solid #f2f0f4}.ck-field:last-child{border-bottom:none}.ck-label{flex-shrink:0;width:190rpx;font-size:26rpx;color:#5a5560}.ck-req::before{content:'*';color:#e05a5a;margin-right:6rpx}.ck-input{flex:1;font-size:26rpx;text-align:right}.ck-chip{font-size:24rpx;padding:10rpx 28rpx;border-radius:30rpx;background:#f2f0f4;color:#5a5560}.ck-chip.active{background:#fdf3e3;color:#e8932c;border:1rpx solid #e8a23c}.ck-note{padding:16rpx 0}.ck-partner-row{padding:26rpx}.ck-picked{padding:20rpx 26rpx}.ck-total{font-size:34rpx;font-weight:700;color:#e8932c}.ck-footer{position:fixed;left:0;right:0;bottom:0;background:#fff;padding:20rpx 30rpx;padding-bottom:calc(20rpx + env(safe-area-inset-bottom));box-shadow:0 -4rpx 20rpx rgba(0,0,0,.06);z-index:20}.ck-submit{background:#e8a23c;color:#fff;height:84rpx;padding:0 56rpx;border-radius:42rpx;font-size:29rpx}
.pk-mask{position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:30}
.pk-sheet{position:fixed;left:0;right:0;bottom:0;z-index:31;background:#fff;border-radius:36rpx 36rpx 0 0;display:flex;flex-direction:column;max-height:75vh;padding-bottom:env(safe-area-inset-bottom)}
.pk-head{padding:28rpx 34rpx 10rpx;justify-content:center;position:relative}
.pk-title{font-size:32rpx;font-weight:700}
.pk-fold{position:absolute;right:34rpx;font-size:34rpx;color:#9a93a2;padding:0 10rpx}
.pk-search{padding:20rpx 30rpx;gap:16rpx}
.pk-search-box{background:#f5f3f7;border-radius:40rpx;padding:14rpx 26rpx;gap:12rpx;font-size:26rpx}
.pk-mag{font-size:26rpx;opacity:.6}
.pk-search-btn{background:#e8a23c;color:#fff;font-size:26rpx;padding:12rpx 36rpx;border-radius:40rpx;flex-shrink:0}
.pk-list{flex:1;min-height:0;padding:0 24rpx}
.pk-row{display:flex;align-items:center;gap:20rpx;padding:18rpx 16rpx;border-radius:20rpx}
.pk-row.active{background:#fdf3e3}
.pk-avatar{width:88rpx;height:88rpx;border-radius:50%;background:#efeaf4;flex-shrink:0}
.pk-avatar-ph{display:flex;align-items:center;justify-content:center;font-size:34rpx;color:#80699e}
.pk-name{font-size:29rpx;font-weight:600;margin-bottom:4rpx}
.pk-empty{text-align:center;padding:80rpx 0;font-size:26rpx}
.pk-bottom-space{height:40rpx}
</style>
