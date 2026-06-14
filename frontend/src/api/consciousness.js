/**
 * 自主意识 API
 */
import http from './http'

// ============ 配置 ============

export const getConsciousnessConfig = () => http.get('/consciousness/config')
export const saveConsciousnessConfig = (data) => http.put('/consciousness/config', data)

// ============ 状态 ============

export const getConsciousnessStatus = () => http.get('/consciousness/status')

// ============ 日志 ============

export const getConsciousnessLogs = (params) => http.get('/consciousness/logs', { params })

// ============ 测试 ============

export const testWeather = () => http.get('/consciousness/test/weather')
export const testHindsight = (query) => http.get('/consciousness/test/hindsight', { params: { query } })
