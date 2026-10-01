/* 路由表。按业务域分组，和 api/ 下的文件一一对应。
 *
 * meta 约定：
 *   public  免登录
 *   blank   用空白布局（登录页不带侧栏）
 *   title   写进 document.title 和顶栏
 *   domain  所属业务域
 *   icon    侧栏图标名（AppLayout 的 ICON 表里的 key）
 *   ready   业务页面是否已开发完。false 的走占位组件，
 *           做完一个改一个 —— 这样侧栏能点、能看进度，不会看起来像坏了
 *
 * ⚠️ 曾经有一个 `theme: 'light' | 'dark'` 字段，用来让数据页走深色。
 * 那条路已经删掉：全站一套牛皮纸卷宗配色，页面之间不再换色。
 * 别再往 meta 里加 theme —— 现在没有任何地方读它，加了是死配置。
 */
import { createRouter, createWebHistory } from 'vue-router'
import { setupGuards } from './guards'

// 占位页目前在用的只有 404（最后那条兜底路由）。views/_placeholder/ 里还有一个
// PlaceholderView：新增「页面已规划、内容还没搬」的路由时再把它取回来用，
// 别现在就 import —— 没用到的懒加载会被 lint 判为未使用变量。
const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { public: true, blank: true, title: '登录' }
  },
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    children: [
      { path: '', redirect: '/dashboard' },

      // —— 总览：看数的，夜航深色 ——
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
        meta: {
          title: '学习驾驶舱',
          domain: 'dashboard',
          icon: 'dashboard',
          ready: true
        }
      },

      // —— 学习 ——
      {
        path: 'path',
        name: 'path',
        component: () => import('@/views/path/PathView.vue'),
        meta: {
          title: '今日路径',
          domain: 'learning',
          icon: 'path',
          ready: true,
          note: '按掌握度 + 前置依赖 + SM-2 排期排出的今日顺序'
        }
      },
      {
        path: 'review',
        name: 'review',
        component: () => import('@/views/review/ReviewView.vue'),
        meta: { title: '复习队列', domain: 'learning', icon: 'review', ready: true }
      },

      // —— 内容 ——
      {
        path: 'cards',
        name: 'cards',
        component: () => import('@/views/cards/CardsView.vue'),
        meta: { title: '卡片', domain: 'content', icon: 'cards', ready: true }
      },
      {
        path: 'docs',
        name: 'docs',
        component: () => import('@/views/docs/DocsView.vue'),
        meta: {
          title: '文档与精读',
          domain: 'content',
          icon: 'docs',
          ready: true,
          note: '文档导入 → 自动分章 → 逐章 AI 精读'
        }
      },

      // —— 工具 ——
      {
        path: 'graph',
        name: 'graph',
        component: () => import('@/views/graph/GraphView.vue'),
        meta: {
          title: '知识图谱',
          domain: 'graph',
          icon: 'graph',
          ready: true,
          note: '按 topicPath + related 关系铺开的知识网'
        }
      },
      {
        path: 'notes',
        name: 'notes',
        component: () => import('@/views/notes/NotesView.vue'),
        meta: { title: '笔记', domain: 'notes', icon: 'notes', ready: true }
      },
      {
        path: 'generate',
        name: 'generate',
        component: () => import('@/views/generate/GenerateView.vue'),
        meta: {
          title: '生成',
          domain: 'ai',
          icon: 'generate',
          ready: true,
          note: '粘贴文本 → 切分草稿 → 补齐 → 发布成卡'
        }
      },
      {
        path: 'ask',
        name: 'ask',
        component: () => import('@/views/ask/AskView.vue'),
        meta: {
          title: 'AI 问答',
          domain: 'ai',
          icon: 'ask',
          ready: true,
          note: '基于卡片知识库的问答：知识库问答（带引用）/ Agent（流式）'
        }
      },

      // —— 管理：自用后台（用户管理 / 运行状态）——
      {
        path: 'admin/users',
        name: 'admin-users',
        component: () => import('@/views/admin/UsersView.vue'),
        meta: {
          title: '用户管理',
          domain: 'admin',
          icon: 'users',
          ready: true,
          note: '账号列表与角色；增删改要等 per-user 数据隔离做完'
        }
      },
      {
        path: 'admin/system',
        name: 'admin-system',
        component: () => import('@/views/admin/SystemView.vue'),
        meta: {
          title: '运行状态',
          domain: 'admin',
          icon: 'server',
          ready: true,
          note: '存储后端、AI 可用性、数据规模'
        }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'notfound',
    component: () => import('@/views/_placeholder/NotFoundView.vue'),
    meta: { public: true, blank: true, title: '页面不存在' }
  }
]

const router = createRouter({
  // history 模式：URL 干净，但**后端必须做 SPA fallback**
  // （任何非 /api、非静态文件的路径都要返回 index.html，否则刷新就 404）
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

setupGuards(router)

/**
 * 导航完成后只做一件事：改标题。
 *
 * ⚠️ 这里曾经负责按路由切主题（写 html 的 data-theme 和 EP 的 dark class）。
 * 全站统一牛皮纸以后**不要把这个逻辑加回来** —— 变量全在 :root 上，
 * 没有任何 [data-theme] 分支，写了也不会有页面对应上；
 * 而 html.dark 一旦被加上，Element Plus 的暗色变量会立刻生效，
 * section 里就会出现「纸色页面挂着深色输入框」这种半生效状态。
 */
router.afterEach(to => {
  document.title = to.meta.title ? to.meta.title + ' · 智径 EduPath' : '智径 EduPath'
})

export default router
