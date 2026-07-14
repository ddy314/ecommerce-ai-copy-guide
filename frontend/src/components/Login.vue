<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

type ViewMode = 'login' | 'register' | 'forgot'
type Role = 'user' | 'merchant'

interface UserInfo {
  username: string
  role: Role
  nickname?: string
  token?: string
  [key: string]: unknown
}

const emit = defineEmits<{
  (e: 'login-success', userInfo: UserInfo): void
}>()

// 视图模式：登录 / 注册 / 找回密码
const viewMode = ref<ViewMode>('login')
// 登录身份
const role = ref<Role>('user')
const loading = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

// 记住密码
const rememberPassword = ref(false)

// 密码可见性
const showLoginPassword = ref(false)
const showRegisterPassword = ref(false)
const showRegisterConfirmPassword = ref(false)
const showForgotPassword = ref(false)
const showForgotConfirmPassword = ref(false)

// 登录表单
const loginForm = reactive({
  username: '',
  password: '',
})
const loginErrors = reactive({
  username: '',
  password: '',
})

// 页面加载时恢复记住的密码
onMounted(() => {
  const saved = localStorage.getItem('rememberedLogin')
  if (saved) {
    try {
      const data = JSON.parse(saved)
      loginForm.username = data.username || ''
      loginForm.password = data.password || ''
      role.value = data.role || 'user'
      rememberPassword.value = true
    } catch {
      localStorage.removeItem('rememberedLogin')
    }
  }
})

// 注册表单
const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  nickname: '',
})
const registerErrors = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  nickname: '',
})

// 找回密码：两步流程
const forgotStep = ref<1 | 2>(1)
const forgotForm = reactive({
  username: '',
  newPassword: '',
  confirmPassword: '',
})
const forgotErrors = reactive({
  username: '',
  newPassword: '',
  confirmPassword: '',
})

// 左侧功能特色列表
const features = [
  { icon: '文', title: 'AI 商品文案生成', desc: '一键生成标题、卖点、详情页文案和广告语，支撑商品上架与营销素材。' },
  { icon: '导', title: '智能导购推荐', desc: '根据用户预算、场景与偏好，生成可解释的推荐理由与替代方案。' },
  { icon: '评', title: '评论情感分析', desc: '提取好评词、差评痛点与可落地的商品优化建议。' },
  { icon: '播', title: '直播脚本生成', desc: '按直播节奏输出开场、讲解、互动与转化话术。' },
]

const roleTabs: { value: Role; label: string; desc: string }[] = [
  { value: 'user', label: '普通用户', desc: '浏览商品、智能导购、购物下单' },
  { value: 'merchant', label: '商家管理员', desc: '商品管理、文案生成、数据分析' },
]

// 切换视图时重置表单与提示
function switchMode(mode: ViewMode) {
  viewMode.value = mode
  errorMsg.value = ''
  successMsg.value = ''
  clearAllErrors()
  if (mode === 'forgot') {
    forgotStep.value = 1
    forgotForm.username = ''
    forgotForm.newPassword = ''
    forgotForm.confirmPassword = ''
  }
}

function switchRole(r: Role) {
  role.value = r
  errorMsg.value = ''
  if (r === 'merchant') {
    // 商家管理员不允许注册，强制切回登录
    if (viewMode.value === 'register') {
      viewMode.value = 'login'
    }
  }
}

function clearAllErrors() {
  loginErrors.username = ''
  loginErrors.password = ''
  registerErrors.username = ''
  registerErrors.password = ''
  registerErrors.confirmPassword = ''
  registerErrors.nickname = ''
  forgotErrors.username = ''
  forgotErrors.newPassword = ''
  forgotErrors.confirmPassword = ''
}

// 统一请求处理
async function request<T>(path: string, body: Record<string, unknown>): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({ message: '请求失败' }))
    throw new Error((err as { message?: string }).message || `HTTP ${response.status}`)
  }
  return response.json() as Promise<T>
}

// 校验：非空
function validateNotEmpty(value: string, field: string): string {
  return value.trim() ? '' : `${field}不能为空`
}

// 校验：密码长度 >= 6
function validatePasswordLength(value: string): string {
  if (!value) return '密码不能为空'
  return value.length >= 6 ? '' : '密码长度不能少于 6 位'
}

// 校验：两次密码一致
function validatePasswordMatch(a: string, b: string): string {
  return a === b ? '' : '两次输入的密码不一致'
}

