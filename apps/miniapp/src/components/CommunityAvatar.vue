<script setup lang="ts">
import { ref, watch } from 'vue'
import { mediaUrl } from '../api/client'
const props = defineProps<{ name: string; url?: string }>()
const failed = ref(false)
watch(() => props.url, () => { failed.value = false })
</script>
<template>
  <view class="community-avatar">
    <image v-if="url && !failed" :src="mediaUrl(url)" mode="aspectFill" class="avatar-image" @error="failed=true" />
    <text v-else>{{ name.slice(0, 1) || '游' }}</text>
  </view>
</template>
<style scoped>
.community-avatar{width:38px;height:38px;flex-shrink:0;display:flex;align-items:center;justify-content:center;border-radius:13px;background:#e7dfef;color:#7c649a;font-size:17px;font-weight:600;overflow:hidden}
.avatar-image{width:100%;height:100%}
</style>
