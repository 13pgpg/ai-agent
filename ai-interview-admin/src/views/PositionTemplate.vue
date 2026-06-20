<template>
  <div>
    <div class="page-header">
      <h1>🎯 岗位模板库</h1>
      <button class="btn-primary" @click="openCreate">+ 新增岗位</button>
    </div>

    <div class="card filter-bar">
      <input v-model="filter.search" placeholder="搜索岗位名/标签..." style="width:240px" @input="debouncedSearch" />
      <select v-model="filter.category" @change="reload">
        <option value="">全部分类</option>
        <option value="backend">后端</option>
        <option value="frontend">前端</option>
        <option value="ai">AI</option>
        <option value="mobile">移动端</option>
        <option value="devops">运维</option>
      </select>
      <select v-model="filter.is_active" @change="reload">
        <option value="">全部状态</option>
        <option value="true">启用</option>
        <option value="false">禁用</option>
      </select>
    </div>

    <div class="card">
      <table>
        <thead>
          <tr>
            <th style="width:60px">ID</th>
            <th style="width:140px">标签</th>
            <th>岗位名称</th>
            <th style="width:80px">分类</th>
            <th style="width:80px">层级</th>
            <th style="width:80px">难度</th>
            <th style="width:80px">题数</th>
            <th style="width:60px">排序</th>
            <th style="width:70px">状态</th>
            <th style="width:170px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in items" :key="t.id">
            <td>{{ t.id }}</td>
            <td><code>{{ t.position_tag }}</code></td>
            <td>{{ t.title }}</td>
            <td><span class="badge badge-blue">{{ t.category }}</span></td>
            <td>{{ t.level }}</td>
            <td><span :class="['badge', diffClass(t.recommended_difficulty)]">{{ t.recommended_difficulty }}</span></td>
            <td>{{ t.recommended_question_count }}</td>
            <td>{{ t.sort_order }}</td>
            <td>
              <span :class="['badge', t.is_active ? 'badge-green' : 'badge-red']">
                {{ t.is_active ? '启用' : '禁用' }}
              </span>
            </td>
            <td>
              <button class="btn-sm btn-primary" @click="openEdit(t)">编辑</button>
              <button class="btn-sm" :class="t.is_active ? 'btn-danger' : 'btn-primary'" @click="toggle(t)">
                {{ t.is_active ? '禁用' : '启用' }}
              </button>
              <button class="btn-sm btn-danger" @click="del(t)">删除</button>
            </td>
          </tr>
          <tr v-if="!items.length"><td colspan="10" class="empty">暂无岗位模板</td></tr>
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
          <h2>{{ editingId ? '编辑岗位模板' : '新增岗位模板' }}</h2>
          <button class="close-btn" @click="closeModal">×</button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-item">
              <label>岗位标签 *<span class="hint-text">（英文小写下划线，如 python_backend）</span></label>
              <input v-model="form.position_tag" placeholder="python_backend" :disabled="!!editingId" />
            </div>
            <div class="form-item">
              <label>岗位名称 *</label>
              <input v-model="form.title" placeholder="Python 后端开发工程师" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-item">
              <label>分类 *</label>
              <select v-model="form.category">
                <option value="backend">后端</option>
                <option value="frontend">前端</option>
                <option value="ai">AI</option>
                <option value="mobile">移动端</option>
                <option value="devops">运维</option>
              </select>
            </div>
            <div class="form-item">
              <label>层级</label>
              <select v-model="form.level">
                <option value="intern">实习</option>
                <option value="junior">初级</option>
                <option value="mid">中级</option>
                <option value="senior">高级</option>
              </select>
            </div>
            <div class="form-item">
              <label>推荐难度</label>
              <select v-model="form.recommended_difficulty">
                <option value="easy">简单</option>
                <option value="medium">中等</option>
                <option value="hard">困难</option>
              </select>
            </div>
            <div class="form-item">
              <label>推荐题数</label>
              <input type="number" v-model.number="form.recommended_question_count" min="1" max="30" />
            </div>
            <div class="form-item">
              <label>排序权重</label>
              <input type="number" v-model.number="form.sort_order" min="0" />
            </div>
          </div>

          <div class="form-item">
            <label>核心技能（逗号分隔）<span class="hint-text">必备技术栈</span></label>
            <input v-model="csv.core_skills" placeholder="Python, FastAPI, MySQL, Redis" />
          </div>
          <div class="form-item">
            <label>加分技能（逗号分隔）</label>
            <input v-model="csv.nice_to_have_skills" placeholder="微服务, Docker, Kubernetes" />
          </div>
          <div class="form-item">
            <label>项目关键词（逗号分隔）<span class="hint-text">候选人简历常见的项目方向</span></label>
            <input v-model="csv.project_keywords" placeholder="电商系统, 高并发, 缓存优化" />
          </div>
          <div class="form-item">
            <label>面试重点（逗号分隔）<span class="hint-text">推荐练习的方向</span></label>
            <input v-model="csv.focus_topics" placeholder="并发, Redis, MySQL, FastAPI" />
          </div>
          <div class="form-item">
            <label>题库 RAG 检索关键词（逗号分隔）</label>
            <input v-model="csv.recommended_query_keywords" placeholder="python_backend, Python, asyncio" />
          </div>
          <div class="form-item">
            <label>典型公司（逗号分隔）</label>
            <input v-model="csv.typical_companies" placeholder="互联网公司, 初创团队" />
          </div>
          <div class="form-item">
            <label>JD 摘要 / 岗位说明</label>
            <textarea v-model="form.jd_summary" rows="3" placeholder="负责后端服务开发，要求扎实的 Python 基础..."></textarea>
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
import { positionTemplateApi } from '../api'

