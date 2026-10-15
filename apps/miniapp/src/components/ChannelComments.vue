<script setup lang="ts">
import { onMounted, ref } from 'vue'
import CommunitySheet from './CommunitySheet.vue'
import CommunityAvatar from './CommunityAvatar.vue'
import { demo } from '../store'
import { notify, requireLogin } from '../navigation'
import { communityTime, createSubmissionKey, getComments, publishComment, removeComment, type CommunityComment } from '../services/community'
const props = defineProps<{postId: number}>()
const emit = defineEmits<{close: []; change: [delta: number]}>()
const rows = ref<CommunityComment[]>([]), next = ref<number|null>(null)
const loading = ref(false), sending = ref(false), draft = ref(''), error = ref('')
const submissionKey = createSubmissionKey('community-comment')
async function load(more = false) {
  if (loading.value) return
  loading.value = true; error.value = ''
  try {
    const data = await getComments(props.postId, more ? next.value ?? undefined : undefined)
    rows.value = (more ? [...rows.value, ...data.results.filter(row => !rows.value.some(old => old.id === row.id))] : data.results).sort((a,b) => a.id-b.id)
    next.value = data.next_after
  } catch (cause) { error.value = (cause as Error).message }
  finally { loading.value = false }
}
async function send() {
  if (!demo.loggedIn) { requireLogin('channel'); return }
  const text = draft.value.trim()
  if (!text || sending.value) return
  sending.value = true
  try {
    const comment = await publishComment(props.postId, text, submissionKey(text))
    if (!rows.value.some(row => row.id === comment.id)) { rows.value.push(comment); emit('change', 1) }
    draft.value = ''
    submissionKey.reset()
  } catch (cause) { notify((cause as Error).message) }
  finally { sending.value = false }
}
async function remove(comment: CommunityComment) {
  uni.showModal({title:'删除评论', content:'删除后将不再公开展示。', success: async result => {
    if (!result.confirm) return
    try { await removeComment(comment.id); rows.value = rows.value.filter(row => row.id !== comment.id); emit('change', -1) }
    catch (cause) { notify((cause as Error).message) }
  }})
}
onMounted(() => load())
</script>
<template>
  <CommunitySheet title="评论" :busy="sending" @close="emit('close')">
    <scroll-view scroll-y class="comments-body">
      <view v-if="!rows.length && loading" class="comments-empty">正在加载评论…</view>
      <view v-else-if="!rows.length && !error" class="comments-empty">还没有评论，来聊聊你的想法吧</view>
      <view v-for="comment in rows" :key="comment.id" class="comment-row">
        <CommunityAvatar :name="comment.author.nickname" :url="comment.author.avatar_url"/>
        <view class="comment-main"><view class="comment-name">{{ comment.author.nickname }}</view><view class="comment-text">{{ comment.content }}</view><view class="comment-meta"><text>{{ communityTime(comment.created_at) }}</text><button v-if="comment.can_delete" class="ui-btn delete-comment" @click="remove(comment)">删除</button></view></view>
      </view>
      <view v-if="error" class="comments-empty">{{ error }}<button class="ui-btn comments-more" @click="load(rows.length>0)">重试</button></view>
      <button v-else-if="next" class="ui-btn comments-more" :disabled="loading" @click="load(true)">{{ loading ? '加载中…' : '加载更多评论' }}</button>
    </scroll-view>
    <view class="comment-composer"><input v-model="draft" class="comment-input" placeholder="友好交流，说说你的想法" maxlength="300" confirm-type="send" :disabled="sending" @confirm="send"/><button class="ui-btn comment-send" :disabled="sending || (demo.loggedIn && !draft.trim())" @click="send">{{ demo.loggedIn ? '发送' : '登录' }}</button></view>
  </CommunitySheet>
</template>
<style scoped>
.comments-body{height:0;flex:1;padding:0 20px}.comment-row{display:flex;gap:10px;padding:18px 0;border-bottom:1px solid #eee8f1}.comment-main{flex:1;min-width:0}.comment-name{font-size:13px;font-weight:600;color:#746186}.comment-text{font-size:14px;line-height:1.7;white-space:pre-wrap;overflow-wrap:anywhere;margin:5px 0 8px}.comment-meta{display:flex;justify-content:space-between;font-size:10px;color:#a096a5}.delete-comment{font-size:11px;color:#9c7c8b}.comments-empty{padding:55px 15px;text-align:center;font-size:13px;color:#94879d}.comments-more{margin:20px auto;padding:10px;font-size:13px;color:#82689d}.comment-composer{padding:14px 20px;display:flex;align-items:center;gap:12px;border-top:1px solid #eee8f1;flex-shrink:0}.comment-input{background:#eeeaf2;border-radius:22px;padding:0 12px;flex:1;height:44px;font-size:13px}.comment-send{font-size:14px;color:#82689d;flex-shrink:0;padding:8px}
</style>
