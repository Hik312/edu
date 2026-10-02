// Java 后端面试题扩充（JavaGuide 单主题/MySQL/分布式/MQ/高可用/Spring，8B 生成 + 对齐自检）：115 张
var CARDS_INTERVIEW_JAVA = 
[
  {
    "id": "java-bigdecimal",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "Java",
      "Java 基础"
    ],
    "title": "BigDecimal 详解",
    "oneLine": "BigDecimal 是 Java 中用于高精度小数运算的类，解决浮点数精度丢失问题，适用于金融计算等场景。",
    "analogy": "就像用精确的秤称重，而不是用粗略的估算，BigDecimal 确保小数运算不丢失精度。",
    "why": "浮点数在计算机中以二进制存储，许多十进制小数无法精确表示，导致精度丢失。例如 0.2 转换为二进制会无限循环，只能舍入，因此无法保证计算结果的准确性。使用 BigDecimal 可以精确表示十进制数，避免这种问题，尤其在涉及金额等高精度场景时至关重要。",
    "mechanism": [
      "BigDecimal 是 Java 中用于高精度小数运算的类，它通过存储十进制数的整数部分和小数部分，避免了浮点数的精度丢失问题。",
      "在创建 BigDecimal 对象时，推荐使用 `BigDecimal(String val)` 或 `BigDecimal.valueOf(double val)` 方法，以防止浮点数转换时的精度丢失。",
      "使用 `add`、`subtract`、`multiply` 和 `divide` 方法进行加减乘除运算，其中 `divide` 方法需要指定精度和舍入模式，否则可能抛出 ArithmeticException 异常。",
      "`compareTo` 方法用于比较两个 BigDecimal 对象的大小，返回 -1、0 或 1，而 `equals` 方法会同时比较数值和精度，可能导致不准确的等值判断。",
      "通过 `setScale` 方法可以设置保留的小数位数和舍入规则，如 `RoundingMode.HALF_UP` 用于四舍五入。",
      "在金融计算等高精度场景中，使用 BigDecimal 能确保计算结果的准确性，避免因浮点数精度丢失导致的错误。",
      "使用 `RoundingMode` 枚举可以指定不同的舍入规则，如 `UP`、`DOWN`、`HALF_UP` 等，以满足不同业务需求。",
      "在实际开发中，应避免使用 `==` 或 `equals` 比较 BigDecimal 对象，而应使用 `compareTo` 方法进行等值判断。"
    ],
    "keywords": [
      "BigDecimal",
      "浮点数精度",
      "小数运算",
      "RoundingMode舍入模式",
      "BigDecimal比较",
      "金额计算",
      "精度丢失"
    ],
    "scene": [
      "金融系统中计算金额，如银行转账、股票交易等，需要确保计算结果的准确性。",
      "电商系统中处理订单金额，避免因浮点数精度丢失导致的结算错误。",
      "科学计算中需要高精度的小数运算，如物理模拟、工程计算等。"
    ],
    "interviewQ": [
      "为什么不能使用 float 或 double 进行高精度小数运算？（答：float 和 double 是二进制浮点数，无法精确表示所有十进制小数，导致精度丢失。）",
      "如何正确创建 BigDecimal 对象以避免精度丢失？（答：使用 `BigDecimal(String val)` 或 `BigDecimal.valueOf(double val)` 方法创建对象，避免直接使用浮点数构造函数。）",
      "BigDecimal 的 divide 方法如何处理除不尽的情况？（答：需要指定精度和舍入模式，否则会抛出 ArithmeticException 异常。）"
    ],
    "related": [
      {
        "id": "java-proxy",
        "kind": "compare",
        "note": "代理模式用于扩展功能，BigDecimal 用于高精度计算，两者都涉及 Java 的高级特性"
      },
      {
        "id": "java-generics-and-wildcards",
        "kind": "compare",
        "note": "泛型和 BigDecimal 都是 Java 的高级特性，用于增强类型安全和精度控制"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "创建对象",
        "运算操作",
        "结果控制"
      ],
      "frames": [
        {
          "s": 0,
          "note": "使用字符串或 valueOf 创建，避免浮点数精度丢失"
        },
        {
          "s": 1,
          "note": "除法需指定精度和舍入模式，否则抛异常"
        },
        {
          "s": 2,
          "note": "setScale 设置小数位数，RoundingMode 控制四舍五入"
        }
      ]
    }
  },
  {
    "id": "java-generics-and-wildcards",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "Java",
      "Java 基础"
    ],
    "title": "泛型&通配符详解",
    "oneLine": "泛型是Java中用于增强类型安全和代码复用的机制，通配符用于解决泛型协变问题，PECS原则指导泛型的读写。",
    "analogy": "泛型就像超市货架的分类标签，确保每个货架只放特定商品；通配符就像临时借用标签，允许灵活使用；PECS原则就像进货和出货的规则，确保商品正确流转。",
    "why": "泛型的引入解决了Java早期类型安全问题，避免了强制类型转换错误。通配符解决了泛型无法协变的问题，使泛型更灵活。PECS原则帮助开发者正确使用泛型读写，避免类型错误。泛型擦除机制确保了与旧版本Java的兼容性，同时保持类型安全。",
    "mechanism": [
      "泛型是Java 5 引入的机制，用于在编译时进行类型检查，确保类型安全，避免运行时错误。通过泛型，可以定义可以处理多种数据类型的类、接口和方法。",
      "泛型通过类型擦除实现，编译器在编译期间将泛型参数替换为Object或其限定类型。运行时泛型信息被保留，但无法直接访问，通过反射API可以读取。",
      "通配符（?）用于泛型方法的参数和返回值，允许类型参数变化，解决泛型无法协变的问题。无界通配符（?）可以接收任何泛型类型，用于不依赖具体类型参数的方法。",
      "上界通配符（? extends T）表示类型实参必须是指定类型或其子类型，允许读取为T类型，但不能写入（除null外）。下界通配符（? super T）表示类型实参必须是指定类型或其父类型，允许写入T类型，但读取只能视为Object。",
      "PECS原则（Producer Extends, Consumer Super）指导泛型的读写：从数据结构中取元素时使用上界通配符（extends），向数据结构中写元素时使用下界通配符（super）。",
      "泛型方法通过定义泛型参数（如E）来实现，可以在方法中使用泛型参数进行类型操作。泛型接口和泛型类通过定义泛型参数来实现通用性。",
      "泛型的限制包括不能实例化泛型参数、不能使用基本类型、不能使用instanceof进行类型判断等，这些都是由于类型擦除机制导致的。"
    ],
    "keywords": [
      "Java泛型",
      "通配符",
      "类型擦除",
      "泛型边界",
      "PECS原则",
      "泛型方法",
      "上界下界通配符",
      "泛型接口"
    ],
    "scene": [
      "自定义接口通用返回结果CommonResult通过泛型T动态指定结果数据类型",
      "Excel处理类ExcelUtil用于动态指定Excel导出的数据类型",
      "构建集合工具类，如Collections中的sort和binarySearch方法"
    ],
    "interviewQ": [
      "泛型擦除机制是什么？为什么要擦除？（答：泛型擦除是将泛型参数在运行时替换为Object或其限定类型，确保与旧版本Java兼容，同时保持类型安全。）",
      "什么是桥方法？为什么需要它？（答：桥方法是编译器自动生成的方法，用于继承泛型类时保持多态，解决泛型擦除导致的方法重写问题。）",
      "PECS原则是什么？如何应用？（答：PECS原则是Producer Extends, Consumer Super，从数据结构取元素用extends，写元素用super，如List<? extends Number>用于读取，List<? super Integer>用于写入。）",
      "泛型有哪些限制？为什么？（答：泛型限制包括不能实例化泛型参数、不能使用基本类型、不能使用instanceof等，这些限制是由于类型擦除机制导致的。）"
    ],
    "related": [
      {
        "id": "java-bigdecimal",
        "kind": "compare",
        "note": "泛型和 BigDecimal 都是 Java 的高级特性，用于增强类型安全和精度控制"
      },
      {
        "id": "java-proxy",
        "kind": "compare",
        "note": "代理模式用于扩展功能，泛型用于类型安全，两者都涉及 Java 的高级特性"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "泛型",
          "lines": [
            "Java 5 引入的类型安全机制",
            "编译时类型检查，避免运行时错误",
            "类型擦除实现，运行时不可直接访问",
            "不能实例化泛型参数，不能用基本类型"
          ]
        },
        {
          "title": "通配符",
          "lines": [
            "用于解决泛型协变问题",
            "无界通配符（?）接收任意泛型类型",
            "上界通配符（? extends T）允许读取T类型",
            "下界通配符（? super T）允许写入T类型"
          ]
        },
        {
          "title": "PECS原则",
          "lines": [
            "Producer Extends：读取用上界通配符",
            "Consumer Super：写入用下界通配符",
            "指导泛型方法的参数和返回值设计",
            "适用于集合类的读写操作"
          ]
        }
      ],
      "frames": [
        {
          "note": "泛型通过类型擦除实现，运行时无法直接访问泛型信息，但可通过反射读取。",
          "active": [
            0
          ]
        },
        {
          "note": "通配符（?）允许泛型参数变化，解决类型协变问题，提升泛型灵活性。",
          "active": [
            1
          ]
        },
        {
          "note": "PECS原则指导泛型的读写：读取用上界通配符，写入用下界通配符，确保类型安全。",
          "active": [
            2
          ]
        }
      ]
    }
  },
  {
    "id": "java-proxy",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "Java",
      "Java 基础"
    ],
    "title": "Java 代理模式详解",
    "oneLine": "代理模式通过代理对象扩展目标对象功能，支持在方法执行前后添加自定义操作。",
    "analogy": "就像快递员通过快递站分拣包裹，代理对象在真实对象执行前后进行拦截和处理。",
    "why": "代理模式解决了直接修改目标对象的局限性，允许在不改变原有逻辑的情况下增强功能。静态代理因需手动为每个方法增强而不够灵活，动态代理则通过运行时生成代理类实现更高效的扩展，尤其适用于框架开发和AOP实现。",
    "mechanism": [
      "代理模式是一种设计模式，通过代理对象替代对真实对象的直接访问，允许在不修改目标对象的前提下扩展功能。",
      "静态代理需要手动为每个目标方法编写增强逻辑，导致接口新增方法时需同步修改代理类，灵活性差且维护成本高。",
      "动态代理通过运行时生成代理类，避免手动编写代理类，支持对实现类或接口的动态增强，提升代码复用和扩展性。",
      "JDK动态代理依赖`InvocationHandler`接口和`Proxy`类，通过`newProxyInstance()`方法生成代理对象，调用方法时实际执行`invoke()`方法。",
      "`invoke()`方法接收代理对象、方法对象和参数数组，允许在方法执行前后插入自定义逻辑，如日志记录或权限校验。",
      "CGLIB代理通过继承目标类生成子类实现增强，适用于没有接口的类，但需要额外的字节码处理库支持。",
      "Spring AOP和RPC框架依赖动态代理实现横切关注点，如事务管理、日志记录和远程调用，提升系统模块化和可维护性。"
    ],
    "keywords": [
      "Java代理模式",
      "静态代理",
      "动态代理",
      "JDK动态代理",
      "CGLIB代理",
      "AOP"
    ],
    "scene": [
      "Spring框架中使用JDK动态代理实现AOP，增强业务逻辑的事务管理与日志记录。",
      "RPC框架中通过动态代理实现远程调用，隐藏网络通信细节，提升代码可维护性。",
      "测试工具中使用代理模式拦截方法调用，实现Mock对象的动态生成和行为控制。"
    ],
    "interviewQ": [
      "追问1：静态代理和动态代理的区别是什么？（答：静态代理需手动为每个方法增强，灵活性差；动态代理在运行时生成代理类，支持接口和实现类增强，更灵活。）",
      "追问2：JDK动态代理和CGLIB代理的实现原理有何不同？（答：JDK动态代理基于接口生成代理类，CGLIB通过继承目标类生成子类，适用于无接口的类。）",
      "追问3：为什么Spring AOP默认使用JDK动态代理？（答：Spring AOP优先使用JDK动态代理，因为其基于接口实现，符合Spring的面向接口编程原则，但对无接口类使用CGLIB。）"
    ],
    "related": [
      {
        "id": "java-bigdecimal",
        "kind": "compare",
        "note": "代理模式用于扩展功能，BigDecimal 用于高精度计算，两者都涉及 Java 的高级特性"
      },
      {
        "id": "java-generics-and-wildcards",
        "kind": "compare",
        "note": "代理模式用于扩展功能，泛型用于类型安全，两者都涉及 Java 的高级特性"
      },
      {
        "id": "java-reflection",
        "kind": "compare",
        "note": "代理模式依赖反射实现动态代理，两者都涉及运行时动态操作"
      },
      {
        "id": "java-serialization",
        "kind": "compare",
        "note": "代理模式与序列化都涉及运行时动态操作，有交互"
      },
      {
        "id": "java-spi",
        "kind": "compare",
        "note": "代理模式与 SPI 都涉及运行时动态加载，有交互"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "创建代理对象",
        "调用目标方法",
        "执行增强逻辑"
      ],
      "frames": [
        {
          "s": 0,
          "note": "创建代理对象时，需要指定目标对象和增强逻辑，如日志记录或权限校验。"
        },
        {
          "s": 1,
          "note": "调用目标方法时，实际执行的是代理对象的 invoke 方法，将方法调用转发给目标对象。"
        },
        {
          "s": 2,
          "note": "执行增强逻辑时，可以在方法执行前后插入自定义操作，如记录日志或进行权限校验。"
        }
      ]
    }
  },
  {
    "id": "java-reflection",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "Java",
      "Java 基础"
    ],
    "title": "Java 反射机制详解",
    "oneLine": "Java 反射机制允许在运行时获取类信息并操作类成员，是框架实现动态功能的核心技术。",
    "analogy": "就像在图书馆里，你可以通过书架编号找到任意一本书，反射机制让你在运行时找到并操作任意类的方法和字段。",
    "why": "反射机制之所以重要，是因为它打破了编译时的限制，让程序在运行时也能动态分析和操作类。传统编程中，类的结构和方法在编译时就已经确定，无法灵活调整。而反射提供了运行时的灵活性，使得框架如 Spring、MyBatis 能够动态加载和处理类，实现依赖注入、AOP 等高级功能。同时，它也是注解实现的基础，让开发者可以通过注解标记类、方法和字段，再通过反射读取这些信息。",
    "mechanism": [
      "反射机制是 Java 提供的一种在运行时分析和操作类的能力，通过 Class 类获取类的信息，如字段、方法、构造器等。",
      "反射通过 Class 对象获取类的元数据，包括类名、包名、父类、接口、注解等信息，这些信息在运行时仍然可用。",
      "通过反射可以访问类的私有成员，例如私有字段和私有方法，这需要通过 setAccessible(true) 方法取消访问控制。",
      "反射可以动态创建类的实例，通过 Class 对象调用 newInstance() 方法或使用 Constructor 类进行实例化。",
      "反射可以调用类的方法，无论是 public、protected 还是 private 方法，都需要通过 Method 类的 invoke 方法实现。",
      "反射可以读取和修改类的字段值，通过 Field 类的 get() 和 set() 方法实现，同样需要取消访问控制。",
      "反射支持动态加载类，通过 Class.forName() 方法传入类的全限定名，实现运行时加载类。",
      "反射在框架中被广泛使用，如 Spring 的依赖注入、MyBatis 的 SQL 映射、JDK 动态代理等，都依赖反射实现动态行为。"
    ],
    "keywords": [
      "Java反射",
      "反射机制",
      "Class类",
      "Method方法",
      "Field字段",
      "动态代理",
      "框架原理",
      "运行时操作"
    ],
    "scene": [
      "Spring 框架通过反射扫描类上的注解，将类注册为 Bean，实现依赖注入。",
      "MyBatis 使用反射动态获取 SQL 映射信息，根据传入的参数执行对应的 SQL 语句。",
      "JDK 动态代理通过反射创建代理对象，拦截方法调用，实现 AOP 功能。"
    ],
    "interviewQ": [
      "反射机制有哪些应用场景？（答：反射用于框架实现动态功能，如 Spring 的依赖注入、MyBatis 的 SQL 映射、JDK 动态代理等。）",
      "反射的优缺点是什么？（答：优点是灵活性强，支持运行时操作类；缺点是性能较低，存在安全风险，如可以绕过泛型检查。）",
      "如何获取 Class 对象？（答：可以通过 TargetObject.class、Class.forName()、instance.getClass()、ClassLoader.loadClass() 四种方式获取。）"
    ],
    "related": [
      {
        "id": "java-spi",
        "kind": "compare",
        "note": "SPI 通过反射实现服务发现，两者都涉及运行时动态加载"
      },
      {
        "id": "java-proxy",
        "kind": "compare",
        "note": "代理模式依赖反射实现动态代理，两者都涉及运行时动态操作"
      },
      {
        "id": "java-why-there-only-value-passing-in-java",
        "kind": "compare",
        "note": "值传递影响反射操作对象时的行为，两者有运行时交互"
      },
      {
        "id": "java-syntactic-sugar",
        "kind": "compare",
        "note": "语法糖提升可读性，反射则实现底层动态操作，两者互补"
      },
      {
        "id": "java-serialization",
        "kind": "compare",
        "note": "序列化涉及对象状态，反射涉及对象结构，两者在运行时交互"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "获取类信息",
        "操作类成员",
        "动态创建实例",
        "调用方法/字段"
      ],
      "frames": [
        {
          "s": 0,
          "note": "通过 Class 对象获取类的元数据，如字段、方法、构造器等信息，是反射的基础操作。"
        },
        {
          "s": 1,
          "note": "使用 setAccessible(true) 取消访问控制，可访问私有字段和私有方法，存在安全风险。"
        },
        {
          "s": 2,
          "note": "通过 Constructor 实例化对象，相比 new 关键字更灵活，但需处理异常和性能开销。"
        },
        {
          "s": 3,
          "note": "Method.invoke() 调用方法时需传入目标对象和参数，支持动态调用任意访问权限的方法。"
        }
      ]
    }
  },
  {
    "id": "java-serialization",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "Java",
      "Java 基础"
    ],
    "title": "Java 序列化详解",
    "oneLine": "Java 序列化是将对象转换为字节流以实现持久化或网络传输，反序列化则恢复对象状态。",
    "analogy": "就像把一本书的内容压缩成电子书，方便存储和传输，读取时再解压恢复原内容。",
    "why": "Java 是面向对象语言，对象包含复杂结构，无法直接存储或传输。序列化将对象状态转换为二进制流，便于持久化、网络传输或跨系统共享。反序列化则恢复对象状态，确保数据完整性。JDK 提供的序列化虽简单，但效率低且存在安全风险，因此常使用其他高性能协议如 Kryo。",
    "mechanism": [
      "序列化是将对象状态转换为二进制流，以便存储或传输。Java 中通过实现 Serializable 接口实现，JVM 会自动处理对象的序列化和反序列化。",
      "反序列化是将二进制流恢复为对象状态，确保对象在不同环境中保持一致性。反序列化时会检查 serialVersionUID 是否匹配，防止版本不兼容导致的错误。",
      "serialVersionUID 是版本控制标识，用于反序列化时验证类的版本一致性。若不一致，会抛出 InvalidClassException，避免数据损坏。",
      "transient 关键字用于标记不需序列化的字段，反序列化时这些字段会被初始化为默认值，如 int 类型置为 0。",
      "Kryo 是高性能的序列化框架，通过字节码生成和变长存储实现高效序列化，适用于需要跨语言调用和高性能的场景。",
      "序列化协议属于 TCP/IP 应用层，负责数据格式转换，确保通信双方使用相同协议进行数据交换。",
      "序列化常用于网络传输、对象持久化、缓存存储等场景，如 RPC 调用、Redis 缓存等。",
      "JDK 序列化存在性能低、跨语言不支持、安全风险等问题，因此在实际开发中较少直接使用，而选择其他更高效的协议。"
    ],
    "keywords": [
      "Java序列化",
      "反序列化",
      "Serializable接口",
      "transient关键字",
      "serialVersionUID",
      "序列化协议"
    ],
    "scene": [
      "网络传输中，RPC 调用前需要将对象序列化为二进制流，接收方再反序列化恢复对象。",
      "将对象存储到 Redis 缓存时，需先序列化为字节流，读取时再反序列化还原对象。",
      "序列化用于跨系统数据交换，如微服务间通信，确保数据格式一致性和兼容性。"
    ],
    "interviewQ": [
      "追问1：为什么推荐使用 Kryo 而不是 JDK 自带的序列化？（答：Kryo 性能更高，支持跨语言调用，且更安全，适用于高性能场景。）",
      "追问2：transient 关键字的作用是什么？（答：transient 修饰的字段不会被序列化，反序列化时会被初始化为默认值。）",
      "追问3：serialVersionUID 的作用是什么？（答：serialVersionUID 用于版本控制，反序列化时验证类的版本一致性，防止版本不匹配导致的错误。）"
    ],
    "related": [
      {
        "id": "java-spi",
        "kind": "compare",
        "note": "SPI 服务发现与序列化都涉及运行时动态加载，有交互"
      },
      {
        "id": "java-why-there-only-value-passing-in-java",
        "kind": "compare",
        "note": "值传递影响序列化对象状态，两者有运行时交互"
      },
      {
        "id": "java-proxy",
        "kind": "compare",
        "note": "代理模式与序列化都涉及运行时动态操作，有交互"
      },
      {
        "id": "java-syntactic-sugar",
        "kind": "compare",
        "note": "语法糖提升可读性，序列化涉及底层对象状态，两者互补"
      },
      {
        "id": "java-reflection",
        "kind": "compare",
        "note": "反射可操作序列化对象，两者都涉及运行时动态处理"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "标记序列化",
        "转换二进制流",
        "验证版本",
        "恢复对象状态"
      ],
      "frames": [
        {
          "s": 0,
          "note": "标记序列化：通过实现 Serializable 接口，JVM 会自动处理对象的序列化过程。"
        },
        {
          "s": 1,
          "note": "转换二进制流：对象状态被转换为字节流，便于存储或传输，如网络传输或持久化。"
        },
        {
          "s": 2,
          "note": "验证版本：反序列化时检查 serialVersionUID 是否匹配，防止版本不兼容导致的错误。"
        },
        {
          "s": 3,
          "note": "恢复对象状态：反序列化将字节流恢复为对象，确保在不同环境中保持一致性，如 Redis 缓存恢复。"
        }
      ]
    }
  },
  {
    "id": "java-spi",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "Java",
      "Java 基础"
    ],
    "title": "Java SPI 机制详解",
    "oneLine": "Java SPI 是一种服务发现机制，允许程序外部动态指定具体实现，实现接口与实现解耦。",
    "analogy": "就像超市的货架，顾客可以自由选择商品，无需超市提前准备所有商品，只需提供货架分类规则。",
    "why": "Java 类加载机制采用双亲委派模型，限制了核心库加载第三方实现。SPI 机制允许核心库定义接口，第三方提供实现，从而实现动态加载和扩展。这解决了直接依赖具体实现导致的耦合问题，提高了程序的扩展性和可维护性。",
    "mechanism": [
      "SPI 即 Service Provider Interface，是 Java 提供的一种服务发现机制，允许程序在运行时动态发现并加载实现类。",
      "SPI 通过在类路径下 `META-INF/services` 目录中定义接口的全类名文件，文件内容为实现类的全类名，实现类可以有多个，用换行分隔。",
      "调用 `ServiceLoader.load()` 会创建服务加载器，遍历类路径下的服务配置文件，按需定位并实例化提供者。",
      "加载器会缓存已加载的提供者，调用 `stream()` 时得到的是 `ServiceLoader.Provider` 流，通过 `type()` 检查提供者类型，调用 `Provider.get()` 获取实例。",
      "SPI 机制解决了 Java 类加载体系中双亲委派模型的限制，允许第三方开发者提供实现类并部署，程序运行时动态发现并加载。",
      "SPI 机制在 JDBC 驱动加载、日志框架、Dubbo 扩展等场景中广泛应用，实现了接口与实现的解耦。",
      "SPI 机制与 API 不同，API 是接口和实现都在实现方，而 SPI 是接口在调用方，实现方根据接口规则提供实现。"
    ],
    "keywords": [
      "Java SPI",
      "SPI机制",
      "ServiceLoader",
      "服务发现",
      "插件化",
      "JDBC驱动加载",
      "Dubbo扩展"
    ],
    "scene": [
      "JDBC 4.0 及之后版本利用 SPI 自动发现和加载数据库驱动，开发者只需将驱动 JAR 包放置在类路径下即可。",
      "日志框架如 SLF4J 利用 SPI 实现日志门面，支持切换具体实现如 Logback、Log4j 等。",
      "Dubbo 框架使用 SPI 实现扩展机制，支持动态加载插件和扩展点。"
    ],
    "interviewQ": [
      "追问1：SPI 机制和 API 有什么区别？（答：API 是接口和实现都在实现方，而 SPI 是接口在调用方，实现方根据接口规则提供实现。）",
      "追问2：SPI 机制在实际开发中有哪些应用场景？（答：JDBC 驱动加载、日志框架、Dubbo 扩展等场景中广泛应用。）",
      "追问3：SPI 机制是如何实现服务发现的？（答：通过在类路径下 `META-INF/services` 目录中定义接口的全类名文件，文件内容为实现类的全类名，实现类可以有多个，用换行分隔。）"
    ],
    "related": [
      {
        "id": "java-reflection",
        "kind": "prereq",
        "note": "反射是 SPI 实现服务发现的底层技术，理解反射有助于理解 SPI"
      },
      {
        "id": "java-serialization",
        "kind": "compare",
        "note": "序列化与 SPI 都涉及运行时动态加载，有交互"
      },
      {
        "id": "java-why-there-only-value-passing-in-java",
        "kind": "compare",
        "note": "值传递影响 SPI 服务加载时对象状态，两者有运行时交互"
      },
      {
        "id": "java-proxy",
        "kind": "compare",
        "note": "代理模式与 SPI 都涉及运行时动态加载，有交互"
      },
      {
        "id": "java-syntactic-sugar",
        "kind": "compare",
        "note": "语法糖提升可读性，SPI 涉及底层动态加载，两者互补"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "定义服务接口",
        "配置实现类",
        "加载并实例化"
      ],
      "frames": [
        {
          "s": 0,
          "note": "定义接口时需在 `META-INF/services` 下创建同名文件，文件内容为实现类全限定名，支持多实现类用换行分隔。"
        },
        {
          "s": 1,
          "note": "调用 `ServiceLoader.load()` 会遍历类路径下的服务配置文件，按需定位并实例化提供者，支持缓存已加载的提供者。"
        },
        {
          "s": 2,
          "note": "通过 `Provider.get()` 获取实例时，会校验类型一致性，确保实例符合接口定义，实现接口与实现的解耦。"
        }
      ]
    }
  },
  {
    "id": "java-syntactic-sugar",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "Java",
      "Java 基础"
    ],
    "title": "Java 语法糖详解",
    "oneLine": "Java 语法糖是编译器在编译阶段将高级语法转换为 JVM 能识别的基础语法，提升可读性但不改变运行时行为。",
    "analogy": "就像超市里的糖衣药丸，外表好看但药效不变，Java 语法糖让代码更简洁，但底层逻辑还是基础语法。",
    "why": "Java 语法糖的出现是为了简化开发者的编码过程，提高代码的可读性和可维护性。虽然 JVM 不支持这些语法糖，但编译器会在编译阶段将其转换为 JVM 可识别的基础语法。这样开发者可以更专注于业务逻辑，而不必担心底层实现细节。同时，语法糖的使用也避免了重复代码，提高了开发效率。",
    "mechanism": [
      "语法糖是指在编程语言中添加的某种语法，这种语法对语言的功能没有影响，但更方便程序员使用。Java 中的语法糖如自动装箱、泛型、Lambda 表达式等，都是在编译阶段被转换为 JVM 可识别的基础语法。",
      "Java 编译器在编译阶段会调用 `desugar()` 方法来解语法糖，将高级语法转换为基础语法。例如，`switch` 支持 `String` 会被转换为 `hashCode()` 分派和 `equals()` 校验。",
      "泛型在 Java 中通过类型擦除实现，编译器会将泛型参数替换为最左边界类型，并移除类型参数。这样 JVM 就无法识别泛型类型，但编译器会确保类型安全。",
      "自动装箱和拆箱是 Java 提供的特性，允许原始类型和其对应的包装类之间自动转换。装箱过程调用 `valueOf()` 方法，拆箱过程调用 `xxxValue()` 方法。",
      "可变参数（varargs）允许方法接收任意数量的参数，编译器会将这些参数转换为数组。在反编译时，可变参数会被转换为数组类型。",
      "Lambda 表达式在编译时会被转换为内部类或匿名类，编译器会生成一个合成类来实现 Lambda 表达式的逻辑。",
      "枚举在 Java 中是通过类实现的，每个枚举常量都是该类的实例，编译器会为枚举生成一个私有构造函数和一个静态初始化块。",
      "增强 for 循环（for-each）是 Java 5 引入的特性，它简化了集合的遍历操作。编译器会将增强 for 循环转换为传统的 for 循环，使用迭代器进行遍历。"
    ],
    "keywords": [
      "Java语法糖",
      "自动装箱拆箱",
      "泛型擦除",
      "增强for循环",
      "可变参数",
      "枚举",
      "Lambda表达式",
      "语法糖原理"
    ],
    "scene": [
      "在开发中使用泛型时，需要避免类型擦除带来的类型安全问题，例如在运行时无法获取泛型类型信息。",
      "使用 Lambda 表达式时，需要注意其在编译时生成的内部类可能会影响性能，尤其是在频繁创建 Lambda 表达式的情况下。",
      "在使用 `switch` 语句处理 `String` 时，需要注意其性能不如枚举或整数常量，因为需要进行哈希值分派和 `equals()` 校验。"
    ],
    "interviewQ": [
      "为什么 Java 中的泛型不被 JVM 支持？（答：泛型通过类型擦除实现，编译器在编译阶段移除类型参数，JVM 无法识别泛型类型。）",
      "Lambda 表达式在编译时如何实现？（答：Lambda 表达式在编译时被转换为内部类或匿名类，编译器生成一个合成类来实现 Lambda 表达式的逻辑。）",
      "自动装箱和拆箱是如何实现的？（答：装箱过程调用 `valueOf()` 方法，拆箱过程调用 `xxxValue()` 方法，例如 `Integer.valueOf()` 和 `intValue()`。）"
    ],
    "related": [
      {
        "id": "java-why-there-only-value-passing-in-java",
        "kind": "compare",
        "note": "值传递影响语法糖的编译行为，两者有编译时交互"
      },
      {
        "id": "java-serialization",
        "kind": "compare",
        "note": "序列化与语法糖都涉及编译时转换，有交互"
      },
      {
        "id": "java-spi",
        "kind": "compare",
        "note": "SPI 与语法糖都涉及编译时转换，有交互"
      },
      {
        "id": "java-reflection",
        "kind": "compare",
        "note": "反射与语法糖都涉及编译时转换，有交互"
      },
      {
        "id": "java-proxy",
        "kind": "compare",
        "note": "代理模式与语法糖都涉及编译时转换，有交互"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "典型语法糖",
          "lines": [
            "自动装箱拆箱",
            "泛型擦除",
            "Lambda表达式",
            "增强for循环"
          ]
        },
        {
          "title": "编译器处理",
          "lines": [
            "desugar()方法转换",
            "类型擦除实现泛型",
            "生成内部类实现Lambda",
            "转换为迭代器实现增强for"
          ]
        },
        {
          "title": "注意事项",
          "lines": [
            "泛型运行时丢失类型",
            "Lambda可能影响性能",
            "String switch性能较低",
            "避免频繁创建Lambda"
          ]
        }
      ],
      "frames": [
        {
          "note": "泛型通过类型擦除实现，运行时无法获取类型信息",
          "active": [
            1
          ]
        },
        {
          "note": "Lambda表达式编译后生成内部类，可能影响性能",
          "active": [
            2
          ]
        },
        {
          "note": "String switch通过hashCode和equals实现，性能不如枚举",
          "active": [
            0
          ]
        }
      ]
    }
  },
  {
    "id": "java-why-there-only-value-passing-in-java",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "Java",
      "Java 基础"
    ],
    "title": "Java 值传递详解",
    "oneLine": "Java 只有值传递，参数传递时传递的是值的副本，不会影响原数据。",
    "analogy": "就像把一杯水倒进另一个杯子，新杯子的水变化不会影响原杯子。",
    "why": "Java 采用值传递是为了保证数据安全和程序稳定性。如果允许引用传递，方法内部对参数的修改可能会直接影响到外部变量，导致难以追踪的错误。值传递通过复制值，确保方法内部的修改不会影响到外部数据，提高程序的可预测性和安全性。此外，值传递机制使得 Java 在多线程编程中能够避免数据竞争问题，确保程序的健壮性。",
    "mechanism": [
      "值传递是 Java 中参数传递的机制，传递的是实参值的副本，不会影响原数据。",
      "对于基本类型参数，传递的是值的拷贝，方法内部对形参的修改不会影响到实参。",
      "对于引用类型参数，传递的是对象引用的拷贝，形参和实参指向同一个对象，因此对对象内容的修改会影响到实参。",
      "虽然引用类型传递的是引用的拷贝，但形参和实参指向同一个对象，因此对对象的修改会影响实参。",
      "在案例 2 中，change 方法的参数拷贝的是 arr 中保存的引用值，因此形参和 arr 指向同一个数组对象，修改数组内容会影响实参。",
      "在案例 3 中，swap 方法的参数拷贝的是 xiaoZhang 和 xiaoLi 中保存的引用值，因此交换形参的引用副本不会影响到实参。",
      "Java 的值传递机制确保了方法内部的修改不会影响到外部数据，提高程序的可预测性和安全性。",
      "值传递在 Java 中是统一的机制，无论是基本类型还是引用类型，传递的都是值的副本，只是引用类型传递的是对象引用的副本，而不是对象本身。"
    ],
    "keywords": [
      "Java值传递",
      "引用传递",
      "参数传递",
      "形参实参",
      "对象引用",
      "方法调用"
    ],
    "scene": [
      "在多线程编程中，值传递可以避免线程间数据竞争，确保每个线程操作的是独立的副本。",
      "在方法中修改对象内容时，如果传递的是引用的副本，修改会影响外部变量，因此需要谨慎处理。",
      "在交换对象引用时，如果传递的是引用的副本，交换操作不会影响到外部变量，因此需要使用其他方式实现交换。"
    ],
    "interviewQ": [
      "为什么 Java 只有值传递？（答：Java 采用值传递是为了保证数据安全和程序稳定性，避免方法内部修改参数影响外部数据，提高程序的可预测性和安全性。）",
      "如何区分基本类型和引用类型的值传递？（答：基本类型传递的是值的副本，引用类型传递的是对象引用的副本，因此对对象内容的修改会影响外部变量。）",
      "在 Java 中如何实现引用类型参数的修改影响外部变量？（答：通过传递对象引用的副本，修改对象内容，因为形参和实参指向同一个对象，因此修改会影响外部变量。）",
      "为什么在 Java 中交换对象引用不会影响外部变量？（答：交换的是形参中保存的引用副本，不会改变实参中保存的引用，因此不会影响外部变量。）"
    ],
    "related": [
      {
        "id": "java-syntactic-sugar",
        "kind": "compare",
        "note": "语法糖影响值传递的可读性，两者有编译时交互"
      },
      {
        "id": "java-serialization",
        "kind": "compare",
        "note": "序列化与值传递都涉及运行时对象状态，有交互"
      },
      {
        "id": "java-reflection",
        "kind": "compare",
        "note": "反射与值传递都涉及运行时对象状态，有交互"
      },
      {
        "id": "java-spi",
        "kind": "compare",
        "note": "SPI 与值传递都涉及运行时对象状态，有交互"
      },
      {
        "id": "java-proxy",
        "kind": "compare",
        "note": "代理模式与值传递都涉及运行时对象状态，有交互"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "基本类型",
          "lines": [
            "传递值的副本，修改不影响原数据",
            "方法内修改形参不会影响实参",
            "适用于int, float, boolean等"
          ]
        },
        {
          "title": "引用类型",
          "lines": [
            "传递引用的副本，指向同一对象",
            "修改对象内容会影响实参",
            "适用于对象、数组等引用类型"
          ]
        },
        {
          "title": "注意事项",
          "lines": [
            "交换引用副本不会改变原引用",
            "需谨慎处理对象内容修改",
            "值传递确保数据隔离与安全性"
          ]
        }
      ],
      "frames": [
        {
          "note": "基本类型传递值的副本，修改不影响原数据",
          "active": [
            0
          ]
        },
        {
          "note": "引用类型传递引用副本，修改对象内容会影响原数据",
          "active": [
            1
          ]
        },
        {
          "note": "交换引用副本不会改变原引用，需其他方式实现交换",
          "active": [
            2
          ]
        }
      ]
    }
  },
  {
    "id": "java-arraylist-source-code",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "集合"
    ],
    "tags": [
      "Java",
      "集合"
    ],
    "title": "ArrayList 源码分析",
    "oneLine": "ArrayList 是基于数组实现的动态数组，支持快速随机访问，具有动态扩容机制。",
    "analogy": "ArrayList 就像一个可以自动扩展的购物车，能装下越来越多的商品，不需要提前知道商品数量。",
    "why": "ArrayList 的设计是为了在频繁查找时提供高效的性能，同时在数据量增长时动态调整容量，避免频繁的内存分配。传统的数组在容量固定时无法扩展，而 ArrayList 通过动态扩容解决了这一问题，使得数据操作更加灵活。",
    "mechanism": [
      "ArrayList 是基于数组实现的动态数组，其底层使用 Object[] 存储元素，支持快速随机访问。",
      "当添加元素时，如果当前数组容量不足，ArrayList 会调用 grow() 方法进行扩容，扩容后的新容量是原容量的 1.5 倍。",
      "扩容过程中，会创建一个新的数组，将原数组中的元素复制到新数组中，然后将新数组的引用赋值给 elementData。",
      "ArrayList 通过 ensureCapacityInternal() 方法判断是否需要扩容，确保数组容量足够存储新元素。",
      "如果当前数组是空数组，则扩容后的容量为默认容量 10，否则扩容后的容量为原容量的 1.5 倍。",
      "ArrayList 的扩容机制可以减少频繁的内存分配，提高性能。",
      "ArrayList 支持序列化和克隆，可以通过 clone() 方法进行浅拷贝。"
    ],
    "keywords": [
      "ArrayList",
      "动态数组",
      "扩容机制",
      "RandomAccess",
      "序列化",
      "Vector"
    ],
    "scene": [
      "在需要频繁查找元素的场景中使用，如数据库查询结果缓存。",
      "在数据量不确定时使用，如用户输入的数据收集。",
      "在需要支持快速随机访问的场景中使用，如数据统计分析。"
    ],
    "interviewQ": [
      "追问1：ArrayList 的扩容机制是怎样的？（答：ArrayList 的扩容机制是当数组容量不足时，会创建一个新的数组，将原数组中的元素复制到新数组中，然后将新数组的引用赋值给 elementData，新容量是原容量的 1.5 倍。）",
      "追问2：ArrayList 和 Vector 的区别是什么？（答：ArrayList 是非线程安全的，而 Vector 是线程安全的；ArrayList 使用动态数组，而 Vector 使用数组实现，但 Vector 的扩容机制是 2 倍。）",
      "追问3：ArrayList 支持随机访问吗？（答：是的，ArrayList 实现了 RandomAccess 接口，支持快速随机访问。）"
    ],
    "related": [
      {
        "id": "java-hashmap-source-code",
        "kind": "compare",
        "note": "对比两者数据结构差异，理解集合框架设计"
      },
      {
        "id": "java-linkedlist-source-code",
        "kind": "compare",
        "note": "对比链表和数组实现的 List 差异，理解底层结构"
      },
      {
        "id": "java-concurrent-hash-map-source-code",
        "kind": "compare",
        "note": "对比线程安全和非线程安全的集合实现差异"
      },
      {
        "id": "java-arrayblockingqueue-source-code",
        "kind": "extends",
        "note": "理解 ArrayBlockingQueue 的实现依赖于 ArrayList 的结构"
      },
      {
        "id": "java-copyonwritearraylist-source-code",
        "kind": "compare",
        "note": "对比写时复制和动态扩容两种线程安全策略"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "判断扩容",
        "扩容准备",
        "数组复制",
        "引用更新"
      ],
      "frames": [
        {
          "s": 0,
          "note": "ensureCapacityInternal 判断是否需要扩容，若当前数组为空则容量设为 10，否则扩容为原容量的 1.5 倍"
        },
        {
          "s": 1,
          "note": "调用 grow() 方法创建新数组，新容量为原容量的 1.5 倍，确保新数组足够存储新元素"
        },
        {
          "s": 2,
          "note": "使用 System.arraycopy 复制原数组元素到新数组，确保数据完整性并避免内存泄漏"
        },
        {
          "s": 3,
          "note": "将新数组的引用赋值给 elementData，完成扩容并释放原数组内存，提升后续添加性能"
        }
      ]
    }
  },
  {
    "id": "java-concurrent-hash-map-source-code",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "集合"
    ],
    "tags": [
      "Java",
      "集合"
    ],
    "title": "ConcurrentHashMap 源码分析",
    "oneLine": "ConcurrentHashMap 是线程安全的 Map 实现，JDK1.7 使用分段锁 Segment，JDK1.8 使用 CAS+Synchronized 实现并发控制。",
    "analogy": "就像多个快递员同时送快递，JDK1.7 用分段锁保证每个分段独立，JDK1.8 用 CAS 确保每个操作原子化。",
    "why": "ConcurrentHashMap 需要线程安全，但又不能像 Hashtable 一样加全局锁，影响性能。JDK1.7 采用分段锁，减少锁粒度；JDK1.8 改用 CAS+Synchronized，减少锁竞争，提升并发性能。",
    "mechanism": [
      "ConcurrentHashMap 在 JDK1.7 中使用分段锁 Segment，每个 Segment 是一个类似 HashMap 的结构，通过分段锁实现并发控制。",
      "Segment 的个数在初始化时确定，不能改变，默认是 16 个，每个 Segment 有独立的锁，减少锁竞争。",
      "put 操作时，根据 key 的 hash 值计算 Segment 的位置，然后获取该 Segment 的锁，确保线程安全。",
      "初始化 Segment 时，使用 CAS 操作确保线程安全，避免多个线程同时初始化同一个 Segment。",
      "Segment 的 put 操作会先查找 key 是否存在，若存在则更新值，否则插入新节点。",
      "Segment 的扩容机制与 HashMap 类似，当元素数量超过阈值时触发扩容，保证容量和负载因子的平衡。",
      "JDK1.8 中 ConcurrentHashMap 改用 CAS+Synchronized 实现，减少锁粒度，提升并发性能。",
      "CAS 操作用于更新头节点和链表长度，确保操作的原子性，减少锁竞争。"
    ],
    "keywords": [
      "ConcurrentHashMap",
      "Segment",
      "CAS操作",
      "分段锁",
      "并发容器",
      "JDK7与JDK8区别"
    ],
    "scene": [
      "多线程环境下需要频繁读写 Map 的场景，如缓存系统。",
      "高并发的 Web 服务中，用于存储请求上下文信息。",
      "分布式系统中，用于共享数据的同步控制。"
    ],
    "interviewQ": [
      "ConcurrentHashMap 在 JDK1.7 和 JDK1.8 中的实现有什么区别？（答：JDK1.7 使用分段锁 Segment，JDK1.8 改用 CAS+Synchronized 实现，减少锁粒度，提升并发性能。）",
      "ConcurrentHashMap 的 put 操作是如何保证线程安全的？（答：JDK1.7 通过分段锁 Segment 实现，每个 Segment 有独立锁；JDK1.8 通过 CAS+Synchronized 实现，减少锁竞争。）",
      "ConcurrentHashMap 的扩容机制是怎样的？（答：当元素数量超过阈值时触发扩容，每个 Segment 独立扩容，保证线程安全。）"
    ],
    "related": [
      {
        "id": "java-arraylist-source-code",
        "kind": "prereq",
        "note": "理解 ArrayList 的实现是学习 ConcurrentHashMap 的基础"
      },
      {
        "id": "java-hashmap-source-code",
        "kind": "prereq",
        "note": "理解 HashMap 的实现是学习 ConcurrentHashMap 的基础"
      },
      {
        "id": "java-arrayblockingqueue-source-code",
        "kind": "compare",
        "note": "对比线程安全的队列与线程安全的 Map 实现"
      },
      {
        "id": "java-copyonwritearraylist-source-code",
        "kind": "compare",
        "note": "对比线程安全的 List 实现与线程安全的 Map 实现"
      },
      {
        "id": "java-java-collection-precautions-for-use",
        "kind": "extends",
        "note": "了解 ConcurrentHashMap 实现原理，能更好理解并发容器选择的注意事项"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "JDK1.7",
          "lines": [
            "分段锁 Segment 实现并发控制",
            "默认 16 个 Segment，每个独立锁",
            "put 操作需获取对应 Segment 锁",
            "CAS 初始化 Segment 避免竞争"
          ]
        },
        {
          "title": "JDK1.8",
          "lines": [
            "CAS+Synchronized 实现并发控制",
            "锁粒度更细，减少锁竞争",
            "CAS 更新头节点和链表长度",
            "无 Segment，结构更简单"
          ]
        }
      ],
      "frames": [
        {
          "note": "JDK1.7 通过分段锁降低锁竞争，但 Segment 数量固定",
          "active": [
            0
          ]
        },
        {
          "note": "JDK1.8 用 CAS+Synchronized 替代分段锁，提升并发性能",
          "active": [
            1
          ]
        },
        {
          "note": "JDK1.8 的 CAS 操作确保头节点和链表长度的原子性",
          "active": [
            1
          ]
        }
      ]
    }
  },
  {
    "id": "java-copyonwritearraylist-source-code",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "集合"
    ],
    "tags": [
      "Java",
      "集合"
    ],
    "title": "CopyOnWriteArrayList 源码分析",
    "oneLine": "CopyOnWriteArrayList 是线程安全的 List 实现，采用写时复制策略，适用于读多写少场景。",
    "analogy": "就像在图书馆借书，大家都可以同时看书，但有人要还书时，会先复制一份书再还，其他人才能继续看原来的书。",
    "why": "传统 List 如 Vector 需要对每个方法加锁，导致性能低下。CopyOnWriteArrayList 通过写时复制，让读操作无需加锁，提高并发性能。虽然写操作开销大，但适合读多写少的场景，如缓存、日志等。",
    "mechanism": [
      "CopyOnWriteArrayList 是线程安全的 List 实现，采用写时复制（Copy-On-Write）策略，即写操作时复制数组，读操作无需加锁。",
      "写操作时，会先加锁，复制底层数组，修改副本后替换原数组，确保读操作不受影响，实现线程安全。",
      "读操作直接访问数组，无需加锁，因此并发性能高，适合读多写少的场景。",
      "写操作的复杂度是 O(n)，因为需要复制整个数组，导致内存占用高，但保证了读操作的线程安全。",
      "迭代器会保留创建时的数组快照，后续修改不会影响迭代器，保证了快照一致性。",
      "写操作通过 ReentrantLock 实现同步，避免多个线程同时修改数组，保证数据一致性。",
      "数组每次复制后会替换为新数组，确保读操作始终访问最新的数组，避免数据不一致。",
      "size() 方法直接返回数组长度，无需维护独立的 size 变量，简化了实现。"
    ],
    "keywords": [
      "CopyOnWriteArrayList",
      "写时复制COW",
      "线程安全List",
      "读多写少",
      "快照一致性",
      "ReentrantLock"
    ],
    "scene": [
      "适用于缓存系统，如 Redis 缓存，读多写少，保证读操作高性能。",
      "日志系统中使用，写入操作较少，读取日志数据频繁，保证并发读取安全。",
      "在多线程环境中维护一个只读的配置列表，避免频繁修改影响性能。"
    ],
    "interviewQ": [
      "CopyOnWriteArrayList 为什么适合读多写少的场景？（答：写操作需要复制数组，开销大，但读操作无需加锁，适合读多写少场景。）",
      "CopyOnWriteArrayList 的读操作为什么不需要加锁？（答：读操作直接访问数组，无需同步，因为写操作会复制数组并替换引用，保证数据一致性。）",
      "CopyOnWriteArrayList 的写操作如何保证线程安全？（答：写操作通过 ReentrantLock 加锁，复制数组并替换引用，避免多个线程同时修改。）"
    ],
    "related": [
      {
        "id": "java-arrayblockingqueue-source-code",
        "kind": "compare",
        "note": "对比线程安全的队列与线程安全的 List 实现"
      },
      {
        "id": "java-arraylist-source-code",
        "kind": "prereq",
        "note": "理解 ArrayList 的实现是学习 CopyOnWriteArrayList 的基础"
      },
      {
        "id": "java-concurrent-hash-map-source-code",
        "kind": "compare",
        "note": "对比线程安全的 List 实现与线程安全的 Map 实现"
      },
      {
        "id": "java-hashmap-source-code",
        "kind": "compare",
        "note": "对比写时复制和哈希表两种线程安全策略"
      },
      {
        "id": "java-delayqueue-source-code",
        "kind": "compare",
        "note": "对比延迟队列与写时复制 List 的实现差异"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "加锁复制",
        "修改副本",
        "替换数组"
      ],
      "frames": [
        {
          "s": 0,
          "note": "写操作加锁，复制当前数组，避免并发修改"
        },
        {
          "s": 1,
          "note": "在副本上进行修改，确保数据一致性，避免覆盖原数组"
        },
        {
          "s": 2,
          "note": "替换原数组为修改后的副本，保证读操作始终访问最新数据"
        }
      ]
    }
  },
  {
    "id": "java-delayqueue-source-code",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "集合"
    ],
    "tags": [
      "Java",
      "集合"
    ],
    "title": "DelayQueue 源码分析",
    "oneLine": "DelayQueue 是 Java 提供的延迟队列，基于 PriorityQueue 实现，用于存储和取出到期的延迟任务。",
    "analogy": "DelayQueue 像是快递站，快递员按预计送达时间排序，只有预计送达时间最早的商品才会优先被派送。",
    "why": "在实际开发中，许多任务需要延时执行，比如订单超时取消。传统的队列无法实现延时，而 DelayQueue 通过 PriorityQueue 实现按到期时间排序，确保任务在到期后被取出，解决了延时任务调度的问题。",
    "mechanism": [
      "DelayQueue 是 Java 提供的延迟队列，基于 PriorityQueue 实现，用于存储和取出到期的延迟任务。它继承 AbstractQueue，实现 BlockingQueue 接口，确保线程安全。",
      "DelayQueue 中的元素必须实现 Delayed 接口，重写 getDelay 方法计算剩余时间，并通过 compareTo 方法定义排序规则，确保队列按到期时间升序排列。",
      "DelayQueue 使用 ReentrantLock 确保存取操作的线程安全，内部的 PriorityQueue 用于存储和排序元素，确保任务按到期时间顺序取出。",
      "当调用 take 方法获取元素时，如果队列为空，线程会进入 Condition 等待队列，直到有任务到期或被唤醒。若任务未到期，线程会等待直到 leader 线程执行完任务后唤醒。",
      "DelayQueue 的 offer 方法将元素添加到 PriorityQueue 中，并检查是否是队首元素，如果是则唤醒等待的线程，确保任务及时被处理。",
      "DelayQueue 的 take 方法通过 ReentrantLock 获取锁，检查队列状态，若为空则阻塞等待，若任务未到期则等待 leader 线程唤醒，确保任务按到期时间顺序取出。",
      "DelayQueue 的 leader 线程负责等待并执行到期任务，其他线程只能等待 leader 线程执行完任务后才能获取元素，确保任务优先级正确。",
      "DelayQueue 的 Condition 对象 available 用于线程间的等待和唤醒，确保线程在任务到期或被唤醒后能及时获取元素。"
    ],
    "keywords": [
      "DelayQueue",
      "Delayed接口",
      "PriorityQueue",
      "线程安全",
      "延时任务",
      "take"
    ],
    "scene": [
      "订单超时取消系统中，使用 DelayQueue 管理订单，15 分钟未支付则自动取消。",
      "定时任务调度系统中，使用 DelayQueue 按照设定时间执行任务，如日志清理。",
      "消息队列中，使用 DelayQueue 延迟处理消息，确保消息在指定时间后被消费。"
    ],
    "interviewQ": [
      "DelayQueue 如何保证线程安全？（答：DelayQueue 使用 ReentrantLock 确保存取操作的线程安全，确保多线程环境下数据一致性。）",
      "DelayQueue 的 take 方法如何处理空队列？（答：take 方法在队列为空时，线程会进入 Condition 等待队列，直到有任务到期或被唤醒。）",
      "DelayQueue 的 leader 线程作用是什么？（答：leader 线程负责等待并执行到期任务，确保任务按到期时间顺序取出，其他线程只能等待 leader 线程执行完任务后才能获取元素。）",
      "DelayQueue 的 offer 方法如何处理元素添加？（答：offer 方法将元素添加到 PriorityQueue 中，并检查是否是队首元素，如果是则唤醒等待的线程，确保任务及时被处理。）"
    ],
    "related": [
      {
        "id": "java-copyonwritearraylist-source-code",
        "kind": "compare",
        "note": "对比延迟队列与写时复制 List 的实现差异"
      },
      {
        "id": "java-arrayblockingqueue-source-code",
        "kind": "compare",
        "note": "对比延迟队列与阻塞队列的实现差异"
      },
      {
        "id": "java-arraylist-source-code",
        "kind": "prereq",
        "note": "理解 ArrayList 的实现是学习 DelayQueue 的基础"
      },
      {
        "id": "java-hashmap-source-code",
        "kind": "compare",
        "note": "对比基于数组和基于哈希表的延迟队列实现"
      },
      {
        "id": "java-java-collection-precautions-for-use",
        "kind": "extends",
        "note": "掌握 DelayQueue 实现原理，能更好理解延迟队列的使用注意事项"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "初始化队列",
        "添加元素",
        "取出元素"
      ],
      "frames": [
        {
          "s": 0,
          "note": "初始化队列时，通过 ReentrantLock 确保线程安全，内部使用 PriorityQueue 存储元素并按到期时间排序"
        },
        {
          "s": 1,
          "note": "添加元素时，通过 offer 方法插入 PriorityQueue，若为队首元素则唤醒等待线程，确保任务及时处理"
        },
        {
          "s": 2,
          "note": "取出元素时，若队列为空则阻塞等待，若任务未到期则等待 leader 线程执行完任务后唤醒，确保按到期时间顺序取出"
        }
      ]
    }
  },
  {
    "id": "java-hashmap-source-code",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "集合"
    ],
    "tags": [
      "Java",
      "集合"
    ],
    "title": "HashMap 源码分析",
    "oneLine": "HashMap 是基于哈希表的 Map 实现，用于存储键值对，解决哈希冲突采用链表和红黑树结构。",
    "analogy": "就像快递分拣，每个快递员（哈希值）负责不同区域（数组位置），如果太多快递（冲突），就用链表或红黑树整理。",
    "why": "HashMap 需要高效存储和查找键值对，哈希冲突是常见问题。链表和红黑树的结合在不同负载下提供平衡的性能，负载因子控制数据密度，避免频繁扩容。",
    "mechanism": [
      "HashMap 是基于哈希表的 Map 实现，通过 key 的 hashCode 计算哈希值，再通过哈希函数处理后确定存储位置，解决哈希冲突采用链表和红黑树结构。",
      "JDK1.7 使用数组+链表结构，通过扰动函数处理 hashCode，减少碰撞，通过 (n - 1) & hash 确定数组位置，冲突时使用链表存储。",
      "JDK1.8 优化了 hash 函数，减少扰动次数，同时在链表长度超过阈值（默认 8）时，将链表转为红黑树，提升查找效率。",
      "当数组长度小于 64 时，链表转红黑树前会先扩容，避免红黑树的复杂性，同时保持查找效率。",
      "负载因子（默认 0.75）控制数组存储密度，当元素数量超过阈值（容量 * 负载因子）时，触发扩容，数组长度变为原来的两倍。",
      "扩容时，所有元素需要重新计算哈希值并迁移至新数组，确保数据分布均匀，避免哈希冲突。",
      "Node 节点用于存储键值对，TreeNode 是红黑树节点，继承自 LinkedHashMap.Entry，支持红黑树的插入、删除和查找操作。",
      "HashMap 的扩容和查找操作都依赖于哈希函数和数组长度，确保数据分布均匀，提升存储和查找效率。"
    ],
    "keywords": [
      "HashMap源码",
      "哈希表",
      "红黑树",
      "链表",
      "扰动函数",
      "负载因子",
      "HashMap扩容"
    ],
    "scene": [
      "在缓存系统中，HashMap 用于快速存储和检索数据，避免频繁的数据库查询。",
      "在分布式系统中，HashMap 用于存储配置信息，确保不同节点间的数据一致性。",
      "在日志系统中，HashMap 用于统计日志条目，快速查找特定日志内容。"
    ],
    "interviewQ": [
      "追问1：HashMap 如何处理哈希冲突？（答：使用链表和红黑树结构，链表长度超过阈值时转为红黑树，提升查找效率。）",
      "追问2：HashMap 的扩容机制是怎样的？（答：当元素数量超过阈值时，数组长度翻倍，所有元素重新计算哈希值并迁移至新数组。）",
      "追问3：JDK1.8 与 JDK1.7 的 HashMap 有何区别？（答：JDK1.8 优化了 hash 函数，减少扰动次数，链表转红黑树的条件更严格，提升查找效率。）"
    ],
    "related": [
      {
        "id": "java-linkedlist-source-code",
        "kind": "compare",
        "note": "对比链表和数组实现的 Map 差异"
      },
      {
        "id": "java-arraylist-source-code",
        "kind": "prereq",
        "note": "理解 ArrayList 的实现是学习 HashMap 的基础"
      },
      {
        "id": "java-concurrent-hash-map-source-code",
        "kind": "compare",
        "note": "对比线程安全的 Map 实现与非线程安全的 Map 实现"
      },
      {
        "id": "java-copyonwritearraylist-source-code",
        "kind": "compare",
        "note": "对比哈希表和写时复制两种线程安全策略"
      },
      {
        "id": "java-delayqueue-source-code",
        "kind": "compare",
        "note": "对比基于数组和基于哈希表的延迟队列实现"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "计算哈希",
        "确定位置",
        "处理冲突",
        "扩容机制",
        "数据迁移"
      ],
      "frames": [
        {
          "s": 0,
          "note": "通过 key.hashCode() 计算哈希值，JDK1.8 优化了 hash 函数，减少扰动次数"
        },
        {
          "s": 1,
          "note": "(n - 1) & hash 确定数组位置，避免除法运算，提升性能"
        },
        {
          "s": 2,
          "note": "链表长度超过 8 时转为红黑树，提升查找效率，同时避免数组扩容的开销"
        },
        {
          "s": 3,
          "note": "负载因子 0.75 控制存储密度，当元素数量超过阈值时触发扩容，数组长度翻倍"
        },
        {
          "s": 4,
          "note": "扩容时所有元素需重新计算哈和值并迁移，确保数据分布均匀，减少哈希冲突"
        }
      ]
    }
  },
  {
    "id": "java-java-collection-precautions-for-use",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "集合"
    ],
    "tags": [
      "Java",
      "集合"
    ],
    "title": "Java集合使用注意事项总结",
    "oneLine": "Java集合使用注意事项包括判空、Arrays.asList陷阱、subList问题、并发容器选择等，避免常见错误。",
    "analogy": "就像整理房间时要分类收纳，集合操作也要注意判空、遍历和线程安全，避免物品丢失或混乱。",
    "why": "集合操作不当可能导致空指针异常、并发修改异常或性能问题。判空时使用isEmpty()而非size()==0，因为部分集合的size()时间复杂度较高。Arrays.asList返回的列表是固定大小，修改会抛异常。subList操作可能引发内存泄漏。并发环境下需选择线程安全的容器，如ConcurrentHashMap或CopyOnWriteArrayList，避免数据不一致。",
    "mechanism": [
      "isEmpty()方法可读性强且时间复杂度为O(1)，适合判断集合是否为空，而size()==0可能因集合实现不同导致复杂度不一致。",
      "ConcurrentLinkedQueue的isEmpty()通过first()方法判断，而size()需要遍历链表，时间复杂度为O(n)，因此优先使用isEmpty()。",
      "ConcurrentHashMap 1.7的size()需统计所有Segment的元素数，而isEmpty()只需找到第一个非空Segment，效率更高。",
      "Collectors.toMap()方法内部调用Map.merge()，其中value为null会触发NullPointerException，需确保value不为空。",
      "foreach循环遍历集合时，直接修改集合会导致ConcurrentModificationException，因为Iterator未同步修改操作。",
      "使用Iterator.remove()或Collection.removeIf()可安全删除元素，避免并发修改异常。",
      "Set去重利用元素唯一性，HashSet的contains()依赖HashMap的containsKey()，时间复杂度接近O(1)，而ArrayList的contains()需遍历，时间复杂度为O(n)。",
      "CopyOnWriteArrayList的迭代器基于快照，适合读多写少场景，而ConcurrentHashMap的迭代器是弱一致的，适合高并发环境。"
    ],
    "keywords": [
      "Java集合最佳实践",
      "集合判空",
      "Arrays.asList",
      "subList",
      "并发容器",
      "集合使用注意事项"
    ],
    "scene": [
      "在并发环境下使用ConcurrentHashMap存储用户会话信息，避免数据不一致。",
      "处理用户订单列表时，使用CopyOnWriteArrayList进行遍历和修改，防止并发修改异常。",
      "数据统计时，使用HashSet去重，提高查询效率。"
    ],
    "interviewQ": [
      "为什么推荐使用isEmpty()而不是size()==0？（答：isEmpty()可读性强且时间复杂度为O(1)，而size()在部分集合中可能为O(n)。）",
      "Collectors.toMap()为何在value为null时会抛异常？（答：toMap()内部调用Map.merge()，其中value为null会触发NullPointerException。）",
      "如何安全地在遍历集合时删除元素？（答：使用Iterator.remove()或Collection.removeIf()，避免ConcurrentModificationException。）"
    ],
    "related": [
      {
        "id": "java-concurrent-hash-map-source-code",
        "kind": "prereq",
        "note": "了解 ConcurrentHashMap 实现原理，能更好理解并发容器选择的注意事项"
      },
      {
        "id": "java-arraylist-source-code",
        "kind": "prereq",
        "note": "了解 ArrayList 实现原理，能更好理解 Arrays.asList 陷阱"
      },
      {
        "id": "java-delayqueue-source-code",
        "kind": "prereq",
        "note": "掌握 DelayQueue 实现原理，能更好理解延迟队列的使用注意事项"
      },
      {
        "id": "java-linkedhashmap-source-code",
        "kind": "prereq",
        "note": "掌握 LinkedHashMap 实现原理，能更好理解插入顺序遍历的注意事项"
      },
      {
        "id": "java-hashmap-source-code",
        "kind": "prereq",
        "note": "掌握 HashMap 实现原理，能更好理解并发容器选择的注意事项"
      }
    ],
    "diagram": null
  },
  {
    "id": "java-linkedhashmap-source-code",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "集合"
    ],
    "tags": [
      "Java",
      "集合"
    ],
    "title": "LinkedHashMap 源码分析",
    "oneLine": "LinkedHashMap 是 HashMap 的子类，通过维护双向链表实现插入顺序或访问顺序遍历，支持 LRU 缓存实现。",
    "analogy": "就像整理房间时，把最近用过的物品放在最前面，这样找东西更快，而不用每次都翻遍整个房间。",
    "why": "HashMap 的遍历顺序是无序的，无法保证插入或访问顺序，而实际应用中经常需要有序遍历，如 LRU 缓存。LinkedHashMap 通过维护双向链表，使得遍历效率与元素数量成正比，相较于 HashMap 的容量成正比的遍历效率更高，因此需要实现这种有序性。",
    "mechanism": [
      "LinkedHashMap 是 HashMap 的子类，内部通过维护双向链表实现插入顺序或访问顺序遍历，使得遍历效率与元素数量成正比。",
      "在插入顺序模式下，每个新插入的节点会被添加到双向链表的尾部，保证遍历时按照插入顺序访问；在访问顺序模式下，每次访问节点后，该节点会被移动到链表尾部，保证遍历时按照访问顺序访问。",
      "当元素被访问时，如果 accessOrder 为 true，get 方法会调用 afterNodeAccess 方法，将该节点移动到链表尾部，以维持访问顺序。",
      "LinkedHashMap 通过重写 removeEldestEntry 方法，可以实现 LRU 缓存功能，当元素数量超过容量时，移除链表头部的最老元素。",
      "在 HashMap 的基础上，LinkedHashMap 的节点类 Entry 继承 HashMap 的 Node 类，并增加 before 和 after 指针，实现双向链表特性。",
      "当链表长度达到阈值时，LinkedHashMap 会将链表转换为红黑树，以提高查找效率，同时保证链表和树节点的双向链表特性。",
      "LinkedHashMap 的构造方法支持设置 accessOrder 参数，控制是否按照访问顺序遍历，默认为 false，表示按照插入顺序遍历。",
      "LinkedHashMap 的 get 方法在访问元素后，若 accessOrder 为 true，会调用 afterNodeAccess 方法，将该节点移动到链表尾部，以维持访问顺序。"
    ],
    "keywords": [
      "LinkedHashMap",
      "双向链表",
      "插入顺序",
      "访问顺序",
      "LRU缓存",
      "accessOrder"
    ],
    "scene": [
      "在实现 LRU 缓存时，使用 LinkedHashMap 通过设置 accessOrder 为 true，保证最近最少使用的元素被移除。",
      "在需要按照插入顺序遍历数据的场景中，使用 LinkedHashMap 保证遍历顺序与插入顺序一致。",
      "在需要按照访问顺序遍历数据的场景中，使用 LinkedHashMap 通过设置 accessOrder 为 true，保证遍历顺序与访问顺序一致。"
    ],
    "interviewQ": [
      "为什么 LinkedHashMap 要维护双向链表？（答：为了支持插入顺序或访问顺序遍历，提高遍历效率，相较于 HashMap 的无序遍历。）",
      "LinkedHashMap 如何实现 LRU 缓存？（答：通过重写 removeEldestEntry 方法，当元素数量超过容量时移除链表头部的最老元素。）",
      "LinkedHashMap 的 get 方法在访问元素后做了什么？（答：若 accessOrder 为 true，会调用 afterNodeAccess 方法，将该节点移动到链表尾部，以维持访问顺序。）"
    ],
    "related": [
      {
        "id": "java-linkedlist-source-code",
        "kind": "compare",
        "note": "对比 LinkedList 和 LinkedHashMap 的实现差异，理解不同集合的适用场景"
      },
      {
        "id": "java-hashmap-source-code",
        "kind": "extends",
        "note": "掌握 HashMap 实现原理，能更好理解 LinkedHashMap 的继承关系"
      },
      {
        "id": "java-arraylist-source-code",
        "kind": "compare",
        "note": "对比 ArrayList 和 LinkedHashMap 的实现差异，理解不同集合的适用场景"
      },
      {
        "id": "java-concurrent-hash-map-source-code",
        "kind": "compare",
        "note": "对比 ConcurrentHashMap 和 LinkedHashMap 的实现差异，理解不同集合的适用场景"
      },
      {
        "id": "java-arrayblockingqueue-source-code",
        "kind": "compare",
        "note": "对比 ArrayBlockingQueue 和 LinkedHashMap 的实现差异，理解不同集合的适用场景"
      }
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "insert",
          "label": "插入",
          "x": 20,
          "y": 25
        },
        {
          "id": "access",
          "label": "访问",
          "x": 70,
          "y": 25
        },
        {
          "id": "remove",
          "label": "移除",
          "x": 20,
          "y": 70
        },
        {
          "id": "reorder",
          "label": "重排",
          "x": 70,
          "y": 70
        }
      ],
      "edges": [
        {
          "from": "insert",
          "to": "reorder"
        },
        {
          "from": "access",
          "to": "reorder"
        },
        {
          "from": "reorder",
          "to": "remove"
        },
        {
          "from": "remove",
          "to": "insert"
        }
      ],
      "frames": [
        {
          "n": "insert",
          "note": "新元素插入链表尾部，保持插入顺序"
        },
        {
          "n": "access",
          "note": "访问元素触发移动到链表尾部，维持访问顺序"
        },
        {
          "n": "reorder",
          "note": "节点移动到尾部，更新双向链表结构"
        },
        {
          "n": "remove",
          "note": "移除头部最老元素，实现 LRU 缓存机制"
        }
      ]
    }
  },
  {
    "id": "java-linkedlist-source-code",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "集合"
    ],
    "tags": [
      "Java",
      "集合"
    ],
    "title": "LinkedList 源码分析",
    "oneLine": "LinkedList 是基于双向链表实现的集合类，支持头尾增删 O(1) 时间复杂度，但随机访问性能差。",
    "analogy": "就像在快递站收发包裹，头尾操作像取最外层的包裹，中间操作则需要一层层拆开找。",
    "why": "LinkedList 的双向链表结构允许快速头尾增删，但不支持随机访问。由于链表内存不连续，无法通过索引直接定位元素，因此无法实现 RandomAccess 接口。这使得在需要频繁随机访问的场景中，LinkedList 性能不如 ArrayList。",
    "mechanism": [
      "LinkedList 是基于双向链表实现的集合类，每个节点包含前驱和后继指针，支持头尾增删 O(1) 时间复杂度。",
      "头尾插入/删除操作只需修改头尾指针即可完成，因此时间复杂度为 O(1)，但中间节点操作需要遍历链表。",
      "指定位置插入/删除需要先遍历到目标位置，平均遍历 n/4 个元素，时间复杂度为 O(n)，因此不适用于频繁随机访问。",
      "LinkedList 实现了 Deque 接口，支持双端队列操作，如 addFirst、removeLast 等，方便实现栈和队列。",
      "获取元素时，node(int index) 方法通过比较索引与链表长度的一半，决定从头或尾遍历，以减少查找时间。",
      "删除操作如 remove(int index) 会先找到目标节点，再修改前后节点指针，时间复杂度为 O(n)。",
      "LinkedList 不支持随机访问，因此无法实现 RandomAccess 接口，这是其性能劣势之一。",
      "LinkedList 的内存占用比 ArrayList 高，因为每个节点需要额外存储前后指针，适合频繁头尾增删的场景。"
    ],
    "keywords": [
      "LinkedList源码",
      "双向链表",
      "Deque接口",
      "LinkedList与ArrayList区别",
      "插入删除性能",
      "链表实现"
    ],
    "scene": [
      "在实现栈或队列时，LinkedList 可以作为双端队列使用，支持高效头尾增删。",
      "需要频繁在链表头尾添加元素的场景，如日志记录系统，使用 LinkedList 性能更优。",
      "在需要遍历链表中间节点的场景中，LinkedList 的性能不如 ArrayList，应避免频繁随机访问。"
    ],
    "interviewQ": [
      "为什么 LinkedList 不支持随机访问？（答：因为链表内存不连续，无法通过索引直接定位元素，因此无法实现 RandomAccess 接口。）",
      "LinkedList 的插入和删除操作时间复杂度如何？（答：头尾插入/删除是 O(1)，中间节点操作是 O(n)，因为需要遍历链表。）",
      "LinkedList 如何实现双端队列？（答：通过实现 Deque 接口，支持 addFirst、removeLast 等操作，方便实现栈和队列。）"
    ],
    "related": [
      {
        "id": "java-linkedhashmap-source-code",
        "kind": "compare",
        "note": "对比 LinkedHashMap 和 LinkedList 的实现差异，理解不同集合的适用场景"
      },
      {
        "id": "java-concurrent-hash-map-source-code",
        "kind": "compare",
        "note": "对比 ConcurrentHashMap 和 LinkedList 的实现差异，理解不同集合的适用场景"
      },
      {
        "id": "java-hashmap-source-code",
        "kind": "compare",
        "note": "对比 HashMap 和 LinkedList 的实现差异，理解不同集合的适用场景"
      },
      {
        "id": "java-arraylist-source-code",
        "kind": "compare",
        "note": "对比 ArrayList 和 LinkedList 的实现差异，理解不同集合的适用场景"
      },
      {
        "id": "java-arrayblockingqueue-source-code",
        "kind": "compare",
        "note": "对比 ArrayBlockingQueue 和 LinkedList 的实现差异，理解不同集合的适用场景"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "头尾增删",
        "中间增删",
        "随机访问",
        "性能对比"
      ],
      "frames": [
        {
          "s": 0,
          "note": "头尾增删操作只需修改头尾指针，时间复杂度为 O(1)，适合频繁头尾操作的场景。"
        },
        {
          "s": 1,
          "note": "中间增删需遍历链表，平均遍历 n/4 个元素，时间复杂度为 O(n)，效率低于数组。"
        },
        {
          "s": 2,
          "note": "随机访问需遍历链表，无法直接定位，时间复杂度为 O(n)，不适用于频繁随机访问。"
        },
        {
          "s": 3,
          "note": "LinkedList 与 ArrayList 的性能差异主要体现在插入删除和随机访问效率上，适合头尾操作场景。"
        }
      ]
    }
  },
  {
    "id": "java-arrayblockingqueue-source-code",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "集合"
    ],
    "tags": [
      "Java",
      "集合"
    ],
    "title": "ArrayBlockingQueue 源码分析",
    "oneLine": "ArrayBlockingQueue 是一个有界阻塞队列，通过 ReentrantLock 和 Condition 实现线程安全的生产者-消费者交互。",
    "analogy": "就像食堂排队打饭，当没有饭时，打饭的人会排队等待；当饭打完后，排队的人会继续等待，直到有新的饭来。",
    "why": "阻塞队列用于解决多线程环境下生产者和消费者之间的数据共享问题。传统的非阻塞队列在队列满或空时无法自动阻塞线程，导致线程频繁轮询，浪费资源。ArrayBlockingQueue 通过阻塞机制，让线程在队列空或满时自动等待，提升并发效率，特别适用于线程池等高并发场景。",
    "mechanism": [
      "ArrayBlockingQueue 是一个基于数组实现的有界阻塞队列，内部使用 ReentrantLock 和 Condition 实现线程安全的生产者-消费者交互。",
      "队列内部维护一个数组用于存储元素，同时维护两个指针（head 和 tail）分别指向队列头和尾，用于实现先进先出的队列特性。",
      "生产者调用 put 方法时，如果队列已满，则会阻塞直到队列有空位；消费者调用 take 方法时，如果队列为空，则会阻塞直到队列有元素。",
      "ReentrantLock 用于保证队列操作的线程安全，Condition 用于实现生产者和消费者的等待与唤醒机制，当队列有元素时唤醒消费者，当队列有空位时唤醒生产者。",
      "put 和 take 方法内部使用 Condition 的 await 和 signal 方法实现阻塞和唤醒，确保线程在队列满或空时不会频繁轮询。",
      "ArrayBlockingQueue 的实现基于生产者-消费者模型，通过阻塞机制实现线程之间的同步与协作，避免资源浪费。",
      "在多线程环境中，ArrayBlockingQueue 可以有效管理线程的阻塞与唤醒，提高系统吞吐量和资源利用率。"
    ],
    "keywords": [
      "ArrayBlockingQueue",
      "阻塞队列",
      "ReentrantLock",
      "Condition",
      "生产者消费者模式",
      "线程池"
    ],
    "scene": [
      "线程池中作为任务队列，当核心线程无法处理任务时，任务会被放入阻塞队列等待执行。",
      "多线程数据交换场景，如生产者线程生成数据后放入队列，消费者线程从队列中取出数据进行处理。",
      "缓存系统中，生产者将数据存入队列，消费者从队列中取出数据进行缓存或处理。"
    ],
    "interviewQ": [
      "ArrayBlockingQueue 为什么使用 ReentrantLock 而不是 synchronized？（答：ReentrantLock 提供了更灵活的锁机制，支持尝试获取锁、公平锁和非公平锁，而 synchronized 只能提供非公平锁。）",
      "ArrayBlockingQueue 的 put 和 take 方法如何实现阻塞？（答：put 和 take 方法内部使用 Condition 的 await 和 signal 方法实现阻塞和唤醒，当队列满时 put 阻塞，队列空时 take 阻塞。）",
      "ArrayBlockingQueue 的队列满和队列空如何通知生产者和消费者？（答：当队列满时，生产者会被阻塞并等待 Condition 通知；当队列空时，消费者会被阻塞并等待 Condition 通知。）"
    ],
    "related": [
      {
        "id": "java-copyonwritearraylist-source-code",
        "kind": "compare",
        "note": "对比 CopyOnWriteArrayList 和 ArrayBlockingQueue 的实现差异，理解不同集合的适用场景"
      },
      {
        "id": "java-delayqueue-source-code",
        "kind": "compare",
        "note": "对比 DelayQueue 和 ArrayBlockingQueue 的实现差异，理解不同集合的适用场景"
      },
      {
        "id": "java-arraylist-source-code",
        "kind": "compare",
        "note": "对比 ArrayList 和 ArrayBlockingQueue 的实现差异，理解不同集合的适用场景"
      },
      {
        "id": "java-linkedhashmap-source-code",
        "kind": "compare",
        "note": "对比 LinkedHashMap 和 ArrayBlockingQueue 的实现差异，理解不同集合的适用场景"
      },
      {
        "id": "java-concurrent-hash-map-source-code",
        "kind": "compare",
        "note": "对比 ConcurrentHashMap 和 ArrayBlockingQueue 的实现差异，理解不同集合的适用场景"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "等待空位",
        "入队操作",
        "唤醒消费者"
      ],
      "frames": [
        {
          "s": 0,
          "note": "生产者调用 put 方法时，若队列已满，会进入等待空位状态，避免资源浪费。"
        },
        {
          "s": 1,
          "note": "入队操作通过 ReentrantLock 加锁，确保线程安全，并更新 head 指针指向新元素。"
        },
        {
          "s": 2,
          "note": "队列有空位后，Condition 唤醒消费者线程，使其继续 take 操作，实现线程协作。"
        }
      ]
    }
  },
  {
    "id": "java-aqs",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "并发"
    ],
    "tags": [
      "Java",
      "并发"
    ],
    "title": "AQS 详解",
    "oneLine": "AQS 是 Java 并发包中用于构建锁和同步器的抽象类，通过 CLH 队列实现线程阻塞与唤醒。",
    "analogy": "AQS 就像一个排队系统，线程是排队的人，CLH 队列是排队的长椅，当有人离开时，后面的人可以被唤醒继续排队。",
    "why": "AQS 的出现解决了线程同步的复杂性问题，避免了开发者重复实现锁和同步器。传统的锁机制需要处理线程阻塞、唤醒、状态管理等复杂逻辑，而 AQS 提供了通用框架，让开发者只需关注业务逻辑。此外，AQS 通过 CLH 队列优化了线程阻塞与唤醒的效率，避免了自旋锁的高 CPU 占用问题，同时支持独占锁和共享锁的实现。",
    "mechanism": [
      "AQS 是一个抽象类，用于构建锁和同步器，通过封装线程同步机制简化开发者的实现难度。",
      "AQS 使用 CLH 队列的变体实现线程等待队列，每个线程被封装为一个 Node 节点，通过双向链表结构管理。",
      "CLH 队列采用自旋 + 阻塞机制，线程在获取锁失败后先尝试自旋，若失败则进入阻塞状态，减少 CPU 资源浪费。",
      "AQS 的 state 变量用于表示同步状态，通过 volatile 修饰保证线程可见性并防止指令重排序。",
      "Node 节点包含 waitStatus 状态，用于控制线程阻塞与唤醒，如 SIGNAL 表示需要唤醒后继节点，CANCELLED 表示线程已取消。",
      "AQS 通过 CAS 操作实现队列的并发安全，确保线程安全地入队和出队，同时支持独占锁和共享锁的实现。",
      "当线程获取锁失败时，会被加入等待队列，通过 acquiresQueued() 方法尝试获取锁，若失败则进入阻塞状态。",
      "当锁被释放时，AQS 会唤醒等待队列中的线程，使其重新尝试获取锁，从而实现线程的同步与协作。"
    ],
    "keywords": [
      "AQS",
      "AbstractQueuedSynchronizer",
      "队列同步器",
      "独占锁",
      "共享锁",
      "CLH队列"
    ],
    "scene": [
      "在 ReentrantLock 中，AQS 被用于实现可重入锁，线程通过 tryAcquire() 获取锁，失败则加入等待队列。",
      "在 Semaphore 中，AQS 被用于实现信号量，通过 acquire() 和 release() 控制资源的获取与释放。",
      "在 CountDownLatch 中，AQS 被用于实现倒计时器，通过 await() 和 countDown() 控制线程的等待与唤醒。"
    ],
    "interviewQ": [
      "AQS 中的 CLH 队列为什么采用双向链表结构？（答：双向链表允许节点直接唤醒后继节点，提高唤醒效率。）",
      "AQS 中的 state 变量如何保证线程可见性？（答：state 被 volatile 修饰，确保线程间可见性并防止指令重排序。）",
      "AQS 如何实现独占锁和共享锁？（答：通过重写 acquire() 和 release() 实现独占锁，通过 acquireShared() 和 releaseShared() 实现共享锁。）"
    ],
    "related": [
      {
        "id": "java-completablefuture-intro",
        "kind": "compare",
        "note": "对比 CompletableFuture 和 AQS 的实现差异，理解不同并发机制的适用场景"
      },
      {
        "id": "java-reentrantlock",
        "kind": "prereq",
        "note": "了解 ReentrantLock 的实现原理，能更好理解 AQS 的加锁与解锁机制"
      },
      {
        "id": "java-java-thread-pool-summary",
        "kind": "compare",
        "note": "对比线程池和 AQS 的实现差异，理解不同并发机制的适用场景"
      },
      {
        "id": "java-optimistic-lock-and-pessimistic-lock",
        "kind": "compare",
        "note": "对比乐观锁和悲观锁与 AQS 的实现差异，理解不同并发机制的适用场景"
      },
      {
        "id": "java-jmm",
        "kind": "compare",
        "note": "对比 JMM 和 AQS 的实现差异，理解不同并发机制的适用场景"
      }
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "locked",
          "label": "已加锁",
          "x": 20,
          "y": 25
        },
        {
          "id": "wait",
          "label": "等待队列",
          "x": 70,
          "y": 25
        },
        {
          "id": "unlocked",
          "label": "未加锁",
          "x": 20,
          "y": 70
        },
        {
          "id": "signal",
          "label": "唤醒线程",
          "x": 70,
          "y": 70
        }
      ],
      "edges": [
        {
          "from": "locked",
          "to": "wait"
        },
        {
          "from": "wait",
          "to": "unlocked"
        },
        {
          "from": "unlocked",
          "to": "signal"
        },
        {
          "from": "signal",
          "to": "locked"
        }
      ],
      "frames": [
        {
          "n": "locked",
          "note": "线程成功获取锁，进入已加锁状态，state 变量更新为非零值"
        },
        {
          "n": "wait",
          "note": "线程获取锁失败，加入等待队列，Node 节点被插入 CLH 队列"
        },
        {
          "n": "unlocked",
          "note": "锁被释放，state 变量变为零，触发唤醒机制"
        },
        {
          "n": "signal",
          "note": "唤醒等待队列中的线程，尝试重新获取锁，完成线程同步与协作"
        }
      ]
    }
  },
  {
    "id": "java-atomic-classes",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "并发"
    ],
    "tags": [
      "Java",
      "并发"
    ],
    "title": "Atomic 原子类总结",
    "oneLine": "Atomic 原子类是 Java 并发包中基于 CAS 实现的线程安全类，用于对变量进行原子操作。",
    "analogy": "就像在图书馆借书，Atomic 原子类确保每次借书操作不会被打断，保证数据一致性。",
    "why": "传统锁机制（如 synchronized）会带来性能损耗和死锁风险，而 Atomic 原子类通过 CAS 实现无锁化操作，提高并发性能。CAS 是一种乐观锁机制，它通过比较并交换操作实现原子性，避免了传统锁的开销，同时保证线程安全。",
    "mechanism": [
      "Atomic 原子类基于 CAS（Compare-And-Swap）实现，CAS 是一种乐观锁机制，通过比较并交换操作保证原子性。",
      "CAS 操作由底层硬件支持，它会检查内存中的值是否与预期值一致，如果一致则更新为新值，否则不更新。",
      "AtomicInteger 等类通过 CAS 实现对基本类型的原子操作，如 getAndSet、getAndIncrement 等方法。",
      "CAS 操作在多线程环境下可以避免锁的开销，提高并发性能，但存在 ABA 问题，需要通过 AtomicStampedReference 等类解决。",
      "AtomicReference 等类用于处理对象引用的原子操作，可以原子地更新引用或带版本号的引用。",
      "AtomicIntegerFieldUpdater 等类用于对对象的字段进行原子更新，适用于无法直接使用 AtomicReference 的场景。",
      "CAS 操作虽然高效，但可能因为重试导致性能下降，因此在使用时需要权衡性能和正确性。",
      "Atomic 原子类适用于需要高并发、低锁开销的场景，如计数器、缓存更新等。"
    ],
    "keywords": [
      "Atomic原子类",
      "AtomicInteger",
      "AtomicLong",
      "AtomicReference",
      "CAS原子操作",
      "JUC并发包"
    ],
    "scene": [
      "在多线程计数器中使用 AtomicInteger 实现线程安全的自增操作。",
      "在缓存系统中使用 AtomicReference 实现引用的原子更新，避免并发修改问题。",
      "在数据库连接池中使用 AtomicStampedReference 解决 ABA 问题，确保连接状态的正确性。"
    ],
    "interviewQ": [
      "Atomic 原子类如何实现线程安全？（答：Atomic 原子类基于 CAS 实现线程安全，CAS 是一种乐观锁机制，通过比较并交换操作保证原子性。）",
      "CAS 有哪些优缺点？（答：CAS 优点是无锁化操作，提高并发性能；缺点是存在 ABA 问题，可能导致重试和性能下降。）",
      "AtomicStampedReference 与 AtomicReference 的区别是什么？（答：AtomicStampedReference 带有版本号，用于解决 ABA 问题，而 AtomicReference 仅用于引用的原子更新。）"
    ],
    "related": [
      {
        "id": "java-cas",
        "kind": "prereq",
        "note": "理解原子类需要先知道 CAS 的实现原理"
      },
      {
        "id": "java-java-concurrent-collections",
        "kind": "compare",
        "note": "对比并发容器与原子类，理解线程安全的实现差异"
      },
      {
        "id": "java-java-lock",
        "kind": "compare",
        "note": "对比锁机制与原子类，理解线程安全的不同实现方式"
      },
      {
        "id": "java-aqs",
        "kind": "extends",
        "note": "原子类底层依赖 AQS 实现线程安全操作"
      },
      {
        "id": "java-threadlocal",
        "kind": "compare",
        "note": "对比原子类和ThreadLocal，理解线程隔离与原子操作的不同"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "基本类型",
          "lines": [
            "支持 int/long 基本类型",
            "提供 getAndSet 等原子方法",
            "适用于计数器等场景"
          ]
        },
        {
          "title": "对象引用",
          "lines": [
            "支持对象引用更新",
            "可带版本号防止 ABA",
            "适用于缓存系统场景"
          ]
        },
        {
          "title": "字段更新",
          "lines": [
            "支持对象字段原子更新",
            "需通过 updater 实现",
            "适用于不可变对象场景"
          ]
        }
      ],
      "frames": [
        {
          "note": "AtomicInteger 适用于线程安全计数器，通过 CAS 实现原子自增",
          "active": [
            0
          ]
        },
        {
          "note": "AtomicReference 可原子更新对象引用，AtomicStampedReference 解决 ABA 问题",
          "active": [
            1
          ]
        },
        {
          "note": "AtomicIntegerFieldUpdater 支持对象字段原子更新，适用于无法直接使用 AtomicReference 的场景",
          "active": [
            2
          ]
        }
      ]
    }
  },
  {
    "id": "java-cas",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "并发"
    ],
    "tags": [
      "Java",
      "并发"
    ],
    "title": "CAS 是如何实现的？",
    "oneLine": "CAS 是一种原子操作，通过比较并交换实现线程安全，常用于无锁编程。",
    "analogy": "CAS 就像在超市结账时，收银员检查你手中的商品是否和账单一致，一致就收钱，否则重新检查。",
    "why": "在多线程环境中，直接修改共享变量可能导致数据不一致。CAS 通过原子操作避免了锁的开销，提高了并发性能。旧方法如 synchronized 会阻塞线程，而 CAS 通过自旋重试，减少了线程切换的开销。因此，CAS 成为实现无锁数据结构和并发控制的重要手段。",
    "mechanism": [
      "CAS 是一种原子操作，通过比较并交换实现线程安全，它依赖于硬件支持的原子指令，如 Intel 的 CMPXCHG 指令。",
      "CAS 操作需要三个参数：内存地址、预期值和新值，如果内存地址的值等于预期值，则更新为新值，并返回 true；否则返回 false。",
      "CAS 操作由 Unsafe 类实现，该类位于 sun.misc 包下，提供 compareAndSwapObject、compareAndSwapInt、compareAndSwapLong 等方法。",
      "Unsafe 类的 CAS 方法是 native 方法，JVM 会将其映射为目标处理器支持的原子指令，如 x86 架构的 CMPXCHG 指令。",
      "Atomic 类如 AtomicInteger 依赖于 CAS 实现原子操作，例如 compareAndSet 方法通过 Unsafe 的 compareAndSwapInt 实现。",
      "CAS 操作在失败时会通过自旋锁机制重试，直到成功或超时，避免了锁的开销，但可能带来 CPU 资源的浪费。",
      "CAS 操作只能保证单个变量的原子性，当需要操作多个变量时，需要将其封装为对象，如 AtomicReference。",
      "CAS 操作存在 ABA 问题，即变量值被修改后又恢复原值，导致误判，需要通过版本号或时间戳解决。"
    ],
    "keywords": [
      "CAS",
      "Compare-And-Swap",
      "原子操作",
      "ABA问题",
      "自旋锁",
      "乐观锁",
      "Unsafe"
    ],
    "scene": [
      "在并发队列中，CAS 用于实现无锁的入队和出队操作，避免线程阻塞。",
      "在原子类如 AtomicInteger 中，CAS 用于保证原子递增和递减操作，如 getAndIncrement。",
      "在数据库乐观锁中，CAS 用于检查版本号，避免并发更新导致的数据不一致。"
    ],
    "interviewQ": [
      "CAS 是如何实现的？（答：CAS 通过 Unsafe 类实现，调用 native 方法，映射为处理器支持的原子指令，如 CMPXCHG。）",
      "CAS 存在哪些问题？（答：CAS 存在 ABA 问题、循环时间长开销大、只能保证单个变量的原子性。）",
      "如何解决 ABA 问题？（答：通过版本号或时间戳，如 AtomicStampedReference，检查引用和版本号是否一致。）"
    ],
    "related": [
      {
        "id": "java-atomic-classes",
        "kind": "extends",
        "note": "原子类基于 CAS 实现，理解 CAS 是理解原子类的关键"
      },
      {
        "id": "java-java-lock",
        "kind": "compare",
        "note": "对比 CAS 与锁机制，理解线程安全的不同实现方式"
      },
      {
        "id": "java-java-concurrent-collections",
        "kind": "compare",
        "note": "对比 CAS 与并发容器，理解线程安全的实现差异"
      },
      {
        "id": "java-aqs",
        "kind": "prereq",
        "note": "理解 CAS 需要先了解 AQS 的底层机制"
      },
      {
        "id": "java-synchronized",
        "kind": "compare",
        "note": "CAS 是无锁编程的核心，与锁升级形成对比"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "1. 比较值",
        "2. 交换值",
        "3. 返回结果"
      ],
      "frames": [
        {
          "s": 0,
          "note": "CAS 首先比较内存地址的值是否等于预期值，这是确保操作原子性的关键判断点。"
        },
        {
          "s": 1,
          "note": "如果值匹配，则更新为新值，这一步依赖硬件指令如 CMPXCHG 实现原子性。"
        },
        {
          "s": 2,
          "note": "操作完成后返回 true 或 false，决定是否成功，这是线程安全的核心逻辑。"
        }
      ]
    }
  },
  {
    "id": "java-completablefuture-intro",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "并发"
    ],
    "tags": [
      "Java",
      "并发"
    ],
    "title": "CompletableFuture 详解",
    "oneLine": "CompletableFuture 是 Java 8 引入的异步编程工具，用于实现异步任务编排和组合。",
    "analogy": "就像在超市购物，你可以同时去不同货架取货，而不是排队一个一个拿。",
    "why": "传统 Future 只能阻塞获取结果，无法编排任务，导致效率低下。CompletableFuture 通过函数式编程和异步编排，解决了任务阻塞和串行执行的问题，提升程序响应速度和并发能力。",
    "mechanism": [
      "CompletableFuture 是 Java 8 引入的异步编程工具，实现了 Future 和 CompletionStage 接口，支持异步任务编排和组合。",
      "通过 supplyAsync 和 runAsync 创建异步任务，将耗时操作交给线程池执行，主线程可以继续处理其他逻辑。",
      "thenApply 方法用于对异步结果进行转换，使用 Function 函数式接口处理结果，返回新的 CompletableFuture。",
      "thenAccept 方法用于消费异步结果，使用 Consumer 函数式接口处理结果，不返回新值。",
      "thenRun 方法用于在异步任务完成后执行某些操作，使用 Runnable 函数式接口，不关心结果。",
      "allOf 方法用于等待多个异步任务全部完成，适用于需要多个任务结果的场景。",
      "anyOf 方法用于等待任意一个异步任务完成，适用于只需要其中一个结果的场景。",
      "线程池配置影响任务执行效率，合理选择线程池可以提升系统并发能力和资源利用率。"
    ],
    "keywords": [
      "CompletableFuture",
      "异步编程",
      "异步编排",
      "Future",
      "thenCompose",
      "thenCombine",
      "allOf",
      "并行任务"
    ],
    "scene": [
      "用户请求获取订单信息，需要同时获取用户信息、商品详情、物流信息、商品推荐等数据。",
      "技术社区首页需要同时获取文章推荐列表、广告栏、文章排行榜、热门话题等信息。",
      "技术社区后台统计模块需要同时获取粉丝数汇总、文章数据（阅读量、评论量、收藏量）汇总等信息。"
    ],
    "interviewQ": [
      "CompletableFuture 和 Future 有什么区别？（答：CompletableFuture 支持异步编排和组合，而 Future 只能阻塞获取结果。）",
      "如何使用 thenApply 和 thenAccept？（答：thenApply 用于转换结果，thenAccept 用于消费结果，两者都返回新的 CompletableFuture。）",
      "allOf 和 anyOf 的应用场景是什么？（答：allOf 用于等待多个任务全部完成，anyOf 用于等待任意一个任务完成。）"
    ],
    "related": [
      {
        "id": "java-aqs",
        "kind": "prereq",
        "note": "理解 CompletableFuture 需要先了解 AQS 的异步执行机制"
      },
      {
        "id": "java-java-thread-pool-summary",
        "kind": "prereq",
        "note": "理解 CompletableFuture 需要先了解线程池的执行原理"
      },
      {
        "id": "java-jmm",
        "kind": "prereq",
        "note": "理解 CompletableFuture 需要先了解内存模型的可见性保证"
      },
      {
        "id": "java-java-lock",
        "kind": "compare",
        "note": "对比异步编程与锁机制，理解线程安全的实现差异"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "创建任务",
        "处理结果",
        "组合任务"
      ],
      "frames": [
        {
          "s": 0,
          "note": "通过 supplyAsync 或 runAsync 创建异步任务，将耗时操作交给线程池执行，主线程可继续处理其他逻辑"
        },
        {
          "s": 1,
          "note": "thenApply 转换结果，thenAccept 消费结果，thenRun 执行后续操作，均通过 Function/Consumer/Runnable 处理结果"
        },
        {
          "s": 2,
          "note": "allOf 等待所有任务完成，anyOf 等待任意任务完成，实现任务编排与组合"
        }
      ]
    }
  },
  {
    "id": "java-java-concurrent-collections",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "并发"
    ],
    "tags": [
      "Java",
      "并发"
    ],
    "title": "Java 常见并发容器总结",
    "oneLine": "Java 并发容器是线程安全的集合类，用于多线程环境下数据共享与操作。",
    "analogy": "就像图书馆的书架，多个读者可以同时取书，但必须确保每本书只被一个人拿走。",
    "why": "在多线程环境中，普通集合类如 HashMap 和 ArrayList 不是线程安全的，可能导致数据不一致或并发错误。并发容器通过锁、CAS 操作等机制保证线程安全，同时优化性能。例如，ConcurrentHashMap 采用分段锁或 CAS 精细控制锁粒度，提升并发效率。",
    "mechanism": [
      "ConcurrentHashMap 是线程安全的 HashMap，通过分段锁（JDK1.7）或 CAS+synchronized（JDK1.8）实现并发安全，避免全局锁导致的性能瓶颈。",
      "CopyOnWriteArrayList 采用写时复制策略，读操作无需加锁，写操作会复制数组并修改副本，确保读写不冲突，适合读多写少场景。",
      "ConcurrentLinkedQueue 使用 CAS 非阻塞算法实现线程安全，支持高并发下的快速读写，适合对性能要求高的场景。",
      "BlockingQueue 是阻塞队列接口，通过加锁或 CAS 实现线程安全，适用于生产者-消费者模型，保证队列满时生产者阻塞，队列空时消费者阻塞。",
      "ArrayBlockingQueue 是有界阻塞队列，使用 ReentrantLock 实现并发控制，生产者和消费者需获取锁才能操作队列，确保线程安全。",
      "LinkedBlockingQueue 是基于链表的阻塞队列，可以有界或无界，使用双锁机制（putLock 和 takeLock）实现并发控制，提高吞吐量。",
      "PriorityBlockingQueue 是支持优先级的无界阻塞队列，使用 ReentrantLock 实现并发控制，元素按自然顺序或自定义规则排序。",
      "ConcurrentSkipListMap 是基于跳表的线程安全 Map，通过分层链表实现快速查找，支持高并发下的并发操作，避免全局锁。"
    ],
    "keywords": [
      "ConcurrentHashMap",
      "CopyOnWriteArrayList",
      "BlockingQueue",
      "ConcurrentLinkedQueue",
      "ConcurrentSkipListMap",
      "CAS"
    ],
    "scene": [
      "在高并发的订单处理系统中，ConcurrentHashMap 用于存储用户购物车信息，保证并发访问安全。",
      "在日志收集系统中，CopyOnWriteArrayList 用于存储日志条目，读取频繁且写入较少，提升性能。",
      "在消息队列系统中，ConcurrentLinkedQueue 用于处理消息的快速读写，避免阻塞操作影响性能。"
    ],
    "interviewQ": [
      "ConcurrentHashMap 在 JDK1.7 和 JDK1.8 的实现有什么区别？（答：JDK1.7 采用分段锁，JDK1.8 采用 CAS+synchronized，提升并发性能。）",
      "CopyOnWriteArrayList 为什么适合读多写少的场景？（答：写操作会复制数组，读操作无需加锁，避免写操作影响读性能。）",
      "BlockingQueue 的生产者-消费者模型如何实现线程安全？（答：通过阻塞操作确保队列满时生产者等待，队列空时消费者等待，避免数据竞争。）"
    ],
    "related": [
      {
        "id": "java-atomic-classes",
        "kind": "compare",
        "note": "对比并发容器与原子类，理解线程安全的实现差异"
      },
      {
        "id": "java-java-lock",
        "kind": "compare",
        "note": "对比并发容器与锁机制，理解线程安全的实现差异"
      },
      {
        "id": "java-jmm",
        "kind": "prereq",
        "note": "理解并发容器需要先了解内存模型的可见性保证"
      },
      {
        "id": "java-cas",
        "kind": "compare",
        "note": "对比并发容器与 CAS，理解线程安全的实现差异"
      },
      {
        "id": "java-structured-concurrency",
        "kind": "compare",
        "note": "结构化并发与并发容器都涉及线程安全，但侧重点不同"
      }
    ],
    "diagram": null
  },
  {
    "id": "java-java-lock",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "并发"
    ],
    "tags": [
      "Java",
      "并发"
    ],
    "title": "Java 锁详解：互斥锁、读写锁、自旋锁与 synchronized 锁优化",
    "oneLine": "Java 锁机制用于保护共享状态，确保线程安全，包括互斥锁、读写锁、自旋锁和 synchronized 的优化策略。",
    "analogy": "就像图书馆借书，互斥锁是只允许一个人借书，读写锁是允许多人同时借书但不能同时修改，自旋锁是排队时先等一会儿再借书，synchronized 是借书前先登记。",
    "why": "锁机制是为了解决多线程访问共享数据时的竞态条件问题。在没有锁的情况下，多个线程可能同时修改同一数据，导致数据不一致。互斥锁通过确保同一时刻只有一个线程访问共享数据，避免了竞态条件。读写锁通过区分读和写操作，提高了并发性能。自旋锁通过减少线程阻塞，降低了上下文切换的开销。synchronized 的优化策略如锁升级和锁消除，提升了 JVM 在不同竞争强度下的性能。",
    "mechanism": [
      "互斥锁是确保同一时刻只有一个线程可以访问共享资源的机制，通过进入临界区前获取锁，执行完后释放锁，避免多个线程同时修改数据。",
      "读写锁将访问分为读和写两种类型，允许多个线程同时读取，但写操作必须独占，确保数据一致性，适用于读多写少的场景。",
      "自旋锁是线程在无法获取锁时，不阻塞而是持续检查锁是否可用，适用于临界区非常短的场景，减少上下文切换的开销。",
      "synchronized 是 Java 提供的内置锁，通过对象头中的 Mark Word 实现锁状态的管理，包括无锁、偏向锁、轻量级锁和重量级锁，根据竞争强度进行优化。",
      "ReentrantLock 是 Java 提供的显式锁，支持公平锁、可重入、尝试获取锁等高级功能，比 synchronized 更灵活。",
      "StampedLock 是 Java 8 引入的读写锁，支持乐观读和悲观读，通过 stamp 标识读操作是否成功，适用于短读场景。",
      "CAS（Compare and Swap）是一种无锁算法，通过比较并交换操作实现原子更新，是乐观锁的核心机制，用于实现 Atomic 类和自旋锁。",
      "锁优化包括锁升级、锁消除、锁粗化等策略，通过 JVM 的 JIT 编译器和运行时优化，减少锁的开销，提升程序性能。"
    ],
    "keywords": [
      "Java锁",
      "互斥锁",
      "读写锁",
      "自旋锁",
      "synchronized",
      "ReentrantLock",
      "StampedLock",
      "CAS"
    ],
    "scene": [
      "在多线程计数器中使用互斥锁确保自增操作的原子性。",
      "在缓存系统中使用读写锁提高读取性能，同时保证写操作的独占性。",
      "在高并发的数据库连接池中使用自旋锁减少线程阻塞，提升吞吐量。"
    ],
    "interviewQ": [
      "为什么互斥锁在高并发下可能成为性能瓶颈？（答：互斥锁在高并发下会导致线程频繁阻塞和唤醒，增加上下文切换开销，降低并发性能。）",
      "读写锁和互斥锁在适用场景上有何区别？（答：读写锁适用于读多写少的场景，允许多个读线程同时访问，而互斥锁对读和写都严格互斥，适用于所有场景。）",
      "自旋锁在什么情况下会比阻塞锁更高效？（答：自旋锁在临界区非常短的情况下更高效，因为避免了线程阻塞和上下文切换的开销，但锁长时间不释放会导致 CPU 空转。）"
    ],
    "related": [
      {
        "id": "java-optimistic-lock-and-pessimistic-lock",
        "kind": "prereq",
        "note": "理解锁机制需要先了解乐观锁和悲观锁的基本概念"
      },
      {
        "id": "java-reentrantlock",
        "kind": "extends",
        "note": "ReentrantLock 是锁机制的具体实现，理解其原理有助于深入锁机制"
      },
      {
        "id": "java-cas",
        "kind": "compare",
        "note": "对比锁机制与 CAS，理解线程安全的不同实现方式"
      },
      {
        "id": "java-java-concurrent-collections",
        "kind": "compare",
        "note": "对比锁机制与并发容器，理解线程安全的实现差异"
      },
      {
        "id": "java-atomic-classes",
        "kind": "compare",
        "note": "对比锁机制与原子类，理解线程安全的不同实现方式"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "互斥锁",
          "lines": [
            "确保同一时刻只有一个线程访问共享资源",
            "通过获取锁和释放锁控制访问",
            "适用于简单同步场景"
          ]
        },
        {
          "title": "读写锁",
          "lines": [
            "允许多线程同时读，写独占",
            "适用于读多写少的场景",
            "提高读取性能"
          ]
        },
        {
          "title": "自旋锁",
          "lines": [
            "线程无法获取锁时持续检查",
            "减少上下文切换开销",
            "适用于临界区极短场景"
          ]
        }
      ],
      "frames": [
        {
          "note": "互斥锁适用于简单同步场景，如多线程计数器确保自增原子性",
          "active": [
            0
          ]
        },
        {
          "note": "读写锁在缓存系统中提升读取性能，同时保证写操作独占",
          "active": [
            1
          ]
        },
        {
          "note": "自旋锁在高并发数据库连接池中减少线程阻塞，提升吞吐量",
          "active": [
            2
          ]
        }
      ]
    }
  },
  {
    "id": "java-java-thread-pool-best-practices",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "并发"
    ],
    "tags": [
      "Java",
      "并发"
    ],
    "title": "Java 线程池最佳实践",
    "oneLine": "线程池配置需结合业务吞吐、任务耗时、下游容量，合理设置线程数、队列长度和拒绝策略。",
    "analogy": "就像快递站分拣员和快递车的配合，线程池是分拣员，队列是快递车，任务是包裹，要确保分拣和运输的节奏匹配。",
    "why": "线程池是管理并发任务的核心工具，合理配置能提升系统吞吐量和稳定性。若线程数过少，任务排队等待，影响效率；线程数过多，资源浪费且可能引发线程饥饿。队列容量设置不当，可能导致任务堆积或直接拒绝，影响用户体验。因此，需结合业务实际，动态调整线程池参数，确保系统在高负载下仍能稳定运行。",
    "mechanism": [
      "线程池的核心是通过线程复用减少创建和销毁线程的开销，提高任务执行效率。线程池由核心线程、工作队列和最大线程数组成，任务提交后，先尝试由核心线程执行，若无空闲线程则进入队列等待。",
      "任务进入队列后，若队列容量已满，线程池会根据拒绝策略处理任务，如直接丢弃、抛出异常或让提交线程执行。合理设置队列容量可以避免任务堆积，同时防止内存溢出。",
      "线程池的线程数需根据任务类型（CPU密集型或I/O密集型）和系统资源动态调整。CPU密集型任务线程数通常等于CPU核心数，I/O密集型任务线程数可更高，以充分利用CPU。",
      "线程池的参数估算需结合业务流量和任务耗时，通过公式计算并发需求，如L ≈ λ × T，其中λ是任务进入速率，T是任务平均执行时间。但需考虑慢任务和系统资源限制，避免线程数设置过高。",
      "队列容量应根据突发流量和任务时效设置，确保任务在有效时间内完成。队列过小会导致任务被拒绝，过大则占用大量内存。需通过压测和监控数据调整队列容量，确保系统在高负载下仍能稳定运行。",
      "线程池需与下游容量协同设计，避免因上游线程数过高导致下游资源耗尽。例如，数据库连接池和HTTP客户端连接池的容量需与线程池配置匹配，防止资源竞争和性能瓶颈。",
      "线程池的监控和调参是持续优化的关键。需关注吞吐量、延迟、CPU利用率、队列等待时间和下游状态，通过压测和实时监控数据调整线程池参数，确保系统在不同负载下保持稳定。",
      "线程池的隔离是保障任务优先级和资源分配的重要手段。不同业务任务应使用独立线程池，避免慢任务影响其他任务执行。同时，需避免线程池死锁，如父任务与子任务共用线程池导致的环形等待问题。"
    ],
    "keywords": [
      "线程池最佳实践",
      "ThreadPoolExecutor参数配置",
      "线程池监控",
      "队列堆积",
      "CallerRunsPolicy",
      "动态线程池",
      "任务超时",
      "虚拟线程"
    ],
    "scene": [
      "订单查询服务使用线程池处理异步任务，需确保队列容量和线程数匹配数据库连接池容量，避免数据库资源耗尽。",
      "支付回调任务需独立线程池，防止慢任务影响核心交易线程池，同时设置合理超时时间避免任务堆积。",
      "日志采集服务使用无界队列线程池，需监控队列等待时间，防止任务因超时被丢弃或影响下游日志存储系统。"
    ],
    "interviewQ": [
      "如何根据业务场景合理配置线程池参数？（答：需结合任务类型、系统资源、业务吞吐和下游容量，通过公式估算并发需求，结合压测和监控数据调整线程数和队列容量。）",
      "线程池队列容量设置过大会带来哪些问题？（答：可能导致内存占用过高，任务在队列中等待时间过长，超出业务超时时间，影响用户体验。）",
      "如何处理线程池队列堆积问题？（答：需分析是流量突增还是任务执行变慢，前者可通过限流或扩容解决，后者需优化慢任务和下游依赖，必要时调整线程池参数。）",
      "线程池拒绝策略如何选择？（答：需根据业务需求选择，如直接丢弃、抛出异常或让提交线程执行，同时需配置自定义拒绝处理逻辑，确保任务可靠性。）"
    ],
    "related": [
      {
        "id": "java-java-thread-pool-summary",
        "kind": "prereq",
        "note": "了解线程池的基本原理后，才能掌握如何合理配置线程池参数。"
      },
      {
        "id": "java-jmm",
        "kind": "compare",
        "note": "线程池的性能受内存模型影响，需结合JMM理解数据可见性问题。"
      },
      {
        "id": "java-reentrantlock",
        "kind": "compare",
        "note": "线程池中的锁机制与ReentrantLock类似，对比可加深对并发控制的理解。"
      },
      {
        "id": "java-java-lock",
        "kind": "compare",
        "note": "线程池中的锁机制与Java锁详解相关，对比可理解锁在并发中的作用。"
      },
      {
        "id": "java-aqs",
        "kind": "extends",
        "note": "线程池的实现依赖AQS，深入AQS有助于理解线程池的底层机制。"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "任务提交",
        "线程复用",
        "队列等待",
        "拒绝策略"
      ],
      "frames": [
        {
          "s": 0,
          "note": "任务提交时，首先尝试由核心线程执行，若无空闲线程则进入队列等待。"
        },
        {
          "s": 1,
          "note": "线程复用减少创建和销毁线程的开销，提升任务执行效率，但需根据CPU密集型或I/O密集型任务调整线程数。"
        },
        {
          "s": 2,
          "note": "队列容量需结合突发流量和任务时效设置，过小导致任务被拒绝，过大则占用大量内存。"
        },
        {
          "s": 3,
          "note": "若队列满，根据拒绝策略处理任务，如直接丢弃、抛出异常或让提交线程执行，需与下游容量协同设计。"
        }
      ]
    }
  },
  {
    "id": "java-java-thread-pool-summary",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "并发"
    ],
    "tags": [
      "Java",
      "并发"
    ],
    "title": "Java 线程池详解",
    "oneLine": "Java 线程池是管理线程执行的工具，通过复用线程减少创建销毁开销，提高系统性能。",
    "analogy": "就像快递站的快递员，任务来了就交给空闲的快递员处理，而不是每次都临时招人。",
    "why": "频繁创建和销毁线程会消耗大量系统资源，线程池通过复用线程降低开销。同时，线程池能控制并发数量，防止资源耗尽，提升系统稳定性。线程池还支持任务队列和拒绝策略，让系统更灵活。",
    "mechanism": [
      "线程池是管理线程执行的工具，通过复用线程减少创建销毁开销，提高系统性能。它维护核心线程和任务队列，任务提交后由空闲线程执行。",
      "线程池的核心参数包括核心线程数、最大线程数、空闲线程存活时间、任务队列和拒绝策略。这些参数决定了线程池如何动态调整线程数量和处理任务。",
      "当任务提交时，线程池首先尝试将任务放入队列。如果队列已满，且线程数小于最大值，则创建新线程执行任务。若线程数已达上限，则触发拒绝策略。",
      "Worker 线程是线程池的执行单元，封装了任务执行逻辑。Worker 会从任务队列中获取任务执行，执行完毕后继续等待新任务。若线程池关闭，Worker 会退出。",
      "任务队列用于存储等待执行的任务，常见类型有无界队列、有界队列等。队列选择影响线程池的吞吐量和响应速度。",
      "拒绝策略用于处理无法执行的任务，如抛出异常、丢弃任务或由调用线程执行。不同策略适用于不同场景，如系统负载过高时选择丢弃旧任务。",
      "线程池通过监控接口提供运行状态，如活跃线程数、任务队列大小等，便于调优和故障排查。"
    ],
    "keywords": [
      "Java线程池",
      "ThreadPoolExecutor",
      "Executor框架",
      "拒绝策略",
      "任务队列"
    ],
    "scene": [
      "Web 服务器处理 HTTP 请求，使用线程池管理并发请求，避免线程爆炸。",
      "批量数据处理任务，使用线程池控制并发数量，防止系统资源耗尽。",
      "定时任务调度，使用 ScheduledThreadPoolExecutor 精确控制任务执行时间。"
    ],
    "interviewQ": [
      "线程池的核心参数有哪些？（答：核心线程数、最大线程数、空闲线程存活时间、任务队列、拒绝策略）",
      "线程池如何处理任务队列满的情况？（答：若线程数小于最大值则创建新线程，否则触发拒绝策略）",
      "线程池的拒绝策略有哪些？（答：AbortPolicy 抛出异常，CallerRunsPolicy 由调用线程执行，DiscardPolicy 直接丢弃，DiscardOldestPolicy 丢弃旧任务）"
    ],
    "related": [
      {
        "id": "java-java-thread-pool-best-practices",
        "kind": "extends",
        "note": "线程池的配置需要结合最佳实践，才能实现高效并发执行。"
      },
      {
        "id": "java-aqs",
        "kind": "extends",
        "note": "线程池的实现依赖AQS，深入AQS有助于理解线程池的底层机制。"
      },
      {
        "id": "java-jmm",
        "kind": "compare",
        "note": "线程池的内存可见性问题与JMM密切相关，对比可理解并发控制机制。"
      },
      {
        "id": "java-java-lock",
        "kind": "compare",
        "note": "线程池中的锁机制与Java锁详解相关，对比可理解锁在并发中的作用。"
      },
      {
        "id": "java-reentrantlock",
        "kind": "compare",
        "note": "线程池中的锁机制与ReentrantLock类似，对比可加深对并发控制的理解。"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "提交任务",
        "队列处理",
        "线程执行",
        "任务完成"
      ],
      "frames": [
        {
          "s": 0,
          "note": "任务提交时，线程池首先尝试将任务放入队列，若队列未满则直接入队，避免线程创建开销。"
        },
        {
          "s": 1,
          "note": "队列满时，若线程数小于最大值，会创建新线程执行任务，避免任务丢失，但可能增加资源消耗。"
        },
        {
          "s": 2,
          "note": "Worker 线程从队列中取出任务执行，执行完毕后自动回收，等待新任务，提升资源利用率。"
        },
        {
          "s": 3,
          "note": "任务完成后，线程池会根据策略决定是否保留线程，若关闭则所有 Worker 退出，释放资源。"
        }
      ]
    }
  },
  {
    "id": "java-jmm",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "并发"
    ],
    "tags": [
      "Java",
      "并发"
    ],
    "title": "JMM（Java 内存模型）详解",
    "oneLine": "JMM 是 Java 定义的并发编程规范，用于解决多线程下的内存可见性和指令重排序问题。",
    "analogy": "就像排队时的规则，JMM 确保不同线程之间能正确看到对方的修改，避免混乱。",
    "why": "Java 是跨平台语言，不同系统内存模型不同，JMM 通过抽象线程与主内存的关系，屏蔽系统差异，确保程序在不同平台下行为一致。同时，CPU 缓存和指令重排序可能导致内存可见性问题，JMM 通过 happens-before 原则和同步操作解决这些问题，使多线程编程更安全可靠。",
    "mechanism": [
      "JMM 是 Java 定义的并发编程规范，抽象了线程与主内存之间的关系，确保共享变量的可见性和同步操作的正确性。",
      "CPU 缓存模型通过 L1、L2、L3 三层缓存解决 CPU 与内存速度不匹配的问题，但可能导致内存缓存不一致性，如多线程下 i++ 操作结果错误。",
      "指令重排序是编译器和处理器为提升性能而进行的优化，可能破坏多线程下的程序顺序，导致可见性问题，如线程 A 修改变量后，线程 B 无法立即看到更新。",
      "JMM 通过 happens-before 原则定义操作之间的顺序关系，确保一个线程的写入对另一个线程可见，如 volatile、synchronized 和锁机制。",
      "JMM 抽象了主内存和本地内存的概念，线程只能操作本地内存中的变量副本，通过同步操作（如 lock、unlock、read、load 等）与主内存交互，确保数据一致性。",
      "JMM 定义了八种同步操作和同步规则，如 lock 和 unlock 必须成对出现，确保变量状态的正确性，避免无意义的内存同步。",
      "JMM 通过内存屏障（Memory Barrier）约束处理器和编译器的重排序行为，确保多线程下内存访问的顺序符合 JMM 的语义。",
      "JMM 的核心是提供跨平台的并发编程规范，屏蔽底层硬件差异，使开发者无需关心底层实现即可编写安全的多线程程序。"
    ],
    "keywords": [
      "JMM",
      "Java内存模型",
      "CPU缓存",
      "指令重排序",
      "happens-before",
      "内存可见性"
    ],
    "scene": [
      "多线程计数器程序中，线程 A 修改计数器后，线程 B 无法立即看到更新，导致结果错误。",
      "使用 volatile 关键字确保变量在多线程间可见，避免缓存不一致问题。",
      "在并发集合中，如 HashMap 在多线程下可能因指令重排序导致数据不一致。"
    ],
    "interviewQ": [
      "JMM 为什么需要 happens-before 原则？（答：happens-before 原则用于定义操作之间的顺序关系，确保一个线程的写入对另一个线程可见，解决指令重排序导致的可见性问题。）",
      "JMM 如何处理 CPU 缓存不一致性？（答：JMM 通过同步操作和内存屏障确保线程间共享变量的可见性，避免缓存不一致导致的错误。）",
      "JMM 和 Java 内存区域有何区别？（答：JMM 是并发编程规范，定义线程与主内存的关系；Java 内存区域是 JVM 运行时的内存划分，如堆、栈等。）"
    ],
    "related": [
      {
        "id": "java-java-thread-pool-summary",
        "kind": "compare",
        "note": "线程池的内存可见性问题与JMM密切相关，对比可理解并发控制机制。"
      },
      {
        "id": "java-aqs",
        "kind": "extends",
        "note": "JMM的实现依赖AQS，深入AQS有助于理解内存模型的底层机制。"
      },
      {
        "id": "java-java-lock",
        "kind": "compare",
        "note": "JMM的内存可见性问题与Java锁详解相关，对比可理解锁在并发中的作用。"
      },
      {
        "id": "java-optimistic-lock-and-pessimistic-lock",
        "kind": "compare",
        "note": "JMM的内存可见性问题与乐观锁、悲观锁的实现机制相关，对比可理解并发控制。"
      },
      {
        "id": "java-java-thread-pool-best-practices",
        "kind": "compare",
        "note": "线程池的性能受内存模型影响，需结合JMM理解数据可见性问题。"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "JMM 核心作用",
          "lines": [
            "解决内存可见性问题",
            "防止指令重排序破坏顺序",
            "定义 happens-before 原则",
            "提供跨平台并发规范"
          ]
        },
        {
          "title": "实现机制",
          "lines": [
            "抽象主内存与本地内存",
            "定义八种同步操作",
            "使用内存屏障约束重排序",
            "通过锁机制保证可见性"
          ]
        }
      ],
      "frames": [
        {
          "note": "JMM 通过 happens-before 原则确保线程间变量可见性，如 volatile 和 synchronized 的作用",
          "active": [
            0
          ]
        },
        {
          "note": "内存屏障限制处理器和编译器的重排序行为，保证多线程下内存访问顺序符合规范",
          "active": [
            1
          ]
        },
        {
          "note": "JMM 抽象主内存和本地内存，线程通过同步操作（lock/unlock）与主内存交互，确保数据一致性",
          "active": [
            1
          ]
        }
      ]
    }
  },
  {
    "id": "java-optimistic-lock-and-pessimistic-lock",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "并发"
    ],
    "tags": [
      "Java",
      "并发"
    ],
    "title": "乐观锁和悲观锁详解",
    "oneLine": "悲观锁假设冲突频繁，每次操作加锁；乐观锁假设冲突少，提交时验证数据一致性。",
    "analogy": "悲观锁像排队时提前占位，乐观锁像先做事再检查是否有人插队。",
    "why": "悲观锁适用于写操作频繁的场景，避免冲突；乐观锁适用于读多写少的场景，减少锁竞争和上下文切换。悲观锁通过锁机制确保数据一致性，但可能导致线程阻塞和死锁；乐观锁通过版本号或CAS算法实现非阻塞更新，但冲突频繁时会重试，影响性能。",
    "mechanism": [
      "悲观锁是一种基于冲突假设的锁机制，认为每次访问共享资源时都可能发生冲突，因此在每次操作前加锁，确保资源独占使用。",
      "悲观锁通过锁机制实现资源独占，例如Java中的synchronized和ReentrantLock，线程在获取锁后才能操作资源，其他线程阻塞等待。",
      "悲观锁在高并发场景下会导致线程阻塞和上下文切换，增加系统开销，且可能引发死锁问题，如线程获取锁的顺序不一致。",
      "乐观锁是一种基于非冲突假设的锁机制，认为共享资源在大多数情况下不会发生冲突，因此无需加锁，只在提交修改时验证数据一致性。",
      "乐观锁通过版本号机制或CAS算法实现，例如版本号机制在数据表中增加version字段，提交时比较版本号是否一致。",
      "CAS算法通过Compare And Swap实现，用预期值和新值比较变量，相等时更新，否则重试，避免线程阻塞。",
      "乐观锁在读多写少的场景中性能优越，但写操作频繁时可能导致大量重试，影响性能，如LongAdder在高并发下分散竞争。",
      "乐观锁通过非阻塞方式减少锁竞争，但需要处理版本号或CAS失败后的重试逻辑，确保数据一致性。"
    ],
    "keywords": [
      "乐观锁",
      "悲观锁",
      "synchronized",
      "ReentrantLock",
      "CAS",
      "版本号机制"
    ],
    "scene": [
      "银行账户余额更新时使用版本号机制，防止并发修改导致数据不一致。",
      "高并发的计数器场景中使用CAS算法，如AtomicInteger实现的原子操作。",
      "数据库更新操作中使用版本号字段，确保并发修改时的数据一致性。"
    ],
    "interviewQ": [
      "追问1：悲观锁和乐观锁在性能上有什么差异？（答：悲观锁在写多场景性能较好，但可能阻塞；乐观锁在读多场景性能较好，但冲突频繁时重试开销大。）",
      "追问2：CAS算法如何实现非阻塞更新？（答：CAS通过Compare And Swap实现原子操作，比较预期值和实际值，相等时更新，否则重试。）",
      "追问3：乐观锁在什么场景下更适用？（答：乐观锁适用于读多写少的场景，如计数器、缓存更新等，减少锁竞争和上下文切换。）"
    ],
    "related": [
      {
        "id": "java-java-lock",
        "kind": "extends",
        "note": "乐观锁和悲观锁是Java锁机制的具体实现，深入锁详解有助于理解其原理。"
      },
      {
        "id": "java-reentrantlock",
        "kind": "compare",
        "note": "ReentrantLock与乐观锁、悲观锁类似，对比可理解锁在并发中的不同策略。"
      },
      {
        "id": "java-aqs",
        "kind": "extends",
        "note": "乐观锁和悲观锁的实现依赖AQS，深入AQS有助于理解锁的底层机制。"
      },
      {
        "id": "java-java-thread-pool-summary",
        "kind": "compare",
        "note": "线程池中的锁机制与乐观锁、悲观锁类似，对比可加深对并发控制的理解。"
      },
      {
        "id": "java-jmm",
        "kind": "compare",
        "note": "JMM的内存可见性问题与乐观锁、悲观锁的实现机制相关，对比可理解并发控制。"
      }
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "初始状态",
          "label": "初始状态",
          "x": 20,
          "y": 25
        },
        {
          "id": "读取数据",
          "label": "读取数据",
          "x": 60,
          "y": 25
        },
        {
          "id": "提交修改",
          "label": "提交修改",
          "x": 100,
          "y": 25
        },
        {
          "id": "验证版本",
          "label": "验证版本",
          "x": 60,
          "y": 70
        },
        {
          "id": "重试或失败",
          "label": "重试或失败",
          "x": 100,
          "y": 70
        }
      ],
      "edges": [
        {
          "from": "初始状态",
          "to": "读取数据"
        },
        {
          "from": "读取数据",
          "to": "提交修改"
        },
        {
          "from": "读取数据",
          "to": "验证版本"
        },
        {
          "from": "提交修改",
          "to": "初始状态"
        },
        {
          "from": "验证版本",
          "to": "提交修改"
        },
        {
          "from": "验证版本",
          "to": "重试或失败"
        },
        {
          "from": "重试或失败",
          "to": "初始状态"
        }
      ],
      "frames": [
        {
          "n": "初始状态",
          "note": "线程开始执行，未进行任何操作，等待读取数据"
        },
        {
          "n": "读取数据",
          "note": "获取数据并记录版本号，准备进行修改操作"
        },
        {
          "n": "验证版本",
          "note": "提交时检查版本号是否一致，确保数据未被其他线程修改"
        },
        {
          "n": "提交修改",
          "note": "版本号一致则更新数据，完成操作并释放资源"
        },
        {
          "n": "重试或失败",
          "note": "版本号不一致则重试或标记操作失败，避免数据不一致"
        }
      ]
    }
  },
  {
    "id": "java-reentrantlock",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "并发"
    ],
    "tags": [
      "Java",
      "并发"
    ],
    "title": "ReentrantLock如何基于AQS实现加锁与解锁",
    "oneLine": "ReentrantLock通过AQS实现加锁与解锁，利用CAS和队列管理线程状态，支持公平与非公平锁。",
    "analogy": "就像排队取餐，ReentrantLock是收银员，AQS是排队系统，线程是顾客，公平锁按顺序排队，非公平锁插队。",
    "why": "ReentrantLock需要管理线程对共享资源的访问，避免并发冲突。传统的synchronized虽然能实现同步，但缺乏灵活性和可扩展性。AQS通过CAS操作和队列机制，实现了高效的锁管理，支持公平和非公平策略，满足不同场景需求。",
    "mechanism": [
      "ReentrantLock是基于AQS实现的可重入锁，通过CAS操作和队列管理线程状态，支持公平与非公平锁。",
      "加锁时，ReentrantLock调用Sync的lock方法，最终执行AQS的acquire方法，尝试获取锁。",
      "tryAcquire是获取锁的核心逻辑，根据锁类型（公平或非公平）执行不同的实现，非公平锁会直接尝试CAS修改状态。",
      "如果获取锁失败，线程会被加入等待队列，通过addWaiter方法创建节点并插入队列尾部。",
      "addWaiter使用CAS设置尾节点，成功后将新节点链接到队列，失败则调用enq方法进行重试。",
      "enq方法通过循环确保节点正确插入队列，处理并发修改的情况，保证队列的完整性。",
      "解锁时，ReentrantLock调用Sync的release方法，执行AQS的tryRelease逻辑，释放锁状态。",
      "tryRelease由ReentrantLock实现，减少锁计数，释放成功后唤醒等待队列中的线程。"
    ],
    "keywords": [
      "ReentrantLock",
      "AQS",
      "公平锁",
      "非公平锁",
      "CAS",
      "队列"
    ],
    "scene": [
      "在多线程环境下，ReentrantLock用于保护共享资源，如数据库连接池的获取与释放。",
      "在高并发的Web服务器中，ReentrantLock用于控制请求处理的同步，防止资源竞争。",
      "在分布式系统中，ReentrantLock结合AQS实现分布式锁，协调多个节点对共享资源的访问。"
    ],
    "interviewQ": [
      "ReentrantLock与synchronized的区别是什么？（答：ReentrantLock支持公平锁、可重入、可中断、超时等特性，而synchronized是Java关键字，不支持这些高级功能。）",
      "AQS如何实现线程等待与唤醒？（答：AQS通过队列管理线程状态，获取锁失败的线程进入等待队列，释放锁后唤醒队列中的线程。）",
      "非公平锁和公平锁在加锁时有何不同？（答：非公平锁会直接尝试CAS修改状态，可能插队；公平锁会检查队列顺序，确保先进先出。）"
    ],
    "related": [
      {
        "id": "java-aqs",
        "kind": "extends",
        "note": "ReentrantLock的实现依赖AQS，深入AQS有助于理解锁的底层机制。"
      },
      {
        "id": "java-java-lock",
        "kind": "extends",
        "note": "ReentrantLock是Java锁机制的具体实现，深入锁详解有助于理解其原理。"
      },
      {
        "id": "java-optimistic-lock-and-pessimistic-lock",
        "kind": "compare",
        "note": "ReentrantLock与乐观锁、悲观锁类似，对比可理解锁在并发中的不同策略。"
      },
      {
        "id": "java-java-thread-pool-summary",
        "kind": "compare",
        "note": "线程池中的锁机制与ReentrantLock类似，对比可加深对并发控制的理解。"
      },
      {
        "id": "java-java-thread-pool-best-practices",
        "kind": "compare",
        "note": "线程池中的锁机制与ReentrantLock类似，对比可加深对并发控制的理解。"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "尝试CAS获取锁",
        "CAS失败加入队列",
        "唤醒等待线程"
      ],
      "frames": [
        {
          "s": 0,
          "note": "非公平锁直接CAS修改状态，成功则持有锁，失败则进入队列"
        },
        {
          "s": 1,
          "note": "addWaiter通过CAS设置尾节点，失败则重试确保队列完整性"
        },
        {
          "s": 2,
          "note": "tryRelease释放锁后唤醒队列首节点，完成线程唤醒与锁状态转移"
        }
      ]
    }
  },
  {
    "id": "java-threadlocal",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "并发"
    ],
    "tags": [
      "Java",
      "并发"
    ],
    "title": "ThreadLocal 是什么原理？",
    "oneLine": "ThreadLocal 是线程本地变量，每个线程拥有独立副本，实现线程隔离。",
    "analogy": "就像每个快递员有自己的快递箱，不会和其他人混淆。",
    "why": "线程共享变量可能导致数据混乱，ThreadLocal 为每个线程创建独立副本，避免并发问题。弱引用设计防止内存泄漏，但需手动清理。",
    "mechanism": [
      "ThreadLocal 是线程本地变量，每个线程拥有独立副本，实现线程隔离。通过 ThreadLocalMap 存储数据，每个线程的 ThreadLocalMap 为独立实例。",
      "ThreadLocalMap 使用数组存储 Entry，每个 Entry 的 key 是弱引用的 ThreadLocal 实例，value 是线程变量。弱引用确保 GC 时 key 可被回收，但 value 仍被强引用。",
      "ThreadLocal.get() 时，先获取当前线程的 ThreadLocalMap，再查找 Entry。若 key 已被 GC 回收，key 为 null，但 value 仍被强引用，需手动清理。",
      "ThreadLocal.set() 时，将 Entry 存入 ThreadLocalMap，使用 hash 算法计算数组下标，解决哈希冲突。若发生冲突，直接覆盖原值。",
      "ThreadLocalMap 无链表结构，使用线性探测法解决哈希冲突。当数组扩容时，重新计算所有 Entry 的下标，保证数据正确性。",
      "ThreadLocalMap 有探测式清理和启发式清理机制。探测式清理在 set 时检查过期 key，启发式清理在 get 时扫描数组，清理过期 Entry。",
      "ThreadLocalMap 的扩容机制是数组大小翻倍，重新计算所有 Entry 的下标，保证数据分布均匀，避免哈希冲突。",
      "ThreadLocalMap 的内存泄漏风险在于，若线程长期存活，过期 Entry 的 value 无法被回收，需手动调用 remove() 清理。"
    ],
    "keywords": [
      "ThreadLocal",
      "线程本地变量",
      "ThreadLocalMap",
      "内存泄漏",
      "弱引用"
    ],
    "scene": [
      "Web 服务中使用 ThreadLocal 存储用户上下文信息，避免多线程干扰。",
      "线程池中使用 ThreadLocal 保存请求参数，防止数据污染。",
      "数据库连接池中使用 ThreadLocal 保存数据库连接，避免连接混乱。"
    ],
    "interviewQ": [
      "追问1：ThreadLocal 的 key 是弱引用，GC 后 key 是否为 null？（答：GC 后 key 可能为 null，但 value 仍被强引用，需手动清理。）",
      "追问2：ThreadLocalMap 的 hash 算法如何实现？（答：使用 key.threadLocalHashCode & (len-1) 计算下标，解决哈希冲突。）",
      "追问3：如何避免 ThreadLocal 内存泄漏？（答：使用完后调用 remove() 清理，或线程结束时自动回收。）"
    ],
    "related": [
      {
        "id": "java-jmm",
        "kind": "prereq",
        "note": "理解线程隔离需要先了解内存模型中的线程本地存储机制"
      },
      {
        "id": "java-reentrantlock",
        "kind": "compare",
        "note": "对比锁机制与线程本地变量，理解线程隔离与同步控制的区别"
      },
      {
        "id": "java-aqs",
        "kind": "extends",
        "note": "ThreadLocal内部使用AQS实现线程安全的变量存储"
      },
      {
        "id": "java-atomic-classes",
        "kind": "compare",
        "note": "对比原子类和ThreadLocal，理解线程隔离与原子操作的不同"
      },
      {
        "id": "java-virtual-threads",
        "kind": "compare",
        "note": "虚拟线程与 ThreadLocal 都涉及线程上下文，但用途不同"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "创建副本",
        "存储数据",
        "获取数据",
        "清理数据"
      ],
      "frames": [
        {
          "s": 0,
          "note": "ThreadLocal 为每个线程创建独立副本，避免线程间数据干扰。"
        },
        {
          "s": 1,
          "note": "ThreadLocalMap 使用数组存储 Entry，key 是弱引用，value 是强引用，确保数据可访问。"
        },
        {
          "s": 2,
          "note": "get() 时通过 ThreadLocalMap 查找 Entry，若 key 被 GC 回收，需手动清理 value 避免内存泄漏。"
        },
        {
          "s": 3,
          "note": "清理机制包括探测式和启发式清理，确保过期 Entry 被及时回收，防止内存泄漏。"
        }
      ]
    }
  },
  {
    "id": "java-io-basis",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java IO"
    ],
    "tags": [
      "Java",
      "Java IO"
    ],
    "title": "Java IO 基础知识总结",
    "oneLine": "Java IO 流分为字节流和字符流，用于处理数据的输入输出，字节流处理二进制数据，字符流处理文本数据。",
    "analogy": "Java IO 流就像水管，字节流是直接传输水，字符流是经过过滤器处理后的水，确保传输的字符不会乱码。",
    "why": "Java IO 流需要区分字节流和字符流，因为字节流处理的是二进制数据，而字符流处理的是文本数据。字符流在读写时会自动进行编码转换，避免乱码问题。字节流适合处理图片、音频等非文本数据，而字符流适合处理文本文件，确保字符的正确读写。",
    "mechanism": [
      "Java IO 流分为字节流和字符流，字节流处理的是二进制数据，字符流处理的是文本数据，两者通过编码转换实现互操作。",
      "字节流的基类是 InputStream 和 OutputStream，它们提供读写字节的方法，如 read() 和 write()，适用于非文本数据的传输。",
      "字符流的基类是 Reader 和 Writer，它们提供读写字符的方法，如 read() 和 write()，在读写时会自动进行编码转换，避免乱码。",
      "InputStreamReader 是字节流转换为字符流的桥梁，它使用 Charset 指定编码方式，确保字符的正确读写。",
      "FileInputStream 和 FileOutputStream 是字节流的常用类，用于读写文件中的字节数据。",
      "BufferedInputStream 和 BufferedOutputStream 是字节流的缓冲类，用于提高读写效率，减少系统调用次数。",
      "DataInputStream 和 DataOutputStream 是字节流的扩展类，用于读写基本数据类型，如 int、double、boolean 等。",
      "ObjectInputStream 和 ObjectOutputStream 是字节流的序列化类，用于将对象写入文件或网络传输，实现对象的持久化和远程调用。"
    ],
    "keywords": [
      "Java IO",
      "字节流",
      "字符流",
      "InputStream",
      "OutputStream",
      "Reader",
      "Writer",
      "文件操作"
    ],
    "scene": [
      "读取和写入文本文件时使用字符流，确保字符的正确读写，避免乱码问题。",
      "处理图片、音频等二进制文件时使用字节流，确保数据的完整性和正确性。",
      "网络传输数据时使用字节流，确保数据的高效传输和正确解析。"
    ],
    "interviewQ": [
      "为什么 Java IO 流要分为字节流和字符流？（答：字节流处理二进制数据，字符流处理文本数据，字符流在读写时会自动进行编码转换，避免乱码问题。）",
      "字节流和字符流的区别是什么？（答：字节流处理的是二进制数据，字符流处理的是文本数据，字符流在读写时会自动进行编码转换，确保字符的正确读写。）",
      "如何使用缓冲流提高 IO 流的效率？（答：使用 BufferedInputStream 和 BufferedOutputStream 包裹字节流，减少系统调用次数，提高读写效率。）"
    ],
    "related": [
      {
        "id": "java-nio-basis",
        "kind": "extends",
        "note": "NIO是IO的进阶模型，理解基础后可深入学习NIO"
      },
      {
        "id": "java-io-design-patterns",
        "kind": "extends",
        "note": "设计模式是IO实现的底层支撑，理解基础后可深入设计模式"
      },
      {
        "id": "java-io-model",
        "kind": "compare",
        "note": "对比IO模型，理解不同IO类型的特点和适用场景"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "字节流处理",
        "字符流处理",
        "编码转换"
      ],
      "frames": [
        {
          "s": 0,
          "note": "字节流处理二进制数据，如图片、音频等，通过 InputStream 和 OutputStream 实现，适合非文本数据传输。"
        },
        {
          "s": 1,
          "note": "字符流处理文本数据，通过 Reader 和 Writer 实现，读写时自动进行编码转换，避免乱码问题。"
        },
        {
          "s": 2,
          "note": "字节流和字符流通过 InputStreamReader 和 OutputStreamWriter 进行编码转换，确保字符的正确读写和数据完整性。"
        }
      ]
    }
  },
  {
    "id": "java-io-design-patterns",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java IO"
    ],
    "tags": [
      "Java",
      "Java IO"
    ],
    "title": "Java IO 设计模式总结",
    "oneLine": "Java IO 通过装饰器、工厂、观察者等设计模式实现灵活的流操作与事件监听。",
    "analogy": "就像用快递员送包裹，装饰器模式给快递员加装保温箱、签收通知，工厂模式负责安排快递员，观察者模式则让快递员能实时通知收件人包裹到达。",
    "why": "Java IO 需要处理多种流操作和事件监听，传统继承方式会导致类爆炸，装饰器模式通过组合方式扩展功能，避免继承复杂性；工厂模式统一创建对象，提升代码可维护性；观察者模式实现事件驱动，让系统更灵活响应文件变化，满足实时监控需求。",
    "mechanism": [
      "装饰器模式通过组合方式扩展对象功能，避免继承复杂性，如 FilterInputStream 用于增强 InputStream 的功能。",
      "工厂模式通过静态方法创建对象，如 Files.newInputStream() 和 Paths.get() 创建 InputStream 和 Path 对象，提升代码解耦。",
      "观察者模式通过 WatchService 和 Watchable 接口实现事件监听，如 Path.register() 注册监听文件变化事件，实现事件驱动。",
      "装饰器模式中的 BufferedInputStream 通过缓冲增强 FileInputStream 的性能，减少磁盘 I/O 次数。",
      "观察者模式中 WatchService 能监听多个文件目录，通过 WatchKey 获取事件信息，如文件创建、删除或修改。",
      "工厂模式中的 ZipFileSystem 使用简单工厂创建 Path 对象，实现不同文件系统的统一接口。",
      "观察者模式中 PollingWatchService 通过守护线程轮询检测文件变化，实现底层文件系统兼容性。",
      "装饰器模式中的 DataInputStream 通过读取字节流实现数据序列化，增强 InputStream 的功能。"
    ],
    "keywords": [
      "装饰器模式",
      "适配器模式",
      "模板方法模式",
      "FilterInputStream",
      "IO流设计"
    ],
    "scene": [
      "开发文件读写工具时，使用装饰器模式增强 FileInputStream 的缓冲功能。",
      "实现文件监控系统时，使用观察者模式监听文件目录变化，实时响应事件。",
      "创建统一的文件读取接口时，使用工厂模式通过 Files.newInputStream() 创建 InputStream 对象。"
    ],
    "interviewQ": [
      "追问1：装饰器模式在 Java IO 中如何实现？（答：通过 FilterInputStream 和 FilterOutputStream 组合扩展 InputStream 和 OutputStream 功能，避免继承复杂性。）",
      "追问2：观察者模式在 Java NIO 中的应用场景是什么？（答：用于监听文件目录变化，如通过 WatchService 和 Watchable 接口实现事件驱动。）",
      "追问3：工厂模式在 Java IO 中如何体现？（答：通过 Files.newInputStream() 和 Paths.get() 等静态方法创建对象，提升代码解耦和可维护性。）"
    ],
    "related": [
      {
        "id": "java-io-basis",
        "kind": "prereq",
        "note": "设计模式是IO实现的底层支撑，理解基础后可深入设计模式"
      },
      {
        "id": "java-io-model",
        "kind": "compare",
        "note": "对比IO模型，理解不同IO类型的特点和适用场景"
      },
      {
        "id": "java-nio-basis",
        "kind": "extends",
        "note": "NIO是IO的进阶模型，理解设计模式后可深入NIO"
      }
    ],
    "diagram": null
  },
  {
    "id": "java-io-model",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java IO"
    ],
    "tags": [
      "Java",
      "Java IO"
    ],
    "title": "Java IO 模型详解",
    "oneLine": "Java 中的 IO 模型包括 BIO、NIO 和 AIO，分别对应同步阻塞、非阻塞和异步 IO，用于处理不同场景下的 I/O 请求。",
    "analogy": "就像在图书馆借书，BIO 是排队借书，NIO 是同时借多本书，AIO 是让图书管理员直接通知你书到了。",
    "why": "I/O 操作是应用程序与外部设备之间的通信，但用户空间无法直接访问内核空间，必须通过系统调用。传统的同步阻塞 I/O 会阻塞线程，导致资源浪费。NIO 通过多路复用减少系统调用次数，提高效率。AIO 则通过异步方式进一步优化性能，适用于高并发场景。",
    "mechanism": [
      "BIO 是同步阻塞 IO 模型，应用程序发起 read 调用后会一直阻塞，直到内核将数据拷贝到用户空间，适用于连接数较少的场景。",
      "NIO 是同步非阻塞 IO 模型，应用程序通过 Selector 管理多个通道，轮询检查数据是否就绪，减少了无效的系统调用，提高了资源利用率。",
      "I/O 多路复用模型通过 select 或 epoll 系统调用，允许一个线程管理多个连接，当数据就绪时才触发 read 调用，减少了 CPU 的消耗。",
      "AIO 是异步 IO 模型，应用程序发起 read 调用后立即返回，通过 Future 或 CompletionHandler 获取结果，适用于高并发和低延迟的场景。",
      "同步 IO 模型中，线程在等待数据准备或拷贝时会被阻塞，而异步 IO 模型通过回调机制避免线程阻塞，提高并发性能。",
      "Java NIO 提供了 Channel、Selector 和 Buffer 等抽象，支持非阻塞和多路复用，使得开发者可以更高效地处理大量 I/O 请求。",
      "Reactor 模式通过事件循环监听 I/O 事件，Proactor 模式则通过异步回调处理 I/O 操作，两者分别对应 NIO 和 AIO 的实现方式。"
    ],
    "keywords": [
      "Java IO模型",
      "BIO",
      "NIO",
      "AIO",
      "阻塞IO",
      "非阻塞IO",
      "多路复用",
      "Reactor模式"
    ],
    "scene": [
      "在高并发的网络服务器中，使用 NIO 处理大量客户端连接，避免线程阻塞。",
      "在文件读写操作中，使用 BIO 适用于小型应用，但不适合处理大量文件。",
      "在需要高吞吐量和低延迟的场景中，如实时通信，使用 AIO 可以提升性能。"
    ],
    "interviewQ": [
      "追问1：BIO 和 NIO 的区别是什么？（答：BIO 是同步阻塞，NIO 是同步非阻塞，通过 Selector 实现多路复用，减少线程阻塞。）",
      "追问2：为什么 NIO 能提高性能？（答：NIO 通过多路复用减少系统调用次数，避免线程阻塞，提高资源利用率。）",
      "追问3：AIO 的优势和适用场景是什么？（答：AIO 是异步 IO，通过回调机制避免线程阻塞，适用于高并发和低延迟的场景。）"
    ],
    "related": [
      {
        "id": "java-nio-basis",
        "kind": "extends",
        "note": "NIO是IO模型的进阶实现，理解基础后可深入NIO"
      },
      {
        "id": "java-io-design-patterns",
        "kind": "compare",
        "note": "对比IO模型，理解不同IO类型的特点和适用场景"
      },
      {
        "id": "java-io-basis",
        "kind": "prereq",
        "note": "理解IO基础后，可深入不同IO模型的实现与区别"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "BIO",
          "lines": [
            "同步阻塞，线程阻塞等待数据",
            "适用于连接数少的场景",
            "线程与连接一一对应",
            "性能低，不适合高并发"
          ]
        },
        {
          "title": "NIO",
          "lines": [
            "同步非阻塞，通过Selector管理通道",
            "多路复用，减少无效系统调用",
            "线程处理多个连接",
            "适合高并发网络服务器"
          ]
        },
        {
          "title": "AIO",
          "lines": [
            "异步非阻塞，发起调用后立即返回",
            "通过回调获取结果，无需等待",
            "适合高吞吐量和低延迟场景",
            "线程不阻塞，提升并发性能"
          ]
        }
      ],
      "frames": [
        {
          "note": "NIO通过Selector实现多路复用，降低资源消耗",
          "active": [
            1
          ]
        },
        {
          "note": "AIO通过回调机制避免线程阻塞，适合实时通信",
          "active": [
            2
          ]
        },
        {
          "note": "BIO线程与连接绑定，适合小型应用但性能差",
          "active": [
            0
          ]
        }
      ]
    }
  },
  {
    "id": "java-nio-basis",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java IO"
    ],
    "tags": [
      "Java",
      "Java IO"
    ],
    "title": "Java NIO 核心知识总结",
    "oneLine": "Java NIO 是一种非阻塞 I/O 模型，通过 Buffer、Channel 和 Selector 实现高效的数据读写和多路复用。",
    "analogy": "就像一个快递员同时处理多个快递包裹，通过智能分拣系统（Selector）快速识别哪些包裹可以取件、哪些可以派送，无需为每个包裹单独等待。",
    "why": "传统 BIO 模型中，每个连接都需要一个线程处理，导致线程资源浪费和性能瓶颈。NIO 通过非阻塞方式，使用少量线程处理多个连接，提高并发能力和 I/O 效率。Selector 实现多路复用，让线程能同时监听多个通道的就绪事件，避免线程阻塞，提升系统吞吐量。",
    "mechanism": [
      "Buffer 是 NIO 的核心组件之一，用于存储和操作数据。它是一种线性结构，支持读写操作，可以将数据从 Channel 读取到 Buffer，或从 Buffer 写入到 Channel。",
      "Channel 是 NIO 中的 I/O 通道，用于读写数据。它与传统的流式 I/O 不同，可以支持非阻塞操作，例如读取或写入数据时不会阻塞线程。",
      "Selector 是 NIO 的多路复用机制，允许一个线程监控多个 Channel 的就绪事件。通过注册 Channel 到 Selector，线程可以监听哪些 Channel 有数据可读、可写或连接就绪。",
      "Selector 的 select() 方法会阻塞线程，直到有 Channel 就绪。当有事件发生时，Selector 会返回对应的 SelectionKey，并将这些 key 加入就绪集合。",
      "Selector 支持多种 select() 方法，如 select()、select(long timeout) 和 selectNow()，以适应不同的场景需求。例如，selectNow() 可以立即返回，不阻塞线程。",
      "在使用 Selector 时，需要为每个 Channel 注册感兴趣的事件类型（如 OP_READ、OP_WRITE），并在事件就绪时进行相应的处理。",
      "通过 Selector 实现多路复用，可以减少线程数量，提高系统的并发处理能力，适用于高并发、低延迟的网络环境。"
    ],
    "keywords": [
      "Java NIO",
      "Channel",
      "Buffer",
      "Selector",
      "非阻塞IO",
      "多路复用"
    ],
    "scene": [
      "在高并发的网络服务器中，使用 Selector 监听多个客户端连接，提高资源利用率。",
      "在实时数据处理系统中，通过 Buffer 和 Channel 实现高效的数据读写，减少 I/O 开销。",
      "在文件传输应用中，利用 NIO 的非阻塞特性，提高文件传输的效率和稳定性。"
    ],
    "interviewQ": [
      "Java NIO 的核心组件有哪些？（答：Buffer、Channel 和 Selector 是 NIO 的核心组件，分别用于数据存储、数据读写和多路复用。）",
      "Selector 的作用是什么？（答：Selector 用于多路复用，允许一个线程监控多个 Channel 的就绪事件，提高系统的并发处理能力。）",
      "NIO 与传统 BIO 的区别是什么？（答：NIO 采用非阻塞方式，通过 Buffer 和 Selector 实现高效 I/O，而 BIO 是阻塞式 I/O，每个连接需要一个线程处理。）"
    ],
    "related": [
      {
        "id": "java-io-model",
        "kind": "prereq",
        "note": "理解IO模型后，可深入NIO的非阻塞特性"
      },
      {
        "id": "java-io-basis",
        "kind": "extends",
        "note": "NIO是IO的进阶模型，理解基础后可深入NIO"
      },
      {
        "id": "java-io-design-patterns",
        "kind": "compare",
        "note": "对比IO模型，理解不同IO类型的特点和适用场景"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "创建 Buffer",
        "注册 Channel",
        "监听事件"
      ],
      "frames": [
        {
          "s": 0,
          "note": "Buffer 需要指定容量和类型，如 ByteBuffer 或 MappedByteBuffer"
        },
        {
          "s": 1,
          "note": "Channel 注册到 Selector 时需绑定读写事件，如 OP_READ 或 OP_WRITE"
        },
        {
          "s": 2,
          "note": "Selector 的 select() 方法会阻塞线程，直到有 Channel 事件就绪，返回 SelectionKey 集合"
        }
      ]
    }
  },
  {
    "id": "java-class-file-structure",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "JVM"
    ],
    "tags": [
      "Java",
      "JVM"
    ],
    "title": "类文件结构详解",
    "oneLine": "类文件结构是 Java 字节码的二进制格式，包含魔数、版本、常量池、字段、方法等信息，用于 JVM 加载和执行。",
    "analogy": "就像图书馆的目录，类文件结构是 Java 程序的索引，帮助 JVM 快速找到每个类的定义、方法和字段，就像读者通过目录找到书籍内容。",
    "why": "Java 程序需要跨平台运行，因此需要一种统一的中间格式——字节码。类文件结构通过魔数和版本号确保兼容性，常量池存储元数据，字段和方法表描述类的组成，使 JVM 能够解析和执行代码，同时支持多种语言在 JVM 上运行。",
    "mechanism": [
      "类文件结构是 Java 字节码的二进制格式，由 ClassFile 定义，包含魔数、版本号、常量池、字段、方法等信息，用于 JVM 加载和执行。",
      "魔数是 Class 文件的标志，固定为 0xCAFEBABE，用于验证文件是否为合法的 Java 字节码，确保 JVM 能正确加载。",
      "版本号包括主版本号和次版本号，主版本号用于区分 Java 大版本，如 Java 8 和 Java 9，确保高版本 JVM 可以运行低版本编译的字节码，但低版本 JVM 无法运行高版本字节码。",
      "常量池存储字面量和符号引用，如类名、方法名、字段名等，通过索引引用，减少重复存储，提高效率。",
      "字段表描述类或接口的字段，包括访问权限、名称、类型等信息，通过常量池索引引用名称和类型，确保灵活性。",
      "方法表描述类或接口的方法，包括访问权限、名称、参数类型、返回类型等信息，通过常量池索引引用方法名和描述符，支持动态绑定。",
      "属性表存储额外信息，如代码长度、异常表、注解等，用于增强类的功能和调试信息，提升可读性和可维护性。",
      "类文件结构通过标准化格式，使 JVM 能够统一解析不同语言编译的字节码，实现跨平台运行，同时支持多种语言在 JVM 上运行。"
    ],
    "keywords": [
      "Class 文件",
      "常量池",
      "魔数",
      "版本",
      "字段",
      "方法"
    ],
    "scene": [
      "在 JVM 调试工具中查看类文件结构，用于分析类的组成和元数据。",
      "使用 `javap -v` 命令反编译类文件，查看版本号、常量池、字段和方法信息。",
      "开发中确保 JDK 版本一致，避免高版本编译的类文件在低版本 JVM 上运行失败。"
    ],
    "interviewQ": [
      "追问1：类文件结构中的常量池有什么作用？（答：常量池存储字面量和符号引用，如类名、方法名等，通过索引引用，减少重复存储，提高效率。）",
      "追问2：魔数 0xCAFEBABE 的作用是什么？（答：魔数用于验证文件是否为合法的 Java 字节码，确保 JVM 能正确加载。）",
      "追问3：为什么高版本 JVM 可以运行低版本编译的类文件？（答：高版本 JVM 兼容低版本字节码，但低版本 JVM 无法解析高版本字节码，因此需保持 JDK 版本一致。）"
    ],
    "related": [
      {
        "id": "java-class-loading-process",
        "kind": "prereq",
        "note": "了解类文件结构是理解类加载过程的基础"
      },
      {
        "id": "java-jvm-garbage-collection",
        "kind": "compare",
        "note": "类文件结构与垃圾回收都涉及对象生命周期管理"
      },
      {
        "id": "java-jvm-intro",
        "kind": "prereq",
        "note": "了解JVM整体架构是理解类文件结构的前提"
      },
      {
        "id": "java-jdk-monitoring-and-troubleshooting-tools",
        "kind": "compare",
        "note": "类文件结构与监控工具都涉及JVM运行状态分析"
      }
    ],
    "diagram": {
      "kind": "arch",
      "nodes": [
        {
          "id": "magic",
          "label": "魔数",
          "x": 15,
          "y": 14,
          "w": 18
        },
        {
          "id": "version",
          "label": "版本号",
          "x": 50,
          "y": 14,
          "w": 18
        },
        {
          "id": "constant_pool",
          "label": "常量池",
          "x": 85,
          "y": 14,
          "w": 22
        },
        {
          "id": "fields",
          "label": "字段表",
          "x": 15,
          "y": 50,
          "w": 18
        },
        {
          "id": "methods",
          "label": "方法表",
          "x": 50,
          "y": 50,
          "w": 18
        },
        {
          "id": "attributes",
          "label": "属性表",
          "x": 85,
          "y": 50,
          "w": 22
        },
        {
          "id": "jvm",
          "label": "JVM",
          "x": 50,
          "y": 84,
          "w": 18
        }
      ],
      "links": [
        {
          "from": "magic",
          "to": "version",
          "label": "顺序"
        },
        {
          "from": "version",
          "to": "constant_pool",
          "label": "顺序"
        },
        {
          "from": "constant_pool",
          "to": "fields",
          "label": "引用"
        },
        {
          "from": "constant_pool",
          "to": "methods",
          "label": "引用"
        },
        {
          "from": "fields",
          "to": "jvm",
          "label": "解析"
        },
        {
          "from": "methods",
          "to": "jvm",
          "label": "解析"
        },
        {
          "from": "attributes",
          "to": "jvm",
          "label": "解析"
        }
      ],
      "frames": [
        {
          "n": "magic",
          "note": "魔数 0xCAFEBABE 标识合法 Java 字节码，确保 JVM 能正确加载。"
        },
        {
          "n": "version",
          "note": "主版本号区分 Java 大版本，如 Java 8 和 Java 9，确保兼容性。"
        },
        {
          "n": "constant_pool",
          "note": "存储类名、方法名等符号引用，通过索引减少重复存储，提高效率。"
        },
        {
          "n": "fields",
          "note": "字段表描述字段访问权限、名称和类型，通过常量池索引引用。"
        },
        {
          "n": "methods",
          "note": "方法表描述方法访问权限、参数类型和返回类型，支持动态绑定。"
        },
        {
          "n": "attributes",
          "note": "属性表存储代码长度、注解等信息，增强类的功能和调试信息。"
        },
        {
          "n": "jvm",
          "note": "JVM 通过标准化格式统一解析不同语言编译的字节码，实现跨平台运行。"
        }
      ]
    }
  },
  {
    "id": "java-class-loading-process",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "JVM"
    ],
    "tags": [
      "Java",
      "JVM"
    ],
    "title": "类加载过程详解",
    "oneLine": "类加载是JVM将Class文件加载到内存并初始化的过程，包含加载、验证、准备、解析和初始化五个阶段。",
    "analogy": "就像快递员将包裹送到指定地址，类加载过程是JVM把Class文件的内容一步步送到内存的各个区域，确保程序能正确运行。",
    "why": "类加载是JVM运行程序的基础，确保类文件的合法性、安全性及正确性。验证阶段防止恶意代码，准备阶段为类变量分配内存，解析阶段将符号引用转换为直接引用，初始化阶段执行类的初始化代码，保证程序运行时的稳定性。",
    "mechanism": [
      "加载阶段是类加载的第一步，通过全类名获取二进制字节流，将字节流转换为方法区的运行时数据结构，并在内存中生成Class对象作为访问入口。",
      "验证阶段确保Class文件符合《Java虚拟机规范》，防止恶意代码危害JVM安全，包括文件格式验证、元数据验证、字节码验证和符号引用验证。",
      "准备阶段为类变量分配内存并设置初始值，仅处理类变量（静态变量），不包括实例变量，初始值通常为零值，如0、0L、null、false等。",
      "解析阶段将符号引用转换为直接引用，如类、字段、方法的符号引用被解析为内存地址或偏移量，确保运行时常量池中的符号引用能正确指向目标。",
      "初始化阶段执行类或接口的初始化方法<clinit>，根据静态字段初始化表达式和静态代码块生成，确保类的静态变量和静态代码块被正确执行。",
      "卸载阶段是JVM回收类的资源，当类的实例对象被回收、类加载器被回收且类未被引用时，类可能被卸载，但启动类加载器定义的类无法被卸载。",
      "类加载过程分为加载、连接（验证、准备、解析）和初始化三个阶段，连接阶段确保类的合法性、内存分配和符号引用解析，初始化阶段执行类的初始化代码。",
      "类加载器（如双亲委派模型）控制类的加载方式，确保类的正确加载和避免重复加载，同时允许自定义类加载器改变委派规则。"
    ],
    "keywords": [
      "类加载",
      "加载",
      "验证",
      "准备",
      "解析",
      "初始化",
      "clinit",
      "常量池"
    ],
    "scene": [
      "在Web应用中，Servlet类在第一次请求时被类加载器加载，确保请求能正确处理。",
      "在动态代理中，JDK通过类加载器加载动态生成的代理类，实现接口的动态绑定。",
      "在JVM中，当使用反射调用Class.forName()时，会触发类的初始化过程，确保类的静态变量和代码块被正确执行。"
    ],
    "interviewQ": [
      "为什么验证阶段是类加载过程中的关键步骤？（答：验证确保Class文件符合规范，防止恶意代码危害JVM安全，包括文件格式、元数据、字节码和符号引用验证。）",
      "准备阶段和初始化阶段在类变量初始化上的区别是什么？（答：准备阶段为类变量分配内存并设置零值，初始化阶段执行静态变量和代码块的显式赋值。）",
      "解析阶段的作用是什么？（答：解析阶段将符号引用转换为直接引用，如类、字段、方法的符号引用被解析为内存地址或偏移量，确保运行时常量池中的符号引用能正确指向目标。）"
    ],
    "related": [
      {
        "id": "java-class-file-structure",
        "kind": "prereq",
        "note": "类加载过程需要解析类文件结构中的信息"
      },
      {
        "id": "java-jvm-intro",
        "kind": "prereq",
        "note": "了解JVM整体架构是理解类加载过程的前提"
      },
      {
        "id": "java-jvm-garbage-collection",
        "kind": "compare",
        "note": "类加载与垃圾回收都涉及对象生命周期管理"
      },
      {
        "id": "java-classloader",
        "kind": "extends",
        "note": "类加载器实现类加载过程中的加载步骤"
      },
      {
        "id": "java-jdk-monitoring-and-troubleshooting-tools",
        "kind": "compare",
        "note": "类加载过程与监控工具都涉及JVM运行状态分析"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "加载",
        "验证",
        "准备",
        "解析",
        "初始化"
      ],
      "frames": [
        {
          "s": 0,
          "note": "加载阶段需通过全类名获取字节流，生成Class对象作为访问入口，不涉及类变量初始化。"
        },
        {
          "s": 1,
          "note": "验证阶段确保Class文件符合规范，防止恶意代码，包括文件格式、元数据、字节码和符号引用验证。"
        },
        {
          "s": 2,
          "note": "准备阶段为类变量分配内存并设置初始值，如0、null、false，不处理实例变量和常量值。"
        },
        {
          "s": 3,
          "note": "解析阶段将符号引用转换为直接引用，如类、字段、方法的符号引用解析为内存地址或偏移量。"
        },
        {
          "s": 4,
          "note": "初始化阶段执行<clinit>方法，按静态变量初始化表达式和静态代码块顺序执行，确保类的静态资源正确初始化。"
        }
      ]
    }
  },
  {
    "id": "java-classloader",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "JVM"
    ],
    "tags": [
      "Java",
      "JVM"
    ],
    "title": "类加载器详解（重点）",
    "oneLine": "类加载器是动态加载Java类到JVM中的机制，实现类加载过程中的加载步骤。",
    "analogy": "类加载器就像快递员，负责将类的字节码从外部送到JVM中，确保程序能正确运行。",
    "why": "类加载器是JVM实现动态加载类的核心机制，允许程序在运行时加载新的类，提升灵活性和扩展性。旧的静态加载方式无法满足动态需求，因此需要类加载器来实现动态加载。双亲委派模型确保类加载的唯一性和安全性，避免类冲突和重复加载。",
    "mechanism": [
      "类加载器的核心作用是动态加载Java类的字节码到JVM中，生成Class对象作为访问入口。它负责从各种来源（如文件系统、网络）获取类的二进制字节流。",
      "类加载过程分为加载、连接和初始化三个阶段，其中加载阶段由类加载器完成。加载阶段包括获取类的二进制字节流、转换为运行时数据结构、生成Class对象。",
      "双亲委派模型是类加载器的核心机制，确保类加载的唯一性和安全性。当加载一个类时，类加载器首先委托父类加载器尝试加载，只有在父类加载器无法加载时，才由自己尝试加载。",
      "类加载器通过findClass方法查找类的字节码，默认实现抛出ClassNotFoundException。如果需要自定义类加载器，需重写findClass方法以实现特定的加载逻辑。",
      "类加载器通过loadClass方法实现双亲委派模型，首先检查是否已加载该类，若未加载则委托父类加载器，最后调用findClass方法加载类。",
      "JVM中常见的类加载器包括启动类加载器、扩展类加载器和应用类加载器。启动类加载器负责加载核心类库，扩展类加载器加载扩展目录中的类，应用类加载器加载应用类路径中的类。",
      "自定义类加载器可以实现特定功能，如加密字节码、动态加载网络资源等。但需注意避免打破双亲委派模型，以确保类加载的唯一性和安全性。",
      "类加载器通过记录已加载的类，避免重复加载同一类。每个类加载器维护一个已加载类的列表，防止重复定义相同二进制名称的类。"
    ],
    "keywords": [
      "类加载器",
      "ClassLoader",
      "双亲委派模型",
      "类加载过程",
      "自定义类加载器",
      "打破双亲委派"
    ],
    "scene": [
      "在Java Web应用中，类加载器用于动态加载Servlet和JSP页面，确保应用的灵活性。",
      "在插件系统中，类加载器用于加载第三方插件，实现模块化和扩展性。",
      "在热部署场景中，类加载器用于动态加载新版本的类，实现无停机更新。"
    ],
    "interviewQ": [
      "追问1：双亲委派模型如何保证类加载的唯一性？（答：双亲委派模型确保每个类由唯一的类加载器加载，避免类冲突和重复加载。）",
      "追问2：自定义类加载器需要重写哪些方法？（答：自定义类加载器需要重写findClass方法，以实现特定的类加载逻辑。）",
      "追问3：打破双亲委派模型的场景有哪些？（答：打破双亲委派模型的场景包括需要动态加载加密字节码、加载不同版本的类等。）"
    ],
    "related": [
      {
        "id": "java-class-loading-process",
        "kind": "prereq",
        "note": "类加载器实现类加载过程中的加载步骤"
      },
      {
        "id": "java-jvm-garbage-collection",
        "kind": "compare",
        "note": "类加载器与垃圾回收都涉及对象生命周期管理"
      },
      {
        "id": "java-jvm-intro",
        "kind": "prereq",
        "note": "了解JVM整体架构是理解类加载器的前提"
      },
      {
        "id": "java-jvm-parameters-intro",
        "kind": "compare",
        "note": "类加载器配置与内存参数共同构成JVM运行环境"
      },
      {
        "id": "java-memory-area",
        "kind": "prereq",
        "note": "类加载器与内存区域共同构成JVM运行环境"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "获取字节码",
        "生成Class对象",
        "初始化类"
      ],
      "frames": [
        {
          "s": 0,
          "note": "类加载器从文件系统或网络获取类的二进制字节流，是加载过程的第一步。"
        },
        {
          "s": 1,
          "note": "字节码被转换为JVM的运行时数据结构，并生成对应的Class对象作为访问入口。"
        },
        {
          "s": 2,
          "note": "初始化阶段会执行静态代码块和初始化类变量，确保类的正确运行状态。"
        }
      ]
    }
  },
  {
    "id": "java-jdk-monitoring-and-troubleshooting-tools",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "JVM"
    ],
    "tags": [
      "Java",
      "JVM"
    ],
    "title": "JDK监控和故障处理工具总结",
    "oneLine": "JDK提供多种命令行工具用于监控JVM运行状态和故障排查，如jps、jstat、jmap等。",
    "analogy": "就像在超市里用购物车查看商品库存，jps是查看货架上的商品，jstat是查看商品的销售情况，jmap是检查商品的库存是否充足。",
    "why": "JVM运行过程中可能出现内存泄漏、线程死锁等问题，这些工具能帮助开发者实时监控、分析和解决这些问题。传统方法如日志记录不够直观，而这些工具能提供更精确的数据支持。",
    "mechanism": [
      "jps是JVM进程状态工具，类似于UNIX的ps命令，用于列出所有Java进程的主类名和进程ID，帮助开发者快速识别和管理运行中的Java应用。",
      "jstat是JVM统计监控工具，可以收集HotSpot虚拟机的运行数据，如GC、内存、编译等信息，帮助开发者在没有GUI的环境下分析JVM性能问题。",
      "jinfo用于实时查看和调整JVM参数，例如查看JVM的启动参数或修改某些可管理的参数，如PrintGC，帮助开发者动态调整JVM行为。",
      "jmap用于生成堆转储快照，可以查询Java堆和类加载器等信息，帮助开发者分析内存泄漏或堆内存使用情况。",
      "jhat用于分析heapdump文件，建立HTTP/HTML服务器，让用户在浏览器中查看分析结果，但JDK9后被移除，推荐使用MAT或VisualVM。",
      "jstack用于生成线程快照，查看线程执行的方法堆栈，帮助开发者定位线程死锁、死循环等问题，是分析线程停顿的重要工具。"
    ],
    "keywords": [
      "JDK 工具",
      "jps",
      "jstat",
      "jmap",
      "jhat",
      "jstack"
    ],
    "scene": [
      "在服务器上运行Java应用时，使用jps查看所有Java进程，确保应用正常运行。",
      "在生产环境中，使用jstat监控GC和内存使用情况，及时发现性能瓶颈。",
      "当应用出现OOM异常时，使用jmap生成堆转储，分析内存泄漏原因。"
    ],
    "interviewQ": [
      "如何使用jstat监控JVM的GC情况？（答：使用jstat -gc <pid>命令，定期查看GC统计信息，分析内存使用和GC频率。）",
      "如何使用jmap生成堆转储？（答：使用jmap -dump:format=b,file=<file_path> <pid>命令，生成堆转储文件，用于后续分析。）",
      "如何使用jstack分析线程死锁？（答：使用jstack <pid>命令生成线程快照，查看线程堆栈，寻找互相等待的锁资源，确认死锁情况。）"
    ],
    "related": [
      {
        "id": "java-class-file-structure",
        "kind": "compare",
        "note": "类文件结构与监控工具都涉及JVM运行状态分析"
      },
      {
        "id": "java-class-loading-process",
        "kind": "compare",
        "note": "类加载过程与监控工具都涉及JVM运行状态分析"
      },
      {
        "id": "java-jvm-garbage-collection",
        "kind": "compare",
        "note": "垃圾回收机制与监控工具都涉及JVM运行状态分析"
      },
      {
        "id": "java-jvm-intro",
        "kind": "prereq",
        "note": "了解JVM整体架构是使用监控工具的前提"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "监控工具",
          "lines": [
            "jps：列出Java进程主类和PID",
            "jstat：收集GC/内存/编译数据",
            "jinfo：查看/调整JVM参数"
          ]
        },
        {
          "title": "诊断工具",
          "lines": [
            "jmap：生成堆转储分析内存泄漏",
            "jhat：分析heapdump（JDK9后移除）",
            "jstack：生成线程快照定位死锁"
          ]
        }
      ],
      "frames": [
        {
          "note": "监控工具适合日常运行状态检查，如jps用于快速识别Java进程",
          "active": [
            0
          ]
        },
        {
          "note": "诊断工具用于异常排查，如jmap分析OOM原因，jstack定位线程死锁",
          "active": [
            1
          ]
        }
      ]
    }
  },
  {
    "id": "java-jvm-garbage-collection",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "JVM"
    ],
    "tags": [
      "Java",
      "JVM"
    ],
    "title": "JVM垃圾回收详解（重点）",
    "oneLine": "JVM垃圾回收是自动管理对象内存的机制，通过算法和分代策略实现对象的回收与分配。",
    "analogy": "垃圾回收就像整理房间，把不再使用的物品清理出去，让空间更整洁。",
    "why": "Java程序运行时，对象会不断创建和销毁，若不及时回收无用对象，会导致内存溢出。垃圾回收机制通过算法和分代策略，自动识别并回收无用对象，释放内存资源，确保程序稳定运行。",
    "mechanism": [
      "JVM垃圾回收是自动管理对象内存的机制，通过算法和分代策略实现对象的回收与分配。它主要分为标记清除、复制、标记整理三种算法，以及分代回收机制。",
      "标记清除算法通过标记存活对象并清除无用对象，但会产生内存碎片，影响后续分配。",
      "复制算法将内存分为两块，每次只使用其中一块，存活对象复制到另一块，解决内存碎片问题，但空间利用率低。",
      "标记整理算法先标记存活对象，再将它们整理到内存一端，消除碎片，但需要移动对象，开销较大。",
      "分代回收机制将堆分为新生代和老年代，新生代采用复制算法，老年代采用标记整理算法，提高回收效率。",
      "新生代内存（Eden区和两个Survivor区）用于存放新创建的对象，大对象直接进入老年代，长期存活的对象也会晋升到老年代。",
      "垃圾回收器如Serial、Parallel、CMS、G1、ZGC、Shenandoah等，根据分代策略和算法选择不同的回收策略，优化性能。",
      "空间分配担保机制确保Minor GC时老年代有足够的空间容纳新生代对象，避免Full GC，提高回收效率。"
    ],
    "keywords": [
      "JVM垃圾回收",
      "GC算法",
      "垃圾回收器",
      "分代回收",
      "标记清除",
      "复制算法",
      "G1 GC",
      "ZGC"
    ],
    "scene": [
      "Web应用服务器在高并发时，需要频繁回收无用对象，避免内存溢出。",
      "大数据处理程序中，大对象直接进入老年代，减少新生代GC频率。",
      "移动应用开发中，使用ZGC或Shenandoah回收器，降低GC停顿时间。"
    ],
    "interviewQ": [
      "如何判断对象是否死亡（两种方法）？（答：引用计数法和可达性分析算法。前者无法解决循环引用问题，后者通过GC Roots进行可达性分析。）",
      "简述强引用、软引用、弱引用、虚引用的区别。（答：强引用不会被回收，软引用在内存不足时回收，弱引用在GC时回收，虚引用仅用于跟踪对象被回收。）",
      "Minor GC和Full GC有什么不同？（答：Minor GC只回收新生代，Full GC回收整个堆及方法区，Full GC更耗时且影响性能。）"
    ],
    "related": [
      {
        "id": "java-class-file-structure",
        "kind": "prereq",
        "note": "垃圾回收机制依赖类文件结构中的对象信息"
      },
      {
        "id": "java-class-loading-process",
        "kind": "prereq",
        "note": "垃圾回收机制依赖类加载过程中的对象信息"
      },
      {
        "id": "java-jvm-intro",
        "kind": "prereq",
        "note": "了解JVM整体架构是理解垃圾回收机制的前提"
      },
      {
        "id": "java-classloader",
        "kind": "compare",
        "note": "类加载器与垃圾回收都涉及对象生命周期管理"
      },
      {
        "id": "java-jdk-monitoring-and-troubleshooting-tools",
        "kind": "compare",
        "note": "垃圾回收机制与监控工具都涉及JVM运行状态分析"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "标记清除",
          "lines": [
            "标记存活对象，清除无用对象",
            "产生内存碎片，影响分配",
            "适用于老年代回收"
          ]
        },
        {
          "title": "复制算法",
          "lines": [
            "内存分为两块，存活对象复制",
            "解决碎片问题，空间利用率低",
            "适用于新生代回收"
          ]
        },
        {
          "title": "标记整理",
          "lines": [
            "标记存活对象，整理到一端",
            "消除碎片，但需移动对象",
            "适用于老年代回收"
          ]
        }
      ],
      "frames": [
        {
          "note": "标记清除算法适合老年代，但会导致内存碎片，影响后续对象分配。",
          "active": [
            0
          ]
        },
        {
          "note": "复制算法通过空间换时间，解决碎片问题，但空间利用率低，适合新生代。",
          "active": [
            1
          ]
        },
        {
          "note": "标记整理算法通过移动对象消除碎片，但开销较大，适合老年代的高吞吐场景。",
          "active": [
            2
          ]
        }
      ]
    }
  },
  {
    "id": "java-jvm-intro",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "JVM"
    ],
    "tags": [
      "Java",
      "JVM"
    ],
    "title": "大白话带你认识 JVM",
    "oneLine": "JVM 是 Java 虚拟机，负责运行 Java 程序，通过类加载和运行时数据区管理内存。",
    "analogy": "JVM 像是家里的小电脑，负责把 Java 代码翻译成机器能理解的指令，同时管理内存，确保程序顺畅运行。",
    "why": "Java 跨平台的核心在于 JVM，它屏蔽了不同操作系统的差异，让 Java 代码能在任何支持 JVM 的设备上运行。JVM 通过类加载机制和运行时数据区管理内存，确保程序安全高效执行，避免直接操作硬件带来的复杂性。",
    "mechanism": [
      "JVM 是 Java 虚拟机，它是一个规范，通过模拟计算机功能在实际操作系统上运行 Java 程序，实现跨平台特性。",
      "Java 源代码编译后生成 .class 字节码文件，JVM 通过类加载器将这些字节码文件加载到内存中，完成程序的初始化。",
      "运行时数据区包括方法区、堆、栈、程序计数器等区域，方法区存储类元数据，堆存放对象实例，栈用于方法调用和局部变量存储，程序计数器记录当前执行位置。",
      "类加载器负责将 .class 文件加载到 JVM 中，经过验证、准备、解析、初始化等步骤，确保类的正确性和安全性。",
      "类加载器遵循双亲委派机制，优先委托父类加载器加载类，避免用户自定义类覆盖系统核心类，保证类的唯一性。",
      "虚拟机栈用于方法调用和执行，每个方法调用生成一个栈帧，保存局部变量、操作数栈等信息，实现方法的调用和返回。",
      "堆是 JVM 中最大的内存区域，用于存储对象实例，垃圾收集器定期回收不再使用的对象，释放内存空间。",
      "JVM 通过运行时数据区和类加载机制，实现 Java 程序的执行和内存管理，确保程序的稳定性和安全性。"
    ],
    "keywords": [
      "JVM 基础",
      "类加载",
      "方法区",
      "堆栈",
      "程序计数器",
      "运行时数据区"
    ],
    "scene": [
      "Web 服务器运行 Java 应用时，JVM 管理内存和类加载，确保请求处理的稳定性。",
      "开发工具中运行 Java 程序时，JVM 负责编译字节码并执行，提供调试和运行环境。",
      "移动应用中使用 Java 语言时，JVM 在 Android 系统中模拟运行环境，实现跨平台兼容性。"
    ],
    "interviewQ": [
      "JVM 的运行时数据区包括哪些区域？（答：包括方法区、堆、栈、程序计数器和本地方法栈，其中方法区和堆是线程共享区域，栈和程序计数器是线程私有区域。）",
      "类加载器的双亲委派机制是什么？（答：类加载器在加载类时优先委托父类加载器，确保系统类的唯一性，避免用户自定义类覆盖核心类。）",
      "JVM 的堆和栈分别用于什么？（答：堆用于存储对象实例，栈用于方法调用和局部变量存储，两者在内存管理中分工明确。）"
    ],
    "related": [
      {
        "id": "java-memory-area",
        "kind": "prereq",
        "note": "了解内存区域是理解JVM运行机制的基础"
      },
      {
        "id": "java-class-loading-process",
        "kind": "extends",
        "note": "类加载过程是JVM运行时的基础流程"
      },
      {
        "id": "java-jvm-parameters-intro",
        "kind": "compare",
        "note": "基础配置与JVM整体概念形成对比，帮助理解优化方向"
      },
      {
        "id": "java-classloader",
        "kind": "extends",
        "note": "类加载器是JVM执行Java程序的关键组件"
      },
      {
        "id": "java-jvm-garbage-collection",
        "kind": "extends",
        "note": "垃圾回收是JVM运行时内存管理的核心机制"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "编译生成字节码",
        "类加载验证",
        "运行时内存管理"
      ],
      "frames": [
        {
          "s": 0,
          "note": "Java 源码编译为 .class 字节码，是 JVM 执行的基础文件格式"
        },
        {
          "s": 1,
          "note": "类加载器验证字节码安全性，准备类元数据并解析符号引用"
        },
        {
          "s": 2,
          "note": "堆栈区分配内存，程序计数器追踪执行位置，实现方法调用和返回"
        }
      ]
    }
  },
  {
    "id": "java-jvm-parameters-intro",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "JVM"
    ],
    "tags": [
      "Java",
      "JVM"
    ],
    "title": "推荐的基础JVM配置",
    "oneLine": "JVM基础配置包括堆内存、新生代、元空间和GC参数，用于优化性能和内存使用。",
    "analogy": "就像整理房间，合理分配空间和工具，避免杂乱和浪费，让生活更高效。",
    "why": "JVM配置直接影响Java应用的性能和稳定性。堆内存不足会导致OOM，新生代过小会增加Full GC频率，元空间未限制可能占用过多本地内存。合理配置可以减少内存浪费、提升GC效率、避免性能瓶颈，确保应用稳定运行。",
    "mechanism": [
      "堆内存（-Xms和-Xmx）是JVM管理的最大内存区域，用于存放对象实例。设置初始和最大堆大小可以平衡内存使用和GC频率，避免频繁调整堆容量带来的性能开销。",
      "新生代（Young Generation）是堆内存中用于存放新对象的区域，通过-Xmn或-XX:NewSize/-XX:MaxNewSize设置大小。新生代过小会导致频繁Minor GC，过大则可能增加Full GC概率，需根据GC日志调整。",
      "元空间（Metaspace）用于存储类元数据，通过-XX:MetaspaceSize和-XX:MaxMetaspaceSize设置初始和最大值。未限制元空间可能导致本地内存被耗尽，影响系统稳定性。",
      "垃圾收集器（GC）选择直接影响应用的吞吐量和延迟。例如，G1 GC适合低延迟场景，Parallel GC适合高吞吐量场景，需根据应用需求选择合适的GC策略。",
      "ZGC和Shenandoah是低延迟GC，适用于对响应时间敏感的应用。ZGC通过-XX:ZAllocationSpikeTolerance和-XX:ZCollectionInterval调整回收间隔，确保内存使用合理。",
      "合理配置JVM参数可以减少内存浪费、提升GC效率、避免性能瓶颈，确保Java应用在不同负载下稳定运行。",
      "通过分析GC日志，可以判断新生代空间分配是否合理，若大量对象过早进入老年代，需适当调整新生代大小，减少Full GC频率。",
      "JVM参数配置需结合具体应用需求和系统环境，避免盲目复制他人配置，需根据实际负载和GC日志进行调优。"
    ],
    "keywords": [
      "JVM 参数",
      "堆大小",
      "栈大小",
      "GC 设置",
      "性能调优",
      "XX 参数"
    ],
    "scene": [
      "Web应用服务器在高并发场景下，需合理配置堆内存和GC策略，避免频繁Full GC导致响应延迟。",
      "微服务架构中，每个服务需独立配置JVM参数，防止内存泄漏和资源争抢，确保服务稳定性。",
      "大数据处理应用在内存密集型任务中，需调整元空间和堆大小，避免内存溢出和GC停顿影响性能。"
    ],
    "interviewQ": [
      "为什么在JVM中设置-Xms和-Xmx为相同值？（答：减少运行时调整堆容量的开销，避免频繁GC。）",
      "如何调整新生代大小以减少Full GC频率？（答：通过-XX:NewSize/-XX:MaxNewSize或-Xmn设置，根据GC日志判断是否需要调整。）",
      "元空间未设置最大值可能导致什么问题？（答：可能占用过多本地内存，导致系统内存不足，引发OOM错误。）",
      "如何选择适合低延迟场景的垃圾收集器？（答：使用ZGC或Shenandoah，它们通过并发回收减少停顿时间。）"
    ],
    "related": [
      {
        "id": "java-jvm-garbage-collection",
        "kind": "compare",
        "note": "垃圾回收参数与内存配置共同影响JVM性能"
      },
      {
        "id": "java-jvm-intro",
        "kind": "prereq",
        "note": "JVM基础概念是配置参数的理论支撑"
      },
      {
        "id": "java-class-loading-process",
        "kind": "compare",
        "note": "类加载流程与内存配置共同影响JVM性能"
      },
      {
        "id": "java-classloader",
        "kind": "compare",
        "note": "类加载器配置与内存参数共同构成JVM运行环境"
      },
      {
        "id": "java-memory-area",
        "kind": "compare",
        "note": "内存区域划分与参数配置共同决定JVM运行行为"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "高吞吐场景",
          "lines": [
            "使用Parallel GC",
            "堆内存设置-Xms=Xmx",
            "新生代占比约1/3",
            "减少Full GC频率"
          ]
        },
        {
          "title": "低延迟场景",
          "lines": [
            "使用G1 GC或ZGC",
            "堆内存预留冗余空间",
            "新生代占比约1/2",
            "控制GC停顿时间"
          ]
        },
        {
          "title": "微服务架构",
          "lines": [
            "独立配置JVM参数",
            "元空间限制最大值",
            "避免内存泄漏风险",
            "监控GC日志调优"
          ]
        }
      ],
      "frames": [
        {
          "note": "高吞吐场景优先选择Parallel GC，堆内存设置为固定值以减少调整开销，新生代占比控制在1/3以内以平衡Minor GC频率与Full GC概率。",
          "active": [
            0
          ]
        },
        {
          "note": "低延迟场景采用G1或ZGC，堆内存预留冗余空间以应对突发负载，新生代占比提高至1/2以减少对象晋升老年代的频率。",
          "active": [
            1
          ]
        },
        {
          "note": "微服务需独立配置JVM参数，限制元空间最大值防止内存泄漏，通过GC日志分析新生代分配合理性，避免Full GC导致服务不稳定。",
          "active": [
            2
          ]
        }
      ]
    }
  },
  {
    "id": "java-memory-area",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "JVM"
    ],
    "tags": [
      "Java",
      "JVM"
    ],
    "title": "Java内存区域详解（重点）",
    "oneLine": "Java内存区域是JVM运行时数据区，包含堆、方法区、虚拟机栈、本地方法栈、程序计数器，用于管理程序执行过程中的内存分配与回收。",
    "analogy": "就像家庭厨房里的不同区域，堆是大冰箱存放食材，方法区是工具柜存放工具，虚拟机栈是每道菜的临时操作台，程序计数器是厨师的下一步动作指示器。",
    "why": "Java内存区域的设计是为了让JVM能高效管理内存，避免程序员手动管理内存带来的复杂性和错误。堆用于存储对象实例，方法区存储类信息，虚拟机栈支持方法调用和执行，程序计数器控制代码执行流程。这些区域的划分使得内存管理更清晰，也便于垃圾回收和线程隔离。",
    "mechanism": [
      "堆是Java内存区域中最大的一块，用于存储对象实例，是被所有线程共享的内存区域。堆的内存分配和回收由垃圾回收器管理，对象的创建和销毁都在堆中完成。",
      "方法区用于存储已被加载的类信息、常量、静态变量、即时编译器编译后的代码等数据。在JDK 1.8中，方法区被元空间（Metaspace）取代，元空间使用本地内存，避免了永久代（PermGen）的内存溢出问题。",
      "虚拟机栈是线程私有的，每个线程在创建时都会分配一个虚拟机栈。栈由多个栈帧组成，每个栈帧对应一个方法的调用。栈帧中包含局部变量表、操作数栈、动态链接和返回地址等信息，用于支持方法调用和执行。",
      "本地方法栈用于支持Native方法的执行，与虚拟机栈功能类似，但在HotSpot虚拟机中，本地方法栈和虚拟机栈是合二为一的，统一使用虚拟机栈来实现。",
      "程序计数器用于记录当前线程执行的字节码指令地址，是线程私有的。当线程执行Java方法时，程序计数器记录当前指令地址；当线程执行Native方法时，程序计数器的值为Undefined。",
      "Java内存区域的设计使得JVM能够高效管理内存，避免内存泄漏和内存溢出问题。堆和方法区是线程共享的，而虚拟机栈、本地方法栈和程序计数器是线程私有的，这种划分有助于线程隔离和并发执行。",
      "内存区域的划分也影响了垃圾回收策略。堆是垃圾回收的主要区域，而方法区（元空间）的垃圾回收相对较少，因为类信息和常量通常不会被频繁回收。"
    ],
    "keywords": [
      "JVM内存区域",
      "运行时数据区",
      "堆内存",
      "方法区",
      "虚拟机栈",
      "程序计数器",
      "对象创建",
      "Java内存模型"
    ],
    "scene": [
      "Web应用中，堆内存用于存储大量对象实例，如用户数据、请求参数等，若堆内存不足可能导致OOM。",
      "多线程程序中，虚拟机栈用于支持每个线程的独立执行，若栈深度过大可能引发StackOverflowError。",
      "使用Native方法时，本地方法栈用于调用C/C++代码，若本地方法栈内存不足可能导致内存溢出。"
    ],
    "interviewQ": [
      "对象创建过程的五步是什么？（答：第一步检查类是否被加载、解析和初始化；第二步为新生对象分配内存；第三步初始化零值；第四步设置对象头；第五步执行<init>方法。）",
      "对象访问定位的两种方式是什么？（答：句柄方式和直接指针方式。句柄方式通过句柄访问对象，而直接指针方式直接通过对象地址访问。）",
      "程序计数器在多线程环境下如何工作？（答：每个线程都有独立的程序计数器，记录当前线程执行的位置，线程切换时能恢复执行位置。）"
    ],
    "related": [
      {
        "id": "java-jvm-intro",
        "kind": "prereq",
        "note": "JVM基础概念是理解内存区域划分的前提"
      },
      {
        "id": "java-classloader",
        "kind": "extends",
        "note": "类加载器与内存区域共同构成JVM运行环境"
      },
      {
        "id": "java-jvm-garbage-collection",
        "kind": "extends",
        "note": "垃圾回收机制是内存区域管理的重要组成部分"
      },
      {
        "id": "java-class-loading-process",
        "kind": "extends",
        "note": "类加载过程与内存区域管理紧密相关"
      },
      {
        "id": "java-jvm-parameters-intro",
        "kind": "compare",
        "note": "内存区域划分与参数配置共同决定JVM运行行为"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "堆内存",
          "lines": [
            "存储对象实例，线程共享",
            "由垃圾回收器管理",
            "OOM风险最高区域"
          ]
        },
        {
          "title": "方法区/元空间",
          "lines": [
            "存储类信息、常量、静态变量",
            "JDK1.8后使用本地内存",
            "GC频率较低"
          ]
        },
        {
          "title": "线程私有区域",
          "lines": [
            "虚拟机栈：方法调用与执行",
            "本地方法栈：Native代码执行",
            "程序计数器：记录字节码地址"
          ]
        }
      ],
      "frames": [
        {
          "note": "堆内存是JVM中最大的共享区域，负责对象实例的存储与回收，是GC的主要目标。",
          "active": [
            0
          ]
        },
        {
          "note": "元空间替代永久代，使用本地内存，避免了PermGen内存溢出问题，但GC频率较低。",
          "active": [
            1
          ]
        },
        {
          "note": "线程私有区域（栈、程序计数器）支持多线程并发执行，栈深度过大可能导致StackOverflowError。",
          "active": [
            2
          ]
        }
      ]
    }
  },
  {
    "id": "java-java8-common-new-features",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 新特性"
    ],
    "tags": [
      "Java",
      "Java 新特性"
    ],
    "title": "Java8 新特性实战",
    "oneLine": "Java8 引入 Lambda、Stream、Optional 等新特性，提升代码简洁性和功能性。",
    "analogy": "就像用快递代替排队，Java8 的 Lambda 表达式让代码更简洁，像快递一样高效传递功能。",
    "why": "Java8 新特性旨在解决传统代码冗长、可读性差的问题。Lambda 表达式让函数式编程更简单，Stream API 提高数据处理效率，Optional 避免 null 引起的错误，Date-Time API 更精确地处理时间，这些改进使得 Java 更现代化，适应复杂业务需求。",
    "mechanism": [
      "Lambda 表达式是 Java8 引入的函数式编程特性，允许将函数作为参数传递给方法，简化代码结构。",
      "Stream API 提供了对集合的高效操作，通过链式调用实现过滤、映射、归约等操作，提升代码可读性和性能。",
      "Optional 类用于封装可能为 null 的值，避免直接使用 null 导致的空指针异常，使代码更安全。",
      "Date-Time API 提供了更精确的时间和日期处理功能，支持时区、格式化和时间计算，解决了传统 Date 类的缺陷。",
      "接口默认方法允许在接口中定义默认实现，解决接口升级时的兼容性问题，同时保持接口的扩展性。",
      "函数式接口是只有一个抽象方法的接口，用于支持 Lambda 表达式和方法引用，使代码更简洁。",
      "方法引用允许直接调用已有方法，简化 Lambda 表达式的写法，提高代码的可读性和复用性。"
    ],
    "keywords": [
      "Lambda",
      "Stream API",
      "Optional",
      "Date/Time API",
      "默认方法",
      "函数式接口"
    ],
    "scene": [
      "在数据处理场景中，使用 Stream API 对集合进行过滤和转换，提升代码效率。",
      "在 Web 开发中，使用 Optional 避免 null 值，防止空指针异常，提高系统稳定性。",
      "在时间计算场景中，使用 Date-Time API 处理时间差、时区转换，确保时间计算的准确性。"
    ],
    "interviewQ": [
      "Lambda 表达式和函数式接口的关系是什么？（答：Lambda 表达式需要函数式接口作为目标类型，函数式接口只有一个抽象方法，使得 Lambda 表达式可以简洁地实现该方法。）",
      "Stream API 和传统的集合遍历有什么区别？（答：Stream API 提供了链式操作和函数式编程方式，使数据处理更简洁高效，而传统遍历需要显式编写循环和条件判断。）",
      "Optional 类如何避免空指针异常？（答：Optional 类封装可能为 null 的值，强制调用者使用 isPresent() 或 get() 方法，避免直接访问 null 值，提高代码安全性。）"
    ],
    "related": [
      {
        "id": "java-jvm-intro",
        "kind": "compare",
        "note": "JVM基础概念与Java8新特性共同构成Java生态"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "Lambda 表达式",
          "lines": [
            "简化函数式编程语法",
            "支持方法引用简化代码",
            "提升代码可读性与复用"
          ]
        },
        {
          "title": "Stream API",
          "lines": [
            "链式操作集合数据",
            "支持过滤、映射、归约",
            "提升性能与可读性"
          ]
        },
        {
          "title": "Optional 类",
          "lines": [
            "封装可能为 null 的值",
            "避免空指针异常",
            "增强代码安全性"
          ]
        }
      ],
      "frames": [
        {
          "note": "Lambda 表达式通过函数式接口实现，使代码更简洁，减少冗余。",
          "active": [
            0
          ]
        },
        {
          "note": "Stream API 通过链式调用实现高效集合操作，提升代码可读性和性能。",
          "active": [
            1
          ]
        },
        {
          "note": "Optional 类通过封装 null 值，避免空指针异常，提升代码安全性。",
          "active": [
            2
          ]
        }
      ]
    }
  },
  {
    "id": "java-basicq01",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "Java 语言有哪些特点？",
    "oneLine": "Java 是一种面向对象、平台无关、支持多线程的编程语言，具有可靠性、安全性、高效性等特点。",
    "analogy": "Java 就像一个全能的厨师，能做各种菜式，而且不管在哪种厨房都能用，还能同时处理多个任务。",
    "why": "Java 的特点源于其设计目标和应用场景。在早期，Java 被设计为一种跨平台的语言，以适应网络环境下的应用开发。随着技术发展，虽然跨平台不再是唯一优势，但其生态、安全性和多线程支持使其在企业级应用中依然占据重要地位。Java 的可靠性、安全性、高效性等特点，使其在开发复杂系统时具有显著优势。",
    "mechanism": [
      "Java 是一种面向对象的编程语言，通过封装、继承和多态等特性，使代码结构更清晰、可重用性更高。",
      "Java 具有平台无关性，通过 Java 虚拟机（JVM）实现，使得 Java 程序可以在任何支持 JVM 的平台上运行。",
      "Java 支持多线程，提供了内置的多线程机制，允许程序同时执行多个任务，提高程序的并发性能。",
      "Java 具备异常处理机制，可以在程序运行过程中捕获和处理错误，提高程序的健壮性。",
      "Java 采用自动内存管理机制，通过垃圾回收（GC）自动回收不再使用的对象，减少内存泄漏的风险。",
      "Java 提供了多重安全防护机制，如访问权限修饰符、限制程序直接访问操作系统资源等，确保程序运行的安全性。",
      "Java 通过 Just In Time（JIT）编译器等技术优化运行效率，使 Java 程序在实际运行中表现良好。",
      "Java 支持网络编程，提供了丰富的网络 API，方便开发网络应用和分布式系统。"
    ],
    "keywords": [
      "面向对象",
      "平台无关性",
      "多线程",
      "异常处理",
      "自动内存管理",
      "安全性"
    ],
    "scene": [
      "企业级应用开发中，Java 常用于构建大型系统，如银行、电商等，因其稳定性和安全性。",
      "跨平台开发中，Java 程序可以在不同操作系统上运行，适合开发桌面应用或移动应用。",
      "多线程编程中，Java 提供了内置的线程支持，适合开发高性能的并发应用。"
    ],
    "interviewQ": [
      "Java 的多线程机制是如何实现的？（答：Java 提供了内置的多线程支持，允许程序同时执行多个任务，提高并发性能。）",
      "Java 的平台无关性是如何实现的？（答：Java 通过 Java 虚拟机（JVM）实现平台无关性，使得 Java 程序可以在任何支持 JVM 的平台上运行。）",
      "Java 的安全性体现在哪些方面？（答：Java 提供了多重安全防护机制，如访问权限修饰符、限制程序直接访问操作系统资源等，确保程序运行的安全性。）"
    ],
    "related": [
      {
        "id": "java-basicq05",
        "kind": "compare",
        "note": "Java语言特性与编译解释机制形成对比，帮助理解语言设计"
      },
      {
        "id": "javasevsjavaee",
        "kind": "compare",
        "note": "Java SE与Java EE区别与语言特性形成对比，帮助理解语言设计"
      },
      {
        "id": "java-basicq25",
        "kind": "compare",
        "note": "方法返回值与语言特性形成对比，帮助理解语言设计"
      },
      {
        "id": "java-basicq15",
        "kind": "compare",
        "note": "基本数据类型与语言特性形成对比，帮助理解语言设计"
      },
      {
        "id": "java-basicq17",
        "kind": "compare",
        "note": "包装类型缓存机制与语言特性形成对比，帮助理解语言设计"
      }
    ],
    "diagram": null
  },
  {
    "id": "javasevsjavaee",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "Java SE 与 Java EE 的区别是什么？",
    "oneLine": "Java SE 是 Java 的基础版本，用于开发桌面和简单服务器应用；Java EE 是企业级应用开发的标准，包含更多企业级功能。",
    "analogy": "Java SE 像是做菜的基本调料，而 Java EE 则像是完整的菜谱和厨房设备，能做出更复杂的菜肴。",
    "why": "Java SE 提供了 Java 编程语言的基础功能，如核心类库和虚拟机，适合开发简单的应用程序。而 Java EE 在此基础上增加了企业级开发所需的组件，如 Servlet、JSP 等，使得开发复杂、分布式和安全的企业级应用成为可能。Java EE 的出现是为了满足企业对高性能、可扩展和可维护性应用的需求。",
    "mechanism": [
      "Java SE 是 Java 平台标准版，包含 Java 编程语言的核心功能，如基础类库、虚拟机等，用于开发桌面和简单服务器应用。",
      "Java EE 建立在 Java SE 的基础上，增加了企业级开发所需的组件，如 Servlet、JSP、EJB 等，用于构建复杂的分布式服务端应用。",
      "Java EE 提供了标准和规范，如 JDBC、JPA、JMS 等，使得企业级应用能够实现数据访问、事务管理、消息传递等功能。",
      "Java EE 的设计目标是支持可移植性、健壮性、可伸缩性和安全性，使得企业级应用能够在不同的环境中运行并满足高并发和高可用性需求。",
      "Java EE 的组件如 Servlet 和 JSP 用于构建 Web 应用程序，而 EJB 用于实现业务逻辑的封装和管理。",
      "Java EE 的 JavaMail 和 JMS 用于处理邮件和消息队列，使得企业级应用能够实现异步通信和数据传输。",
      "Java EE 的出现解决了传统 Java 应用在开发复杂企业级应用时的不足，如缺乏标准、组件支持和安全性保障。"
    ],
    "keywords": [
      "Java SE",
      "Java EE",
      "Servlet",
      "JSP",
      "EJB",
      "JDBC",
      "JPA",
      "JTA"
    ],
    "scene": [
      "开发桌面应用程序时，通常使用 Java SE，因为它提供了基础的类库和虚拟机支持。",
      "构建企业级 Web 应用程序时，Java EE 提供了 Servlet、JSP、JDBC 等组件，使得开发更加高效。",
      "在需要处理分布式系统和消息传递的场景中，Java EE 的 JMS 和 EJB 能够提供支持。"
    ],
    "interviewQ": [
      "Java EE 与 Java SE 的主要区别是什么？（答：Java SE 是基础版本，用于开发桌面和简单服务器应用；Java EE 是企业级应用开发的标准，包含更多企业级功能。）",
      "Java EE 中的 Servlet 和 JSP 有什么作用？（答：Servlet 用于处理 HTTP 请求，JSP 用于生成动态网页内容，两者共同构建 Web 应用程序。）",
      "Java EE 中的 EJB 有什么作用？（答：EJB 用于封装业务逻辑，提供事务管理、安全性和远程调用等功能，使得企业级应用更加健壮和可维护。）"
    ],
    "related": [
      {
        "id": "jvmvsjdkvsjre",
        "kind": "prereq",
        "note": "了解 JVM、JDK、JRE 的关系，才能更好理解 Java SE 和 Java EE 的区别"
      },
      {
        "id": "java-basicq05",
        "kind": "prereq",
        "note": "理解 Java 编译与解释并存的机制，有助于区分 SE 和 EE 的运行原理"
      },
      {
        "id": "java-basicq01",
        "kind": "compare",
        "note": "Java SE与Java EE区别与语言特性形成对比，帮助理解语言设计"
      },
      {
        "id": "oraclejdkvsopenjdk",
        "kind": "compare",
        "note": "对比 Java SE 与 Java EE 的区别，能更清晰理解 JDK 的不同版本定位"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "Java SE",
          "lines": [
            "基础版本，包含核心类库和JVM",
            "用于桌面和简单服务器应用",
            "提供基础语言功能和运行环境"
          ]
        },
        {
          "title": "Java EE",
          "lines": [
            "基于Java SE的企业级开发标准",
            "包含Servlet、JSP、EJB等组件",
            "支持分布式系统和消息传递"
          ]
        }
      ],
      "frames": [
        {
          "note": "Java EE 更适合开发复杂企业级应用，而 Java SE 适合基础开发",
          "active": [
            0,
            1
          ]
        },
        {
          "note": "Java EE 提供了标准规范，如 JDBC 和 JPA，提升开发效率和可移植性",
          "active": [
            0,
            1
          ]
        },
        {
          "note": "Java EE 的 JMS 和 EJB 支持异步通信和业务逻辑封装，满足高并发需求",
          "active": [
            0,
            1
          ]
        }
      ]
    }
  },
  {
    "id": "jvmvsjdkvsjre",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "JVM vs JDK vs JRE 是什么关系？",
    "oneLine": "JVM 是运行 Java 字节码的虚拟机，JDK 是开发工具包，JRE 是运行环境。",
    "analogy": "JVM 像是不同城市的出租车，JDK 是造出租车的工厂，JRE 是出租车司机和车。",
    "why": "Java 要实现跨平台运行，必须通过 JVM 将字节码转换为不同系统的机器码。JDK 提供开发工具，JRE 提供运行环境。JVM 是核心，JDK 和 JRE 是围绕 JVM 的扩展。随着 Java 模块化，JRE 逐渐被更灵活的 jlink 替代。",
    "mechanism": [
      "JVM 是 Java 虚拟机，它负责运行 Java 字节码，实现 Java 的跨平台特性。",
      "JDK 是 Java 开发工具包，包含 JRE、编译器 javac、文档生成器 javadoc、调试器 jdb 等工具，用于开发和调试 Java 程序。",
      "JRE 是 Java 运行环境，包含 JVM 和 Java 基础类库，用于运行已编译的 Java 程序。",
      "JDK 9 引入模块系统，将 JDK 重新组织为 94 个模块，允许开发者使用 jlink 工具创建自定义运行时映像。",
      "JRE 在 JDK 9 后逐渐被模块化运行时替代，jlink 可以生成更小的运行时环境，提升部署效率。",
      "JVM 规范允许不同厂商实现自己的 JVM，如 HotSpot、J9、Zing 等，确保 Java 程序在不同平台运行。",
      "JDK 和 JRE 的关系在 JDK 9 后被模块化系统取代，开发者可以根据需求选择模块，减少运行时依赖。"
    ],
    "keywords": [
      "JVM",
      "JDK",
      "JRE",
      "模块系统",
      "jlink"
    ],
    "scene": [
      "开发 Java 应用时，需要安装 JDK 来编译和调试代码。",
      "部署 Java 应用时，只需要 JRE 来运行程序，无需开发工具。",
      "在容器化或云原生环境中，使用 jlink 创建定制运行时，减少镜像体积。"
    ],
    "interviewQ": [
      "JVM、JDK、JRE 三者的关系是什么？（答：JVM 是运行环境，JDK 包含 JRE 和开发工具，JRE 是运行 Java 程序所需环境。）",
      "JDK 9 后如何管理 JRE？（答：通过模块系统和 jlink 工具，创建定制运行时，减少依赖。）",
      "为什么 JVM 要支持不同平台？（答：JVM 实现 Java 的跨平台特性，确保字节码在不同系统上运行。）"
    ],
    "related": [
      {
        "id": "java-basicq05",
        "kind": "prereq",
        "note": "了解 Java 编译与解释并存的机制，有助于理解 JVM、JDK、JRE 的作用"
      },
      {
        "id": "javasevsjavaee",
        "kind": "prereq",
        "note": "理解 Java SE 和 Java EE 的区别，有助于理解 JVM、JDK、JRE 的关系"
      },
      {
        "id": "java-basicq04",
        "kind": "extends",
        "note": "了解 JVM、JDK、JRE 的关系，才能更好理解字节码的运行环境"
      },
      {
        "id": "java-basicq06",
        "kind": "extends",
        "note": "了解 JVM、JDK、JRE 的关系，才能更好理解 AOT 的运行环境"
      },
      {
        "id": "oraclejdkvsopenjdk",
        "kind": "extends",
        "note": "了解 JVM、JDK、JRE 的关系，才能理解 Oracle JDK 和 OpenJDK 的区别"
      }
    ],
    "diagram": null
  },
  {
    "id": "java-basicq04",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "什么是字节码？采用字节和的好处是什么？",
    "oneLine": "字节码是 JVM 可以理解的中间代码，用于解决 Java 语言的可移植性和执行效率问题。",
    "analogy": "字节码就像快递员配送的包裹，它不直接送到用户手中，而是先送到快递站，再由快递站根据收件人地址分发到不同地方。",
    "why": "传统解释型语言执行效率低，而字节码通过 JVM 实现了跨平台运行，同时借助 JIT 编译器将热点代码编译为机器码，提升了执行效率。字节码不针对特定机器，因此 Java 程序无需重新编译即可在不同操作系统上运行，解决了可移植性问题。",
    "mechanism": [
      "字节码是 Java 源代码编译后的中间代码，扩展名为 `.class`，由 JVM 解释执行。",
      "JVM 加载字节码后，首先通过解释器逐行执行，识别频繁调用的方法（即热点代码）。",
      "JIT 编译器将热点代码编译为机器码，使得后续执行时可以直接使用已编译的机器码，提高运行效率。",
      "JIT 编译器采用惰性评估策略，只编译消耗大部分系统资源的热点代码，从而优化资源使用。",
      "JVM 会根据代码执行情况收集信息，进行动态优化，执行次数越多，优化效果越明显。",
      "字节码不针对特定处理器，因此 Java 程序可以在不同操作系统上运行，无需重新编译。",
      "JIT 编译器与解释器共存，使得 Java 语言在编译与解释之间取得平衡，兼顾效率与可移植性。"
    ],
    "keywords": [
      "字节码",
      "JVM",
      "JIT",
      "热点代码",
      "解释器",
      "机器码"
    ],
    "scene": [
      "Java 程序在不同操作系统上运行时，无需重新编译，直接通过 JVM 执行字节码。",
      "JIT 编译器在 JVM 中用于优化热点代码，提高程序运行速度。",
      "JVM 加载字节码后，通过解释器和 JIT 编译器共同执行，实现编译与解释共存。"
    ],
    "interviewQ": [
      "JIT 编译器如何优化热点代码？（答：JIT 编译器识别热点代码，将其编译为机器码，提高执行效率。）",
      "字节码和机器码的区别是什么？（答：字节码是 JVM 可以理解的中间代码，而机器码是计算机可以直接执行的二进制代码。）",
      "Java 为什么能跨平台运行？（答：Java 程序编译为字节码，由 JVM 解释执行，因此可以在不同操作系统上运行。）"
    ],
    "related": [
      {
        "id": "java-basicq05",
        "kind": "prereq",
        "note": "理解 Java 编译与解释并存的机制，有助于理解字节码的作用"
      },
      {
        "id": "jvmvsjdkvsjre",
        "kind": "prereq",
        "note": "了解 JVM、JDK、JRE 的关系，才能更好理解字节码的运行环境"
      },
      {
        "id": "java-basicq13",
        "kind": "compare",
        "note": "了解字节码后，能更清楚移位运算符在底层的实现方式"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "编译生成",
        "JVM 加载",
        "执行优化"
      ],
      "frames": [
        {
          "s": 0,
          "note": "Java 源码编译为字节码，不依赖具体硬件，实现跨平台特性"
        },
        {
          "s": 1,
          "note": "JVM 加载字节码后，解释器逐行执行，识别高频调用的热点代码"
        },
        {
          "s": 2,
          "note": "JIT 编译器将热点代码转为机器码，后续调用直接使用编译结果，提升性能"
        }
      ]
    }
  },
  {
    "id": "java-basicq05",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "为什么说 Java 语言‘编译与解释并存’？",
    "oneLine": "Java 语言通过编译和解释技术结合，实现跨平台运行和性能优化。",
    "analogy": "Java 就像一个会做饭的厨师，先将菜谱翻译成通用的菜谱（字节码），然后根据厨房设备（JVM）选择是直接按菜谱做（解释）还是提前做熟（编译）。",
    "why": "Java 采用编译与解释并存的方式，主要是为了兼顾跨平台性和运行效率。传统的编译型语言如 C、C++ 无法跨平台运行，而解释型语言如 Python 运行效率低。Java 通过编译生成字节码，使代码可以在任何安装了 JVM 的平台上运行，同时利用 JIT 编译技术在运行时将字命码编译为机器码，提升执行效率。这种混合方式既解决了平台兼容性问题，又优化了性能。",
    "mechanism": [
      "Java 源码首先由编译器编译为字节码（.class 文件），字节码是一种中间表示，可以在任何安装了 JVM 的平台上运行。",
      "字节码由 JVM 解释执行，JVM 逐行将字节码翻译为机器码并执行，这种方式类似于解释型语言，具有良好的跨平台性。",
      "JVM 在运行时会使用 JIT（即时编译）技术，将频繁执行的字节码编译为机器码，提升程序的执行效率。",
      "JIT 编译器会分析字节码的执行频率，将热点代码编译为本地机器码，减少解释执行的开销。",
      "JIT 编译器在编译过程中会进行优化，如常量折叠、循环展开等，进一步提升程序性能。",
      "JVM 的执行策略由具体实现决定，可以是纯解释执行，也可以是混合编译与解释执行，甚至完全编译执行。",
      "Java 的这种混合机制使得它在跨平台性和性能之间取得平衡，既保证了代码的可移植性，又提升了运行效率。"
    ],
    "keywords": [
      "字节码",
      "JVM",
      "JIT",
      "编译",
      "解释"
    ],
    "scene": [
      "在开发 Java Web 应用时，服务器会使用 JVM 解释执行字节码，确保代码在不同操作系统上运行。",
      "在高并发的 Java 应用中，JIT 编译器会将热点代码编译为机器码，提升系统吞吐量。",
      "在嵌入式设备或资源受限的环境中，JVM 可能选择纯解释执行，以节省内存和 CPU 资源。"
    ],
    "interviewQ": [
      "Java 为什么需要编译和解释并存？（答：Java 通过编译生成字节码实现跨平台，JIT 编译提升性能，解释执行保证灵活性。）",
      "JIT 编译器在 JVM 中的作用是什么？（答：JIT 编译器将字节码编译为机器码，提升执行效率，同时进行代码优化。）",
      "JVM 如何决定使用编译还是解释执行？（答：JVM 根据具体实现和运行时情况决定，可能混合使用编译和解释，甚至纯编译。）"
    ],
    "related": [
      {
        "id": "java-basicq04",
        "kind": "prereq",
        "note": "理解字节码的作用，有助于理解 Java 编译与解释并存的机制"
      },
      {
        "id": "jvmvsjdkvsjre",
        "kind": "prereq",
        "note": "了解 JVM、JDK、JRE 的关系，才能更好理解 Java 编译与解释并存的机制"
      },
      {
        "id": "java-basicq01",
        "kind": "compare",
        "note": "Java语言特性与编译解释机制形成对比，帮助理解语言设计"
      },
      {
        "id": "javasevsjavaee",
        "kind": "extends",
        "note": "理解 Java 编译与解释并存的机制，有助于区分 SE 和 EE 的运行原理"
      },
      {
        "id": "java-basicq06",
        "kind": "extends",
        "note": "理解 Java 编译与解释并存的机制，有助于理解 AOT 的优缺点"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "源码编译",
        "字节码解释",
        "JIT优化"
      ],
      "frames": [
        {
          "s": 0,
          "note": "Java 源码被编译为字节码，实现跨平台基础"
        },
        {
          "s": 1,
          "note": "JVM 解释字节码为机器码，确保不同平台可运行"
        },
        {
          "s": 2,
          "note": "JIT 编译器识别热点代码，将其编译为机器码提升性能"
        }
      ]
    }
  },
  {
    "id": "java-basicq06",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "AOT 有什么优点？为什么不全部使用 AOT 呢？",
    "oneLine": "AOT 在程序执行前将代码编译为机器码，提升启动速度和运行时内存效率，但存在构建复杂性和动态特性限制。",
    "analogy": "AOT 像是提前把菜切好再下锅，节省了烹饪时间；但有些菜需要临时加料，AOT 无法预知，可能影响口感。",
    "why": "AOT 的优势在于减少运行时的预热开销，提升冷启动性能，适合短生命周期服务。但其依赖构建期的静态分析，无法处理动态加载和反射等运行时行为，限制了灵活性。JIT 虽然启动慢，但能根据运行时数据持续优化热点代码，更适合长时间运行的服务。",
    "mechanism": [
      "AOT 在构建阶段将 Java 代码编译为机器码，避免了运行时的解释执行和 JIT 预热，直接生成可执行文件，提升启动速度。",
      "AOT 编译器如 GraalVM Native Image 会进行闭世界分析，从程序入口出发，分析哪些类、方法和字段可能在运行时被访问，只保留必要代码，减少运行时内存占用。",
      "AOT 编译器需要提前知道所有可能访问的类和方法，对于动态反射、动态代理和 JNI 等运行时行为，必须通过可达性元数据显式声明，否则无法处理。",
      "构建阶段的静态分析无法捕获运行时的动态行为，如动态类加载或字节码生成，这些行为在 AOT 中需要额外的适配和元数据支持。",
      "AOT 生成的本地可执行文件不依赖 JVM，适合 CLI、Serverless 和冷启动敏感的服务，但构建时间更长，且需要处理元数据维护和兼容性适配问题。",
      "JIT 在运行时根据热点代码进行编译优化，能持续提升性能，适合长时间运行的服务，但启动较慢，且运行时内存占用较高。",
      "AOT 和 JIT 各有适用场景，AOT 适合冷启动和内存敏感场景，JIT 适合持续优化和长生命周期服务，两者结合可发挥各自优势。"
    ],
    "keywords": [
      "AOT",
      "JIT",
      "GraalVM",
      "Native Image",
      "闭世界分析",
      "可达性元数据"
    ],
    "scene": [
      "微服务应用在云平台中频繁冷启动，使用 AOT 提升启动速度。",
      "Serverless 服务需要快速启动和低内存占用，AOT 是理想选择。",
      "依赖反射和动态代理的框架在 AOT 中需提供可达性元数据，否则无法正常运行。"
    ],
    "interviewQ": [
      "追问1：AOT 和 JIT 在编译时机和性能表现上有何区别？（答：AOT 在构建阶段编译，提升启动速度；JIT 在运行时编译，优化热点代码，适合长生命周期服务。）",
      "追问2：为什么 AOT 无法处理动态反射和动态类加载？（答：AOT 依赖构建期静态分析，无法预知运行时动态行为，需通过可达性元数据显式声明。）",
      "追问3：AOT 有哪些典型应用场景？（答：冷启动频繁、内存敏感、Serverless 和 CLI 应用，适合短生命周期服务。）"
    ],
    "related": [
      {
        "id": "java-basicq05",
        "kind": "prereq",
        "note": "理解 Java 编译与解释并存的机制，有助于理解 AOT 的优缺点"
      },
      {
        "id": "jvmvsjdkvsjre",
        "kind": "prereq",
        "note": "了解 JVM、JDK、JRE 的关系，才能更好理解 AOT 的运行环境"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "AOT 优点",
          "lines": [
            "启动速度更快，无需 JVM 启动",
            "运行时内存占用更低",
            "适合冷启动敏感场景",
            "不依赖 JVM，适合 CLI/Serverless"
          ]
        },
        {
          "title": "AOT 局限",
          "lines": [
            "构建复杂，需显式声明动态行为",
            "无法处理动态类加载和字节码生成",
            "构建时间更长，兼容性适配复杂",
            "不支持反射、动态代理和 JNI"
          ]
        }
      ],
      "frames": [
        {
          "note": "AOT 适合冷启动和内存敏感场景，如 Serverless 和微服务。",
          "active": [
            0
          ]
        },
        {
          "note": "AOT 需要显式声明动态行为，如反射和动态代理，否则无法处理。",
          "active": [
            1
          ]
        },
        {
          "note": "JIT 适合长生命周期服务，能持续优化性能，但启动较慢。",
          "active": [
            0,
            1
          ]
        }
      ]
    }
  },
  {
    "id": "oraclejdkvsopenjdk",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "Oracle JDK 和 OpenJDK 有什么区别？",
    "oneLine": "Oracle JDK 是 Oracle 基于 OpenJDK 开发的闭源版本，而 OpenJDK 是开源的 Java 开发工具包。",
    "analogy": "就像两家餐厅用同一种食材做菜，一家公开食谱，一家保留秘方，OpenJDK 是公开食谱，Oracle JDK 是保留秘方的版本。",
    "why": "Oracle JDK 和 OpenJDK 的差异源于 Oracle 收购 Sun 后对 Java 的商业化策略。OpenJDK 的开源特性使其更受开发者欢迎，而 Oracle JDK 则提供了额外的工具和商业支持。这种差异让开发者可以根据需求选择合适的版本，同时保障了 Java 的生态多样性。",
    "mechanism": [
      "Oracle JDK 是 Oracle 基于 OpenJDK 开发的闭源版本，它在 OpenJDK 的基础上添加了一些特有功能，如 Java Flight Recorder 和 Java Mission Control。",
      "OpenJDK 是完全开源的 Java 开发工具包，它由 Oracle 和其他开发者共同维护，所有代码都可以查看和修改。",
      "Oracle JDK 的许可协议根据版本不同而变化，部分版本需要付费使用，而 OpenJDK 则遵循 GPLv2 + Classpath Exception 协议，允许商业免费使用。",
      "Oracle JDK 包含一些闭源的第三方组件，如图形光栅化器，而 OpenJDK 则完全由开源社区维护。",
      "Oracle JDK 提供了长期支持（LTS）版本，如 Java 8、11、17、21、25，而 OpenJDK 本身不承诺商业 LTS 服务。",
      "OpenJDK 的开源特性使其可以被定制和优化，例如阿里巴巴基于 OpenJDK 开发了 Dragonwell8。",
      "Oracle JDK 的某些版本需要付费使用，而 OpenJDK 则是免费的，这使得 OpenJDK 成为许多开发者的首选。"
    ],
    "keywords": [
      "OpenJDK",
      "Oracle JDK",
      "GPLv2",
      "Classpath Exception",
      "LTS",
      "NFTC"
    ],
    "scene": [
      "开发人员在构建企业级应用时，可能选择 Oracle JDK 来获得额外的监控工具和商业支持。",
      "开源社区和云服务提供商通常使用 OpenJDK，因为它完全免费且可定制。",
      "在需要长期支持的项目中，开发者可能选择 Oracle 提供的 LTS 版本，而不是 OpenJDK。"
    ],
    "interviewQ": [
      "追问1：Oracle JDK 和 OpenJDK 的主要区别是什么？（答：Oracle JDK 是闭源的，包含一些特有功能和工具，而 OpenJDK 是开源的，完全免费且可定制。）",
      "追问2：为什么开发者更倾向于使用 OpenJDK？（答：OpenJDK 是开源的，允许开发者自由修改和优化，同时免费使用，适合需要灵活性和成本控制的项目。）",
      "追问3：Oracle JDK 的许可证如何影响其使用？（答：Oracle JDK 的许可证根据版本不同而变化，部分版本需要付费使用，而 OpenJDK 则遵循 GPLv2 + Classpath Exception 协议，允许商业免费使用。）"
    ],
    "related": [
      {
        "id": "jvmvsjdkvsjre",
        "kind": "prereq",
        "note": "了解 JVM、JDK、JRE 的关系，才能理解 Oracle JDK 和 OpenJDK 的区别"
      },
      {
        "id": "javasevsjavaee",
        "kind": "compare",
        "note": "对比 Java SE 与 Java EE 的区别，能更清晰理解 JDK 的不同版本定位"
      },
      {
        "id": "java-basicq05",
        "kind": "compare",
        "note": "了解 Java 编译与解释并存的特性，有助于理解 JDK 的运行机制"
      },
      {
        "id": "java-25-lts",
        "kind": "compare",
        "note": "Java 25 LTS 与 JDK 版本选择都涉及 Java 生态，但方向不同"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "Oracle JDK",
          "lines": [
            "基于 OpenJDK 开发",
            "含 Java Flight Recorder",
            "部分版本需付费",
            "提供 LTS 支持"
          ]
        },
        {
          "title": "OpenJDK",
          "lines": [
            "完全开源免费",
            "由社区维护",
            "可定制优化",
            "无商业 LTS 承诺"
          ]
        }
      ],
      "frames": [
        {
          "note": "Oracle JDK 适合需要商业支持和监控工具的企业级应用",
          "active": [
            0
          ]
        },
        {
          "note": "OpenJDK 更适合开源社区和云服务，因其完全免费且可定制",
          "active": [
            1
          ]
        },
        {
          "note": "Oracle JDK 的 LTS 版本如 Java 8、11 等适合长期维护项目",
          "active": [
            0
          ]
        },
        {
          "note": "OpenJDK 的开源特性使其能被优化，如阿里巴巴的 Dragonwell8",
          "active": [
            1
          ]
        }
      ]
    }
  },
  {
    "id": "java-basicq09",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "注释有哪几种形式？",
    "oneLine": "Java 中的注释分为单行注释、多行注释和文档注释，用于解释代码逻辑。",
    "analogy": "注释就像图书馆的书签，帮助读者快速找到想要的信息，避免在书页中迷失。",
    "why": "注释是程序员之间的沟通工具，尤其在项目复杂时，能帮助他人快速理解代码逻辑。但过度注释反而会降低代码的可读性。因此，注释应简洁明了，以补充代码表达不足的部分。",
    "mechanism": [
      "单行注释用于解释某一行代码的作用，通常以 // 开头，只作用于当前行。",
      "多行注释用于解释一段代码的作用，通常以 /* 开头，以 */ 结尾，可以跨越多行。",
      "文档注释用于生成 Java 开发文档，通常以 /** 开头，以 */ 结尾，可以包含详细说明。",
      "单行注释和文档注释在实际开发中使用较多，因为它们能有效提升代码可读性和文档生成效率。",
      "多行注释较少使用，因为其主要用于注释代码块，而现代开发更倾向于使用更清晰的代码结构。",
      "注释不会被编译器执行，因此不会影响程序运行，但能帮助其他开发者理解代码意图。",
      "注释应尽量简洁，避免冗余，因为好的代码本身就能表达意图，不需要过多注释。",
      "注释应避免解释显而易见的代码逻辑，而应关注复杂逻辑或关键决策点。"
    ],
    "keywords": [
      "单行注释",
      "多行注释",
      "文档注释"
    ],
    "scene": [
      "在团队协作中，注释可以帮助其他成员快速理解代码逻辑，特别是在项目结构复杂时。",
      "在编写 API 文档时，文档注释可以自动生成文档，提高开发效率。",
      "在代码审查中，注释可以解释代码的意图，帮助审阅者理解开发者的思路。"
    ],
    "interviewQ": [
      "为什么文档注释在实际开发中使用较多？（答：文档注释可以自动生成 API 文档，提高开发效率。）",
      "注释和代码之间应该如何平衡？（答：注释应补充代码表达不足的部分，避免冗余，以提升可读性。）",
      "多行注释在实际开发中使用较少的原因是什么？（答：多行注释主要用于注释代码块，而现代开发更倾向于使用更清晰的代码结构。）"
    ],
    "related": [
      {
        "id": "java-basicq11",
        "kind": "prereq",
        "note": "了解 Java 关键字后，才能更清楚注释的作用和使用场景"
      },
      {
        "id": "java-basicq15",
        "kind": "compare",
        "note": "对比基本数据类型，能更清楚字符型常量和字符串常量的区别"
      },
      {
        "id": "continue-break-return",
        "kind": "compare",
        "note": "了解控制流语句后，能更清楚注释在代码中的作用"
      },
      {
        "id": "java-basicq12",
        "kind": "compare",
        "note": "注释和自增自减运算符都是代码中用于解释和操作变量的重要手段"
      }
    ],
    "diagram": null
  },
  {
    "id": "java-basicq11",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "Java 语言关键字有哪些？",
    "oneLine": "Java 语言的关键字是语言的核心组成部分，用于定义语法结构、访问权限、程序控制等。",
    "analogy": "Java 关键字就像交通规则中的红绿灯，它们规定了程序的运行方式和结构，确保代码的正确性和一致性。",
    "why": "Java 关键字是语言的基础，它们用于定义变量、方法、类的访问权限，控制程序流程，处理异常，以及定义数据类型。这些关键字的存在使得 Java 语言具有结构化和可读性，同时避免了命名冲突。例如，`private` 和 `public` 控制访问权限，确保代码的安全性和模块化。而 `try` 和 `catch` 用于异常处理，提高程序的健壮性。",
    "mechanism": [
      "Java 关键字是语言中具有特殊含义的保留字，它们不能作为标识符使用，如变量名或类名。",
      "访问控制关键字如 `private`、`protected` 和 `public` 用于控制类、方法和变量的访问权限，确保封装性和安全性。",
      "类、方法和变量修饰符如 `abstract`、`final` 和 `static` 用于定义类、方法和变量的特性，如抽象类、常量和静态成员。",
      "程序控制关键字如 `if`、`else`、`for` 和 `while` 用于控制程序的执行流程，实现条件判断和循环。",
      "错误处理关键字如 `try`、`catch` 和 `finally` 用于捕获和处理运行时异常，确保程序的健壮性。",
      "包相关关键字如 `import` 和 `package` 用于组织和管理代码，提高代码的可维护性。",
      "基本类型关键字如 `boolean`、`int` 和 `double` 用于定义变量的数据类型，确保数据的正确存储和操作。",
      "变量引用关键字如 `super` 和 `this` 用于引用父类和当前类的成员，增强代码的灵活性和可读性。"
    ],
    "keywords": [
      "private",
      "protected",
      "public",
      "abstract",
      "class",
      "extends",
      "final",
      "implements"
    ],
    "scene": [
      "在开发一个银行系统时，`private` 和 `public` 关键字用于控制账户信息的访问权限，确保数据安全。",
      "在开发一个图形用户界面（GUI）时，`static` 和 `final` 关键字用于定义常量和静态方法，提高代码的可维护性。",
      "在开发一个网络应用时，`try` 和 `catch` 关键字用于处理网络请求中的异常，确保程序的稳定性。"
    ],
    "interviewQ": [
      "为什么 Java 的关键字都是小写的？（答：为了区分关键字和用户定义的标识符，提高代码的可读性和避免冲突。）",
      "Java 中 `default` 关键字有哪些用途？（答：在 `switch` 中作为默认分支，定义默认方法，以及作为访问控制修饰符。）",
      "Java 中 `final` 关键字的作用是什么？（答：`final` 关键字用于定义常量、防止继承和禁止方法重写，确保代码的稳定性。）"
    ],
    "related": [
      {
        "id": "java-basicq01",
        "kind": "prereq",
        "note": "了解 Java 的特点后，才能理解关键字在语言设计中的作用"
      },
      {
        "id": "java-basicq05",
        "kind": "compare",
        "note": "了解 Java 编译与解释并存的特性，有助于理解关键字的语法作用"
      },
      {
        "id": "java-basicq09",
        "kind": "compare",
        "note": "注释和关键字都是代码中用于解释和控制逻辑的重要手段"
      }
    ],
    "diagram": null
  },
  {
    "id": "java-basicq12",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "自增自减运算符如何影响变量值？",
    "oneLine": "自增自减运算符用于快速增加或减少变量值，分为前缀和后缀形式，影响变量值的读取顺序。",
    "analogy": "就像在超市结账时，先扫码再付款是前缀形式，先付款再扫码是后缀形式，影响最终账单金额。",
    "why": "在编程中，频繁地对变量进行加减操作时，使用自增自减运算符可以简化代码，提高可读性。前缀形式在操作前立即改变变量值，而后缀形式则在操作后改变变量值，这种差异在复杂表达式中可能导致不同的结果，因此需要明确其执行顺序。",
    "mechanism": [
      "自增运算符 `++` 和自减运算符 `--` 是 Java 中用于快速增加或减少变量值的运算符，分为前缀和后缀形式。",
      "前缀形式（如 `++a`）会在使用变量之前先对变量进行自增或自减操作，确保后续的运算使用的是更新后的值。",
      "后缀形式（如 `a++`）会在使用变量之后才对变量进行自增或自减操作，确保运算使用的是原始值。",
      "在表达式中，前缀形式会先修改变量值，再参与运算，因此结果会受到影响。",
      "后缀形式会先使用变量的当前值参与运算，再修改变量值，因此结果会有所不同。",
      "在多步运算中，前缀和后缀形式的顺序会影响变量的最终值，因此需要特别注意其执行顺序。",
      "在实际编程中，前缀形式常用于需要立即使用更新后的值的场景，而后缀形式则用于需要保留原始值的场景。"
    ],
    "keywords": [
      "自增运算符",
      "自减运算符",
      "前缀形式",
      "后缀形式"
    ],
    "scene": [
      "在循环中，使用前缀形式可以确保循环变量在每次迭代时都使用最新的值。",
      "在计算表达式时，后缀形式可以确保运算使用的是原始值，避免干扰后续计算。",
      "在多变量赋值时，前缀和后缀形式的顺序可能导致变量值的差异，需要注意其影响。"
    ],
    "interviewQ": [
      "请解释前缀形式和后缀形式的区别（答：前缀形式先修改变量值，再参与运算；后缀形式先使用变量值，再修改变量值）。",
      "在表达式 `b = a++` 中，`a` 和 `b` 的值如何变化？（答：`b` 会获得 `a` 的原始值，`a` 之后会增加 1）。",
      "如果 `a = 5`，执行 `b = ++a` 后，`a` 和 `b` 的值是多少？（答：`a` 和 `b` 都是 6）。",
      "在 `int a = 9; int b = a++;` 中，`a` 和 `b` 的值分别是多少？（答：`a` 是 10，`b` 是 9）"
    ],
    "related": [
      {
        "id": "java-basicq13",
        "kind": "prereq",
        "note": "了解移位运算符后，才能理解自增自减运算符的底层逻辑"
      },
      {
        "id": "continue-break-return",
        "kind": "compare",
        "note": "对比控制流语句，能更清楚自增自减运算符在代码中的作用"
      },
      {
        "id": "java-basicq09",
        "kind": "compare",
        "note": "注释和自增自减运算符都是代码中用于解释和操作变量的重要手段"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "读取变量值",
        "执行运算",
        "更新变量值"
      ],
      "frames": [
        {
          "s": 0,
          "note": "后缀形式先读取变量原始值，用于当前运算，不会立即改变变量。"
        },
        {
          "s": 1,
          "note": "运算完成后，变量才会被自增或自减，影响后续步骤的值。"
        },
        {
          "s": 2,
          "note": "前缀形式在使用前先修改变量，确保后续运算使用的是更新后的值。"
        }
      ]
    }
  },
  {
    "id": "java-basicq13",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "移位运算符是什么？",
    "oneLine": "移位运算符是将二进制数向左或向右移动若干位的运算，用于快速乘除2的幂次方或处理位字段。",
    "analogy": "就像整理房间时，把物品从左边搬到右边，或者把物品从右边搬到左边，空位用0补齐。",
    "why": "移位运算符之所以重要，是因为它直接对应处理器的硬件指令，执行速度快，节省内存。在哈希算法、数据压缩和加密中，移位操作能快速混淆数据，提高效率。此外，它还能处理位字段，节省存储空间。由于移位操作在硬件层面执行，相比乘除法，效率更高，因此在底层实现和性能优化中被广泛使用。",
    "mechanism": [
      "移位运算符将二进制数向左或向右移动若干位，用于快速乘以或除以2的幂次方。它通过直接操作二进制位，避免了普通算术运算的复杂性，从而提升运算效率。",
      "左移运算符（<<）将二进制数的每一位向左移动，低位补0，相当于乘以2的幂次方。例如，将数字5（二进制101）左移1位，得到1010，即10，相当于5乘以2。",
      "右移运算符（>>）将二进制数的每一位向右移动，高位补符号位（正数补0，负数补1），相当于除以2的幂次方。例如，将数字8（二进制1000）右移1位，得到100，即4，相当于8除以2。",
      "无符号右移运算符（>>>）将二进制数的每一位向右移动，高位补0，适用于无符号数的右移操作。例如，将数字-8（二进制11111111111111111111111111111111）无符号右移2位，得到1073741822，即二进制00111111111111111111111111111111。",
      "移位操作在哈希算法中用于混淆数据，例如HashMap的hash方法使用无符号右移来混合哈希值，提高哈希分布的均匀性。",
      "移位操作在数据压缩中用于快速处理二进制数据，例如霍夫曼编码通过移位运算符可以快速处理和操作二进制数据，以生成紧凑的压缩格式。",
      "当移位位数超过数值位数时，会先取余后再进行移位，例如int类型左移42位等同于左移10位（42%32=10），以避免超出有效位数范围。",
      "移位运算符支持int和long类型，short、byte、char类型在移位前会被转换为int类型，确保运算的正确性。"
    ],
    "keywords": [
      "移位运算符",
      "左移",
      "右移",
      "无符号右移",
      "HashMap",
      "hash"
    ],
    "scene": [
      "在HashMap的hash方法中，使用无符号右移混淆哈希值，提高哈希分布的均匀性。",
      "在数据压缩中，如霍夫曼编码，使用移位运算符快速处理二进制数据，生成紧凑的压缩格式。",
      "在位字段管理中，通过移位操作存储和操作多个布尔值，节省内存空间。"
    ],
    "interviewQ": [
      "追问1：移位运算符在Java中支持哪些类型？（答：移位运算符支持int和long类型，short、byte、char类型在移位前会被转换为int类型。）",
      "追问2：无符号右移和带符号右移的区别是什么？（答：无符号右移（>>>）高位补0，带符号右移（>>）高位补符号位，适用于无符号数的右移操作。）",
      "追问3：移位位数超过数值位数会怎样？（答：当移位位数超过数值位数时，会先取余后再进行移位，例如int类型左移42位等同于左移10位。）",
      "追问4：移位运算符在哈希算法中的作用是什么？（答：移位运算符在哈希算法中用于混淆数据，例如HashMap的hash方法使用无符号右移来混合哈希值，提高哈希分布的均匀性。）"
    ],
    "related": [
      {
        "id": "java-basicq12",
        "kind": "prereq",
        "note": "了解自增自减运算符后，才能理解移位运算符的底层逻辑"
      },
      {
        "id": "java-basicq16",
        "kind": "compare",
        "note": "对比基本类型和包装类型，能更清楚移位运算符的使用场景"
      },
      {
        "id": "java-basicq04",
        "kind": "compare",
        "note": "了解字节码后，能更清楚移位运算符在底层的实现方式"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "二进制位移动",
        "数值变化",
        "应用场景"
      ],
      "frames": [
        {
          "s": 0,
          "note": "移位操作直接操作二进制位，避免了普通算术运算的复杂性，提升效率。"
        },
        {
          "s": 1,
          "note": "左移补0，右移补符号位，数值变化等同于乘除2的幂次方，但需注意符号位处理。"
        },
        {
          "s": 2,
          "note": "HashMap通过无符号右移混淆哈希值，霍夫曼编码利用移位快速处理二进制数据，提升压缩效率。"
        }
      ]
    }
  },
  {
    "id": "continue-break-return",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "continue、break 和 return 的区别是什么？",
    "oneLine": "continue、break 和 return 是控制循环和方法执行的关键词，分别用于跳过当前循环、终止循环和结束方法。",
    "analogy": "continue 像是排队时跳过当前的人继续下一个人；break 像是直接离开队伍；return 像是结束整个排队过程并离开。",
    "why": "在循环中，有时需要提前结束或跳过某些步骤。continue 用于跳过当前循环继续下一次，避免重复执行某些代码；break 用于立即终止循环，避免继续执行后续代码；return 则用于结束整个方法，避免继续执行方法中的其他代码。这些关键词能提高代码的效率和控制流程。",
    "mechanism": [
      "continue 是用于跳过当前循环体的执行，继续执行下一次循环。它不会终止循环，而是直接跳到循环的判断条件部分，继续下一次循环。",
      "break 是用于立即终止整个循环体的执行，跳出循环体并继续执行循环之后的代码。它会完全终止循环，不会继续执行循环体中的任何代码。",
      "return 是用于结束当前方法的执行，返回到调用该方法的地方。它会终止方法的执行，不会继续执行方法中的任何代码。",
      "continue 只影响当前循环的这一次执行，不会影响整个循环的结构。",
      "break 会终止整个循环的执行，使程序继续执行循环之后的代码。",
      "return 不仅会终止当前方法的执行，还会将控制权返回到调用该方法的地方。",
      "continue 和 break 通常用于循环结构中，而 return 通常用于方法中。",
      "continue 和 break 只影响循环的执行，而 return 影响整个方法的执行。"
    ],
    "keywords": [
      "continue",
      "break",
      "return",
      "循环",
      "方法"
    ],
    "scene": [
      "在处理数组时，continue 用于跳过某些元素的处理，例如跳过负数。",
      "在处理用户输入时，break 用于在用户输入特定值时立即终止循环。",
      "在处理复杂逻辑的方法中，return 用于在满足条件时立即返回结果，避免不必要的计算。"
    ],
    "interviewQ": [
      "追问1：continue 和 break 的区别是什么？（答：continue 跳过当前循环继续下一次，break 终止整个循环。）",
      "追问2：return 会终止哪些结构的执行？（答：return 会终止方法的执行，返回到调用方法的地方。）",
      "追问3：在循环中使用 return 会有什么影响？（答：return 会立即终止整个方法的执行，不会继续执行循环中的后续代码。）",
      "追问4：continue 和 break 在循环中的使用场景有什么不同？（答：continue 用于跳过当前循环的某些步骤，break 用于立即终止循环。）"
    ],
    "related": [
      {
        "id": "java-basicq16",
        "kind": "prereq",
        "note": "了解基本类型和包装类型区别后，才能理解控制流语句的作用场景"
      },
      {
        "id": "java-basicq09",
        "kind": "compare",
        "note": "了解控制流语句后，能更清楚注释在代码中的作用"
      },
      {
        "id": "java-basicq12",
        "kind": "compare",
        "note": "对比控制流语句，能更清楚自增自减运算符在代码中的作用"
      },
      {
        "id": "java-basicq17",
        "kind": "compare",
        "note": "包装类型和控制流语句是Java语言的不同维度，对比理解更全面"
      },
      {
        "id": "java-basicq18",
        "kind": "compare",
        "note": "自动装箱拆箱和控制流语句是Java语言的不同维度，对比理解更全面"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "进入循环",
        "执行语句",
        "跳转判断"
      ],
      "frames": [
        {
          "s": 0,
          "note": "continue 会跳过当前循环体，直接回到循环判断条件，继续下一次循环。"
        },
        {
          "s": 1,
          "note": "break 会立即终止整个循环，跳转到循环外的代码继续执行。"
        },
        {
          "s": 2,
          "note": "return 会结束当前方法执行，返回调用处，不再执行方法中后续代码。"
        }
      ]
    }
  },
  {
    "id": "java-basicq15",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "Java 中的几种基本数据类型了解么？",
    "oneLine": "Java 有 8 种基本数据类型，包括 4 种整数型、2 种浮点型、1 种字符型和 1 种布尔型。",
    "analogy": "就像超市里的商品分类，基本数据类型是 Java 语言中用来存储不同类型数据的‘货架’，每种货架都有自己的容量和默认商品。",
    "why": "Java 的基本数据类型是为了提供高效、直接的数据存储和操作方式。它们的固定大小和默认值确保了程序在不同平台上运行时的一致性，避免了因硬件差异导致的兼容性问题。同时，它们的取值范围和存储方式也满足了各种应用场景的需求。",
    "mechanism": [
      "Java 的基本数据类型是语言内置的最小数据单位，包括整数型、浮点型、字符型和布尔型，它们的大小和默认值由 Java 规范定义。",
      "整数型（byte、short、int、long）使用二进制补码表示法，最高位为符号位，其余位表示数值，因此最大正数是所有位都为 1 的情况。",
      "浮点型（float、double）使用 IEEE 754 标准表示，包含正负零、无穷大和 NaN 等特殊值，以支持更广泛的数据范围和精度。",
      "字符型（char）使用 16 位 Unicode 编码，可以表示 0 到 65535 的字符，适用于多语言环境。",
      "布尔型（boolean）虽然逻辑上占用 1 位，但实际存储由 JVM 厂商决定，通常以字节为单位存储。",
      "基本数据类型具有固定的存储大小，不随硬件架构变化，这保证了 Java 程序的可移植性。",
      "每种基本类型都有对应的包装类，用于对象化处理，例如 Integer、Double 等，支持泛型和集合操作。",
      "基本数据类型的默认值和取值范围确保了程序在初始化和运行时的正确性和稳定性。"
    ],
    "keywords": [
      "byte",
      "short",
      "int",
      "long",
      "float",
      "double",
      "char",
      "boolean"
    ],
    "scene": [
      "在嵌入式系统中，byte 和 short 被用于节省内存空间，提高数据处理效率。",
      "在数据库操作中，int 和 long 用于存储整数型字段，确保数据的准确性和范围。",
      "在图形处理中，char 用于存储字符和符号，支持多语言字符集的表示。"
    ],
    "interviewQ": [
      "追问1：为什么整数型的最大正数是 2^n - 1？（答：因为二进制补码表示法中，最高位为符号位，其余位为 1 时表示最大正数。）",
      "追问2：浮点型的特殊值如 NaN 是什么？（答：NaN 表示非数字，用于表示未定义或不可表示的浮点运算结果。）",
      "追问3：boolean 类型的实际存储方式是什么？（答：boolean 逻辑上占 1 位，但实际存储由 JVM 厂商决定，通常以字节为单位。）"
    ],
    "related": [
      {
        "id": "java-basicq17",
        "kind": "compare",
        "note": "基本类型和包装类型是Java语言的基础，理解它们是学习缓存机制的前提"
      },
      {
        "id": "java-basicq16",
        "kind": "prereq",
        "note": "了解基本类型和包装类型区别后，才能理解基本类型在内存中的存储方式"
      },
      {
        "id": "java-basicq01",
        "kind": "compare",
        "note": "基本数据类型与语言特性形成对比，帮助理解语言设计"
      },
      {
        "id": "java-basicq09",
        "kind": "compare",
        "note": "对比基本数据类型，能更清楚字符型常量和字符串常量的区别"
      }
    ],
    "diagram": null
  },
  {
    "id": "java-basicq16",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "基本类型和包装类型的区别是什么？",
    "oneLine": "基本类型用于存储简单值，包装类型用于对象化，支持泛型和 null 值。",
    "analogy": "基本类型就像直接装水的瓶子，包装类型则像装在纸箱里的瓶子，可以放在货架上，也能放在一起。",
    "why": "基本类型不能作为泛型参数，因为泛型要求对象类型。包装类型可以用于集合、参数传递等场景。基本类型有默认值，而包装类型默认为 null，这在某些情况下更灵活。此外，包装类型支持方法调用，如 equals() 和 compareTo()，而基本类型只能用 == 比较值。",
    "mechanism": [
      "基本类型是 Java 中的原始数据类型，如 int、char、boolean 等，它们直接存储值，不涉及对象。",
      "包装类型是基本类型的对象形式，如 Integer、Character、Boolean 等，它们是类，可以存储 null 值。",
      "基本类型的局部变量存储在栈中，而实例字段存储在堆中，静态字段存储在 JVM 的类区或堆中。",
      "包装类型作为对象，存储在堆中，但 JIT 可能通过逃逸分析和标量替换将对象分配到栈中，以优化性能。",
      "基本类型有默认值，例如 int 默认为 0，而包装类型默认为 null，这在某些场景下更符合逻辑。",
      "基本类型使用 == 比较值，而包装类型使用 == 比较引用，若要比较值，应使用 equals() 或 compareTo() 方法。",
      "包装类型支持泛型，例如 List<Integer>，而基本类型不能直接作为泛型参数，需使用包装类型。"
    ],
    "keywords": [
      "基本类型",
      "包装类型",
      "泛型",
      "null",
      "栈",
      "堆"
    ],
    "scene": [
      "在集合类中使用包装类型，如 List<Integer>，以支持泛型。",
      "在方法参数中使用包装类型，以允许 null 值。",
      "在对象属性中使用包装类型，以避免默认值问题。"
    ],
    "interviewQ": [
      "为什么包装类型可以用于泛型？（答：泛型要求对象类型，包装类型是类，可以作为泛型参数。）",
      "基本类型和包装类型的默认值有什么区别？（答：基本类型有默认值，如 int 默认为 0；包装类型默认为 null。）",
      "为什么基本类型不能直接作为泛型参数？（答：泛型要求对象类型，而基本类型不是对象，必须使用包装类型。）"
    ],
    "related": [
      {
        "id": "java-basicq18",
        "kind": "prereq",
        "note": "了解自动装箱拆箱原理后，才能理解包装类型和基本类型之间的转换"
      },
      {
        "id": "continue-break-return",
        "kind": "compare",
        "note": "基本类型和控制流语句是Java语言的不同维度，对比理解更全面"
      },
      {
        "id": "java-basicq17",
        "kind": "prereq",
        "note": "了解包装类型缓存机制后，才能理解自动装箱拆箱的原理"
      },
      {
        "id": "java-basicq13",
        "kind": "compare",
        "note": "对比基本类型和包装类型，能更清楚移位运算符的使用场景"
      },
      {
        "id": "java-basicq15",
        "kind": "extends",
        "note": "了解基本类型和包装类型区别后，才能理解基本类型在内存中的存储方式"
      }
    ],
    "diagram": null
  },
  {
    "id": "java-basicq17",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "包装类型的缓存机制了解么？",
    "oneLine": "Java 中的 Integer、Short、Byte、Long、Character 等包装类使用缓存机制提升性能，避免重复创建对象。",
    "analogy": "就像超市里准备好了常用商品，顾客可以直接拿，不用每次都重新进货。",
    "why": "Java 为了提升性能和减少内存开销，对常用的包装类型进行了缓存。如果直接创建对象，会浪费资源，而缓存可以复用已有的对象，提高效率。但缓存范围是有限的，超出范围就会创建新对象，因此需要权衡性能和内存。",
    "mechanism": [
      "Integer 的 valueOf 方法会检查数值是否在缓存范围内，如果在则直接返回缓存中的对象，否则创建新对象。",
      "缓存范围默认是 [-128, 127]，超出范围就会创建新对象，避免内存浪费和性能下降。",
      "Character 的缓存范围是 [0, 127]，通过静态数组存储，每次调用 valueOf 会直接从数组中获取。",
      "Boolean 直接返回预定义的 TRUE 和 FALSE 实例，没有缓存范围的概念。",
      "JVM 提供了 -XX:AutoBoxCacheMax 参数调整 Integer 的缓存上限，但下限固定为 -128。",
      "Float 和 Double 没有实现缓存机制，每次都会创建新对象，因此比较时会返回 false。",
      "当使用 new 关键字创建包装类对象时，会跳过缓存，直接创建新对象，因此比较时会返回 false。",
      "在实际开发中，应使用 equals 方法比较包装类对象的值，而不是 ==，以避免因缓存导致的错误。"
    ],
    "keywords": [
      "Integer",
      "缓存",
      "valueOf",
      "Boolean",
      "Character",
      "AutoBoxCacheMax"
    ],
    "scene": [
      "在使用 Integer 进行频繁的值比较时，如果超出缓存范围，可能导致内存浪费。",
      "在使用 Boolean 时，直接返回预定义对象，无需创建新对象，提高性能。",
      "在使用 Float 或 Double 时，由于没有缓存机制，每次都会创建新对象，导致比较结果为 false。"
    ],
    "interviewQ": [
      "为什么 Integer 的缓存范围是 [-128, 127]？（答：为了在性能和内存之间取得平衡，避免浪费资源。）",
      "如何修改 Integer 的缓存上限？（答：可以通过 JVM 参数 -XX:AutoBoxCacheMax 修改，但不能低于 -128。）",
      "为什么比较包装类对象的值时要用 equals 而不是 ==？（答：因为 == 比较的是对象引用，而 equals 比较的是值，避免因缓存导致的错误。）",
      "Float 和 Double 为什么不实现缓存机制？（答：因为它们的值范围太大，缓存会浪费大量内存，因此不实现缓存。）"
    ],
    "related": [
      {
        "id": "java-basicq15",
        "kind": "prereq",
        "note": "了解基本数据类型后，才能理解包装类型缓存机制的实现"
      },
      {
        "id": "java-basicq16",
        "kind": "prereq",
        "note": "了解基本类型和包装类型区别后，才能理解包装类型缓存机制"
      },
      {
        "id": "java-basicq18",
        "kind": "prereq",
        "note": "了解自动装箱拆箱原理后，才能理解包装类型缓存机制"
      },
      {
        "id": "continue-break-return",
        "kind": "compare",
        "note": "包装类型和控制流语句是Java语言的不同维度，对比理解更全面"
      },
      {
        "id": "java-basicq01",
        "kind": "compare",
        "note": "包装类型缓存机制与语言特性形成对比，帮助理解语言设计"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "有缓存类型",
          "lines": [
            "Integer 缓存范围 [-128, 127]",
            "Character 缓存范围 [0, 127]",
            "Boolean 直接返回预定义对象"
          ]
        },
        {
          "title": "无缓存类型",
          "lines": [
            "Float/Double 每次创建新对象",
            "new Integer() 跳过缓存",
            "== 比较可能因缓存导致错误"
          ]
        }
      ],
      "frames": [
        {
          "note": "Integer 和 Character 通过缓存减少对象创建，提升性能",
          "active": [
            0
          ]
        },
        {
          "note": "Boolean 直接返回预定义对象，无需创建新实例",
          "active": [
            0
          ]
        },
        {
          "note": "Float/Double 没有缓存，每次 new 都会创建新对象",
          "active": [
            1
          ]
        },
        {
          "note": "使用 equals 比较包装类值，避免因缓存导致的 == 比较错误",
          "active": [
            0,
            1
          ]
        }
      ]
    }
  },
  {
    "id": "java-basicq18",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "自动装箱与拆箱了解吗？原理是什么？",
    "oneLine": "自动装箱是基本类型转为包装类，拆箱是包装类转为基本类型，由JVM自动完成。",
    "analogy": "就像把硬币放进钱包和取出硬币的过程，装箱是把硬币放进钱包，拆箱是把硬币拿出来。",
    "why": "在Java中，基本类型和包装类是不同的类型，不能直接赋值。自动装箱与拆箱的出现是为了简化代码，避免显式转换带来的繁琐。如果频繁进行装箱拆箱，会增加内存开销和性能损耗，因此应尽量避免不必要的操作。",
    "mechanism": [
      "装箱是将基本类型转换为对应的包装类对象，例如int转为Integer，这是通过调用包装类的valueOf()方法实现的。",
      "拆箱是将包装类对象转换为基本类型，例如Integer转为int，这是通过调用包装类的xxxValue()方法实现的，如intValue()。",
      "在字节码层面，装箱操作会调用Integer.valueOf()，而拆箱操作会调用intValue()，这体现了JVM对装箱拆箱的底层实现。",
      "自动装箱与拆箱的机制使得开发者无需手动进行类型转换，提高了代码的可读性和开发效率。",
      "当使用包装类进行运算时，JVM会自动进行装箱和拆箱操作，以确保运算的正确性。",
      "频繁的装箱拆箱可能导致不必要的内存分配和垃圾回收，影响程序性能，因此应合理使用基本类型。",
      "在实际开发中，应尽量避免在循环中使用包装类，尤其是涉及大量数据运算时，以减少性能损耗。"
    ],
    "keywords": [
      "装箱",
      "拆箱",
      "valueOf",
      "xxxValue",
      "基本类型",
      "包装类"
    ],
    "scene": [
      "在使用集合类时，如ArrayList，需要存储对象，因此会进行装箱操作。",
      "在进行数值运算时，如将Integer对象赋值给int变量，会触发拆箱操作。",
      "在循环中频繁使用包装类进行计算，可能导致性能下降，应改用基本类型。"
    ],
    "interviewQ": [
      "追问1：装箱和拆箱是如何实现的？（答：装箱通过调用valueOf()方法，拆箱通过调用xxxValue()方法。）",
      "追问2：为什么频繁装箱拆箱会影响性能？（答：频繁装箱拆箱会增加内存开销和垃圾回收压力，影响程序运行效率。）",
      "追问3：如何避免不必要的装箱拆箱？（答：应尽量使用基本类型，避免在循环中使用包装类，以减少性能损耗。）"
    ],
    "related": [
      {
        "id": "java-basicq16",
        "kind": "prereq",
        "note": "了解基本类型和包装类型区别后，才能理解自动装箱拆箱的原理"
      },
      {
        "id": "java-basicq17",
        "kind": "prereq",
        "note": "了解包装类型缓存机制后，才能理解自动装箱拆箱的原理"
      },
      {
        "id": "continue-break-return",
        "kind": "compare",
        "note": "自动装箱拆箱和控制流语句是Java语言的不同维度，对比理解更全面"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "装箱",
          "lines": [
            "基本类型转包装类",
            "调用valueOf()方法",
            "如int→Integer",
            "JVM自动完成"
          ]
        },
        {
          "title": "拆箱",
          "lines": [
            "包装类转基本类型",
            "调用xxxValue()方法",
            "如Integer→int",
            "JVM自动完成"
          ]
        }
      ],
      "frames": [
        {
          "note": "装箱操作在字节码中调用Integer.valueOf()，实现基本类型到包装类的转换。",
          "active": [
            0
          ]
        },
        {
          "note": "拆箱操作在字节码中调用intValue()，实现包装类到基本类型的转换。",
          "active": [
            1
          ]
        }
      ]
    }
  },
  {
    "id": "java-basicq22",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "成员变量与局部变量的区别？",
    "oneLine": "成员变量是类的属性，有默认值；局部变量是方法或代码块中的临时变量，无默认值。",
    "analogy": "成员变量就像家里的家具，不管有没有人住，都会默认有基本配置；而局部变量就像临时借用的工具，必须自己准备。",
    "why": "成员变量有默认值是为了方便使用，避免初始化时的空指针或未定义值问题。而局部变量没有默认值，是因为它们的生命周期短，必须显式赋值以确保程序的正确性和安全性。JLS 规定成员变量在创建时会自动初始化为默认值，而局部变量必须在使用前被赋值，这是语言设计上的强制性规则。",
    "mechanism": [
      "成员变量是类的属性，属于类或实例，而局部变量是方法或代码块中的临时变量，仅在方法调用期间存在。",
      "成员变量可以被 public、private、static 等修饰符修饰，而局部变量不能被访问控制修饰符及 static 修饰，但两者都可以被 final 修饰。",
      "成员变量使用 static 修饰时属于类，不使用 static 时属于实例，而局部变量保存在当前栈帧的局部变量表中。",
      "成员变量如果没有显式赋值，会自动初始化为类型的默认值，如 int 为 0、boolean 为 false、引用类型为 null。",
      "局部变量没有默认值，必须显式赋值，否则编译器会报错，这是为了确保在使用前变量已被正确初始化。",
      "成员变量的生命周期与对象一致，对象存在时变量存在，对象销毁时变量消失；局部变量的生命周期与方法调用一致，方法调用结束变量即被回收。",
      "JIT 优化可能减少局部变量的实际存储开销，但成员变量的存储方式仍依赖于是否使用 static 修饰。",
      "成员变量和局部变量在代码示例中分别体现为类的属性和方法中的临时变量，如 name、age 是成员变量，num1、str 是局部变量。"
    ],
    "keywords": [
      "成员变量",
      "局部变量",
      "默认值",
      "final",
      "static",
      "JIT"
    ],
    "scene": [
      "在 Java 程序中，成员变量用于存储对象的状态，如用户信息中的 name 和 age。",
      "局部变量用于临时存储方法中的中间结果，如计算 sum 时的 num2 和 sum。",
      "在构造方法中，成员变量通过 this 关键字赋值，而局部变量如 num3 则在方法内定义和使用。"
    ],
    "interviewQ": [
      "为什么局部变量没有默认值？（答：局部变量必须显式赋值，以确保在使用前已被正确初始化，这是 JLS 的强制性规定。）",
      "成员变量和局部变量在存储方式上有何不同？（答：成员变量存储在堆中（实例变量）或类的静态区域（类变量），局部变量存储在栈中的局部变量表中。）",
      "final 修饰符对成员变量和局部变量有何影响？（答：final 修饰的成员变量和局部变量都必须显式赋值，防止被修改。）"
    ],
    "related": [
      {
        "id": "java-basicq24",
        "kind": "compare",
        "note": "变量类型不同，但都涉及变量的存储和作用域，对比理解更清晰"
      },
      {
        "id": "java-basicq27",
        "kind": "compare",
        "note": "都涉及变量的生命周期和访问方式，对比理解更清晰"
      }
    ],
    "diagram": null
  },
  {
    "id": "java-basicq24",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "字符型常量和字符串常量的区别？",
    "oneLine": "字符型常量是单引号包裹的单个字符，字符串常量是双引号包裹的字符序列。",
    "analogy": "字符型常量就像一个单独的字母，字符串常量就像一整段话，它们在存储和使用方式上完全不同。",
    "why": "字符型常量在 Java 中占两个字节，可以参与数值运算，而字符串常量是 String 对象的引用，不是直接的内存地址。这种设计使得字符型常量更适用于简单的字符操作，而字符串常量更适合处理复杂的文本信息。字符型常量的简单性使得它在内存中占用更少空间，而字符串常量的引用机制则允许更灵活的字符串操作和共享。",
    "mechanism": [
      "字符型常量是单引号包裹的一个字符，表示 UTF-16 代码单元，可以参与数值运算，例如 'A' 可以与数字相加。",
      "字符串常量是双引号包裹的字符序列，表示对 String 对象的引用，而不是直接的内存地址，因此在内存中存储的是对象的引用。",
      "字符型常量在 Java 中占两个字节，这是由于 Java 使用 UTF-16 编码，每个字符占两个字节，而字符串常量的内存占用则取决于 JVM 的实现细节。",
      "字符串常量在运行时会被 JVM 自动优化，多个相同的字符串常量会被合并为一个对象，从而节省内存。",
      "字符型常量在进行运算时可以直接使用其数值，例如 'A' + 1 会得到 'B' 的 ASCII 值，而字符串常量则需要通过方法进行操作。",
      "字符串常量在内存中存储的是对象的引用，因此在进行字符串拼接时会创建新的 String 对象，而字符型常量则不会产生这种开销。",
      "字符型常量的简单性使其在需要快速处理单个字符的场景中更为高效，而字符串常量则更适合处理复杂的文本信息。"
    ],
    "keywords": [
      "char",
      "String",
      "UTF-16",
      "双引号",
      "单引号"
    ],
    "scene": [
      "在处理单个字符的输入输出时，使用字符型常量更高效。",
      "在需要字符串拼接或格式化时，使用字符串常量更方便。",
      "在需要处理多语言字符或特殊符号时，字符串常量可以更好地支持 UTF-16 编码。"
    ],
    "interviewQ": [
      "为什么字符型常量在 Java 中占两个字节？（答：因为 Java 使用 UTF-16 编码，每个字符占两个字节。）",
      "字符串常量在内存中如何存储？（答：字符串常量在内存中存储的是 String 对象的引用，而不是直接的内存地址。）",
      "字符型常量和字符串常量在进行运算时有何不同？（答：字符型常量可以参与数值运算，而字符串常量需要通过方法进行操作。）"
    ],
    "related": [
      {
        "id": "java-basicq22",
        "kind": "compare",
        "note": "变量类型不同，但都涉及变量的存储和作用域，对比理解更清晰"
      },
      {
        "id": "java-basicq16",
        "kind": "prereq",
        "note": "理解基本类型和包装类型的区别，有助于区分字符型常量和字符串常量"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "字符型常量",
          "lines": [
            "单引号包裹单个字符",
            "表示 UTF-16 代码单元",
            "可参与数值运算",
            "占 2 字节内存"
          ]
        },
        {
          "title": "字符串常量",
          "lines": [
            "双引号包裹字符序列",
            "表示 String 对象引用",
            "运行时自动优化合并",
            "拼接时创建新对象"
          ]
        }
      ],
      "frames": [
        {
          "note": "字符型常量适合单字符处理，如输入输出场景",
          "active": [
            0
          ]
        },
        {
          "note": "字符串常量适合文本处理，如拼接和格式化",
          "active": [
            1
          ]
        },
        {
          "note": "字符型常量可直接运算，如 'A' + 1 = 'B' 的 ASCII 值",
          "active": [
            0
          ]
        },
        {
          "note": "字符串常量存储对象引用，支持多语言字符和特殊符号",
          "active": [
            1
          ]
        }
      ]
    }
  },
  {
    "id": "java-basicq25",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "什么是方法的返回值？方法有哪几种类型？",
    "oneLine": "方法的返回值是方法执行后返回的结果，用于传递给其他代码使用。",
    "analogy": "就像去超市买东西，你告诉收银员要买什么，收银员把商品和价格给你，这就是返回值。",
    "why": "在编程中，方法执行后往往需要将结果传递给其他代码继续使用，比如计算结果、状态信息等。如果没有返回值，方法就无法与其他代码进行数据交互，限制了程序的灵活性和功能。因此，返回值是方法设计中不可或缺的一部分。",
    "mechanism": [
      "方法的返回值是指方法执行后返回给调用者的结果，它必须与方法声明的返回类型一致，用于传递数据。",
      "无参数无返回值的方法不接收任何输入，也不返回任何结果，常用于执行一些不需要结果的操作，比如打印信息。",
      "有参数无返回值的方法接收输入参数，但不返回结果，常用于执行某些操作，如修改数据或控制流程。",
      "有返回值无参数的方法不接收输入，但返回结果，常用于计算或获取某个值，如获取系统时间。",
      "有返回值有参数的方法接收输入参数，并返回结果，常用于处理数据并返回处理后的结果，如计算两个数的乘积。",
      "返回值的类型在方法声明时已经确定，调用者可以根据返回值类型来接收和使用结果，确保数据的一致性和正确性。",
      "return语句用于结束方法的执行并返回结果，如果方法有返回值，必须使用return语句返回结果，否则会导致编译错误。",
      "方法的返回值可以是基本数据类型、对象、数组等，具体取决于方法的设计和需求。"
    ],
    "keywords": [
      "返回值",
      "方法",
      "参数",
      "无返回值",
      "有返回值"
    ],
    "scene": [
      "在计算两个数的和时，使用有返回值有参数的方法，将结果返回给调用者。",
      "在日志系统中，使用无返回值无参数的方法，仅用于记录日志信息。",
      "在数据处理模块中，使用有返回值无参数的方法，返回处理后的数据给上层逻辑。"
    ],
    "interviewQ": [
      "追问1：为什么有些方法没有返回值？（答：有些方法仅用于执行操作，不需要返回结果，如打印日志或修改数据。）",
      "追问2：如何在方法中返回结果？（答：使用return语句返回结果，并确保返回值类型与方法声明一致。）",
      "追问3：返回值的类型如何确定？（答：返回值的类型在方法声明时确定，必须与返回值类型一致，否则会导致编译错误。）"
    ],
    "related": [
      {
        "id": "java-basicq27",
        "kind": "compare",
        "note": "都涉及方法的特性，对比理解方法的返回值和静态/实例方法的区别"
      },
      {
        "id": "java-basicq28",
        "kind": "compare",
        "note": "都涉及方法的特性，对比理解方法的返回值和重写机制"
      },
      {
        "id": "java-basicq01",
        "kind": "compare",
        "note": "方法返回值与语言特性形成对比，帮助理解语言设计"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "无返回值",
          "lines": [
            "不接收输入，也不返回结果",
            "常用于执行不需要结果的操作",
            "如打印信息、修改数据"
          ]
        },
        {
          "title": "有返回值",
          "lines": [
            "不接收输入，但返回结果",
            "常用于计算或获取值",
            "如获取系统时间、计算乘积"
          ]
        }
      ],
      "frames": [
        {
          "note": "无返回值方法适用于执行不需要结果的操作，如日志记录。",
          "active": [
            0
          ]
        },
        {
          "note": "有返回值方法适用于需要传递结果的场景，如数据计算。",
          "active": [
            1
          ]
        }
      ]
    }
  },
  {
    "id": "java-basicq27",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "静态方法和实例方法有何不同？",
    "oneLine": "静态方法属于类，实例方法属于对象，调用方式和访问权限不同。",
    "analogy": "静态方法就像公共电话亭，所有人都可以使用，但不能知道是谁在使用；实例方法就像私人电话，只能由拥有电话的人使用。",
    "why": "静态方法和实例方法的不同主要源于它们的生命周期和访问权限。静态方法在类加载时就存在，不依赖于对象实例，因此可以无需创建对象直接调用。而实例方法需要对象实例才能调用，因为它们依赖于对象的状态和数据。这种设计使得静态方法适合处理与类相关的通用操作，而实例方法适合处理与对象状态相关的具体操作。",
    "mechanism": [
      "静态方法是属于类的，可以在不创建对象的情况下直接通过类名调用，而实例方法必须通过对象实例调用。",
      "静态方法只能访问静态成员，因为它们在类加载时就已经存在，无法访问实例成员，因为实例成员只有在对象创建后才会存在。",
      "实例方法可以访问实例成员和静态成员，因为它们在对象创建后才能被访问，且可以操作对象的状态。",
      "静态方法在类加载时初始化，而实例方法在对象创建时初始化，因此静态方法的执行效率通常更高。",
      "静态方法不能访问实例变量和实例方法，因为它们没有具体的对象引用，无法操作对象的状态。",
      "实例方法可以修改对象的状态，而静态方法通常用于执行与类相关的通用操作，不涉及对象状态。",
      "静态方法在多线程环境下可能引发问题，因为它们是类级别的，而实例方法则与特定对象相关，线程安全问题更易控制。",
      "静态方法不能作为重写的方法，因为它们不依赖于对象实例，而实例方法可以被重写以实现多态。"
    ],
    "keywords": [
      "静态方法",
      "实例方法",
      "静态成员",
      "实例成员"
    ],
    "scene": [
      "在工具类中使用静态方法，如Math类中的数学运算方法。",
      "在单例模式中使用静态方法来获取唯一实例。",
      "在需要不依赖对象状态的通用功能中使用静态方法，如日志记录。"
    ],
    "interviewQ": [
      "追问1：为什么静态方法不能访问实例成员？（答：因为静态方法在类加载时初始化，而实例成员只有在对象创建后才存在，因此无法访问。）",
      "追问2：静态方法和实例方法在多线程环境下有什么不同？（答：静态方法是类级别的，可能引发线程安全问题；实例方法是对象级别的，线程安全问题更易控制。）",
      "追问3：静态方法能否作为重写的方法？（答：不能，因为静态方法不依赖于对象实例，而重写需要基于对象实例的多态性。）"
    ],
    "related": [
      {
        "id": "java-basicq25",
        "kind": "compare",
        "note": "都涉及方法的特性，对比理解方法的返回值和静态/实例方法的区别"
      },
      {
        "id": "java-basicq28",
        "kind": "compare",
        "note": "都涉及方法的特性，对比理解方法的返回值和重写机制"
      },
      {
        "id": "java-basicq22",
        "kind": "compare",
        "note": "都涉及变量的生命周期和访问方式，对比理解更清晰"
      }
    ],
    "diagram": null
  },
  {
    "id": "java-basicq28",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "重载和重写有什么区别？",
    "oneLine": "重载是同一个类中方法名相同但参数不同的多个方法，重写是子类对父类方法的覆盖。",
    "analogy": "重载就像去超市买鸡蛋，不同包装的鸡蛋可以有不同的价格；重写就像你继承了父母的长相，但你可以选择改变发型。",
    "why": "重载解决了同一个类中需要处理不同参数类型的问题，避免了方法名重复；重写则解决了子类需要根据自身需求改变父类方法行为的问题，同时保持接口一致性。两者都是面向对象编程中重要的机制，分别应对不同的场景需求。",
    "mechanism": [
      "重载是同一个类中多个方法具有相同名称但不同参数列表，编译器通过参数类型和数量进行匹配，实现不同的逻辑处理。",
      "重载方法的返回值类型和访问修饰符可以不同，但参数列表必须不同，这是区分重载方法的关键。",
      "重写是子类对父类方法的重新实现，方法名和参数列表必须完全相同，返回值类型可以是父类的子类，访问权限不能低于父类。",
      "重写方法在运行时由JVM动态绑定，根据对象的实际类型决定调用哪个方法，这是动态绑定的核心机制。",
      "重写方法的异常声明范围不能超过父类，访问权限不能低于父类，这是为了保证程序的稳定性和安全性。",
      "重写返回值类型如果是引用类型，可以返回子类对象，这是多态的一种体现，增强了代码的灵活性。",
      "重载和重写都属于方法的多态表现，但重载是静态绑定，重写是动态绑定，这是它们在绑定时期的根本区别。",
      "重载和重写都用于提高代码的复用性和可读性，但适用场景不同，重载用于同一个类，重写用于继承关系。"
    ],
    "keywords": [
      "重载",
      "重写",
      "方法签名",
      "动态绑定",
      "静态绑定"
    ],
    "scene": [
      "在开发一个工具类时，可能需要重载多个构造方法，以适应不同的初始化参数。",
      "在继承一个类时，如果父类方法不能满足子类需求，就需要重写该方法以实现定制化逻辑。",
      "在设计接口时，重载可以提高方法的灵活性，而重写则确保子类可以扩展父类的功能。"
    ],
    "interviewQ": [
      "追问1：重载和重写在编译时和运行时分别如何处理？（答：重载是编译时静态绑定，重写是运行时动态绑定。）",
      "追问2：重写和重载在方法签名上有何不同？（答：重载方法签名不同，重写方法签名必须完全相同。）",
      "追问3：重写时返回值类型可以变化吗？（答：可以，但只能是父类返回值类型的子类，基本类型不可变。）",
      "追问4：重载和重写分别适用于哪些场景？（答：重载适用于同一个类，重写适用于继承关系。）"
    ],
    "related": [
      {
        "id": "java-basicq27",
        "kind": "compare",
        "note": "都涉及方法的特性，对比理解方法的返回值和静态/实例方法的区别"
      },
      {
        "id": "java-basicq25",
        "kind": "compare",
        "note": "都涉及方法的特性，对比理解方法的返回值和重写机制"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "重载",
          "lines": [
            "同一类中方法名相同，参数不同",
            "编译器通过参数匹配调用",
            "返回值和访问修饰符可不同",
            "属于静态绑定"
          ]
        },
        {
          "title": "重写",
          "lines": [
            "子类覆盖父类方法",
            "方法名和参数完全相同",
            "返回值可为父类子类，权限不能低于父类",
            "属于动态绑定"
          ]
        },
        {
          "title": "区别",
          "lines": [
            "重载是编译时确定，重写是运行时确定",
            "重载用于同一类，重写用于继承关系",
            "重载不改变方法签名，重写必须保持签名一致",
            "重载提高灵活性，重写增强扩展性"
          ]
        }
      ],
      "frames": [
        {
          "note": "重载和重写都属于多态，但绑定时机不同",
          "active": [
            0,
            1,
            2
          ]
        },
        {
          "note": "重载方法参数不同，重写方法参数必须相同",
          "active": [
            0,
            1
          ]
        },
        {
          "note": "重写方法返回值可为子类，权限不能低于父类",
          "active": [
            1
          ]
        },
        {
          "note": "重载是静态绑定，重写是动态绑定，这是核心区别",
          "active": [
            2
          ]
        }
      ]
    }
  },
  {
    "id": "java-basicq29",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Java 基础"
    ],
    "tags": [
      "面试",
      "Java 基础"
    ],
    "title": "什么是可变长参数？",
    "oneLine": "可变长参数是 Java5 引入的特性，允许方法接受不定数量的参数。",
    "analogy": "就像快递员可以收任意数量的包裹，不管是一包还是十包，都可以装进同一个箱子。",
    "why": "传统方法在调用时需要知道参数个数，而可变长参数解决了参数数量不确定的问题。当需要处理多个参数时，可变长参数能简化代码，提高灵活性。同时，它还能与固定参数共存，但会优先匹配固定参数，避免歧义。",
    "mechanism": [
      "可变长参数是 Java5 引入的一种方法参数类型，允许在调用方法时传入不定数量的参数。",
      "可变长参数在方法定义中使用省略号（...）表示，它只能作为方法的最后一个参数，前面可以有其他参数。",
      "当调用方法时，可变参数会被自动转换为一个数组，从而可以像操作数组一样处理这些参数。",
      "在方法重载的情况下，Java 会优先匹配固定参数的方法，因为固定参数的匹配度更高。",
      "可变参数在编译后会被转换为一个数组，因此在反编译后的 class 文件中可以看到对应的数组类型。",
      "使用可变参数可以简化代码，避免需要定义多个重载方法来处理不同数量的参数。",
      "可变参数在实际开发中常用于处理不确定数量的输入，如日志记录、数据收集等场景。"
    ],
    "keywords": [
      "可变长参数",
      "String... args",
      "方法重载",
      "数组",
      "固定参数"
    ],
    "scene": [
      "在日志记录系统中，可变参数用于收集任意数量的日志信息。",
      "在数据处理工具中，可变参数用于接收多个输入数据进行批量处理。",
      "在命令行工具中，可变参数用于处理用户输入的多个参数，如文件路径或选项。"
    ],
    "interviewQ": [
      "追问1：可变参数在方法重载时如何匹配？（答：Java 会优先匹配固定参数的方法，因为固定参数的匹配度更高。）",
      "追问2：可变参数在编译后会变成什么？（答：可变参数在编译后会被转换为一个数组，因此在反编译后的 class 文件中可以看到对应的数组类型。）",
      "追问3：可变参数可以出现在方法的哪个位置？（答：可变参数只能作为方法的最后一个参数，前面可以有其他参数。）"
    ],
    "related": [],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "定义参数",
        "调用方法",
        "处理参数"
      ],
      "frames": [
        {
          "s": 0,
          "note": "定义参数时使用String... args，只能作为最后一个参数，前面可有其他参数"
        },
        {
          "s": 1,
          "note": "调用方法时，参数会被自动转为数组，如log(\"msg\", \"arg1\", \"arg2\")"
        },
        {
          "s": 2,
          "note": "处理参数时可像数组一样操作，如遍历或计算总长度，编译后转为数组类型"
        }
      ]
    }
  },
  {
    "id": "java-collq03",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "集合"
    ],
    "tags": [
      "面试",
      "集合"
    ],
    "title": "集合框架底层数据结构总结",
    "oneLine": "集合框架底层数据结构是实现集合功能的核心，不同集合采用不同的数据结构以满足不同场景需求。",
    "analogy": "就像整理房间，不同的收纳方式（如抽屉、架子、箱子）适合不同的物品，集合框架中的数据结构也像不同的收纳方式，适合不同的使用场景。",
    "why": "集合框架中的数据结构设计是为了满足不同场景下的性能需求。例如，ArrayList 通过数组实现快速的随机访问，而 LinkedList 通过双向链表实现高效的插入和删除操作。HashMap 使用数组+链表/红黑树解决哈希冲突，提高查找效率。这些设计使得集合能够高效地处理各种数据操作，如增删改查。",
    "mechanism": [
      "ArrayList 是基于数组实现的，它通过动态数组存储元素，支持快速的随机访问，但插入和删除操作需要移动元素，效率较低。",
      "Vector 与 ArrayList 类似，也是基于数组实现，但它是线程安全的，内部使用 synchronized 关键字保证线程安全。",
      "LinkedList 是基于双向链表实现的，它通过节点之间的指针连接实现高效的插入和删除操作，但随机访问效率较低。",
      "HashSet 基于 HashMap 实现，使用哈希表存储元素，通过哈希函数计算元素的存储位置，确保元素的唯一性。",
      "LinkedHashSet 是 HashSet 的子类，内部使用 LinkedHashMap 实现，通过双向链表维护元素的插入顺序。",
      "TreeSet 基于红黑树实现，通过自平衡的排序二叉树维护元素的有序性，支持快速的查找、插入和删除操作。",
      "HashMap 在 JDK 1.8 之前使用数组+链表解决哈希冲突，JDK 1.8 后在链表长度超过阈值时转换为红黑树，以提高查找效率。",
      "LinkedHashMap 继承自 HashMap，在其基础上增加双向链表，用于维护元素的插入顺序或访问顺序。"
    ],
    "keywords": [
      "ArrayList",
      "Vector",
      "LinkedList",
      "HashSet",
      "LinkedHashSet",
      "TreeSet",
      "HashMap",
      "LinkedHashMap"
    ],
    "scene": [
      "在需要频繁随机访问元素的场景中，使用 ArrayList 会更高效。",
      "在需要频繁插入和删除元素的场景中，使用 LinkedList 会更高效。",
      "在需要存储唯一元素且不关心顺序的场景中，使用 HashSet 会更高效。"
    ],
    "interviewQ": [
      "追问1：ArrayList 和 LinkedList 有什么区别？（答：ArrayList 基于数组，支持快速随机访问，但插入和删除效率低；LinkedList 基于双向链表，插入和删除效率高，但随机访问效率低。）",
      "追问2：HashMap 在 JDK 1.8 后有什么变化？（答：JDK 1.8 后在链表长度超过阈值时转换为红黑树，以提高查找效率。）",
      "追问3：TreeSet 和 TreeSet 的底层数据结构是什么？（答：TreeSet 基于红黑树实现，支持快速的查找、插入和删除操作。）"
    ],
    "related": [
      {
        "id": "arraylist-linkedlist",
        "kind": "prereq",
        "note": "了解 ArrayList 与 LinkedList 的区别有助于理解集合框架底层数据结构"
      },
      {
        "id": "arraylist-array",
        "kind": "prereq",
        "note": "了解 ArrayList 与 Array 的区别有助于理解集合框架底层数据结构"
      },
      {
        "id": "java-collq10",
        "kind": "prereq",
        "note": "了解 ArrayList 的时间复杂度有助于理解集合框架底层数据结构"
      }
    ],
    "diagram": null
  },
  {
    "id": "arraylist-array",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "集合"
    ],
    "tags": [
      "面试",
      "集合"
    ],
    "title": "ArrayList 和 Array 的区别是什么？",
    "oneLine": "ArrayList 是动态数组，支持动态扩容和泛型；Array 是静态数组，长度固定，不支持泛型。",
    "analogy": "ArrayList 像一个可以自动变大的购物车，装不下时会自动扩容；Array 则像一个固定大小的购物袋，装不下就只能扔掉。",
    "why": "Array 是静态数组，长度固定，不能动态调整，适合已知数据量的场景。而 ArrayList 是动态数组，能根据数据量自动扩容，适合数据量不确定的场景。此外，ArrayList 支持泛型，能确保类型安全，而 Array 不支持泛型，容易出现类型错误。",
    "mechanism": [
      "ArrayList 是基于动态数组实现的集合类，它内部维护一个数组，当元素数量超过当前数组容量时，会自动扩容，以适应更多数据。",
      "Array 是静态数组，创建后长度固定，无法动态调整，只能通过重新创建数组来改变大小，这在数据量不确定时不够灵活。",
      "ArrayList 支持泛型，可以在创建时指定存储的数据类型，如 List<String>，确保类型安全，避免类型转换错误。",
      "Array 不支持泛型，只能存储基本类型或对象，无法在创建时指定类型，容易导致类型错误，需要手动进行类型转换。",
      "ArrayList 可以存储对象，而 Array 可以存储基本类型或对象，但无法直接存储对象数组以外的类型，如 List<String>。",
      "ArrayList 提供了丰富的 API 方法，如 add()、remove()、set() 等，支持插入、删除、修改等操作，而 Array 只能通过下标访问元素，无法直接进行插入和删除。",
      "ArrayList 在创建时不需要指定大小，可以动态增长，而 Array 在创建时必须指定大小，无法动态调整。",
      "ArrayList 支持 trimToSize() 方法，可以主动缩小底层数组，释放未使用的内存，而 Array 无法做到这一点。"
    ],
    "keywords": [
      "ArrayList",
      "Array",
      "动态数组",
      "静态数组",
      "泛型",
      "扩容"
    ],
    "scene": [
      "在开发一个动态数据处理系统时，使用 ArrayList 可以灵活添加和删除元素，而 Array 不适合这种场景。",
      "在需要存储大量基本类型数据时，Array 更加高效，因为它可以直接存储基本类型，而 ArrayList 需要使用包装类。",
      "在需要类型安全的代码中，ArrayList 通过泛型确保类型正确，而 Array 容易出现类型错误，需要手动转换。"
    ],
    "interviewQ": [
      "为什么 ArrayList 支持动态扩容？（答：ArrayList 内部维护一个数组，当元素数量超过当前容量时，会自动扩容，以适应更多数据。）",
      "ArrayList 和 Array 在存储基本类型时有什么区别？（答：Array 可以直接存储基本类型，而 ArrayList 需要使用对应的包装类，如 Integer、Double 等。）",
      "ArrayList 如何确保类型安全？（答：ArrayList 支持泛型，可以在创建时指定存储的数据类型，如 List<String>，确保类型正确，避免类型转换错误。）"
    ],
    "related": [
      {
        "id": "arraylist-linkedlist",
        "kind": "prereq",
        "note": "了解 ArrayList 与 LinkedList 的区别有助于理解 ArrayList 与 Array 的区别"
      },
      {
        "id": "java-collq10",
        "kind": "prereq",
        "note": "了解 ArrayList 的时间复杂度有助于理解 ArrayList 与 Array 的区别"
      },
      {
        "id": "java-collq03",
        "kind": "prereq",
        "note": "了解集合框架底层数据结构有助于理解 ArrayList 与 Array 的区别"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "ArrayList",
          "lines": [
            "动态数组，支持扩容",
            "支持泛型，类型安全",
            "提供丰富 API 操作",
            "可存储对象，灵活高效"
          ]
        },
        {
          "title": "Array",
          "lines": [
            "静态数组，长度固定",
            "不支持泛型，易类型错误",
            "只能通过下标访问",
            "存储基本类型更高效"
          ]
        }
      ],
      "frames": [
        {
          "note": "ArrayList 适合动态数据场景，如动态添加删除元素",
          "active": [
            0
          ]
        },
        {
          "note": "Array 适合存储大量基本类型数据，如 int[] 更高效",
          "active": [
            1
          ]
        },
        {
          "note": "ArrayList 通过泛型确保类型安全，避免类型转换错误",
          "active": [
            0
          ]
        },
        {
          "note": "Array 需手动类型转换，容易引发运行时错误",
          "active": [
            1
          ]
        }
      ]
    }
  },
  {
    "id": "java-collq10",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "集合"
    ],
    "tags": [
      "面试",
      "集合"
    ],
    "title": "ArrayList 插入和删除元素的时间复杂度是什么？",
    "oneLine": "ArrayList 插入和删除元素的时间复杂度取决于操作位置和数组容量，涉及元素移动和扩容。",
    "analogy": "就像整理书架，插入新书在中间需要挪动后面所有书，删除中间书也要挪动后面书，而尾部操作则更快。",
    "why": "ArrayList 是基于数组实现的，插入和删除操作需要移动元素以保持连续性。头部和中间插入删除需要移动大量元素，时间复杂度为 O(n)。尾部插入在未扩容时为 O(1)，扩容时需复制数组，时间复杂度为 O(n)。删除操作类似，尾部删除直接移除，而中间删除需要移动元素，时间复杂度也为 O(n)。",
    "mechanism": [
      "头部插入需要将所有元素向后移动一位，因此时间复杂度为 O(n)。",
      "尾部插入在数组未满时只需在末尾添加元素，时间复杂度为 O(1)；当数组满时需要扩容，复制原数组到新数组，再添加元素，时间复杂度为 O(n)。",
      "指定位置插入需要将该位置之后的所有元素向后移动一位，平均移动 n/2 个元素，时间复杂度为 O(n)。",
      "头部删除需要将所有元素向前移动一位，因此时间复杂度为 O(n)。",
      "尾部删除只需移除最后一个元素，时间复杂度为 O(1)。",
      "指定位置删除需要将该位置之后的所有元素向前移动一位，平均移动 n/2 个元素，时间复杂度为 O(n)。",
      "扩容操作会创建一个更大的数组，并将原数组元素复制到新数组，这会导致时间复杂度为 O(n)。",
      "ArrayList 通过动态扩容机制来应对元素数量增长，但扩容会带来额外的性能开销。"
    ],
    "keywords": [
      "时间复杂度",
      "插入",
      "删除",
      "扩容",
      "数组"
    ],
    "scene": [
      "在需要频繁插入头部元素的场景中，ArrayList 的性能较差，建议使用 LinkedList。",
      "在数据量较大且频繁进行尾部插入时，ArrayList 可能会因为扩容导致性能波动。",
      "在需要频繁删除中间元素的系统中，ArrayList 的时间复杂度较高，可能影响程序效率。"
    ],
    "interviewQ": [
      "为什么尾部插入在未扩容时是 O(1)？（答：因为只需在数组末尾添加元素，无需移动其他元素。）",
      "扩容操作对时间复杂度有什么影响？（答：扩容时需要复制原数组到新数组，时间复杂度为 O(n)。）",
      "指定位置插入和删除的时间复杂度为什么是 O(n)？（答：因为需要移动平均 n/2 个元素，导致时间复杂度为 O(n)。）"
    ],
    "related": [
      {
        "id": "arraylist-array",
        "kind": "prereq",
        "note": "了解 ArrayList 与 Array 的区别有助于理解插入和删除的时间复杂度"
      },
      {
        "id": "arraylist-linkedlist",
        "kind": "prereq",
        "note": "了解 ArrayList 与 LinkedList 的区别有助于理解插入和删除的时间复杂度"
      },
      {
        "id": "java-collq03",
        "kind": "prereq",
        "note": "了解集合框架底层数据结构有助于理解插入和删除的时间复杂度"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "ArrayList",
          "lines": [
            "头部/中间插入/删除需移动元素，O(n)",
            "尾部插入（非扩容）O(1)，扩容时O(n)",
            "扩容需复制数组，带来额外开销"
          ]
        },
        {
          "title": "LinkedList",
          "lines": [
            "插入/删除仅需调整指针，O(1)",
            "不涉及元素移动，性能更稳定",
            "不支持随机访问，内存碎片化"
          ]
        }
      ],
      "frames": [
        {
          "note": "ArrayList在频繁头部/中间操作时性能较差，而LinkedList更优",
          "active": [
            0,
            1
          ]
        },
        {
          "note": "ArrayList尾部插入可能因扩容导致性能波动，LinkedList无此问题",
          "active": [
            0,
            1
          ]
        },
        {
          "note": "ArrayList适合数据量大且以尾部操作为主的场景，LinkedList适合频繁插入删除的场景",
          "active": [
            0,
            1
          ]
        }
      ]
    }
  },
  {
    "id": "arraylist-linkedlist",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "集合"
    ],
    "tags": [
      "面试",
      "集合"
    ],
    "title": "ArrayList 与 LinkedList 区别？",
    "oneLine": "ArrayList 与 LinkedList 是 Java 中两种常用集合，区别在于底层数据结构、线程安全、插入删除效率、随机访问支持和内存占用。",
    "analogy": "ArrayList 像一个整齐排列的货架，可以快速找到商品；LinkedList 像一串连接的快递箱，只能从头或尾快速拿到箱子。",
    "why": "ArrayList 和 LinkedList 都不保证线程安全，但它们的底层结构不同，导致性能差异。ArrayList 用数组实现，支持快速随机访问，适合频繁读取；LinkedList 用双向链表实现，适合频繁在头尾插入删除。但链表在中间位置操作效率较低，且占用更多内存。因此，除非有特殊需求，一般推荐使用 ArrayList。",
    "mechanism": [
      "ArrayList 是基于数组实现的集合，通过索引直接访问元素，支持 O(1) 的随机访问，但插入和删除元素时需要移动其他元素，时间复杂度为 O(n)。",
      "LinkedList 是基于双向链表实现的集合，每个节点包含前后指针，支持在头尾快速插入和删除元素，时间复杂度为 O(1)，但随机访问需要遍历链表，时间复杂度为 O(n)。",
      "ArrayList 的数组结构在扩容时会创建新数组并复制元素，导致额外的内存开销和性能损耗，但可以高效访问元素。",
      "LinkedList 的每个节点都需要存储前后指针，导致每个元素占用更多内存，但插入和删除操作更高效。",
      "ArrayList 支持快速随机访问，因为数组的索引可以直接定位到元素，而 LinkedList 不支持，因为需要从头或尾遍历链表。",
      "ArrayList 的随机访问能力使其在需要频繁读取数据的场景中表现更优，而 LinkedList 在频繁插入和删除头尾元素时表现更优。",
      "由于 LinkedList 的插入和删除操作在中间位置效率较低，因此在大多数情况下，ArrayList 是更优的选择。",
      "RandomAccess 接口用于标识支持快速随机访问的集合，ArrayList 实现了该接口，而 LinkedList 没有实现，这影响了部分算法（如二分查找）的实现方式。"
    ],
    "keywords": [
      "ArrayList",
      "LinkedList",
      "RandomAccess",
      "数组",
      "链表",
      "随机访问"
    ],
    "scene": [
      "在需要频繁访问元素的场景中，如数据查询、统计，使用 ArrayList 更高效。",
      "在需要频繁在头尾插入或删除元素的场景中，如消息队列、缓存，使用 LinkedList 更高效。",
      "在内存受限的环境中，由于 LinkedList 每个元素占用更多内存，可能不适合使用。"
    ],
    "interviewQ": [
      "为什么在大多数情况下推荐使用 ArrayList 而不是 LinkedList？（答：ArrayList 的数组结构支持快速随机访问，且在内存使用上更高效，适合大多数场景。）",
      "RandomAccess 接口的作用是什么？（答：RandomAccess 接口用于标识支持快速随机访问的集合，影响部分算法（如二分查找）的实现方式。）",
      "LinkedList 在中间位置插入或删除元素的时间复杂度是多少？（答：O(n)，因为需要遍历到指定位置才能进行插入或删除操作。）"
    ],
    "related": [
      {
        "id": "arraylist-array",
        "kind": "prereq",
        "note": "了解 ArrayList 与 Array 的区别有助于理解 ArrayList 与 LinkedList 的区别"
      },
      {
        "id": "java-collq03",
        "kind": "prereq",
        "note": "了解集合框架底层数据结构有助于理解 ArrayList 与 LinkedList 的区别"
      },
      {
        "id": "java-collq10",
        "kind": "prereq",
        "note": "了解插入和删除的时间复杂度有助于理解 ArrayList 与 LinkedList 的区别"
      },
      {
        "id": "queue-deque",
        "kind": "compare",
        "note": "ArrayList 与 LinkedList 的插入删除方式能对比 Queue 与 Deque 的操作机制"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "ArrayList",
          "lines": [
            "基于数组实现，支持O(1)随机访问",
            "插入删除需移动元素，时间复杂度O(n)",
            "扩容时复制数组，内存开销大",
            "实现RandomAccess接口，适合频繁读取"
          ]
        },
        {
          "title": "LinkedList",
          "lines": [
            "基于双向链表实现，支持O(1)头尾插入删除",
            "随机访问需遍历链表，时间复杂度O(n)",
            "每个节点存储前后指针，内存占用更高",
            "不实现RandomAccess接口，不适合二分查找"
          ]
        }
      ],
      "frames": [
        {
          "note": "ArrayList适合频繁读取数据的场景，如数据查询、统计",
          "active": [
            0
          ]
        },
        {
          "note": "LinkedList适合频繁在头尾插入删除的场景，如消息队列、缓存",
          "active": [
            1
          ]
        },
        {
          "note": "内存受限时优先选ArrayList，LinkedList内存占用更高",
          "active": [
            0,
            1
          ]
        }
      ]
    }
  },
  {
    "id": "fail-fast-fail-safe",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "集合"
    ],
    "tags": [
      "面试",
      "集合"
    ],
    "title": "集合中的 fail-fast 和 fail-safe 是什么？",
    "oneLine": "fail-fast 是在并发修改时立即抛出异常，fail-safe 则在修改时复制快照，避免异常。",
    "analogy": "fail-fast 像是发现有人闯入房间就立刻报警，fail-safe 则像在房间外复制一份房间状态，即使有人闯入，也能继续使用复制的房间。",
    "why": "fail-fast 的设计是为了在并发修改时尽早发现错误，防止程序在不一致的数据上继续运行，避免更严重的后果。而 fail-safe 的设计是为了在不确定的环境中保持系统的稳定性，即使遇到异常也能继续运行，适用于不稳定或不可预测的场景。",
    "mechanism": [
      "fail-fast 是一种快速失败机制，当集合在迭代过程中被并发修改时，会立即抛出 ConcurrentModificationException 异常，以阻止程序继续运行在不一致的数据上。",
      "fail-fast 通过维护一个 modCount 变量来记录集合的修改次数，迭代器在每次 next() 调用时都会检查当前的 modCount 是否与预期的 expectedModCount 一致，如果不一致则抛出异常。",
      "fail-safe 是一种安全失败机制，它通过在修改时复制一份快照来避免并发修改带来的问题，即使在迭代过程中有其他线程修改集合，也不会影响当前的迭代操作。",
      "fail-safe 的实现方式是写时复制（Copy-On-Write），即在修改集合时，会复制一份新的数组，基于这个新数组进行修改，然后将底层数组的引用指向新的数组。",
      "fail-safe 的缺点是遍历操作无法获得实时结果，因为遍历的是复制的快照，而不是最新的数据。",
      "fail-fast 适用于需要立即发现错误并停止运行的场景，而 fail-safe 更适合在不确定或不稳定的环境中保持系统的稳定性。",
      "fail-fast 的实现方式是通过维护 modCount 和 expectedModCount 的比对，而 fail-safe 的实现方式是通过写时复制来避免并发修改带来的问题。",
      "fail-fast 和 fail-safe 的区别在于它们处理并发修改的方式不同，fail-fast 会在发现异常时立即停止运行，而 fail-safe 会继续运行并基于快照进行操作。"
    ],
    "keywords": [
      "fail-fast",
      "fail-safe",
      "ConcurrentModificationExceptio",
      "CopyOnWriteArrayList",
      "modCount",
      "expectedModCount"
    ],
    "scene": [
      "在多线程环境下使用 ArrayList 时，如果其他线程修改了集合，会导致 ConcurrentModificationException 异常，这是 fail-fast 的典型应用场景。",
      "在需要高并发和稳定性的场景中，如日志系统或消息队列，使用 CopyOnWriteArrayList 可以避免并发修改带来的问题，这是 fail-safe 的典型应用场景。",
      "在不确定的环境中，如网络通信或传感器数据采集，使用 fail-safe 机制可以确保系统在异常情况下仍能继续运行，这是 fail-safe 的典型应用场景。"
    ],
    "interviewQ": [
      "追问1：fail-fast 和 fail-safe 的区别是什么？（答：fail-fast 在并发修改时立即抛出异常，fail-safe 通过复制快照避免异常。）",
      "追问2：fail-fast 的实现原理是什么？（答：fail-fast 通过维护 modCount 和 expectedModCount 的比对，发现并发修改时抛出异常。）",
      "追问3：fail-safe 的实现原理是什么？（答：fail-safe 通过写时复制（Copy-On-Write）来避免并发修改带来的问题，修改时复制快照并更新引用。）"
    ],
    "related": [
      {
        "id": "priorityqueue",
        "kind": "compare",
        "note": "PriorityQueue 的优先级排序能对比 fail-fast 和 fail-safe 的异常处理逻辑"
      },
      {
        "id": "arrayblockingqueue-linkedblockingqueue",
        "kind": "compare",
        "note": "ArrayBlockingQueue 和 LinkedBlockingQueue 的实现方式能对比 fail-fast 和 fail-safe 的差异"
      },
      {
        "id": "comparable-comparator",
        "kind": "compare",
        "note": "Comparable 和 Comparator 的排序机制能对比 fail-fast 和 fail-safe 的设计逻辑"
      },
      {
        "id": "queue-deque",
        "kind": "compare",
        "note": "Queue 和 Deque 的区别能帮助理解 fail-fast 和 fail-safe 的实现机制"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "fail-fast",
          "lines": [
            "并发修改立即抛异常",
            "通过 modCount 检查",
            "适用于需要立即停止的场景",
            "可能导致程序中断"
          ]
        },
        {
          "title": "fail-safe",
          "lines": [
            "修改时复制快照",
            "写时复制（Copy-On-Write）",
            "迭代不受其他线程影响",
            "无法获取实时数据"
          ]
        }
      ],
      "frames": [
        {
          "note": "fail-fast 通过 modCount 检查，确保迭代一致性，但会中断程序。",
          "active": [
            0
          ]
        },
        {
          "note": "fail-safe 通过复制快照避免异常，适合高并发但容忍数据延迟的场景。",
          "active": [
            1
          ]
        },
        {
          "note": "fail-fast 适用于需要立即发现错误的场景，fail-safe 更适合不稳定环境。",
          "active": [
            0,
            1
          ]
        }
      ]
    }
  },
  {
    "id": "comparable-comparator",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "集合"
    ],
    "tags": [
      "面试",
      "集合"
    ],
    "title": "Comparable 和 Comparator 的区别",
    "oneLine": "Comparable 和 Comparator 都用于排序，但前者是对象内置排序方式，后者是外部定制排序方式。",
    "analogy": "Comparable 好比是自带排序功能的快递员，Comparator 好比是临时请来的快递员，可以根据不同需求灵活安排。",
    "why": "在 Java 中，对象默认没有排序能力，所以需要通过接口实现排序逻辑。Comparable 接口让对象自己定义排序规则，适用于单一种排序方式；Comparator 接口则允许在不修改对象的情况下，通过外部类定义排序规则，适用于需要多种排序方式的情况。这种设计提高了代码的灵活性和复用性。",
    "mechanism": [
      "Comparable 接口是 Java 标准库中的一个接口，它定义了 `compareTo(Object obj)` 方法，用于比较两个对象的大小，通常用于实现自然排序。",
      "Comparator 接口是 Java 标准库中的另一个接口，它定义了 `compare(Object obj1, Object obj2)` 方法，用于比较两个对象的大小，通常用于实现定制排序。",
      "当一个类实现了 Comparable 接口，它就可以使用 `Collections.sort()` 方法进行排序，无需额外提供 Comparator。",
      "当需要对一个集合进行多种排序方式时，可以使用 Comparator 接口，通过传入不同的 Comparator 实现不同的排序逻辑。",
      "Comparator 接口允许在不修改对象的情况下，通过外部类定义排序规则，使得代码更加灵活。",
      "在使用 Comparator 时，可以通过 `Collections.sort(list, comparator)` 方法进行排序，其中 comparator 是一个实现了 Comparator 接口的类。",
      "Comparator 接口可以用于实现多个排序策略，例如在 TreeMap 中，可以通过 Comparator 来定义键的排序方式。",
      "Comparator 接口的灵活性使得它在需要多种排序方式的场景中更加适用，而 Comparable 接口则更适合单一种排序方式。"
    ],
    "keywords": [
      "Comparable",
      "Comparator",
      "compareTo",
      "compare",
      "Collections.sort",
      "TreeMap"
    ],
    "scene": [
      "在需要对集合进行单一种排序方式时，使用 Comparable 接口实现对象的自然排序。",
      "在需要对集合进行多种排序方式时，使用 Comparator 接口实现定制排序。",
      "在 TreeMap 中，通过 Comparator 接口定义键的排序方式，实现按年龄排序的 TreeMap。"
    ],
    "interviewQ": [
      "追问1：Comparable 和 Comparator 哪个更适用于需要多种排序方式的场景？（答：Comparator 更适用于需要多种排序方式的场景，因为它可以在不修改对象的情况下定义不同的排序逻辑。）",
      "追问2：如果一个类已经实现了 Comparable 接口，是否还能使用 Comparator 接口进行排序？（答：可以，只要在排序时传入一个 Comparator 实例，就可以覆盖默认的排序方式。）",
      "追问3：Comparator 接口的 compare 方法返回值的含义是什么？（答：返回值为负数表示第一个参数小于第二个参数，为零表示相等，为正数表示第一个参数大于第二个参数。）"
    ],
    "related": [
      {
        "id": "queue-deque",
        "kind": "compare",
        "note": "Queue 和 Deque 的操作方式能对比 Comparable 和 Comparator 的使用场景"
      },
      {
        "id": "priorityqueue",
        "kind": "prereq",
        "note": "PriorityQueue 的排序依赖 Comparable 和 Comparator 的机制"
      },
      {
        "id": "arrayblockingqueue-linkedblockingqueue",
        "kind": "compare",
        "note": "ArrayBlockingQueue 和 LinkedBlockingQueue 的排序方式能对比 Comparable 和 Comparator 的差异"
      },
      {
        "id": "fail-fast-fail-safe",
        "kind": "compare",
        "note": "fail-fast 和 fail-safe 的异常处理能对比 Comparable 和 Comparator 的设计逻辑"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "Comparable",
          "lines": [
            "对象内置排序方式",
            "实现 compareTo 方法",
            "适用于自然排序",
            "无需额外 Comparator"
          ]
        },
        {
          "title": "Comparator",
          "lines": [
            "外部定制排序方式",
            "实现 compare 方法",
            "支持多种排序策略",
            "无需修改对象"
          ]
        }
      ],
      "frames": [
        {
          "note": "Comparable 适合单一种排序方式，如自然排序",
          "active": [
            0
          ]
        },
        {
          "note": "Comparator 适合多种排序方式，如 TreeMap 的键排序",
          "active": [
            1
          ]
        },
        {
          "note": "Comparator 可通过外部类定义排序规则，提升代码灵活性",
          "active": [
            1
          ]
        }
      ]
    }
  },
  {
    "id": "queue-deque",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "集合"
    ],
    "tags": [
      "面试",
      "集合"
    ],
    "title": "Queue 与 Deque 的区别",
    "oneLine": "Queue 是单端队列，只能在队首删除、队尾插入；Deque 是双端队列，可在两端插入和删除。",
    "analogy": "Queue 像排队买票，只能从队尾进、队首出；Deque 像可以双向进出的队伍，队首和队尾都可以进和出。",
    "why": "Queue 的设计是为了实现先进先出的顺序，适用于需要按顺序处理任务的场景。而 Deque 的设计是为了更灵活地处理数据，支持在两端进行操作，适用于需要频繁在两端插入或删除元素的场景。Queue 的方法在操作失败时会抛出异常，而 Deque 的方法则会返回特殊值，这样可以避免程序崩溃。",
    "mechanism": [
      "Queue 是单端队列，只能从一端插入元素，另一端删除元素，遵循先进先出（FIFO）规则。",
      "Queue 接口扩展了 Collection 接口，根据操作失败后的处理方式分为两类：一种在操作失败后会抛出异常，另一种则会返回特殊值。",
      "Queue 的插入队尾方法有 add(E e) 和 offer(E e)，前者在队列满时会抛出异常，后者则返回 false。",
      "Queue 的删除队首方法有 remove() 和 poll()，前者在队列为空时会抛出异常，后者则返回 null。",
      "Deque 是双端队列，可以在队首和队尾进行插入和删除操作，扩展了 Queue 接口。",
      "Deque 的插入队首方法有 addFirst(E e) 和 offerFirst(E e)，前者在队列满时会抛出异常，后者则返回 false。",
      "Deque 的删除队首方法有 removeFirst() 和 pollFirst()，前者在队列为空时会抛出异常，后者则返回 null。",
      "Deque 还提供了 push() 和 pop() 方法，可用于模拟栈，实现后进先出（LIFO）的顺序。"
    ],
    "keywords": [
      "Queue",
      "Deque",
      "FIFO",
      "add",
      "offer",
      "remove",
      "poll"
    ],
    "scene": [
      "在操作系统中，进程调度使用 Queue 来管理等待执行的进程。",
      "在浏览器中，页面加载时使用 Deque 来管理请求队列，支持在两端插入和删除请求。",
      "在游戏开发中，使用 Deque 来管理游戏对象的事件队列，支持在两端快速插入和删除事件。"
    ],
    "interviewQ": [
      "Queue 和 Deque 的区别是什么？（答：Queue 是单端队列，只能在队首删除、队尾插入；Deque 是双端队列，可在两端插入和删除。）",
      "Queue 的方法在操作失败时如何处理？（答：Queue 的方法在操作失败时会抛出异常，而返回特殊值的方法则不会抛出异常。）",
      "Deque 的方法在操作失败时如何处理？（答：Deque 的方法在操作失败时会返回特殊值，如 null 或 false，而不会抛出异常。）",
      "Deque 为什么可以模拟栈？（答：Deque 提供了 push() 和 pop() 方法，可以用于模拟栈的后进先出（LIFO）顺序。）"
    ],
    "related": [
      {
        "id": "arraylist-linkedlist",
        "kind": "compare",
        "note": "ArrayList 与 LinkedList 的插入删除方式能对比 Queue 与 Deque 的操作机制"
      },
      {
        "id": "arrayblockingqueue-linkedblockingqueue",
        "kind": "extends",
        "note": "ArrayBlockingQueue 和 LinkedBlockingQueue 是 Queue 的具体实现"
      },
      {
        "id": "priorityqueue",
        "kind": "compare",
        "note": "PriorityQueue 的优先级排序能对比 Queue 与 Deque 的操作逻辑"
      },
      {
        "id": "fail-fast-fail-safe",
        "kind": "compare",
        "note": "fail-fast 和 fail-safe 的异常处理能对比 Queue 与 Deque 的实现差异"
      },
      {
        "id": "comparable-comparator",
        "kind": "compare",
        "note": "Queue 和 Deque 的操作方式能对比 Comparable 和 Comparator 的使用场景"
      }
    ],
    "diagram": null
  },
  {
    "id": "priorityqueue",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "集合"
    ],
    "tags": [
      "面试",
      "集合"
    ],
    "title": "PriorityQueue 是什么？",
    "oneLine": "PriorityQueue 是一种基于堆结构的队列，元素出队顺序根据优先级决定。",
    "analogy": "PriorityQueue 就像一个快递站，快递员总是优先处理最紧急的包裹，而不是按送达顺序。",
    "why": "在普通队列中，元素是按先进先出的顺序出队，无法根据优先级排序。PriorityQueue 的出现解决了这个问题，使得高优先级的任务能更快被处理，例如任务调度、事件处理等场景。传统的队列无法满足这种需求，因此需要一种新的数据结构来实现优先级排序。",
    "mechanism": [
      "PriorityQueue 是一种基于堆结构的队列，其核心思想是维护一个优先级顺序，使得每次出队时取出优先级最高的元素。",
      "PriorityQueue 使用二叉堆实现，底层采用可变长数组存储数据，通过堆的上浮和下沉操作保持堆的性质。",
      "插入元素时，新元素会被放置在数组末尾，然后通过上浮操作，与父节点比较并交换位置，直到满足堆的性质。",
      "删除堆顶元素时，将最后一个元素移动到堆顶，然后通过下沉操作，与子节点比较并交换位置，直到满足堆的性质。",
      "PriorityQueue 默认是小顶堆，即堆顶元素是所有元素中最小的，但可以通过提供 Comparator 参数来定义自定义的优先级顺序。",
      "PriorityQueue 不支持存储 NULL 值，且在未提供 Comparator 时，元素需要实现 Comparable 接口以支持比较。",
      "Priority、Queue 是非线程安全的，因此在多线程环境中需要额外的同步机制。",
      "PriorityQueue 的插入和删除操作的时间复杂度为 O(log n)，这使得它在处理大量数据时效率较高。"
    ],
    "keywords": [
      "PriorityQueue",
      "二叉堆",
      "上浮",
      "下沉",
      "Comparator",
      "Comparable"
    ],
    "scene": [
      "在任务调度系统中，PriorityQueue 可用于管理不同优先级的任务，确保高优先级任务优先执行。",
      "在带权图的最短路径算法中，如 Dijkstra 算法，PriorityQueue 用于维护当前最短路径的节点。",
      "在 Top K 问题中，PriorityQueue 用于快速找到前 K 大或前 K 小的元素。"
    ],
    "interviewQ": [
      "PriorityQueue 和普通队列有什么区别？（答：PriorityQueue 的出队顺序是根据优先级决定的，而普通队列是先进先出。）",
      "PriorityQueue 是如何实现插入和删除操作的？（答：插入时通过上浮操作维护堆结构，删除时通过下沉操作维护堆结构。）",
      "PriorityQueue 默认是小顶堆还是大顶堆？如何自定义优先级？（答：默认是小顶堆，可以通过 Comparator 参数定义自定义的优先级顺序。）"
    ],
    "related": [
      {
        "id": "comparable-comparator",
        "kind": "prereq",
        "note": "PriorityQueue 的排序依赖 Comparable 和 Comparator 的机制"
      },
      {
        "id": "fail-fast-fail-safe",
        "kind": "compare",
        "note": "fail-fast 和 fail-safe 的异常处理能对比 PriorityQueue 的线程安全设计"
      },
      {
        "id": "arrayblockingqueue-linkedblockingqueue",
        "kind": "compare",
        "note": "ArrayBlockingQueue 和 LinkedBlockingQueue 的线程安全机制能对比 PriorityQueue 的实现"
      },
      {
        "id": "queue-deque",
        "kind": "compare",
        "note": "Queue 和 Deque 的操作方式能对比 PriorityQueue 的优先级排序逻辑"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "插入元素",
        "维护堆结构",
        "出队元素"
      ],
      "frames": [
        {
          "s": 0,
          "note": "插入元素时，新元素被添加到数组末尾，随后通过上浮操作与父节点比较并交换位置，直到满足堆的性质。"
        },
        {
          "s": 1,
          "note": "堆的上浮和下沉操作确保了堆的性质，即父节点的优先级始终高于子节点，从而维持优先级顺序。"
        },
        {
          "s": 2,
          "note": "出队时，堆顶元素（优先级最高）被移除，最后一个元素补位后通过下沉操作重新调整堆结构，保证优先级顺序不变。"
        }
      ]
    }
  },
  {
    "id": "arrayblockingqueue-linkedblockingqueue",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "集合"
    ],
    "tags": [
      "面试",
      "集合"
    ],
    "title": "ArrayBlockingQueue 和 LinkedBlockingQueue 有什么区别？",
    "oneLine": "ArrayBlockingQueue 和 LinkedBlockingQueue 是 Java 并发包中两种线程安全的阻塞队列，它们在实现方式、容量、锁机制和内存占用等方面存在差异。",
    "analogy": "就像两个人在超市排队结账，ArrayBlockingQueue 是固定长度的队伍，而 LinkedBlockingQueue 是可以无限增长的队伍，但也可以设定长度。两人分别用不同的通道结账，避免互相干扰。",
    "why": "在多线程环境中，队列需要保证线程安全，避免数据竞争。ArrayBlockingQueue 通过数组实现，容量固定，适合有界场景；LinkedBlockingQueue 通过链表实现，容量可动态扩展，适合无界或可控的有界场景。锁分离机制能减少锁竞争，提高并发性能。",
    "mechanism": [
      "ArrayBlockingQueue 是基于数组实现的有界阻塞队列，容量在创建时指定，不允许超过，适合需要控制队列大小的场景。",
      "LinkedBlockingQueue 是基于链表实现的阻塞队列，容量可以不指定，默认无界，也可以指定为有界，灵活性更高。",
      "ArrayBlockingQueue 使用单个锁对象，生产和消费共享同一个锁，可能导致锁竞争，影响性能。",
      "LinkedBlockingQueue 使用两个锁对象，生产用 putLock，消费用 takeLock，锁分离可以减少锁竞争，提高并发效率。",
      "ArrayBlockingQueue 在创建时需要预先分配数组内存，内存占用相对固定，但可能比实际使用的大。",
      "LinkedBlockingQueue 是动态分配链表节点内存，内存占用随元素增加而增长，内存利用率更高。",
      "ArrayBlockingQueue 的数组结构在数据插入和删除时需要移动元素，时间复杂度较高。",
      "LinkedBlockingQueue 的链表结构在数据插入和删除时只需修改指针，时间复杂度较低，效率更高。"
    ],
    "keywords": [
      "ArrayBlockingQueue",
      "LinkedBlockingQueue",
      "阻塞队列",
      "有界队列"
    ],
    "scene": [
      "在生产者-消费者模型中，ArrayBlockingQueue 适合需要严格控制队列容量的场景，如缓存管理。",
      "在高并发的系统中，LinkedBlockingQueue 因其锁分离机制，适合需要高吞吐量的场景，如任务调度。",
      "在内存敏感的系统中，ArrayBlockingQueue 因其内存占用固定，适合需要预分配内存的场景，如嵌入式系统。"
    ],
    "interviewQ": [
      "为什么 ArrayBlockingQueue 是有界队列，而 LinkedBlockingQueue 可以是无界的？（答：ArrayBlockingQueue 在创建时必须指定容量，而 LinkedBlockingQueue 默认无界，也可以指定容量成为有界队列。）",
      "ArrayBlockingQueue 和 LinkedBlockingQueue 在锁机制上有何不同？（答：ArrayBlockingQueue 使用单个锁，而 LinkedBlockingQueue 使用两个锁，分别用于生产和消费，减少锁竞争。）",
      "LinkedBlockingQueue 的内存占用和 ArrayBlockingQueue 有何差异？（答：ArrayBlockingQueue 需要预先分配数组内存，而 LinkedBlockingQueue 是动态分配链表节点内存，内存利用率更高。）"
    ],
    "related": [
      {
        "id": "comparable-comparator",
        "kind": "compare",
        "note": "Comparable 和 Comparator 的排序机制能对比 ArrayBlockingQueue 和 LinkedBlockingQueue 的线程安全设计"
      },
      {
        "id": "fail-fast-fail-safe",
        "kind": "compare",
        "note": "fail-fast 和 fail-safe 的异常处理能对比 ArrayBlockingQueue 和 LinkedBlockingQueue 的实现"
      },
      {
        "id": "priorityqueue",
        "kind": "compare",
        "note": "PriorityQueue 的优先级排序能对比 ArrayBlockingQueue 和 LinkedBlockingQueue 的线程安全机制"
      },
      {
        "id": "queue-deque",
        "kind": "extends",
        "note": "ArrayBlockingQueue 和 LinkedBlockingQueue 是 Queue 的具体实现"
      }
    ],
    "diagram": null
  },
  {
    "id": "java-mysqlq14",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "MySQL"
    ],
    "tags": [
      "面试",
      "MySQL"
    ],
    "title": "MySQL 支持哪些存储引擎？默认使用哪个？",
    "oneLine": "MySQL 支持多种存储引擎，其中 InnoDB 是默认的事务性存储引擎。",
    "analogy": "就像超市里有不同种类的货架，MySQL 提供了多种存储引擎，InnoDB 像是专门用来处理购物车结算的货架，支持事务操作。",
    "why": "在早期版本中，MyISAM 是默认存储引擎，但它不支持事务，数据安全性较低。随着 MySQL 版本升级，InnoDB 成为默认引擎，因为它支持事务、行级锁和崩溃恢复，更适合高并发和数据一致性要求高的场景。因此，MySQL 5.5.5 版本之后，InnoDB 成为默认存储引擎。",
    "mechanism": [
      "MySQL 支持多种存储引擎，如 InnoDB、MyISAM、Memory、Archive 等，每种引擎有不同的特性。",
      "InnoDB 是事务性存储引擎，支持 ACID 特性，确保数据的一致性和可靠性。",
      "MyISAM 是非事务性引擎，适合只读或低并发的场景，但不支持事务和行级锁。",
      "存储引擎的选择会影响性能和功能，如 InnoDB 支持崩溃恢复，而 MyISAM 不支持。",
      "MySQL 5.5.5 版本之后，默认使用 InnoDB，而之前版本默认使用 MyISAM。",
      "通过 `SHOW ENGINES` 可以查看所有支持的存储引擎，`SHOW VARIABLES LIKE '%storage_engine%'` 可以查看当前默认引擎。",
      "InnoDB 是 MySQL 中最常用和功能最全面的存储引擎，适合大多数应用场景。"
    ],
    "keywords": [
      "存储引擎",
      "InnoDB",
      "MyISAM",
      "事务性存储引擎",
      "默认存储引擎"
    ],
    "scene": [
      "在高并发的电商系统中，使用 InnoDB 确保订单数据的事务一致性。",
      "在只读的报表系统中，使用 MyISAM 提高查询性能。",
      "在需要临时存储数据的场景中，使用 Memory 引擎提升速度。"
    ],
    "interviewQ": [
      "为什么 MySQL 5.5.5 版本之后默认使用 InnoDB？（答：InnoDB 支持事务、行级锁和崩溃恢复，适合高并发和数据一致性要求高的场景。）",
      "InnoDB 和 MyISAM 的主要区别是什么？（答：InnoDB 支持事务和行级锁，而 MyISAM 不支持，且不支持崩溃恢复。）",
      "如何查看 MySQL 当前的默认存储引擎？（答：使用 `SHOW VARIABLES LIKE '%storage_engine%'` 命令查看默认存储引擎。）"
    ],
    "related": [
      {
        "id": "myisam-innodb",
        "kind": "prereq",
        "note": "了解存储引擎差异才能理解为什么 InnoDB 成为默认选择"
      },
      {
        "id": "java-mysqlq36",
        "kind": "compare",
        "note": "表级锁和行级锁是锁机制的具体表现，与存储引擎特性相关"
      },
      {
        "id": "java-mysql-sql-executed",
        "kind": "extends",
        "note": "了解存储引擎是理解SQL执行过程的基础，因为执行器依赖存储引擎实现"
      }
    ],
    "diagram": null
  },
  {
    "id": "myisam-innodb",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "MySQL"
    ],
    "tags": [
      "面试",
      "MySQL"
    ],
    "title": "MyISAM 和 InnoDB 有什么区别？",
    "oneLine": "MyISAM 和 InnoDB 是 MySQL 的两种存储引擎，区别主要体现在锁机制、事务支持、外键、崩溃恢复、MVCC 等方面。",
    "analogy": "MyISAM 像一家只能同时接待一个顾客的餐厅，而 InnoDB 像一家可以同时接待多个顾客的餐厅，每个人点什么菜都不影响其他人。",
    "why": "在高并发写操作中，MyISAM 的表级锁会导致性能下降，而 InnoDB 的行级锁可以提高并发性能。此外，MyISAM 不支持事务和崩溃恢复，导致数据不安全，而 InnoDB 通过事务和日志机制保证了数据的一致性和可靠性。因此，InnoDB 更适合现代应用的需求。",
    "mechanism": [
      "MyISAM 是 MySQL 5.5 之前默认的存储引擎，支持全文索引、压缩和空间函数，但不支持事务和行级锁，导致并发写性能差。",
      "InnoDB 是 MySQL 5.5 之后的默认存储引擎，支持事务、行级锁和外键，通过 MVCC 实现高并发下的数据一致性。",
      "MyISAM 使用表级锁，当一个表被写入时，其他操作必须等待，这在并发写场景下会严重影响性能。",
      "InnoDB 使用行级锁，可以同时对不同行加锁，提高并发写性能，同时支持表级锁作为备选。",
      "MyISAM 不支持事务，无法进行提交和回滚操作，导致数据在崩溃后无法恢复。",
      "InnoDB 支持事务，通过提交和回滚操作保证数据的一致性，并在崩溃后通过 redo log 恢复到崩溃前的状态。",
      "MyISAM 不支持外键，无法维护数据完整性，而 InnoDB 支持外键，有助于保持数据的一致性。",
      "MyISAM 不支持 MVCC，而 InnoDB 通过 MVCC 减少锁操作，提高并发性能。"
    ],
    "keywords": [
      "MyISAM",
      "InnoDB",
      "行级锁",
      "事务",
      "外键",
      "MVCC"
    ],
    "scene": [
      "在高并发的电商系统中，使用 InnoDB 可以避免表级锁导致的性能瓶颈。",
      "在需要保证数据一致性的金融系统中，InnoDB 的事务支持是必须的。",
      "在日志系统中，使用 MyISAM 的压缩特性可以节省存储空间。"
    ],
    "interviewQ": [
      "InnoDB 为什么支持行级锁？（答：InnoDB 通过行级锁提高并发写性能，避免表级锁导致的性能瓶颈。）",
      "InnoDB 如何实现崩溃恢复？（答：InnoDB 通过 redo log 记录事务操作，崩溃后根据日志恢复到一致状态。）",
      "为什么 InnoDB 支持 MVCC？（答：MVCC 通过版本链减少锁操作，提高并发性能，避免死锁。）"
    ],
    "related": [
      {
        "id": "java-mysqlq36",
        "kind": "compare",
        "note": "表级锁和行级锁是锁机制的具体表现，与存储引擎特性相关"
      },
      {
        "id": "java-mysqlq14",
        "kind": "prereq",
        "note": "了解存储引擎差异才能理解为什么 InnoDB 成为默认选择"
      },
      {
        "id": "java-mysqlq40",
        "kind": "extends",
        "note": "意向锁是 InnoDB 锁机制的一部分，与存储引擎特性相关"
      },
      {
        "id": "java-mysqlq39",
        "kind": "compare",
        "note": "共享锁和排他锁是锁机制的具体表现，与存储引擎特性相关"
      },
      {
        "id": "java-mysqlq42",
        "kind": "extends",
        "note": "了解InnoDB和MyISAM的区别，能更好理解自增锁是InnoDB特有的机制"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "MyISAM",
          "lines": [
            "表级锁，写操作阻塞其他操作",
            "不支持事务，无法回滚",
            "不支持外键，数据完整性弱",
            "不支持 MVCC，并发性能低"
          ]
        },
        {
          "title": "InnoDB",
          "lines": [
            "行级锁，支持高并发写入",
            "支持事务，保证数据一致性",
            "支持外键，维护数据完整性",
            "通过 MVCC 实现高并发"
          ]
        }
      ],
      "frames": [
        {
          "note": "InnoDB 适合需要高并发写和事务支持的场景，如电商系统。",
          "active": [
            1
          ]
        },
        {
          "note": "MyISAM 适合日志系统，利用压缩特性节省存储空间。",
          "active": [
            0
          ]
        },
        {
          "note": "InnoDB 崩溃后可通过 redo log 恢复数据，而 MyISAM 无法恢复。",
          "active": [
            1
          ]
        }
      ]
    }
  },
  {
    "id": "java-mysqlq36",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "MySQL"
    ],
    "tags": [
      "面试",
      "MySQL"
    ],
    "title": "表级锁和行级锁了解吗？有什么区别？",
    "oneLine": "表级锁锁整张表，行级锁锁具体行，行级锁并发性能更好。",
    "analogy": "表级锁就像在图书馆门口挂‘禁止入内’，行级锁就像在某本书上贴‘正在借阅’，后者更精准，减少干扰。",
    "why": "表级锁简单高效，但高并发下冲突多，影响性能；行级锁更精细，减少冲突，提升并发度，但实现复杂，开销更大。因此，InnoDB默认使用行级锁以适应高并发需求。",
    "mechanism": [
      "表级锁是一种锁定粒度较大的锁，它对整张表进行加锁，适用于非索引字段，实现简单，资源消耗少，加锁速度快。",
      "表级锁在加锁时不会区分具体行，因此在并发写入时容易发生冲突，导致高并发下性能下降。",
      "行级锁是一种锁定粒度较小的锁，它只对特定行记录进行加锁，适用于索引字段，能有效减少锁冲突。",
      "行级锁在加锁时需要定位到具体行，因此实现复杂，资源消耗大，加锁速度较慢，但能提升并发度。",
      "行级锁在存储引擎层面实现，InnoDB支持行级锁，而MyISAM虽然也支持表级锁，但不支持行级锁。",
      "行级锁虽然可能引发死锁，但其并发度高，适合高并发写入的场景，如电商平台的订单处理。",
      "表级锁在MySQL中是通用的，适用于所有存储引擎，但其并发性能较差，不适合高并发写入。",
      "行级锁的锁粒度更小，能提升并发性能，但需要确保索引字段的正确使用，否则可能影响性能。"
    ],
    "keywords": [
      "表级锁",
      "行级锁",
      "索引字段",
      "并发写入",
      "存储引擎"
    ],
    "scene": [
      "电商平台在处理订单时，使用行级锁确保每笔订单的独立性，避免冲突。",
      "日志系统中，表级锁用于批量处理日志数据，减少锁冲突。",
      "高并发的社交平台，使用行级锁优化用户点赞操作，提升性能。"
    ],
    "interviewQ": [
      "为什么行级锁的并发性能更高？（答：行级锁只锁定具体行，减少锁冲突，提升并发度。）",
      "行级锁和表级锁在实现上有什么不同？（答：行级锁在存储引擎层面实现，针对索引字段；表级锁是通用锁，适用于非索引字段。）",
      "在什么场景下会使用表级锁？（答：表级锁适用于批量处理或非索引字段操作，如日志系统。）"
    ],
    "related": [
      {
        "id": "myisam-innodb",
        "kind": "prereq",
        "note": "了解存储引擎差异才能理解表级锁和行级锁的适用场景"
      },
      {
        "id": "java-mysqlq40",
        "kind": "compare",
        "note": "意向锁是行级锁的补充，与锁机制相关"
      },
      {
        "id": "java-mysqlq39",
        "kind": "compare",
        "note": "共享锁和排他锁是锁机制的具体表现，与锁类型相关"
      },
      {
        "id": "java-mysqlq14",
        "kind": "compare",
        "note": "表级锁和行级锁是锁机制的具体表现，与存储引擎特性相关"
      },
      {
        "id": "java-mysqlq42",
        "kind": "compare",
        "note": "了解表级锁和行级锁的区别，有助于理解自增锁作为表级锁的特性"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "表级锁",
          "lines": [
            "锁整张表，资源消耗少",
            "加锁速度快，实现简单",
            "并发写入冲突高，性能差"
          ]
        },
        {
          "title": "行级锁",
          "lines": [
            "锁具体行，粒度更小",
            "并发性能高，适合高并发",
            "实现复杂，资源消耗大"
          ]
        }
      ],
      "frames": [
        {
          "note": "表级锁适用于非索引字段，但高并发下容易冲突",
          "active": [
            0
          ]
        },
        {
          "note": "行级锁在InnoDB中实现，能有效减少锁冲突",
          "active": [
            1
          ]
        },
        {
          "note": "表级锁是通用锁，但性能较差，不适合高并发写入",
          "active": [
            0
          ]
        },
        {
          "note": "行级锁可能引发死锁，但能提升电商订单处理性能",
          "active": [
            1
          ]
        }
      ]
    }
  },
  {
    "id": "java-mysqlq39",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "MySQL"
    ],
    "tags": [
      "面试",
      "MySQL"
    ],
    "title": "共享锁和排他锁是什么？",
    "oneLine": "共享锁（S锁）允许多事务同时读取，排他锁（X锁）独占写入，锁类型之间存在兼容性差异。",
    "analogy": "共享锁就像图书馆的书可以多人同时借阅，排他锁则像借书时必须独自占有书本，其他人不能借阅。",
    "why": "共享锁和排他锁是数据库并发控制的核心机制，用于解决多个事务同时访问数据时的冲突问题。共享锁允许读取操作，确保数据一致性；排他锁则用于写入操作，防止数据被其他事务修改。如果没有锁机制，多个事务同时修改同一数据可能导致数据不一致或错误。因此，锁机制是保证事务隔离性和数据一致性的关键。",
    "mechanism": [
      "共享锁（S锁）是一种读锁，当事务读取记录时获取，允许多个事务同时获取，锁兼容，确保数据可以被多个事务同时读取。",
      "排他锁（X锁）是一种写锁，当事务修改记录时获取，不允许其他事务同时获取，锁不兼容，确保数据在写入过程中不会被其他事务修改。",
      "共享锁与共享锁之间兼容，因此多个事务可以同时对同一数据加共享锁，但共享锁与排他锁之间不兼容，不能同时存在。",
      "排他锁与任何锁都不兼容，因此当一个事务对数据加排他锁后，其他事务无法对该数据加任何类型的锁，包括共享锁。",
      "在数据库中，共享锁和排他锁的兼容性决定了事务能否同时访问同一数据，从而实现事务的隔离性。",
      "共享锁主要用于读操作，确保数据在读取时不会被修改；排他锁主要用于写操作，确保数据在修改时不会被其他事务干扰。",
      "在实际应用中，共享锁和排他锁的使用需要根据事务的类型和需求进行选择，以平衡并发性和数据一致性。"
    ],
    "keywords": [
      "共享锁",
      "排他锁",
      "锁兼容",
      "锁不兼容",
      "MVCC"
    ],
    "scene": [
      "在电商系统中，共享锁用于读取商品库存信息，多个用户可以同时查看库存，但不能同时修改。",
      "在银行系统中，排他锁用于处理转账操作，确保同一笔资金不会被多个事务同时修改。",
      "在日志系统中，共享锁用于读取日志数据，多个事务可以同时读取日志，但不能同时写入。"
    ],
    "interviewQ": [
      "共享锁和排他锁的区别是什么？（答：共享锁允许多事务同时读取，排他锁独占写入，锁类型之间存在兼容性差异。）",
      "为什么共享锁和排他锁之间不兼容？（答：共享锁和排他锁之间不兼容是为了防止数据在读取和写入过程中发生冲突，确保数据一致性。）",
      "在什么情况下会使用共享锁？（答：在需要多个事务同时读取数据但不修改数据的场景中，如商品库存查询，会使用共享锁。）"
    ],
    "related": [
      {
        "id": "java-mysqlq40",
        "kind": "compare",
        "note": "意向锁是锁机制的一部分，与锁类型相关"
      },
      {
        "id": "myisam-innodb",
        "kind": "prereq",
        "note": "了解存储引擎差异才能理解锁机制的适用场景"
      },
      {
        "id": "java-mysqlq36",
        "kind": "compare",
        "note": "表级锁和行级锁是锁机制的具体表现，与锁类型相关"
      },
      {
        "id": "java-mysql-tx-isolation",
        "kind": "compare",
        "note": "共享锁和排他锁是事务隔离级别实现的基础，两者有直接关联"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "共享锁(S锁)",
          "lines": [
            "允许多事务同时读取",
            "锁兼容，不阻塞读",
            "用于读操作，确保数据一致性",
            "不阻止其他S锁"
          ]
        },
        {
          "title": "排他锁(X锁)",
          "lines": [
            "独占写入，阻塞所有锁",
            "锁不兼容，阻止任何锁",
            "用于写操作，确保数据隔离",
            "阻止其他S锁和X锁"
          ]
        }
      ],
      "frames": [
        {
          "note": "共享锁适用于读操作，允许多事务并发读取，但不能同时写入。",
          "active": [
            0
          ]
        },
        {
          "note": "排他锁适用于写操作，确保数据在修改时不会被其他事务干扰。",
          "active": [
            1
          ]
        },
        {
          "note": "共享锁与排他锁不兼容，不能同时存在，确保事务隔离性。",
          "active": [
            0,
            1
          ]
        }
      ]
    }
  },
  {
    "id": "java-mysqlq40",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "MySQL"
    ],
    "tags": [
      "面试",
      "MySQL"
    ],
    "title": "意向锁有什么作用？",
    "oneLine": "意向锁用于快速判断表是否可加表锁，避免逐行遍历，提升性能。",
    "analogy": "就像在图书馆里，如果想借整本书，先看有没有人正在借整本书，这样就不会浪费时间找每本书。",
    "why": "当需要对表加锁时，如果逐行检查是否被锁，效率低下。意向锁允许在表级别快速判断是否有行锁存在，从而避免不必要的遍历，提高锁管理效率。同时，意向锁与行锁互斥，确保数据一致性。",
    "mechanism": [
      "意向锁是表级锁，用于表示事务有意向对表中的某些行加锁，从而避免对整个表进行逐行检查。",
      "当事务需要对某行加共享锁（S锁）或排他锁（X锁）时，InnoDB会先获取该行所在表的对应意向锁（IS锁或IX锁）。",
      "意向锁之间是兼容的，这意味着多个事务可以同时对同一表加IS锁或IX锁，不会互相阻塞。",
      "意向锁与行锁互斥，当表级锁（如IS锁或IX锁）存在时，行级锁（如S锁或X锁）无法加锁，反之亦然。",
      "意向锁不会与行级的共享锁或排他锁互斥，但表级的共享锁和排他锁会与意向锁互斥。",
      "意向锁由数据引擎维护，用户无法手动操作，确保锁管理的自动化和一致性。",
      "通过意向锁，可以快速判断是否可以对表加锁，避免逐行检查，提升数据库性能。"
    ],
    "keywords": [
      "意向锁",
      "IS锁",
      "IX锁",
      "共享锁",
      "排他锁"
    ],
    "scene": [
      "在高并发的订单处理系统中，当需要对整个订单表加锁时，意向锁可以快速判断是否有行锁存在。",
      "在数据迁移过程中，意向锁帮助快速判断是否可以对整个表进行锁定，避免数据不一致。",
      "在事务处理中，当需要对某一行加锁时，意向锁确保表级锁的兼容性，避免锁冲突。"
    ],
    "interviewQ": [
      "意向锁和行锁之间有什么关系？（答：意向锁与行锁互斥，但不会与行级的共享锁或排他锁互斥。）",
      "为什么需要使用意向锁？（答：意向锁可以快速判断是否可以对表加锁，避免逐行检查，提升性能。）",
      "意向锁和表级锁有什么区别？（答：意向锁是表级锁，用于表示事务有意向对表中的某些行加锁，而表级锁是直接对表加锁。）"
    ],
    "related": [
      {
        "id": "java-mysqlq39",
        "kind": "compare",
        "note": "共享锁和排他锁是锁机制的具体表现，与意向锁相关"
      },
      {
        "id": "myisam-innodb",
        "kind": "prereq",
        "note": "了解存储引擎差异才能理解意向锁的适用场景"
      },
      {
        "id": "java-mysqlq36",
        "kind": "compare",
        "note": "表级锁和行级锁是锁机制的具体表现，与意向锁相关"
      },
      {
        "id": "java-mysqlq42",
        "kind": "compare",
        "note": "意向锁是InnoDB中用于协调锁冲突的机制，与自增锁有共通的锁管理逻辑"
      },
      {
        "id": "java-mysql-tx-isolation",
        "kind": "compare",
        "note": "意向锁是事务隔离级别实现的补充机制，两者共同保障事务隔离"
      }
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "start",
          "label": "开始事务",
          "x": 20,
          "y": 30
        },
        {
          "id": "lock_row",
          "label": "加行锁",
          "x": 70,
          "y": 30
        },
        {
          "id": "intent_lock",
          "label": "加意向锁",
          "x": 20,
          "y": 70
        },
        {
          "id": "check_lock",
          "label": "检查表锁",
          "x": 70,
          "y": 70
        },
        {
          "id": "end",
          "label": "事务结束",
          "x": 50,
          "y": 100
        }
      ],
      "edges": [
        {
          "from": "start",
          "to": "lock_row"
        },
        {
          "from": "lock_row",
          "to": "intent_lock"
        },
        {
          "from": "intent_lock",
          "to": "check_lock"
        },
        {
          "from": "check_lock",
          "to": "end"
        }
      ],
      "frames": [
        {
          "n": "start",
          "note": "事务开始，准备对某行加锁"
        },
        {
          "n": "lock_row",
          "note": "尝试对某行加行锁（S/X）"
        },
        {
          "n": "intent_lock",
          "note": "InnoDB自动加表级意向锁（IS/IX）"
        },
        {
          "n": "check_lock",
          "note": "通过意向锁快速判断是否可加表锁，避免逐行检查"
        },
        {
          "n": "end",
          "note": "事务结束，锁资源释放"
        }
      ]
    }
  },
  {
    "id": "java-mysqlq42",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "MySQL"
    ],
    "tags": [
      "面试",
      "MySQL"
    ],
    "title": "自增锁有了解吗？",
    "oneLine": "自增锁是InnoDB中用于控制自增列插入的表级锁，用于保证自增列的连续性。",
    "analogy": "就像在超市排队结账，自增锁确保每个人按顺序排队，不会有人插队导致混乱。",
    "why": "自增锁的存在是为了保证自增列的值不会出现重复或跳跃，尤其是在多线程环境下。如果没有自增锁，多个事务同时插入数据可能会导致自增列的值不连续，甚至出现重复。传统的自增锁模式会阻塞其他事务，而交错模式则通过轻量级互斥锁实现更高的并发性。",
    "mechanism": [
      "自增锁是InnoDB中用于控制自增列插入的表级锁，用于保证自增列的连续性。",
      "在传统模式下，自增锁会阻塞其他事务对自增列的插入操作，确保自增列的值不会出现重复。",
      "在连续模式下，自增锁仍然使用表级锁，但会尽量保证自增列的值连续，适用于MySQL 8.0之前。",
      "在交错模式下，自增锁不再使用表级锁，而是使用轻量级互斥锁，允许多个插入操作并发执行，提高性能。",
      "交错模式适用于大多数场景，但需要注意主从同步时Binlog格式为Statement的情况，否则可能导致数据不一致性。",
      "自增锁的配置项为innodb_autoinc_lock_mode，可以设置为0（传统模式）、1（连续模式）或2（交错模式）。",
      "自增锁的使用会影响数据库的并发性能，需要根据实际场景选择合适的模式。"
    ],
    "keywords": [
      "自增锁",
      "AUTO-INC Locks",
      "innodb_autoinc_lock_mode",
      "连续模式",
      "交错模式"
    ],
    "scene": [
      "在高并发的插入场景下，交错模式可以提升性能，但需要确保主从同步的Binlog格式不是Statement。",
      "在需要保证自增列连续性的场景下，传统模式或连续模式更合适，但会牺牲并发性能。",
      "在主从同步且Binlog格式为Statement的场景下，不应使用交错模式，否则可能导致数据不一致性。"
    ],
    "interviewQ": [
      "为什么在主从同步且Binlog格式为Statement时不能使用交错模式？（答：交错模式下插入语句可以并发执行，导致执行顺序无法保证，从而引发主从数据不一致。）",
      "自增锁的三种模式分别是什么？（答：传统模式、连续模式、交错模式。）",
      "自增锁的作用是什么？（答：自增锁用于保证自增列的连续性，防止多个事务同时插入导致值重复或跳跃。）"
    ],
    "related": [
      {
        "id": "java-mysqlq36",
        "kind": "compare",
        "note": "了解表级锁和行级锁的区别，有助于理解自增锁作为表级锁的特性"
      },
      {
        "id": "java-mysqlq40",
        "kind": "compare",
        "note": "意向锁是InnoDB中用于协调锁冲突的机制，与自增锁有共通的锁管理逻辑"
      },
      {
        "id": "myisam-innodb",
        "kind": "prereq",
        "note": "了解InnoDB和MyISAM的区别，能更好理解自增锁是InnoDB特有的机制"
      },
      {
        "id": "java-mysql-mvcc",
        "kind": "compare",
        "note": "MVCC是InnoDB的并发控制机制，与自增锁同属InnoDB的锁管理范畴"
      }
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "传统模式",
          "label": "传统模式",
          "x": 20,
          "y": 30
        },
        {
          "id": "连续模式",
          "label": "连续模式",
          "x": 70,
          "y": 30
        },
        {
          "id": "交错模式",
          "label": "交错模式",
          "x": 50,
          "y": 70
        }
      ],
      "edges": [
        {
          "from": "传统模式",
          "to": "连续模式"
        },
        {
          "from": "传统模式",
          "to": "交错模式"
        },
        {
          "from": "连续模式",
          "to": "交错模式"
        }
      ],
      "frames": [
        {
          "n": "传统模式",
          "note": "阻塞其他插入，确保自增连续，但并发性能差"
        },
        {
          "n": "连续模式",
          "note": "尽量保证连续，但使用表级锁，适用于MySQL 8.0之前"
        },
        {
          "n": "交错模式",
          "note": "使用轻量锁，允许多并发，但主从同步时需避免Statement格式"
        }
      ]
    }
  },
  {
    "id": "java-mysql-sql-executed",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "MySQL"
    ],
    "tags": [
      "面试",
      "MySQL"
    ],
    "title": "SQL语句在MySQL中的执行过程是怎样的？",
    "oneLine": "SQL语句在MySQL中经过连接器、分析器、优化器、执行器等组件处理，最终调用存储引擎完成数据操作。",
    "analogy": "就像快递员送快递，先到快递站登记信息，再分拣包裹，规划最优路线，最后派送到用户手中。",
    "why": "在数据库中，SQL语句需要经过一系列处理才能高效执行。早期的查询缓存虽然能提升性能，但频繁更新会导致缓存失效，反而影响效率。因此，MySQL 8.0后移除了查询缓存。分析器和优化器能确保SQL语法正确且执行方案最优，执行器则负责调用存储引擎完成实际操作，确保数据安全和一致性。",
    "mechanism": [
      "连接器负责用户身份认证和权限检查，确保用户有权限访问数据库，连接建立后会缓存用户的权限信息，后续操作无需重复验证。",
      "查询缓存（MySQL 8.0前）用于缓存SELECT语句和结果集，通过Key-Value形式存储，查询时先检查缓存，命中则直接返回，未命中则继续后续处理。",
      "分析器对SQL进行词法和语法分析，提取查询的表、字段、条件等信息，判断SQL是否合法，为后续执行做准备。",
      "优化器根据MySQL的优化算法选择最优的执行方案，如索引选择、表关联顺序等，确保查询效率最大化。",
      "执行器负责执行SQL语句，先进行权限校验，确保用户有操作权限，然后调用存储引擎接口，完成数据读写操作。",
      "对于更新语句，执行器会先进行数据查询，再调用存储引擎写入数据，同时记录binlog和redolog日志，确保数据一致性。",
      "InnoDB引擎使用redolog（重做日志）和binlog（归档日志）实现事务的持久化和数据一致性，通过两阶段提交机制防止数据丢失。",
      "redolog在prepare状态后，binlog写入完成后，redolog才会提交为commit状态，确保事务的原子性和一致性。"
    ],
    "keywords": [
      "MySQL执行流程",
      "SQL执行过程",
      "连接器",
      "解析器",
      "优化器",
      "执行器",
      "Server层",
      "存储引擎"
    ],
    "scene": [
      "在电商系统中，用户查询商品信息时，SQL语句经过连接器、分析器、优化器处理后，调用InnoDB引擎返回结果。",
      "在银行系统中，更新账户余额的SQL语句需要经过权限校验、日志记录和事务提交，确保数据一致性。",
      "在日志分析系统中，频繁的SELECT查询可能因查询缓存失效导致性能下降，因此需避免使用查询缓存。"
    ],
    "interviewQ": [
      "为什么MySQL 8.0之后移除了查询缓存？（答：查询缓存在频繁更新时会导致大量缓存失效，影响性能，因此MySQL 8.0移除了该功能。）",
      "优化器在执行SQL时如何选择最优的执行方案？（答：优化器根据MySQL的优化算法，如索引选择、表关联顺序等，选择执行效率最高的方案。）",
      "InnoDB引擎如何保证事务的原子性和一致性？（答：InnoDB通过redolog和binlog的两阶段提交机制，确保事务在异常重启后仍能保持一致性。）"
    ],
    "related": [
      {
        "id": "java-mysql-explain",
        "kind": "prereq",
        "note": "了解执行计划分析方法，能更深入理解SQL执行过程中的优化策略"
      },
      {
        "id": "java-mysqlq14",
        "kind": "prereq",
        "note": "了解存储引擎是理解SQL执行过程的基础，因为执行器依赖存储引擎实现"
      },
      {
        "id": "java-mysqlq36",
        "kind": "compare",
        "note": "表级锁和行级锁是执行过程中涉及的锁机制，与执行流程有直接关联"
      },
      {
        "id": "java-mysql-index-invalid",
        "kind": "extends",
        "note": "索引失效场景是执行过程中的常见问题，能帮助理解执行器如何处理索引"
      },
      {
        "id": "java-mysql-logs",
        "kind": "extends",
        "note": "SQL执行过程涉及日志机制，是理解日志作用的前提"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "连接器",
        "分析器",
        "优化器",
        "执行器"
      ],
      "frames": [
        {
          "s": 0,
          "note": "连接器验证用户权限，缓存权限信息，建立连接"
        },
        {
          "s": 1,
          "note": "分析器检查SQL合法性，提取表、字段、条件等元数据"
        },
        {
          "s": 2,
          "note": "优化器选择索引和执行顺序，确保查询效率最大化"
        },
        {
          "s": 3,
          "note": "执行器校验权限后调用存储引擎，记录binlog和redolog日志"
        }
      ]
    }
  },
  {
    "id": "java-mysql-mvcc",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "MySQL"
    ],
    "tags": [
      "面试",
      "MySQL"
    ],
    "title": "InnoDB如何实现MVCC？",
    "oneLine": "InnoDB通过隐藏列、ReadView和undo log实现MVCC，支持快照读和当前读，确保事务隔离。",
    "analogy": "就像图书馆借书，每个人看到的书是自己借的版本，其他人修改的书不会影响你当前的阅读。",
    "why": "在高并发场景下，直接读写会导致阻塞和脏读。MVCC通过维护数据版本，让读操作不阻塞写操作，写操作也不影响读操作。InnoDB通过隐藏列和undo log记录版本变化，结合ReadView判断可见性，实现事务隔离，提升并发性能。",
    "mechanism": [
      "MVCC是多版本并发控制，通过维护数据行的多个版本实现事务隔离，InnoDB使用隐藏列和undo log记录版本变化。",
      "InnoDB为每行数据添加三个隐藏字段：DB_TRX_ID记录最后一次修改事务ID，DB_ROLL_PTR指向undo log，DB_ROW_ID用于聚簇索引。",
      "ReadView用于判断数据可见性，保存当前活跃事务ID列表，当事务读取数据时，通过比较DB_TRX_ID与ReadView中的值决定是否可见。",
      "undo log分为insert和update两种，insert undo log在事务提交后可直接删除，update undo log需等待purge线程清理，用于支持MVCC。",
      "事务执行select时生成ReadView，快照中保存活跃事务ID列表，确保事务只看到创建快照前已提交的数据。",
      "在RR隔离级别下，ReadView在事务开始时生成，后续查询复用同一快照，避免不可重复读；在RC级别下，每次查询生成新快照，可能导致不可重复读。",
      "版本回收机制定期清理不再需要的旧版本数据，防止空间浪费，通过purge线程执行。",
      "快照读使用旧版本数据，当前读获取最新版本，锁定读会加锁，防止其他事务修改，确保数据一致性。"
    ],
    "keywords": [
      "MVCC",
      "多版本并发控制",
      "InnoDB",
      "快照读",
      "当前读",
      "ReadView",
      "undo log",
      "隐藏列"
    ],
    "scene": [
      "电商系统下单时，多个用户同时查看商品库存，通过MVCC避免读写冲突。",
      "银行转账系统中，多个事务同时查询账户余额，MVCC确保读取一致性。",
      "日志分析系统中，不同时间点的数据快照读取，MVCC支持历史数据查询。"
    ],
    "interviewQ": [
      "InnoDB如何判断数据版本是否可见？（答：通过ReadView中的m_low_limit_id、m_up_limit_id和m_ids比较DB_TRX_ID，判断是否在当前事务可见范围内。）",
      "MVCC中undo log的作用是什么？（答：用于事务回滚和MVCC，当数据版本不可见时，通过undo log读取旧版本数据。）",
      "InnoDB中隐藏列DB_TRX_ID和DB_ROLL_PTR的作用是什么？（答：DB_TRX_ID记录最后一次修改事务ID，DB_ROLL_PTR指向undo log，用于版本链回溯。）"
    ],
    "related": [
      {
        "id": "myisam-innodb",
        "kind": "prereq",
        "note": "了解InnoDB和MyISAM的区别，能更好理解MVCC是InnoDB特有的机制"
      },
      {
        "id": "java-mysqlq36",
        "kind": "compare",
        "note": "表级锁和行级锁是锁机制的基础，与MVCC的锁管理有共通点"
      },
      {
        "id": "java-mysqlq42",
        "kind": "compare",
        "note": "自增锁是InnoDB的锁机制，与MVCC同属InnoDB的并发控制范畴"
      },
      {
        "id": "java-mysql-tx-isolation",
        "kind": "compare",
        "note": "事务隔离级别是MVCC实现的背景，两者共同保障事务的隔离性"
      },
      {
        "id": "java-mysql-logs",
        "kind": "extends",
        "note": "MVCC依赖日志机制实现版本控制，是理解MVCC的前提"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "记录事务ID",
        "生成ReadView",
        "判断数据可见性"
      ],
      "frames": [
        {
          "s": 0,
          "note": "DB_TRX_ID记录事务ID，用于标识行的最后修改者，确保版本追踪"
        },
        {
          "s": 1,
          "note": "ReadView保存当前活跃事务ID列表，用于后续数据可见性判断"
        },
        {
          "s": 2,
          "note": "通过比较DB_TRX_ID与ReadView中的事务ID，决定当前事务是否可见该行数据"
        }
      ]
    }
  },
  {
    "id": "java-mysql-tx-isolation",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "MySQL"
    ],
    "tags": [
      "面试",
      "MySQL"
    ],
    "title": "事务隔离级别是什么？",
    "oneLine": "事务隔离级别是MySQL中控制事务并发访问数据的机制，用于防止脏读、不可重复读和幻读问题。",
    "analogy": "就像在图书馆借书，不同隔离级别决定了你是否能看到别人正在阅读的书，是否能借到同一本书，以及是否能发现别人新加入的书。",
    "why": "在并发环境中，多个事务同时操作同一数据可能导致数据不一致。例如，脏读是读取未提交的数据，不可重复读是同一事务中多次读取结果不一致，幻读是读取到其他事务新增的数据。隔离级别通过限制事务的可见性，确保数据一致性，但会牺牲一定的并发性能。",
    "mechanism": [
      "READ-UNCOMMITTED 是最低隔离级别，允许读取未提交的数据变更，可能导致脏读、不可重复读和幻读，适用于对数据一致性要求极低的场景。",
      "READ-COMMITTED 允许读取已提交的数据，防止脏读，但幻读和不可重复读仍可能发生，适用于大多数数据库的默认设置。",
      "REPEATABLE-READ 是MySQL InnoDB的默认级别，通过MVCC和Next-Key Locks机制，防止脏读和不可重复读，但标准定义下仍可能发生幻读。",
      "SERIALIZABLE 是最高隔离级别，所有事务按顺序执行，完全避免脏读、不可重复读和幻读，但并发性能最差，适用于严格一致性要求的分布式事务。",
      "MVCC（多版本并发控制）通过为事务创建快照，确保快照读不会看到其他事务的修改，从而避免幻读。",
      "Next-Key Locks 是行锁和间隙锁的组合，用于防止其他事务在当前读操作期间插入新数据，从而解决幻读问题。",
      "快照读（Snapshot Read）是普通的SELECT语句，读取事务启动时的数据快照，而当前读（Current Read）如SELECT ... FOR UPDATE会锁定数据，防止幻读。",
      "在写密集型场景中，REPEATABLE-READ的间隙锁机制可能导致更多的锁等待，而READ-COMMITTED的性能通常更优。"
    ],
    "keywords": [
      "事务隔离级别",
      "脏读",
      "不可重复读",
      "幻读",
      "MVCC",
      "Next-Key Locks"
    ],
    "scene": [
      "电商系统中，订单状态更新时需要避免其他事务的干扰，防止脏读和不可重复读。",
      "银行转账系统中，高并发下需要严格一致性，可能使用SERIALIZABLE隔离级别。",
      "日志分析系统中，读多写少，使用REPEATABLE-READ以平衡性能和一致性。"
    ],
    "interviewQ": [
      "为什么InnoDB在REPEATABLE-READ级别下能解决幻读？（答：通过MVCC和Next-Key Locks机制，快照读避免看到其他事务的修改，当前读锁定间隙防止插入新数据。）",
      "如何在MySQL中设置事务隔离级别？（答：使用SET [SESSION|GLOBAL] TRANSACTION ISOLATION LEVEL命令，如SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ。）",
      "什么是快照读和当前读？（答：快照读是普通的SELECT，读取事务启动时的数据快照；当前读如SELECT ... FOR UPDATE，锁定数据防止幻读。）"
    ],
    "related": [
      {
        "id": "myisam-innodb",
        "kind": "prereq",
        "note": "了解InnoDB和MyISAM的区别，能更好理解事务隔离级别是InnoDB的特性"
      },
      {
        "id": "java-mysqlq39",
        "kind": "compare",
        "note": "共享锁和排他锁是事务隔离级别实现的基础，两者有直接关联"
      },
      {
        "id": "java-mysqlq40",
        "kind": "compare",
        "note": "意向锁是事务隔离级别实现的补充机制，两者共同保障事务隔离"
      },
      {
        "id": "java-mysql-mvcc",
        "kind": "compare",
        "note": "MVCC是事务隔离级别实现的底层机制，两者共同保障事务的隔离性"
      }
    ],
    "diagram": null
  },
  {
    "id": "java-mysql-index-bplus",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "MySQL"
    ],
    "tags": [
      "面试",
      "MySQL"
    ],
    "title": "可以命中索引",
    "oneLine": "索引是用于快速查询的数据结构，能大幅减少扫描数据量，直接定位记录。",
    "analogy": "就像字典的目录，不用翻整本书，直接找到对应页码，节省时间。",
    "why": "索引能显著提升查询效率，但并非所有情况都适用。当数据量小、查询结果集占比大或索引维护不当，全表扫描可能更快。此外，索引会增加存储和维护成本，设计不当可能导致优化器误选索引，反而降低性能。索引的使用需要权衡，既要考虑查询效率，也要考虑更新和存储成本。",
    "mechanism": [
      "索引是一种排序好的数据结构，例如B+树，能快速定位数据，减少扫描量。B+树的非叶子节点存储索引，叶子节点存储数据或主键，使得查询过程高效。",
      "查询时，数据库先通过索引找到符合条件的记录位置，再直接读取数据，避免全表扫描。这种方式减少了磁盘I/O次数，显著提升了查询速度。",
      "聚簇索引的叶子节点存储数据，查询时直接获取，无需回表，效率高。这种结构使得主键查询和范围查询都非常高效。",
      "非聚簇索引的叶子节点存储主键值，查询需先通过索引找到主键，再回表获取数据。这种设计虽然增加了查询步骤，但减少了数据存储空间。",
      "覆盖索引的索引包含所有查询字段，避免回表，提升查询速度。这种索引设计能够减少磁盘I/O，提高查询效率。",
      "联合索引遵循最左前缀原则，查询条件需从左到右匹配，否则索引失效。这种设计确保了联合索引的有效性，避免了不必要的全表扫描。",
      "索引失效可能因查询条件不匹配、使用函数、类型转换、范围查询等导致。这些情况使得数据库无法有效利用索引，导致性能下降。",
      "优化器根据统计信息选择最优查询路径，但统计信息过时可能导致错误决策。这种情况下，即使有索引，也可能选择全表扫描。"
    ],
    "keywords": [
      "MySQL索引",
      "B+树索引",
      "聚簇索引",
      "覆盖索引",
      "联合索引",
      "索引失效",
      "最左前缀原则"
    ],
    "scene": [
      "在大型电商系统中，商品搜索使用覆盖索引，避免回表，提升响应速度。",
      "在用户登录系统中，使用唯一索引确保用户名唯一，提高查询效率。",
      "在日志分析系统中，联合索引用于快速定位特定时间段的记录，提升查询性能。"
    ],
    "interviewQ": [
      "追问1：为什么联合索引要遵循最左前缀原则？（答：联合索引的存储结构是按照从左到右的顺序排列的，如果查询条件不满足最左前缀原则，索引无法有效使用，导致全表扫描。）",
      "追问2：索引失效有哪些常见原因？（答：索引失效可能因为查询条件不匹配、使用函数、类型转换、范围查询等，这些情况使得数据库无法有效利用索引，导致性能下降。）",
      "追问3：如何避免索引失效？（答：避免使用函数、类型转换、范围查询等，确保查询条件与索引列匹配，同时合理设计索引结构，提高查询效率。）",
      "追问4：为什么聚簇索引的查询效率更高？（答：聚簇索引的叶子节点存储数据，查询时直接获取，无需回表，减少了磁盘I/O次数，显著提升了查询速度。）"
    ],
    "related": [
      {
        "id": "java-mysql-index-invalid",
        "kind": "prereq",
        "note": "了解索引失效场景，能更好理解索引命中时的查询优化效果"
      },
      {
        "id": "java-mysqlq36",
        "kind": "compare",
        "note": "表级锁和行级锁是索引查询时可能涉及的锁机制，有直接关联"
      },
      {
        "id": "myisam-innodb",
        "kind": "prereq",
        "note": "了解InnoDB和MyISAM的区别，能更好理解索引是InnoDB的特性"
      },
      {
        "id": "java-mysql-explain",
        "kind": "compare",
        "note": "执行计划分析能帮助理解索引命中时的查询优化路径"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "覆盖索引",
          "lines": [
            "索引包含所有查询字段",
            "避免回表操作",
            "减少磁盘I/O",
            "提升查询效率"
          ]
        },
        {
          "title": "聚簇索引",
          "lines": [
            "叶子节点存储数据",
            "直接获取记录",
            "主键查询高效",
            "范围查询高效"
          ]
        },
        {
          "title": "非聚簇索引",
          "lines": [
            "叶子节点存储主键",
            "需回表获取数据",
            "存储空间较小",
            "查询步骤增加"
          ]
        }
      ],
      "frames": [
        {
          "note": "覆盖索引适用于查询字段全在索引中的场景，可直接返回结果，减少磁盘I/O。",
          "active": [
            0
          ]
        },
        {
          "note": "聚簇索引通过主键直接定位数据，适合高频主键查询和范围查询，但更新成本较高。",
          "active": [
            1
          ]
        },
        {
          "note": "非聚簇索引通过主键回表获取数据，虽然存储空间小，但增加了查询步骤，适合数据量大的场景。",
          "active": [
            2
          ]
        }
      ]
    }
  },
  {
    "id": "java-mysql-index-invalid",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "MySQL"
    ],
    "tags": [
      "面试",
      "MySQL"
    ],
    "title": "MySQL索引失效场景有哪些？",
    "oneLine": "MySQL索引失效是指即使建立了索引，查询时也无法使用索引导致性能下降，常见原因包括SQL写法不当、索引设计问题等。",
    "analogy": "就像在图书馆找书，如果书架上的书不是按类别排列，而是随意摆放，你只能一本一本地翻，效率低下。",
    "why": "索引的核心是利用B+Tree的有序性快速定位数据，但当查询条件破坏了这种有序性，比如对索引列进行计算、使用通配符模糊查询、违背最左前缀原则等，MySQL无法利用索引进行二分查找，只能全表扫描。这会导致查询性能急剧下降，尤其在数据量大时影响严重。",
    "mechanism": [
      "SELECT * 查询不会直接导致索引失效，但如果查询需要的字段不在索引中，MySQL需要回表获取数据。优化器会比较索引扫描加回表与全表扫描的成本，如果查询结果占总数据量比例较高（通常在20%~30%），优化器会放弃索引，选择全表扫描。",
      "违背最左前缀原则时，联合索引的字段顺序决定了匹配顺序。如果查询条件跳过了最左列，或在中间列使用范围查询（如>、BETWEEN），索引无法继续匹配后续字段，只能降级为范围扫描加过滤，导致索引失效。",
      "在索引列上进行计算、函数或类型转换会破坏B+Tree的有序性。索引存储的是原始值，经过函数处理后变为无序，MySQL无法利用二分查找快速定位，只能全表扫描。",
      "LIKE模糊查询以通配符开头（如'%abc'）会破坏B+Tree的有序性。由于索引是按字符从左到右排序的，前缀通配符导致无法确定搜索区间的起始点，无法利用索引。",
      "OR连接的多个条件中，只要任意一列没有索引，MySQL会放弃所有索引，执行全表扫描。如果两侧都有索引，MySQL可能触发索引合并（Index Merge），但合并成本可能高于全表扫描，导致索引失效。",
      "IN/NOT IN使用不当时，当列表长度超过eq_range_index_dive_limit（默认200），优化器会切换到基于统计信息的估算，可能导致误判索引成本，从而放弃索引。NOT IN常量列表通常会导致全表扫描。",
      "隐式类型转换发生在索引列上时，如字符串列与数字值比较，MySQL会将字符串转换为浮点数，破坏B+Tree的有序性，导致索引失效。只有当转换发生在常量侧，索引仍可能有效。",
      "ORDER BY排序优化陷阱中，如果排序字段不在索引中，或索引顺序与ORDER BY不一致，MySQL会触发Using filesort，导致排序成本高。如果排序字段包含非索引列，还需回表排序，进一步影响性能。"
    ],
    "keywords": [
      "MySQL索引失效",
      "最左前缀原则",
      "覆盖索引",
      "索引下推",
      "隐式类型转换",
      "SQL优化"
    ],
    "scene": [
      "在电商系统中，用户搜索商品时，如果使用LIKE '%abc'模糊查询，可能导致全表扫描，影响搜索性能。",
      "在订单系统中，使用OR连接两个条件，如WHERE user_id = 1 OR order_date > '2023-01-01'，如果其中一列没有索引，可能导致索引失效。",
      "在日志分析系统中，对时间字段进行计算（如DATE(create_time) = '2022-01-01'）会导致索引失效，只能全表扫描。"
    ],
    "interviewQ": [
      "为什么SELECT * 查询不会直接导致索引失效？（答：SELECT * 不直接导致索引失效，但如果查询字段不在索引中，需要回表，优化器会根据数据量比例决定是否使用索引。）",
      "违背最左前缀原则会导致索引失效吗？（答：是的，联合索引的字段顺序决定了匹配顺序，跳过最左列或使用范围查询会导致后续列无法匹配，索引失效。）",
      "隐式类型转换如何导致索引失效？（答：隐式类型转换发生在索引列上时，如字符串列与数字值比较，MySQL会将字符串转换为浮点数，破坏B+Tree的有序性，导致索引失效。）"
    ],
    "related": [
      {
        "id": "java-mysql-explain",
        "kind": "prereq",
        "note": "了解执行计划能更准确判断索引是否被使用"
      },
      {
        "id": "java-mysql-perf-spec",
        "kind": "prereq",
        "note": "索引设计规范能避免索引失效，是优化的前置知识"
      },
      {
        "id": "java-mysql-sql-executed",
        "kind": "prereq",
        "note": "了解SQL执行流程能更好理解索引失效的底层原因"
      },
      {
        "id": "java-mysql-index-bplus",
        "kind": "extends",
        "note": "了解索引失效场景，能更好理解索引命中时的查询优化效果"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "失效场景",
          "lines": [
            "查询字段不在索引中，需回表",
            "违背最左前缀原则，跳过最左列",
            "索引列进行计算/函数/类型转换"
          ]
        },
        {
          "title": "对比方案",
          "lines": [
            "使用覆盖索引避免回表",
            "遵循最左前缀原则设计联合索引",
            "避免在索引列使用函数或类型转换"
          ]
        }
      ],
      "frames": [
        {
          "note": "失效场景中，查询字段不在索引中会导致回表，需优化器比较索引扫描与全表扫描成本",
          "active": [
            0
          ]
        },
        {
          "note": "对比方案中，使用覆盖索引可避免回表，提升查询效率，但需确保索引字段覆盖查询需求",
          "active": [
            1
          ]
        },
        {
          "note": "失效场景中，索引列进行计算或类型转换会破坏B+Tree有序性，导致无法使用索引",
          "active": [
            0
          ]
        },
        {
          "note": "对比方案中，遵循最左前缀原则可确保联合索引有效，避免跳过最左列导致索引失效",
          "active": [
            1
          ]
        }
      ]
    }
  },
  {
    "id": "java-mysql-explain",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "MySQL"
    ],
    "tags": [
      "面试",
      "MySQL"
    ],
    "title": "如何分析 MySQL 的执行计划？",
    "oneLine": "MySQL 的执行计划用于分析 SQL 查询的执行方式，帮助优化性能。",
    "analogy": "就像快递员规划送货路线，执行计划告诉 MySQL 如何高效地从数据库中取出数据。",
    "why": "执行计划帮助我们了解 SQL 查询的执行过程，包括使用的索引、访问类型、行数估算等。通过分析执行计划，可以发现查询中的性能瓶颈，如全表扫描、缺少索引或不必要的排序操作。传统方法如手动优化难以发现这些问题，而执行计划提供了一种系统化的方法，使我们能够针对性地进行优化。",
    "mechanism": [
      "执行计划是 MySQL 查询优化器对 SQL 语句进行分析后生成的执行方案，用于指导数据库如何高效地获取数据。",
      "通过 EXPLAIN 命令，可以获取执行计划的详细信息，包括查询顺序、访问类型、使用的索引等，帮助我们理解查询的执行流程。",
      "EXPLAIN 的结果包含多个字段，如 id、select_type、type、key 等，每个字段代表不同的含义，如 id 表示查询的执行顺序，type 表示访问类型。",
      "type 字段表示 MySQL 访问表的方式，如 system、const、eq_ref、ref、range、index、ALL 等，其中 ALL 表示全表扫描，性能较差。",
      "key 字段表示实际使用的索引，若未使用索引，可能需要优化查询或添加索引。",
      "rows 字段表示预计要读取的行数，数值越大，查询性能越差，需优化。",
      "Extra 字段包含附加信息，如 Using index 表示使用了覆盖索引，Using temporary 表示使用了临时表，可能需要优化查询。",
      "EXPLAIN ANALYZE 可以真正执行查询，并输出实际耗时和行数，比标准 EXPLAIN 更可靠，适合深度排查慢查询。"
    ],
    "keywords": [
      "MySQL执行计划",
      "EXPLAIN",
      "查询优化器",
      "SQL性能分析",
      "索引命中",
      "type访问类型",
      "Extra字段"
    ],
    "scene": [
      "在分析慢查询时，使用 EXPLAIN 查看执行计划，发现全表扫描问题。",
      "在多表 JOIN 场景中，通过执行计划判断是否使用了正确的索引和连接顺序。",
      "在优化子查询时，通过执行计划判断子查询是否被物化或优化。"
    ],
    "interviewQ": [
      "如何判断 SQL 是否使用了索引？（答：查看 key 字段是否为实际使用的索引，若为 NULL 表示未使用索引。）",
      "EXPLAIN 和 EXPLAIN ANALYZE 的区别是什么？（答：EXPLAIN 仅分析查询计划，EXPLAIN ANALYZE 真正执行查询并输出实际耗时和行数。）",
      "如何优化执行计划中的全表扫描？（答：添加合适的索引，避免不必要的条件或使用覆盖索引。）"
    ],
    "related": [
      {
        "id": "java-mysql-sql-executed",
        "kind": "prereq",
        "note": "了解SQL执行流程能更好理解执行计划的生成过程"
      },
      {
        "id": "java-mysql-perf-spec",
        "kind": "prereq",
        "note": "优化规范能指导执行计划的优化方向，是执行计划分析的前置"
      },
      {
        "id": "java-mysql-index-invalid",
        "kind": "prereq",
        "note": "分析执行计划能判断索引是否被使用，是理解失效场景的前提"
      },
      {
        "id": "java-mysql-index-bplus",
        "kind": "compare",
        "note": "执行计划分析能帮助理解索引命中时的查询优化路径"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "生成执行计划",
        "解析执行方案",
        "判断访问类型",
        "评估性能影响"
      ],
      "frames": [
        {
          "s": 0,
          "note": "使用 EXPLAIN 命令生成执行计划，查看查询顺序和访问类型，这是分析的第一步。"
        },
        {
          "s": 1,
          "note": "解析执行计划中的 type 字段，判断是否为全表扫描（ALL）或使用了索引（range、ref 等），这是性能的关键点。"
        },
        {
          "s": 2,
          "note": "检查 rows 字段的数值，数值越大表示需要扫描的行越多，可能需要优化索引或查询逻辑。"
        },
        {
          "s": 3,
          "note": "通过 Extra 字段判断是否使用了覆盖索引或临时表，这些是性能优化的重要线索。"
        }
      ]
    }
  },
  {
    "id": "java-mysql-logs",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "MySQL"
    ],
    "tags": [
      "面试",
      "MySQL"
    ],
    "title": "MySQL三大日志的作用与原理",
    "oneLine": "MySQL三大日志（binlog、redo log和undo log）用于保证数据一致性、崩溃恢复和主从复制。",
    "analogy": "就像快递员送包裹，binlog记录所有操作，redo log确保包裹安全送达，undo log则能回退错误操作。",
    "why": "MySQL需要日志来应对宕机、数据丢失和主从同步问题。redo log通过WAL机制实现崩溃恢复，binlog用于主从复制，undo log支持事务回滚和MVCC。这些机制共同保障数据一致性与持久性。",
    "mechanism": [
      "redo log是InnoDB存储引擎独有的日志，用于崩溃恢复。当MySQL实例宕机时，InnoDB通过重放redo log中的记录，将数据页恢复到最新状态。",
      "事务提交时，InnoDB会将redo log buffer中的内容刷盘。刷盘时机由innodb_flush_log_at_trx_commit参数控制，该参数有三种策略：0（性能高但数据丢失风险大）、1（最安全但性能最低）、2（性能和安全性平衡）。",
      "日志文件组采用环形数组形式，由write pos和checkpoint控制。write pos记录当前写入位置，checkpoint记录已清理的位置，二者之间的空间用于写入新日志。当write pos追上checkpoint时，日志文件组满，需清理日志以腾出空间。",
      "binlog用于主从复制和审计，记录所有对数据库的更改。在双一配置（innodb_flush_log_at_trx_commit=1和sync_binlog=1）下，binlog切换时会触发redo log刷盘，确保数据一致性。",
      "undo log用于事务回滚和MVCC。当事务执行时，InnoDB会生成undo log记录，用于回滚操作或供其他事务读取旧版本数据，保证事务的ACID特性。",
      "Checkpoint机制确保脏页刷盘，避免日志文件组满。当Checkpoint触发时，InnoDB会将脏页写入磁盘，并同步刷新redo log，缩短崩溃恢复时间。",
      "WAL（预写日志）原则要求数据页写入磁盘前，其对应的redo log必须先落盘。这确保了在崩溃恢复时，数据页和日志记录的同步性。"
    ],
    "keywords": [
      "MySQL日志",
      "binlog",
      "redo log",
      "undo log",
      "两阶段提交",
      "崩溃恢复",
      "主从复制",
      "WAL"
    ],
    "scene": [
      "数据库宕机后，通过redo log恢复数据，确保数据不丢失。",
      "主从复制中，binlog记录所有操作，用于同步从库数据。",
      "事务回滚时，undo log记录旧版本数据，支持事务的原子性。"
    ],
    "interviewQ": [
      "为什么redo log采用环形数组结构？（答：环形数组可循环利用日志空间，避免频繁创建和删除文件，提高性能。）",
      "innodb_flush_log_at_trx_commit参数的作用是什么？（答：控制redo log刷盘时机，影响数据安全性和性能，值为1时最安全。）",
      "什么是WAL原则？（答：Write-Ahead Logging要求数据页写入磁盘前，其对应的redo log必须先落盘，确保崩溃恢复时数据一致性。）",
      "undo log和redo log的区别是什么？（答：undo log用于事务回滚和MVCC，redo log用于崩溃恢复，两者共同保障事务的ACID特性。）"
    ],
    "related": [
      {
        "id": "java-mysql-mvcc",
        "kind": "prereq",
        "note": "MVCC依赖日志机制实现版本控制，是理解MVCC的前提"
      },
      {
        "id": "java-mysql-sql-executed",
        "kind": "prereq",
        "note": "SQL执行过程涉及日志机制，是理解日志作用的前提"
      }
    ],
    "diagram": {
      "kind": "arch",
      "nodes": [
        {
          "id": "binlog",
          "label": "binlog",
          "x": 20,
          "y": 30,
          "w": 20
        },
        {
          "id": "redo",
          "label": "redo log",
          "x": 50,
          "y": 30,
          "w": 22
        },
        {
          "id": "undo",
          "label": "undo log",
          "x": 80,
          "y": 30,
          "w": 20
        },
        {
          "id": "innodb",
          "label": "InnoDB",
          "x": 50,
          "y": 70,
          "w": 24
        }
      ],
      "links": [
        {
          "from": "binlog",
          "to": "innodb",
          "label": "主从复制"
        },
        {
          "from": "redo",
          "to": "innodb",
          "label": "崩溃恢复"
        },
        {
          "from": "undo",
          "to": "innodb",
          "label": "事务回滚"
        },
        {
          "from": "innodb",
          "to": "binlog",
          "label": "刷盘触发"
        }
      ],
      "frames": [
        {
          "n": "binlog",
          "note": "记录所有更改，用于主从复制和审计，双一配置下触发redo刷盘"
        },
        {
          "n": "redo",
          "note": "InnoDB独有，崩溃恢复时重放日志，刷盘由innodb_flush_log_at_trx_commit控制"
        },
        {
          "n": "undo",
          "note": "事务回滚和MVCC，记录旧版本数据，保证事务ACID"
        },
        {
          "n": "innodb",
          "note": "协调日志写入，通过WAL原则确保数据页和日志同步，触发Checkpoint机制"
        }
      ]
    }
  },
  {
    "id": "java-mysql-perf-spec",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "MySQL"
    ],
    "tags": [
      "面试",
      "MySQL"
    ],
    "title": "MySQL高性能优化规范建议总结",
    "oneLine": "MySQL优化规范涵盖命名、设计、字段、索引、SQL编写等，提升数据库性能和稳定性。",
    "analogy": "就像整理房间，每个物品都有固定位置，避免杂乱，提高查找效率。",
    "why": "MySQL性能优化是为了解决数据存储、查询、更新效率低的问题。随着数据量增长，未优化的数据库会导致查询变慢、资源浪费，甚至系统崩溃。通过规范设计、合理索引、避免冗余，可以提升查询速度、减少资源占用，确保系统稳定运行。",
    "mechanism": [
      "数据库命名规范要求使用小写字母和下划线，避免保留关键字，便于管理和维护，减少歧义。这种统一的命名方式有助于团队协作，避免因命名不规范导致的查询错误和维护困难。",
      "使用InnoDB存储引擎支持事务和行级锁，提升高并发场景下的性能和数据一致性。InnoDB通过日志机制和多版本并发控制（MVCC）确保数据的完整性和并发操作的高效性，避免了MyISAM引擎在高并发下的锁表问题。",
      "统一使用UTF8或UTF8MB4字符集，避免字符集转换导致的乱码和索引失效，确保数据存储和查询的准确性。使用UTF8MB4可以支持存储emoji等特殊字符，避免因字符集不一致导致的查询错误和性能下降。",
      "表和字段添加注释，有助于团队协作和文档维护，提高代码可读性和可维护性。注释可以明确字段的含义和使用场景，减少因理解错误导致的开发和维护成本。",
      "控制单表数据量在500万以内，避免备份、恢复和修改表结构时的性能问题，提升系统稳定性。过大的表会导致备份和恢复时间增加，修改表结构时需要锁定表，影响其他操作的执行效率。",
      "避免使用TEXT和BLOB类型存储大字段，减少磁盘I/O和内存临时表的使用，提升查询效率。TEXT和BLOB类型在排序和分组操作时无法使用内存临时表，必须使用磁盘临时表，导致查询性能下降。",
      "优先使用最小数据类型存储数据，减少存储空间和内存占用，提升查询和索引性能。使用更小的数据类型可以减少磁盘空间占用，提高内存访问速度，从而提升查询效率。",
      "合理设计索引，避免冗余和重复索引，减少查询优化器生成执行计划的时间，提升查询效率。过多的索引会增加插入和更新操作的开销，同时增加查询优化器生成执行计划的时间，影响查询性能。"
    ],
    "keywords": [
      "MySQL优化规范",
      "数据库设计规范",
      "索引设计",
      "SQL编写规范",
      "慢查询优化",
      "字段类型选择",
      "表结构设计"
    ],
    "scene": [
      "电商系统中，订单表数据量超过500万，导致备份和恢复时间变长，需分库分表处理。",
      "日志系统中，使用TEXT类型存储日志内容，导致查询时无法使用内存临时表，需分离到扩展表中。",
      "金融系统中，金额字段使用decimal类型，确保计算精度，避免浮点数精度丢失问题。"
    ],
    "interviewQ": [
      "追问1：为什么建议使用InnoDB存储引擎而不是MyISAM？（答：InnoDB支持事务和行级锁，适合高并发场景，而MyISAM在高并发下容易锁表，影响性能。）",
      "追问2：为什么避免使用TEXT和BLOB类型存储大字段？（答：TEXT和BLOB类型在排序和分组操作时无法使用内存临时表，必须使用磁盘临时表，导致查询性能下降。）",
      "追问3：如何选择联合索引的列顺序？（答：区分度最高的列放在最左侧，最频繁使用的列放在左侧，字段长度优先级最低，以减少存储空间和提升I/O性能。）",
      "追问4：覆盖索引的好处是什么？（答：覆盖索引可以避免回表操作，减少IO，提升查询效率，同时将随机IO转化为顺序IO，加快查询速度。）"
    ],
    "related": [
      {
        "id": "java-mysql-explain",
        "kind": "prereq",
        "note": "执行计划分析是优化规范落地的实践，是理解规范的前提"
      },
      {
        "id": "java-mysql-index-invalid",
        "kind": "prereq",
        "note": "索引失效场景是优化规范的重要内容，是理解规范的前提"
      },
      {
        "id": "java-mysql-sql-executed",
        "kind": "prereq",
        "note": "SQL执行过程是优化规范的核心内容，是理解规范的前提"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "规范设计",
          "lines": [
            "统一命名规则",
            "使用InnoDB引擎",
            "UTF8MB4字符集",
            "添加字段注释"
          ]
        },
        {
          "title": "性能优化",
          "lines": [
            "控制单表500万以内",
            "避免TEXT/BLOB类型",
            "使用最小数据类型",
            "合理设计索引"
          ]
        },
        {
          "title": "场景适配",
          "lines": [
            "电商分库分表",
            "日志分离扩展表",
            "金融decimal精度"
          ]
        }
      ],
      "frames": [
        {
          "note": "规范设计确保团队协作和数据一致性，减少歧义和维护成本",
          "active": [
            0
          ]
        },
        {
          "note": "性能优化通过减少存储和查询开销，提升系统稳定性和查询效率",
          "active": [
            1
          ]
        },
        {
          "note": "场景适配针对不同业务需求，解决特定性能瓶颈和数据准确性问题",
          "active": [
            2
          ]
        }
      ]
    }
  },
  {
    "id": "java-cap-base",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "分布式"
    ],
    "tags": [
      "面试",
      "分布式"
    ],
    "title": "CAP 定理与 BASE 理论是什么？",
    "oneLine": "CAP 定理指出分布式系统无法同时满足一致性、可用性和分区容错，必须在 C 与 A 之间取舍；BASE 理论则强调最终一致性。",
    "analogy": "CAP 定理就像在超市排队结账，如果收银员被隔离（分区），只能选择让所有顾客等待（一致性）或让部分顾客先走（可用性）。",
    "why": "CAP 定理源于分布式系统中网络分区是常态，无法避免。当分区发生时，系统必须在强一致性（C）和高可用性（A）之间取舍，因为网络延迟和丢包无法完全消除。BASE 理论则为这种取舍提供了现实解决方案，即通过最终一致性（Eventually Consistent）在分区后逐步达成一致性，而不是立即强一致。",
    "mechanism": [
      "CAP 定理的核心是分布式系统无法同时满足一致性（C）、可用性（A）和分区容错性（P），只能在 C 与 A 之间取舍。当网络分区发生时，系统必须在强一致性与高可用性之间做出选择。",
      "一致性（C）要求所有操作按实时顺序线性化，即写入后所有读取都必须返回最新值。这通常需要同步复制，但会降低可用性。",
      "可用性（A）要求非故障节点必须对每个请求返回响应，即使数据不一致。这通常通过异步复制实现，但可能导致数据不一致。",
      "分区容错性（P）是默认前提，即假设网络异步且可能分区。系统必须在分区发生时决定是牺牲一致性还是可用性。",
      "BASE 理论（Basically Available, Soft State, Eventually Consistent）强调最终一致性，允许在分区后数据逐步同步，而不是立即一致。",
      "最终一致性（Eventually Consistent）意味着系统在分区后会逐步达成一致，但可能在一段时间内存在不一致状态。这适用于高可用性场景。",
      "软状态（Soft State）允许系统在分区后暂时不一致，但最终会恢复到一致状态。这降低了系统对实时一致性的依赖。",
      "BASE 理论为 CAP 定理提供了现实解决方案，即在分区后通过异步复制和最终一致性实现可用性，而不是强一致性。"
    ],
    "keywords": [
      "CAP 定理",
      "BASE 理论",
      "一致性",
      "可用性",
      "分区容错",
      "最终一致性"
    ],
    "scene": [
      "在分布式锁场景中，ZooKeeper 采用 CP 架构，确保强一致性，但牺牲可用性，可能导致锁获取失败。",
      "在微服务注册中心中，Eureka 采用 AP 架构，确保高可用性，但可能路由到已下线实例，需要重试。",
      "在社交动态系统中，Cassandra 通过调整读写一致性级别在延迟与一致性之间权衡，实现高可用性。"
    ],
    "interviewQ": [
      "CAP 定理为什么在分区发生时必须在 C 与 A 之间取舍？（答：网络分区是常态，无法避免，同步复制会降低可用性，异步复制可能导致数据不一致。）",
      "BASE 理论如何解决 CAP 定理的取舍问题？（答：BASE 理论强调最终一致性，允许在分区后逐步同步数据，而不是立即强一致。）",
      "CAP 定理的适用范围是什么？（答：CAP 理论主要讨论单个数据对象在副本复制场景下的一致性与可用性权衡，不适用于复杂系统。）"
    ],
    "related": [
      {
        "id": "java-consistent-hashing",
        "kind": "extends",
        "note": "了解CAP定理后，能更好理解一致性哈希如何权衡一致性与可用性"
      },
      {
        "id": "java-raft",
        "kind": "extends",
        "note": "了解CAP定理后，能更好理解Raft如何实现一致性"
      },
      {
        "id": "java-distributed-lock2",
        "kind": "extends",
        "note": "了解CAP定理后，能更好理解分布式锁如何权衡一致性与可用性"
      },
      {
        "id": "java-distributed-transaction",
        "kind": "extends",
        "note": "了解CAP定理后，能更好理解事务如何权衡一致性与可用性"
      },
      {
        "id": "java-distributed-id-design",
        "kind": "extends",
        "note": "了解CAP定理后，能更好理解ID生成如何权衡一致性与可用性"
      }
    ],
    "diagram": {
      "kind": "state-machine",
      "nodes": [
        {
          "id": "c",
          "label": "一致性",
          "x": 20,
          "y": 30
        },
        {
          "id": "a",
          "label": "可用性",
          "x": 80,
          "y": 30
        },
        {
          "id": "p",
          "label": "分区容错",
          "x": 50,
          "y": 70
        }
      ],
      "edges": [
        {
          "from": "c",
          "to": "p"
        },
        {
          "from": "a",
          "to": "p"
        },
        {
          "from": "p",
          "to": "c"
        },
        {
          "from": "p",
          "to": "a"
        }
      ],
      "frames": [
        {
          "n": "c",
          "note": "网络分区发生时，系统必须放弃一致性以保证可用性"
        },
        {
          "n": "a",
          "note": "网络分区发生时，系统必须放弃可用性以保证一致性"
        },
        {
          "n": "p",
          "note": "分区容错是默认前提，系统必须在 C 与 A 之间做出选择"
        }
      ]
    }
  },
  {
    "id": "java-consistent-hashing",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "分布式"
    ],
    "tags": [
      "面试",
      "分布式"
    ],
    "title": "一致性哈希算法如何解决节点扩缩容问题？",
    "oneLine": "一致性哈希通过哈希环和虚拟节点实现数据分布的稳定性，减少节点变化时的数据迁移。",
    "analogy": "就像在环形跑道上安排摊位，新增或移除摊位时，只影响相邻摊位，不会让所有顾客都跑向同一个摊位。",
    "why": "传统哈希取模算法在节点扩缩容时会导致大量数据迁移，影响系统稳定性。一致性哈希通过哈希环将数据和节点映射到环上，节点变化只影响相邻区域的数据，减少迁移量。虚拟节点进一步优化数据分布，避免数据倾斜和单点故障。",
    "mechanism": [
      "一致性哈希算法通过哈希环将数据和节点映射到一个环形结构上，每个节点负责环上特定区域的数据，从而实现数据的稳定分布。",
      "当新增或移除节点时，哈希环的结构不变，仅影响相邻区域的数据，避免大规模数据迁移，提升系统的容错性。",
      "哈希环的起点为0，终点为2^32-1，形成一个闭合的环形结构，数据通过顺时针查找最近的节点进行分配。",
      "虚拟节点是真实节点在哈希环上的虚拟分身，通过增加环上的节点密度，实现数据的均匀分布，解决数据倾斜问题。",
      "每个真实节点对应多个虚拟节点，虚拟节点均匀分布在环上，确保数据分布的均衡性，提升系统的负载均衡能力。",
      "当物理节点宕机时，其对应的虚拟节点失效，数据会自然迁移到其他相邻的物理节点，避免单点故障。",
      "虚拟节点的引入使得系统在节点变化时，数据迁移量显著减少，同时提升系统的稳定性和容错能力。",
      "通过合理设置虚拟节点数量，可以平衡数据分布和系统性能，例如每个真实节点对应100-200个虚拟节点。"
    ],
    "keywords": [
      "一致性哈希",
      "哈希环",
      "虚拟节点",
      "数据倾斜",
      "负载均衡",
      "分布式缓存"
    ],
    "scene": [
      "在负载均衡场景中，多个服务器共同处理请求，一致性哈希确保相同请求始终发送到同一台服务器。",
      "分布式缓存系统中，如Redis或Memcached，使用一致性哈希将数据均匀分布到多个缓存服务器。",
      "分库分表场景中，一致性哈希帮助数据均匀分布到不同的数据库或表，避免单点压力过大。"
    ],
    "interviewQ": [
      "为什么一致性哈希比传统哈希取模算法更适用于分布式系统？（答：一致性哈希通过哈希环和虚拟节点减少节点变化时的数据迁移，提升系统的容错性和负载均衡能力。）",
      "虚拟节点在一致性哈希中起到什么作用？（答：虚拟节点均匀分布在哈希环上，解决数据倾斜问题，提升数据分布的均衡性和系统的容错能力。）",
      "一致性哈希如何处理节点的扩缩容？（答：节点变化时，仅影响相邻区域的数据，通过哈希环的结构减少数据迁移量，避免系统崩溃。）"
    ],
    "related": [
      {
        "id": "java-cap-base",
        "kind": "prereq",
        "note": "了解CAP定理后，能更好理解一致性哈希如何权衡一致性与可用性"
      },
      {
        "id": "java-raft",
        "kind": "compare",
        "note": "对比两种分布式协调机制，理解节点一致性保障方式"
      },
      {
        "id": "java-distributed-lock2",
        "kind": "compare",
        "note": "对比数据分布与资源锁的协调机制，理解分布式系统一致性"
      },
      {
        "id": "java-distributed-transaction",
        "kind": "compare",
        "note": "对比数据分布与事务的协调机制，理解分布式系统一致性"
      },
      {
        "id": "java-distributed-id-design",
        "kind": "compare",
        "note": "对比数据分布与ID生成的协调机制，理解分布式系统一致性"
      }
    ],
    "diagram": {
      "kind": "arch",
      "nodes": [
        {
          "id": "hash_ring",
          "label": "哈希环",
          "x": 14,
          "y": 14,
          "w": 22
        },
        {
          "id": "physical_node",
          "label": "物理节点",
          "x": 50,
          "y": 14,
          "w": 22
        },
        {
          "id": "virtual_node",
          "label": "虚拟节点",
          "x": 86,
          "y": 14,
          "w": 22
        },
        {
          "id": "data",
          "label": "数据",
          "x": 50,
          "y": 50,
          "w": 22
        },
        {
          "id": "request",
          "label": "请求",
          "x": 50,
          "y": 84,
          "w": 22
        }
      ],
      "links": [
        {
          "from": "hash_ring",
          "to": "physical_node",
          "label": "映射"
        },
        {
          "from": "hash_ring",
          "to": "virtual_node",
          "label": "扩展"
        },
        {
          "from": "data",
          "to": "hash_ring",
          "label": "定位"
        },
        {
          "from": "request",
          "to": "hash_ring",
          "label": "查找"
        },
        {
          "from": "virtual_node",
          "to": "physical_node",
          "label": "迁移"
        }
      ],
      "frames": [
        {
          "n": "hash_ring",
          "note": "哈希环将数据和节点映射到环形结构，形成闭合的分布空间"
        },
        {
          "n": "physical_node",
          "note": "物理节点负责环上特定区域的数据，节点变化仅影响相邻区域"
        },
        {
          "n": "virtual_node",
          "note": "虚拟节点均匀分布，解决数据倾斜，提升负载均衡能力"
        },
        {
          "n": "data",
          "note": "数据通过顺时针查找最近的节点，实现稳定分配和快速定位"
        },
        {
          "n": "request",
          "note": "请求通过哈希环找到对应节点，确保相同请求始终发送到同一服务器"
        }
      ]
    }
  },
  {
    "id": "java-raft",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "分布式"
    ],
    "tags": [
      "面试",
      "分布式"
    ],
    "title": "Raft 算法是什么？",
    "oneLine": "Raft 是一种分布式共识算法，用于实现节点间日志复制和一致性，确保系统在故障时仍能正常运行。",
    "analogy": "就像一群将军选一个大帅，谁先喊出‘我要当大帅’并获得半数以上支持，谁就成为大帅，其他人听他的指挥。",
    "why": "在分布式系统中，节点可能宕机或断网，导致数据不一致。Raft 通过 Leader 选举、日志复制和安全性约束，确保即使部分节点失效，系统仍能保持一致性。它解决了 Paxos 算法复杂难懂的问题，使共识算法更易理解和实现。",
    "mechanism": [
      "Raft 将共识问题拆解为三个独立模块：Leader 选举、日志复制和安全性。Leader 负责接收客户端请求并协调日志复制，Follower 被动接收日志，Candidate 是临时状态，用于选举 Leader。",
      "Leader 通过心跳机制维持集群状态，定期发送 AppendEntries RPC 保持连接。如果 Follower 在选举超时后未收到心跳，会转换为 Candidate 并发起选举，通过 RequestVote RPC 获取选票。",
      "选举过程中，Candidate 随机化选举超时时间，避免多个节点同时超时导致选票分散。赢得过半数选票的 Candidate 成为 Leader，否则进入下一任期重新选举。",
      "Leader 接收客户端请求后，生成日志条目并广播给 Follower。Follower 验证日志一致性后复制日志，Leader 收到多数响应后推进 commitIndex 并提交日志。",
      "日志匹配属性确保日志不会分叉：如果两个日志在相同索引位置的 term 一致，则内容相同。通过 prevLogIndex 和 prevLogTerm 的一致性检查，保证日志历史一致。",
      "当 Leader 宕机，新 Leader 会通过 AppendEntries 同步日志，强制 Follower 清除不一致的记录并覆盖最新日志，确保日志统一。日志提交后按顺序应用到状态机，保证最终一致性。",
      "Raft 通过租约机制和联合一致性处理成员变更，确保集群在节点上下线时仍能正常运行。这些机制共同保障了系统的容错性和一致性。"
    ],
    "keywords": [
      "Raft",
      "Leader 选举",
      "日志复制",
      "日志匹配属性",
      "安全性",
      "成员变更"
    ],
    "scene": [
      "etcd 使用 Raft 实现分布式键值存储，确保数据一致性。",
      "Consul 通过 Raft 管理服务发现和配置，保证集群状态同步。",
      "在分布式数据库中，Raft 用于日志复制，防止数据丢失或不一致。"
    ],
    "interviewQ": [
      "Raft 中 Leader 选举的随机化超时时间有什么作用？（答：避免多个节点同时超时导致选票分散，提高选举成功率。）",
      "日志匹配属性如何确保日志不分叉？（答：通过 prevLogIndex 和 prevLogTerm 的一致性检查，确保日志历史一致，防止分叉。）",
      "Raft 如何处理 Leader 宕机后的日志同步？（答：新 Leader 通过 AppendEntries 强制 Follower 清除不一致日志并覆盖最新日志，确保统一。）"
    ],
    "related": [
      {
        "id": "java-cap-base",
        "kind": "prereq",
        "note": "了解CAP定理后，能更好理解Raft如何实现一致性"
      },
      {
        "id": "java-distributed-lock2",
        "kind": "compare",
        "note": "对比数据分布与资源锁的协调机制，理解分布式系统一致性"
      },
      {
        "id": "java-consistent-hashing",
        "kind": "compare",
        "note": "对比两种分布式协调机制，理解节点一致性保障方式"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "选举 Leader",
        "日志复制",
        "提交日志",
        "处理故障"
      ],
      "frames": [
        {
          "s": 0,
          "note": "Follower 未收到心跳，转为 Candidate，随机化选举超时时间，避免选票分散。"
        },
        {
          "s": 1,
          "note": "Leader 生成日志条目，广播 AppendEntries RPC，Follower 验证日志一致性后复制。"
        },
        {
          "s": 2,
          "note": "Leader 收到多数响应后推进 commitIndex，提交日志到状态机，确保最终一致性。"
        },
        {
          "s": 3,
          "note": "Leader 宕机后，新 Leader 通过 AppendEntries 同步日志，强制 Follower 清除不一致记录。"
        }
      ]
    }
  },
  {
    "id": "java-distributed-lock2",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "分布式"
    ],
    "tags": [
      "面试",
      "分布式"
    ],
    "title": "为什么需要分布式锁？",
    "oneLine": "分布式锁用于协调多个进程对共享资源的互斥访问，解决本地锁无法跨JVM协调的问题。",
    "analogy": "就像多个快递员同时送同一份包裹，必须有一个统一的调度中心协调谁先送，避免包裹被重复派送。",
    "why": "当多个服务实例需要互斥操作同一份共享资源时，本地锁无法跨JVM协调，导致并发问题。例如秒杀场景中，多个实例同时扣减库存，可能造成超卖。分布式锁通过外部系统（如Redis）实现跨进程互斥，确保同一时间只有一个实例能操作资源。",
    "mechanism": [
      "分布式锁是一种跨进程的互斥机制，通过外部系统（如Redis、ZooKeeper）协调多个实例对共享资源的访问，确保同一时间只有一个实例能操作资源。",
      "当多个实例需要操作同一份共享资源时，它们必须先获取同一把锁。获取锁失败的实例将无法执行业务逻辑，直到锁被释放。",
      "锁的获取和释放由外部系统原子化处理，确保只有持有锁的实例才能执行业务操作，防止并发冲突。",
      "锁的持有者需要在业务执行期间保持锁的有效性，通常通过设置锁的过期时间或续约机制来避免锁提前失效。",
      "锁释放时必须校验持有者身份，防止非法释放锁导致资源竞争。例如Redis锁释放时需校验value值是否匹配。",
      "锁的粒度应根据资源划分，如按商品ID、订单ID等设计lock key，避免将无关资源混入同一锁中。",
      "锁的续约机制（如看门狗）和Fencing Token用于防止锁过期后旧持有者继续操作资源，确保业务一致性。",
      "锁的获取语义可以是阻塞等待、限时等待或立即失败，需根据业务需求设置最大等待时间和重试策略。"
    ],
    "keywords": [
      "分布式锁",
      "互斥",
      "锁粒度",
      "Fencing Token",
      "秒杀超卖",
      "库存扣减"
    ],
    "scene": [
      "秒杀系统中多个实例同时扣减库存，需用分布式锁防止超卖。",
      "订单服务部署多个实例，需用锁协调对数据库库存的并发操作。",
      "分布式任务调度系统中，多个节点需互斥执行同一任务，防止重复处理。"
    ],
    "interviewQ": [
      "追问1：分布式锁和本地锁的区别是什么？（答：本地锁只能协调同一JVM内的线程，而分布式锁通过外部系统协调跨JVM的进程。）",
      "追问2：如何确保分布式锁的安全释放？（答：释放锁时需校验持有者身份，如Redis锁需校验value值是否匹配，防止非法释放。）",
      "追问3：锁粒度设计不当会带来什么问题？（答：锁粒度过粗可能导致资源争用，粒度过细则增加锁管理复杂度，需根据业务场景合理划分。）"
    ],
    "related": [
      {
        "id": "java-raft",
        "kind": "compare",
        "note": "对比两种分布式协调机制，理解节点一致性保障方式"
      },
      {
        "id": "java-cap-base",
        "kind": "prereq",
        "note": "了解CAP定理后，能更好理解分布式锁如何权衡一致性与可用性"
      },
      {
        "id": "java-consistent-hashing",
        "kind": "compare",
        "note": "对比数据分布与资源锁的协调机制，理解分布式系统一致性"
      },
      {
        "id": "java-distributed-transaction",
        "kind": "extends",
        "note": "理解分布式锁后，能更好掌握事务的互斥与一致性保障"
      },
      {
        "id": "java-distributed-id-design",
        "kind": "extends",
        "note": "理解分布式锁后，能更好掌握ID生成的互斥与一致性保障"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "获取锁",
        "执行业务",
        "释放锁"
      ],
      "frames": [
        {
          "s": 0,
          "note": "获取锁需通过外部系统（如Redis）原子化操作，确保只有一个实例能获取锁。"
        },
        {
          "s": 1,
          "note": "业务执行期间必须保持锁的有效性，通过设置过期时间或续约机制防止锁失效。"
        },
        {
          "s": 2,
          "note": "释放锁前需校验持有者身份，防止非法释放导致资源竞争，如Redis需校验value值是否匹配。"
        }
      ]
    }
  },
  {
    "id": "java-distributed-transaction",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "分布式"
    ],
    "tags": [
      "面试",
      "分布式"
    ],
    "title": "开启一个事务",
    "oneLine": "开启事务是确保一组操作要么全部成功，要么全部失败的关键步骤，用于维护数据一致性。",
    "analogy": "就像在厨房里同时准备多个菜，如果其中一个菜烧糊了，就要全部倒掉重新开始，确保每道菜都成功。",
    "why": "在单体系统中，数据库事务通过ACID特性确保数据一致性，但在分布式系统中，多个服务和数据库的协作需要分布式事务。开启事务是协调多个操作的起点，确保在出现故障时能回滚，避免数据不一致。如果没有事务机制，数据可能会处于中间状态，导致系统混乱。",
    "mechanism": [
      "开启事务是启动一个逻辑操作单元，确保所有相关操作在同一个事务上下文中执行，防止数据在中间状态被提交。",
      "在数据库中，开启事务通常通过执行`START TRANSACTION`命令，标记事务的开始，之后的所有操作都属于该事务。",
      "事务开启后，数据库会记录所有操作日志（如redo log和undo log），以便在发生错误时回滚，保证原子性和持久性。",
      "在分布式系统中，开启事务意味着启动一个全局事务，协调多个服务和数据库的事务状态，确保所有参与者都处于一致的准备状态。",
      "事务开启后，系统会检查所有涉及的资源是否可用，并准备执行预提交操作（如写入日志），以确保后续提交或回滚的可行性。",
      "如果在事务执行过程中发生错误，系统会根据事务的隔离性和一致性要求，决定是否回滚或重试，以保证最终数据的一致性。",
      "在分布式事务中，开启事务后，事务管理器（TM）会向所有资源管理器（RM）发送准备请求，确保所有参与者都准备好执行本地事务。",
      "事务开启后，系统会持续监控事务的执行状态，确保在提交或回滚时能够正确处理所有操作，避免数据不一致。"
    ],
    "keywords": [
      "事务",
      "START TRANSACTION",
      "ACID",
      "redo log",
      "undo log",
      "隔离性"
    ],
    "scene": [
      "在电商系统中，用户下单时需要同时更新订单表和库存表，开启事务确保这两个操作要么都成功，要么都失败。",
      "在银行转账系统中，开启事务确保转账操作的原子性，防止因网络中断导致数据不一致。",
      "在微服务架构中，订单服务和库存服务需要在同一个事务中完成操作，开启事务协调多个服务的事务状态。"
    ],
    "interviewQ": [
      "开启事务在数据库中是如何实现的？（答：通过执行START TRANSACTION命令，标记事务的开始，之后的所有操作都属于该事务。）",
      "事务开启后，数据库会记录哪些日志？（答：会记录redo log和undo log，用于保证事务的持久性和原子性。）",
      "在分布式系统中，开启事务的作用是什么？（答：确保多个服务和数据库的事务状态一致，协调所有参与者执行预提交操作。）"
    ],
    "related": [
      {
        "id": "java-distributed-lock2",
        "kind": "prereq",
        "note": "理解分布式锁后，能更好掌握事务的互斥与一致性保障"
      },
      {
        "id": "java-cap-base",
        "kind": "prereq",
        "note": "了解CAP定理后，能更好理解事务如何权衡一致性与可用性"
      },
      {
        "id": "java-consistent-hashing",
        "kind": "compare",
        "note": "对比数据分布与事务的协调机制，理解分布式系统一致性"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "标记事务开始",
        "记录操作日志",
        "检查资源可用性",
        "准备提交或回滚"
      ],
      "frames": [
        {
          "s": 0,
          "note": "执行 START TRANSACTION 命令，标记事务开始，所有后续操作进入事务上下文。"
        },
        {
          "s": 1,
          "note": "数据库开始记录 redo log 和 undo log，用于后续回滚或持久化操作。"
        },
        {
          "s": 2,
          "note": "系统检查所有涉及的资源是否可用，确保后续提交或回滚的可行性。"
        },
        {
          "s": 3,
          "note": "根据事务隔离性和一致性要求，决定是否提交或回滚，确保最终数据一致性。"
        }
      ]
    }
  },
  {
    "id": "java-distributed-id-design",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "分布式"
    ],
    "tags": [
      "面试",
      "分布式"
    ],
    "title": "分布式 ID 设计如何满足不同业务场景需求？",
    "oneLine": "分布式 ID 设计需结合业务需求，满足唯一性、可读性、安全性、高效性等特性。",
    "analogy": "就像快递单号，既要唯一且可追踪，又要便于用户识别和查询，同时不能泄露隐私信息。",
    "why": "分布式 ID 是解决多节点系统中唯一标识问题的必要手段。传统单机 ID 无法满足分布式场景下的全局唯一性，而业务需求又要求 ID 具有可读性、可查询性、安全性等特性。例如订单号需便于客服查询，优惠券码需防伪且可批量生成，TraceId 需支持调用链追踪。因此，需要根据不同业务场景设计不同的 ID 生成策略，以平衡性能、安全性和可读性。",
    "mechanism": [
      "分布式 ID 是一种全局唯一、可读、安全的标识符，用于在分布式系统中唯一标识数据或业务实体。其核心是确保在不同节点生成的 ID 不重复，同时满足业务对 ID 的可读性、安全性、查询效率等要求。",
      "订单号设计需兼顾信息安全和可读性。例如，订单号中可包含时间、类型等信息，但不能泄露隐私或运营数据。同时，订单号应尽量使用数字，以提高数据库查询效率。",
      "优惠券码设计需支持批量生成、防伪和校验。通常采用编码空间（如 a-z、A-Z、0-9）生成唯一兑换码，同时加入校验码以确保数据有效性。",
      "TraceId 生成需高效且可自主生成，避免依赖外部服务。通常结合服务器 IP、时间戳、自增序列和进程 ID 生成唯一标识，确保调用链路可追踪。",
      "短网址 ID 需支持长度压缩和高效映射。通过将数字 ID 转换为更高进制字符（如 Base62），可缩短网址长度，便于传播。",
      "不同业务场景对 ID 的要求不同，如订单号需要可查询，优惠券码需要防伪，TraceId 需要支持调用链追踪。因此，需根据业务需求选择合适的 ID 生成策略。",
      "ID 生成策略需兼顾性能和安全性。例如，使用 Redis 或数据库自增生成 ID 时，需考虑并发和锁机制；使用 Snowflake 或 Leaf 等算法时，需确保时间戳和序列号的唯一性。",
      "ID 生成需考虑扩展性和容错性。例如，使用号段模式时，需合理规划号段长度和分配策略，避免 ID 重复或资源浪费。"
    ],
    "keywords": [
      "分布式 ID",
      "订单号生成",
      "优惠券 ID",
      "TraceId",
      "短网址",
      "ID 生成策略"
    ],
    "scene": [
      "订单系统中，订单号需便于客服查询，同时不能泄露隐私信息，如用户手机号或交易流水。",
      "优惠券和兑换券需支持批量生成、防伪和校验，如疫情消费券需在活动前生成，且不可被破解。",
      "分布式系统中，TraceId 需支持调用链追踪，如日志系统中需记录每个服务的调用路径。"
    ],
    "interviewQ": [
      "订单号设计中如何平衡信息安全和可读性？（答：订单号中可包含时间、类型等信息，但不能泄露隐私或运营数据，同时尽量使用数字提高查询效率。）",
      "优惠券码如何确保唯一性和防伪？（答：采用编码空间生成唯一兑换码，并加入校验码确保数据有效性，防止被破解或重复使用。）",
      "TraceId 生成为何需要结合服务器 IP 和时间戳？（答：结合 IP 和时间戳可确保 ID 唯一性，同时支持调用链追踪，避免依赖外部服务。）"
    ],
    "related": [
      {
        "id": "java-distributed-lock2",
        "kind": "prereq",
        "note": "理解分布式锁后，能更好掌握ID生成的互斥与一致性保障"
      },
      {
        "id": "java-consistent-hashing",
        "kind": "compare",
        "note": "对比数据分布与ID生成的协调机制，理解分布式系统一致性"
      },
      {
        "id": "java-cap-base",
        "kind": "prereq",
        "note": "了解CAP定理后，能更好理解ID生成如何权衡一致性与可用性"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "订单号",
          "lines": [
            "包含时间、类型信息",
            "避免泄露隐私数据",
            "使用数字提升查询效率"
          ]
        },
        {
          "title": "优惠券码",
          "lines": [
            "支持批量生成",
            "加入校验码防伪",
            "使用编码空间（Base62）"
          ]
        },
        {
          "title": "TraceId",
          "lines": [
            "结合 IP、时间戳生成",
            "支持调用链追踪",
            "避免依赖外部服务"
          ]
        }
      ],
      "frames": [
        {
          "note": "订单号需兼顾可读性和隐私安全，避免暴露用户敏感信息",
          "active": [
            0
          ]
        },
        {
          "note": "优惠券码需防伪且支持批量生成，编码空间和校验码是关键",
          "active": [
            1
          ]
        },
        {
          "note": "TraceId 需高效生成并支持调用链追踪，避免依赖外部服务",
          "active": [
            2
          ]
        }
      ]
    }
  },
  {
    "id": "java-api-gateway",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "分布式"
    ],
    "tags": [
      "面试",
      "分布式"
    ],
    "title": "什么是 API 网关？",
    "oneLine": "API 网关是客户端与后端服务之间的统一入口，负责请求路由、鉴权、限流等核心功能。",
    "analogy": "API 网关就像快递员，接收所有包裹，检查是否符合收件要求，然后根据地址分发到正确的地方。",
    "why": "在微服务架构中，每个服务都需要独立处理认证、限流等逻辑，导致代码重复和维护困难。网关统一处理这些通用功能，避免重复开发，提高系统可维护性和安全性。同时，网关还能实现负载均衡和流量控制，保障系统稳定性。网关的出现解决了后端服务重复实现相同功能的问题，使得每个服务可以专注于业务逻辑，而无需处理通用功能。此外，网关还能提供统一的监控和日志记录，方便系统管理和故障排查。",
    "mechanism": [
      "API 网关是客户端与后端服务之间的统一入口，所有请求必须经过网关，由网关决定如何处理请求。网关的核心职责是将请求路由到正确的后端服务，并处理鉴权、限流等通用功能。",
      "网关通过路由功能将请求转发到正确的后端服务，根据配置的规则动态选择目标服务。例如，根据请求路径或方法匹配对应的路由规则，将请求分发到相应的微服务实例。",
      "网关支持负载均衡，根据后端服务的负载情况或配置策略，将请求分发到不同的实例，提高系统可用性。例如，可以配置轮询、随机、权重等负载均衡策略，确保请求均匀分配到各个服务实例。",
      "网关提供安全认证功能，对请求进行身份验证和权限校验，确保只有合法用户才能访问服务。例如，通过 OAuth2、JWT 等方式验证用户身份，并根据 RBAC 等授权机制判断用户是否有权限访问特定资源。",
      "网关实现限流熔断机制，根据配置的阈值限制请求流量，防止系统过载，提高系统稳定性。例如，可以配置每秒最大请求数，当超过阈值时，自动熔断并返回默认值，避免系统崩溃。",
      "网关记录请求日志，用于后续分析和监控，帮助团队了解系统运行状态和用户行为。例如，可以记录请求的 IP、时间、方法、路径等信息，便于后续审计和故障排查。",
      "网关支持协议转换，将不同协议的请求统一转换为后端服务能识别的格式，提高系统兼容性。例如，可以将 HTTP 请求转换为 gRPC 或 AMQP 协议，以便与不同技术栈的服务进行通信。",
      "网关可以进行响应缓存，对于静态或更新不频繁的数据，直接从缓存中返回，减少后端服务压力。例如，可以配置缓存策略，将某些请求的响应结果存储在内存或 Redis 中，后续相同请求直接返回缓存结果，提高系统性能。"
    ],
    "keywords": [
      "API 网关",
      "微服务网关",
      "Spring Cloud Gateway",
      "Kong",
      "APISIX",
      "ShenYu",
      "限流熔断",
      "负载均衡"
    ],
    "scene": [
      "在电商系统中，网关负责统一处理用户的登录请求，验证身份后将请求转发到订单、支付等后端服务。",
      "在金融系统中，网关通过限流和熔断机制，防止高并发请求导致系统崩溃，保障交易安全。",
      "在微服务架构中，网关统一处理所有服务的鉴权和日志记录，避免每个服务重复实现相同功能。"
    ],
    "interviewQ": [
      "追问1：网关的核心职责是什么？（答：网关的核心职责是请求转发和请求过滤，分别负责将请求路由到正确服务和处理鉴权、限流等通用功能。）",
      "追问2：网关如何实现负载均衡？（答：网关通过配置负载均衡策略，如轮询、随机、权重等，将请求分发到不同的后端服务实例，提高系统可用性。）",
      "追问3：网关如何实现限流和熔断？（答：网关通过配置限流阈值，当请求超过阈值时自动熔断，返回默认值，防止系统过载。）",
      "追问4：网关在微服务架构中的作用是什么？（答：网关在微服务架构中作为统一入口，处理鉴权、限流、日志等通用功能，避免每个服务重复实现相同逻辑，提高系统可维护性和安全性。）"
    ],
    "related": [
      {
        "id": "java-rpc-intro",
        "kind": "compare",
        "note": "API 网关处理请求路由，而 RPC 实现服务间通信，两者共同构建分布式系统"
      },
      {
        "id": "java-zookeeper-intro",
        "kind": "compare",
        "note": "API 网关管理服务入口，ZooKeeper 管理服务注册信息，两者协同实现服务发现"
      }
    ],
    "diagram": {
      "kind": "arch",
      "nodes": [
        {
          "id": "client",
          "label": "客户端",
          "x": 15,
          "y": 14,
          "w": 18
        },
        {
          "id": "gw",
          "label": "API 网关",
          "x": 50,
          "y": 14,
          "w": 26
        },
        {
          "id": "svc",
          "label": "后端服务",
          "x": 85,
          "y": 14,
          "w": 22
        },
        {
          "id": "db",
          "label": "数据库",
          "x": 85,
          "y": 84,
          "w": 22
        },
        {
          "id": "cache",
          "label": "缓存",
          "x": 50,
          "y": 84,
          "w": 22
        }
      ],
      "links": [
        {
          "from": "client",
          "to": "gw",
          "label": "请求"
        },
        {
          "from": "gw",
          "to": "svc",
          "label": "路由"
        },
        {
          "from": "svc",
          "to": "db",
          "label": "调用"
        },
        {
          "from": "svc",
          "to": "cache",
          "label": "读写"
        },
        {
          "from": "gw",
          "to": "cache",
          "label": "缓存"
        }
      ],
      "frames": [
        {
          "n": "client",
          "note": "客户端发起请求，通过统一入口访问系统"
        },
        {
          "n": "gw",
          "note": "网关处理鉴权、限流、路由等通用功能，决定请求走向"
        },
        {
          "n": "svc",
          "note": "后端服务处理业务逻辑，访问数据库或缓存获取数据"
        },
        {
          "n": "db",
          "note": "数据库存储核心业务数据，确保数据一致性与安全性"
        },
        {
          "n": "cache",
          "note": "缓存存储热点数据，提升系统响应速度和吞吐量"
        }
      ]
    }
  },
  {
    "id": "java-rpc-intro",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "分布式"
    ],
    "tags": [
      "面试",
      "分布式"
    ],
    "title": "RPC 是什么？为什么需要它？",
    "oneLine": "RPC 是远程过程调用，让调用远程服务像调用本地方法一样简单。",
    "analogy": "就像在图书馆借书，你不需要知道书在哪个书架，只需要告诉图书管理员你要哪本书，他就会帮你取来。",
    "why": "在分布式系统中，服务部署在不同机器上，无法直接调用。手动实现网络通信需要处理传输协议、序列化等复杂问题。RPC 封装了这些细节，让开发者像调用本地方法一样调用远程服务，极大简化开发流程。",
    "mechanism": [
      "RPC 的核心是让调用远程方法像调用本地方法一样简单，它通过代理类和网络传输实现远程调用。客户端 Stub 将方法调用信息封装成 RpcRequest，通过网络传输到服务端。",
      "服务端 Stub 接收到 RpcRequest 后，反序列化为 Java 对象，并调用本地方法执行。服务端 Stub 根据 RpcRequest 中的类、方法、方法参数等信息调用本地方法，执行完成后将结果封装成 RpcResponse 并通过网络传输回客户端。",
      "客户端 Stub 接收到 RpcResponse 后，反序列化为 Java 对象，最终返回调用结果。整个过程屏蔽了网络传输和序列化细节，让开发者专注于业务逻辑。",
      "RPC 通过动态代理技术实现，使调用远程方法与本地方法在语法上保持一致。开发者无需关心底层网络通信细节，只需像调用本地方法一样调用远程方法。",
      "网络传输使用 Socket 或 Netty 等工具实现，确保数据高效可靠地传输。不同的传输方式会影响性能和稳定性，例如 Netty 相比 Socket 更加高效。",
      "序列化是 RPC 的关键环节，将对象转换为可传输的格式，如 JSON、ProtoBuf 等。不同的序列化方式会影响传输效率和兼容性，例如 ProtoBuf 更高效但学习成本较高。",
      "服务发现是 RPC 的重要环节，客户端需要知道服务提供端的地址才能进行调用。服务发现可以通过注册中心如 Zookeeper 实现，确保服务调用的可靠性和扩展性。"
    ],
    "keywords": [
      "RPC",
      "远程过程调用",
      "动态代理",
      "序列化",
      "服务发现",
      "Dubbo",
      "gRPC",
      "Thrift"
    ],
    "scene": [
      "微服务架构中，服务之间通过 RPC 进行通信，如订单服务调用库存服务。",
      "跨语言调用场景，如 Java 服务调用 Python 服务，使用 gRPC 实现。",
      "高并发场景下，通过 RPC 实现服务间的负载均衡和流量控制。"
    ],
    "interviewQ": [
      "追问1：RPC 的核心原理是什么？（答：RPC 通过客户端 Stub 和服务端 Stub 实现远程调用，屏蔽网络传输和序列化细节，使调用远程方法像调用本地方法一样简单。）",
      "追问2：RPC 和 HTTP 的区别是什么？（答：RPC 是基于网络传输的远程调用，而 HTTP 是基于请求-响应的协议。RPC 更适合高并发、低延迟的场景，而 HTTP 更适合通用接口调用。）",
      "追问3：RPC 中的序列化和反序列化有什么作用？（答：序列化将对象转换为可传输的格式，反序列化将传输的数据还原为对象，确保数据在传输过程中的完整性和一致性。）",
      "追问4：RPC 中的服务发现是怎么实现的？（答：服务发现通过注册中心如 Zookeeper 实现，客户端根据注册中心获取服务提供端的地址，确保服务调用的可靠性和扩展性。）"
    ],
    "related": [
      {
        "id": "java-api-gateway",
        "kind": "compare",
        "note": "RPC 实现服务间通信，API 网关管理服务入口，两者共同构建分布式系统"
      },
      {
        "id": "java-zookeeper-intro",
        "kind": "compare",
        "note": "RPC 需要服务注册，ZooKeeper 管理服务注册信息，两者共同实现服务发现"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "封装请求",
        "网络传输",
        "反序列化",
        "执行本地方法",
        "返回结果"
      ],
      "frames": [
        {
          "s": 0,
          "note": "客户端 Stub 将方法调用封装为 RpcRequest，包含类、方法、参数等信息"
        },
        {
          "s": 1,
          "note": "RpcRequest 通过 Socket 或 Netty 等工具传输到服务端，确保高效可靠"
        },
        {
          "s": 2,
          "note": "服务端 Stub 反序列化 RpcRequest 为 Java 对象，准备调用本地方法"
        },
        {
          "s": 3,
          "note": "服务端执行本地方法，处理业务逻辑，生成 RpcResponse 返回"
        },
        {
          "s": 4,
          "note": "客户端 Stub 反序列化 RpcResponse，将结果返回给调用方"
        }
      ]
    }
  },
  {
    "id": "java-zookeeper-intro",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "分布式"
    ],
    "tags": [
      "面试",
      "分布式"
    ],
    "title": "该数据节点关联的数据内容为空",
    "oneLine": "ZooKeeper 中数据节点（znode）的数据内容为空，说明该节点未存储任何业务数据。",
    "analogy": "就像一个空的快递箱，虽然箱子存在，但里面什么都没有，等待你放入实际的货物。",
    "why": "ZooKeeper 的设计初衷是用于分布式协调，而不是存储大量业务数据。因此，数据节点通常只存储元信息或轻量级数据。如果数据节点的数据内容为空，说明该节点可能用于协调目的，如注册中心或分布式锁，而不是存储业务数据。这样可以提高性能并避免资源浪费。",
    "mechanism": [
      "ZooKeeper 的数据节点（znode）由两部分组成：stat 状态信息和 data 数据内容。当 data 数据内容为空时，说明该节点未存储任何业务数据。",
      "ZooKeeper 的数据模型采用层次化的多叉树结构，每个节点都有唯一的路径标识。数据节点可以是持久节点、临时节点、持久顺序节点或临时顺序节点。",
      "当创建一个数据节点时，可以指定其类型和是否需要顺序性。如果数据节点的数据内容为空，可能是由于该节点仅用于协调目的，如注册中心或分布式锁。",
      "ZooKeeper 的数据节点存储的数据内容通常较小，最大不超过 1M。如果数据节点的数据内容为空，可能是为了节省存储空间和提高性能。",
      "ZooKeeper 的数据节点通过 Watcher 机制实现事件监听。当数据节点的数据内容发生变化时，会触发相应的事件通知。",
      "ZooKeeper 的数据节点状态信息（stat）包含事务 ID、创建时间、更新时间等信息，用于跟踪节点的变化。",
      "ZooKeeper 的数据节点可以通过命令行工具（如 zkCli.sh）查看其状态信息和数据内容。如果数据内容为空，说明该节点未存储任何业务数据。",
      "ZooKeeper 的数据节点在集群中同步，确保所有节点的数据一致性。如果数据节点的数据内容为空，说明该节点未存储任何业务数据。"
    ],
    "keywords": [
      "ZooKeeper",
      "znode",
      "数据节点",
      "data",
      "stat",
      "Watcher",
      "ACL"
    ],
    "scene": [
      "在注册中心中，数据节点用于存储服务的注册信息，数据内容为空表示该节点未存储任何服务信息。",
      "在分布式锁中，数据节点用于表示锁的状态，数据内容为空表示锁未被占用。",
      "在配置中心中，数据节点用于存储配置信息，数据内容为空表示该节点未存储任何配置数据。"
    ],
    "interviewQ": [
      "为什么 ZooKeeper 的数据节点数据内容可能为空？（答：ZooKeeper 的设计初衷是用于分布式协调，而不是存储大量业务数据。因此，数据节点通常只存储元信息或轻量级数据。如果数据节点的数据内容为空，说明该节点可能用于协调目的，如注册中心或分布式锁，而不是存储业务数据。）",
      "ZooKeeper 的数据节点数据内容为空有什么影响？（答：如果数据节点的数据内容为空，可能是为了节省存储空间和提高性能。但需要注意，ZooKeeper 不适合存储大量数据，因此应避免在数据节点中存储大文件。）",
      "如何查看 ZooKeeper 数据节点的数据内容？（答：可以使用 zkCli.sh 命令行工具，通过 get 命令查看数据节点的数据内容。如果数据内容为空，说明该节点未存储任何业务数据。）"
    ],
    "related": [
      {
        "id": "java-api-gateway",
        "kind": "compare",
        "note": "ZooKeeper 管理服务注册信息，API 网关管理服务入口，两者协同实现服务发现"
      },
      {
        "id": "java-rpc-intro",
        "kind": "compare",
        "note": "ZooKeeper 管理服务注册信息，RPC 需要服务注册，两者共同实现服务发现"
      }
    ],
    "diagram": null
  },
  {
    "id": "java-mq-basics",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "消息队列"
    ],
    "tags": [
      "面试",
      "消息队列"
    ],
    "title": "消息队列是什么？",
    "oneLine": "消息队列是用于异步处理、削峰填谷和解耦的中间件，通过生产者和消费者模型实现消息传递。",
    "analogy": "消息队列就像快递站，用户下单后把包裹交给快递员，快递员再分发给各个收件人，无需用户直接联系收件人。",
    "why": "随着分布式系统的发展，系统间直接调用会导致耦合度高、扩展性差。消息队列通过异步处理和解耦，降低系统复杂性，提高可扩展性。同时，高并发场景下，消息队列可以缓冲请求，避免后端服务崩溃。此外，消息队列支持分布式事务和顺序保证，满足复杂业务需求。",
    "mechanism": [
      "消息队列是一种先进先出的数据结构，用于存储和传递消息。生产者将消息发送到队列，消费者从队列中取出消息进行处理。",
      "异步处理通过将耗时操作放入消息队列，使用户请求立即返回，提高用户体验。但需注意业务流程的配合，如订单提交后需等待消息处理完成再通知用户。",
      "削峰填谷通过将高并发请求缓冲到消息队列，后端服务按自身能力逐步处理，避免系统过载。例如秒杀活动时，消息队列可缓解瞬时流量冲击。",
      "解耦通过生产者和消费者之间的间接通信，减少模块间直接依赖。新增模块只需订阅消息即可，不影响原有系统。",
      "消息队列支持发布-订阅和点对点两种模型。发布-订阅模式适用于广播场景，点对点模式适用于一对一通信。",
      "消息可靠性通过确认机制、持久化、重试和补偿策略实现。生产者发送消息后需确认，Broker存储消息需持久化，消费者处理失败需重试或补偿。",
      "幂等性通过唯一索引、状态机和消费记录表实现，防止重复消费。业务唯一键是幂等处理的核心。",
      "消息积压处理需先分析原因，如生产突增或消费者变慢，再采取限流、扩容或优化消费逻辑等措施。"
    ],
    "keywords": [
      "消息队列",
      "MQ",
      "异步解耦",
      "削峰填谷",
      "消息丢失",
      "消息幂等",
      "消息顺序",
      "Kafka"
    ],
    "scene": [
      "电商秒杀活动时，使用消息队列缓冲大量订单请求，避免后端服务崩溃。",
      "用户下单后，订单数据通过消息队列异步处理，减少响应时间。",
      "微服务架构中，订单服务通过消息队列通知库存服务扣减库存，实现解耦。"
    ],
    "interviewQ": [
      "追问1：消息队列如何保证消息不丢失？（答：通过生产者确认、持久化存储、消费者重试和补偿机制等多环节保障消息可靠性。）",
      "追问2：消息队列如何处理重复消费？（答：通过幂等性设计，如唯一索引、状态机和消费记录表，确保消息处理唯一性。）",
      "追问3：消息队列的两种消息模型是什么？（答：点对点模型和发布-订阅模型，前者适用于一对一通信，后者适用于广播场景。）"
    ],
    "related": [
      {
        "id": "java-kafka",
        "kind": "prereq",
        "note": "消息队列是 Kafka 的基础，理解消息队列有助于深入理解 Kafka 的功能"
      },
      {
        "id": "java-rabbitmq",
        "kind": "extends",
        "note": "了解消息队列的基本概念后，才能理解 RabbitMQ 的具体实现"
      },
      {
        "id": "java-rocketmq",
        "kind": "extends",
        "note": "掌握消息队列的基本概念后，才能理解 RocketMQ 的具体实现"
      },
      {
        "id": "java-realtime-push",
        "kind": "extends",
        "note": "了解消息队列的基本概念是选择实时推送方案的前提"
      }
    ],
    "diagram": {
      "kind": "arch",
      "nodes": [
        {
          "id": "prod",
          "label": "生产者",
          "x": 20,
          "y": 14,
          "w": 18
        },
        {
          "id": "mq",
          "label": "消息队列",
          "x": 50,
          "y": 50,
          "w": 22
        },
        {
          "id": "cons",
          "label": "消费者",
          "x": 80,
          "y": 84,
          "w": 18
        },
        {
          "id": "broker",
          "label": "Broker",
          "x": 50,
          "y": 14,
          "w": 22
        }
      ],
      "links": [
        {
          "from": "prod",
          "to": "broker",
          "label": "发送"
        },
        {
          "from": "broker",
          "to": "mq",
          "label": "存储"
        },
        {
          "from": "mq",
          "to": "cons",
          "label": "消费"
        },
        {
          "from": "prod",
          "to": "mq",
          "label": "写入"
        },
        {
          "from": "cons",
          "to": "mq",
          "label": "确认"
        }
      ],
      "frames": [
        {
          "n": "prod",
          "note": "生产者将消息发送到消息队列，无需等待消费者处理完成"
        },
        {
          "n": "mq",
          "note": "消息队列存储消息，支持持久化和确认机制，防止消息丢失"
        },
        {
          "n": "cons",
          "note": "消费者从消息队列中取出消息处理，处理失败可重试或补偿"
        }
      ]
    }
  },
  {
    "id": "java-kafka",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "消息队列"
    ],
    "tags": [
      "面试",
      "消息队列"
    ],
    "title": "Kafka 是什么？主要应用场景有哪些？",
    "oneLine": "Kafka 是一个分布式流式处理平台，具备消息队列、持久化存储和流式处理功能，适用于实时数据管道和流数据处理。",
    "analogy": "Kafka 像是一个快递站，接收快递（消息）并分发给不同的收件人（消费者），同时还能保存快递记录，方便后续查看和处理。",
    "why": "Kafka 的设计初衷是处理海量日志数据，但随着发展，它逐渐具备了消息队列的特性。传统消息队列无法处理高吞吐量，而 Kafka 通过分区、副本和批量处理等机制，解决了消息丢失、可靠性差等问题，成为大数据领域的重要工具。",
    "mechanism": [
      "Kafka 是一个分布式流式处理平台，它结合了消息队列、持久化存储和流式处理三大功能，支持高吞吐量和低延迟。",
      "Kafka 通过将消息持久化到磁盘，避免了消息丢失的风险，同时支持多副本机制，确保数据的高可用性和容灾能力。",
      "Kafka 的分区机制允许消息在多个节点上分布存储，提高系统的并发处理能力和负载均衡能力。",
      "Kafka 的发布-订阅模型支持多个消费者同时消费同一消息，适用于需要广播或分发的场景。",
      "Kafka 的批量处理和异步机制提升了性能，使其能够每秒处理数百万条消息。",
      "Kafka 的流式处理能力允许在消息发布时进行实时处理，支持复杂的数据转换和分析。",
      "Kafka 的零拷贝技术减少了数据复制的开销，提高了传输效率，是其高性能的重要原因之一。"
    ],
    "keywords": [
      "Kafka",
      "消息队列",
      "Kafka分区",
      "Kafka副本",
      "ISR",
      "消费者组",
      "Rebalance",
      "零拷贝"
    ],
    "scene": [
      "实时数据管道：用于将日志、传感器数据等实时数据从源系统传输到数据仓库或分析平台。",
      "流数据处理：用于实时分析用户行为、交易数据等，支持实时监控和预警。",
      "消息队列：用于解耦系统组件，实现异步通信和任务分发，如订单处理、通知系统等。"
    ],
    "interviewQ": [
      "追问1：Kafka 的分区机制如何提高系统的并发能力？（答：Kafka 的分区机制允许消息在多个节点上分布存储，提高系统的并发处理能力和负载均衡能力。）",
      "追问2：Kafka 的发布-订阅模型和队列模型有什么区别？（答：Kafka 的发布-订阅模型支持多个消费者同时消费同一消息，适用于广播或分发的场景，而队列模型只能保证消息被一个消费者使用。）",
      "追问3：Kafka 如何实现高性能？（答：Kafka 通过分区、副本、批量处理、异步机制和零拷贝技术实现高性能，支持每秒处理数百万条消息。）"
    ],
    "related": [
      {
        "id": "java-mq-basics",
        "kind": "extends",
        "note": "Kafka 是消息队列的高级实现，理解消息队列有助于掌握 Kafka 的核心概念"
      },
      {
        "id": "java-rocketmq",
        "kind": "compare",
        "note": "两者都是高性能消息中间件，对比它们的原理有助于理解消息系统的设计差异"
      },
      {
        "id": "java-realtime-push",
        "kind": "prereq",
        "note": "Kafka 是一种消息队列，可作为实时推送的底层消息传输机制"
      }
    ],
    "diagram": null
  },
  {
    "id": "java-rabbitmq",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "消息队列"
    ],
    "tags": [
      "面试",
      "消息队列"
    ],
    "title": "RabbitMQ 是什么？",
    "oneLine": "RabbitMQ 是基于 AMQP 协议的开源消息中间件，用于生产者与消费者之间的消息传递和路由。",
    "analogy": "RabbitMQ 就像邮局，生产者把包裹送到邮局，邮局根据地址分发给收件人，消费者则从邮局取件。",
    "why": "RabbitMQ 的出现是为了解决系统间异步通信、解耦和流量削峰的问题。传统同步调用容易造成系统耦合和性能瓶颈，而 RabbitMQ 通过消息队列实现生产者和消费者之间的解耦，确保消息可靠传递和系统高可用。随着业务复杂度增加，RabbitMQ 的路由能力、确认机制和多协议支持使其成为分布式系统中不可或缺的组件。",
    "mechanism": [
      "RabbitMQ 是一个消息中间件，它接收生产者发送的消息，根据路由规则将消息转发给消费者。其核心是 AMQP 协议，支持多种消息协议如 AMQP 0-9-1、AMQP 1.0、MQTT 和 STOMP。",
      "生产者将消息发送到 Exchange（交换器），Exchange 根据消息头中的 RoutingKey 和绑定规则将消息路由到对应的 Queue（队列）。不同类型的 Exchange（如 direct、topic、fanout）有不同的路由策略。",
      "消息在 Queue 中暂存，等待消费者从队列中获取。消费者通过连接到 RabbitMQ 服务器并订阅队列来消费消息，消息体包含实际业务数据，而消息头用于路由和元数据。",
      "RabbitMQ 支持消息持久化和确认机制，确保消息不会丢失。消费者在处理消息时，需要手动确认（Ack）以通知 RabbitMQ 消息已被成功处理。",
      "RabbitMQ 还支持死信队列（DLX）和延迟队列，用于处理无法被正常消费的消息或需要延迟处理的消息。这些特性使得 RabbitMQ 能够应对复杂的业务场景。",
      "RabbitMQ 的高可用性依赖于 Quorum Queue 和 Streams，它们分别基于 Raft 协议和日志结构，适用于日志存储、历史回放和大量消息堆积的场景。",
      "RabbitMQ 的管理界面（Management UI）可以监控队列、连接、Channel 等状态，帮助用户实时了解系统运行情况。",
      "RabbitMQ 的插件机制允许扩展功能，如支持 MQTT、STOMP、Prometheus 监控等，使其能够适应多种业务需求。"
    ],
    "keywords": [
      "RabbitMQ",
      "AMQP协议",
      "Exchange交换机",
      "消息确认",
      "死信队列",
      "延迟队列",
      "优先级队列",
      "Quorum Queue"
    ],
    "scene": [
      "在电商系统中，订单处理使用 RabbitMQ 实现异步处理，确保下单后库存更新和物流通知不会阻塞主流程。",
      "在日志收集系统中，RabbitMQ 作为日志中间件，将日志消息分发到多个分析服务，支持日志回放和历史查询。",
      "在微服务架构中，RabbitMQ 用于服务间通信，实现服务解耦，避免直接调用带来的耦合和性能问题。"
    ],
    "interviewQ": [
      "RabbitMQ 的核心组件有哪些？（答：RabbitMQ 的核心组件包括生产者、消费者、Exchange、Queue、Broker 和 Binding。生产者发送消息到 Exchange，Exchange 根据路由规则将消息路由到 Queue，消费者从 Queue 中获取消息。）",
      "RabbitMQ 的 Exchange 有哪些类型？（答：RabbitMQ 的 Exchange 有 4 种类型：direct、fanout、topic 和 headers。每种类型有不同的路由规则，如 direct 根据 RoutingKey 和 BindingKey 完全匹配，fanout 忽略 RoutingKey，将消息分发到所有绑定队列。）",
      "RabbitMQ 如何保证消息的可靠性？（答：RabbitMQ 通过消息持久化、消费者手动 Ack 和 Publisher Confirms 机制保证消息可靠性。消息在发送前可以设置持久化标志，消费者处理完成后需手动确认，防止消息丢失。）"
    ],
    "related": [
      {
        "id": "java-mq-basics",
        "kind": "prereq",
        "note": "了解消息队列的基本概念后，才能理解 RabbitMQ 的具体实现"
      },
      {
        "id": "java-rocketmq",
        "kind": "compare",
        "note": "两者都是消息中间件，对比它们的高性能原理有助于理解消息系统的设计差异"
      }
    ],
    "diagram": {
      "kind": "arch",
      "nodes": [
        {
          "id": "prod",
          "label": "生产者",
          "x": 15,
          "y": 14,
          "w": 18
        },
        {
          "id": "ex",
          "label": "Exchange",
          "x": 50,
          "y": 14,
          "w": 22
        },
        {
          "id": "queue",
          "label": "队列",
          "x": 85,
          "y": 14,
          "w": 22
        },
        {
          "id": "cons",
          "label": "消费者",
          "x": 15,
          "y": 84,
          "w": 18
        },
        {
          "id": "mgmt",
          "label": "管理界面",
          "x": 50,
          "y": 84,
          "w": 22
        },
        {
          "id": "dlx",
          "label": "死信队列",
          "x": 85,
          "y": 84,
          "w": 22
        }
      ],
      "links": [
        {
          "from": "prod",
          "to": "ex",
          "label": "发送"
        },
        {
          "from": "ex",
          "to": "queue",
          "label": "路由"
        },
        {
          "from": "queue",
          "to": "cons",
          "label": "消费"
        },
        {
          "from": "queue",
          "to": "dlx",
          "label": "转发"
        },
        {
          "from": "ex",
          "to": "mgmt",
          "label": "监控"
        },
        {
          "from": "queue",
          "to": "mgmt",
          "label": "监控"
        }
      ],
      "frames": [
        {
          "n": "prod",
          "note": "生产者将消息发送到 Exchange，触发路由规则"
        },
        {
          "n": "ex",
          "note": "Exchange 根据 RoutingKey 和绑定规则将消息路由到 Queue"
        },
        {
          "n": "queue",
          "note": "消息在 Queue 中暂存，等待消费者获取并确认"
        },
        {
          "n": "cons",
          "note": "消费者手动确认消息，确保处理成功"
        },
        {
          "n": "dlx",
          "note": "无法消费的消息被转发至死信队列，便于后续处理"
        },
        {
          "n": "mgmt",
          "note": "管理界面监控队列、连接状态，支持插件扩展"
        }
      ]
    }
  },
  {
    "id": "java-rocketmq",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "消息队列"
    ],
    "tags": [
      "面试",
      "消息队列"
    ],
    "title": "RocketMQ 的高性能原理是什么？",
    "oneLine": "RocketMQ 通过零拷贝和顺序写实现高性能读写，确保消息高效存储和传输。",
    "analogy": "就像快递员用最短路径送快递，RocketMQ 通过优化数据传输路径，让消息快速到达目的地。",
    "why": "在分布式系统中，消息的高效传输至关重要。传统方式中，数据在传输过程中会经历多次拷贝，导致性能下降。RocketMQ 引入零拷贝技术，减少数据在内存和磁盘之间的拷贝次数，从而提升传输效率。同时，顺序写入磁盘可以充分利用磁盘的顺序读写特性，提高写入速度。这些优化使得 RocketMQ 能够在高并发场景下保持高性能。",
    "mechanism": [
      "RocketMQ 的高性能主要依赖于零拷贝技术，通过减少数据在内存和磁盘之间的拷贝次数，提升传输效率。",
      "零拷贝技术通过 mmap 映射文件和 sendfile 系统调用，避免了数据在用户空间和内核空间之间的多次拷贝，从而节省了 CPU 时间。",
      "RocketMQ 的消息存储采用顺序写入方式，将消息追加到磁盘文件的末尾，充分利用磁盘的顺序读写特性，提高写入速度。",
      "顺序写入减少了磁盘寻址时间，使得写入操作更加高效，同时保证了消息的顺序性。",
      "RocketMQ 的消息存储机制包括 CommitLog 和 ConsumeQueue，其中 CommitLog 负责存储所有消息，而 ConsumeQueue 负责按主题和队列分组存储消息索引。",
      "CommitLog 通过顺序写入确保消息的高效存储，而 ConsumeQueue 则通过索引机制快速定位消息，提高消费效率。",
      "RocketMQ 的高性能还依赖于其异步刷盘机制，将消息写入磁盘的操作异步执行，避免阻塞主线程，提高系统吞吐量。",
      "通过零拷贝和顺序写入的结合，RocketMQ 实现了高吞吐、低延迟的高性能消息传输，适用于大规模分布式系统。"
    ],
    "keywords": [
      "零拷贝",
      "顺序写",
      "CommitLog",
      "ConsumeQueue",
      "高性能"
    ],
    "scene": [
      "在电商系统中，订单消息需要快速写入磁盘，确保交易数据的可靠性。",
      "在实时数据处理场景中，消息的高效传输是保证系统低延迟的关键。",
      "在高并发的金融系统中，消息的顺序写入和零拷贝技术确保了数据的准确性和高效性。"
    ],
    "interviewQ": [
      "RocketMQ 的零拷贝技术是如何实现的？（答：RocketMQ 通过 mmap 映射文件和 sendfile 系统调用，减少数据在内存和磁盘之间的拷贝次数，提升传输效率。）",
      "为什么 RocketMQ 采用顺序写入磁盘？（答：顺序写入充分利用磁盘的顺序读写特性，减少磁盘寻址时间，提高写入速度，并保证消息的顺序性。）",
      "RocketMQ 的 CommitLog 和 ConsumeQueue 分别负责什么？（答：CommitLog 负责存储所有消息，而 ConsumeQueue 负责按主题和队列分组存储消息索引，提高消费效率。）"
    ],
    "related": [
      {
        "id": "java-kafka",
        "kind": "compare",
        "note": "两者都是高性能消息中间件，对比它们的原理有助于理解消息系统的设计差异"
      },
      {
        "id": "java-mq-basics",
        "kind": "prereq",
        "note": "掌握消息队列的基本概念后，才能理解 RocketMQ 的具体实现"
      },
      {
        "id": "java-rabbitmq",
        "kind": "compare",
        "note": "两者都是消息中间件，对比它们的高性能原理有助于理解消息系统的设计差异"
      }
    ],
    "diagram": {
      "kind": "arch",
      "nodes": [
        {
          "id": "commitlog",
          "label": "CommitLog",
          "x": 20,
          "y": 30,
          "w": 22
        },
        {
          "id": "consumequeue",
          "label": "ConsumeQueue",
          "x": 70,
          "y": 30,
          "w": 22
        },
        {
          "id": "mmap",
          "label": "mmap 映射",
          "x": 20,
          "y": 70,
          "w": 22
        },
        {
          "id": "sendfile",
          "label": "sendfile",
          "x": 70,
          "y": 70,
          "w": 22
        },
        {
          "id": "os",
          "label": "操作系统",
          "x": 50,
          "y": 14,
          "w": 22
        }
      ],
      "links": [
        {
          "from": "os",
          "to": "mmap",
          "label": "mmap"
        },
        {
          "from": "os",
          "to": "sendfile",
          "label": "sendfile"
        },
        {
          "from": "mmap",
          "to": "commitlog",
          "label": "顺序写入"
        },
        {
          "from": "sendfile",
          "to": "commitlog",
          "label": "零拷贝"
        },
        {
          "from": "commitlog",
          "to": "consumequeue",
          "label": "索引存储"
        },
        {
          "from": "consumequeue",
          "to": "os",
          "label": "快速定位"
        }
      ],
      "frames": [
        {
          "n": "commitlog",
          "note": "顺序写入磁盘，减少寻址时间，提升写入效率"
        },
        {
          "n": "consumequeue",
          "note": "按主题分组存储索引，快速定位消息位置"
        },
        {
          "n": "mmap",
          "note": "内存映射文件，减少数据拷贝次数，提升读写效率"
        },
        {
          "n": "sendfile",
          "note": "系统调用实现零拷贝，避免用户与内核空间数据复制"
        }
      ]
    }
  },
  {
    "id": "java-rate-limit",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "高可用"
    ],
    "tags": [
      "面试",
      "高可用"
    ],
    "title": "什么是limit-request？",
    "oneLine": "limit-request 是一种限流策略，用于控制单位时间内请求的处理速率，防止系统过载。",
    "analogy": "就像在超市门口设置排队人数限制，确保每个人都能有序购物，避免拥挤导致混乱。",
    "why": "在高并发场景下，系统处理能力有限，若请求量超过系统负载，可能导致服务崩溃或响应延迟。limit-request 通过控制请求速率，确保系统稳定运行，同时平衡用户体验与系统性能。传统方法如固定窗口算法存在突发流量问题，而 limit-request 提供更平滑的限流机制，避免资源浪费和用户体验下降。",
    "mechanism": [
      "limit-request 是一种基于令牌桶算法的限流策略，通过动态生成令牌来控制请求速率，允许短时突发流量，同时保持整体速率稳定。",
      "系统初始化一个令牌桶，桶的容量和令牌生成速率由配置决定，令牌桶会按照设定速率持续生成令牌。",
      "当请求到达时，系统会尝试从令牌桶中获取一个令牌，若桶中有令牌，则允许请求通过，并减少桶中令牌数量；若桶中无令牌，则拒绝请求。",
      "令牌桶的容量决定了系统可以处理的突发流量，而令牌生成速率决定了系统的平均处理能力，两者共同作用实现限流控制。",
      "当请求量超过令牌生成速率时，桶会逐渐填满，多余的请求会被丢弃，避免系统过载。",
      "若请求量低于令牌生成速率，桶中令牌会逐渐累积，系统可以处理更多请求，提高资源利用率。",
      "limit-request 通过动态调整令牌生成速率和桶容量，适应不同场景下的流量波动，确保系统稳定运行。",
      "在分布式系统中，limit-request 需要配合 Redis 或其他分布式协调工具，确保多个实例共享限流状态，实现全局限流控制。"
    ],
    "keywords": [
      "令牌桶算法",
      "限流",
      "分布式限流",
      "Guava RateLimiter",
      "Redisson"
    ],
    "scene": [
      "在电商秒杀活动中，limit-request 用于控制接口的访问频率，防止短时间内大量请求导致数据库崩溃。",
      "在 API 网关中，limit-request 用于限制第三方调用者的请求速率，确保系统资源合理分配。",
      "在微服务架构中，limit-request 用于控制服务之间的调用频率，避免因服务雪崩导致整体系统瘫痪。"
    ],
    "interviewQ": [
      "limit-request 与固定窗口算法有何区别？（答：limit-request 基于令牌桶算法，允许短时突发流量，而固定窗口算法在窗口边界存在突刺问题。）",
      "如何实现分布式限流？（答：通过 Redis 或 Redisson 等工具实现令牌桶算法，确保多个实例共享限流状态。）",
      "limit-request 的令牌桶容量如何影响系统性能？（答：容量越大，允许的突发流量越高，但可能增加系统负载；容量越小，限流更严格，但可能影响用户体验。）"
    ],
    "related": [
      {
        "id": "java-idempotency",
        "kind": "compare",
        "note": "两者都是系统限流与安全设计的手段，对比它们的原理有助于理解系统保护机制"
      },
      {
        "id": "java-timeout-retry",
        "kind": "compare",
        "note": "两者都是系统容错与安全设计的手段，对比它们的原理有助于理解系统保护机制"
      },
      {
        "id": "java-circuit-breaker",
        "kind": "compare",
        "note": "熔断和限流都是流量控制手段，熔断更关注异常时的断路，限流则控制请求速率。"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "初始化令牌桶",
        "请求到达",
        "令牌分配",
        "处理或拒绝"
      ],
      "frames": [
        {
          "s": 0,
          "note": "初始化令牌桶时需配置容量和生成速率，决定系统突发流量和平均处理能力。"
        },
        {
          "s": 1,
          "note": "请求到达时系统检查令牌桶是否有可用令牌，若无则直接拒绝，避免系统过载。"
        },
        {
          "s": 2,
          "note": "令牌分配后，系统减少桶中令牌数量，允许请求通过，同时保持整体速率稳定。"
        },
        {
          "s": 3,
          "note": "当请求量超过生成速率，桶逐渐填满，多余请求被丢弃；若请求量低，令牌累积，提升资源利用率。"
        }
      ]
    }
  },
  {
    "id": "java-idempotency",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "高可用"
    ],
    "tags": [
      "面试",
      "高可用"
    ],
    "title": "什么是接口幂等性？",
    "oneLine": "接口幂等性指多次相同请求对服务端资源产生的效果与执行一次相同，避免重复操作导致数据异常。",
    "analogy": "就像去银行取钱，无论取多少次，账户余额不会变，取一次和取十次结果一样。",
    "why": "在高并发或网络不稳定时，用户可能重复提交请求，如多次点击付款按钮。若未保证幂等性，可能导致重复扣款、库存超卖等严重问题。因此，幂等性是保障数据一致性和业务安全的关键。此外，重复请求可能由客户端刷新、网关重试、消息重复投递等触发，这些场景下都需要服务端具备幂等性处理能力，以避免数据不一致和业务逻辑错误。",
    "mechanism": [
      "幂等性本质是保证多次相同请求对系统资源的修改效果与执行一次相同，避免重复操作导致数据异常。例如，支付接口无论执行多少次，都应确保账户只扣一次款。",
      "前端通过按钮置灰减少重复提交，但无法完全防止重复请求，需服务端配合处理幂等性。用户可能刷新页面、绕过前端，或由网关超时重试触发重复调用，因此幂等性边界必须放在服务端。",
      "服务端常用唯一键、唯一索引、去重表、状态机等技术实现幂等，确保重复请求不会导致数据错误。例如，订单创建时使用唯一索引，防止重复插入相同订单。",
      "唯一索引通过数据库约束保证数据唯一性，插入重复数据时抛出异常，程序捕获后可返回已有结果。例如，订单号字段设置唯一索引，重复创建订单时会抛出唯一约束异常。",
      "去重表记录请求信息，通过唯一索引判断是否重复，若插入成功则执行业务逻辑，否则直接返回。例如，支付回调时记录交易流水号，防止同一笔交易被重复处理。",
      "状态机通过定义业务状态流转规则，防止重复操作或状态回退，如订单支付后不再允许重复支付，避免状态回退导致的业务混乱。",
      "分布式锁通过加锁保证同一时刻只有一个请求能执行，但需结合业务判断防止重复操作。例如，库存扣减时加锁，防止多个请求同时扣减导致超卖。",
      "Token 机制为每次请求生成唯一凭证，服务端验证 Token 后执行业务逻辑，避免重复提交。例如，表单提交时生成一次性 Token，防止重复提交相同表单。"
    ],
    "keywords": [
      "幂等键",
      "Token 机制",
      "唯一索引",
      "去重表",
      "状态机",
      "分布式锁"
    ],
    "scene": [
      "创建订单场景：订单号作为唯一键，防止重复创建订单，确保订单数据不重复。",
      "支付回调场景：使用第三方交易流水号作为唯一标识，防止重复入账，避免资金错误。",
      "库存扣减场景：通过乐观锁或唯一索引控制库存扣减，防止超卖或重复扣减。"
    ],
    "interviewQ": [
      "如何在支付回调场景中保证幂等性？（答：使用第三方交易流水号作为唯一标识，配合去重表和订单状态机，防止重复入账。）",
      "如何处理表单重复提交问题？（答：前端按钮置灰减少重复点击，服务端使用 Token 机制确保同一表单只能提交一次。）",
      "库存扣减如何保证幂等性？（答：结合乐观锁或唯一索引控制库存扣减，防止重复扣减导致超卖。）",
      "如何在订单创建场景中实现幂等性？（答：使用唯一索引确保订单号唯一，防止重复创建订单，同时配合去重表兜底。）"
    ],
    "related": [
      {
        "id": "java-rate-limit",
        "kind": "compare",
        "note": "两者都是系统限流与安全设计的手段，对比它们的原理有助于理解系统保护机制"
      },
      {
        "id": "java-timeout-retry",
        "kind": "compare",
        "note": "两者都是系统容错与安全设计的手段，对比它们的原理有助于理解系统保护机制"
      },
      {
        "id": "java-circuit-breaker",
        "kind": "compare",
        "note": "熔断和幂等性都用于保障系统稳定性，熔断防止雪崩，幂等性避免重复操作。"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "唯一索引",
          "lines": [
            "数据库约束保证唯一性",
            "插入重复数据抛异常",
            "捕获后返回已有结果"
          ]
        },
        {
          "title": "去重表",
          "lines": [
            "记录请求信息",
            "通过唯一键判断重复",
            "插入成功才执行逻辑"
          ]
        },
        {
          "title": "状态机",
          "lines": [
            "定义状态流转规则",
            "防止重复操作或回退",
            "如订单支付后禁止重复支付"
          ]
        }
      ],
      "frames": [
        {
          "note": "唯一索引适用于订单创建等需要保证数据唯一性的场景",
          "active": [
            0
          ]
        },
        {
          "note": "去重表适合支付回调等需要防止重复处理的场景",
          "active": [
            1
          ]
        },
        {
          "note": "状态机适用于订单支付等需要控制状态流转的业务场景",
          "active": [
            2
          ]
        }
      ]
    }
  },
  {
    "id": "java-timeout-retry",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "高可用"
    ],
    "tags": [
      "面试",
      "高可用"
    ],
    "title": "如何正确设置超时和重试机制？",
    "oneLine": "超时机制用于控制请求等待时间，重试机制用于处理瞬态故障，两者结合提升系统可用性。",
    "analogy": "就像在餐厅等餐，如果太久没上菜就离开（超时），如果服务员失误就重新点一次（重试）。",
    "why": "没有超时机制会导致请求堆积和资源浪费，没有重试机制则无法应对瞬态故障。两者结合可以避免系统崩溃，同时防止重试风暴和雪崩效应。超时机制释放资源，重试机制提升成功率，但需合理配置避免过度消耗。",
    "mechanism": [
      "超时机制是指当请求超过指定时间未处理时，主动取消请求并抛出异常，防止资源浪费。连接超时和读取超时是两种常见类型，分别对应建立连接和接收响应的等待时间。",
      "重试机制是对同一业务意图再次发起调用，用于处理瞬态故障和偶然性故障。重试需配合超时机制，避免因请求失败而无限等待，同时防止重试风暴导致系统崩溃。",
      "指数退避重试是重试策略之一，每次重试间隔呈指数增长（如1s、2s、4s），避免多个客户端同步重试，减少对下游系统的压力。配合随机抖动（Jitter）可进一步打散重试时间。",
      "重试次数不宜过多，通常在线同步请求重试1-3次，异步任务可更多。重试需区分可重试错误（如连接超时、502/503/504）和不可重试错误（如参数错误、权限失败），避免资源浪费。",
      "超时时间应根据业务场景和网络环境设置，读取超时建议根据P99/P999延迟和SLO设置，连接超时需区分同机房和跨地域调用。下游超时应小于上游超时，预留网络和处理时间。",
      "超时和重试需与熔断、限流组合使用，避免下游持续异常时重试放大故障。熔断快速失败，限流保护下游不被流量冲垮，超时释放资源，重试提升成功率。",
      "重试请求需保证幂等性，避免重复操作导致数据不一致。涉及签名、时间戳、幂等键时，需确保重试请求仍合法且可识别为同一业务操作。",
      "超时配置可动态调整，通过配置中心实现，根据系统状态和性能指标（如P99/P999延迟、超时率）优化超时值，避免固定值带来的风险。"
    ],
    "keywords": [
      "超时机制",
      "重试机制",
      "指数退避",
      "随机抖动",
      "重试风暴",
      "幂等性"
    ],
    "scene": [
      "微服务调用链中，上游服务设置超时时间小于下游超时，防止资源浪费。",
      "异步任务或MQ消费中，重试次数较多但需配合退避策略和死信队列，避免消息堆积。",
      "支付系统中，重试需配合幂等键，防止重复扣款或订单创建。"
    ],
    "interviewQ": [
      "如何设置超时时间？（答：根据P99/P999延迟、SLO和可接受的误超时率设置，结合网络环境区分同机房和跨地域调用。）",
      "重试策略有哪些？（答：固定间隔、线性退避、指数退避、带Jitter的指数退避，分布式系统推荐带Jitter的指数退避。）",
      "如何区分可重试和不可重试错误？（答：可重试错误如连接超时、502/503/504，不可重试错误如参数错误、权限失败，需配合幂等设计。）",
      "重试风暴如何避免？（答：使用指数退避和Jitter打散重试时间，限制重试次数，配合熔断和限流机制。）"
    ],
    "related": [
      {
        "id": "java-idempotency",
        "kind": "compare",
        "note": "两者都是系统容错与安全设计的手段，对比它们的原理有助于理解系统保护机制"
      },
      {
        "id": "java-rate-limit",
        "kind": "compare",
        "note": "两者都是系统限流与安全设计的手段，对比它们的原理有助于理解系统保护机制"
      },
      {
        "id": "java-circuit-breaker",
        "kind": "extends",
        "note": "理解超时和重试机制后，才能知道熔断如何配合这些机制防止系统崩溃。"
      }
    ],
    "diagram": {
      "kind": "arch",
      "nodes": [
        {
          "id": "client",
          "label": "客户端",
          "x": 20,
          "y": 30,
          "w": 22
        },
        {
          "id": "gateway",
          "label": "网关",
          "x": 50,
          "y": 30,
          "w": 22
        },
        {
          "id": "service",
          "label": "服务",
          "x": 80,
          "y": 30,
          "w": 22
        },
        {
          "id": "db",
          "label": "数据库",
          "x": 20,
          "y": 70,
          "w": 22
        },
        {
          "id": "cache",
          "label": "缓存",
          "x": 80,
          "y": 70,
          "w": 22
        }
      ],
      "links": [
        {
          "from": "client",
          "to": "gateway",
          "label": "请求"
        },
        {
          "from": "gateway",
          "to": "service",
          "label": "转发"
        },
        {
          "from": "service",
          "to": "db",
          "label": "查询"
        },
        {
          "from": "service",
          "to": "cache",
          "label": "读取"
        },
        {
          "from": "client",
          "to": "cache",
          "label": "缓存请求"
        },
        {
          "from": "service",
          "to": "gateway",
          "label": "响应"
        }
      ],
      "frames": [
        {
          "n": "client",
          "note": "客户端发起请求，设置超时和重试策略，防止无限等待"
        },
        {
          "n": "gateway",
          "note": "网关转发请求，根据超时配置决定是否中断或重试"
        },
        {
          "n": "service",
          "note": "服务处理请求，若超时或失败，触发重试机制并检查幂等性"
        },
        {
          "n": "db",
          "note": "数据库响应延迟，若超时则释放资源，避免资源浪费"
        },
        {
          "n": "cache",
          "note": "缓存读取失败，重试时确保幂等性，避免重复操作"
        },
        {
          "n": "gateway",
          "note": "网关汇总响应，结合熔断和限流策略，保护系统稳定性"
        }
      ]
    }
  },
  {
    "id": "java-circuit-breaker",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "高可用"
    ],
    "tags": [
      "面试",
      "高可用"
    ],
    "title": "什么是服务降级与熔断？",
    "oneLine": "服务降级是系统压力大时主动关闭非核心功能，熔断是下游异常时及时断路止损。",
    "analogy": "就像堵车时先让救护车和消防车通过，再让普通车辆排队，降级是主动让路，熔断是紧急刹车防止连锁反应。",
    "why": "在微服务架构中，一个请求可能涉及多个服务调用。如果某个服务响应变慢、超时或挂掉，很容易引发雪崩效应，导致整个链路崩溃。服务降级和熔断是应对这类问题的两道防线：降级在系统压力大时主动关闭非核心功能，熔断在下游持续异常时及时断路止损，防止故障扩散，保障核心链路可用。",
    "mechanism": [
      "服务降级的本质是系统在资源紧张时主动关闭非核心功能，优先保障核心链路。比如大促时关闭推荐模块，保留下单和支付功能，确保用户能完成交易。",
      "降级触发的条件包括系统整体压力大（如CPU飙升、线程池打满）、下游服务异常（如库存服务超时）、网络链路故障或临时关闭非核心功能。这些条件共同构成了降级的触发机制，确保系统在资源紧张时能快速做出响应。",
      "降级的粒度可以粗也可以细，从关闭整个服务到仅关闭某个接口或页面区块。例如，推荐服务异常时关闭所有推荐结果，或仅关闭商品详情页中的“猜你喜欢”区域。这种灵活性使得系统能根据实际需求动态调整。",
      "降级方式包括延迟处理、页面片段降级、接口兜底降级、页面跳转降级、写降级和读降级。例如，评论后发积分可以异步处理，推荐接口异常时返回缓存数据，确保用户仍能看到内容。",
      "熔断器状态机包括Closed（关闭）、Open（打开）和Half-Open（半开）三种状态。当下游服务持续异常时，熔断器进入Open状态，阻止后续请求，防止故障扩散。在一段时间后，熔断器进入Half-Open状态，尝试少量请求测试服务是否恢复，若成功则恢复到Closed状态。",
      "熔断的触发条件包括超时降级（RT持续超过阈值）、失败降级（异常率超过阈值）、故障降级（下游返回HTTP 5xx等错误）和限流降级（QPS超过阈值）。这些条件共同构成了熔断的触发机制，确保系统在异常时能快速响应。",
      "熔断的处理方式包括返回默认值、缓存数据或降级页。例如，推荐接口异常时返回缓存数据，确保页面仍能打开。如果缓存也没命中，直接返回默认值，避免继续调用下游服务。",
      "降级开关的设计需要支持快速打开和关闭，不能依赖代码修改和发版。常见方案包括配置文件、数据库开关表、配置中心和Redis开关。生产环境推荐使用Nacos或Apollo配置中心，确保实时性和可靠性。"
    ],
    "keywords": [
      "服务降级",
      "熔断器",
      "熔断机制",
      "Fallback",
      "熔断器状态机",
      "Sentinel",
      "Hystrix",
      "Resilience4j"
    ],
    "scene": [
      "电商大促时关闭推荐模块，保留下单和支付功能，确保核心链路可用。",
      "库存服务异常时，熔断器进入Open状态，阻止后续请求，防止故障扩散。",
      "系统维护时，将用户跳转到静态维护页面，避免影响核心功能。"
    ],
    "interviewQ": [
      "降级和熔断的区别是什么？（答：降级是主动关闭非核心功能，熔断是下游异常时断路止损，防止故障扩散。）",
      "熔断器状态机有哪几种状态？（答：Closed（关闭）、Open（打开）、Half-Open（半开），通过状态切换实现故障隔离和自动恢复。）",
      "如何设计降级开关？（答：使用配置中心（如Nacos、Apollo）实现动态开关，支持快速打开和关闭，避免依赖代码修改和发版。）"
    ],
    "related": [
      {
        "id": "java-idempotency",
        "kind": "compare",
        "note": "熔断和幂等性都用于保障系统稳定性，熔断防止雪崩，幂等性避免重复操作。"
      },
      {
        "id": "java-rate-limit",
        "kind": "compare",
        "note": "熔断和限流都是流量控制手段，熔断更关注异常时的断路，限流则控制请求速率。"
      },
      {
        "id": "java-timeout-retry",
        "kind": "prereq",
        "note": "理解超时和重试机制后，才能知道熔断如何配合这些机制防止系统崩溃。"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "服务降级",
          "lines": [
            "系统压力大时关闭非核心功能",
            "保障核心链路可用性",
            "支持粗粒度或细粒度关闭",
            "处理方式包括延迟、兜底、跳转等"
          ]
        },
        {
          "title": "熔断机制",
          "lines": [
            "下游异常时及时断路止损",
            "状态机包含Closed/Open/Half-Open",
            "触发条件包括超时、失败、限流",
            "处理方式包括返回缓存或默认值"
          ]
        }
      ],
      "frames": [
        {
          "note": "服务降级与熔断是系统容错的两种核心手段，前者主动关闭非核心功能，后者在异常时断路防止扩散。",
          "active": [
            0,
            1
          ]
        },
        {
          "note": "降级开关需支持快速配置，熔断器状态机通过状态流转实现自动恢复，两者共同保障系统稳定性。",
          "active": [
            0,
            1
          ]
        }
      ]
    }
  },
  {
    "id": "java-load-balancing",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "性能优化"
    ],
    "tags": [
      "面试",
      "性能优化"
    ],
    "title": "负载均衡是什么？",
    "oneLine": "负载均衡是将用户请求分摊到多个服务器处理，提高系统并发能力和可靠性。",
    "analogy": "就像排队时，服务员会根据人数分配任务，避免某个人太忙而其他人空闲。",
    "why": "随着业务增长，单台服务器可能无法处理所有请求，导致响应变慢甚至崩溃。负载均衡通过分散请求到多台服务器，避免单点过载，同时提高系统整体的可用性和扩展性。它不会解决慢 SQL 或缓存击穿等问题，但能优化资源利用。",
    "mechanism": [
      "负载均衡是将用户请求分摊到多个服务器处理，以提高系统并发能力和可靠性，是服务端负载均衡的核心。",
      "服务端负载均衡在系统外部请求和网关层之间实现，通过软件（如 Nginx、LVS）或硬件（如 F5）完成，硬件性能强但成本高，软件成本低但性能稍弱。",
      "四层负载均衡工作在传输层（TCP/UDP），基于 IP 和端口进行请求分发，不涉及报文内容，性能高但功能有限。",
      "七层负载均衡工作在应用层（HTTP/HTTPS），基于 URL、Cookie 等内容进行路由，功能更强大，但消耗更多性能。",
      "客户端负载均衡用于系统内部服务，客户端根据负载均衡算法选择服务器，如 Spring Cloud Load Balancer 和 Dubbo。",
      "常见负载均衡算法包括随机法、轮询法、加权轮询、一致性哈希、最小连接法、最少活跃法和最快响应时间法。",
      "七层负载均衡可通过 DNS 解析和反向代理实现，DNS 解析通过轮询返回 IP，反向代理如 Nginx 将请求分配到后端服务器。",
      "负载均衡不会自动解决慢 SQL 或缓存击穿问题，但能优化资源利用，提高系统整体性能和可靠性。"
    ],
    "keywords": [
      "负载均衡",
      "四层负载均衡",
      "七层负载均衡",
      "Nginx负载均衡",
      "LVS",
      "负载均衡算法",
      "轮询",
      "一致性哈希"
    ],
    "scene": [
      "电商系统在大促期间使用 Nginx 实现七层负载均衡，根据 URL 分发请求到不同服务器。",
      "数据库集群使用 LVS 实现四层负载均衡，将 TCP 请求分发到多个数据库节点。",
      "微服务架构中，Spring Cloud Load Balancer 实现客户端负载均衡，请求在服务实例间分发。"
    ],
    "interviewQ": [
      "负载均衡为什么不能解决慢 SQL 问题？（答：负载均衡只负责请求分发，无法优化数据库查询性能，慢 SQL 仍会拖慢后端处理。）",
      "四层和七层负载均衡有什么区别？（答：四层基于 IP 和端口，七层基于 HTTP 内容，七层更灵活但性能开销更大。）",
      "一致性哈希算法解决了什么问题？（答：一致性哈希解决了服务器增减时哈希值重新分布的问题，减少数据迁移。）"
    ],
    "related": [
      {
        "id": "java-rw-split-sharding",
        "kind": "prereq",
        "note": "了解读写分离和分库分表后，才能理解负载均衡如何优化数据库访问。"
      },
      {
        "id": "java-deep-pagination",
        "kind": "compare",
        "note": "负载均衡和深度分页都涉及请求分发，但前者优化并发，后者关注查询性能。"
      },
      {
        "id": "java-sql-optimization",
        "kind": "compare",
        "note": "负载均衡和SQL优化都提升系统性能，但前者关注请求分配，后者关注查询效率。"
      }
    ],
    "diagram": null
  },
  {
    "id": "java-rw-split-sharding",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "性能优化"
    ],
    "tags": [
      "面试",
      "性能优化"
    ],
    "title": "读写分离和分库分表是什么？",
    "oneLine": "读写分离是将数据库的读操作和写操作分到不同节点，提升读扩展能力；分库分表是将数据拆分到多个数据库和表中，解决单点性能瓶颈。",
    "analogy": "读写分离就像在超市收银台，写操作是收银员，读操作是自助收银机；分库分表就像把商品分到不同货架，方便快速取货。",
    "why": "随着业务增长，单数据库可能面临读写性能瓶颈。读写分离通过将读请求分摊到从库，减轻主库压力，提升并发能力；分库分表通过水平或垂直拆分数据，避免单表数据过大导致查询变慢，提高系统扩展性。两者结合可应对高并发、大数据量场景下的性能挑战。",
    "mechanism": [
      "读写分离是将数据库的读操作和写操作分到不同节点，写请求进入主库，读请求分摊到从库，提升数据库读扩展能力。主从复制是实现读写分离的基础，通过主库将数据变化记录到binlog，从库同步这些变化。",
      "主从复制依赖binlog记录数据变化，主库将binlog发送给从库，从库通过I/O线程接收并写入relay log，再由applier线程执行relay log中的事件。主库和从库之间的同步延迟可能导致数据不一致，需通过强制读主库或等待从库追上位点解决。",
      "读写分离实现方式包括代理方式和组件方式。代理方式如MySQL Router、ProxySQL，通过中间件路由读写请求；组件方式如ShardingSphere-JDBC，直接在应用层处理读写分离，减少中间件依赖。",
      "分库分表分为垂直分库和水平分表。垂直分库按业务拆分，如订单库、用户库；水平分表按数据行拆分，如订单表按用户ID分片。分片键选择需考虑查询频率和分布均匀性，避免热点问题。",
      "分库分表后需处理跨库查询、分布式事务和ID生成问题。跨库查询可通过分库分表中间件或应用层处理；分布式事务使用两阶段提交或最终一致性方案；分布式ID需保证全局唯一性，如Snowflake算法。",
      "分库分表后需注意主从延迟和慢SQL问题。主从延迟可通过优化从库性能、减少从库数量、使用半同步复制解决；慢SQL需通过索引优化、查询重构和缓存减少对从库的影响。",
      "分库分表后需治理慢SQL、索引、连接池和报表流量，避免从库性能下降。同时，读写分离后仍需确保强一致性读请求路由到主库，避免数据不一致问题。"
    ],
    "keywords": [
      "读写分离",
      "分库分表",
      "主从复制",
      "水平分表",
      "垂直分库",
      "ShardingSphere",
      "MyCat",
      "分布式ID"
    ],
    "scene": [
      "电商系统订单表分库分表，按用户ID分片，提升查询性能。",
      "支付系统使用读写分离，支付后立即查询余额强制读主库。",
      "日志系统使用分库分表，按时间范围分片，避免单表数据过大。"
    ],
    "interviewQ": [
      "读写分离和分库分表的区别是什么？（答：读写分离是将读写操作分到不同节点，提升读扩展能力；分库分表是将数据拆分到多个数据库和表中，解决单点性能瓶颈。）",
      "如何避免读写分离中读到从库旧数据？（答：强制读主库、等待从库追上位点、延迟读取，但需根据业务场景选择合适方案。）",
      "分库分表后如何处理跨库查询？（答：使用分库分表中间件或应用层处理，通过分片键路由查询，避免全表扫描。）"
    ],
    "related": [
      {
        "id": "java-load-balancing",
        "kind": "prereq",
        "note": "了解负载均衡后，才能理解如何通过分库分表优化数据库性能。"
      },
      {
        "id": "java-deep-pagination",
        "kind": "compare",
        "note": "分库分表和深度分页都涉及数据分片，但前者优化查询，后者关注分页性能。"
      },
      {
        "id": "java-sql-optimization",
        "kind": "compare",
        "note": "分库分表和SQL优化都提升数据库性能，但前者关注数据分布，后者关注查询效率。"
      }
    ],
    "diagram": {
      "kind": "arch",
      "nodes": [
        {
          "id": "app",
          "label": "应用层",
          "x": 20,
          "y": 14,
          "w": 22
        },
        {
          "id": "db",
          "label": "数据库",
          "x": 50,
          "y": 14,
          "w": 22
        },
        {
          "id": "shard",
          "label": "分片中间件",
          "x": 80,
          "y": 14,
          "w": 22
        },
        {
          "id": "master",
          "label": "主库",
          "x": 20,
          "y": 50,
          "w": 22
        },
        {
          "id": "slave",
          "label": "从库",
          "x": 80,
          "y": 50,
          "w": 22
        },
        {
          "id": "cache",
          "label": "缓存",
          "x": 50,
          "y": 84,
          "w": 22
        }
      ],
      "links": [
        {
          "from": "app",
          "to": "shard",
          "label": "路由"
        },
        {
          "from": "shard",
          "to": "master",
          "label": "写入"
        },
        {
          "from": "shard",
          "to": "slave",
          "label": "读取"
        },
        {
          "from": "master",
          "to": "slave",
          "label": "同步"
        },
        {
          "from": "app",
          "to": "cache",
          "label": "缓存"
        }
      ],
      "frames": [
        {
          "n": "app",
          "note": "应用层通过分片中间件路由读写请求，减少中间件依赖"
        },
        {
          "n": "shard",
          "note": "分片中间件将写请求转发至主库，读请求分发至从库"
        },
        {
          "n": "master",
          "note": "主库通过binlog同步数据变化至从库，保障数据一致性"
        },
        {
          "n": "slave",
          "note": "从库处理读请求，缓解主库压力，提升读扩展能力"
        },
        {
          "n": "cache",
          "note": "缓存热点数据，减少对从库的查询压力，提升响应速度"
        }
      ]
    }
  },
  {
    "id": "java-deep-pagination",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "性能优化"
    ],
    "tags": [
      "面试",
      "性能优化"
    ],
    "title": "MySQL 在无法利用索引的情况下跳过1000000条记录后，再获取10条记录",
    "oneLine": "深度分页查询性能下降，因MySQL需扫描大量记录且无法利用索引，导致效率低下。",
    "analogy": "就像在图书馆里找第100万本书，却要从头翻到第100万页才能拿到第100万零10页的书。",
    "why": "深度分页查询性能下降的根本原因在于MySQL的执行机制：对于LIMIT offset, N，MySQL并非直接跳到offset处，而是必须从头扫描offset + N条记录。如果查询依赖二级索引且不满足覆盖索引，这意味着MySQL需要对前offset条记录执行毫无意义的回表查询（产生海量的随机I/O），最后再将这些辛苦查出的数据丢弃。即便优化器最终因代价过高退化为全表扫描，顺序扫描百万行的成本依然",
    "mechanism": [
      "深度分页的核心问题是MySQL无法直接跳过大量记录，而是必须扫描offset + N条记录，导致性能下降。",
      "当查询使用二级索引但不满足覆盖索引时，MySQL需要对前offset条记录执行回表操作，产生大量随机I/O，影响查询效率。",
      "MySQL的查询优化器基于成本选择执行计划，如果偏移量过大，优化器可能放弃索引选择全表扫描，导致性能进一步下降。",
      "使用覆盖索引可以避免回表操作，直接从索引中获取所需字段，减少随机I/O，提升查询效率。",
      "延迟关联和子查询的优化思路是将LIMIT操作转移到主键索引上，减少回表次数，提升查询性能。",
      "游标分页通过记录上一页最后一条记录的ID，使用WHERE id > last_id LIMIT n获取下一页数据，避免扫描大量记录。",
      "在复杂过滤场景中，使用联合索引（如status, id）实现覆盖索引扫描，可以高效跳过前100万条符合条件的记录。",
      "深度分页优化方案的选择需结合业务形态，如信息流推荐使用游标分页，后台列表使用延迟关联或子查询。"
    ],
    "keywords": [
      "深度分页",
      "分页优化",
      "LIMIT优化",
      "MySQL分页",
      "延迟关联",
      "覆盖索引"
    ],
    "scene": [
      "信息流推荐系统需要按时间或热度排序，但用户无法跳页，适合使用游标分页。",
      "后台管理系统需要跳页和精确总数，适合使用延迟关联或子查询。",
      "订单列表需要按时间排序，但用户只能加载更多，适合使用游标分页。"
    ],
    "interviewQ": [
      "为什么深度分页会导致性能下降？（答：MySQL必须扫描offset + N条记录，无法直接跳过，导致大量回表操作和随机I/O。）",
      "如何优化深度分页查询？（答：使用游标分页、延迟关联、子查询或覆盖索引，减少回表操作和扫描量。）",
      "延迟关联和子查询的区别是什么？（答：延迟关联通过INNER JOIN将分页转移到主键索引，减少回表；子查询先获取起始ID再过滤，但可能产生临时表。）"
    ],
    "related": [
      {
        "id": "java-sql-optimization",
        "kind": "prereq",
        "note": "了解SQL优化后，才能理解深度分页为何会导致性能下降。"
      },
      {
        "id": "java-load-balancing",
        "kind": "compare",
        "note": "深度分页和负载均衡都涉及请求分发，但前者关注分页性能，后者关注并发能力。"
      },
      {
        "id": "java-rw-split-sharding",
        "kind": "compare",
        "note": "深度分页和分库分表都涉及数据分片，但前者关注查询性能，后者关注数据分布。"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "跳过偏移量",
        "执行查询",
        "获取结果"
      ],
      "frames": [
        {
          "s": 0,
          "note": "跳过偏移量时，MySQL需扫描offset + N条记录，无法利用索引，导致性能下降。"
        },
        {
          "s": 1,
          "note": "若使用二级索引但不满足覆盖索引，需对前offset条记录执行回表操作，产生大量随机I/O。"
        },
        {
          "s": 2,
          "note": "最终获取10条记录时，若优化器放弃索引选择全表扫描，性能进一步下降，需依赖覆盖索引或游标分页优化。"
        }
      ]
    }
  },
  {
    "id": "java-sql-optimization",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "性能优化"
    ],
    "tags": [
      "面试",
      "性能优化"
    ],
    "title": "反例在SQL优化中的作用",
    "oneLine": "反例是SQL优化中避免错误做法的典型案例，帮助识别常见误区。",
    "analogy": "就像在超市购物时，反例是那些被证明无效的购物方式，比如盲目抢购打折商品反而浪费时间。",
    "why": "反例在SQL优化中非常重要，因为它们揭示了那些看似合理却实际无效的做法。例如，直接使用SELECT *会导致不必要的I/O开销，而盲目添加索引可能反而降低性能。通过反例，我们可以避免重复犯错，提高优化效率。反例的存在提醒我们，优化不能只依赖经验，而应基于实际分析和测试。反例的识别和分析是优化过程中不可或缺的一环，有助于开发者更深入理解查询性能问题。",
    "mechanism": [
      "反例是SQL优化中常见的错误做法，比如使用SELECT *，它会增加I/O、网络传输和内存开销，尤其在处理大字段如varchar、blob、text时更为明显。",
      "反例的出现往往是因为开发者没有深入分析查询性能，而是依赖经验或规则，导致优化效果不佳。例如，直接添加索引可能反而降低性能，因为索引维护成本高，且可能影响写入速度。",
      "反例的识别需要结合执行计划和实际数据，比如通过EXPLAIN分析查询是否使用了索引，是否出现了全表扫描、回表、临时表或文件排序。",
      "反例的处理应基于具体场景，例如在跨服务查询或未来需要分库分表时，应避免复杂Join，而是采用分页或冗余字段。",
      "反例的优化策略包括改写SQL、调整索引、使用缓存或搜索引擎，而不是简单地依赖规则。例如，使用范围查询代替LIMIT offset, size可以有效解决深度分页问题。",
      "反例的验证需要实际测试，确保优化后的查询在真实数据量和条件下表现良好，而不仅仅是在小数据集上验证。",
      "反例的避免需要结合业务需求和系统架构，例如在高并发场景中，外键和级联可能增加耦合和迁移成本，应优先在应用层处理。"
    ],
    "keywords": [
      "SELECT *",
      "复杂Join",
      "深度分页",
      "外键",
      "字段类型",
      "索引优化"
    ],
    "scene": [
      "在高并发电商系统中，使用SELECT *会导致大量I/O开销，影响查询性能。",
      "跨服务查询时，复杂Join可能引发跨节点查询、合并和排序，增加延迟。",
      "分页查询时，深度分页可能导致全表扫描，影响响应时间。"
    ],
    "interviewQ": [
      "追问1：为什么不能直接使用SELECT *？（答：SELECT *会增加I/O、网络传输和内存开销，尤其在处理大字段时更为明显。）",
      "追问2：如何处理复杂Join？（答：复杂Join应结合业务场景，如字段类型一致、索引合适、数据量可控时使用，否则应拆分查询并在应用层组装。）",
      "追问3：深度分页如何优化？（答：深度分页可通过范围查询、子查询、延迟关联或覆盖索引优化，避免全表扫描和回表。）",
      "追问4：外键在高并发场景下是否适用？（答：外键在高并发和分库分表场景下可能增加耦合和迁移成本，应优先在应用层处理。）"
    ],
    "related": [
      {
        "id": "java-deep-pagination",
        "kind": "prereq",
        "note": "了解深度分页的性能问题后，才能理解SQL优化中反例的作用。"
      },
      {
        "id": "java-load-balancing",
        "kind": "compare",
        "note": "SQL优化和负载均衡都提升系统性能，但前者关注查询效率，后者关注请求分配。"
      },
      {
        "id": "java-rw-split-sharding",
        "kind": "compare",
        "note": "SQL优化和分库分表都提升数据库性能，但前者关注查询效率，后者关注数据分布。"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "反例",
          "lines": [
            "SELECT * 增加I/O与网络开销",
            "复杂Join引发跨节点查询",
            "深度分页导致全表扫描"
          ]
        },
        {
          "title": "正例",
          "lines": [
            "改写SQL减少数据传输",
            "使用分页或冗余字段",
            "优化索引避免回表"
          ]
        }
      ],
      "frames": [
        {
          "note": "反例中SELECT *会增加I/O、网络和内存开销，尤其在处理大字段时更明显。",
          "active": [
            0
          ]
        },
        {
          "note": "正例通过改写SQL减少数据传输，例如使用分页或冗余字段替代复杂Join。",
          "active": [
            1
          ]
        },
        {
          "note": "反例的验证需实际测试，确保优化后的查询在真实数据量和条件下表现良好。",
          "active": [
            0,
            1
          ]
        }
      ]
    }
  },
  {
    "id": "java-cold-hot-separation",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "性能优化"
    ],
    "tags": [
      "面试",
      "性能优化"
    ],
    "title": "什么是数据冷热分离？",
    "oneLine": "数据冷热分离是根据访问频率和业务重要性，将数据划分为冷热存储，提升性能并降低成本。",
    "analogy": "就像超市将高频购买的商品放在收银台附近，低频商品放在仓库，既方便取货又节省空间。",
    "why": "随着数据量增长，存储成本和查询性能成为瓶颈。冷热分离通过分层存储，将频繁访问的数据放在高性能介质，减少查询延迟；将低频数据迁移到低成本介质，降低存储开销。同时，满足合规要求，如金融行业需长期归档数据，冷热分离可兼顾成本和合规性。",
    "mechanism": [
      "数据冷热分离是根据数据的访问频率和业务重要性，将数据划分为冷热存储，分别存储在不同性能和成本的介质中，以提升查询性能并降低成本。",
      "热数据存储在高性能介质（如 SSD、内存）中，保障核心业务的响应速度；冷数据迁移至低成本介质（如 HDD、对象存储），大幅削减存储开支。",
      "冷热数据的区分主要通过时间维度和访问频率两种方式。时间维度适用于数据访问频率与时间强相关的场景，如订单、日志等；访问频率适用于数据价值与时间无关的场景，如文章、商品等。",
      "实际落地时，冷热分离采用多级分层策略，如热数据、温数据、冷数据和归档数据，分别对应不同的存储介质和访问延迟。",
      "冷数据被访问时，可通过缓存层加速查询，避免直接访问冷库，同时使用布隆过滤器防止恶意查询穿透。",
      "冷数据迁移需保证数据一致性，通过状态标记和幂等迁移方案，确保迁移过程中的数据完整性。",
      "冷热分离的实现方式包括业务层代码实现、任务调度迁移和 Binlog 监听迁移，其中任务调度迁移是最常用的方案，适合时间维度区分场景。",
      "冷热分离的优缺点包括提升性能、降低成本，但也增加了系统复杂性和跨库查询效率的挑战，需在实际项目中权衡取舍。"
    ],
    "keywords": [
      "数据冷热分离",
      "冷数据迁移",
      "冷数据存储",
      "分层存储",
      "TiDB冷热分离",
      "HBase",
      "数据归档",
      "存储成本优化"
    ],
    "scene": [
      "订单系统将90天前的订单数据标记为冷数据，迁移至对象存储以降低存储成本。",
      "内容系统将浏览量低于阈值的文章标记为冷数据，存储在低成本介质中。",
      "金融行业将超过3年的订单数据归档至磁带库，满足合规要求并降低存储成本。"
    ],
    "interviewQ": [
      "冷热分离如何保证数据一致性？（答：通过状态标记和幂等迁移方案，确保迁移过程中的数据完整性。）",
      "冷数据被访问后如何处理？（答：采用不回迁+缓存层方案，缓存未命中时查冷库并写入缓存，同时使用布隆过滤器防止恶意查询穿透。）",
      "冷热分离的多级分层策略有哪些？（答：热数据、温数据、冷数据和归档数据，分别对应不同的存储介质和访问延迟。）"
    ],
    "related": [],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "热数据存储",
          "lines": [
            "存储在 SSD/内存中",
            "保障核心业务响应速度",
            "访问频率高，价值高",
            "适合订单、日志等场景"
          ]
        },
        {
          "title": "冷数据存储",
          "lines": [
            "存储在 HDD/对象存储中",
            "降低存储成本",
            "访问频率低，价值低",
            "适合文章、商品等场景"
          ]
        },
        {
          "title": "冷热分离策略",
          "lines": [
            "多级分层：热/温/冷/归档",
            "时间维度区分：如90天前订单",
            "访问频率区分：如浏览量低于阈值",
            "需保证数据一致性与迁移安全"
          ]
        }
      ],
      "frames": [
        {
          "note": "热数据存储在高性能介质中，保障核心业务的响应速度，适用于订单、日志等访问频率高的场景。",
          "active": [
            0
          ]
        },
        {
          "note": "冷数据迁移至低成本介质，如对象存储，大幅削减存储开支，适用于文章、商品等访问频率低的场景。",
          "active": [
            1
          ]
        },
        {
          "note": "冷热分离采用多级分层策略，如热/温/冷/归档，结合时间维度和访问频率区分，需确保数据一致性与迁移安全。",
          "active": [
            2
          ]
        }
      ]
    }
  },
  {
    "id": "java-spring-ioc-aop",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Spring"
    ],
    "tags": [
      "面试",
      "Spring"
    ],
    "title": "IoC 和 AOP 是什么？",
    "oneLine": "IoC 是控制反转，将对象创建和管理交给容器；AOP 是面向切面编程，将横切关注点与业务逻辑分离。",
    "analogy": "IoC 像是把做菜的步骤交给厨师，你只需要点菜；AOP 像是把调味的过程统一处理，让每道菜都自动加盐。",
    "why": "IoC 解决了对象之间耦合度高、管理复杂的问题，让开发更灵活；AOP 解决了横切关注点分散在多个类中的问题，提高代码复用性和可维护性。传统方式需要在每个类中重复实现日志、事务等逻辑，而 AOP 将这些逻辑封装成切面，统一管理。",
    "mechanism": [
      "IoC 是控制反转，指将对象的创建和管理权交给外部容器，而不是由程序直接实例化对象。例如，使用 Spring 容器管理对象，开发人员只需从容器中获取对象，无需手动 new。",
      "IoC 通过依赖注入（DI）实现，容器在运行时将依赖对象注入到需要的类中。例如，Service 层通过容器获取 Dao 层的实现，无需手动 new，降低了耦合度。",
      "AOP 是面向切面编程，将横切关注点（如日志、事务）从核心业务逻辑中分离。例如，日志记录可以统一由切面处理，而无需在每个方法中重复编写日志代码。",
      "AOP 通过动态代理实现，Spring AOP 使用 JDK Proxy 或 CGLIB 代理目标对象，将通知（Advice）织入到连接点（JoinPoint）中。例如，环绕通知可以在目标方法执行前后插入日志记录逻辑。",
      "AOP 的核心概念包括切面（Aspect）、连接点（JoinPoint）、切点（Pointcut）和通知（Advice）。切面封装横切关注点，切点定义哪些连接点需要增强，通知指定在哪些时刻执行增强逻辑。",
      "AOP 的实现方式包括动态代理和字节码操作。Spring AOP 基于动态代理，而 AspectJ 使用字节码操作实现更细粒度的织入。",
      "AOP 在实际应用中常用于日志记录、事务管理、权限控制等场景。例如，使用 @Transactional 注解实现事务管理，无需在每个方法中编写事务代码。"
    ],
    "keywords": [
      "IoC",
      "DI",
      "AOP",
      "动态代理",
      "切面编程",
      "横切关注点"
    ],
    "scene": [
      "在 Spring 项目中，Service 层通过容器获取 Dao 实现，无需手动 new，降低了耦合度。",
      "使用 AOP 实现日志记录，一行注解即可完成多个方法的日志记录，避免重复代码。",
      "在事务管理中，@Transactional 注解由 Spring AOP 统一处理，无需在每个方法中编写事务代码。"
    ],
    "interviewQ": [
      "IoC 和 DI 有什么区别？（答：IoC 是控制反转的思想，DI 是 IoC 的常见实现方式，用于将依赖对象注入到需要的类中。）",
      "AOP 的核心概念有哪些？（答：切面、连接点、切点、通知，这些概念共同定义了 AOP 的实现方式和逻辑。）",
      "Spring AOP 是如何实现 AOP 的？（答：Spring AOP 基于动态代理，通过 JDK Proxy 或 CGLIB 代理目标对象，将通知织入到连接点中。）"
    ],
    "related": [
      {
        "id": "java-spring-transaction",
        "kind": "prereq",
        "note": "掌握 IoC 和 AOP 后，能更清晰理解 Spring 事务如何通过 AOP 实现"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "IoC",
          "lines": [
            "将对象创建交给容器",
            "通过依赖注入实现解耦",
            "Spring 容器管理对象生命周期",
            "降低耦合度，提高可测试性"
          ]
        },
        {
          "title": "AOP",
          "lines": [
            "将横切关注点与业务逻辑分离",
            "通过动态代理实现增强",
            "支持日志、事务、权限等场景",
            "减少重复代码，提高可维护性"
          ]
        }
      ],
      "frames": [
        {
          "note": "IoC 通过容器管理对象，降低耦合度，提升灵活性",
          "active": [
            0
          ]
        },
        {
          "note": "AOP 通过动态代理实现横切关注点的统一处理，避免重复代码",
          "active": [
            1
          ]
        },
        {
          "note": "Spring AOP 使用动态代理实现事务、日志等增强功能",
          "active": [
            0,
            1
          ]
        }
      ]
    }
  },
  {
    "id": "java-spring-transaction",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "Spring"
    ],
    "tags": [
      "面试",
      "Spring"
    ],
    "title": "Spring 事务如何管理？",
    "oneLine": "Spring 事务是通过 AOP 实现的声明式事务管理，用于保证数据库操作的原子性、一致性、隔离性和持久性。",
    "analogy": "就像在超市结账时，收银员必须确保所有商品都成功付款，否则全部取消，避免部分支付导致库存错误。",
    "why": "事务管理是为了解决多个数据库操作之间的一致性问题。如果没有事务，一个操作失败可能导致数据不一致。Spring 事务通过 AOP 在方法执行前后进行事务的开启、提交或回滚，确保操作的原子性和一致性，同时避免并发访问时的数据冲突。",
    "mechanism": [
      "Spring 事务是基于 AOP 实现的声明式事务管理，通过 @Transactional 注解在方法执行前后控制事务的开启、提交和回滚。",
      "当方法被 @Transactional 注解修饰时，Spring 会创建一个代理对象，拦截方法调用并在执行前开启事务，执行后根据结果提交或回滚事务。",
      "事务的传播行为决定了多个事务方法之间的调用关系，例如 REQUIRED 表示如果当前存在事务则加入，否则新建事务。",
      "事务的隔离级别决定了多个事务并发执行时的可见性，如 DEFAULT 表示使用数据库默认的隔离级别，避免脏读、不可重复读和幻读。",
      "事务的回滚规则决定了哪些异常会触发事务回滚，例如默认情况下，只有运行时异常（如 NullPointerException）会触发回滚，检查型异常（如 IOException）不会。",
      "Spring 事务管理依赖于底层数据库的事务支持，如 MySQL 的 InnoDB 引擎支持事务，而 MyISAM 引擎不支持。",
      "事务的持久性由数据库的回滚日志（undo log）保证，即使在系统崩溃后也能通过日志恢复数据到事务执行前的状态。",
      "Spring 事务管理器（PlatformTransactionManager）根据事务定义（TransactionDefinition）的参数，如传播行为、隔离级别、超时等，管理事务的生命周期。"
    ],
    "keywords": [
      "@Transactional",
      "事务传播",
      "隔离级别",
      "回滚规则",
      "PlatformTransactionManager",
      "TransactionDefinition"
    ],
    "scene": [
      "在电商系统中，订单支付涉及多个数据库操作，如扣减库存和更新订单状态，必须使用事务保证一致性。",
      "在银行转账系统中，转账操作涉及两个账户的余额变更，必须使用事务避免出现余额不一致的问题。",
      "在日志系统中，日志写入和数据库记录必须同时成功或失败，否则可能导致数据丢失或不一致。"
    ],
    "interviewQ": [
      "Spring 事务如何实现？（答：Spring 事务通过 AOP 实现声明式事务管理，使用 @Transactional 注解控制事务的开启、提交和回滚。）",
      "事务的传播行为有哪些？（答：事务的传播行为包括 REQUIRED、REQUIRES_NEW、NEVER、SUPPORTS、MANDATORY、NOT_SUPPORTED、NEGBEAN、NEVER 等，用于控制多个事务方法之间的调用关系。）",
      "事务的隔离级别有哪些？（答：事务的隔离级别包括 DEFAULT、READ_UNCOMMITTED、READ_COMMITTED、REPEATABLE_READ、SERIALIZABLE，用于控制多个事务并发执行时的数据可见性。）"
    ],
    "related": [
      {
        "id": "java-spring-ioc-aop",
        "kind": "prereq",
        "note": "理解 IoC 和 AOP 后，能更深入掌握 Spring 事务如何通过 AOP 实现"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "添加注解",
        "创建代理",
        "执行方法",
        "提交/回滚"
      ],
      "frames": [
        {
          "s": 0,
          "note": "添加 @Transactional 注解后，Spring 会为该方法创建代理对象，用于拦截调用。"
        },
        {
          "s": 1,
          "note": "代理对象在方法执行前开启事务，通过数据库连接对象设置为只读或可提交状态。"
        },
        {
          "s": 2,
          "note": "方法执行过程中，若发生异常或明确调用 commit/rollback，事务会根据规则提交或回滚。"
        },
        {
          "s": 3,
          "note": "事务提交后，数据库的 undo log 会记录变更，确保数据持久化且可恢复。"
        }
      ]
    }
  },
  {
    "id": "java-restful-api",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "系统设计"
    ],
    "tags": [
      "面试",
      "系统设计"
    ],
    "title": "RESTful API 是什么？",
    "oneLine": "RESTful API 是基于 REST 架构的 API 设计规范，通过 HTTP 方法和统一资源标识符实现资源的增删改查。",
    "analogy": "就像快递员通过地址和快递单号找到包裹，RESTful API 通过 URL 和 HTTP 方法找到并操作资源。",
    "why": "传统 API 设计缺乏统一规范，导致接口混乱、难以维护。RESTful API 通过使用 HTTP 方法和资源路径，使接口更清晰、易于理解和使用，同时支持幂等性，提升系统稳定性和可扩展性。",
    "mechanism": [
      "RESTful API 是基于 REST 架构的 API 设计规范，通过 HTTP 方法（GET、POST、PUT、DELETE 等）和统一资源标识符（URI）操作资源，实现客户端与服务器的交互。",
      "GET 方法用于获取资源，如 `GET /classes` 获取所有班级信息，确保请求安全且幂等，不会改变服务器状态。",
      "POST 方法用于创建资源，如 `POST /classes` 新建班级，客户端通常提供完整资源数据，服务器处理并返回新资源的 URI。",
      "PUT 方法用于更新资源，如 `PUT /classes/12` 修改编号为 12 的班级，客户端提供完整资源数据，服务器替换原资源。",
      "DELETE 方法用于删除资源，如 `DELETE /classes/12` 删除编号为 12 的班级，确保操作幂等，避免重复删除问题。",
      "PATCH 方法用于部分更新资源，如 `PATCH /classes/12` 修改班级部分信息，客户端提供需要更新的属性，服务器仅修改指定字段。",
      "RESTful API 强调资源路径使用名词，如 `/classes` 表示班级集合，`/classes/12` 表示单个班级，避免使用动词，提升接口可读性和一致性。",
      "RESTful API 使用状态码（如 200、404、500）反馈请求结果，帮助客户端理解操作是否成功，提升系统健壮性。"
    ],
    "keywords": [
      "RESTful API",
      "REST",
      "HTTP方法",
      "状态码",
      "幂等性",
      "资源路径"
    ],
    "scene": [
      "电商系统中，前端通过 `GET /products` 获取商品列表，通过 `POST /orders` 创建订单。",
      "微服务架构中，服务 A 通过 `GET /users/{id}` 获取用户信息，服务 B 通过 `DELETE /users/{id}` 删除用户。",
      "API 网关中，通过 `PATCH /users/{id}` 更新用户部分信息，如修改邮箱或密码。"
    ],
    "interviewQ": [
      "RESTful API 的 HTTP 方法有哪些？（答：GET、POST、PUT、DELETE、PATCH，分别用于获取、创建、更新、删除和部分更新资源。）",
      "为什么 RESTful API 使用名词而不是动词？（答：使用名词表示资源，使接口更清晰、易于理解和维护，符合 REST 架构原则。）",
      "RESTful API 中幂等性是什么意思？（答：幂等性指多次执行相同操作结果一致，如 GET、PUT、DELETE 方法确保操作不会因重复请求导致异常。）"
    ],
    "related": [
      {
        "id": "java-jwt",
        "kind": "prereq",
        "note": "掌握 JWT 后，能更好理解 RESTful API 中如何实现身份认证"
      },
      {
        "id": "java-state-machine-workflow",
        "kind": "compare",
        "note": "RESTful API 用于接口设计，状态机用于业务逻辑，两者结合可实现完整功能"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "定义资源",
        "操作资源",
        "响应反馈"
      ],
      "frames": [
        {
          "s": 0,
          "note": "RESTful API 以资源为中心，通过 URI 标识资源，如 /classes 表示班级集合。"
        },
        {
          "s": 1,
          "note": "GET/POST/PUT/DELETE 等 HTTP 方法对应增删改查，如 POST /classes 创建新班级，返回 201 状态码。"
        },
        {
          "s": 2,
          "note": "状态码（如 200/404）反馈请求结果，确保客户端能准确判断操作是否成功。"
        }
      ]
    }
  },
  {
    "id": "java-jwt",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "系统设计"
    ],
    "tags": [
      "面试",
      "系统设计"
    ],
    "title": "JWT 是什么？",
    "oneLine": "JWT 是一种用于身份认证的紧凑格式，包含 Header、Payload 和 Signature，用于安全传输声明。",
    "analogy": "JWT 就像一张电子通行证，里面写明了你的身份和权限，别人不能随意修改，但也不能看到具体内容。",
    "why": "JWT 的出现是为了简化身份验证流程，避免服务器存储会话状态。传统 Session 需要服务器保存会话信息，而 JWT 可以让客户端存储令牌，减轻服务器压力。同时，JWT 的签名机制能防止令牌被篡改，提升安全性。",
    "mechanism": [
      "JWT 是一种紧凑的声明格式，用于在两个方之间安全传递信息，由 Header、Payload 和 Signature 三部分组成。",
      "Header 包含令牌类型和签名算法，如 HS256，经过 Base64Url 编码后成为 JWT 的第一部分。",
      "Payload 包含声明（Claims），如用户标识、过期时间等，这些声明分为注册声明、公有声明和私有声明。",
      "Signature 是根据编码后的 Header、Payload 和签名密钥计算得出，用于验证令牌是否被篡改。",
      "签名算法如 HS256 使用共享密钥，RS256 使用非对称加密，确保只有持有密钥的服务器才能验证签名。",
      "JWT 验证过程包括解析 Header 和 Payload，检查签名，并验证声明如 `exp` 和 `nbf` 是否符合要求。",
      "服务端在收到 JWT 后，会解析出 Header、Payload 和 Signature，并根据密钥重新生成签名，与原签名对比以确认令牌有效性。",
      "JWT 的签名不能加密内容，因此不能用于传输敏感信息，如密码或身份证号，这些信息应存储在服务器或加密后传输。"
    ],
    "keywords": [
      "JWT",
      "Header",
      "Payload",
      "Signature",
      "Base64Url",
      "签名算法"
    ],
    "scene": [
      "在 Web 应用中，用户登录后，服务端生成 JWT 并返回给客户端，客户端在后续请求中携带 JWT 进行身份验证。",
      "在移动端，用户登录后，服务端生成 JWT 并存储在设备中，每次请求都通过 HTTP Header 携带 JWT。",
      "在微服务架构中，JWT 用于服务间通信，确保请求来源合法，避免中间人攻击。"
    ],
    "interviewQ": [
      "JWT 和传统 Session 验证有什么区别？（答：JWT 是无状态的，客户端存储令牌，服务端不保存会话状态；Session 需要服务器存储会话信息，但支持撤销和权限变更。）",
      "JWT 的签名机制如何防止篡改？（答：签名是根据 Header、Payload 和密钥计算得出，服务端验证签名时会重新生成签名并与原签名对比，确保内容未被修改。）",
      "为什么不能将敏感信息放在 JWT 的 Payload 中？（答：Payload 是 Base64 编码的，任何人都可以解码，因此不能存储密码、身份证号等敏感信息，应加密或存储在服务器。）"
    ],
    "related": [
      {
        "id": "java-restful-api",
        "kind": "prereq",
        "note": "了解 RESTful API 后，能更清晰理解 JWT 在身份认证中的作用"
      }
    ],
    "diagram": {
      "kind": "pipeline",
      "stages": [
        "生成 JWT",
        "传输 JWT",
        "验证 JWT"
      ],
      "frames": [
        {
          "s": 0,
          "note": "生成 JWT 时需编码 Header、Payload，并用密钥生成 Signature，确保签名算法如 HS256 或 RS256 正确应用。"
        },
        {
          "s": 1,
          "note": "传输 JWT 时需通过 HTTP Header 携带，避免明文传输敏感信息，JWT 本身不加密内容，仅用于身份验证。"
        },
        {
          "s": 2,
          "note": "验证 JWT 时需解析 Header 和 Payload，检查签名是否匹配，并验证声明如 `exp` 和 `nbf` 是否在有效期内。"
        }
      ]
    }
  },
  {
    "id": "java-realtime-push",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "系统设计"
    ],
    "tags": [
      "面试",
      "系统设计"
    ],
    "title": "Web 实时消息推送方案有哪些？",
    "oneLine": "Web 实时消息推送是通过推或拉的方式，实现前端页面实时更新未读消息数，常见方案包括短轮询、长轮询、iframe 流、SSE 和 WebSocket。",
    "analogy": "就像快递员送快递，短轮询是每隔几分钟就打电话问有没有快递，长轮询是快递员一直等在门口，SSE 是快递员用快递柜实时推送快递信息，WebSocket 是快递员和你随时能通话。",
    "why": "消息推送是网站运营的重要功能，用于实时通知用户新消息。短轮询频繁请求浪费资源，长轮询减少请求次数但仍有性能问题，iframe 流不友好且效率低，SSE 和 WebSocket 提供更高效的实时通信方式，SSE 更适合单向推送，WebSocket 适合双向通信。",
    "mechanism": [
      "短轮询是客户端定时向服务器发送 HTTP 请求，服务器返回未读消息数，前端更新页面。优点是实现简单，缺点是频繁请求浪费资源。",
      "长轮询是客户端发起请求后，服务器保持连接直到有新消息或超时，再返回结果。相比短轮询，减少了请求次数，但仍有性能问题。",
      "iframe 流是通过隐藏的 iframe 标签持续请求数据，服务器保持响应并实时写入数据。实现简单，但浏览器会持续加载，用户体验差。",
      "SSE 是基于 HTTP 的服务器推送技术，客户端通过 EventSource 建立连接，服务器持续发送事件流。实现简单，适合单向推送，支持自动重连。",
      "WebSocket 是基于 TCP 的全双工通信协议，客户端和服务器可随时发送数据。适合双向通信，但实现复杂，需要协议升级。",
      "消息推送的核心是客户端与服务端的实时通信，选择方案需根据场景决定，如站内信适合 SSE，游戏适合 WebSocket。"
    ],
    "keywords": [
      "Web消息推送",
      "实时消息",
      "WebSocket",
      "SSE",
      "长轮询",
      "短轮询"
    ],
    "scene": [
      "站内信系统需要实时更新未读消息数，适合使用 SSE 或 WebSocket。",
      "监控系统需要实时推送状态变化，适合使用 WebSocket。",
      "股票行情需要实时更新价格，适合使用 SSE。"
    ],
    "interviewQ": [
      "如何选择 SSE 和 WebSocket？（答：SSE 适合单向推送，实现简单；WebSocket 适合双向通信，但实现复杂。）",
      "长轮询和短轮询的区别？（答：长轮询减少请求次数，但仍有性能问题；短轮询频繁请求，浪费资源。）",
      "SSE 的优点有哪些？（答：基于 HTTP，实现简单；支持自动重连；适合单向推送。）"
    ],
    "related": [
      {
        "id": "java-state-machine-workflow",
        "kind": "compare",
        "note": "状态机处理状态变化，推送方案处理消息传输，两者结合可实现状态同步"
      },
      {
        "id": "java-kafka",
        "kind": "extends",
        "note": "Kafka 是一种消息队列，可作为实时推送的底层消息传输机制"
      },
      {
        "id": "java-mq-basics",
        "kind": "prereq",
        "note": "了解消息队列的基本概念是选择实时推送方案的前提"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "SSE",
          "lines": [
            "基于 HTTP 的服务器推送",
            "单向通信，支持自动重连",
            "适合站内信、状态更新"
          ]
        },
        {
          "title": "WebSocket",
          "lines": [
            "全双工 TCP 协议通信",
            "双向实时交互，性能高",
            "适合游戏、股票行情"
          ]
        },
        {
          "title": "长轮询",
          "lines": [
            "服务器保持连接直到有数据",
            "减少请求次数，仍有性能问题",
            "适合简单实时场景"
          ]
        }
      ],
      "frames": [
        {
          "note": "SSE 和 WebSocket 是主流方案，SSE 适合单向推送，WebSocket 适合双向通信。",
          "active": [
            0,
            1
          ]
        },
        {
          "note": "长轮询在性能上仍有不足，适合对实时性要求不高的场景。",
          "active": [
            2
          ]
        }
      ]
    }
  },
  {
    "id": "java-state-machine-workflow",
    "domain": "Java后端",
    "category": "work",
    "subject": "java",
    "topicPath": [
      "Java后端",
      "系统设计"
    ],
    "tags": [
      "面试",
      "系统设计"
    ],
    "title": "状态机与流程编排如何选型？",
    "oneLine": "状态机用于状态变化规则，流程编排用于组织任务依赖，两者可协同解决复杂业务流程。",
    "analogy": "就像图书馆借书流程，状态机决定借书状态变化，流程编排决定哪些书可以借、如何归还。",
    "why": "业务流程常涉及多步骤、条件分支和异步操作，状态机能集中管理状态变化规则，避免状态混乱；流程编排则能组织跨任务依赖，确保正确顺序执行。两者结合可提升可维护性与可靠性，避免状态冲突和任务遗漏。状态机解决状态变化规则问题，流程编排解决任务依赖和流程组织问题，两者协同可提升系统健壮性和可扩展性。",
    "mechanism": [
      "状态机通过状态、事件、转移、守卫条件和动作定义业务状态变化规则，确保状态转换符合业务逻辑，例如售后申请从待审核到待退款的转移需满足审核记录完整和退款金额合法的条件。",
      "流程编排通过节点模板、流程定义和实例管理任务执行顺序，支持跨服务、跨请求的复杂流程组织，例如商品入库前需完成功能检测和外观拍照，由编排器决定任务执行顺序和依赖关系。",
      "状态机与流程编排结合，流程引擎调度任务，任务内部用状态机约束状态变化，实现状态与任务的解耦，例如订单支付流程中，状态机管理支付状态，流程编排组织支付、退款、审核等任务的执行顺序。",
      "状态机处理单个业务的线性或分支状态变化，流程编排处理多个任务的依赖关系和并行执行，例如售后申请中，检测和拍照任务可以并行执行，但入库任务需等待两者都完成。",
      "并行分支汇聚需幂等处理任务完成事件，避免重复操作，同时通过事务或锁机制确保条件满足后推进流程，例如检测和拍照任务完成后，编排器需确认两者都成功才能继续入库流程。",
      "任务重试需支持幂等，避免重复扣款或发货，通过唯一业务操作ID和本地事务保证执行一致性，例如退款任务超时后重试，需确保不会重复扣款，通过幂等键和本地事务保证操作唯一性。",
      "流程定义与执行实例分离，确保定义版本不可变，实例可按旧版本运行，避免版本迁移时的兼容性问题，例如流程定义发布新版本后，旧实例仍按旧版本执行，确保业务连续性。",
      "自研引擎需处理配置校验、进度持久化、版本兼容、故障恢复和资源限制，维护成本远高于节点调度，例如需支持配置发布前检查不可达节点、缺失出口、分支冲突等，确保流程可靠性。"
    ],
    "keywords": [
      "状态机",
      "FSM",
      "流程编排",
      "工作流",
      "并行网关",
      "任务幂等",
      "流程版本",
      "失败补偿"
    ],
    "scene": [
      "订单支付流程中，状态机管理支付状态，流程编排组织支付、退款、审核等任务的执行顺序。",
      "售后审核流程中，状态机管理审核状态，流程编排组织审核、退款、驳回等任务的执行顺序。",
      "商品入库流程中，状态机管理入库状态，流程编排组织检测、拍照、返工等任务的执行顺序。"
    ],
    "interviewQ": [
      "追问1：状态机与流程编排的区别是什么？（答：状态机用于管理状态变化规则，流程编排用于组织任务依赖和执行顺序，两者可协同解决复杂业务流程。）",
      "追问2：如何处理并行分支的汇聚？（答：通过幂等处理任务完成事件，结合事务或锁机制确保条件满足后推进流程，避免重复操作和无限等待。）",
      "追问3：任务重试为什么需要幂等？（答：避免重复扣款或发货，通过唯一业务操作ID和本地事务保证执行一致性，确保任务重试后不会产生重复业务影响。）",
      "追问4：自研流程引擎需要评估哪些成本？（答：需处理配置校验、进度持久化、版本兼容、故障恢复和资源限制，维护成本远高于节点调度，需评估是否值得自研。）"
    ],
    "related": [
      {
        "id": "java-restful-api",
        "kind": "compare",
        "note": "RESTful API 用于接口设计，状态机用于业务逻辑，两者结合可实现完整功能"
      },
      {
        "id": "java-realtime-push",
        "kind": "compare",
        "note": "状态机处理状态变化，推送方案处理消息传输，两者结合可实现状态同步"
      }
    ],
    "diagram": {
      "kind": "snapshot",
      "panels": [
        {
          "title": "状态机",
          "lines": [
            "定义状态转换规则",
            "支持条件守卫判断",
            "处理单业务线性分支",
            "与流程编排协同解耦"
          ]
        },
        {
          "title": "流程编排",
          "lines": [
            "组织任务执行顺序",
            "支持跨服务并行执行",
            "处理任务依赖关系",
            "提供幂等重试机制"
          ]
        }
      ],
      "frames": [
        {
          "note": "状态机适合处理单个业务的状态变化，如支付状态从待支付到已支付的转换需满足条件守卫",
          "active": [
            0
          ]
        },
        {
          "note": "流程编排适合组织多个任务的依赖关系，如检测和拍照任务可并行执行，但入库需等待两者完成",
          "active": [
            1
          ]
        },
        {
          "note": "两者结合可实现状态与任务解耦，如订单支付流程中状态机管理支付状态，编排器组织支付、退款等任务",
          "active": [
            0,
            1
          ]
        }
      ]
    }
  }
];
module.exports = CARDS_INTERVIEW_JAVA;