// ---------- 登录 ----------
function validateLogin(): boolean {
  loginErrors.username = validateNotEmpty(loginForm.username, '账号')
  loginErrors.password = validateNotEmpty(loginForm.password, '密码')
  return !loginErrors.username && !loginErrors.password
}

async function handleLogin() {
  errorMsg.value = ''
  successMsg.value = ''
  if (!validateLogin()) return
  loading.value = true
  try {
    const data = await request<{
      token?: string
      access_token?: string
      user?: Record<string, unknown>
      username?: string
      nickname?: string
      role?: string
      message?: string
    }>('/api/auth/login', {
      username: loginForm.username.trim(),
      password: loginForm.password,
      role: role.value,
    })

    const token = data.token || data.access_token || ''
    const userInfo: UserInfo = {
      username: (data.user?.username as string) || data.username || loginForm.username.trim(),
      role: role.value,
      nickname: (data.user?.nickname as string) || data.nickname || loginForm.username.trim(),
      token,
      ...(data.user as Record<string, unknown> | undefined),
    }

    // 持久化
    if (token) localStorage.setItem('token', token)
    localStorage.setItem('userInfo', JSON.stringify(userInfo))

    // 记住密码处理
    if (rememberPassword.value) {
      localStorage.setItem('rememberedLogin', JSON.stringify({
        username: loginForm.username,
        password: loginForm.password,
        role: role.value,
      }))
    } else {
      localStorage.removeItem('rememberedLogin')
    }

    successMsg.value = '登录成功，正在跳转...'
    emit('login-success', userInfo)
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '登录失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

// ---------- 注册 ----------
function validateRegister(): boolean {
  registerErrors.username = validateNotEmpty(registerForm.username, '账号')
  registerErrors.nickname = validateNotEmpty(registerForm.nickname, '昵称')
  registerErrors.password = validatePasswordLength(registerForm.password)
  registerErrors.confirmPassword = validatePasswordMatch(
    registerForm.password,
    registerForm.confirmPassword,
  )
  if (!registerErrors.confirmPassword && !registerForm.confirmPassword) {
    registerErrors.confirmPassword = '请确认密码'
  }
  return (
    !registerErrors.username &&
    !registerErrors.nickname &&
    !registerErrors.password &&
    !registerErrors.confirmPassword
  )
}

async function handleRegister() {
  errorMsg.value = ''
  successMsg.value = ''
  if (!validateRegister()) return
  loading.value = true
  try {
    await request('/api/auth/register', {
      username: registerForm.username.trim(),
      password: registerForm.password,
      nickname: registerForm.nickname.trim(),
    })
    successMsg.value = '注册成功，请使用新账号登录'
    // 自动填充登录账号
    loginForm.username = registerForm.username.trim()
    loginForm.password = ''
    viewMode.value = 'login'
    // 清空注册表单
    registerForm.username = ''
    registerForm.password = ''
    registerForm.confirmPassword = ''
    registerForm.nickname = ''
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '注册失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

// ---------- 找回密码 ----------
function validateForgotStep1(): boolean {
  forgotErrors.username = validateNotEmpty(forgotForm.username, '账号')
  return !forgotErrors.username
}

function validateForgotStep2(): boolean {
  forgotErrors.newPassword = validatePasswordLength(forgotForm.newPassword)
  forgotErrors.confirmPassword = validatePasswordMatch(
    forgotForm.newPassword,
    forgotForm.confirmPassword,
  )
  if (!forgotErrors.confirmPassword && !forgotForm.confirmPassword) {
    forgotErrors.confirmPassword = '请确认新密码'
  }
  return !forgotErrors.newPassword && !forgotErrors.confirmPassword
}

// 第一步：校验账号是否存在
async function handleCheckUsername() {
  errorMsg.value = ''
  successMsg.value = ''
  if (!validateForgotStep1()) return
  loading.value = true
  try {
    await request('/api/auth/check-username', {
      username: forgotForm.username.trim(),
    })
    // 校验通过，进入第二步
    forgotStep.value = 2
    successMsg.value = '账号验证通过，请设置新密码'
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '账号不存在或校验失败'
  } finally {
    loading.value = false
  }
}

// 第二步：重置密码
async function handleResetPassword() {
  errorMsg.value = ''
  successMsg.value = ''
  if (!validateForgotStep2()) return
  loading.value = true
  try {
    await request('/api/auth/reset-password', {
      username: forgotForm.username.trim(),
      new_password: forgotForm.newPassword,
    })
    successMsg.value = '密码重置成功，请使用新密码登录'
    // 自动填充账号
    loginForm.username = forgotForm.username.trim()
    loginForm.password = ''
    // 重置找回流程
    forgotStep.value = 1
    forgotForm.username = ''
    forgotForm.newPassword = ''
    forgotForm.confirmPassword = ''
    viewMode.value = 'login'
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '密码重置失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

const canRegister = computed(() => role.value === 'user')
</script>

<template>
  <div class="login-page">
    <div class="login-container">
      <!-- 左侧：系统介绍 -->
      <aside class="intro-panel">
        <div class="intro-inner">
          <p class="eyebrow">AI Commerce Assistant</p>
          <h1 class="intro-title">电商AI商品文案生成<br />与智能导购助手</h1>
          <p class="intro-lead">
            基于真实电商数据的 AI 助手系统：Scrapy 爬取京东商品与评论，PostgreSQL 存储，
            Redis 缓存，AI 大模型驱动文案生成、导购推荐、情感分析与直播脚本。
          </p>

          <div class="feature-list">
            <div v-for="f in features" :key="f.title" class="feature-item">
              <span class="feature-icon">{{ f.icon }}</span>
              <div class="feature-text">
                <h3>{{ f.title }}</h3>
                <p>{{ f.desc }}</p>
              </div>
            </div>
          </div>
        </div>
        <div class="intro-footer">
          <span class="dot dot--green"></span>
          <span>双端架构 · 普通用户前台 + 商家管理后台</span>
        </div>
      </aside>

      <!-- 右侧：登录卡片 -->
      <section class="auth-panel">
        <div class="auth-card">
          <!-- 视图切换标题 -->
          <div class="auth-header">
            <h2>
              {{ viewMode === 'login' ? '欢迎登录' : viewMode === 'register' ? '注册新账号' : '找回密码' }}
            </h2>
            <p class="auth-subtitle">
              {{ viewMode === 'login'
                ? '请选择身份并输入账号密码'
                : viewMode === 'register'
                  ? '仅普通用户可注册，商家账号请联系管理员'
                  : '输入账号验证后即可重置密码' }}
            </p>
          </div>

          <!-- 身份切换 tab（仅登录与注册入口展示） -->
          <div v-if="viewMode === 'login'" class="role-tabs">
            <button
              v-for="tab in roleTabs"
              :key="tab.value"
              :class="['role-tab', { active: role === tab.value }]"
              @click="switchRole(tab.value)"
            >
              <span class="role-tab-label">{{ tab.label }}</span>
              <span class="role-tab-desc">{{ tab.desc }}</span>
            </button>
          </div>

          <!-- 全局提示 -->
          <div v-if="errorMsg" class="alert alert--error">{{ errorMsg }}</div>
          <div v-if="successMsg" class="alert alert--success">{{ successMsg }}</div>

          <!-- 登录表单 -->
          <form v-if="viewMode === 'login'" class="auth-form" @submit.prevent="handleLogin">
            <div class="form-group">
              <label>账号</label>
              <input
                v-model="loginForm.username"
                type="text"
                placeholder="请输入账号"
                :class="{ invalid: loginErrors.username }"
              />
              <span v-if="loginErrors.username" class="field-error">{{ loginErrors.username }}</span>
            </div>
            <div class="form-group">
              <label>密码</label>
              <div class="password-wrapper">
                <input
                  v-model="loginForm.password"
                  :type="showLoginPassword ? 'text' : 'password'"
                  placeholder="请输入密码"
                  :class="{ invalid: loginErrors.password }"
                />
                <button
                  type="button"
                  class="password-toggle"
                  @click="showLoginPassword = !showLoginPassword"
                  :aria-label="showLoginPassword ? '隐藏密码' : '显示密码'"
                >
                  <span class="eye-icon">{{ showLoginPassword ? '🙈' : '👁' }}</span>
                </button>
              </div>
              <span v-if="loginErrors.password" class="field-error">{{ loginErrors.password }}</span>
            </div>

            <!-- 记住密码 -->
            <div class="remember-row">
              <label class="checkbox-label">
                <input
                  v-model="rememberPassword"
                  type="checkbox"
                  class="checkbox-input"
                />
                <span class="checkbox-custom"></span>
                <span class="checkbox-text">记住密码</span>
              </label>
            </div>

            <button type="submit" class="submit-btn" :disabled="loading">
              {{ loading ? '登录中...' : '登 录' }}
            </button>

            <div class="form-links">
              <button type="button" class="link-btn" @click="switchMode('forgot')">
                忘记密码？
              </button>
              <button
                v-if="canRegister"
                type="button"
                class="link-btn"
                @click="switchMode('register')"
              >
                没有账号？立即注册
              </button>
            </div>
          </form>

          <!-- 注册表单 -->
          <form v-else-if="viewMode === 'register'" class="auth-form" @submit.prevent="handleRegister">
            <div class="form-group">
              <label>账号</label>
              <input
                v-model="registerForm.username"
                type="text"
                placeholder="请设置登录账号"
                :class="{ invalid: registerErrors.username }"
              />
              <span v-if="registerErrors.username" class="field-error">{{ registerErrors.username }}</span>
            </div>
            <div class="form-group">
              <label>昵称</label>
              <input
                v-model="registerForm.nickname"
                type="text"
                placeholder="请输入昵称"
                :class="{ invalid: registerErrors.nickname }"
              />
              <span v-if="registerErrors.nickname" class="field-error">{{ registerErrors.nickname }}</span>
            </div>
            <div class="form-group">
              <label>密码</label>
              <div class="password-wrapper">
                <input
                  v-model="registerForm.password"
                  :type="showRegisterPassword ? 'text' : 'password'"
                  placeholder="密码长度不少于 6 位"
                  :class="{ invalid: registerErrors.password }"
                />
                <button
                  type="button"
                  class="password-toggle"
                  @click="showRegisterPassword = !showRegisterPassword"
                  :aria-label="showRegisterPassword ? '隐藏密码' : '显示密码'"
                >
                  <span class="eye-icon">{{ showRegisterPassword ? '🙈' : '👁' }}</span>
                </button>
              </div>
              <span v-if="registerErrors.password" class="field-error">{{ registerErrors.password }}</span>
            </div>
            <div class="form-group">
              <label>确认密码</label>
              <div class="password-wrapper">
                <input
                  v-model="registerForm.confirmPassword"
                  :type="showRegisterConfirmPassword ? 'text' : 'password'"
                  placeholder="请再次输入密码"
                  :class="{ invalid: registerErrors.confirmPassword }"
                />
                <button
                  type="button"
                  class="password-toggle"
                  @click="showRegisterConfirmPassword = !showRegisterConfirmPassword"
                  :aria-label="showRegisterConfirmPassword ? '隐藏密码' : '显示密码'"
                >
                  <span class="eye-icon">{{ showRegisterConfirmPassword ? '🙈' : '👁' }}</span>
                </button>
              </div>
              <span v-if="registerErrors.confirmPassword" class="field-error">{{ registerErrors.confirmPassword }}</span>
            </div>
            <button type="submit" class="submit-btn" :disabled="loading">
              {{ loading ? '注册中...' : '注 册' }}
            </button>
            <div class="form-links">
              <button type="button" class="link-btn" @click="switchMode('login')">
                已有账号？返回登录
              </button>
            </div>
          </form>

          <!-- 找回密码表单 -->
          <form v-else class="auth-form" @submit.prevent="forgotStep === 1 ? handleCheckUsername() : handleResetPassword()">
            <!-- 步骤指示器 -->
            <div class="step-indicator">
              <span :class="['step', { active: forgotStep >= 1, done: forgotStep > 1 }]">
                <i>1</i> 验证账号
              </span>
              <span class="step-line" :class="{ active: forgotStep > 1 }"></span>
              <span :class="['step', { active: forgotStep >= 2 }]">
                <i>2</i> 重置密码
              </span>
            </div>

            <!-- 第一步：输入账号 -->
            <template v-if="forgotStep === 1">
              <div class="form-group">
                <label>账号</label>
                <input
                  v-model="forgotForm.username"
                  type="text"
                  placeholder="请输入需要找回的账号"
                  :class="{ invalid: forgotErrors.username }"
                />
                <span v-if="forgotErrors.username" class="field-error">{{ forgotErrors.username }}</span>
              </div>
              <button type="submit" class="submit-btn" :disabled="loading">
                {{ loading ? '验证中...' : '下一步' }}
              </button>
            </template>

            <!-- 第二步：设置新密码 -->
            <template v-else>
              <div class="form-group">
                <label>新密码</label>
                <div class="password-wrapper">
                  <input
                    v-model="forgotForm.newPassword"
                    :type="showForgotPassword ? 'text' : 'password'"
                    placeholder="密码长度不少于 6 位"
                    :class="{ invalid: forgotErrors.newPassword }"
                  />
                  <button
                    type="button"
                    class="password-toggle"
                    @click="showForgotPassword = !showForgotPassword"
                    :aria-label="showForgotPassword ? '隐藏密码' : '显示密码'"
                  >
                    <span class="eye-icon">{{ showForgotPassword ? '🙈' : '👁' }}</span>
                  </button>
                </div>
                <span v-if="forgotErrors.newPassword" class="field-error">{{ forgotErrors.newPassword }}</span>
              </div>
              <div class="form-group">
                <label>确认新密码</label>
                <div class="password-wrapper">
                  <input
                    v-model="forgotForm.confirmPassword"
                    :type="showForgotConfirmPassword ? 'text' : 'password'"
                    placeholder="请再次输入新密码"
                    :class="{ invalid: forgotErrors.confirmPassword }"
                  />
                  <button
                    type="button"
                    class="password-toggle"
                    @click="showForgotConfirmPassword = !showForgotConfirmPassword"
                    :aria-label="showForgotConfirmPassword ? '隐藏密码' : '显示密码'"
                  >
                    <span class="eye-icon">{{ showForgotConfirmPassword ? '🙈' : '👁' }}</span>
                  </button>
                </div>
                <span v-if="forgotErrors.confirmPassword" class="field-error">{{ forgotErrors.confirmPassword }}</span>
              </div>
              <button type="submit" class="submit-btn" :disabled="loading">
                {{ loading ? '重置中...' : '重置密码' }}
              </button>
            </template>

            <div class="form-links">
              <button type="button" class="link-btn" @click="switchMode('login')">
                返回登录
              </button>
            </div>
          </form>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
}

.login-page::before {
  content: '';
  position: absolute;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
  background-size: 50px 50px;
  animation: backgroundMove 20s linear infinite;
  opacity: 0.3;
}

@keyframes backgroundMove {
  0% {
    transform: translate(0, 0);
  }
  100% {
    transform: translate(50px, 50px);
  }
}

.login-container {
  width: min(1100px, 100%);
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 25px 80px rgba(0, 0, 0, 0.25), 0 10px 40px rgba(0, 0, 0, 0.15);
  min-height: 680px;
  animation: fadeInUp 0.6s ease-out;
  position: relative;
  z-index: 1;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(40px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 左侧介绍 */
.intro-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: clamp(40px, 5vw, 64px);
  color: #fff;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  overflow: hidden;
}

.intro-panel::before {
  position: absolute;
  top: -150px;
  right: -150px;
  width: 400px;
  height: 400px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  content: '';
  animation: float 10s ease-in-out infinite;
  filter: blur(2px);
}

.intro-panel::after {
  position: absolute;
  bottom: -120px;
  left: -100px;
  width: 300px;
  height: 300px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  content: '';
  animation: float 12s ease-in-out infinite reverse;
  filter: blur(2px);
}

@keyframes float {
  0%, 100% {
    transform: translate(0, 0) scale(1);
  }
  50% {
    transform: translate(30px, -30px) scale(1.05);
  }
}

.intro-inner {
  position: relative;
  z-index: 1;
}

.eyebrow {
  margin: 0 0 18px;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.95);
}

.intro-title {
  margin: 0;
  font-size: clamp(28px, 3.2vw, 40px);
  line-height: 1.15;
  letter-spacing: -0.03em;
}

.intro-lead {
  margin: 20px 0 0;
  font-size: 15px;
  line-height: 1.75;
  color: rgba(255, 255, 255, 0.92);
}

.feature-list {
  display: grid;
  gap: 16px;
  margin-top: 32px;
}

.feature-item {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.feature-icon {
  flex: 0 0 auto;
  display: inline-grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: 12px;
  font-weight: 800;
  font-size: 16px;
  color: var(--brand-dark);
  background: rgba(255, 250, 240, 0.92);
}

.feature-text h3 {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 700;
}

.feature-text p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.9);
}

.intro-footer {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 24px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.9);
}

.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--yellow);
}

.dot--green {
  background: #6fe0a8;
  box-shadow: 0 0 0 4px rgba(111, 224, 168, 0.25);
}

/* 右侧登录卡片 */
.auth-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(28px, 4vw, 48px);
  background: var(--panel);
}

