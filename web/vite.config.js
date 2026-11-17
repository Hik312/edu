import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发时 dev server 跑 5173，/api 与 /data 转发到 Python 后端（默认 8080）。
// 后端端口换了的同学改这里的 target 即可 —— 前端代码里从不写死后端地址。
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) }
  },
  server: {
    // ⚠️ host 必须写死 IPv4，不能留空（默认 'localhost'）。
    // Node 18+ 解析 'localhost' 时优先取 IPv6，dev server 于是**只**监听
    // [::1]:5173（`netstat -ano | findstr 5173` 可以直接看到，没有 127.0.0.1 那条）。
    // 浏览器或系统代理那一侧只要按 IPv4 去找，HMR 的 WebSocket 就连不上，
    // 控制台刷 `WebSocket connection to 'ws://localhost:5173/?token=...' failed`。
    // 页面本身往往是好的 —— 报错的是热更新通道，别误判成前端崩了。
    host: '127.0.0.1',
    port: 5173,
    // 端口被占时直接失败，不要自动换到 5174/5175。
    // 悄悄换端口的后果：HMR 客户端还拿着 5173 去连，又是满屏 WebSocket 报错。
    strictPort: true,
    // HMR 也显式指到 IPv4：客户端默认会用页面来源拼 ws 地址，
    // 页面若是从 localhost 打开的就又回到 ::1 上了
    hmr: { host: '127.0.0.1', protocol: 'ws' },
    proxy: {
      // 注意 changeOrigin 保持 false：后端 CORS 为了兼容 `*` 没开 credentials，
      // 改了 origin 反而会让某些鉴权头被浏览器提前拦掉
      '/api': { target: 'http://127.0.0.1:8080', changeOrigin: false },
      '/data': { target: 'http://127.0.0.1:8080', changeOrigin: false }
    }
  },
  build: {
    outDir: 'dist',
    // true 会把 public/ 以外的东西清掉。dist 是纯产物目录，清掉是安全的。
    emptyOutDir: true,
    // 单文件超过 500KB 才警告 —— Element Plus 整包引入本来就大，
    // 留着这个阈值免得每次构建都刷一堆黄字，真超了说明该做按需了
    chunkSizeWarningLimit: 1200
  }
})
