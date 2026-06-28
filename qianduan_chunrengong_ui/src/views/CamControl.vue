<template>
  <div class="cam-control-page">
    <h1>🎮 实时操控 — 键盘方向键控制 AGV</h1>

    <!-- Toast -->
    <div :class="['toast', toastClass, { show: toastShow }]">{{ toastMsg }}</div>

    <div class="main">
      <!-- ===== 左侧：视频区 ===== -->
      <div class="video-side">
        <div class="cam-btns">
          <button
            v-for="(cam, i) in cameras"
            :key="cam.id || i"
            :class="['cam-btn', { active: activeCam === i }]"
            @click="switchCam(i)"
          >{{ cam.name }}</button>
        </div>
        <div class="video-panel">
          <video ref="videoRef" autoplay muted playsinline style="display:none"></video>
          <div class="ph" v-if="videoPlaceholder" :style="{ position: 'absolute' }">
            <span class="icon">{{ videoIcon }}</span>{{ videoMsg }}
          </div>
          <div class="video-overlay">{{ videoOverlay }}</div>
        </div>
      </div>

      <!-- ===== 右侧：操控区 ===== -->
      <div class="ctrl-side">
        <!-- 键盘操控卡片 -->
        <div class="card">
          <h3>⌨ 键盘操控</h3>
          <div class="dir-display">
            <div class="dir-row">
              <div
                :class="['dir-key', { active: currentDir === 'forward' }]"
                style="font-size:28px;cursor:pointer"
                @mousedown="sendCmd('forward')"
                @mouseup="sendCmd('stop')"
                @mouseleave="sendCmd('stop')"
              >&#9650;</div>
            </div>
            <div class="dir-row">
              <div
                :class="['dir-key', 'stop-key', { active: currentDir === 'stop' }]"
                style="cursor:pointer"
                @click="sendCmd('stop')"
              >■</div>
            </div>
            <div class="dir-row">
              <div
                :class="['dir-key', { active: currentDir === 'backward' }]"
                style="font-size:28px;cursor:pointer"
                @mousedown="sendCmd('backward')"
                @mouseup="sendCmd('stop')"
                @mouseleave="sendCmd('stop')"
              >&#9660;</div>
            </div>
          </div>
          <div class="key-hint">
            <b>↑</b> 前进 &nbsp; <b>↓</b> 后退 &nbsp; <b>空格</b> 停止 &nbsp; 松开自动停止
            <br><span style="color:#d2991d">⚠ AGV 马达有方向反转保护，换向前需先停稳 ~0.5s</span>
          </div>
        </div>

        <!-- AGV 状态卡片 -->
        <div class="card">
          <h3>🚛 AGV 状态</h3>
          <div class="status-row"><span class="lbl">运行状态</span>
            <span v-if="agvState.isRunning" class="val green">● 行驶中</span>
            <span v-else class="val red">● 停止</span>
          </div>
          <div class="status-row"><span class="lbl">行驶距离</span>
            <span class="val">{{ (agvState.currentPosition || 0).toFixed(2) }} m</span>
          </div>
          <div class="status-row"><span class="lbl">系统时间</span>
            <span class="val">{{ agvState.sysTime || '--' }}</span>
          </div>
          <div class="status-row"><span class="lbl">网络延迟</span>
            <span class="val" :class="latencyMs ? (latencyMs < 200 ? 'green' : 'yellow') : ''">
              {{ latencyMs ? latencyMs + 'ms' : '--' }}
            </span>
          </div>
          <div class="status-row"><span class="lbl">最后指令</span>
            <span class="val" :class="currentDir === 'stop' ? 'red' : 'green'">
              {{ currentDir === 'forward' ? '前进 ▶' : currentDir === 'backward' ? '后退 ◀' : '停止 ■' }}
            </span>
          </div>
        </div>

        <!-- 清空日志 -->
        <div class="card" style="flex-shrink:0;padding:4px 12px;text-align:right">
          <button @click="logs = []" style="padding:3px 10px;border:1px solid #30363d;border-radius:4px;background:transparent;color:#8b949e;cursor:pointer;font-size:10px">🗑 清空日志</button>
        </div>

        <!-- 日志面板 -->
        <div id="log" ref="logRef">
          <div v-for="(entry, i) in logs" :key="i" :class="entry.cls">
            <span class="ts">{{ entry.ts }}</span> {{ entry.msg }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'

// ===== 配置 =====
const API = '/prod-api'
const EASY = '/easy-api'
const AUTH = 'Basic YWRtaW4xMjM6QWRtaW5AMTIz'

// ===== 响应式状态 =====
const cameras = ref([])
const activeCam = ref(0)
const agvState = reactive({ isRunning: false, currentPosition: 0, sysTime: '' })
const currentDir = ref('stop')
const keysDown = reactive({})
const logs = ref([])
const latencyMs = ref(0)

// Toast
const toastShow = ref(false)
const toastMsg = ref('')
const toastClass = ref('')
let toastTimer = null

// Video
const videoRef = ref(null)
const logRef = ref(null)
const videoPlaceholder = ref(true)
const videoIcon = ref('🎥')
const videoMsg = ref('连接中...')
const videoOverlay = ref('--')

// 非响应式变量
let player = null
let heartbeatTimer = null
let stopDebounce = 0

// ===== 日志 =====
function log(msg, cls) {
  const now = new Date()
  const ts = ('0' + now.getHours()).slice(-2) + ':' +
             ('0' + now.getMinutes()).slice(-2) + ':' +
             ('0' + now.getSeconds()).slice(-2)
  logs.value.push({ ts, msg, cls: cls || '' })
  nextTick(() => {
    if (logRef.value) logRef.value.scrollTop = logRef.value.scrollHeight
  })
}

// ===== Toast =====
function showToast(msg, cls) {
  toastMsg.value = msg
  toastClass.value = cls || ''
  toastShow.value = true
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastShow.value = false }, 600)
}

