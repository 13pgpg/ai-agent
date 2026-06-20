<template>
  <div>
    <div class="page-header">
      <h1>📥 批量导入题目</h1>
      <router-link to="/question-bank"><button class="btn-secondary">← 返回题库</button></router-link>
    </div>

    <div class="card">
      <div class="hint">
        <p><b>导入格式</b>：JSON 数组，每个元素含字段 <code>category / position_tag / difficulty / question / reference_answer / key_points / tags</code></p>
        <p><b>说明</b>：导入后题目会先入库（embedding 为 NULL），再由后台 Celery 异步批量向量化。</p>
      </div>

      <div style="display:flex;gap:12px;margin-bottom:14px">
        <input type="file" accept=".json" @change="loadFile" />
        <button class="btn-secondary" @click="loadSample">加载示例数据</button>
      </div>

      <div class="form-item">
        <label>JSON 内容（可直接粘贴或上传文件后预览）</label>
        <textarea v-model="jsonText" rows="20" spellcheck="false"></textarea>
      </div>

      <div class="actions">
        <button class="btn-primary" @click="submit" :disabled="loading">
          {{ loading ? '导入中...' : `导入 ${parseCount} 条` }}
        </button>
        <button class="btn-secondary" @click="jsonText = ''">清空</button>
      </div>

      <div v-if="result" class="result-box">
        <span class="badge badge-green">导入成功</span>
        <span>共 {{ result.inserted_count }} 条，向量化任务已提交</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { questionBankApi } from '../api'

const jsonText = ref('')
const loading = ref(false)
const result = ref(null)

const parseCount = computed(() => {
  try {
    const arr = JSON.parse(jsonText.value)
    return Array.isArray(arr) ? arr.length : 0
  } catch { return 0 }
})

function loadFile(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = ev => { jsonText.value = ev.target.result }
  reader.readAsText(file)
}

function loadSample() {
  const sample = [
    {
      category: 'technical',
      position_tag: 'python_backend',
      difficulty: 'medium',
      question: '请解释 Python 中的 GIL（全局解释器锁）机制及其影响',
      reference_answer: 'GIL 是 CPython 解释器中的一个互斥锁，保证同一时刻只有一个线程执行 Python 字节码。这导致多线程在 CPU 密集型任务中无法真正并行，但 IO 密集型任务影响较小。绕过 GIL 的方式包括使用 multiprocessing、C 扩展释放 GIL、或改用 Jython/PyPy。',
      key_points: ['GIL 是互斥锁', '同一时刻一个线程执行字节码', 'CPU 密集多进程 IO 密集多线程', '原因是引用计数线程安全'],
      tags: ['GIL', '并发', 'Python']
    },
    {
      category: 'technical',
      position_tag: 'python_backend',
      difficulty: 'hard',
      question: '深入说明 asyncio 的事件循环原理，以及 async/await 是如何工作的',
      reference_answer: 'asyncio 基于事件循环（Event Loop）+ 协程（Coroutine）。async 函数调用返回协程对象，await 处会挂起当前协程并把控制权交回事件循环。事件循环不断从就绪队列取协程恢复执行，遇到 IO 等待时挂起、IO 完成后回到就绪队列。底层用 selector 监听 fd 事件，单线程实现高并发 IO。',
      key_points: ['事件循环驱动', 'await 让出控制权', '协程是可暂停的函数', 'selector 监听 IO 事件', '单线程高并发'],
      tags: ['asyncio', '协程', 'Python']
    }
  ]
  jsonText.value = JSON.stringify(sample, null, 2)
}

async function submit() {
  let items
  try {
    items = JSON.parse(jsonText.value)
  } catch (e) { alert('JSON 格式错误：' + e.message); return }

  if (!Array.isArray(items) || !items.length) { alert('请提供非空的 JSON 数组'); return }

  loading.value = true
  result.value = null
  try {
    result.value = await questionBankApi.batchImport(items)
  } catch (e) { alert('导入失败: ' + e.message) }
  finally { loading.value = false }
}
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h1 { font-size: 20px; }
.btn-secondary { background: #e5e7eb; color: #374151; padding: 8px 14px; }

.hint { background: #eff6ff; color: #1e40af; padding: 12px 16px; border-radius: 6px; margin-bottom: 16px; font-size: 13px; line-height: 1.7; }
.hint code { background: white; padding: 1px 6px; border-radius: 3px; font-family: monospace; }
.hint p { margin: 4px 0; }

.form-item label { display: block; font-size: 13px; color: #374151; margin-bottom: 6px; font-weight: 500; }
.form-item textarea { width: 100%; padding: 10px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; font-family: 'Consolas', monospace; resize: vertical; }
.form-item textarea:focus { border-color: #4f46e5; outline: none; }

.actions { display: flex; gap: 8px; margin-top: 14px; }
.result-box { margin-top: 16px; padding: 12px 16px; background: #f0fdf4; border-radius: 6px; display: flex; align-items: center; gap: 10px; }
</style>
