<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { ApiGamePartner } from '../api/types'
import { mediaUrl } from '../api/client'
import { getGamePartners } from '../services/catalog'
import AppIcon from './AppIcon.vue'

const props = defineProps<{ gameId: number; selectedId?: number }>()
const emit = defineEmits<{ close: []; select: [partner: ApiGamePartner] }>()
const partners = ref<ApiGamePartner[]>([])
const loading = ref(false)
const error = ref('')
const keyword = ref('')
const query = ref('')
const failedAvatars = ref<number[]>([])
const filtered = computed(() => partners.value.filter(partner =>
  partner.nickname.toLowerCase().includes(query.value) || String(partner.id).includes(query.value),
))

async function loadPartners() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    partners.value = await getGamePartners(props.gameId)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '加载失败，请重试'
  } finally {
    loading.value = false
  }
}

function search() {
  query.value = keyword.value.trim().toLowerCase()
  uni.hideKeyboard()
}

function clearSearch() {
  keyword.value = ''
  query.value = ''
}

onMounted(loadPartners)

// H5 scrolls the document; page-meta locks the native mini-program page.
// #ifdef H5
let previousOverflow = ''
function closeOnEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
}
onMounted(() => {
  previousOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  document.addEventListener('keydown', closeOnEscape)
})
onBeforeUnmount(() => {
  document.body.style.overflow = previousOverflow
  document.removeEventListener('keydown', closeOnEscape)
})
// #endif
</script>

<template>
  <view class="picker-mask" @click="emit('close')" @touchmove.stop.prevent />
  <view class="picker-sheet" role="dialog" aria-modal="true" aria-label="选择陪陪" @touchmove.stop>
    <view class="picker-header">
      <text class="picker-title">选择陪陪</text>
      <button class="ui-btn picker-close" aria-label="关闭选择陪陪" @click="emit('close')">
        <view class="picker-chevron" />
      </button>
    </view>
    <view class="picker-search">
      <AppIcon name="search" :size="20" />
      <input v-model="keyword" class="picker-input" placeholder="请输入用户名称/ID" aria-label="搜索陪陪名称或ID" confirm-type="search" maxlength="80" @confirm="search" />
      <button v-if="keyword || query" class="ui-btn picker-clear" aria-label="清空搜索" @click="clearSearch">×</button>
      <button class="ui-btn picker-search-button" @click="search">搜索</button>
    </view>
    <scroll-view scroll-y class="picker-list">
      <view v-if="loading" class="picker-empty">正在加载陪陪…</view>
      <view v-else-if="error" class="picker-empty">
        <view>{{ error }}</view>
        <button class="ui-btn picker-retry" @click="loadPartners">重新加载</button>
      </view>
      <view v-else-if="!partners.length" class="picker-empty">该游戏暂无可接单的陪陪，可选择自动安排</view>
      <view v-else-if="!filtered.length" class="picker-empty">
        <view>没有找到匹配的陪陪</view>
        <button class="ui-btn picker-retry" @click="clearSearch">查看全部陪陪</button>
      </view>
      <view v-else class="picker-results">
        <button v-for="partner in filtered" :key="partner.id" class="ui-btn picker-row" :class="{ selected: partner.id === selectedId }" :aria-label="`选择${partner.nickname}，ID ${partner.id}`" @click="emit('select', partner)">
          <image v-if="partner.avatar_url && !failedAvatars.includes(partner.id)" :src="mediaUrl(partner.avatar_url)" class="picker-avatar" mode="aspectFill" @error="failedAvatars.push(partner.id)" />
          <view v-else class="picker-avatar picker-placeholder">{{ partner.nickname.slice(0, 1) || '陪' }}</view>
          <view class="picker-identity">
            <view class="picker-name">{{ partner.nickname }}</view>
            <view class="picker-id">ID: {{ partner.id }}<text v-if="partner.id === selectedId" class="picker-selected"> · 已选</text></view>
          </view>
          <text class="picker-count">总接单：{{ partner.completed_orders ?? '未知' }}</text>
        </button>
      </view>
    </scroll-view>
  </view>
