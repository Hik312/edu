// 严格 JSON 字面量：Node(vm) 与 Python(json) 都能直接读，请勿改回单引号
var CARDS_SPRINGBOOT = [
  {
    "id": "sb-autoconfig",
    "domain": "求职·Java",
    "topicPath": [
      "SpringBoot",
      "核心原理",
      "自动装配"
    ],
    "title": "SpringBoot 自动装配是怎么跑起来的",
    "oneLine": "由一个 ImportSelector 拉清单，条件注解逐个过闸，通过的才注册成 Bean 定义",
    "analogy": "像自助餐厅的取餐单：先拿到一张候选菜单（imports 清单），逐个看后厨有没有这道菜的原料（@ConditionalOnClass），有才正式上架",
    "why": "没有它，每个 starter 都要手写一堆 @Bean 配置；有了它，引入 jar 即生效",
    "mechanism": [
      "① 入口注解 @SpringBootApplication 是复合注解，内含 @EnableAutoConfiguration",
      "② @EnableAutoConfiguration 上标注 @Import(AutoConfigurationImportSelector.class)",
      "③ 配置类后处理器 ConfigurationClassPostProcessor 解析 @Import，回调这个 DeferredImportSelector",
      "④ 读取候选清单：Spring Boot 3 读 META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports（2.x 是 spring.factories 的 EnableAutoConfiguration 项）",
      "⑤ 去重 + 按 @AutoConfigureOrder / @AutoConfigureBefore/After 排序",
      "⑥ 逐个用条件注解过闸：@ConditionalOnClass 看类路径有没有这个依赖，@ConditionalOnMissingBean 看用户是否自己定义了，@ConditionalOnProperty 看配置项开关",
      "⑦ 通过筛选的类作为 @Configuration 被解析，其 @Bean 方法注册为 BeanDefinition"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "复合入口注解",
        "拉候选清单",
        "排序去重",
        "条件注解过闸",
        "注册 BeanDefinition"
      ],
      "frames": [
        {
          "s": 0,
          "note": "@SpringBootApplication = @Configuration + @ComponentScan + @EnableAutoConfiguration"
        },
        {
          "s": 1,
          "note": "Spring Boot 3 由 ImportCandidates 读 imports 文件；2.x 由 SpringFactoriesLoader 读 spring.factories"
        },
        {
          "s": 2,
          "note": "排序是给后续装配顺序用的：后置条件往往依赖前置 Bean 是否存在"
        },
        {
          "s": 3,
          "note": "这一步决定了「引入 jar 才生效」：类不在 classpath 就整条跳过"
        },
        {
          "s": 4,
          "note": "注意注册的是定义而非实例，实例化发生在后续容器启动阶段"
        }
      ]
    },
    "interviewQ": [
      "Spring Boot 2 和 3 在自动装配清单文件上有什么区别？（答：2.x 用 spring.factories 的 EnableAutoConfiguration 段，3.x 迁到 AutoConfiguration.imports 文件）",
      "为什么我们自己写个 @Service 就能覆盖官方默认 Bean？",
      "自动装配是按需还是全量？开销在哪一步？"
    ],
    "keywords": [
      "自动装配",
      "AutoConfiguration",
      "ImportSelector",
      "ConditionalOnClass",
      "条件装配"
    ],
    "scene": [
      "接 Redis：只引 spring-boot-starter-data-redis，RedisAutoConfiguration 检测到类路径有 RedisOperations 才注册 RedisTemplate；你自己再写一个，OnMissingBean 就自动让位给你的版本",
      "写公司内部 starter：把短信、文件存储、鉴权 SDK 封装成 starter，别人引个依赖 + 加一行配置就能用，不用每个项目复制配置类",
      "踩坑：自动配置类必须在 AutoConfiguration.imports 里登记；只在自己包里写个 @Configuration 是不会被自动装配扫到的"
    ],
    "tags": [
      "高频",
      "原理"
    ],
    "category": "work",
    "subject": "java",
    "related": [
      {
        "id": "sb-condition",
        "kind": "prereq",
        "note": "自动装配逐个过闸靠的就是条件注解，不看这个只记住流程"
      },
      {
        "id": "sb-bean-lifecycle",
        "kind": "extends",
        "note": "装配通过后注册成 BeanDefinition，接着走完整生命周期"
      },
      {
        "id": "sb-startup",
        "kind": "compare",
        "note": "自动装配发生在 refresh 里，是启动流程的一个阶段而非并列关系"
      }
    ]
  },
  {
    "id": "sb-startup",
    "domain": "求职·Java",
    "topicPath": [
      "SpringBoot",
      "核心原理",
      "启动流程"
    ],
    "title": "SpringApplication.run 这一趟到底做了什么",
    "oneLine": "两阶段：先准备环境和上下文，再刷新容器把 Bean 全部建出来",
    "analogy": "像开店营业前：先租好铺面、备好水电（环境准备），把货架摆上（注册 Bean 定义），最后统一开张（refresh）",
    "why": "排查启动报错、理解配置加载时机、理解为什么有些 Bean 在某个阶段还没准备好，都得靠这张图",
    "mechanism": [
      "① new SpringApplication(...)：推断应用类型（Servlet / Reactive / 普通），加载 ApplicationContextInitializer 与 Listener",
      "② prepareEnvironment：按顺序叠加 PropertySource，发布 ApplicationEnvironmentPreparedEvent，此时配置文件刚读完",
      "③ 创建 ApplicationContext：Servlet Web 场景是 AnnotationConfigServletWebServerApplicationContext",
      "④ prepareContext：执行 initializer，把主配置类注册成 BeanDefinition",
      "⑤ refreshContext → AbstractApplicationContext.refresh()：BeanFactory 初始化、执行 BeanFactoryPostProcessor、注册 BeanPostProcessor、实例化所有非懒加载单例",
      "⑥ 其中 onRefresh() 由 ServletWebServerApplicationContext 覆写，创建并启动内嵌 Tomcat",
      "⑦ finishRefresh 后调用 CommandLineRunner / ApplicationRunner，标记 Started"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "推断类型 + 加载扩展点",
        "准备环境",
        "创建上下文",
        "refresh 刷新",
        "启动内嵌容器",
        "执行 Runner"
      ],
      "frames": [
        {
          "s": 0,
          "note": "WebApplicationType.deduce 靠 classpath 里有没有 DispatcherServlet / DispatcherHandler 判断"
        },
        {
          "s": 1,
          "note": "监听器可以在这里改配置，这也是很多框架（Nacos 等）抢 earliest 时机的方式"
        },
        {
          "s": 2,
          "note": "上下文此时基本是空的，只有 Environment 可用"
        },
        {
          "s": 3,
          "note": "绝大多数 Bean 在这一步被创建，循环依赖、初始化异常基本都炸在这里"
        },
        {
          "s": 4,
          "note": "注意顺序：端口是在 refresh 内部的 onRefresh 里监听的，不是 run 方法最后"
        },
        {
          "s": 5,
          "note": "Runner 执行时容器已就绪，适合做预热、缓存加载"
        }
      ]
    },
    "interviewQ": [
      "想在所有 Bean 创建完成后执行一段代码，有几种写法？（Runner / SmartInitializingSingleton / ContextRefreshedEvent / InitializingBean）",
      "为什么有时 @Value 拿不到值？（时机过早，Environment 还没叠加完成，或 Bean 不是容器管理）"
    ],
    "keywords": [
      "启动流程",
      "run",
      "refresh",
      "ApplicationRunner",
      "生命周期"
    ],
    "scene": [
      "接配置中心：Nacos / Apollo 拉远端配置必须早于 Bean 创建，所以它们的钩子挂在 EnvironmentPreparedEvent 这一步",
      "启动预热：本地字典缓存、线程池预创建、灰度开关自检，这些适合写在 CommandLineRunner 里，此时容器已就绪",
      "排错：启动卡住时看日志最后一条事件时间戳，配合 Arthas 看是哪个 Bean 的初始化卡住了"
    ],
    "tags": [
      "高频",
      "原理"
    ],
    "category": "work",
    "subject": "java",
    "related": [
      {
        "id": "sb-embedded-tomcat",
        "kind": "extends",
        "note": "onRefresh 阶段拉起内嵌容器，是启动流程的第 8 步"
      },
      {
        "id": "sb-autoconfig",
        "kind": "extends",
        "note": "refresh 里由 ConfigurationClassPostProcessor 触发自动装配"
      }
    ]
  },
  {
    "id": "sb-bean-lifecycle",
    "domain": "求职·Java",
    "topicPath": [
      "SpringBoot",
      "IoC",
      "Bean 生命周期"
    ],
    "title": "一个 Bean 从定义到可用完整走几步",
    "oneLine": "实例化 → 属性填充 → 初始化回调 → BeanPostProcessor 织入代理 → 进单例池",
    "analogy": "像造一台车：先出车架（实例化），装发动机座椅（属性注入），出厂检测（初始化回调），最后贴膜改装（后置处理器生成代理），停进成品仓（单例池）",
    "why": "AOP、事务、@Autowired 为什么有时不生效，答案全在这个顺序里",
    "mechanism": [
      "① BeanDefinition 登记：配置类被解析，定义信息进 BeanDefinitionMap，此刻还没有对象",
      "② 实例化 createBeanInstance：通过构造器反射或工厂方法造出原始对象",
      "③ populateBean：按类型 / 名称注入依赖，这一步最容易触发依赖 Bean 的创建",
      "④ Aware 回调：BeanNameAware、BeanFactoryAware、ApplicationContextAware 依次拿到容器资源",
      "⑤ postProcessBeforeInitialization：BeanPostProcessor 前置处理",
      "⑥ 初始化：@PostConstruct → InitializingBean.afterPropertiesSet → 自定义 init-method",
      "⑦ postProcessAfterInitialization：AOP 代理在这一步生成，返回的可能已不是原对象",
      "⑧ 成品入 singletonObjects；容器关闭时 @PreDestroy → DisposableBean → destroy-method"
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "def",
          "label": "定义登记"
        },
        {
          "id": "inst",
          "label": "实例化"
        },
        {
          "id": "pop",
          "label": "属性注入"
        },
        {
          "id": "init",
          "label": "初始化回调"
        },
        {
          "id": "proxy",
          "label": "生成代理"
        },
        {
          "id": "ready",
          "label": "成品可用"
        }
      ],
      "edges": [
        {
          "from": "def",
          "to": "inst"
        },
        {
          "from": "inst",
          "to": "pop"
        },
        {
          "from": "pop",
          "to": "init"
        },
        {
          "from": "init",
          "to": "proxy"
        },
        {
          "from": "proxy",
          "to": "ready"
        }
      ],
      "frames": [
        {
          "n": "def",
          "note": "只有 BeanDefinition，没有对象；也是 BeanDefinitionRegistryPostProcessor 能改定义的原因"
        },
        {
          "n": "inst",
          "note": "构造器选型：多个构造器且无参构造器存在时用无参，否则选 @Autowired 标注的那个"
        },
        {
          "n": "pop",
          "note": "循环依赖在这一步被触发；字段注入是反射强行塞入构造器之外的值"
        },
        {
          "n": "init",
          "note": "三种初始化方式的执行顺序是固定的，扩展框架常用 InitializingBean 做自检"
        },
        {
          "n": "proxy",
          "note": "关键：此时替换掉原对象，所以注入到别人手里的是代理对象"
        },
        {
          "n": "ready",
          "note": "进一级单例池，此后所有 getBean 都拿到同一个实例"
        }
      ]
    },
    "interviewQ": [
      "为什么在自己类里 this.xxx() 调用带 @Transactional 的方法事务不生效？",
      "AOP 代理是在哪一步生成的？（答：postProcessAfterInitialization，不是实例化时）"
    ],
    "keywords": [
      "Bean生命周期",
      "PostConstruct",
      "BeanPostProcessor",
      "代理生成时机",
      "单例池"
    ],
    "scene": [
      "@PostConstruct 里加载字典表：此刻属性已注入完成，适合做依赖数据库的一次性初始化",
      "写 BeanPostProcessor 给特定注解字段织入：例如把 RPC 代理注入到标注了 @RpcClient 的字段上",
      "坑：@PostConstruct 里做远程调用，失败会让整个容器启动失败而不是降级，别往里塞重操作"
    ],
    "tags": [
      "高频",
      "必会"
    ],
    "category": "work",
    "subject": "java",
    "related": [
      {
        "id": "sb-circular",
        "kind": "extends",
        "note": "循环依赖是生命周期中「属性填充」这一卡住时的解法"
      },
      {
        "id": "sb-aop-proxy",
        "kind": "extends",
        "note": "代理生成发生在初始化之后，这一步决定了你拿到的是不是原对象"
      }
    ]
  },
  {
    "id": "sb-circular",
    "domain": "求职·Java",
    "topicPath": [
      "SpringBoot",
      "IoC",
      "循环依赖"
    ],
    "title": "三级缓存怎么解开循环依赖",
    "oneLine": "把半成品提前曝光到缓存里，让对方能先把引用拿到手，回头补完自己",
    "analogy": "两个人互相借钱：不用等对方转账完成，先拍个「欠条」塞给对方（早期引用），回头再兑现",
    "why": "面试必考，也是理解「为什么构造器注入的循环依赖救不回来」的钥匙",
    "mechanism": [
      "① 三级缓存：singletonObjects（成品） / earlySingletonObjects（半成品） / singletonFactories（对象工厂）",
      "② A 实例化后被包成一个 ObjectFactory 塞进三级缓存（还没有属性）",
      "③ A 填充属性时发现需要 B，容器去创建 B",
      "④ B 填充属性时回头找 A：一级没有 → 二级没有 → 三级找到 ObjectFactory",
      "⑤ 执行 getObject() 得到 A 的早期引用（若 A 被 AOP 增强，这里直接生成代理对象），放入二级，三级删除",
      "⑥ B 拿到 A 的引用后完成创建并进入一级缓存",
      "⑦ 回到 A，补齐属性，执行初始化，最终把自己放进一级缓存并清理二级"
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "a",
          "label": "A 实例化"
        },
        {
          "id": "f",
          "label": "三级工厂"
        },
        {
          "id": "e",
          "label": "二级早期"
        },
        {
          "id": "b",
          "label": "B 拿到引用"
        },
        {
          "id": "back",
          "label": "A 补完"
        },
        {
          "id": "done",
          "label": "进一级池"
        }
      ],
      "edges": [
        {
          "from": "a",
          "to": "f"
        },
        {
          "from": "f",
          "to": "e"
        },
        {
          "from": "e",
          "to": "b"
        },
        {
          "from": "b",
          "to": "back"
        },
        {
          "from": "back",
          "to": "done"
        }
      ],
      "frames": [
        {
          "n": "a",
          "note": "对象已存在但属性为空，此刻只能算半成品"
        },
        {
          "n": "f",
          "note": "关键设计：三级缓存存的是「工厂」而不是对象，延迟到真正被需要时才决定是否生成代理"
        },
        {
          "n": "e",
          "note": "一旦二级有值，三级就被删除，保证同一注入过程只解析一次"
        },
        {
          "n": "b",
          "note": "B 持有的引用是能正常工作的，因为方法调用时 A 的字段才被真正读取"
        },
        {
          "n": "back",
          "note": "回到 A 的创建流程继续走属性填充与初始化"
        },
        {
          "n": "done",
          "note": "Spring Boot 2.6 起默认禁用循环依赖，真要用需显式配置 spring.main.allow-circular-references=true"
        }
      ]
    },
    "interviewQ": [
      "为什么必须三级缓存，两级不行吗？（关键在 AOP：需要延迟决定要不要生成早期代理，二级缓存做不了这个延迟）",
      "什么情况下三级缓存也救不了？（构造器注入导致的循环依赖 —— 实例化本身就要依赖，无法提前曝光）"
    ],
    "keywords": [
      "三级缓存",
      "循环依赖",
      "早期引用",
      "构造器注入",
      "allow-circular-references"
    ],
    "scene": [
      "Service 互相注入：订单 Service 要查用户、用户 Service 又要查订单 → 启动时直接报 cycle 错误",
      "很多人临时加 allow-circular-references=true 或 @Lazy 绕过去，但根因是职责边界没划清，正解是抽第三个编排层或把一段逻辑下沉到应用层",
      "构造器注入造成的循环依赖三级缓存救不回来，会抛 BeanCurrentlyInCreationException —— 这是必须重构的信号，不是配置能解决的"
    ],
    "tags": [
      "必考",
      "坑点"
    ],
    "category": "work",
    "subject": "java",
    "related": [
      {
        "id": "sb-bean-lifecycle",
        "kind": "prereq",
        "note": "先有生命周期的分步，才知道三级缓存卡在哪一步"
      },
      {
        "id": "sb-aop-proxy",
        "kind": "compare",
        "note": "早期引用暴露的是代理对象，AOP 会让循环依赖更容易踩坑"
      }
    ]
  },
  {
    "id": "sb-aop-proxy",
    "domain": "求职·Java",
    "topicPath": [
      "SpringBoot",
      "AOP",
      "代理实现"
    ],
    "title": "JDK 动态代理和 CGLIB 到底差在哪",
    "oneLine": "前者实现同一套接口做兄弟替身，后者继承原类做儿子替身，因此限制完全不同",
    "analogy": "JDK 代理像找了个同工种的同事代你上班，前提是你们都持同一岗位资格（接口）；CGLIB 像让你儿子顶替你，但你私藏的那些 final 本事他学不去",
    "why": "决定了 @Transactional / @Cacheable 这类注解能不能生效，以及为什么 final 方法、私有方法不受 AOP 影响",
    "mechanism": [
      "① JDK 动态代理：目标类至少实现一个接口，运行时生成实现同接口的代理类，调用转发到 InvocationHandler.invoke",
      "② CGLIB：生成目标类的子类并重写方法，通过 MethodInterceptor 拦截",
      "③ 限制差异：JDK 只能代理接口里声明的方法；CGLIB 不能代理 final 类、final 方法、private 方法",
      "④ 选择逻辑由 DefaultAopProxyFactory 决定：有接口优先考虑 JDK，否则 CGLIB",
      "⑤ Spring Boot 的 AopAutoConfiguration 默认把 proxyTargetClass 置为 true，所以 Boot 项目里即使有接口也通常走 CGLIB",
      "⑥ 只有走代理对象的方法调用才会被拦截，this 自调用绕过了代理，增强不生效"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "JDK 动态代理",
          "lines": [
            "要求：目标实现了接口",
            "产物：接口的另一个实现类",
            "限制：接口以外的方法管不到",
            "调用链：Proxy → InvocationHandler → 目标"
          ]
        },
        {
          "title": "CGLIB 子类代理",
          "lines": [
            "要求：可被继承（无 final）",
            "产物：目标类的子类",
            "限制：final / private 无法重写",
            "调用链：子类 → MethodInterceptor → 父类方法"
          ]
        }
      ],
      "frames": [
        {
          "note": "先问一句：目标类有没有实现接口？这是选择的第一道判断",
          "active": []
        },
        {
          "note": "但在 Spring Boot 里，proxyTargetClass 默认为 true，多数场景直接走 CGLIB",
          "active": [
            1
          ]
        },
        {
          "note": "无论哪种，自调用 this.method() 都绕过了代理对象，所以增强失效",
          "active": [
            0,
            1
          ]
        }
      ]
    },
    "interviewQ": [
      "Spring Boot 默认用的是哪种？（答：proxyTargetClass 默认 true → CGLIB，这是和裸 Spring 的区别）",
      "怎么让同一个类里的内部方法调用也能吃到事务？（注入自身代理 / AopContext / 拆到另一个 Bean）"
    ],
    "keywords": [
      "动态代理",
      "CGLIB",
      "JDK代理",
      "proxyTargetClass",
      "自调用失效"
    ],
    "scene": [
      "注入报 BeanNotOfRequiredTypeException：JDK 代理生成的是「接口的实现类」，你的字段却声明成具体实现类，类型对不上",
      "给 final 类或 final 方法加 @Cacheable 不生效：CGLIB 靠继承重写，final 方法重写不了",
      "多数据源切换：自定义注解 + AOP 环绕，在方法执行前把数据源 key 塞进 ThreadLocal，执行完清理"
    ],
    "tags": [
      "高频",
      "坑点"
    ],
    "category": "work",
    "subject": "java",
    "related": [
      {
        "id": "sb-transactional",
        "kind": "extends",
        "note": "事务就是靠代理实现的，自调用失效的根因在这里"
      },
      {
        "id": "sb-circular",
        "kind": "compare",
        "note": "两者都涉及「你拿到的对象是不是原对象」这个问题"
      }
    ]
  },
  {
    "id": "sb-mvc-flow",
    "domain": "求职·Java",
    "topicPath": [
      "SpringBoot",
      "SpringMVC",
      "请求链路"
    ],
    "title": "一次 HTTP 请求在框架里穿过了哪几层",
    "oneLine": "由 DispatcherServlet 统一入口收口，按 映射 → 适配 → 执行 → 回写 四段走完",
    "analogy": "像快递总机：先查单号确认派给谁（映射），找到对应工具车（适配器），中间过安检门（拦截器），最后把回执按格式包装寄回",
    "why": "排查参数绑定失败、返回值序列化异常、拦截器不生效等问题时，这张图是定位地图",
    "mechanism": [
      "① 请求进 Tomcat，依次穿过 Filter 链，到达 DispatcherServlet.doDispatch",
      "② HandlerMapping 按 URL 找到目标方法封装为 HandlerExecutionChain（含拦截器）",
      "③ HandlerAdapter 按类型适配：普通 Controller 用的是 RequestMappingHandlerAdapter",
      "④ 执行拦截器 preHandle；任一只返回 false 则中断",
      "⑤ HandlerMethodArgumentResolver 完成参数解析与数据绑定（@RequestBody / @RequestParam / @PathVariable）",
      "⑥ 反射调用 Controller 方法，拿到返回值",
      "⑦ HandlerMethodReturnValueHandler + HttpMessageConverter 把返回值写成 JSON（@ResponseBody 场景）",
      "⑧ 执行 postHandle、渲染或输出，最后 afterCompletion；异常统一走 HandlerExceptionResolver"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "Tomcat + Filter",
        "HandlerMapping",
        "HandlerAdapter",
        "拦截器 pre",
        "参数绑定",
        "执行方法",
        "返回值写出"
      ],
      "frames": [
        {
          "s": 0,
          "note": "Filter 属于 Servlet 规范，能拦截一切请求，但拿不到 Spring 的 Handler 信息"
        },
        {
          "s": 1,
          "note": "这一步确定「谁来干」，返回的是方法 + 拦截链的打包对象"
        },
        {
          "s": 2,
          "note": "适配器模式：让不同类型的 Handler（Controller / Servlet / 函数式）都能统一调用"
        },
        {
          "s": 3,
          "note": "拦截器是 Spring MVC 层概念，此时已进入 DispatcherServlet，能拿到方法元信息"
        },
        {
          "s": 4,
          "note": "@RequestBody 由 RequestResponseBodyMethodProcessor 处理，配合消息转换器反序列化"
        },
        {
          "s": 5,
          "note": "真正执行业务方法，事务代理在这一层被调用"
        },
        {
          "s": 6,
          "note": "对象转 JSON 由 MappingJackson2HttpMessageConverter 完成，日期/循环引用问题出在这"
        }
      ]
    },
    "interviewQ": [
      "Filter、Interceptor、AOP 的触发顺序和作用粒度有什么区别？",
      "@RequestParam 和 @RequestBody 的处理类分别是谁？"
    ],
    "keywords": [
      "DispatcherServlet",
      "HandlerMapping",
      "拦截器",
      "参数绑定",
      "消息转换器"
    ],
    "scene": [
      "统一返回结构：用 ResponseBodyAdvice 在所有 @ResponseBody 返回前包一层 Result<T>，Controller 里不用手写包装",
      "参数校验兜底：@RestControllerAdvice 拦 MethodArgumentNotValidException，返回友好提示而不是甩给用户一个 400 堆栈",
      "幂等与防重：在 HandlerInterceptor.preHandle 里校验请求令牌，走到一半发现重复直接拦掉，不进业务方法"
    ],
    "tags": [
      "高频"
    ],
    "category": "work",
    "subject": "java",
    "related": [
      {
        "id": "sb-filter-levels",
        "kind": "extends",
        "note": "请求链路里具体在哪几层被拦，拆开单独看"
      },
      {
        "id": "sb-embedded-tomcat",
        "kind": "prereq",
        "note": "DispatcherServlet 要先注册进容器，链路才跑得起来"
      }
    ]
  },
  {
    "id": "sb-transactional",
    "domain": "求职·Java",
    "topicPath": [
      "SpringBoot",
      "事务",
      "失效场景"
    ],
    "title": "@Transactional 失效的六种常见写法",
    "oneLine": "凡是让调用没走到代理对象、或者让异常没传出去的写法，都会让注解形同虚设",
    "analogy": "像装了门禁却从消防门进出：规则本身没问题，只是你压根没经过它",
    "why": "事务不回滚是线上最容易被忽视也最难复盘的坑",
    "mechanism": [
      "① 自调用：同一类里 this.method() 绕开代理，增强不生效",
      "② 方法不是 public：代理类无法覆盖私有方法，JDK 代理也只认接口公开方法",
      "③ 方法被 final / static 修饰：CGLIB 子类无法重写",
      "④ 异常被 catch 吞掉：事务切面靠捕获异常决定是否回滚，没看到异常就正常提交",
      "⑤ 抛出的是受检异常，且没配 rollbackFor：默认只对 RuntimeException 和 Error 回滚",
      "⑥ 对象不是容器管理的 Bean：自己 new 出来的实例没有代理层",
      "⑦ 传播行为配置错误：NOT_SUPPORTED / NEVER / SUPPORTS 在外层无事务时不生效"
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "生效写法",
          "lines": [
            "public 方法",
            "由另一个 Bean 调用进来",
            "异常继续向上抛",
            "读法是 RuntimeException 或指定 rollbackFor",
            "异常不被 catch 吞掉"
          ]
        },
        {
          "title": "失效写法",
          "lines": [
            "private / final 方法",
            "同类中 this.xxx()",
            "异常被 try 吞了",
            "受检异常未配 rollbackFor",
            "new 出来的对象调用"
          ]
        }
      ],
      "frames": [
        {
          "note": "核心判断：这次调用有没有经过代理对象？这是 ① ② ③ ⑥ 的共同根因",
          "active": [
            1
          ]
        },
        {
          "note": "第二层判断：异常有没有被事务切面感知到？这是 ④ ⑤ 的共同根因",
          "active": [
            0
          ]
        },
        {
          "note": "排查顺序建议：先看方法修饰符 → 再看调用来源 → 最后看异常处理方式",
          "active": [
            0,
            1
          ]
        }
      ]
    },
    "interviewQ": [
      "同类内部方法调用想生效有几种解法？",
      "rollbackFor 不配置时，抛出 IOException 会回滚吗？（答：不会）"
    ],
    "keywords": [
      "事务失效",
      "自调用",
      "rollbackFor",
      "传播行为",
      "代理绕过"
    ],
    "scene": [
      "下单扣库存：外层 createOrder 用 try-catch 把 deductStock 的异常吞了，事务感知不到 → 库存没回滚，订单也没落库",
      "同一个 Service 里用 this.deductStock() 调带事务的方法，绕过了代理 → 库存扣了，后续创建订单失败却不回滚",
      "调用第三方接口抛受检异常且没配 rollbackFor → 事务照常提交，半成品数据留在库里"
    ],
    "tags": [
      "必考",
      "坑点"
    ],
    "category": "work",
    "subject": "java",
    "related": [
      {
        "id": "sb-aop-proxy",
        "kind": "prereq",
        "note": "不先懂代理，六种失效只能靠背，换种写法就认不出"
      },
      {
        "id": "sb-bean-lifecycle",
        "kind": "compare",
        "note": "两者都讲究「哪个时机做哪件事」"
      }
    ]
  },
  {
    "id": "sb-condition",
    "domain": "求职·Java",
    "topicPath": [
      "SpringBoot",
      "核心原理",
      "条件装配"
    ],
    "title": "条件注解凭什么决定装配与否",
    "oneLine": "每个 Condition 返回布尔值，容器在注册定义前用它做一道闸门",
    "analogy": "像餐厅的备餐规则：有食材才能做这道菜（OnClass），后厨没被别人占着才自己上（OnMissingBean），菜单开关打开了才供应（OnProperty）",
    "why": "理解它，才能解释「为什么我加了依赖它就自动配好了」以及自定义 starter 的核心写法",
    "mechanism": [
      "① 条件注解本质是 @Conditional 的派生，各自绑定一个 Condition 实现类",
      "② @ConditionalOnClass：判断 classpath 是否有指定类，不存在则整个配置类/方法跳过",
      "③ @ConditionalOnMissingBean：容器里没有同类型 Bean 才注册 —— 这正是用户自定义 Bean 能覆盖默认配置的原因",
      "④ @ConditionalOnProperty：读取配置项，matchIfMissing 决定缺省时的行为",
      "⑤ @ConditionalOnBean：依赖某个 Bean 先存在",
      "⑥ @ConditionalOnWebApplication：限定运行环境",
      "⑦ 判定发生在注册 BeanDefinition 之前，因此未通过的类连解析都不会做"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "扫描到配置类",
        "读取 Condition",
        "Class 与 Bean 检查",
        "配置项检查",
        "决定注册或跳过"
      ],
      "frames": [
        {
          "s": 0,
          "note": "这些候选来自 imports 清单或组件扫描"
        },
        {
          "s": 1,
          "note": "每个条件注解对应一个实现了 Condition 接口的匹配器"
        },
        {
          "s": 2,
          "note": "OnClass 是依赖开关，OnMissingBean 是默认可被覆盖的开关"
        },
        {
          "s": 3,
          "note": "matchIfMissing=true 表示配置缺失时也当作匹配"
        },
        {
          "s": 4,
          "note": "跳过意味着这个自动配置类完全不参与后续的 Bean 定义注册"
        }
      ]
    },
    "interviewQ": [
      "为什么我自己定义一个 RestTemplate Bean，官方的默认 Bean 就不见了？（答：@ConditionalOnMissingBean）",
      "写一个自定义 starter 需要哪些要素？"
    ],
    "keywords": [
      "条件注解",
      "ConditionalOnMissingBean",
      "ConditionalOnClass",
      "matchIfMissing",
      "自定义starter"
    ],
    "scene": [
      "存储策略切换：@ConditionalOnProperty(havingValue=\"oss\") 配线上 OSS，另一个实现类标 havingValue=\"local\", matchIfMissing=true 给本地开发用磁盘",
      "多实现类兜底：默认实现加 @ConditionalOnMissingBean，业务方只要自己定义一个 Bean 就自动顶掉默认实现",
      "只在 Web 环境生效的配置加 @ConditionalOnWebApplication，跑纯单元测试（无 web 容器）时就不会被加载"
    ],
    "tags": [
      "高频"
    ],
    "category": "work",
    "subject": "java",
    "related": [
      {
        "id": "sb-autoconfig",
        "kind": "extends",
        "note": "条件注解是自动装配的执行单元，最终服务于装配决策"
      }
    ]
  },
  {
    "id": "sb-filter-levels",
    "domain": "求职·Java",
    "topicPath": [
      "SpringBoot",
      "SpringMVC",
      "拦截层次"
    ],
    "title": "Filter、Interceptor、AOP 三层该怎么选",
    "oneLine": "越靠外层越通用也越贫瘠，越靠内层越贴近业务也越依赖容器",
    "analogy": "小区门禁（Filter）谁都能拦但只认脸；单元门（Interceptor）能识别住户；入户门（AOP）知道你家具体在干嘛",
    "why": "选错层级会导致要么拿不到想要的对象，要么范围过大误伤静态资源",
    "mechanism": [
      "① Filter：Servlet 规范，Tomcat 层，能拦所有请求，只能拿到 request/response",
      "② Interceptor：Spring MVC 层，在 DispatcherServlet 之后，能拿到目标 HandlerMethod 与 ModelAndView",
      "③ AOP：Spring 容器层，作用于 Bean 方法，粒度最细，能拿到参数与返回值",
      "④ 执行顺序：Filter → Interceptor.preHandle → AOP 增强 → Controller 方法体",
      "⑤ 退出顺序：AOP → Interceptor.postHandle → 视图渲染 → afterCompletion → Filter 返回",
      "⑥ 选择建议：编码过滤、跨域放 Filter；登录鉴权按粒度选 Interceptor；日志审计、事务用 AOP"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "Tomcat / Filter",
        "DispatcherServlet",
        "Interceptor",
        "AOP 代理",
        "Controller",
        "响应返回"
      ],
      "frames": [
        {
          "s": 0,
          "note": "Servlet 容器层，Spring 上下文还不存在，拿不到 @Service"
        },
        {
          "s": 1,
          "note": "统一入口，从这里开始进入 Spring 的世界"
        },
        {
          "s": 2,
          "note": "Spring MVC 概念，可以拿到 HandlerMethod 做权限元数据判断"
        },
        {
          "s": 3,
          "note": "Spring Bean 概念，事务、缓存、自定义切面在这一层"
        },
        {
          "s": 4,
          "note": "真正的业务方法体被执行"
        },
        {
          "s": 5,
          "note": "回溯顺序相反：内层先返回，外层后收尾"
        }
      ]
    },
    "interviewQ": [
      "想在方法返回后修改返回值，用哪种最合适？（答：AOP 环绕或 ResponseBodyAdvice）",
      "跨域配置放 Filter 还是 Interceptor？"
    ],
    "keywords": [
      "Filter",
      "Interceptor",
      "AOP",
      "执行顺序",
      "拦截粒度"
    ],
    "scene": [
      "traceId：放 Filter，所有请求包括静态资源都能带上，日志链路才串得起来",
      "登录鉴权：放 Interceptor，此时能拿到 HandlerMethod，可以读方法上的 @RequireLogin 等元注解做细粒度控制",
      "操作审计日志：放 AOP，能同时拿到方法参数与返回值，记录「谁在什么时候把哪条数据改成了什么」"
    ],
    "tags": [
      "高频"
    ],
    "category": "work",
    "subject": "java",
    "related": [
      {
        "id": "sb-mvc-flow",
        "kind": "prereq",
        "note": "先有完整链路，才知道这三层各自插在哪"
      },
      {
        "id": "sb-aop-proxy",
        "kind": "compare",
        "note": "AOP 是三层里最靠内的那一层，粒度最细"
      }
    ]
  },
  {
    "id": "sb-embedded-tomcat",
    "domain": "求职·Java",
    "topicPath": [
      "SpringBoot",
      "核心原理",
      "内嵌容器"
    ],
    "title": "SpringBoot 为什么不需要外置 Tomcat",
    "oneLine": "把容器做成一个 Bean，随refresh 启动——它不是外部配上来的，是被 spring 管理的对象",
    "analogy": "传统项目是租房：先有房子（外置容器）再往里搬家具；Boot 是房车：家具装好，车一发动整套就跑起来了",
    "why": "理解它可以解释端口nginx配置、为什么能打成 jar 直接跑、以及优雅关闭怎么实现",
    "mechanism": [
      "① 引入 spring-boot-starter-web，随之带入 spring-boot-starter-tomcat",
      "② ServletWebServerFactoryAutoConfiguration 在条件装配下注册 TomcatServletWebServerFactory",
      "③ ServletWebServerApplicationContext.onRefresh() 调用 createWebServer()",
      "④ 工厂创建 Tomcat 实例，配置 Connector（默认 8080）、添加 Context 与 Servlet",
      "⑤ 包装成 WebServer 并启动（非阻塞方式监听端口）",
      "⑥ finishRefresh 时发布 WebServerInitializedEvent，此时应用对外可用",
      "⑦ 容器关闭时调用 WebServer.stop 与 destroy，配合 graceful shutdown 处理未完成请求"
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "引入 starter",
        "注册容器工厂",
        "onRefresh 回调",
        "创建 Tomcat",
        "listen 端口",
        "就绪对外服务"
      ],
      "frames": [
        {
          "s": 0,
          "note": "starter 只做依赖聚合，真正干活的是对应的 autoconfigure 模块"
        },
        {
          "s": 1,
          "note": "换 Undertow / Jetty 就是替换这里的工厂实现"
        },
        {
          "s": 2,
          "note": "注意时机：这是 refresh 过程内部的一步，不是 run 方法末尾"
        },
        {
          "s": 3,
          "note": "ServerProperties 里的配置项（端口、线程数）在这一步生效"
        },
        {
          "s": 4,
          "note": "端口绑定失败会在这一步抛异常导致启动中断"
        },
        {
          "s": 5,
          "note": "在此之前 Runner 尚未执行，流量进来时可能还有 Bean 未完全预热"
        }
      ]
    },
    "interviewQ": [
      "如何优雅停机？（配置 server.shutdown=graceful 与 spring.lifecycle.timeout-per-shutdown-phase）",
      "怎么换成 Undertow？（排除 tomcat starter，引入 undertow starter）"
    ],
    "keywords": [
      "内嵌Tomcat",
      "WebServerFactory",
      "优雅关闭",
      "端口",
      "jar部署"
    ],
    "scene": [
      "Docker 部署：容器通常只给 1~2 核，默认 200 个工作线程配 JVM 堆一起看，线程数不调等于白限资源",
      "滚动发布：配 server.shutdown=graceful 加 timeout-per-shutdown-phase，让存量请求处理完再下线，用户无感发版",
      "同机多实例：启动参数加 --server.port=8081 即可，命令行参数优先级高于配置文件，不用改任何代码"
    ],
    "tags": [
      "高频"
    ],
    "category": "work",
    "subject": "java",
    "related": [
      {
        "id": "sb-startup",
        "kind": "prereq",
        "note": "容器的启动是启动流程的一步，脱离流程看没有意义"
      },
      {
        "id": "sb-mvc-flow",
        "kind": "extends",
        "note": "容器起来后才有请求链路可走"
      }
    ]
  }
];

if (typeof module !== "undefined") { module.exports = CARDS_SPRINGBOOT; }
