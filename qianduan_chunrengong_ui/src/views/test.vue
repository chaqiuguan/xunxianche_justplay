<template>
  <div style="padding:20px;background:#0d1117;color:#e0e0e0;min-height:100vh;font-family:Consolas,monospace">
    <h2 style="color:#58a6ff">上传接口测试</h2>

    <div style="margin:16px 0">
      <label style="color:#8b949e">Task ID: </label>
      <input v-model="taskId" placeholder="输入任务ID" style="padding:4px 8px;width:120px">
      <button @click="runTests" style="margin-left:8px;padding:4px 12px;cursor:pointer">测试</button>
    </div>

    <div v-for="r in results" :key="r.label" style="margin:12px 0;padding:14px;background:#161b22;border-radius:8px">
      <h3 :style="{color: r.ok ? '#3fb950' : '#f85149'}">{{ r.label }}</h3>
      <pre style="font-size:11px;color:#8b949e;white-space:pre-wrap;word-break:break-all">{{ r.detail }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const taskId = ref('')
const results = ref([])

async function runTests() {
  results.value = []
  const id = taskId.value.trim()
  if (!id) return

  // 1. 查询任务当前状态
  let taskRes, statusBefore
  try {
    taskRes = await fetch('/prod-api/agv/task/' + id).then(r => r.json())
    statusBefore = taskRes.data?.taskStatus || taskRes.taskStatus || '?'
    results.value.push({ label: '1. 任务当前状态', ok: true, detail: JSON.stringify({ status: statusBefore, id: id }, null, 2) })
  } catch (e) {
    results.value.push({ label: '1. 任务当前状态', ok: false, detail: '请求失败: ' + e.message })
    return
  }

  // 2. 查询待上传数据
  try {
    const res = await fetch('/prod-api/agv/task/preupload/' + id).then(r => r.json())
    results.value.push({ label: '2. 待上传数据', ok: true, detail: JSON.stringify(res, null, 2) })
  } catch (e) {
    results.value.push({ label: '2. 待上传数据', ok: false, detail: '请求失败: ' + e.message })
  }

  // 3. 执行上传
  let uploadRes
  try {
    uploadRes = await fetch('/prod-api/agv/task/upload/' + id, { method: 'POST' }).then(r => r.json())
    results.value.push({ label: '3. 上传结果', ok: uploadRes.code === 200, detail: JSON.stringify(uploadRes, null, 2) })
  } catch (e) {
    results.value.push({ label: '3. 上传结果', ok: false, detail: '请求失败: ' + e.message })
    return
  }

  // 4. 再次查询任务状态
  try {
    const res = await fetch('/prod-api/agv/task/' + id).then(r => r.json())
    const statusAfter = res.data?.taskStatus || res.taskStatus || '?'
    const changed = statusBefore !== statusAfter
    results.value.push({
      label: '4. 上传后任务状态',
      ok: changed,
      detail: `${statusBefore} → ${statusAfter}` + (changed ? ' (已改变)' : ' (未改变)'),
    })
  } catch (e) {
    results.value.push({ label: '4. 上传后任务状态', ok: false, detail: '请求失败: ' + e.message })
  }
}
</script>
