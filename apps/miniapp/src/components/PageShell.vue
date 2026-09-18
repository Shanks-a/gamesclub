<script setup lang="ts">
import { ref } from 'vue'
import { back } from '../navigation'
import AppIcon from './AppIcon.vue'
withDefaults(defineProps<{title:string;subtitle?:string;backable?:boolean}>(),{backable:false})
const top=ref(20), navHeight=ref(48)
// #ifdef MP-WEIXIN
const system=uni.getSystemInfoSync();top.value=system.statusBarHeight || 20
const menu=uni.getMenuButtonBoundingClientRect();navHeight.value=(menu.top-top.value)*2+menu.height
// #endif
</script>
<template>
 <view class="shell">
  <view :style="{height:top+'px'}" />
  <view class="mini-nav" :style="{height:navHeight+'px'}"><text class="demo-label">交互演示 · 非真实交易</text></view>
  <view class="page-heading between">
   <view class="row gap"><button v-if="backable" class="ui-btn back-button" aria-label="返回" @click="back"><AppIcon name="back" /></button><text class="page-title">{{title}}</text></view>
   <view class="row gap"><slot name="actions" /></view>
  </view>
  <view v-if="subtitle" class="subtitle">{{subtitle}}</view>
  <slot />
 </view>
</template>
<style scoped>
.shell{min-height:100%;padding-bottom:24rpx}.mini-nav{display:flex;align-items:center;padding:0 38rpx}.demo-label{font-size:19rpx;letter-spacing:1rpx;color:#887e94}.page-heading{padding:8rpx 38rpx 14rpx;min-height:86rpx}.page-title{font-size:48rpx;font-weight:700;letter-spacing:-1rpx}.subtitle{padding:0 38rpx;color:#747486;font-size:25rpx}.back-button{display:flex;align-items:center;justify-content:center;width:40rpx;height:64rpx}
</style>
