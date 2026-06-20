import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue') },
  { path: '/', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { auth: true } },
  { path: '/users', name: 'Users', component: () => import('../views/Users.vue'), meta: { auth: true } },
  { path: '/interviews', name: 'Interviews', component: () => import('../views/Interviews.vue'), meta: { auth: true } },
  { path: '/interviews/:id', name: 'InterviewDetail', component: () => import('../views/InterviewDetail.vue'), meta: { auth: true } },

  // 题库管理
  { path: '/question-bank', name: 'QuestionBank', component: () => import('../views/QuestionBank.vue'), meta: { auth: true } },
  { path: '/question-bank/test', name: 'QuestionBankTest', component: () => import('../views/QuestionBankTest.vue'), meta: { auth: true } },
  { path: '/question-bank/import', name: 'QuestionBankImport', component: () => import('../views/QuestionBankImport.vue'), meta: { auth: true } },

  // 知识文档管理
  { path: '/knowledge', name: 'Knowledge', component: () => import('../views/Knowledge.vue'), meta: { auth: true } },
  { path: '/knowledge/test', name: 'KnowledgeTest', component: () => import('../views/KnowledgeTest.vue'), meta: { auth: true } },
  { path: '/knowledge/:id', name: 'KnowledgeDetail', component: () => import('../views/KnowledgeDetail.vue'), meta: { auth: true } },

  // 岗位模板管理（Agent 数据源）
  { path: '/position-templates', name: 'PositionTemplate', component: () => import('../views/PositionTemplate.vue'), meta: { auth: true } }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  if (to.meta.auth && !authStore.isLoggedIn) next('/login')
  else next()
})

export default router