// ===== AGV 指令 =====
const labels = { forward: '前进 ▶', backward: '后退 ◀', stop: '停止 ■' }

async function sendCmd(action) {
  log('sendCmd: ' + action + ' (current=' + currentDir.value + ')', 'info')
  if (action === currentDir.value) {
    log('  → blocked (same as current)', 'info')
    return
  }

  // 方向反转防抖：停止后需等 300ms 才能切换方向
  if (action !== 'stop' && stopDebounce > 0) {
    const elapsed = Date.now() - stopDebounce
    if (elapsed < 300) {
      log('  → debounce ' + elapsed + 'ms since stop, delaying...', 'info')
      setTimeout(() => sendCmd(action), 300 - elapsed)
      return
    }
  }

  if (action === 'stop') {
    stopDebounce = Date.now()
  } else {
    stopDebounce = 0
  }

  currentDir.value = action

  const endpoint = action === 'forward' ? '/agv/movement/forward'
    : action === 'backward' ? '/agv/movement/backward'
    : '/agv/movement/stop'

  if (action !== 'stop') showToast(action === 'forward' ? '▲ 前进' : '▼ 后退', action === 'backward' ? 'back' : 'fwd')

  try {
    const t0 = Date.now()
    const res = await fetch(API + endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' } })
    const data = await res.json()
    latencyMs.value = Date.now() - t0

    if (data.code === 200 || data.code === 0) {
      log(labels[action] + ' (' + latencyMs.value + 'ms)', 'ok')
    } else {
      log(labels[action] + ' 失败: ' + (data.msg || 'HTTP ' + res.status), 'err')
    }
  } catch (e) {
    log('指令失败: ' + e.message, 'err')
  }
}

// ===== 键盘事件 =====
function onKeyDown(e) {
  log('keydown: key="' + e.key + '" code="' + e.code + '" repeat=' + e.repeat, 'info')
  if (e.key === 'ArrowUp' || e.key === 'w' || e.key === 'W') {
    e.preventDefault()
    if (e.repeat) { log('  → ignored (repeat)', 'info'); return }
    log('  → SEND forward', 'ok')
    sendCmd('forward')
  } else if (e.key === 'ArrowDown' || e.key === 's' || e.key === 'S') {
    e.preventDefault()
    if (e.repeat) { log('  → ignored (repeat)', 'info'); return }
    log('  → SEND backward', 'ok')
    sendCmd('backward')
  } else if (e.key === ' ') {
    e.preventDefault()
    log('  → SEND stop (space)', 'ok')
    showToast('■ 停止', 'stop')
    sendCmd('stop')
  }
}

function onKeyUp(e) {
  log('keyup:   key="' + e.key + '" code="' + e.code + '"', 'info')
  if (e.key === 'ArrowUp' || e.key === 'w' || e.key === 'W') {
    if (!keysDown['ArrowDown'] && !keysDown['s'] && !keysDown['S']) {
      log('  → SEND stop (↑ released, no ↓ pressed)', 'ok')
      sendCmd('stop')
    } else {
      log('  → skip stop (↓ still pressed)', 'info')
    }
  } else if (e.key === 'ArrowDown' || e.key === 's' || e.key === 'S') {
    if (!keysDown['ArrowUp'] && !keysDown['w'] && !keysDown['W']) {
      log('  → SEND stop (↓ released, no ↑ pressed)', 'ok')
      sendCmd('stop')
    } else {
      log('  → skip stop (↑ still pressed)', 'info')
    }
  }
}

function trackKeyDown(e) { keysDown[e.key] = true }
function trackKeyUp(e) { keysDown[e.key] = false }

// ===== 心跳轮询 =====
async function pollHeartbeat() {
  try {
    const res = await fetch(API + '/agv/movement/heartbeat')
    const data = await res.json()
    if (data.code === 200 || data.code === 0) {
      const s = data.data || {}
      Object.assign(agvState, s)
    }
  } catch (e) { /* silent */ }
}

// ===== 视频播放 =====
function connectVideo() {
  // 销毁旧实例
  if (player) { try { player.destroy() } catch (e) { /* */ } player = null }

  const video = videoRef.value
  if (!video) return
  video.style.display = 'none'
  videoPlaceholder.value = true
  videoIcon.value = '🎥'
  videoMsg.value = '连接中...'
  videoOverlay.value = '--'

  if (!cameras.value.length) {
    videoIcon.value = '⚠️'
    videoMsg.value = '无摄像头数据'
    return
  }

  const cam = cameras.value[activeCam.value]
  const url = '/flv/cam' + (activeCam.value + 1)
  const t0 = Date.now()

  if (typeof mpegts === 'undefined' || !mpegts.isSupported()) {
    videoIcon.value = '❌'
    videoMsg.value = 'MSE不支持'
    return
  }

  try {
    player = mpegts.createPlayer({
      type: 'flv', isLive: true, url: url,
      hasAudio: false, hasVideo: true,
      enableStashBuffer: false
    })

    player.on(mpegts.Events.MEDIA_INFO, () => {
      const el = ((Date.now() - t0) / 1000).toFixed(1)
      log('✅ 画面已连接 (' + el + 's) ' + cam.name, 'ok')
      video.style.display = ''
      videoPlaceholder.value = false
    })

    player.on(mpegts.Events.STATISTICS_INFO, (s) => {
      const el = ((Date.now() - t0) / 1000).toFixed(0)
      const spd = (s.speed || 0) >= 1000 ? ((s.speed || 0) / 1000).toFixed(1) + 'MB/s' : (s.speed || 0).toFixed(0) + 'KB/s'
      videoOverlay.value = spd + ' | ' + (video.videoWidth || 0) + 'x' + (video.videoHeight || 0) + ' | ' + el + 's'
    })

    player.on(mpegts.Events.ERROR, (type, info) => {
      log('❌ 视频错误: ' + type, 'err')
    })

    player.attachMediaElement(video)
    player.load()
  } catch (e) {
    log('❌ 视频异常: ' + e.message, 'err')
    videoIcon.value = '❌'
    videoMsg.value = e.message
  }
}

function switchCam(i) {
  activeCam.value = i
  connectVideo()
}

// ===== 初始化 =====
onMounted(async () => {
  log('=== 实时操控测试页 ===', 'info')
  log('键盘: ↑/W=前进 ↓/S=后退 松开=停止', 'info')
  log('⚠ AGV 马达方向反转保护: 换向前需停稳 ~0.5s，否则反向指令可能被硬件忽略', 'err')

  // 加载摄像头列表
  try {
    const r = await fetch(EASY + '/devices?page=1&size=999', {
      headers: { 'Authorization': AUTH }
    })
    const d = await r.json()
    cameras.value = d.items || []
  } catch (e) {
    log('easy-api 失败: ' + e.message, 'err')
  }

  // 兜底摄像头
  if (!cameras.value.length) {
    cameras.value = [
      { id: 'PbemokuspQHD5', name: '摄像头1' },
      { id: 'Psh0GyTpkiSdC', name: '摄像头2' },
      { id: 'Pk8FmQHNeOqSx', name: '摄像头3' },
      { id: 'PaKHUtvPpcrZq', name: '摄像头4' }
    ]
  }
  log('摄像头: ' + cameras.value.length + ' 个', 'info')

  // 启动视频
  connectVideo()

  // 启动心跳
  pollHeartbeat()
  heartbeatTimer = setInterval(pollHeartbeat, 2000)

  // 键盘事件
  document.addEventListener('keydown', onKeyDown)
  document.addEventListener('keyup', onKeyUp)
  window.addEventListener('keydown', trackKeyDown)
  window.addEventListener('keyup', trackKeyUp)

  log('就绪，按 ↑ 前进', 'ok')
})

// ===== 清理 =====
onUnmounted(() => {
  if (currentDir.value !== 'stop') sendCmd('stop')
  if (player) { try { player.destroy() } catch (e) { /* */ } }
  if (heartbeatTimer) clearInterval(heartbeatTimer)
  document.removeEventListener('keydown', onKeyDown)
  document.removeEventListener('keyup', onKeyUp)
  window.removeEventListener('keydown', trackKeyDown)
  window.removeEventListener('keyup', trackKeyUp)
})
</script>

<style scoped>
.cam-control-page {
  background: #0d1117;
  color: #e0e0e0;
  font-family: 'Microsoft YaHei', Arial, sans-serif;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
h1 {
  text-align: center;
  font-size: 16px;
  padding: 6px 0;
  color: #fff;
  flex-shrink: 0;
  line-height: 1;
}
.main {
  flex: 1;
  display: flex;
  gap: 8px;
  padding: 0 8px 8px;
  overflow: hidden;
  min-height: 0;
}

/* ===== 视频区 ===== */
.video-side {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  min-height: 0;
  height: 100%;
}
.video-panel {
  flex: 1;
  background: #000;
  border: 2px solid #21262d;
  border-radius: 8px;
  position: relative;
  overflow: hidden;
  min-height: 0;
  max-height: 100%;
}
.video-panel video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  max-width: 100%;
  max-height: 100%;
}
.video-panel .ph {
  text-align: center;
  color: #555;
  font-size: 14px;
}
.video-panel .ph .icon {
  font-size: 48px;
  display: block;
  margin-bottom: 8px;
}
.video-overlay {
  position: absolute;
  top: 8px;
  left: 8px;
  background: rgba(0,0,0,.7);
  color: #58a6ff;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-family: Consolas, monospace;
  pointer-events: none;
}

/* ===== 操控面板 ===== */
.ctrl-side {
  width: 300px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
  min-height: 0;
  overflow: hidden;
}
.card {
  background: #161b22;
  border: 1px solid #21262d;
  border-radius: 8px;
  padding: 8px 12px;
  flex-shrink: 0;
}
.card h3 {
  font-size: 12px;
  color: #58a6ff;
  margin-bottom: 6px;
}

/* ===== 方向键 ===== */
.dir-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 4px 0;
}
.dir-row {
  display: flex;
  gap: 4px;
}
.dir-key {
  width: 48px;
  height: 48px;
  border: 2px solid #30363d;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  transition: all .15s;
  background: #0d1117;
  color: #484f58;
  user-select: none;
}
.dir-key.active {
  background: #238636;
  border-color: #2ea043;
  color: #fff;
  box-shadow: 0 0 16px rgba(35,134,54,.4);
}
.dir-key.stop-key {
  width: 80px;
  color: #f85149;
  border-color: #30363d;
}
.dir-key.stop-key.active {
  background: #da3633;
  border-color: #f85149;
  color: #fff;
  box-shadow: 0 0 16px rgba(248,81,73,.4);
}
.key-hint {
  font-size: 9px;
  color: #484f58;
  text-align: center;
  margin-top: 4px;
}

