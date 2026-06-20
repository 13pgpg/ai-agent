<template>
  <div>
    <div class="page-header">
      <h1>📚 题库管理</h1>
      <div class="actions">
        <router-link to="/question-bank/test"><button class="btn-secondary">🔍 检索测试</button></router-link>
        <router-link to="/question-bank/import"><button class="btn-secondary">📥 批量导入</button></router-link>
        <button class="btn-secondary" @click="reindexAll">🔄 全量重建</button>
        <button class="btn-primary" @click="openCreate">+ 新增题目</button>
      </div>
    </div>

    <!-- 统计简览 -->
    <div class="stats-row" v-if="stats">
      <div class="stat-card">
        <div class="stat-num">{{ stats.total }}</div>
        <div class="stat-label">题目总数</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">{{ stats.embedded }}</div>
        <div class="stat-label">已向量化</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">{{ Object.keys(stats.by_category || {}).length }}</div>
        <div class="stat-label">分类数</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">{{ stats.top_used?.[0]?.use_count || 0 }}</div>
        <div class="stat-label">最高使用次数</div>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="card filter-bar">
      <input v-model="filter.search" placeholder="搜索题面/答案..." style="width:240px" @input="debouncedSearch" />
      <select v-model="filter.category" @change="reload">
        <option value="">全部分类</option>
        <option value="technical">技术</option>
        <option value="behavioral">行为</option>
        <option value="system_design">系统设计</option>
        <option value="project">项目</option>
      </select>
      <select v-model="filter.position_tag" @change="reload">
        <option value="">全部岗位</option>
        <option value="python_backend">Python 后端</option>
        <option value="java_backend">Java 后端</option>
        <option value="vue_frontend">Vue 前端</option>
        <option value="react_frontend">React 前端</option>
        <option value="fullstack">全栈</option>
      </select>
      <select v-model="filter.difficulty" @change="reload">
        <option value="">全部难度</option>
        <option value="easy">简单</option>
        <option value="medium">中等</option>
        <option value="hard">困难</option>
      </select>
      <select v-model="filter.is_active" @change="reload">
        <option value="">全部状态</option>
        <option value="true">启用</option>
        <option value="false">禁用</option>
      </select>
    </div>

    <!-- 列表 -->
    <div class="card">
      <table>
        <thead>
          <tr>
            <th style="width:60px">ID</th>
            <th style="width:90px">分类</th>
            <th style="width:120px">岗位</th>
            <th style="width:70px">难度</th>
            <th>题面</th>
            <th style="width:80px">使用次数</th>
            <th style="width:80px">向量化</th>
            <th style="width:70px">状态</th>
            <th style="width:160px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="q in items" :key="q.id">
            <td>{{ q.id }}</td>
            <td>{{ q.category }}</td>
            <td>{{ q.position_tag }}</td>
            <td><span :class="['badge', diffClass(q.difficulty)]">{{ q.difficulty }}</span></td>
            <td class="cell-question">{{ q.question }}</td>
            <td>{{ q.use_count }}</td>
            <td>
              <span v-if="q.has_embedding" class="badge badge-green">✓</span>
              <span v-else class="badge badge-yellow">!</span>
            </td>
            <td>
              <span :class="['badge', q.is_active ? 'badge-green' : 'badge-red']">
                {{ q.is_active ? '启用' : '禁用' }}
              </span>
            </td>
            <td>
              <button class="btn-sm btn-primary" @click="openEdit(q)">编辑</button>
              <button class="btn-sm" :class="q.is_active ? 'btn-danger' : 'btn-primary'" @click="toggle(q)">
                {{ q.is_active ? '禁用' : '启用' }}
              </button>
              <button class="btn-sm btn-danger" @click="del(q)">删除</button>
            </td>
          </tr>
          <tr v-if="!items.length"><td colspan="9" class="empty">暂无题目</td></tr>
        </tbody>
      </table>

      <div class="pagination" v-if="total > perPage">
        <button class="btn-sm" :disabled="page <= 1" @click="page--; reload()">上一页</button>
        <span>{{ page }} / {{ Math.ceil(total / perPage) }} (共 {{ total }} 条)</span>
        <button class="btn-sm" :disabled="page >= Math.ceil(total / perPage)" @click="page++; reload()">下一页</button>
      </div>
    </div>

    <!-- 创建/编辑弹窗 -->
    <div v-if="showModal" class="modal-mask" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h2>{{ editingId ? '编辑题目' : '新增题目' }}</h2>
          <button class="close-btn" @click="closeModal">×</button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-item">
              <label>分类 *</label>
              <select v-model="form.category">
                <option value="technical">技术</option>
                <option value="behavioral">行为</option>
                <option value="system_design">系统设计</option>
                <option value="project">项目</option>
              </select>
            </div>
            <div class="form-item">
              <label>岗位标签 *</label>
              <input v-model="form.position_tag" placeholder="python_backend" />
            </div>
            <div class="form-item">
              <label>难度 *</label>
              <select v-model="form.difficulty">
                <option value="easy">简单</option>
                <option value="medium">中等</option>
                <option value="hard">困难</option>
              </select>
            </div>
          </div>
          <div class="form-item">
            <label>题面 *</label>
            <textarea v-model="form.question" rows="3" placeholder="请输入题目..."></textarea>
          </div>
          <div class="form-item">
            <label>参考答案 / 采分要点</label>
            <textarea v-model="form.reference_answer" rows="6" placeholder="详细的参考答案，用于 AI 评分对照（强烈建议填写）..."></textarea>
          </div>
          <div class="form-item">
            <label>关键采分点（每行一条）</label>
            <textarea v-model="keyPointsText" rows="3" placeholder="GIL 是 CPython 的全局解释器锁&#10;只能有一个线程执行 Python 字节码&#10;..."></textarea>
          </div>
          <div class="form-item">
            <label>标签（逗号分隔）</label>
            <input v-model="tagsText" placeholder="GIL, 并发, Python" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="closeModal">取消</button>
          <button class="btn-primary" @click="save" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { questionBankApi } from '../api'

