/* ⚠️ 这个文件现在是「自杀版」，它不再缓存任何东西，唯一职责是把自己拆掉。
 *
 * ---------------------------------------------------------------------------
 * 为什么（2026-09-26）
 *
 * 它原本是旧单文件版（legacy.html）的离线缓存。legacy.html 里有一行
 * `navigator.serviceWorker.register('sw.js')`，而 sw.js 就在站点根上，
 * **scope 因此是整个域** —— 只要用户点过一次「旧版入口」，这个 SW 就会
 * 接管之后所有页面的请求，包括 Vue 版的 /login、/dashboard。
 *
 * 而旧策略里有个一直没人发现的漏洞：
 *
 *     const isDoc = url.pathname === '/' || /\.(html|js|json)$/.test(url.pathname)
 *
 * `.vue` 和 `.css` **不在**这个正则里，于是它们落进了「其他静态资源：缓存优先」
 * 那一支。构建产物没问题（文件名带 hash，改了名字就变），但 **dev server 下
 * /src/**.vue 的 URL 是不带 hash 的** —— 一旦被缓存，改完代码刷新拿到的
 * 还是旧模块。
 *
 * 表现是最难查的那种：**同一页刷新几次，布局在两个样子之间跳**。
 * 一次命中缓存（旧布局）、一次走网络（新布局），两个都是"稳定"的，
 * 所以看起来像随机、像布局算法不稳定，唯独不像缓存问题。
 *
 * ---------------------------------------------------------------------------
 * 现在它做三件事，然后永久消失：
 *   1. **不再注册 fetch 监听器** —— 没有 fetch handler 的 SW 不会拦截任何请求，
 *      这一步就足以立刻止血（浏览器会直接走网络）。
 *   2. activate 时删掉所有 Cache Storage（旧版本号里的那些陈年页面）。
 *   3. 把自己 unregister 掉，并让受它控制的页面重新加载一次，落回干净状态。
 *
 * 另外 index.html 的 <head> 里还有一道主动清理（不信赖「浏览器什么时候才来
 * 检查更新」—— 那个最长能拖 24 小时）。两道互为兜底。
 *
 * 要恢复离线能力的话：**别复活这份文件**。新前端要 PWA 就重新写一份带
 * 构建 hash 的 SW 策略（见 docs/技术架构.md 第 5 节），别复用 legacy 那套。
 */

self.addEventListener('install', function () {
  self.skipWaiting();
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys()
      .then(function (keys) {
        return Promise.all(keys.map(function (k) { return caches.delete(k); }));
      })
      .then(function () { return self.registration.unregister(); })
      .then(function () { return self.clients.matchAll({ type: 'window' }); })
      .then(function (cs) {
        // 受控页面重新加载一次，让它们落到「没有 SW」的状态。
        // 只导航 http(s) 页面，别去碰 chrome-extension 之类。
        cs.forEach(function (c) {
          if (/^https?:/.test(c.url)) c.navigate(c.url);
        });
      })
  );
});

// 故意不写 self.addEventListener('fetch', ...) —— 见文件头第 1 条。
