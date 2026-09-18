<script setup lang="ts">
withDefaults(defineProps<{name:string;size?:number;active?:boolean}>(),{size:24,active:false})
</script>
<template><image :src="`/static/icons/${name}${active?'-active':''}.png`" :style="{width:size+'px',height:size+'px',flexShrink:0}" mode="aspectFit" /></template>
