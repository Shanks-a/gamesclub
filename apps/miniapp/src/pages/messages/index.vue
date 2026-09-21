<script setup lang="ts">
import { ref, computed } from 'vue'
import PageShell from '../../components/PageShell.vue'
import AppIcon from '../../components/AppIcon.vue'
import EmptyState from '../../components/EmptyState.vue'
import { conversations } from '../../domain'
import { demo } from '../../store'
import { requireLogin } from '../../navigation'
const query=ref('')
const list=computed(()=>conversations.filter(c=>`${c.name}${c.text}`.includes(query.value.trim())))
function preview(item:typeof conversations[number]){const messages=demo.messages[item.id]||[];return messages.length?messages[messages.length-1].text:item.text}
function open(id:string){requireLogin('detail',{kind:id==='notice'?'notifications':'chat',id})}
</script>
<template><PageShell title="会话" subtitle="每一次相遇，都从一句你好开始"><view class="body">
 <view class="search"><AppIcon name="search" :size="20"/><input v-model="query" placeholder="搜索联系人或聊天内容"/><button v-if="query" class="ui-btn clear" @click="query=''">清除</button></view>
 <view v-if="!demo.loggedIn" class="login-hint row between"><text class="small muted">登录后查看你的会话</text><button class="ui-btn accent small" @click="requireLogin('messages')">演示登录 ›</button></view>
 <template v-else><button v-for="item in list" :key="item.id" class="ui-btn conversation" @click="open(item.id)"><view :class="['avatar',item.color]">{{item.name.slice(0,1)}}</view><view class="message-text grow"><view class="between"><text class="name">{{item.name}}</text><text class="tiny muted">{{item.time}}</text></view><view class="between message-bottom"><text class="preview">{{preview(item)}}</text><text v-if="item.unread&&!demo.read.includes(item.id)" class="badge">{{item.unread}}</text></view></view></button><EmptyState v-if="!list.length" title="没有找到会话" description="试试搜索联系人姓名。"/><view v-else class="footnote">已经没有更多会话了</view></template>
 <EmptyState v-if="!demo.loggedIn" title="让每一句问候都有回应" description="登录演示只使用本地示例会话，不连接真实联系人。"/>
</view></PageShell></template>
<style scoped>
.login-hint{padding:22rpx;background:#eae4f1;border-radius:24rpx}.conversation{display:flex;gap:28rpx;text-align:left;width:100%;padding:28rpx 0 0}.message-text{padding:2rpx 0 32rpx;border-bottom:1px solid #e6e3ea;min-height:130rpx}.name{font-size:30rpx;font-weight:600}.message-bottom{margin-top:20rpx;gap:12rpx}.preview{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:23rpx;color:#747486}.badge{width:34rpx;height:34rpx;border-radius:50%;background:#80699e;color:white;font-size:20rpx;text-align:center;line-height:34rpx;flex-shrink:0}
</style>
