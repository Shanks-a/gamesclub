<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'
defineProps<{ title: string; busy?: boolean }>()
const emit = defineEmits<{ close: [] }>()
let overflow = ''
onMounted(() => {
  uni.hideTabBar({animation:false})
  // #ifdef H5
  overflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  // #endif
})
onBeforeUnmount(() => {
  uni.showTabBar({animation:false})
  // #ifdef H5
  document.body.style.overflow = overflow
  // #endif
})
</script>
<template>
  <view class="community-mask" @click="!busy && emit('close')" @touchmove.stop.prevent />
  <view class="community-sheet" role="dialog" aria-modal="true" :aria-label="title" @touchmove.stop>
    <view class="sheet-heading"><text>{{ title }}</text><button class="ui-btn sheet-close" :disabled="busy" aria-label="关闭弹窗" @click="emit('close')">×</button></view>
    <slot />
  </view>
</template>
<style scoped>
.community-mask{position:fixed;inset:0;z-index:1000;background:rgba(42,35,48,.4)}
.community-sheet{position:fixed;bottom:0;left:0;right:0;z-index:1001;max-width:480px;margin:auto;height:78vh;max-height:90vh;display:flex;flex-direction:column;background:#f8f7f4;border-radius:24px 24px 0 0;padding-bottom:env(safe-area-inset-bottom);overflow:hidden}
.sheet-heading{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;font-size:18px;font-weight:600;flex-shrink:0}
.sheet-close{width:36px;height:36px;font-size:25px;color:#8d8198}
</style>
