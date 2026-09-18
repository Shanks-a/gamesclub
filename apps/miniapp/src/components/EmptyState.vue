<script setup lang="ts">
import AppIcon from './AppIcon.vue'
withDefaults(defineProps<{title?:string;description?:string}>(),{title:'这里暂时还没有内容',description:'试试其他筛选，或稍后再来看看。'})
</script>
<template><view class="empty"><AppIcon name="message" :size="36"/><view class="empty-title">{{title}}</view><view class="small">{{description}}</view><slot/></view></template>
