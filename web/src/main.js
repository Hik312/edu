import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'

// 顺序有讲究：先 Element Plus 自己的样式，再我们的令牌覆盖它。
// 反过来的话 --el-* 会被默认亮色盖住，页面变成一堆白卡片。
//
// 刻意**不引** dark/css-vars.css：全站只有一套牛皮纸配色，没有暗色主题，
// 而那份样式只在 html.dark 下生效 —— 引了就是白背 30KB 永远不用的变量。
import 'element-plus/dist/index.css'
import datav from '@/plugins/datav'
import '@/styles/tokens.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)

// Pinia 必须在 router 之前装：路由守卫里会 useAuthStore()
app.use(createPinia())
app.use(router)
app.use(ElementPlus)
// DataV 放最后：它的边框组件会给 .dv-* 加一层底色，让 Element Plus 先铺底
app.use(datav)

// 骨架屏的移除放在 try/finally 里，不能只是挂在 mount 后面那一行：
//
// #boot 是 index.html 里 **#app 的兄弟节点**（不是子节点，Vue 接管 #app 时
// 不会顺带清掉它），靠 `position:fixed; inset:0` 盖满全屏，只有中间的
// logo 和文字是可见的、没有底色。所以一旦 mount() 抛异常而这一行没执行，
// 它就会**永久叠在所有页面正中间** —— 登录页上凭空多一个居中 logo，
// 而且 `pointer-events:none` 让它连点击都不挡，很容易被当成"布局错乱"。
//
// 放在 finally 里：挂载失败也让骨架消失，露出真正的错误现场。
try {
  app.mount('#app')
} finally {
  document.getElementById('boot')?.remove()
}

// Service Worker 不注册。public/sw.js 现在是「自杀版」：只注销旧 SW、清掉它的缓存
// 并把自己拆掉（legacy.html 时代注册过它，页面本身已删，这份清理还留着兜底）。
// 真要做 PWA 就写一份带构建 hash 的新策略，别复用那一套。
