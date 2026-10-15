<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import CommunityAvatar from './CommunityAvatar.vue'
import { getLeaderboard, type Leaderboard, type RankingSort } from '../services/community'
const props = defineProps<{gameId: number}>()
const sort = ref<RankingSort>('heat'), board = ref<Leaderboard|null>(null)
const loading = ref(false), error = ref('')
let sequence = 0
const podium = computed(() => [2,1,3].map(rank => board.value?.top_three.find(partner => partner.rank === rank)))
async function load(more = false) {
  const run = ++sequence
  loading.value = true; error.value = ''
  try {
    const data = await getLeaderboard(props.gameId, sort.value, more ? board.value?.next_offset ?? 0 : 0)
    if (run !== sequence) return
    board.value = more && board.value ? {...data, results:[...board.value.results, ...data.results.filter(row => !board.value!.results.some(old => old.id===row.id))]} : data
  } catch (cause) { if (run === sequence) error.value = (cause as Error).message }
  finally { if (run === sequence) loading.value = false }
}
function changeSort(value: RankingSort) { if (sort.value===value) return; sort.value=value; board.value=null; void load() }
onMounted(() => load())
</script>
<template>
  <view class="leaderboard">
    <view class="rank-switch"><button class="ui-btn" :class="{active:sort==='heat'}" @click="changeSort('heat')">热度榜</button><button class="ui-btn" :class="{active:sort==='orders'}" @click="changeSort('orders')">接单榜</button></view>
    <view class="rank-description">{{ sort==='heat'?'近 30 天完成单量 · 人气实力派':'累计完成单量 · 默契值得信赖' }}</view>
    <view v-if="loading && !board" class="rank-empty">正在更新榜单…</view>
    <view v-else-if="board && !board.count" class="rank-empty"><view class="rank-empty-star">☆</view><view>该游戏暂无可展示的陪玩</view><view>有接单中的陪玩后，榜单将在这里展示</view></view>
    <template v-else-if="board">
      <view class="podium-section">
        <view class="podium-title"><text class="podium-line"/><text>闪耀 TOP 3</text><text class="podium-line"/></view>
        <view class="podium"><view v-for="(partner,index) in podium" :key="index" class="podium-slot" :class="{first:partner?.rank===1}">
          <template v-if="partner"><view class="medal">{{ partner.rank===1?'♛':'✦' }}</view><CommunityAvatar :name="partner.nickname" :url="partner.avatar_url"/><view class="podium-name">{{ partner.nickname }}</view><view class="podium-number">{{ sort==='heat'?partner.recent_orders:partner.completed_orders }}<text> 单</text></view><view class="podium-base" :class="'place-'+partner.rank"><text>0{{ partner.rank }}</text></view></template><view v-else class="podium-vacant">虚位以待</view>
        </view></view>
      </view>
      <view class="rank-list-heading"><text>全部排名</text><text class="rank-total">{{ board.count }} 位陪玩</text></view>
      <view v-for="partner in board.results" :key="partner.id" class="ranking-row"><text class="rank-index" :class="{leading:partner.rank<=3}">{{ String(partner.rank).padStart(2,'0') }}</text><CommunityAvatar :name="partner.nickname" :url="partner.avatar_url"/><view class="rank-person"><view class="rank-name">{{ partner.nickname }}</view><view class="rank-secondary">{{ sort==='heat'?'累计':'近30天' }} {{ sort==='heat'?partner.completed_orders:partner.recent_orders }} 单</view></view><view class="rank-score"><text>{{ sort==='heat'?partner.recent_orders:partner.completed_orders }}</text><text>完成单</text></view></view>
      <button v-if="board.next_offset!==null" class="ui-btn rank-more" :disabled="loading" @click="load(true)">{{ loading?'加载中…':'加载更多排名' }}</button>
      <view class="rank-rule">仅统计本游戏已完成订单，取消及未完成订单不计入。同分依次参考另一榜单单量及陪玩 ID。榜单仅展示当前可接单的陪玩。</view>
    </template>
    <view v-if="error" class="rank-empty">{{ error }}<button class="ui-btn rank-more" @click="load(!!board)">重新加载</button></view>
  </view>
</template>
<style scoped>
.rank-switch{display:flex;gap:6px;padding:4px;background:#ebe6f0;border-radius:26px}.rank-switch button{flex:1;padding:9px 6px;font-size:12px;border-radius:20px;color:#9b8ba8}.rank-switch button.active{background:#fff;color:#7b5e97;font-weight:600;box-shadow:0 2px 6px #d8cde833}.rank-description{font-size:10px;color:#a293ad;text-align:center;padding:12px 0 20px}.podium-section{background:linear-gradient(155deg,#f4eefa,#eee8f2 55%,#f7f1e7);border-radius:18px;padding:18px 8px 0;overflow:hidden}.podium-title{display:flex;align-items:center;justify-content:center;gap:8px;letter-spacing:2px;font-size:11px;color:#9a809f}.podium-line{height:1px;width:15px;background:#cdbfd8}.podium{display:flex;align-items:flex-end;justify-content:center;gap:5px;margin-top:22px}.podium-slot{width:33.333%;min-width:0;display:flex;flex-direction:column;align-items:center;position:relative}.medal{font-size:15px;color:#afa1bb;line-height:18px}.podium-slot.first .medal{color:#d2a24f;font-size:24px;line-height:24px}.podium-name{font-size:10px;font-weight:600;color:#7c688b;margin-top:8px;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.podium-number{font-size:16px;color:#8b6c9f;font-weight:700;margin:3px 0 10px}.podium-number text{font-size:9px;font-weight:400}.podium-base{display:flex;justify-content:center;padding-top:8px;width:100%;border-radius:10px 10px 0 0;background:linear-gradient(#e4d9ef,#eae2f0);height:46px;color:#baa8c9;font-size:24px;font-weight:700}.podium-base.place-1{height:68px;background:linear-gradient(#e4d0a9,#efe0c4);color:#b78e4e}.podium-base.place-3{height:36px;background:linear-gradient(#eadbd7,#eee4e0);color:#bb9b91}.podium-vacant{font-size:10px;color:#b5a8bd;padding-bottom:24px}.rank-list-heading{display:flex;justify-content:space-between;align-items:center;font-size:15px;font-weight:600;padding:24px 0 8px}.rank-total{font-size:10px;color:#a598ae;font-weight:400}.ranking-row{display:flex;align-items:center;gap:8px;padding:15px 0;border-bottom:1px solid #e9e3ee}.rank-index{font-size:12px;color:#b3a8bc;font-weight:600;width:18px;flex-shrink:0}.rank-index.leading{color:#ad8cbb}.rank-person{min-width:0;flex:1}.rank-name{font-size:12px;color:#65586f;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.rank-secondary{font-size:9px;color:#ac9fb6;margin-top:5px}.rank-score{display:flex;flex-direction:column;align-items:flex-end;gap:2px;flex-shrink:0}.rank-score text:first-child{font-size:17px;font-weight:600;color:#8a70a1}.rank-score text:last-child{font-size:9px;color:#b0a4b8}.rank-rule{font-size:10px;color:#a99bb2;line-height:1.9;padding:20px 0}.rank-more{font-size:12px;color:#82689d;margin:16px auto;padding:8px}.rank-empty{text-align:center;font-size:12px;color:#a194ac;line-height:2;padding:35px 10px}.rank-empty-star{font-size:32px;margin-bottom:10px}
@media(max-width:350px){.ranking-row{gap:5px}.rank-index{width:15px;font-size:10px}.rank-name{font-size:11px}}
</style>
