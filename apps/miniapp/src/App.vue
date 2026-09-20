<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app'
import { restore } from './store'
import { restoreAccessToken } from './api/client'
import { loadCatalog } from './services/catalog'
onLaunch(()=>{restore();restoreAccessToken();loadCatalog().catch(()=>{})})
</script>
<style>
@import './styles.css';
</style>