</template>

<style scoped>
.picker-mask{position:fixed;inset:0;z-index:30;background:rgba(0,0,0,.45)}
.picker-sheet{position:fixed;left:0;right:0;bottom:0;z-index:31;height:62vh;max-height:80vh;display:flex;flex-direction:column;background:#f8f7f4;border-radius:36rpx 36rpx 0 0;padding-bottom:env(safe-area-inset-bottom);overflow:hidden}
.picker-header{position:relative;display:flex;align-items:center;justify-content:center;flex-shrink:0;padding:28rpx 80rpx 20rpx}
.picker-title{font-size:32rpx;font-weight:600}
.picker-close{position:absolute;right:20rpx;top:12rpx;width:72rpx;height:72rpx;display:flex;align-items:center;justify-content:center}
.picker-chevron{width:20rpx;height:20rpx;border-right:3rpx solid #777;border-bottom:3rpx solid #777;transform:rotate(45deg);margin-top:-8rpx}
.picker-search{display:flex;align-items:center;gap:16rpx;flex-shrink:0;margin:0 28rpx 16rpx;padding:8rpx 10rpx 8rpx 20rpx;background:#fff;border-radius:50rpx}
.picker-input{flex:1;min-width:0;height:64rpx;font-size:27rpx}
.picker-clear{padding:8rpx;color:#747486;font-size:32rpx}
.picker-search-button{flex-shrink:0;padding:12rpx 28rpx;border-radius:40rpx;background:#ffbf4b;color:#fff;font-size:27rpx}
.picker-list{height:0;flex:1;min-height:0;overscroll-behavior:contain}
.picker-results{padding:0 24rpx 24rpx}
.picker-row{width:100%;display:flex;align-items:center;gap:16rpx;margin-bottom:10rpx;padding:14rpx 12rpx;text-align:left;border-radius:18rpx;background:#fff}
.picker-row.selected{background:#fff2d8}
.picker-avatar{flex-shrink:0;width:80rpx;height:80rpx;border-radius:12rpx;background:#ece7ef}
.picker-placeholder{display:flex;align-items:center;justify-content:center;font-size:30rpx;color:#80699e}
.picker-identity{flex:1;min-width:0}
.picker-name{font-size:28rpx;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.picker-id{margin-top:6rpx;font-size:23rpx;color:#747486}
.picker-selected{color:#9a6714}
.picker-count{flex-shrink:0;font-size:23rpx;color:#56515a;white-space:nowrap}
.picker-empty{padding:60rpx 32rpx;text-align:center;color:#747486;font-size:26rpx}
.picker-retry{margin:24rpx auto 0;color:#9a6714;padding:12rpx 24rpx}
/* #ifdef H5 */
@media(min-width:700px){
  .picker-sheet{max-width:480px;margin:auto;border-radius:24px 24px 0 0}
  .picker-header{padding:20px 50px 16px}.picker-title{font-size:20px}
  .picker-close{top:6px;right:12px;width:44px;height:44px}.picker-chevron{width:12px;height:12px;border-width:2px}
  .picker-search{margin:0 16px 12px;padding:5px 6px 5px 12px;gap:8px}.picker-input{height:36px;font-size:15px}
  .picker-search-button{padding:8px 18px;font-size:15px}.picker-clear{font-size:20px}
  .picker-results{padding:0 14px 16px}.picker-row{gap:10px;padding:10px 8px;margin-bottom:8px}
  .picker-avatar{width:48px;height:48px;border-radius:8px}.picker-placeholder{font-size:20px}
  .picker-name{font-size:16px}.picker-id,.picker-count{font-size:13px}.picker-empty{font-size:15px}
}
/* #endif */
</style>
