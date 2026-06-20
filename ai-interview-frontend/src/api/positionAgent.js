import api from './request'

/**
 * 运行岗位匹配 Agent
 * @param {{ resume_id: number, target_direction?: string }} payload
 */
export function matchPositions(payload) {
  // Agent 调用比较慢，超时设为 3 分钟
  return api.post('/position-agent/match', payload, { timeout: 180000 })
}

/**
 * 从 Agent 推荐结果直接启动专项模拟面试
 * @param {{ resume_id: number, position_tag: string, difficulty?: string, total_questions?: number }} payload
 */
export function startInterviewFromAgent(payload) {
  return api.post('/position-agent/start-interview', payload, { timeout: 120000 })
}