const items = ref([])
const total = ref(0)
const page = ref(1)
const perPage = 20
const filter = reactive({ search: '', category: '', is_active: '' })

const showModal = ref(false)
const editingId = ref(null)
const saving = ref(false)
const form = reactive({
  position_tag: '', title: '', category: 'backend', level: 'junior',
  recommended_difficulty: 'medium', recommended_question_count: 8,
  sort_order: 0, jd_summary: ''
})
const csv = reactive({
  core_skills: '', nice_to_have_skills: '', project_keywords: '',
  focus_topics: '', recommended_query_keywords: '', typical_companies: ''
})

let searchTimer = null
function debouncedSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; reload() }, 300)
}

function diffClass(d) {
  return { easy: 'badge-green', medium: 'badge-blue', hard: 'badge-red' }[d] || 'badge-yellow'
}

function csvToArray(s) {
  return (s || '').split(',').map(x => x.trim()).filter(Boolean)
}

function arrayToCsv(arr) {
  return Array.isArray(arr) ? arr.join(', ') : ''
}

async function reload() {
  try {
    const params = { page: page.value, per_page: perPage }
    if (filter.search) params.search = filter.search
    if (filter.category) params.category = filter.category
    if (filter.is_active !== '') params.is_active = filter.is_active
    const data = await positionTemplateApi.list(params)
    items.value = data.items
    total.value = data.total
  } catch (e) { alert(e.message) }
}

function openCreate() {
  editingId.value = null
  form.position_tag = ''; form.title = ''
  form.category = 'backend'; form.level = 'junior'
  form.recommended_difficulty = 'medium'; form.recommended_question_count = 8
  form.sort_order = 0; form.jd_summary = ''
  Object.keys(csv).forEach(k => csv[k] = '')
  showModal.value = true
}

