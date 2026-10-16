<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

interface OrderRow { id:number; order_no:string; status:string; version:number; game_id:number; partner?:number|null; preferred_partner?:number|null; preferred_partner_info?:{nickname:string}|null }
interface PartnerRow { id:number; nickname:string; game:{id:number}; is_active:boolean }
const props=defineProps<{order:OrderRow}>()
const emit=defineEmits<{updated:[]}>()
const opened=ref(false), loading=ref(false), busy=ref(false), loadError=ref('')
const candidates=ref<PartnerRow[]>([]), partnerId=ref<number|null>(null), note=ref(''), confirmed=ref(false)
const version=ref(0)
const targetOrder=ref<OrderRow|null>(null)
const canAssign=computed(()=>['PENDING_ARRANGEMENT','PENDING_ACCEPTANCE'].includes(props.order.status))
const changingPreferred=computed(()=>!!targetOrder.value?.preferred_partner && partnerId.value!==targetOrder.value.preferred_partner)
async function loadCandidates(){
  loading.value=true; loadError.value=''; candidates.value=[]
  try {
    let page=1
    while(true){
      const data=await api(`partners/?game=${targetOrder.value!.game_id}&active=true&page_size=100&page=${page}`)
      candidates.value.push(...data.results)
      if(candidates.value.length>=data.count)break
      page++
    }
  }catch(e){loadError.value=(e as Error).message}finally{loading.value=false}
}
function open(){
  targetOrder.value={...props.order}
  version.value=props.order.version
  partnerId.value=props.order.preferred_partner||props.order.partner||null
  note.value=''; confirmed.value=false; opened.value=true
  void loadCandidates()
}
async function assign(){
  if(busy.value||!targetOrder.value)return
  if(!confirmed.value||!candidates.value.some(p=>p.id===partnerId.value)){
    ElMessage.warning('请选择有效陪玩，并确认已沟通接单');return
  }
  if(changingPreferred.value&&!note.value.trim()){
    ElMessage.warning('请记录与客户协商更换人选的情况');return
  }
  busy.value=true
  try{
    await api(`orders/${targetOrder.value.id}/assign/`,'POST',{version:version.value,partner_id:partnerId.value,note:note.value.trim()})
    opened.value=false; ElMessage.success('已确认接单，订单资料及会话已同步')
  }catch(e){ElMessage.error((e as Error).message)}finally{busy.value=false;emit('updated')}
}
</script>
<template>
  <el-button v-if="canAssign" link type="success" :disabled="busy" @click="open">确认接单</el-button>
  <el-tag v-else-if="order.status==='ACCEPTED'" type="info">待陪玩开始</el-tag>
  <el-tag v-else-if="order.status==='IN_SERVICE'">陪玩服务中</el-tag><el-tag v-else-if="order.status==='PENDING_CONFIRMATION'" type="warning">待用户确认</el-tag>
  <el-dialog v-model="opened" title="客服确认接单" width="520px" append-to-body :close-on-click-modal="!busy" :close-on-press-escape="!busy" :show-close="!busy">
    <el-form label-width="100px">
      <el-form-item label="订单号">{{targetOrder?.order_no}}</el-form-item>
      <el-form-item v-if="targetOrder?.preferred_partner" label="客户意向"><el-tag>{{targetOrder.preferred_partner_info?.nickname||`#${targetOrder.preferred_partner}`}}</el-tag></el-form-item>
      <el-alert title="请先在群内或私下确认陪玩可以接单。系统不会群发或通知陪玩。" type="info" :closable="false"/>
      <el-form-item label="实际接单人">
        <el-select v-model="partnerId" filterable :loading="loading" :disabled="busy||loading" placeholder="选择该游戏的陪玩">
          <el-option v-for="p in candidates" :key="p.id" :value="p.id" :label="`${p.nickname}（ID ${p.id}）`"/>
        </el-select>
      </el-form-item>
      <el-alert v-if="loadError" :title="loadError" type="error" :closable="false"><el-button @click="loadCandidates">重新加载</el-button></el-alert>
      <el-form-item label="处理说明" :required="changingPreferred"><el-input v-model="note" type="textarea" :maxlength="500" show-word-limit :disabled="busy" placeholder="更换指定陪玩时，请记录客户同意更换的沟通情况"/></el-form-item>
      <el-checkbox v-model="confirmed" :disabled="busy">已确认陪玩同意接单，且已与客户确认人选</el-checkbox>
    </el-form>
    <template #footer><el-button :disabled="busy" @click="opened=false">取消</el-button><el-button type="primary" :loading="busy" :disabled="loading||!!loadError||!confirmed" @click="assign">确认接单</el-button></template>
  </el-dialog>
</template>