/* ===== 状态行 ===== */
.status-row {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  padding: 2px 0;
  border-bottom: 1px solid rgba(255,255,255,.03);
}
.status-row .lbl { color: #8b949e; }
.status-row .val { color: #c9d1d9; }
.status-row .val.green { color: #3fb950; }
.status-row .val.red { color: #f85149; }
.status-row .val.yellow { color: #d2991d; }

/* ===== 摄像头切换 ===== */
.cam-btns {
  display: flex;
  gap: 4px;
}
.cam-btn {
  padding: 4px 10px;
  border: 1px solid #30363d;
  border-radius: 4px;
  background: transparent;
  color: #8b949e;
  cursor: pointer;
  font-size: 11px;
  transition: all .2s;
}
.cam-btn.active {
  background: #1f6feb;
  border-color: #1f6feb;
  color: #fff;
}

/* ===== 日志 ===== */
#log {
  flex: 1;
  background: #161b22;
  border: 1px solid #21262d;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 10px;
  line-height: 1.6;
  font-family: Consolas, monospace;
  overflow-y: auto;
  color: #8b949e;
  min-height: 0;
}
#log .ts { color: #484f58; }
#log .ok { color: #3fb950; }
#log .err { color: #f85149; }
#log .info { color: #58a6ff; }

/* ===== Toast ===== */
.toast {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%,-50%);
  background: rgba(0,0,0,.9);
  color: #fff;
  padding: 16px 32px;
  border-radius: 8px;
  font-size: 24px;
  pointer-events: none;
  z-index: 100;
  opacity: 0;
  transition: opacity .15s;
}
.toast.show { opacity: 1; }
.toast.fwd { color: #3fb950; }
.toast.stop { color: #f85149; }
.toast.back { color: #d2991d; }
</style>
