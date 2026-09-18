<script setup lang="ts">
import { ref, computed } from 'vue'
import PageShell from '../../components/PageShell.vue'
import AppIcon from '../../components/AppIcon.vue'
import EmptyState from '../../components/EmptyState.vue'
import { games, topics } from '../../domain'
import { detail } from '../../navigation'
const selected=ref('王者荣耀'), query=ref('')
const list=computed(()=>topics.filter(t=>(selected.value==='全部'||t.game===selected.value)&&`${t.title}${t.game}${t.author}`.includes(query.value.trim())))
</script>
<template><PageShell title="频道" subtitle="找到同好，一起开局">
 <view class="search-wrap"><view class="search"><AppIcon name="search" :size="20"/><input v-model="query" placeholder="搜索频道、游戏或感兴趣的话题"/><button v-if="query" class="ui-btn clear" @click="query=''">清除</button></view></view>
 <view class="channel-layout"><view class="sidebar"><button class="ui-btn" v-for="game in ['全部',...games]" :key="game" :class="{chosen:selected===game}" @click="selected=game">{{game}}</button><button class="ui-btn" @click="detail('games')">更多游戏</button></view>
  <view class="channel-content"><view class="heading">{{selected==='全部'?'发现同好':selected}}</view><view class="small muted intro">同频玩家 · 快乐组队</view>
   <view class="soft banner" @click="detail('topic',list[0]?.id || '0-0')"><view class="heading">今晚，一起冲分</view><view class="small muted">进入组队话题，寻找默契队友</view><view class="accent small">去组队 →</view></view>
   <view class="heading topic-heading">发现频道</view>
   <view v-for="topic in list" :key="topic.id" class="topic" @click="detail('topic',topic.id)"><text class="hash">#</text><view class="grow"><view class="topic-title">{{topic.title}}</view><view class="tiny muted">{{topic.author}} · {{topic.count}} 条讨论<text v-if="selected==='全部'"> · {{topic.game}}</text></view></view></view>
   <EmptyState v-if="!list.length" title="没有找到话题" description="换个关键词试试。"/>
  </view>
 </view>
</PageShell></template>
<style scoped>
.search-wrap{padding:0 38rpx}.channel-layout{display:flex;min-height:68vh}.sidebar{width:168rpx;flex-shrink:0;background:#eeedf0;padding:20rpx 14rpx}.sidebar button{height:112rpx;margin:0 0 32rpx;font-size:23rpx;color:#747486;border-radius:24rpx;display:flex;align-items:center;justify-content:center}.sidebar .chosen{background:#ddd5ea;color:#80699e;font-weight:600}.channel-content{flex:1;min-width:0;padding:22rpx 38rpx 28rpx 30rpx}.intro{margin:12rpx 0 26rpx}.banner{padding:26rpx}.banner .heading{font-size:32rpx}.banner .small{margin-top:16rpx;font-size:21rpx}.topic-heading{margin:36rpx 0 14rpx;font-size:30rpx}.topic{display:flex;gap:15rpx;padding:25rpx 0 32rpx}.hash{font-size:34rpx;color:#8875aa;font-weight:700}.topic-title{font-size:26rpx;font-weight:600;margin-bottom:12rpx}
</style>
