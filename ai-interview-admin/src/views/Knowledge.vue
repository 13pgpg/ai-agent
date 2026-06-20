<template>
  <div>
    <div class="page-header">
      <h1>📄 知识文档管理</h1>
      <div class="actions">
        <router-link to="/knowledge/test"><button class="btn-secondary">🔍 检索测试</button></router-link>
        <button class="btn-primary" @click="openUpload">+ 上传文档</button>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="card filter-bar">
      <input v-model="filter.search" placeholder="搜索标题..." style="width:240px" @input="debouncedSearch" />
      <select v-model="filter.category" @change="reload">
        <option value="">全部分类</option>
        <option value="python">Python</option>
        <option value="java">Java</option>
        <option value="vue">Vue</option>
        <option value="system_design">系统设计</option>
        <option value="behavioral">行为面试</option>
      </select>
      <select v-model="filter.status" @change="reload">
        <option value="">全部状态</option>
        <option value="pending">待索引</option>
        <option value="indexing">索引中</option>
        <option value="indexed">已索引</option>
        <option value="failed">失败</option>
      </select>
      <button class="btn-sm btn-secondary" @click="reload">🔄 刷新</button>
    </div>

    <!-- 列表 -->
    <div class="card">
      <table>
        <thead>
          <tr>
            <th style="width:60px">ID</th>
            <th>标题</th>
            <th style="width:80px">类型</th>
            <th style="width:90px">大小</th>
            <th style="width:100px">分类</th>
            <th style="width:80px">Chunks</th>
            <th style="width:100px">状态</th>
            <th style="width:160px">上传时间</th>
            <th style="width:230px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in items" :key="d.id">
            <td>{{ d.id }}</td>
            <td class="cell-title">{{ d.title }}</td>
            <td><span class="badge badge-blue">{{ d.file_type }}</span></td>
            <td>{{ formatSize(d.file_size) }}</td>
            <td>{{ d.category || '-' }}</td>
            <td>{{ d.chunk_count }}</td>
            <td><span :class="['badge', statusClass(d.status)]">{{ statusLabel(d.status) }}</span></td>
            <td>{{ formatDate(d.created_at) }}</td>
            <td>
              <router-link :to="`/knowledge/${d.id}`"><button class="btn-sm btn-primary">详情</button></router-link>
              <button class="btn-sm" :class="d.is_active ? 'btn-danger' : 'btn-primary'" @click="toggle(d)">
                {{ d.is_active ? '禁用' : '启用' }}
              </button>
              <button class="btn-sm btn-secondary" @click="reindex(d)">重建</button>
              <button class="btn-sm btn-danger" @click="del(d)">删除</button>
            </td>
          </tr>
          <tr v-if="!items.length"><td colspan="9" class="empty">暂无文档</td></tr>
        </tbody>
      </table>

      <div class="pagination" v-if="total > perPage">
        <button class="btn-sm" :disabled="page <= 1" @click="page--; reload()">上一页</button>
        <span>{{ page }} / {{ Math.ceil(total / perPage) }} (共 {{ total }} 条)</span>
        <button class="btn-sm" :disabled="page >= Math.ceil(total / perPage)" @click="page++; reload()">下一页</button>
      </div>
    </div>

    <!-- 上传弹窗 -->
    <div v-if="showModal" class="modal-mask" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h2>上传文档</h2>
          <button class="close-btn" @click="closeModal">×</button>
        </div>
        <div class="modal-body">
          <div class="hint">支持 PDF / Markdown / TXT 格式，上传后后台异步切分 + 向量化。</div>

          <div class="form-item">
            <label>选择文件 *</label>
            <input type="file" accept=".pdf,.md,.markdown,.txt" @change="onFileChange" />
            <div v-if="file" class="file-info">
              已选：{{ file.name }} ({{ formatSize(file.size) }})
            </div>
          </div>
          <div class="form-item">
            <label>标题（不填则用文件名）</label>
            <input v-model="form.title" placeholder="例：Python 后端面试宝典" />
          </div>
          <div class="form-item">
            <label>分类</label>
            <select v-model="form.category">
              <option value="">未分类</option>
              <option value="python">Python</option>
              <option value="java">Java</option>
              <option value="vue">Vue</option>
              <option value="system_design">系统设计</option>
              <option value="behavioral">行为面试</option>
            </select>
          </div>
          <div class="form-item">
            <label>简介</label>
            <textarea v-model="form.description" rows="3" placeholder="文档简介..."></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="closeModal">取消</button>
          <button class="btn-primary" @click="upload" :disabled="uploading || !file">
            {{ uploading ? '上传中...' : '上传并索引' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { knowledgeApi } from '../api'

const items = ref([])
const total = ref(0)
const page = ref(1)
const perPage = 20
const filter = reactive({ search: '', category: '', status: '' })

const showModal = ref(false)
const file = ref(null)
const form = reactive({ title: '', category: '', description: '' })
const uploading = ref(false)

let searchTimer = null
let pollTimer = null

function debouncedSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; reload() }, 300)
}

