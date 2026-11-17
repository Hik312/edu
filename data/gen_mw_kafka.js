// 严格 JSON 字面量：Node(vm) 与 Python(json) 都能直接读，请勿改回单引号
// 中间件 · Kafka 与消息队列（2026-10-09）
// ★ 缺口：middleware 科目里「消息队列」只有 4 张，其中Kafka 只有 1 张概览，
//   分区模型/ISR/acks/消费语义/积压这些面试高频一个都没有。
var CARDS_MW_KAFKA = [
  {
    "id": "kafka-architecture",
    "domain": "中间件",
    "category": "work",
    "subject": "middleware",
    "topicPath": ["中间件", "Kafka", "架构与分区模型"],
    "title": "Kafka 为什么快？为什么能扛住高吞吐？",
    "oneLine": "顺序写磁盘 + 零拷贝（sendfile）+ 批量压缩，把「磁盘 IO」优化到极致，所以单机就能扛百万 TPS。",
    "analogy": "像流水线传送带：不是一件件手工处理，而是大批量连续流过去，边走边打包。",
    "why": "它和 Redis 的缓存思路完全不同——Kafka 是吞吐优先的日志型队列，不是低延迟的点查。",
    "mechanism": [
      "① 顺序写磁盘：Kafka 只追加写日志不随机改，顺序写吞吐远高于随机写（机械盘顺序能到几百 MB/s）",
      "② 零拷贝：sendfile 在内核态直接搬数据不经用户态，省一次拷贝和上下文切换",
      "③ 批量压缩：攒够 batch 再发+压缩，网络和磁盘 IO 都省",
      "④ 页缓存：读走内存不直接读磁盘（依赖 OS 页缓存，可切换为 O_DIRECT 绕过）",
      "⑤ 分区并行：多分区可并行读写，吞吐随分区数近似线性增长",
      "⑥ 顺序保证只在**单个分区内**——全局有序要单分区（吞吐上不去）"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": ["写内存页缓存", "批量攒够", "顺序追加写磁盘", "压缩保留策略"],
      "frames": [
        { "s": 0, "note": "先写页缓存，不等磁盘" },
        { "s": 1, "note": "攒 batch 减少小包" },
        { "s": 2, "note": "顺序追加写，磁盘友好" },
        { "s": 3, "note": "压缩+按保留策略清理" }
      ]
    },
    "interviewQ": [
      "Kafka 为什么这么快？",
      "顺序写为什么比随机写快？",
      "Kafka 能保证全局有序吗？"
    ],
    "keywords": ["Kafka", "顺序写", "零拷贝", "批量", "页缓存", "吞吐"],
    "scene": [
      "日志采集百万条/秒靠 Kafka 落盘再消费，业务库压力小很多。",
      "面试被问「Kafka 为什么快」，答顺序写+零拷贝+批量+页缓存四条。"
    ],
    "tags": ["Kafka", "架构", "性能"],
    "related": [
      { "id": "kafka-partition-replica", "kind": "extends", "note": "分区模型是吞吐扩展的基础" },
      { "id": "kafka-consumer-group", "kind": "extends", "note": "消费侧模型" }
    ]
  },
  {
    "id": "kafka-partition-replica",
    "domain": "中间件",
    "category": "work",
    "subject": "middleware",
    "topicPath": ["中间件", "Kafka", "分区与副本"],
    "title": "Kafka 的分区和副本怎么设计？为什么不能随意扩分区？",
    "oneLine": "分区是并行度单位、副本是可用性单位；同一个 key 落同一分区保证有序，但**扩分区会破坏这个映射**。",
    "analogy": "分区像超市收银台（开得越多排队越少），副本像备份收银台（主台坏了换备的）。",
    "why": "扩分区导致 key 重新映射，是生产环境里的经典事故。",
    "mechanism": [
      "① 分区数决定吞吐上限（并行度），单分区约百万级/天",
      "② 消息按 key 哈希取模落到分区 → 同 key 同分区、保序",
      "③ ⚠️ 扩分区后取模基数变了 → 同一 key 落到新分区，**原有顺序断裂**",
      "④ 副本（replica）分布在不同 broker，同步到 ISR 列表才算已提交",
      "⑤ leader 负责读写、follower 只同步；leader 挂了从 ISR 里选新leader",
      "⑥ ⚠️ 副本不是备份：acks=all 只保证写入 ISR，不等于「绝不丢」（除非配合同步刷盘）",
      "⑦ 扩容的正确姿势：新建topic+双写迁移，或一开始就估够分区（分区只能增不能减）"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        { "title": "分区", "lines": ["分区0 P0 P1", "分区1 P2 P3"], "note": "并行读写" },
        { "title": "副本/ISR", "lines": ["leader 处理读写", "follower 同步"], "note": "高可用" }
      ],
      "frames": [
        { "s": 0, "note": "分区决定并行度" },
        { "s": 1, "note": "扩分区会打断 key 映射" },
        { "s": 2, "note": "副本靠 ISR 保可用" }
      ]
    },
    "interviewQ": [
      "为什么 Kafka 不能随意扩分区？",
      "ISR 是什么？",
      "acks=all 能保证不丢消息吗？"
    ],
    "keywords": ["Kafka", "分区", "副本", "ISR", "acks", "分区扩展"],
    "scene": [
      "扩分区后同一订单的事件顺序乱了，排查半天是取模基数变了。",
      "leader 挂了消息停止消费，定位到 ISR 里 follower 掉队了。"
    ],
    "tags": ["Kafka", "高可用", "分区"],
    "related": [
      { "id": "kafka-architecture", "kind": "extends", "note": "分区是吞吐的基础" },
      { "id": "kafka-consumer-group", "kind": "extends", "note": "消费者按分区分配" }
    ]
  },
  {
    "id": "kafka-consumer-group",
    "domain": "中间件",
    "category": "work",
    "subject": "middleware",
    "topicPath": ["中间件", "Kafka", "消费组与消费语义"],
    "title": "消费者组怎么分工？为什么同一分区只能被组内一个消费者消费？",
    "oneLine": "同一消费组内分区被独占（一个分区只能给一个消费者），保证组内不并发消费同分区保序；不同组各自独立消费全量。",
    "analogy": "一组人分工扫一个仓库：每片区域分给一个人不重复扫；不同组则是互不干扰的两队人各扫一遍。",
    "why": "搞清「分区独占」才能解释消费并行度上限、消费停滞（rebalance）等问题。",
    "mechanism": [
      "① 同一消费组内，一个分区同一时刻只能被**一个**消费者持有",
      "② 消费者数 ≤ 分区数才有意义；多出来的消费者空转",
      "③ 不同消费组互不影响，各自都能收到全量消息（广播语义）",
      "④ 消费者崩溃或新增触发 rebalance（重新分配分区），期间**短暂停止消费**",
      "⑤ ⚠️ rebalance 频繁（如会话超时设置过短）会导致消费停顿、积压",
      "⑥ 提交位点（offset）：先处理后提交=可能重复；先提交后处理=可能丢失"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        { "title": "组内", "lines": ["C1→分区0", "C2→分区1", "分区独占"], "note": "并行但保序" },
        { "title": "组间", "lines": ["组A 收全量", "组B 收全量"], "note": "互不影响" }
      ],
      "frames": [
        { "s": 0, "note": "组内分区独占 → 同分区不并发" },
        { "s": 1, "note": "rebalance 会短暂停止消费" },
        { "s": 2, "note": "offset 提交时机决定重复/丢失" }
      ]
    },
    "interviewQ": [
      "为什么同一分区只能被组内一个消费者消费？",
      "消费者数超过分区数会怎样？",
      "offset 先提交还是后提交？"
    ],
    "keywords": ["Kafka", "消费组", "消费者", "rebalance", "offset", "分区独占"],
    "scene": [
      "扩到 10 个消费者但只有 3 个分区，7 个空转，并行度上不去。",
      "消费者频繁 rebalance 导致消息积压，查出是心跳超时设太短。"
    ],
    "tags": ["Kafka", "消费", "消费者组"],
    "related": [
      { "id": "kafka-partition-replica", "kind": "extends", "note": "分区数限制消费并行度" },
      { "id": "kafka-ack-reliability", "kind": "extends", "note": "提交位点与投递语义" }
    ]
  },
  {
    "id": "kafka-ack-reliability",
    "domain": "中间件",
    "category": "work",
    "subject": "middleware",
    "topicPath": ["中间件", "Kafka", "可靠性与投递语义"],
    "title": "acks=0/1/all 有什么区别？为什么「不丢消息」要同时控制多个环节？",
    "oneLine": "acks=0 不等确认最易丢、acks=1 只等leader 写盘、acks=all 等全部 ISR 确认；端到端不丢还要生产者重试+幂等+消费端手动提交。",
    "analogy": "寄快递：acks=0 是发完就走，acks=1 是快递员收件即算妥，acks=all 是全家签收才妥。",
    "why": "面试常问「怎么保证消息不丢」，答案是分环节设防而不是一个参数。",
    "mechanism": [
      "① acks=0：不等 broker 确认，broker 挂了消息就丢（吞吐最高）",
      "② acks=1：只等 leader 写入即返回，follower 没同步就宕机会丢",
      "③ acks=all（或 -1）：等 ISR 全部确认，配合 min.insync.replicas≥2 才算稳",
      "④ 生产端：acks=all + retries>0 + enable.idempotence=true（去重）",
      "⑤ Broker：min.insync.replicas 防止「全部副本同步完才宕机」的极端丢数据",
      "⑥ 消费端：**先处理业务再手动提交 offset**，崩了会重投（所以消费侧必须幂等）",
      "⑦ 端到端「不丢」= 生产端重试 + Broker 副本 + 消费端手动提交且业务幂等"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        { "title": "acks 对照", "lines": ["0: 不等确认", "1: 等 leader", "all: 等 ISR"], "note": "可靠性↑吞吐↓" },
        { "title": "端到端不丢", "lines": ["生产端重试+幂等", "Broker 多副本", "消费端手动提交"], "note": "分环节设防" }
      ],
      "frames": [
        { "s": 0, "note": "acks 决定 broker 侧可靠性" },
        { "s": 1, "note": "端到端要三环节一起做" },
        { "s": 2, "note": "消费端重投 → 业务必须幂等" }
      ]
    },
    "interviewQ": [
      "acks 三档的区别？",
      "怎么保证消息不丢失？",
      "先提交 offset 还是先处理业务？"
    ],
    "keywords": ["Kafka", "acks", "可靠性", "offset提交", "幂等", "ISR"],
    "scene": [
      "设了acks=1，leader 写完就宕机，follower 没同步，消息丢了。",
      "消费端自动提交 offset，崩了消息被跳过，改为手动提交后靠幂等处理。"
    ],
    "tags": ["Kafka", "可靠性", "消息不丢"],
    "related": [
      { "id": "kafka-consumer-group", "kind": "extends", "note": "消费端提交位点策略" },
      { "id": "kafka-partition-replica", "kind": "extends", "note": "ISR 与 min.insync.replicas" }
    ]
  },
  {
    "id": "mq-use-case",
    "domain": "中间件",
    "category": "work",
    "subject": "middleware",
    "topicPath": ["中间件", "消息队列", "MQ 选型与典型场景"],
    "title": "什么时候该用消息队列？Kafka 和 RabbitMQ 怎么选？",
    "oneLine": "MQ 用于异步解耦、削峰填谷；Kafka 走高吞吐日志/流式，RabbitMQ 走低延迟任务分发——选型看「吞吐」还是「路由灵活」。",
    "analogy": "Kafka 像高速公路货运（能装能跑但路线固定），RabbitMQ 像快递分拣（件小、路由灵活、送达快）。",
    "why": "很多场景用 MQ 是为了解耦，但选错模型（比如用 Kafka 做延时任务）会付出复杂度代价。",
    "mechanism": [
      "① 三大用途：异步解耦（主流程不等下游）、削峰填谷（突发流量进队列）、服务治理（限流重试）",
      "② Kafka：分布式日志、顺序追加、海量吞吐（百万/s），消费要自己管位点",
      "③ RabbitMQ：AMQP 协议、路由灵活（topic/exchange/死信）、延迟低（万级/s）、管理界面友好",
      "④ ⚠️ 延时/死信队列是 RabbitMQ 的强项，Kafka 做延时要么自研要么用外挂调度",
      "⑤ Kafka 适合日志采集、流式计算、埋点；RabbitMQ 适合业务任务分发",
      "⑥ 引入 MQ 的代价：数据一致性变最终一致、排查链路变难、运维成本上升"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        { "title": "Kafka", "lines": ["高吞吐", "顺序日志", "消费位点自管"], "note": "流式/日志" },
        { "title": "RabbitMQ", "lines": ["路由灵活", "低延迟", "延时/死信"], "note": "任务分发" }
      ],
      "frames": [
        { "s": 0, "note": "先判断是否真需要 MQ" },
        { "s": 1, "note": "吞吐选 Kafka，灵活路由选 Rabbit" }
      ]
    },
    "interviewQ": [
      "什么时候该引入消息队列？",
      "Kafka 和 RabbitMQ 怎么选？",
      "用 MQ 的代价是什么？"
    ],
    "keywords": ["消息队列", "Kafka", "RabbitMQ", "选型", "解耦", "削峰"],
    "scene": [
      "下单接口要发5 种下游通知，全同步调导致主流程5 秒，改成 MQ 异步后50ms。",
      "用 Kafka 做延时关单，写了大量调度代码，换 RabbitMQ 死信队列后几行搞定。"
    ],
    "tags": ["消息队列", "选型", "架构"],
    "related": [
      { "id": "kafka-architecture", "kind": "extends", "note": "Kafka 侧细节" },
      { "id": "java-consistent-hashing", "kind": "compare", "note": "分布式一致性与 MQ 投递语义" }
    ]
  },
  {
    "id": "redis-mq-vs-kafka",
    "domain": "中间件",
    "category": "work",
    "subject": "middleware",
    "topicPath": ["中间件", "消息队列", "Redis 也能当队列"],
    "title": "Redis 的 Stream/List 为什么也能当消息队列？和 Kafka 差在哪？",
    "oneLine": "Redis List（LPUSH/BRPOP）就能做简单队列，Stream 补上消费组与持久化；但它是「点对点」，不擅长海量吞吐与回溯。",
    "analogy": "Redis 队列像小区快递柜（够用、简单），Kafka 像全国物流网（能扛海量但建设复杂）。",
    "why": "中小规模用 Redis 做队列更省事，量一大就撑不住——知道边界才知道什么时候换。",
    "mechanism": [
      "① Redis List：LPUSH 生产 + BRPOP 消费，最简队列（无确认、无重试）",
      "② Redis Stream：XADD + 消费组（XREADGROUP），有 ack、pending、可重放，接近 Kafka 语义",
      "③ ⚠️ List 弹出即消失：消费端崩了消息就丢（要可靠得自己处理）",
      "④ Stream 有持久化（AOF/RDB）+ 历史消息可读，适合中小规模",
      "⑤ 优势：低延迟、部署简单、和缓存一套基础设施",
      "⑥ ⚠️ 局限：不是分布式日志，消费组弱于 Kafka，吞吐/扩展性不及 Kafka（单实例瓶颈）",
      "⑦ 选择：中小规模/低延迟→Redis Stream；海量日志/流式/需要回溯→Kafka"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        { "title": "Redis List", "lines": ["LPUSH/BRPOP", "无ack，弹出即丢"], "note": "最简队列" },
        { "title": "Redis Stream", "lines": ["消费组+ack", "可重放历史"], "note": "接近 Kafka" },
        { "title": "Kafka", "lines": ["海量吞吐", "分布式日志"], "note": "重方案" }
      ],
      "frames": [
        { "s": 0, "note": "List 最简但会丢" },
        { "s": 1, "note": "Stream 补上 ack 和重放" },
        { "s": 2, "note": "海量还是得 Kafka" }
      ]
    },
    "interviewQ": [
      "Redis 能做消息队列吗？有什么局限？",
      "Redis Stream 和 List 有什么区别？",
      "什么时候从 Redis 换成 Kafka？"
    ],
    "keywords": ["Redis Stream", "List队列", "LPUSH", "BRPOP", "消费组", "消息队列"],
    "scene": [
      "用 Redis List 做队列，消費端崩了消息丢失，改成 Stream + 消费组后能重投。",
      "面试被问「Redis 和 Kafka 都能做队列怎么选」，答规模+可靠性诉求。"
    ],
    "tags": ["Redis", "消息队列", "Stream", "选型"],
    "related": [
      { "id": "java-redis-stream-mq", "kind": "extends", "note": "Redis Stream 做消息队列的细节" },
      { "id": "mq-use-case", "kind": "compare", "note": "与 Kafka 的选型对比" }
    ]
  }
];
if (typeof module !== "undefined" && module.exports) {
  module.exports = CARDS_MW_KAFKA;
}