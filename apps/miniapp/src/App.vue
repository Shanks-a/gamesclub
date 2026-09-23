<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app'
import { restore, logoutDemo, validateSession } from './store'
import { restoreAccessToken } from './api/client'
import { loadCatalog } from './services/catalog'
onLaunch(()=>{restore();uni.$on('auth-expired',logoutDemo);if(restoreAccessToken())void validateSession().catch(()=>{});loadCatalog().catch(()=>uni.showToast({title:'目录加载失败，请检查后端连接',icon:'none'}))})
</script>
<style>
@import './styles.css';
</style>
