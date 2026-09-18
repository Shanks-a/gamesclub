<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app'
import { restore } from './store'
onLaunch(restore)
</script>
<style>
@import './styles.css';
</style>
