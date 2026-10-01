// 自动生成于 2026-09-29 by scripts/gen_cards.py（大纲批量造卡）。
// 机器产出，人工复核后可保留/删改；此文件由 git 管理，属「内容」不是「状态」。
var CARDS_CS = [
  {
    "id": "cs-tcp-handshake",
    "domain": "计算机基础",
    "category": "work",
    "subject": "cs",
    "topicPath": [
      "计算机基础",
      "TCP 三次握手"
    ],
    "title": "TCP 三次握手为什么能建立连接？",
    "oneLine": "TCP 三次握手确保双方能正确建立连接。",
    "analogy": "两个人打电话确认对方能听得到。",
    "why": "确保双方能正确建立连接，避免错误连接。",
    "mechanism": [
      "① 客户端发送 SYN 包请求连接",
      "② 服务端回复 SYN-ACK 确认收到请求",
      "③ 客户端发送 ACK 确认收到服务端响应"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "客户端发送 SYN",
        "服务端回复 SYN-ACK",
        "客户端发送 ACK"
      ],
      "frames": [
        {
          "s": 0,
          "note": "客户端发送SYN请求"
        },
        {
          "s": 1,
          "note": "服务端接收SYN并回复SYN-ACK"
        },
        {
          "s": 2,
          "note": "客户端发送ACK确认"
        }
      ]
    },
    "interviewQ": [
      "为什么不能两次握手？",
      "三次握手和四次挥手的区别？"
    ],
    "keywords": [
      "TCP",
      "SYN",
      "ACK"
    ],
    "scene": [
      "客户端发送SYN后服务端未响应导致连接失败",
      "服务端主动关闭连接时需要四次挥手"
    ],
    "tags": [
      "网络协议",
      "连接管理"
    ],
    "related": []
  },
  {
    "id": "cs-http-vs-https",
    "domain": "计算机基础",
    "category": "work",
    "subject": "cs",
    "topicPath": [
      "计算机基础",
      "HTTP 与 HTTPS 区别"
    ],
    "title": "HTTP 与 HTTPS 的区别是什么？",
    "oneLine": "HTTPS 通过 SSL/TLS 加密数据传输。",
    "analogy": "快递员用密码箱送包裹，确保不被偷看。",
    "why": "防止数据被窃取或篡改，保证通信安全。",
    "mechanism": [
      "① HTTP 通过明文传输数据",
      "② HTTPS 使用 SSL/TLS 加密数据",
      "③ HTTPS 在传输层使用 TLS 协议"
    ],
    "interviewQ": [
      "HTTPS 如何保证数据安全？",
      "SSL/TLS 协议的作用？"
    ],
    "keywords": [
      "HTTP",
      "HTTPS",
      "SSL/TLS"
    ],
    "scene": [
      "HTTPS 用于支付系统保护用户隐私",
      "浏览器提示不安全时需启用 HTTPS"
    ],
    "tags": [
      "网络安全",
      "加密传输"
    ],
    "related": []
  },
  {
    "id": "cs-process-thread-coroutine",
    "domain": "计算机基础",
    "category": "work",
    "subject": "cs",
    "topicPath": [
      "计算机基础",
      "进程/线程/协程区别"
    ],
    "title": "进程、线程和协程有什么区别？",
    "oneLine": "进程是资源分配单位，线程是执行单位，协程是用户态线程。",
    "analogy": "进程是独立的房间，线程是房间里的活动，协程是同一房间中不同活动的切换。",
    "why": "提高程序并发能力，优化资源利用。",
    "mechanism": [
      "① 进程拥有独立的内存空间",
      "② 线程共享进程资源但有独立执行栈",
      "③ 协程由用户代码控制切换，减少系统开销"
    ],
    "interviewQ": [
      "线程和协程的区别？",
      "协程如何实现并发？"
    ],
    "keywords": [
      "进程",
      "线程",
      "协程"
    ],
    "scene": [
      "多线程实现并发处理请求",
      "协程用于异步任务调度避免阻塞"
    ],
    "tags": [
      "并发编程",
      "线程管理"
    ],
    "related": []
  }
];

if (typeof module !== "undefined" && module.exports) { module.exports = CARDS_CS; }
