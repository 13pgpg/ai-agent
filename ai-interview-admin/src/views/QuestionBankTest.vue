<template>
  <div>
    <div class="page-header">
      <h1>🔍 题库检索测试</h1>
      <router-link to="/question-bank"><button class="btn-secondary">← 返回题库</button></router-link>
    </div>

    <div class="card">
      <div class="hint">
        测试输入「岗位 + 简历技能关键词」（模拟真实出题时的检索 query），看能召回什么题。
      </div>

      <div class="form-grid">
        <div class="form-item span-2">
          <label>查询文本 *</label>
          <input v-model="query" placeholder="例：python_backend 协程 异步 redis" @keyup.enter="search" />
        </div>
        <div class="form-item">
          <label>返回数量 K</label>
          <input type="number" v-model.number="k" min="1" max="50" />
        </div>
        <div class="form-item">
          <label>最低相似度</label>
          <input type="number" v-model.number="minScore" min="0" max="1" step="0.05" />
        </div>
        <div class="form-item">
          <label>岗位筛选（可选）</label>
          <input v-model="positionTag" placeholder="python_backend" />
        </div>
        <div class="form-item">
          <label>难度（可选）</label>
          <select v-model="difficulty">
            <option value="">全部</option>
            <option value="easy">简单</option>
            <option value="medium">中等</option>
            <option value="hard">困难</option>
          </select>
        </div>
      </div>

      <div class="actions">
        <button class="btn-primary" @click="search" :disabled="loading">{{ loading ? '检索中...' : '🔍 开始检索' }}</button>
      </div>
    </div>

    <div v-if="result" class="card result-card">
      <div class="result-header">
        <span>查询：<b>{{ result.query }}</b></span>
        <span class="badge badge-blue">召回 {{ result.count }} 题</span>
      </div>

      <div v-if="!result.items.length" class="empty">没有匹配的题目，建议降低 min_score 阈值或先往题库里加题</div>

      <div v-for="(item, idx) in result.items" :key="item.id" class="result-item">
        <div class="ri-header">
          <span class="ri-rank">#{{ idx + 1 }}</span>
          <span class="ri-id">题目 ID: {{ item.id }}</span>
          <span class="badge badge-blue">{{ item.category }}</span>
          <span class="badge badge-yellow">{{ item.position_tag }}</span>
          <span :class="['badge', diffClass(item.difficulty)]">{{ item.difficulty }}</span>
          <span class="ri-sim">相似度 {{ (item.similarity * 100).toFixed(1) }}%</span>
        </div>
        <div class="ri-q">{{ item.question }}</div>
        <details v-if="item.reference_answer">
          <summary>参考答案</summary>
          <div class="ri-ref">{{ item.reference_answer }}</div>
        </details>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { questionBankApi } from '../api'

const query = ref('python_backend 协程 异步')
const k = ref(20)
const minScore = ref(0.7)
const positionTag = ref('')
const difficulty = ref('')
const loading = ref(false)
const result = ref(null)

function diffClass(d) {
  return { easy: 'badge-green', medium: 'badge-blue', hard: 'badge-red' }[d] || 'badge-yellow'
}

async function search() {
  if (!query.value.trim()) { alert('请输入查询文本'); return }
  loading.value = true
  try {
    const payload = {
      query: query.value.trim(),
      k: k.value,
      min_score: minScore.value
    }
    if (positionTag.value.trim()) payload.position_tag = positionTag.value.trim()
    if (difficulty.value) payload.difficulty = difficulty.value
    result.value = await questionBankApi.testRetrieve(payload)
  } catch (e) { alert(e.message) }
  finally { loading.value = false }
}
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h1 { font-size: 20px; }
.btn-secondary { background: #e5e7eb; color: #374151; padding: 8px 14px; }

.hint { background: #eff6ff; color: #1e40af; padding: 10px 14px; border-radius: 6px; margin-bottom: 16px; font-size: 13px; }
.form-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 16px; }
.form-item.span-2 { grid-column: span 2; }
.form-item label { display: block; font-size: 13px; color: #374151; margin-bottom: 6px; font-weight: 500; }
.form-item input, .form-item select { width: 100%; }
.actions { display: flex; gap: 8px; }

.result-card { margin-top: 20px; }
.result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; padding-bottom: 12px; border-bottom: 1px solid #f3f4f6; }
.empty { text-align: center; color: #9ca3af; padding: 30px 0; }

.result-item { padding: 14px 0; border-bottom: 1px solid #f3f4f6; }
.result-item:last-child { border-bottom: none; }
.ri-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; font-size: 13px; }
.ri-rank { font-weight: 700; color: #4f46e5; }
.ri-id { color: #6b7280; }
.ri-sim { margin-left: auto; color: #059669; font-weight: 600; }
.ri-q { font-size: 14px; color: #111827; line-height: 1.6; margin-bottom: 6px; }
details summary { cursor: pointer; color: #4f46e5; font-size: 13px; }
.ri-ref { margin-top: 8px; padding: 10px 12px; background: #f9fafb; border-radius: 6px; font-size: 13px; color: #4b5563; line-height: 1.6; white-space: pre-wrap; }
</style>
