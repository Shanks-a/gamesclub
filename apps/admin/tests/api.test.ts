import test from 'node:test'
import assert from 'node:assert/strict'

// 全局 mock：document.cookie 与可替换的 fetch
;(globalThis as any).document = { cookie: '' }

import { api, setCsrfToken } from '../src/api.ts'

// 每次测试前重置，用 helper 设置带调用记录的 fetch mock
let calls: { url: string; opts: any }[] = []
function setFetch(handler: (url: string, opts: any) => any) {
  calls = []
  ;(globalThis as any).fetch = (url: string, opts: any) => {
    calls.push({ url, opts })
    return handler(url, opts)
  }
}

test('api GET returns data', async () => {
  setFetch(() => ({ ok: true, status: 200, json: () => Promise.resolve({ count: 1 }) }))
  const data = await api('orders/')
  assert.equal(data.count, 1)
  assert.equal(calls[0].url, '/api/v1/management/orders/')
})

test('api POST attaches CSRF token and JSON body', async () => {
  setCsrfToken('csrf-123')
  setFetch(() => ({ ok: true, status: 200, json: () => Promise.resolve({}) }))
  await api('products/', 'POST', { title: '测试' })
  assert.equal(calls[0].url, '/api/v1/management/products/')
  assert.equal(calls[0].opts.method, 'POST')
  assert.equal(calls[0].opts.headers['X-CSRFToken'], 'csrf-123')
})

test('api rejects with friendly message on 409 VERSION_CONFLICT', async () => {
  setFetch(() => ({ ok: false, status: 409, json: () => Promise.resolve({ error: { code: 'VERSION_CONFLICT', message: '冲突' } }) }))
  await assert.rejects(api('products/1/', 'PATCH', {}), /数据已被修改/)
})

test('api rejects with server message on other errors', async () => {
  setFetch(() => ({ ok: false, status: 400, json: () => Promise.resolve({ error: { message: '参数错误' } }) }))
  await assert.rejects(api('games/', 'POST', {}), /参数错误/)
})
