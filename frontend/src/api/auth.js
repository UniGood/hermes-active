import api from './index'

export const authApi = {
  // 用户登录
  login(username, password) {
    return api.post('/auth/login', { username, password })
  },

  // 获取当前用户信息
  getMe() {
    return api.get('/auth/me')
  },

  // 修改密码
  changePassword(oldPassword, newPassword) {
    return api.post('/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword
    })
  },

  // 刷新 token
  refreshToken() {
    return api.post('/auth/refresh')
  }
}
