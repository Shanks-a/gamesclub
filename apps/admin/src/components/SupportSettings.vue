<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
const form=ref({mode:'disabled',corp_id:'',url:'',notice:''})
const loading=ref(true), busy=ref(false), error=ref('')
async function load(){loading.value=true;error.value='';try{form.value=await api('support-settings/')}catch(e){error.value=(e as Error).message}finally{loading.value=false}}
async function save(){if(busy.value)return;busy.value=true;try{form.value=await api('support-settings/','PATCH',form.value);ElMessage.success('客服配置已保存')}catch(e){ElMessage.error((e as Error).message)}finally{busy.value=false}}
onMounted(load)
</script>
<template>
  <el-divider>外部客服渠道（选配）</el-divider>
  <el-alert v-if="error" :title="error" type="error" :closable="false"><el-button @click="load">重试</el-button></el-alert>
  <el-form v-else v-loading="loading" label-position="top">
    <el-form-item label="接入渠道"><el-select v-model="form.mode"><el-option value="disabled" label="暂未配置 / 关闭"/><el-option value="wechat" label="微信小程序原生客服"/><el-option value="enterprise" label="企业微信客服"/></el-select></el-form-item>
    <template v-if="form.mode==='enterprise'"><el-form-item label="企业 ID"><el-input v-model="form.corp_id" maxlength="64"/></el-form-item><el-form-item label="客服链接"><el-input v-model="form.url" placeholder="https://work.weixin.qq.com/kfid/…" maxlength="300"/></el-form-item></template>
    <el-alert v-if="form.mode==='wechat'" title="须先在微信公众平台配置客服接待人员；浏览器预览不支持原生客服会话。" type="info" :closable="false"/>
    <el-form-item label="接待说明（选填）"><el-input v-model="form.notice" type="textarea" maxlength="200" show-word-limit placeholder="例如客服接待时间；请勿填写密钥"/></el-form-item>
    <p class="support-hint">仅超级管理员可保存。站内在线客服始终可用；这里仅配置额外的微信或企业微信入口。</p>
    <el-button type="primary" :disabled="loading" :loading="busy" @click="save">保存客服配置</el-button>
  </el-form>
</template>
<style scoped>.support-hint{font-size:13px;color:#777;line-height:1.7}</style>
