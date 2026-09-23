<script setup lang="ts">
import { money, type Product } from '../domain'
import { detail } from '../navigation'
defineProps<{product:Product;horizontal?:boolean}>()
</script>
<template>
 <button class="ui-btn product" :class="{horizontal}" @click="detail('product',product.id)">
  <view class="cover"><image :src="product.cover || `/static/art/product-${product.art}.png`" mode="aspectFill" class="art"/><text v-if="!horizontal && product.original>product.price" class="badge">特惠</text></view>
  <view class="product-text"><view class="name">{{product.title}}</view><view class="desc">{{product.game}} · 1小时</view><view class="price">¥{{money(product.price)}}<text v-if="!horizontal" class="old">¥{{money(product.original)}}</text><text v-else class="unit"> / 小时</text></view></view>
 </button>
</template>
<style scoped>
.product{width:100%;text-align:left;background:#fff;border-radius:28rpx;padding:16rpx;overflow:hidden}.cover{position:relative;height:194rpx;border-radius:22rpx;overflow:hidden}.art{width:100%;height:100%}.badge{position:absolute;left:14rpx;top:14rpx;background:#fff;border-radius:30rpx;font-size:20rpx;color:#747486;padding:7rpx 15rpx}.product-text{padding:17rpx 8rpx 6rpx}.name{font-size:27rpx;font-weight:600}.desc{font-size:21rpx;color:#747486;margin:9rpx 0 18rpx}.price{font-size:37rpx;line-height:1.2}.horizontal{display:flex;gap:22rpx;padding:20rpx}.horizontal .cover{height:146rpx;width:146rpx;flex-shrink:0}.horizontal .product-text{padding:7rpx 0;flex:1}.horizontal .name{font-size:30rpx}.horizontal .price{font-size:30rpx}.unit{font-size:24rpx}
</style>