.auth-card {
  width: 100%;
  max-width: 380px;
}

.auth-header {
  margin-bottom: 24px;
}

.auth-header h2 {
  margin: 0 0 8px;
  font-size: 26px;
  letter-spacing: -0.02em;
  color: var(--ink);
}

.auth-subtitle {
  margin: 0;
  font-size: 14px;
  color: var(--muted);
  line-height: 1.6;
}

/* 身份切换 tab */
.role-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 24px;
}

.role-tab {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: transparent;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
}

.role-tab:hover {
  border-color: var(--brand);
}

.role-tab.active {
  border-color: var(--brand);
  background: rgba(217, 95, 45, 0.08);
  box-shadow: 0 0 0 1px var(--brand) inset;
}

.role-tab-label {
  font-weight: 700;
  font-size: 14px;
  color: var(--brand-dark);
}

.role-tab-desc {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.4;
}

/* 全局提示 */
.alert {
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
  margin-bottom: 16px;
  line-height: 1.5;
}

.alert--error {
  background: #fdeceb;
  color: #c0392b;
  border: 1px solid rgba(192, 57, 43, 0.2);
}

.alert--success {
  background: #e8f6ee;
  color: var(--green);
  border: 1px solid rgba(31, 138, 91, 0.2);
}

/* 表单 */
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
}

