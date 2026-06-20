<template>
  <div>
    <div class="page-header">
      <h1>🔍 文档检索测试</h1>
      <router-link to="/knowledge"><button class="btn-secondary">← 返回文档列表</button></router-link>
    </div>

    <div class="card">
      <div class="hint">
        测试输入查询文本，看从知识文档库里能召回什么 chunks。这个检索用于答案评分增强、用户答疑场景。
      </div>

      <div class="form-grid">
        <div class="form-item span-2">
          <label>查询文本 *</label>
          <input v-model="query" placeholder="例：Python GIL 影响" @keyup.enter="search" />
        </div>
        <div class="form-item">
          <label>返回数量 K</label>
          <input type="number" v-model.number="k" min="1" max="20" />
        </div>
        <div class="form-item">
          <label>最低相似度</label>
          <input type="number" v-model.number="minScore" min="0" max="1" step="0.05" />
        </div>
        <div class="form-item">
          <label>分类筛选（可选）</label>
          <input v-model="category" placeholder="python" />
        </div>
      </div>

      <div class="actions">
        <button class="btn-primary" @click="search" :disabled="loading">{{ loading ? '检索中...' : '🔍 开始检索' }}</button>
      </div>
    </div>

    <div v-if="result" class="card result-card">
      <div class="result-header">
        <span>查询：<b>{{ result.query }}</b></span>
        <span class="badge badge-blue">召回 {{ result.count }} 个 chunk</span>
      </div>

      <div v-if="!result.items.length" class="empty">没有匹配的内容，建议降低 min_score 或先上传更多文档</div>

      <div v-for="(item, idx) in result.items" :key="item.id" class="result-item">
        <div class="ri-header">
          <span class="ri-rank">#{{ idx + 1 }}</span>
          <span class="ri-id">Chunk ID: {{ item.id }}</span>
          <span class="ri-doc">来自文档: {{ item.document_id }}</span>
          <span class="ri-sim">相似度 {{ (item.similarity * 100).toFixed(1) }}%</span>
        </div>
        <div class="ri-content">{{ item.content }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { knowledgeApi } from '../api'

const query = ref('Python 协程 异步原理')
const k = ref(4)
const minScore = ref(0.3)
const category = ref('')
const loading = ref(false)
const result = ref(null)

async function search() {
  if (!query.value.trim()) { alert('请输入查询文本'); return }
  loading.value = true
  try {
    const payload = { query: query.value.trim(), k: k.value, min_score: minScore.value }
    if (category.value.trim()) payload.category = category.value.trim()
    result.value = await knowledgeApi.testRetrieve(payload)
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
.form-item input { width: 100%; }
.actions { display: flex; gap: 8px; }

.result-card { margin-top: 20px; }
.result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; padding-bottom: 12px; border-bottom: 1px solid #f3f4f6; }
.empty { text-align: center; color: #9ca3af; padding: 30px 0; }

.result-item { padding: 14px 0; border-bottom: 1px solid #f3f4f6; }
.result-item:last-child { border-bottom: none; }
.ri-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; font-size: 13px; color: #6b7280; }
.ri-rank { font-weight: 700; color: #4f46e5; }
.ri-sim { margin-left: auto; color: #059669; font-weight: 600; }
.ri-content { padding: 12px 14px; background: #f9fafb; border-radius: 6px; font-size: 13px; color: #374151; line-height: 1.7; white-space: pre-wrap; }
</style>
