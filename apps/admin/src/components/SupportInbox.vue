<script setup lang="ts">
import { ref,computed,nextTick,onMounted,onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
interface Message {id:number;content:string;from_staff:boolean;sender_name:string;read_at:string|null;created_at:string}
interface Thread {id:number;name:string;role:string;order_no:string;reply_state:string;unread_count:number;last_message:Message|null;messages?:Message[]}
const displayTime=(value:string)=>new Date(value).toLocaleString('zh-CN',{hour12:false})
const props=defineProps<{initialId?:number}>()
const rows=ref<Thread[]>([]),selected=ref<number|null>(props.initialId||null),current=ref<Thread|null>(null)
const history=ref<HTMLElement|null>(null)
const draft=ref(''),error=ref(''),sending=ref(false),filter=ref('all')
const list=computed(()=>rows.value.filter(row=>filter.value==='all'||(filter.value==='unread'?row.unread_count>0:row.reply_state==='needs_reply')))
let timer:ReturnType<typeof setInterval>|undefined, reading=false, active=true
const drafts=new Map<number,string>(), retries=new Map<number,{content:string;key:string}>()
function state(row:Thread){return row.reply_state==='needs_reply'?'待客服回复':row.reply_state==='awaiting_reply'?'已回复 · 等待对方':'尚无消息'}
function select(id:number){if(selected.value)drafts.set(selected.value,draft.value);selected.value=id;current.value=null;draft.value=drafts.get(id)||'';void refresh()}
async function refresh(){
  if(reading||!active||document.hidden)return
  reading=true;const id=selected.value
  try{
    const [threads,detail]=await Promise.all([api('support-conversations/'),id?api(`support-conversations/${id}/`):Promise.resolve(null)])
    if(!active)return
    rows.value=threads;error.value=''
    if(selected.value===id&&detail){const changed=current.value?.messages?.at(-1)?.id!==detail.messages.at(-1)?.id;current.value=detail;if(changed){await nextTick();if(history.value)history.value.scrollTop=history.value.scrollHeight};rows.value=rows.value.map(row=>row.id===id?{...row,unread_count:0}:row)}
  }catch(e){if(active)error.value=(e as Error).message}finally{reading=false;if(active&&selected.value!==id)void refresh()}
}
async function send(){
  const id=selected.value,content=draft.value.trim();if(!id||!content||sending.value)return
  const previous=retries.get(id), attempt=previous?.content===content?previous:{content,key:crypto.randomUUID()}
  retries.set(id,attempt);sending.value=true
  try{await api(`support-conversations/${id}/`,'POST',{content,client_key:attempt.key});retries.delete(id)
    if(selected.value===id&&draft.value.trim()===content)draft.value=''
    if(drafts.get(id)?.trim()===content)drafts.delete(id);await refresh()
  }catch(e){ElMessage.error((e as Error).message)}finally{sending.value=false}
}
onMounted(()=>{void refresh();timer=setInterval(()=>void refresh(),5000)})
onUnmounted(()=>{active=false;if(timer)clearInterval(timer)})
</script>
<template>
  <p>团队共享收件箱 · 每 5 秒自动更新 · 打开会话标为团队已读，回复后才消除「待客服回复」。</p>
  <el-alert v-if="error" :title="error" type="error"/>
  <div class="support-inbox">
    <aside><el-radio-group v-model="filter"><el-radio-button value="all">全部</el-radio-button><el-radio-button value="needs_reply">待回复</el-radio-button><el-radio-button value="unread">未读</el-radio-button></el-radio-group>
      <button v-for="row in list" :key="row.id" class="thread" :class="{selected:selected===row.id}" @click="select(row.id)"><strong>{{row.name}} · {{row.role}}</strong><span v-if="row.unread_count" class="unread">{{row.unread_count}} 未读</span><small>{{row.order_no||'一般咨询'}}</small><span>{{row.last_message?.content||'尚无消息'}}</span><small>{{state(row)}}</small></button>
      <p v-if="!list.length">暂无符合条件的会话</p>
    </aside>
    <section v-if="current"><h3>{{current.name}} · {{current.order_no||'一般咨询'}}</h3><div ref="history" class="history"><div v-for="m in current.messages" :key="m.id" class="message" :class="{mine:m.from_staff}"><small>{{m.from_staff?`客服 ${m.sender_name}`:current.name}} · {{displayTime(m.created_at)}}</small><p>{{m.content}}</p><small v-if="m.from_staff">{{m.read_at?'对方已读':'对方未读'}}</small></div></div><el-input v-model="draft" type="textarea" :rows="3" maxlength="2000" show-word-limit placeholder="输入回复；Ctrl + Enter 发送" @keydown.ctrl.enter.prevent="send"/><el-button type="primary" :loading="sending" :disabled="!draft.trim()" @click="send">发送回复</el-button></section>
    <section v-else><p>请选择会话，或从订单管理中联系用户／陪玩。</p></section>
  </div>
</template>
<style scoped>
.support-inbox{display:grid;grid-template-columns:320px minmax(0,1fr);gap:24px;margin-top:20px}.support-inbox aside{max-height:70vh;overflow:auto}.thread{display:block;width:100%;text-align:left;background:white;border:1px solid #ddd;border-radius:10px;padding:16px;margin:12px 0;cursor:pointer;overflow-wrap:anywhere}.thread.selected{border-color:#80699e;background:#f7f2ff}.thread small,.thread span{display:block;margin-top:8px}.thread span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.unread{color:#b84343}.history{height:45vh;overflow:auto;background:#f7f6f9;padding:16px;margin-bottom:16px}.message{display:flex;flex-direction:column;align-items:flex-start;margin-bottom:20px}.message.mine{align-items:flex-end}.message p{white-space:pre-wrap;overflow-wrap:anywhere;max-width:85%;padding:12px;background:white;border-radius:8px;margin:8px 0}.message.mine p{background:#e7dff3}.message small{color:#777}.el-button{margin-top:12px}
</style>
