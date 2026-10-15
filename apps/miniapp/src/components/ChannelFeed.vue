<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import CommunityAvatar from './CommunityAvatar.vue'
import ChannelComposer from './ChannelComposer.vue'
import ChannelComments from './ChannelComments.vue'
import { demo } from '../store'
import { mediaUrl } from '../api/client'
import { notify, requireLogin } from '../navigation'
import { communityTime, getPosts, previewImages, removePost, setPostLike, type CommunityPost } from '../services/community'
const props = defineProps<{ gameId: number; gameName: string }>()
const emit = defineEmits<{ modal: [open: boolean] }>()
const posts = ref<CommunityPost[]>([]), next = ref<number|null>(null)
const loading = ref(false), error = ref(''), composing = ref(false)
const commentPost = ref<CommunityPost|null>(null), liking = ref<number[]>([])
async function load(more = false) {
  if (loading.value) return
  loading.value = true; error.value = ''
  try {
    const data = await getPosts(props.gameId, more ? next.value ?? undefined : undefined)
    posts.value = more ? [...posts.value, ...data.results.filter(row => !posts.value.some(post => post.id === row.id))] : data.results
    next.value = data.next_before
  } catch (cause) { error.value = (cause as Error).message }
  finally { loading.value = false }
}
function compose() {
  if (!demo.loggedIn) { requireLogin('channel'); return }
  composing.value = true; emit('modal', true)
}
function closeModal() { composing.value = false; commentPost.value = null; emit('modal', false) }
function published(post: CommunityPost) {
  posts.value = [post, ...posts.value.filter(old => old.id !== post.id)]
  closeModal(); notify('动态已发布')
}
async function like(post: CommunityPost) {
  if (!demo.loggedIn) { requireLogin('channel'); return }
  if (liking.value.includes(post.id)) return
  liking.value.push(post.id)
  try { Object.assign(post, await setPostLike(post.id, !post.liked)) }
  catch (cause) { notify((cause as Error).message) }
  finally { liking.value = liking.value.filter(id => id !== post.id) }
}
function comments(post: CommunityPost) { commentPost.value = post; emit('modal', true) }
function changeCommentCount(delta: number) { if (commentPost.value) commentPost.value.comment_count = Math.max(0, commentPost.value.comment_count + delta) }
function remove(post: CommunityPost) {
  uni.showModal({title:'删除动态', content:'这条动态及其评论将不再公开展示。', success: async result => {
    if (!result.confirm) return
    try { await removePost(post.id); posts.value = posts.value.filter(item => item.id !== post.id) }
    catch (cause) { notify((cause as Error).message) }
  }})
}
onMounted(() => load())
onBeforeUnmount(() => emit('modal', false))
</script>
<template>
  <view class="feed">
    <button class="ui-btn share-entry" @click="compose"><CommunityAvatar :name="demo.me?.nickname || '我'" :url="demo.me?.avatar_url"/><view class="share-prompt"><text>分享你的游戏日常</text><text class="share-sub">高光时刻 · 上分心得 · 寻找同好</text></view><text class="share-plus">＋</text></button>
    <view class="feed-heading"><text>玩家动态</text><button class="ui-btn feed-refresh" :disabled="loading" @click="load()">{{ loading ? '刷新中' : '最新 · 刷新' }}</button></view>
    <view v-if="!posts.length && loading" class="feed-empty">正在寻找同频的声音…</view>
    <view v-else-if="!posts.length && !error" class="feed-empty"><view class="empty-mark">✦</view><view class="empty-title">故事从你开始</view><view>还没有玩家分享 {{ gameName }} 的日常</view><button class="ui-btn first-post" @click="compose">发布第一条动态</button></view>
    <view v-for="post in posts" :key="post.id" class="post">
      <view class="post-heading"><CommunityAvatar :name="post.author.nickname" :url="post.author.avatar_url"/><view class="post-author"><text class="post-name">{{ post.author.nickname }}</text><text class="post-time">{{ communityTime(post.created_at) }}</text></view><button v-if="post.can_delete" class="ui-btn post-delete" aria-label="删除动态" @click="remove(post)">删除</button></view>
      <view v-if="post.content" class="post-text">{{ post.content }}</view>
      <view v-if="post.images.length" class="post-images" :class="{single:post.images.length===1}"><image v-for="(image,index) in post.images" :key="image.id" :src="mediaUrl(image.url)" mode="aspectFill" @click="previewImages(post.images,index)"/></view>
      <view class="post-footer"><text class="post-game"># {{ gameName }}</text><view class="post-actions"><button class="ui-btn post-action" :class="{liked:post.liked}" :disabled="liking.includes(post.id)" :aria-label="post.liked?'取消点赞':'点赞'" @click="like(post)"><text class="like-icon">{{ post.liked ? '♥' : '♡' }}</text>{{ post.like_count || '赞' }}</button><button class="ui-btn post-action" aria-label="查看评论" @click="comments(post)"><view class="comment-icon"/>{{ post.comment_count || '评论' }}</button></view></view>
    </view>
    <view v-if="error" class="feed-empty">{{ error }}<button class="ui-btn first-post" @click="load(posts.length>0)">重新加载</button></view>
    <button v-else-if="next" class="ui-btn load-more" :disabled="loading" @click="load(true)">{{ loading ? '加载中…' : '看看更多动态' }}</button>
    <view v-else-if="posts.length" class="feed-end">每一次分享，都让这里更热闹</view>
    <ChannelComposer v-if="composing" :game-id="gameId" :game-name="gameName" @close="closeModal" @published="published"/>
    <ChannelComments v-if="commentPost" :key="commentPost.id" :post-id="commentPost.id" @close="closeModal" @change="changeCommentCount"/>
  </view>
