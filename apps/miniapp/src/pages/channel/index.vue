<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow, onHide } from '@dcloudio/uni-app'
import PageShell from '../../components/PageShell.vue'
import ChannelFeed from '../../components/ChannelFeed.vue'
import ChannelLeaderboard from '../../components/ChannelLeaderboard.vue'
import { request, mediaUrl } from '../../api/client'
import type { ApiGame } from '../../api/types'
import { demo } from '../../store'

const partitions = ref<ApiGame[]>([]), selectedId = ref<number|null>(null)
const section = ref<'feed'|'ranking'>('feed'), loading = ref(false), error = ref('')
const modalOpen = ref(false), visit = ref(0), visible = ref(true)
const selected = computed(() => partitions.value.find(game => game.id===selectedId.value))
const subtitles: Record<string,string> = {王者荣耀:'峡谷里的默契，生活里的同频',和平精英:'一起落地，一起分享每次胜利',无畏契约:'好配合，值得被看见',英雄联盟:'相遇峡谷，也相聚在这里'}
const symbols: Record<string,string> = {王者荣耀:'王',和平精英:'平',无畏契约:'契',英雄联盟:'盟'}
async function loadGames() {
  loading.value=true; error.value=''
  try {
    partitions.value = await request<ApiGame[]>('/games/')
    if (!partitions.value.some(game => game.id===selectedId.value)) selectedId.value=partitions.value[0]?.id ?? null
  } catch (cause) { error.value=(cause as Error).message }
  finally { loading.value=false }
}
function selectGame(id: number) { selectedId.value=id; modalOpen.value=false }
onShow(() => { visible.value=true; visit.value++; void loadGames() })
onHide(() => { visible.value=false; modalOpen.value=false })
</script>
<template>
  <page-meta :page-style="modalOpen?'overflow: hidden;':''"/>
  <PageShell title="频道" compact>
    <view class="channel-caption">找到同好，让热爱有回响</view>
    <view v-if="error" class="channel-state">{{ error }}<button class="ui-btn reload-games" @click="loadGames">重新加载游戏</button></view>
    <view v-else-if="loading && !partitions.length" class="channel-state">正在加载游戏分区…</view>
    <view v-else-if="!partitions.length" class="channel-state">还没有开放的游戏分区</view>
    <view v-else class="channel-layout">
      <scroll-view scroll-y class="game-rail">
        <text class="rail-label">游戏分区</text>
        <button v-for="game in partitions" :key="game.id" class="ui-btn game-option" :class="{chosen:game.id===selectedId}" :aria-label="'切换到'+game.name" @click="selectGame(game.id)">
          <view class="game-symbol"><image v-if="game.icon" :src="mediaUrl(game.icon)" mode="aspectFill"/><text v-else>{{ symbols[game.name] || game.name.slice(0,1) }}</text></view><text>{{ game.name }}</text>
        </button>
        <view class="rail-decoration">✦</view>
      </scroll-view>
      <view v-if="selected" class="channel-main">
        <view class="game-intro"><view class="intro-eyebrow">GAME COMMUNITY <text>✦</text></view><view class="intro-title">{{ selected.name }}</view><view class="intro-subtitle">{{ subtitles[selected.name] || '分享游戏日常，遇见同频队友' }}</view></view>
        <view class="section-tabs"><button class="ui-btn section-tab" :class="{active:section==='feed'}" @click="section='feed'">玩家动态<text v-if="section==='feed'" class="tab-dot"/></button><button class="ui-btn section-tab" :class="{active:section==='ranking'}" @click="section='ranking'">陪玩榜单<text v-if="section==='ranking'" class="tab-dot"/></button></view>
        <template v-if="visible"><ChannelFeed v-if="section==='feed'" :key="selected.id+'-'+visit+'-'+(demo.me?.id||'guest')" :game-id="selected.id" :game-name="selected.name" @modal="modalOpen=$event"/><ChannelLeaderboard v-else :key="selected.id+'-'+visit" :game-id="selected.id"/></template>
      </view>
    </view>
  </PageShell>
</template>
<style scoped>
.channel-caption{font-size:12px;color:#a497ad;padding:0 20px 22px}.channel-layout{display:flex;align-items:stretch;min-height:calc(100vh - 200px);padding-bottom:30px}.game-rail{width:78px;flex-shrink:0;background:#eeebf1;border-radius:0 22px 0 0;padding:18px 6px;align-self:flex-start;position:sticky;top:0;height:calc(100vh - 160px)}.rail-label{display:block;text-align:center;font-size:9px;letter-spacing:1px;color:#b0a3bb;margin:0 0 20px}.game-option{position:relative;display:flex;flex-direction:column;align-items:center;gap:9px;width:100%;padding:13px 4px;margin-bottom:8px;font-size:10px;color:#a597af;border-radius:14px;line-height:1.5}.game-option.chosen{background:#e0d6eb;color:#795b98;font-weight:600}.game-option.chosen::before{content:'';position:absolute;left:-6px;top:25px;width:3px;height:20px;background:#9c82b5;border-radius:0 3px 3px 0}.game-symbol{width:32px;height:32px;display:flex;align-items:center;justify-content:center;border-radius:11px;background:#e5e0eb;color:#a798b6;font-size:16px;font-weight:600}.chosen .game-symbol{background:#c6b4da;color:#fff}.game-symbol image{width:100%;height:100%;border-radius:11px}.rail-decoration{text-align:center;color:#c4b7d1;margin-top:28px;font-size:20px}.channel-main{min-width:0;flex:1;padding:0 16px 15px}.game-intro{padding:5px 0 14px}.intro-eyebrow{font-size:8px;letter-spacing:1.6px;color:#b6a4c6;display:flex;align-items:center;gap:10px}.intro-eyebrow text{font-size:16px;color:#b5a0c6}.intro-title{font-size:23px;font-weight:650;color:#61526f;letter-spacing:.5px;margin:7px 0}.intro-subtitle{font-size:10px;color:#a69aaf;line-height:1.8}.section-tabs{display:flex;gap:25px;border-bottom:1px solid #e9e2ee;margin-bottom:20px}.section-tab{position:relative;padding:10px 0 14px;font-size:14px;color:#b0a2bb;line-height:1.5}.section-tab.active{color:#7c5e98;font-weight:600}.tab-dot{position:absolute;bottom:-2px;left:50%;width:20px;height:3px;border-radius:4px;background:#9679af;transform:translateX(-50%)}.channel-state{padding:60px 24px;text-align:center;color:#998ba4;font-size:13px}.reload-games{margin:20px auto;color:#82689d;font-size:13px;padding:10px}
@media(max-width:350px){.game-rail{width:66px;padding-left:4px;padding-right:4px}.game-option{font-size:9px}.channel-main{padding-left:12px;padding-right:12px}.intro-title{font-size:21px}.section-tabs{gap:20px}.section-tab{font-size:13px}}
</style>
