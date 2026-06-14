import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue')
  },
  {
    path: '/',
    component: () => import('../components/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue')
      },
      {
        path: 'sessions',
        name: 'Sessions',
        component: () => import('../views/Sessions.vue')
      },
      {
        path: 'sessions/:id',
        name: 'SessionDetail',
        component: () => import('../views/SessionDetail.vue')
      },
      {
        path: 'messages',
        name: 'Messages',
        component: () => import('../views/Messages.vue')
      },
      {
        path: 'config',
        name: 'Config',
        component: () => import('../views/Config.vue')
      },
      {
        path: 'consciousness',
        name: 'Consciousness',
        component: () => import('../views/Consciousness.vue')
      },
      {
        path: 'cron-jobs',
        name: 'CronJobs',
        component: () => import('../views/CronJobs.vue')
      },
      {
        path: 'task-logs',
        name: 'TaskLogs',
        component: () => import('../views/TaskLogs.vue')
      },
      {
        path: 'system-logs',
        name: 'SystemLogs',
        component: () => import('../views/SystemLogs.vue')
      },
      {
        path: 'test',
        name: 'Test',
        component: () => import('../views/Test.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫 - 直接读 localStorage，不调用 store
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')

  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/')
  } else {
    next()
  }
})

export default router