function openEdit(t) {
  editingId.value = t.id
  form.position_tag = t.position_tag; form.title = t.title
  form.category = t.category; form.level = t.level
  form.recommended_difficulty = t.recommended_difficulty
  form.recommended_question_count = t.recommended_question_count
  form.sort_order = t.sort_order; form.jd_summary = t.jd_summary || ''
  csv.core_skills = arrayToCsv(t.core_skills)
  csv.nice_to_have_skills = arrayToCsv(t.nice_to_have_skills)
  csv.project_keywords = arrayToCsv(t.project_keywords)
  csv.focus_topics = arrayToCsv(t.focus_topics)
  csv.recommended_query_keywords = arrayToCsv(t.recommended_query_keywords)
  csv.typical_companies = arrayToCsv(t.typical_companies)
  showModal.value = true
}

function closeModal() { showModal.value = false }

async function save() {
  if (!form.position_tag.trim() || !form.title.trim()) {
    alert('岗位标签和岗位名称必填'); return
  }
  saving.value = true
  try {
    const payload = {
      ...form,
      position_tag: form.position_tag.trim(),
      title: form.title.trim(),
      jd_summary: form.jd_summary.trim() || null,
      core_skills: csvToArray(csv.core_skills),
      nice_to_have_skills: csvToArray(csv.nice_to_have_skills),
      project_keywords: csvToArray(csv.project_keywords),
      focus_topics: csvToArray(csv.focus_topics),
      recommended_query_keywords: csvToArray(csv.recommended_query_keywords),
      typical_companies: csvToArray(csv.typical_companies)
    }
    if (editingId.value) {
      // 更新时不发 position_tag（不允许改）
      delete payload.position_tag
      await positionTemplateApi.update(editingId.value, payload)
    } else {
      await positionTemplateApi.create(payload)
    }
    closeModal()
    await reload()
  } catch (e) { alert('保存失败: ' + e.message) }
  finally { saving.value = false }
}

async function toggle(t) {
  try {
    await positionTemplateApi.toggle(t.id, !t.is_active)
    t.is_active = !t.is_active
  } catch (e) { alert(e.message) }
}

async function del(t) {
  if (!confirm(`确认删除岗位「${t.title}」？`)) return
  try {
    await positionTemplateApi.delete(t.id)
    await reload()
  } catch (e) { alert(e.message) }
}

onMounted(reload)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h1 { font-size: 20px; }
.btn-secondary { background: #e5e7eb; color: #374151; padding: 8px 14px; }

.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; padding: 14px 16px; }

code { background: #f3f4f6; padding: 1px 6px; border-radius: 3px; font-size: 12px; color: #4f46e5; }
.empty { text-align: center; color: #9ca3af; padding: 30px 0; }
.pagination { display: flex; align-items: center; justify-content: center; gap: 16px; padding: 16px 0 0; font-size: 13px; color: #6b7280; }

td button + button { margin-left: 4px; }

.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,.45); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: white; border-radius: 10px; width: 760px; max-width: 92vw; max-height: 90vh; display: flex; flex-direction: column; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #f3f4f6; }
.modal-header h2 { font-size: 16px; font-weight: 600; }
.close-btn { background: transparent; font-size: 22px; padding: 0 8px; color: #9ca3af; }
.modal-body { padding: 20px; overflow-y: auto; }
.modal-footer { padding: 14px 20px; border-top: 1px solid #f3f4f6; display: flex; justify-content: flex-end; gap: 8px; }

.form-row { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; margin-bottom: 14px; }
.form-row:has(> :nth-child(3)) { grid-template-columns: repeat(5, 1fr); }
.form-item { margin-bottom: 14px; }
.form-item label { display: block; font-size: 13px; color: #374151; margin-bottom: 6px; font-weight: 500; }
.hint-text { font-size: 11px; color: #9ca3af; margin-left: 6px; font-weight: 400; }
.form-item input, .form-item select, .form-item textarea {
  width: 100%; padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; outline: none; resize: vertical;
}
.form-item input:disabled { background: #f9fafb; color: #6b7280; }
.form-item input:focus, .form-item textarea:focus, .form-item select:focus { border-color: #4f46e5; }
</style>
