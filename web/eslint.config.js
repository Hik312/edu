/* ESLint 配置（flat config，ESLint 9+ 的新格式）。
 *
 * 目标不是「把所有错都报出来」，而是**拦住那些一眼看不懂的写法**：
 *   - 一个函数 200 行 → 读的人要在本子上记状态
 *   - 五层嵌套 → 眼睛在括号里迷路
 *   - var / == → 行为跟眼睛看到的不一样
 *
 * 所以这里的规则刻意少而重：能自动修的交给 Prettier，剩下的只留人工必须改的。
 * 新增规则前先问一句「这条能不能自动修」，能的别加在这儿。
 */
import js from '@eslint/js'
import globals from 'globals'
import pluginVue from 'eslint-plugin-vue'
import prettierRecommended from 'eslint-plugin-prettier/recommended'

export default [
  // dist 是构建产物、public 是原样复制的静态资源（图标 / 种子页 / SW 清理脚本），都不归 lint 管
  { ignores: ['dist/**', 'public/**', 'node_modules/**', '*.min.js'] },

  js.configs.recommended,
  ...pluginVue.configs['flat/essential'],
  prettierRecommended,

  {
    files: ['**/*.{js,vue}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: { ...globals.browser }
    },
    rules: {
      // —— 一眼能看懂：命名、比较、变量声明 ——
      'prefer-const': 'error',
      'no-var': 'error',
      eqeqeq: ['error', 'smart'],
      'no-implicit-coercion': 'error',

      // —— 复杂度：读代码的人记不住太多状态 ——
      complexity: ['warn', 15],
      'max-depth': ['warn', 4],
      'max-nested-callbacks': ['warn', 4],
      // 700 行而不是 400：.vue 的 template + style 天然就占一半，
      // 拿 400 去卡它只会天天误报，然后所有人学会无视这条规则。
      // 到 700 才是「这个组件真的该拆了」的信号。
      'max-lines': ['warn', { max: 700, skipBlankLines: true, skipComments: true }],
      'max-params': ['warn', 5],

      // —— 不留半成品 ——
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'no-debugger': 'error',
      'no-alert': 'error',

      // —— Vue 专项 ——
      // 单文件组件名允许多词也允许单词：AppLayout 是通用的，CardView 不是组件名冲突源
      'vue/multi-word-component-names': 'off',
      // 属性顺序人工难维护，交给 Prettier 排
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      // 一个组件的 <script> 超过 300 行就该拆了，比 max-lines 宽松一点（模板占位多）
      'vue/component-api-style': ['warn', ['script-setup']]
    }
  },

  {
    // 脚本很少改动，规则放宽：这里更关心能不能跑，不是漂不漂亮
    files: ['scripts/**/*.js', 'vite.config.js', 'eslint.config.js'],
    languageOptions: { globals: { ...globals.node } },
    rules: {
      'no-console': 'off',
      'max-lines': 'off',
      complexity: 'off'
    }
  }
]
