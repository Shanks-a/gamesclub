<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import CommunitySheet from './CommunitySheet.vue'
import { demo } from '../store'
import { mediaUrl } from '../api/client'
import { notify } from '../navigation'
import { createSubmissionKey, publishPost, uploadCommunityImage, type CommunityImage, type CommunityPost } from '../services/community'

const props = defineProps<{gameId: number; gameName: string}>()
const emit = defineEmits<{close: []; published: [post: CommunityPost]}>()
const content = ref(''), images = ref<CommunityImage[]>([])
const busy = ref(false), uploading = ref(false), error = ref('')
const locked = computed(() => busy.value || uploading.value)
const canPublish = computed(() => !locked.value && (!!content.value.trim() || images.value.length > 0))
const draftKey = `channel-draft-${demo.me?.id}-${props.gameId}`
const submissionKey = createSubmissionKey('community-post')
onMounted(() => {
  try { const draft = uni.getStorageSync(draftKey); if (typeof draft === 'string') content.value = draft.slice(0, 1000) } catch { /* Draft storage is optional. */ }
})
function saveDraft() {
  try { uni.setStorageSync(draftKey, content.value) } catch { /* Keep the editor usable without device storage. */ }
}
async function chooseImages() {
  if (locked.value || images.value.length >= 9) return
  uni.chooseImage({count: 9-images.value.length, sizeType:['compressed'], sourceType:['album'], success: async selection => {
    uploading.value = true; error.value = ''
    try {
      for (const path of selection.tempFilePaths) images.value.push(await uploadCommunityImage(path))
    } catch (cause) { error.value = (cause as Error).message }
    finally { uploading.value = false }
  }})
}
async function publish() {
  if (!canPublish.value) return
  busy.value = true; error.value = ''
  const text = content.value.trim(), ids = images.value.map(image => image.id)
  try {
    const post = await publishPost(props.gameId, text, ids, submissionKey(JSON.stringify([text, ids])))
    try { uni.removeStorageSync(draftKey) } catch { /* Publishing already succeeded. */ }
    emit('published', post)
  } catch (cause) { error.value = (cause as Error).message }
  finally { busy.value = false }
}
function close() {
  if (locked.value) return
  saveDraft()
  if (content.value.trim()) notify('文字已保留为本机草稿')
  emit('close')
}
</script>
<template>
  <CommunitySheet title="分享游戏日常" :busy="locked" @close="close">
    <scroll-view scroll-y class="composer-body">
      <view class="composer-game">发布到 · {{ gameName }}</view>
      <textarea v-model="content" class="composer-input" placeholder="今天有什么想分享？记录高光、聊聊心得，或和同好打个招呼…" maxlength="1000" :disabled="locked" @input="saveDraft" />
      <view class="composer-count">{{ content.length }} / 1000</view>
      <view class="composer-images">
        <view v-for="(image, index) in images" :key="image.id" class="image-cell"><image :src="mediaUrl(image.url)" mode="aspectFill"/><button class="ui-btn remove-image" :disabled="locked" aria-label="移除图片" @click="images.splice(index,1)">×</button></view>
        <button v-if="images.length<9" class="ui-btn add-image" :disabled="locked" @click="chooseImages"><text>＋</text><text>{{ uploading ? '上传中…' : '添加图片' }}</text></button>
      </view>
      <view class="composer-note">最多 9 张图片，每张不超过 5MB。动态及评论对所有玩家公开。</view>
      <view v-if="error" class="composer-error">{{ error }}</view>
    </scroll-view>
    <view class="composer-footer"><text>分享热爱，友好交流</text><button class="ui-btn publish-button" :disabled="!canPublish" :loading="busy" @click="publish">发布动态</button></view>
  </CommunitySheet>
</template>
<style scoped>
.composer-body{flex:1;height:0;padding:0 20px}.composer-game{display:inline-block;background:#ebe5f1;color:#7e659b;border-radius:20px;padding:6px 12px;font-size:12px;margin:0 0 16px}
.composer-input{width:100%;height:170px;box-sizing:border-box;font-size:15px;line-height:1.8}.composer-count{text-align:right;color:#99919e;font-size:11px;margin-bottom:16px}
.composer-images{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.image-cell,.add-image{position:relative;height:88px;border-radius:12px;overflow:hidden;background:#ece8f0}.image-cell image{width:100%;height:100%}.remove-image{position:absolute;right:0;top:0;width:26px;height:26px;background:#4c4359;color:white;border-radius:0 0 0 10px;font-size:20px}.add-image{display:flex;align-items:center;justify-content:center;flex-direction:column;font-size:11px;color:#8a769c;gap:4px}.add-image text:first-child{font-size:27px}
.composer-note{color:#918896;font-size:11px;line-height:1.8;margin:16px 0}.composer-error{font-size:13px;color:#b54e59;margin-bottom:16px}.composer-footer{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-shrink:0;border-top:1px solid #eae5ef;padding:14px 20px;font-size:12px;color:#9b91a2}.publish-button{padding:12px 22px;background:#82689d;color:white;border-radius:24px;font-size:14px}
</style>
