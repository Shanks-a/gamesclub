import test from 'node:test'
import assert from 'node:assert/strict'
import { filterProducts,changeDemoOrder,seedOrders,money } from '../src/domain.ts'
test('filters combine game and query without altering catalog order',()=>{
 assert.equal(filterProducts('王者荣耀','双人')[0]?.id,'duo')
 assert.equal(filterProducts('和平精英','双人').length,0)
 assert.equal(filterProducts('全部','不存在').length,0)
 const sorted=filterProducts('全部','',true)
 assert.deepEqual(sorted.map(p=>p.price),[2500,2900,3200,3500,3900])
 assert.equal(filterProducts('全部')[0].id,'duo')
})
test('demo order transitions reject repeated payment and cancelled-order mutation',()=>{
 const initial={...seedOrders[0]}
 const paid=changeDemoOrder(initial,'pay')
 assert.equal(paid.tab,'待发货');assert.equal(initial.tab,'待付款')
 assert.throws(()=>changeDemoOrder(paid,'pay'))
 assert.throws(()=>changeDemoOrder(paid,'receive'))
 const cancelled=changeDemoOrder(initial,'cancel')
 assert.throws(()=>changeDemoOrder(cancelled,'pay'))
 const completed=changeDemoOrder(seedOrders[3],'receive')
 assert.equal(completed.tab,'评价')
 const reviewed=changeDemoOrder(completed,'review');assert.equal(reviewed.reviewed,true)
 assert.throws(()=>changeDemoOrder(reviewed,'review'))
})
test('integer cents display preserves fractional amounts',()=>{assert.equal(money(2900),'29');assert.equal(money(2950),'29.50');assert.equal(money(1),'0.01')})