.form-group input {
  padding: 11px 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  background: rgba(255, 255, 255, 0.7);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(217, 95, 45, 0.12);
}

.form-group input.invalid {
  border-color: #c0392b;
  box-shadow: 0 0 0 3px rgba(192, 57, 43, 0.1);
}

.field-error {
  font-size: 12px;
  color: #c0392b;
}

/* 密码可见性切换 */
.password-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.password-wrapper input {
  width: 100%;
  padding-right: 44px;
}

.password-toggle {
  position: absolute;
  right: 8px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.password-toggle:hover {
  opacity: 1;
}

.eye-icon {
  font-size: 18px;
  user-select: none;
}

/* 记住密码 */
.remember-row {
  display: flex;
  align-items: center;
  margin: 4px 0;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.checkbox-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.checkbox-custom {
  position: relative;
  width: 18px;
  height: 18px;
  border: 2px solid var(--line);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.7);
  transition: all 0.2s;
}

.checkbox-input:checked + .checkbox-custom {
  background: var(--brand);
  border-color: var(--brand);
}

.checkbox-input:checked + .checkbox-custom::after {
  content: '';
  position: absolute;
  left: 5px;
  top: 2px;
  width: 4px;
  height: 8px;
  border: solid #fffaf0;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.checkbox-input:focus + .checkbox-custom {
  box-shadow: 0 0 0 3px rgba(217, 95, 45, 0.12);
}

.checkbox-text {
  font-size: 13px;
  color: var(--ink);
  font-weight: 500;
}

.submit-btn {
  margin-top: 4px;
  padding: 13px 20px;
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  color: #fffaf0;
  background: var(--brand);
  cursor: pointer;
  transition: background 0.2s, transform 0.18s;
}

.submit-btn:hover:not(:disabled) {
  background: var(--brand-dark);
  transform: translateY(-1px);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-links {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 4px;
}

.link-btn {
  background: none;
  border: none;
  color: var(--brand);
  font-size: 13px;
  cursor: pointer;
  padding: 0;
  transition: color 0.2s;
}

.link-btn:hover {
  color: var(--brand-dark);
  text-decoration: underline;
}

/* 步骤指示器 */
.step-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.step {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--muted);
}

.step i {
  display: inline-grid;
  width: 22px;
  height: 22px;
  place-items: center;
  border-radius: 50%;
  font-style: normal;
  font-size: 12px;
  font-weight: 700;
  color: #fffaf0;
  background: var(--muted);
}

.step.active {
  color: var(--brand-dark);
  font-weight: 600;
}

.step.active i {
  background: var(--brand);
}

.step.done i {
  background: var(--green);
}

.step-line {
  flex: 1;
  height: 2px;
  background: var(--line);
  border-radius: 2px;
}

.step-line.active {
  background: var(--brand);
}

@media (max-width: 860px) {
  .login-container {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .intro-panel {
    padding: 32px;
  }

  .feature-list {
    margin-top: 24px;
  }
}

@media (max-width: 520px) {
  .login-page {
    padding: 16px 12px;
  }

  .login-container {
    border-radius: 22px;
  }

  .role-tabs {
    grid-template-columns: 1fr;
  }

  .form-links {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>