function formatDate(s) { return s ? new Date(s).toLocaleString('zh-CN') : '' }
function formatSize(b) {
  if (!b) return '-'
  if (b < 1024) return b + ' B'
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB'
  return (b / 1024 / 1024).toFixed(1) + ' MB'
}
function statusLabel(s) {
  return { pending: '待索引', indexing: '索引中', indexed: '已索引', failed: '失败' }[s] || s
}
function statusClass(s) {
  return { pending: 'badge-yellow', indexing: 'badge-blue', indexed: 'badge-green', failed: 'badge-red' }[s] || ''
}

async function reload() {
  try {
    const params = { page: page.value, per_page: perPage }
    if (filter.search) params.search = filter.search
    if (filter.category) params.category = filter.category
    if (filter.status) params.status = filter.status
    const data = await knowledgeApi.list(params)
    items.value = data.items
    total.value = data.total
  } catch (e) { alert(e.message) }
}

function openUpload() {
  file.value = null
  form.title = ''; form.category = ''; form.description = ''
  showModal.value = true
}

function closeModal() { showModal.value = false }

function onFileChange(e) { file.value = e.target.files?.[0] || null }

async function upload() {
  if (!file.value) { alert('请选择文件'); return }
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    if (form.title) fd.append('title', form.title)
    if (form.category) fd.append('category', form.category)
    if (form.description) fd.append('description', form.description)
    await knowledgeApi.uploadDocument(fd)
    closeModal()
    await reload()
  } catch (e) { alert('上传失败: ' + e.message) }
  finally { uploading.value = false }
}

async function toggle(d) {
  try {
    await knowledgeApi.toggle(d.id, !d.is_active)
    d.is_active = !d.is_active
  } catch (e) { alert(e.message) }
}

async function reindex(d) {
  if (!confirm(`重建文档 #${d.id} 的索引？会先删除旧 chunks 再重新切分。`)) return
  try {
    await knowledgeApi.reindex(d.id)
    alert('重建任务已启动')
    await reload()
  } catch (e) { alert(e.message) }
}

async function del(d) {
  if (!confirm(`确认删除文档「${d.title}」？所有 chunks 一并删除。`)) return
  try {
    await knowledgeApi.delete(d.id)
    await reload()
  } catch (e) { alert(e.message) }
}

onMounted(() => {
  reload()
  // 每 5 秒轮询一次，让索引中的文档状态自动更新
  pollTimer = setInterval(() => {
    if (items.value.some(d => ['pending', 'indexing'].includes(d.status))) reload()
  }, 5000)
})
onUnmounted(() => clearInterval(pollTimer))
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h1 { font-size: 20px; }
.actions { display: flex; gap: 8px; }
.btn-secondary { background: #e5e7eb; color: #374151; padding: 8px 14px; }

.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 14px 16px; align-items: center; }

.cell-title { max-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty { text-align: center; color: #9ca3af; padding: 30px 0; }

.pagination { display: flex; align-items: center; justify-content: center; gap: 16px; padding: 16px 0 0; font-size: 13px; color: #6b7280; }

td button + button { margin-left: 4px; }

.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,.45); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: white; border-radius: 10px; width: 560px; max-width: 92vw; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #f3f4f6; }
.modal-header h2 { font-size: 16px; font-weight: 600; }
.close-btn { background: transparent; font-size: 22px; padding: 0 8px; color: #9ca3af; }
.modal-body { padding: 20px; }
.modal-footer { padding: 14px 20px; border-top: 1px solid #f3f4f6; display: flex; justify-content: flex-end; gap: 8px; }

.hint { background: #eff6ff; color: #1e40af; padding: 10px 14px; border-radius: 6px; margin-bottom: 16px; font-size: 13px; }
.form-item { margin-bottom: 14px; }
.form-item label { display: block; font-size: 13px; color: #374151; margin-bottom: 6px; font-weight: 500; }
.form-item input, .form-item select, .form-item textarea {
  width: 100%; padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; outline: none; resize: vertical;
}
.file-info { margin-top: 6px; font-size: 12px; color: #6b7280; }
</style>