const items = ref([])
const total = ref(0)
const page = ref(1)
const perPage = 20
const stats = ref(null)
const filter = reactive({ search: '', category: '', position_tag: '', difficulty: '', is_active: '' })

const showModal = ref(false)
const editingId = ref(null)
const saving = ref(false)
const form = reactive({ category: 'technical', position_tag: '', difficulty: 'medium', question: '', reference_answer: '' })
const keyPointsText = ref('')
const tagsText = ref('')

let searchTimer = null
function debouncedSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; reload() }, 300)
}

function diffClass(d) {
  return { easy: 'badge-green', medium: 'badge-blue', hard: 'badge-red' }[d] || 'badge-yellow'
}

async function reload() {
  try {
    const params = { page: page.value, per_page: perPage }
    if (filter.search) params.search = filter.search
    if (filter.category) params.category = filter.category
    if (filter.position_tag) params.position_tag = filter.position_tag
    if (filter.difficulty) params.difficulty = filter.difficulty
    if (filter.is_active !== '') params.is_active = filter.is_active
    const data = await questionBankApi.list(params)
    items.value = data.items
    total.value = data.total
  } catch (e) { alert(e.message) }
}

async function loadStats() {
  try { stats.value = await questionBankApi.stats() } catch (e) { console.warn(e) }
}

function openCreate() {
  editingId.value = null
  form.category = 'technical'; form.position_tag = ''; form.difficulty = 'medium'
  form.question = ''; form.reference_answer = ''
  keyPointsText.value = ''; tagsText.value = ''
  showModal.value = true
}

function openEdit(q) {
  editingId.value = q.id
  form.category = q.category; form.position_tag = q.position_tag; form.difficulty = q.difficulty
  form.question = q.question; form.reference_answer = q.reference_answer || ''
  keyPointsText.value = (q.key_points || []).join('\n')
  tagsText.value = (q.tags || []).join(', ')
  showModal.value = true
}

function closeModal() { showModal.value = false }

async function save() {
  if (!form.question.trim() || !form.position_tag.trim()) {
    alert('题面和岗位标签必填'); return
  }
  saving.value = true
  try {
    const payload = {
      category: form.category,
      position_tag: form.position_tag.trim(),
      difficulty: form.difficulty,
      question: form.question.trim(),
      reference_answer: form.reference_answer.trim() || null,
      key_points: keyPointsText.value.split('\n').map(s => s.trim()).filter(Boolean),
      tags: tagsText.value.split(',').map(s => s.trim()).filter(Boolean)
    }
    if (editingId.value) {
      await questionBankApi.update(editingId.value, payload)
    } else {
      await questionBankApi.create(payload)
    }
    closeModal()
    await reload()
    await loadStats()
  } catch (e) { alert('保存失败: ' + e.message) }
  finally { saving.value = false }
}

async function toggle(q) {
  try {
    await questionBankApi.toggle(q.id, !q.is_active)
    q.is_active = !q.is_active
  } catch (e) { alert(e.message) }
}

async function del(q) {
  if (!confirm(`确认删除题目 #${q.id}？`)) return
  try {
    await questionBankApi.delete(q.id)
    await reload(); await loadStats()
  } catch (e) { alert(e.message) }
}

async function reindexAll() {
  if (!confirm('全量重建会重新计算所有题目的向量，耗时较长（异步），确认？')) return
  try {
    await questionBankApi.reindexAll()
    alert('全量重建任务已提交，请稍后刷新查看')
  } catch (e) { alert(e.message) }
}

onMounted(() => { reload(); loadStats() })
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h1 { font-size: 20px; }
.actions { display: flex; gap: 8px; }
.btn-secondary { background: #e5e7eb; color: #374151; padding: 8px 14px; }
.btn-secondary:hover { background: #d1d5db; }

.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 16px; }
.stat-card { background: white; padding: 16px 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
.stat-num { font-size: 26px; font-weight: 700; color: #4f46e5; }
.stat-label { font-size: 12px; color: #6b7280; margin-top: 4px; }

.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 14px 16px; }

.cell-question { max-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty { text-align: center; color: #9ca3af; padding: 30px 0; }

.pagination { display: flex; align-items: center; justify-content: center; gap: 16px; padding: 16px 0 0; font-size: 13px; color: #6b7280; }

td button + button { margin-left: 4px; }

.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,.45); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: white; border-radius: 10px; width: 720px; max-width: 92vw; max-height: 90vh; display: flex; flex-direction: column; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #f3f4f6; }
.modal-header h2 { font-size: 16px; font-weight: 600; }
.close-btn { background: transparent; font-size: 22px; padding: 0 8px; color: #9ca3af; }
.modal-body { padding: 20px; overflow-y: auto; }
.modal-footer { padding: 14px 20px; border-top: 1px solid #f3f4f6; display: flex; justify-content: flex-end; gap: 8px; }

.form-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 14px; }
.form-item { margin-bottom: 14px; }
.form-item label { display: block; font-size: 13px; color: #374151; margin-bottom: 6px; font-weight: 500; }
.form-item input, .form-item select, .form-item textarea {
  width: 100%; padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; outline: none; resize: vertical;
}
.form-item input:focus, .form-item textarea:focus, .form-item select:focus { border-color: #4f46e5; }
</style>