</template>
<style scoped>
.share-entry{display:flex;align-items:center;gap:10px;background:#fff;width:100%;text-align:left;padding:14px 12px;border-radius:16px}.share-prompt{min-width:0;flex:1;display:flex;flex-direction:column;gap:5px;font-size:13px;color:#5d526a}.share-sub{font-size:10px;color:#a397ad;line-height:1.6}.share-plus{font-size:24px;color:#8b70a4;flex-shrink:0}
.feed-heading{display:flex;align-items:center;justify-content:space-between;padding:24px 0 12px;font-size:15px;font-weight:600}.feed-refresh{font-size:10px;color:#9d90a8;font-weight:400}.post{padding:17px 0;border-bottom:1px solid #e9e4ed}.post-heading{display:flex;gap:9px;align-items:center}.post-author{flex:1;min-width:0;display:flex;flex-direction:column;gap:3px}.post-name{font-size:13px;font-weight:600;color:#675875;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.post-time{font-size:9px;color:#a096a5}.post-delete{font-size:10px;color:#9d8fa7;padding:6px 0 6px 8px}.post-text{font-size:13px;line-height:1.85;margin:12px 0;white-space:pre-wrap;overflow-wrap:anywhere}.post-images{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px}.post-images image{width:100%;height:75px;border-radius:8px}.post-images.single{grid-template-columns:1fr}.post-images.single image{height:180px}.post-footer{display:flex;align-items:center;justify-content:space-between;gap:6px;flex-wrap:wrap;margin-top:12px}.post-game{font-size:10px;color:#a495b1}.post-actions{display:flex;gap:14px}.post-action{font-size:11px;color:#9b8da5;display:flex;align-items:center;gap:4px;padding:4px 0}.post-action.liked{color:#ae6b87}.like-icon{font-size:20px;line-height:1}.comment-icon{width:12px;height:10px;border:1.3px solid currentColor;border-radius:4px;position:relative}.comment-icon::after{content:'';position:absolute;bottom:-3px;left:3px;width:3px;height:3px;border-left:1px solid currentColor;transform:skewY(-35deg)}
.feed-empty{text-align:center;font-size:12px;line-height:1.9;color:#a094aa;padding:35px 10px}.empty-mark{font-size:32px;color:#ad9ac0;margin-bottom:8px}.empty-title{font-size:16px;color:#766486;margin-bottom:8px}.first-post{font-size:12px;color:#82689d;padding:10px 16px;border-radius:22px;background:#ebe5f0;margin:16px auto 0}.load-more{font-size:12px;color:#82689d;margin:20px auto;padding:10px}.feed-end{font-size:10px;color:#b3a9bb;text-align:center;padding:25px 0}
@media(max-width:350px){.share-entry{gap:7px;padding:12px 8px}.share-prompt{font-size:12px}.share-sub{font-size:9px}.post-actions{gap:10px}.post-images image{height:60px}}
</style>
