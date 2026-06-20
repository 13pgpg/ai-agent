<template>
  <div class="container">
    <div class="page-header">
      <h1>🎯 岗位智能匹配</h1>
      <p class="subtitle">AI Agent 会分析你的简历，推荐最适合的岗位方向，并给出具体的能力差距和学习建议</p>
    </div>

    <!-- 第一步：选择简历 + 期望方向 -->
    <div v-if="!result" class="card form-card">
      <h2>开始匹配</h2>

      <div class="form-item">
        <label>选择简历 *</label>
        <div v-if="loadingResumes" class="hint">加载简历中...</div>
        <div v-else-if="!resumes.length" class="empty-resume">
          还没有简历，
          <router-link to="/resume/upload" class="link">先去上传一份简历</router-link>
        </div>
        <div v-else class="resume-grid">
          <div
            v-for="r in resumes"
            :key="getResumeId(r)"
            :class="['resume-card', { active: selectedResumeId === getResumeId(r), disabled: r.status !== 'completed' }]"
            @click="r.status === 'completed' && (selectedResumeId = getResumeId(r))"
          >
            <div class="resume-name">📄 {{ r.file_name || `简历 #${getResumeId(r)}` }}</div>
            <div class="resume-meta">
              目标：{{ r.target_position || '未填写' }}
            </div>
            <span :class="['status-tag', r.status]">
              {{ statusLabel(r.status) }}
            </span>
          </div>
        </div>
      </div>

      <div class="form-item">
        <label>期望求职方向（可选）<span class="hint-text">如 "Python 后端" / "AI 应用开发"</span></label>
        <input v-model="targetDirection" placeholder="不填也可以，AI 会自己分析" />
      </div>

      <div class="form-actions">
        <button
          class="btn-primary btn-large"
          :disabled="!selectedResumeId || running"
          @click="runMatch"
        >
          {{ running ? '🤖 Agent 思考中（可能需要 30-60 秒）...' : '🚀 开始匹配' }}
        </button>
      </div>

      <!-- Agent 运行过程的可视化 -->
      <div v-if="running" class="agent-progress">
        <div class="progress-line">
          <div class="dot dot-active"></div>
          <span>读取简历</span>
        </div>
        <div class="progress-line">
          <div class="dot dot-active"></div>
          <span>分析候选人画像</span>
        </div>
        <div class="progress-line">
          <div class="dot dot-active"></div>
          <span>从岗位库匹配</span>
        </div>
        <div class="progress-line">
          <div class="dot dot-active"></div>
          <span>生成推荐结果</span>
        </div>
      </div>
    </div>

    <!-- 第二步：展示结果 -->
    <div v-if="result" class="result-area">
      <div class="result-header">
        <h2>✨ 匹配结果</h2>
        <button class="btn-secondary" @click="reset">重新匹配</button>
      </div>

      <!-- 候选人画像 -->
      <div class="card profile-card" v-if="result.candidate_profile">
        <h3>👤 我的画像</h3>
        <div class="profile-grid">
          <div class="profile-item">
            <label>经验层级</label>
            <span class="level-badge">{{ levelLabel(result.candidate_profile.experience_level) }}</span>
          </div>
          <div class="profile-item">
            <label>核心技术栈</label>
            <div class="tag-list">
              <span v-for="s in result.candidate_profile.primary_stack" :key="s" class="tag tag-primary">{{ s }}</span>
            </div>
          </div>
          <div class="profile-item" v-if="result.candidate_profile.secondary_stack?.length">
            <label>次要技术栈</label>
            <div class="tag-list">
              <span v-for="s in result.candidate_profile.secondary_stack" :key="s" class="tag tag-gray">{{ s }}</span>
            </div>
          </div>
          <div class="profile-item" v-if="result.candidate_profile.project_directions?.length">
            <label>项目方向</label>
            <div class="tag-list">
              <span v-for="s in result.candidate_profile.project_directions" :key="s" class="tag tag-blue">{{ s }}</span>
            </div>
          </div>
          <div class="profile-item">
            <label>✓ 强项</label>
            <ul class="bullet-list">
              <li v-for="s in result.candidate_profile.strong_points" :key="s">{{ s }}</li>
            </ul>
          </div>
          <div class="profile-item">
            <label>✗ 短板</label>
            <ul class="bullet-list">
              <li v-for="s in result.candidate_profile.weak_points" :key="s">{{ s }}</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- 推荐岗位 -->
      <div class="card position-card" v-if="result.recommended_positions?.length">
        <h3>🎯 推荐岗位（Top {{ result.recommended_positions.length }}）</h3>
        <div class="position-list">
          <div
            v-for="(pos, idx) in result.recommended_positions"
            :key="pos.position_tag"
            class="position-item"
          >
            <div class="position-header">
              <span class="rank">#{{ idx + 1 }}</span>
              <span class="position-title">{{ pos.title }}</span>
              <span class="match-score">匹配度 {{ Math.round(pos.match_score * 100) }}%</span>
            </div>
            <div class="match-bar">
              <div class="match-bar-fill" :style="{ width: pos.match_score * 100 + '%' }"></div>
            </div>

            <div v-if="pos.reasons?.length" class="position-section">
              <label>✓ 推荐理由</label>
              <ul>
                <li v-for="r in pos.reasons" :key="r">{{ r }}</li>
              </ul>
            </div>

            <div v-if="pos.missing_skills?.length" class="position-section">
              <label>⚠ 待补充能力</label>
              <div class="tag-list">
                <span v-for="s in pos.missing_skills" :key="s" class="tag tag-orange">{{ s }}</span>
              </div>
            </div>

            <div class="position-actions">
              <button
                class="btn-primary"
                :disabled="startingInterview === pos.position_tag"
                @click="startInterview(pos.position_tag)"
              >
                {{ startingInterview === pos.position_tag ? '启动中...' : '🎤 开始模拟面试' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Top 1 岗位面试方向 -->
      <div class="card focus-card" v-if="result.top_position_focus">
        <h3>📚 重点练习方向</h3>
        <p class="focus-position">{{ result.top_position_focus.title || result.top_position_focus.position_tag }}</p>
        <div v-if="result.top_position_focus.focus_topics?.length" class="tag-list">
          <span v-for="t in result.top_position_focus.focus_topics" :key="t" class="tag tag-blue">{{ t }}</span>
        </div>
        <div class="focus-meta">
          推荐难度：<b>{{ difficultyLabel(result.top_position_focus.recommended_difficulty) }}</b>
          ｜ 推荐题数：<b>{{ result.top_position_focus.recommended_question_count }}</b>
        </div>
      </div>

      <!-- 下一步建议 -->
      <div class="card next-card" v-if="result.next_actions?.length">
        <h3>🚀 下一步建议</h3>
        <ol class="next-list">
          <li v-for="(act, i) in result.next_actions" :key="i">{{ act }}</li>
        </ol>
      </div>

      <!-- Agent 调用过程（可折叠）-->
      <details class="card debug-card" v-if="intermediateSteps?.length">
        <summary>🔧 Agent 调用过程（{{ intermediateSteps.length }} 步）</summary>
        <div v-for="(step, i) in intermediateSteps" :key="i" class="debug-step">
          <div class="debug-step-header">Step {{ i + 1 }}: <code>{{ step.tool }}</code></div>
          <div class="debug-step-output">{{ step.output_preview }}</div>
        </div>
      </details>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getResumes } from '../api/resume'
import { matchPositions, startInterviewFromAgent } from '../api/positionAgent'

const router = useRouter()

const resumes = ref([])
const loadingResumes = ref(true)
const selectedResumeId = ref(null)
const targetDirection = ref('')

const running = ref(false)
const result = ref(null)
const intermediateSteps = ref([])
const startingInterview = ref(null)

function getResumeId(resume) {
  return resume?.resume_id ?? resume?.id ?? null
}

function statusLabel(s) {
  return { pending: '待解析', parsing: '解析中', completed: '已完成', failed: '解析失败' }[s] || s
}
function levelLabel(l) {
  return { campus: '在校 / 应届', junior: '初级（1-3 年）', mid: '中级（3-5 年）', senior: '高级（5 年+）' }[l] || l
}
function difficultyLabel(d) {
  return { easy: '简单', medium: '中等', hard: '困难' }[d] || d
}

onMounted(async () => {
  try {
    const data = await getResumes()
    resumes.value = data.items || data || []
    // 默认选第一份已完成的简历
    const first = resumes.value.find(r => r.status === 'completed')
    if (first) selectedResumeId.value = getResumeId(first)
  } catch (e) {
    console.error(e)
  } finally {
    loadingResumes.value = false
  }
})

async function runMatch() {
  if (!selectedResumeId.value) {
    alert('请先选择一份已完成解析的简历')
    return
  }
  running.value = true
  result.value = null
  intermediateSteps.value = []
  try {
    const data = await matchPositions({
      resume_id: selectedResumeId.value,
      target_direction: targetDirection.value.trim() || undefined,
    })
    result.value = data.result
    intermediateSteps.value = data.intermediate_steps || []
  } catch (e) {
    alert('Agent 运行失败：' + e.message)
  } finally {
    running.value = false
  }
}

function reset() {
  result.value = null
  intermediateSteps.value = []
}

async function startInterview(positionTag) {
  startingInterview.value = positionTag
  try {
    const data = await startInterviewFromAgent({
      resume_id: selectedResumeId.value,
      position_tag: positionTag,
    })
    if (data.interview_id) {
      router.push(`/interview/${data.interview_id}`)
    } else {
      alert('启动失败：' + JSON.stringify(data))
    }
  } catch (e) {
    alert('启动面试失败：' + e.message)
  } finally {
    startingInterview.value = null
  }
}
</script>

<style scoped>
.container { max-width: 960px; margin: 0 auto; padding: 24px; }

.page-header { margin-bottom: 20px; }
.page-header h1 { font-size: 24px; margin-bottom: 8px; }
.subtitle { color: #6b7280; font-size: 14px; }

.card { background: white; padding: 24px; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 16px; }
.form-card h2 { font-size: 18px; margin-bottom: 18px; }

.form-item { margin-bottom: 18px; }
.form-item label { display: block; font-size: 13px; color: #374151; margin-bottom: 8px; font-weight: 500; }
.form-item input { width: 100%; padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; }
.form-item input:focus { border-color: #4f46e5; outline: none; }

.hint { font-size: 13px; color: #9ca3af; }
.hint-text { font-size: 11px; color: #9ca3af; margin-left: 6px; font-weight: 400; }

.empty-resume { padding: 16px; background: #f9fafb; border-radius: 8px; color: #6b7280; font-size: 14px; }
.link { color: #4f46e5; font-weight: 500; }

.resume-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
.resume-card { padding: 14px; border: 2px solid #e5e7eb; border-radius: 8px; cursor: pointer; transition: all 0.2s; position: relative; }
.resume-card:hover:not(.disabled) { border-color: #818cf8; }
.resume-card.active { border-color: #4f46e5; background: #eef2ff; }
.resume-card.disabled { opacity: 0.5; cursor: not-allowed; }
.resume-name { font-weight: 600; font-size: 14px; margin-bottom: 6px; }
.resume-meta { font-size: 12px; color: #6b7280; }
.status-tag { position: absolute; top: 8px; right: 8px; font-size: 11px; padding: 2px 8px; border-radius: 10px; }
.status-tag.completed { background: #d1fae5; color: #065f46; }
.status-tag.parsing { background: #fef3c7; color: #92400e; }
.status-tag.failed { background: #fee2e2; color: #991b1b; }
.status-tag.pending { background: #e0e7ff; color: #3730a3; }

.form-actions { display: flex; justify-content: center; margin-top: 20px; }
.btn-primary { background: #4f46e5; color: white; border: none; border-radius: 8px; padding: 10px 24px; font-size: 14px; cursor: pointer; transition: background 0.2s; }
.btn-primary:hover:not(:disabled) { background: #4338ca; }
.btn-primary:disabled { background: #a5b4fc; cursor: not-allowed; }
.btn-large { padding: 14px 36px; font-size: 16px; font-weight: 500; }
.btn-secondary { background: #e5e7eb; color: #374151; border: none; border-radius: 8px; padding: 8px 16px; font-size: 13px; cursor: pointer; }
.btn-secondary:hover { background: #d1d5db; }

.agent-progress { margin-top: 24px; padding: 20px; background: #f9fafb; border-radius: 8px; }
.progress-line { display: flex; align-items: center; gap: 10px; padding: 6px 0; font-size: 14px; color: #6b7280; }
.dot { width: 10px; height: 10px; border-radius: 50%; background: #d1d5db; }
.dot-active { background: #4f46e5; animation: pulse 1.4s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

.result-area { animation: fadeIn 0.4s; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.result-header h2 { font-size: 22px; }

.profile-card h3, .position-card h3, .focus-card h3, .next-card h3 { font-size: 18px; margin-bottom: 16px; }
.profile-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.profile-item { }
.profile-item > label { display: block; font-size: 12px; color: #6b7280; margin-bottom: 6px; font-weight: 500; }
.profile-item span, .profile-item li { font-size: 14px; color: #111827; }
.level-badge { background: #eef2ff; color: #4f46e5; padding: 4px 12px; border-radius: 12px; font-weight: 500; font-size: 13px; }

.tag-list { display: flex; gap: 6px; flex-wrap: wrap; }
.tag { padding: 4px 10px; border-radius: 12px; font-size: 12px; }
.tag-primary { background: #eef2ff; color: #4f46e5; }
.tag-gray { background: #f3f4f6; color: #4b5563; }
.tag-blue { background: #dbeafe; color: #1e40af; }
.tag-orange { background: #fed7aa; color: #9a3412; }

.bullet-list { padding-left: 18px; line-height: 1.8; color: #374151; }
.bullet-list li { font-size: 13px; }

.position-list { display: flex; flex-direction: column; gap: 16px; }
.position-item { padding: 18px; border: 1px solid #e5e7eb; border-radius: 8px; }
.position-header { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.rank { background: #4f46e5; color: white; padding: 2px 10px; border-radius: 10px; font-size: 12px; font-weight: 700; }
.position-title { font-size: 16px; font-weight: 600; flex: 1; }
.match-score { color: #059669; font-weight: 600; font-size: 14px; }
.match-bar { background: #f3f4f6; height: 6px; border-radius: 3px; margin-bottom: 14px; overflow: hidden; }
.match-bar-fill { background: linear-gradient(90deg, #4f46e5, #818cf8); height: 100%; transition: width 0.6s; }
.position-section { margin-bottom: 12px; }
.position-section label { display: block; font-size: 12px; color: #6b7280; margin-bottom: 6px; font-weight: 500; }
.position-section ul { padding-left: 18px; line-height: 1.7; }
.position-section li { font-size: 13px; color: #374151; }
.position-actions { display: flex; justify-content: flex-end; margin-top: 10px; }

.focus-position { font-size: 15px; font-weight: 500; margin-bottom: 10px; color: #4f46e5; }
.focus-meta { margin-top: 12px; font-size: 13px; color: #6b7280; }

.next-list { padding-left: 22px; line-height: 1.9; }
.next-list li { font-size: 14px; color: #111827; padding: 4px 0; }

.debug-card { background: #f9fafb; }
.debug-card summary { font-size: 13px; color: #6b7280; cursor: pointer; }
.debug-step { margin-top: 12px; padding: 10px 12px; background: white; border-radius: 6px; }
.debug-step-header { font-size: 12px; color: #4f46e5; margin-bottom: 6px; }
.debug-step-output { font-size: 12px; color: #6b7280; font-family: 'Consolas', monospace; word-break: break-all; }
code { background: #eef2ff; padding: 1px 6px; border-radius: 3px; color: #4f46e5; font-size: 12px; }
</style>
