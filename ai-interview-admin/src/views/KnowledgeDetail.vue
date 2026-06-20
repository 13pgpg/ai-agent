<template>
  <div>
    <div class="page-header">
      <h1>📄 文档详情</h1>
      <router-link to="/knowledge"><button class="btn-secondary">← 返回列表</button></router-link>
    </div>

    <div v-if="doc" class="card">
      <div class="info-grid">
        <div><label>ID</label><span>{{ doc.id }}</span></div>
        <div><label>标题</label><span>{{ doc.title }}</span></div>
        <div><label>文件名</label><span>{{ doc.file_name }}</span></div>
        <div><label>类型</label><span class="badge badge-blue">{{ doc.file_type }}</span></div>
        <div><label>大小</label><span>{{ formatSize(doc.file_size) }}</span></div>
        <div><label>分类</label><span>{{ doc.category || '-' }}</span></div>
        <div><label>状态</label><span :class="['badge', statusClass(doc.status)]">{{ statusLabel(doc.status) }}</span></div>
        <div><label>Chunks</label><span>{{ doc.chunk_count }}</span></div>
        <div><label>启用</label><span :class="['badge', doc.is_active ? 'badge-green' : 'badge-red']">{{ doc.is_active ? '是' : '否' }}</span></div>
        <div><label>上传时间</label><span>{{ formatDate(doc.created_at) }}</span></div>
        <div v-if="doc.description" class="full-width"><label>简介</label><span>{{ doc.description }}</span></div>
        <div v-if="doc.error_message" class="full-width"><label>错误信息</label><span class="err">{{ doc.error_message }}</span></div>
      </div>
    </div>

    <div class="card chunks-card">
      <h2>切片预览（共 {{ doc?.chunk_count || 0 }} 个）</h2>

      <div v-if="!chunks.length" class="empty">
        {{ doc?.status === 'indexed' ? '没有切片数据' : '文档尚未完成索引，请等待索引完成后查看' }}
      </div>

      <div v-for="c in chunks" :key="c.id" class="chunk">
        <div class="chunk-header">
          <span class="badge badge-blue">#{{ c.chunk_index }}</span>
          <span class="ck-id">Chunk ID: {{ c.id }}</span>
          <span v-if="c.has_embedding" class="badge badge-green">已向量化</span>
          <span v-else class="badge badge-yellow">未向量化</span>
        </div>
        <div class="chunk-content">{{ c.content }}</div>
      </div>

      <div class="pagination" v-if="chunkPage > 1 || chunks.length === perPage">
        <button class="btn-sm" :disabled="chunkPage <= 1" @click="chunkPage--; loadChunks()">上一页</button>
        <span>第 {{ chunkPage }} 页</span>
        <button class="btn-sm" :disabled="chunks.length < perPage" @click="chunkPage++; loadChunks()">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { knowledgeApi } from '../api'

const route = useRoute()
const doc = ref(null)
const chunks = ref([])
const chunkPage = ref(1)
const perPage = 10

function formatDate(s) { return s ? new Date(s).toLocaleString('zh-CN') : '' }
function formatSize(b) {
  if (!b) return '-'
  if (b < 1024) return b + ' B'
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB'
  return (b / 1024 / 1024).toFixed(1) + ' MB'
}
function statusLabel(s) { return { pending: '待索引', indexing: '索引中', indexed: '已索引', failed: '失败' }[s] || s }
function statusClass(s) { return { pending: 'badge-yellow', indexing: 'badge-blue', indexed: 'badge-green', failed: 'badge-red' }[s] || '' }

async function loadDoc() {
  try { doc.value = await knowledgeApi.detail(route.params.id) } catch (e) { alert(e.message) }
}

async function loadChunks() {
  try {
    const data = await knowledgeApi.chunks(route.params.id, { page: chunkPage.value, per_page: perPage })
    chunks.value = data.items
  } catch (e) { alert(e.message) }
}

onMounted(() => { loadDoc(); loadChunks() })
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h1 { font-size: 20px; }
.btn-secondary { background: #e5e7eb; color: #374151; padding: 8px 14px; }

.info-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px 24px; }
.info-grid > div { display: flex; flex-direction: column; gap: 4px; }
.info-grid label { font-size: 12px; color: #6b7280; }
.info-grid span { font-size: 14px; color: #111827; }
.full-width { grid-column: 1 / -1; }
.err { color: #b91c1c; }

.chunks-card { margin-top: 16px; }
.chunks-card h2 { font-size: 16px; margin-bottom: 14px; padding-bottom: 12px; border-bottom: 1px solid #f3f4f6; }
.empty { text-align: center; color: #9ca3af; padding: 30px 0; }

.chunk { padding: 14px 0; border-bottom: 1px solid #f3f4f6; }
.chunk-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; font-size: 13px; color: #6b7280; }
.chunk-content { padding: 12px 14px; background: #f9fafb; border-radius: 6px; font-size: 13px; color: #374151; line-height: 1.7; white-space: pre-wrap; }

.pagination { display: flex; align-items: center; justify-content: center; gap: 16px; padding: 16px 0 0; font-size: 13px; color: #6b7280; }
</style>
