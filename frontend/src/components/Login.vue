<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import {
  SparklesIcon,
  ShoppingBagIcon,
  ChatBubbleLeftRightIcon,
  ChartBarIcon,
  UserIcon,
  BuildingStorefrontIcon,
  EyeIcon,
  EyeSlashIcon,
  ArrowPathIcon,
} from '@heroicons/vue/24/outline'

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

const features = [
  { icon: SparklesIcon, title: 'AI 商品文案生成', desc: '一键生成标题、卖点、详情页文案和广告语，支撑商品上架与营销素材。' },
  { icon: ShoppingBagIcon, title: '智能导购推荐', desc: '根据用户预算、场景与偏好，生成可解释的推荐理由与替代方案。' },
  { icon: ChatBubbleLeftRightIcon, title: 'AI 客服咨询', desc: '结合商品知识与真实评论，7×24 小时智能解答用户疑问。' },
  { icon: ChartBarIcon, title: '评论情感分析', desc: '提取好评词、差评痛点与可落地的商品优化建议。' },
]

const roleTabs: { value: Role; label: string; desc: string; icon: any }[] = [
  { value: 'user', label: '普通用户', desc: '浏览商品、智能导购、购物下单', icon: UserIcon },
  { value: 'merchant', label: '商家管理员', desc: '商品管理、文案生成、数据分析', icon: BuildingStorefrontIcon },
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
    loginForm.username = registerForm.username.trim()
    loginForm.password = ''
    viewMode.value = 'login'
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

async function handleCheckUsername() {
  errorMsg.value = ''
  successMsg.value = ''
  if (!validateForgotStep1()) return
  loading.value = true
  try {
    await request('/api/auth/check-username', {
      username: forgotForm.username.trim(),
    })
    forgotStep.value = 2
    successMsg.value = '账号验证通过，请设置新密码'
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '账号不存在或校验失败'
  } finally {
    loading.value = false
  }
}

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
    loginForm.username = forgotForm.username.trim()
    loginForm.password = ''
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

const headline = computed(() => {
  if (viewMode.value === 'login') return '欢迎回来'
  if (viewMode.value === 'register') return '创建新账号'
  return '找回密码'
})
</script>

<template>
  <div class="login-page">
    <!-- 灵动背景 -->
    <div class="ambient">
      <div class="orb orb--1"></div>
      <div class="orb orb--2"></div>
      <div class="orb orb--3"></div>
      <div class="grid-overlay"></div>
    </div>

    <div class="login-container">
      <!-- 左侧：系统介绍 -->
      <aside class="intro-panel">
        <div class="intro-glass">
          <div class="intro-badge">
            <SparklesIcon class="intro-badge__icon" />
            <span>AI Commerce Assistant</span>
          </div>
          <h1 class="intro-title">
            电商 AI 商品文案<br />与智能导购助手
          </h1>
          <p class="intro-lead">
            基于真实电商数据的 AI 助手系统，集文案生成、智能导购、评论分析、AI 客服于一体，
            为商家与用户打造更聪明的电商体验。
          </p>

          <div class="feature-list">
            <div v-for="f in features" :key="f.title" class="feature-item">
              <div class="feature-icon">
                <component :is="f.icon" class="w-5 h-5" />
              </div>
              <div class="feature-text">
                <h3>{{ f.title }}</h3>
                <p>{{ f.desc }}</p>
              </div>
            </div>
          </div>
        </div>
        <div class="intro-footer">
          <span class="status-dot"></span>
          <span>双端架构 · 普通用户前台 + 商家管理后台</span>
        </div>
      </aside>

      <!-- 右侧：登录卡片 -->
      <section class="auth-panel">
        <div class="auth-card">
          <div class="auth-header">
            <h2>{{ headline }}</h2>
            <p class="auth-subtitle">
              {{ viewMode === 'login'
                ? '请选择身份并输入账号密码'
                : viewMode === 'register'
                  ? '仅普通用户可注册，商家账号请联系管理员'
                  : '输入账号验证后即可重置密码' }}
            </p>
          </div>

          <!-- 身份切换 tab -->
          <div v-if="viewMode === 'login'" class="role-tabs">
            <button
              v-for="tab in roleTabs"
              :key="tab.value"
              :class="['role-tab', { active: role === tab.value }]"
              @click="switchRole(tab.value)"
            >
              <component :is="tab.icon" class="role-tab__icon" />
              <div class="role-tab__text">
                <span class="role-tab-label">{{ tab.label }}</span>
                <span class="role-tab-desc">{{ tab.desc }}</span>
              </div>
            </button>
          </div>

          <!-- 全局提示 -->
          <transition name="slide-down">
            <div v-if="errorMsg" class="alert alert--error">
              <span>{{ errorMsg }}</span>
            </div>
          </transition>
          <transition name="slide-down">
            <div v-if="successMsg" class="alert alert--success">
              <span>{{ successMsg }}</span>
            </div>
          </transition>

          <!-- 登录表单 -->
          <form v-if="viewMode === 'login'" class="auth-form" @submit.prevent="handleLogin">
            <div class="form-group">
              <label>账号</label>
              <div class="input-wrap">
                <input
                  v-model="loginForm.username"
                  type="text"
                  placeholder="请输入账号"
                  :class="{ invalid: loginErrors.username }"
                />
              </div>
              <span v-if="loginErrors.username" class="field-error">{{ loginErrors.username }}</span>
            </div>
            <div class="form-group">
              <label>密码</label>
              <div class="input-wrap password-wrapper">
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
                >
                  <component :is="showLoginPassword ? EyeSlashIcon : EyeIcon" class="w-5 h-5" />
                </button>
              </div>
              <span v-if="loginErrors.password" class="field-error">{{ loginErrors.password }}</span>
            </div>

            <div class="remember-row">
              <label class="checkbox-label">
                <input v-model="rememberPassword" type="checkbox" class="checkbox-input" />
                <span class="checkbox-custom"></span>
                <span class="checkbox-text">记住密码</span>
              </label>
            </div>

            <button type="submit" class="submit-btn" :disabled="loading">
              <ArrowPathIcon v-if="loading" class="w-4 h-4 animate-spin" />
              <span>{{ loading ? '登录中...' : '登 录' }}</span>
            </button>

            <div class="form-links">
              <button type="button" class="link-btn" @click="switchMode('forgot')">
                忘记密码？
              </button>
              <button v-if="canRegister" type="button" class="link-btn" @click="switchMode('register')">
                没有账号？立即注册
              </button>
            </div>
          </form>

          <!-- 注册表单 -->
          <form v-else-if="viewMode === 'register'" class="auth-form" @submit.prevent="handleRegister">
            <div class="form-group">
              <label>账号</label>
              <div class="input-wrap">
                <input v-model="registerForm.username" type="text" placeholder="请设置登录账号" :class="{ invalid: registerErrors.username }" />
              </div>
              <span v-if="registerErrors.username" class="field-error">{{ registerErrors.username }}</span>
            </div>
            <div class="form-group">
              <label>昵称</label>
              <div class="input-wrap">
                <input v-model="registerForm.nickname" type="text" placeholder="请输入昵称" :class="{ invalid: registerErrors.nickname }" />
              </div>
              <span v-if="registerErrors.nickname" class="field-error">{{ registerErrors.nickname }}</span>
            </div>
            <div class="form-group">
              <label>密码</label>
              <div class="input-wrap password-wrapper">
                <input v-model="registerForm.password" :type="showRegisterPassword ? 'text' : 'password'" placeholder="密码长度不少于 6 位" :class="{ invalid: registerErrors.password }" />
                <button type="button" class="password-toggle" @click="showRegisterPassword = !showRegisterPassword">
                  <component :is="showRegisterPassword ? EyeSlashIcon : EyeIcon" class="w-5 h-5" />
                </button>
              </div>
              <span v-if="registerErrors.password" class="field-error">{{ registerErrors.password }}</span>
            </div>
            <div class="form-group">
              <label>确认密码</label>
              <div class="input-wrap password-wrapper">
                <input v-model="registerForm.confirmPassword" :type="showRegisterConfirmPassword ? 'text' : 'password'" placeholder="请再次输入密码" :class="{ invalid: registerErrors.confirmPassword }" />
                <button type="button" class="password-toggle" @click="showRegisterConfirmPassword = !showRegisterConfirmPassword">
                  <component :is="showRegisterConfirmPassword ? EyeSlashIcon : EyeIcon" class="w-5 h-5" />
                </button>
              </div>
              <span v-if="registerErrors.confirmPassword" class="field-error">{{ registerErrors.confirmPassword }}</span>
            </div>
            <button type="submit" class="submit-btn" :disabled="loading">
              <ArrowPathIcon v-if="loading" class="w-4 h-4 animate-spin" />
              <span>{{ loading ? '注册中...' : '注 册' }}</span>
            </button>
            <div class="form-links">
              <button type="button" class="link-btn" @click="switchMode('login')">
                已有账号？返回登录
              </button>
            </div>
          </form>

          <!-- 找回密码表单 -->
          <form v-else class="auth-form" @submit.prevent="forgotStep === 1 ? handleCheckUsername() : handleResetPassword()">
            <div class="step-indicator">
              <div :class="['step', { active: forgotStep >= 1, done: forgotStep > 1 }]">
                <span class="step-num">1</span>
                <span class="step-label">验证账号</span>
              </div>
              <div class="step-line" :class="{ active: forgotStep > 1 }"></div>
              <div :class="['step', { active: forgotStep >= 2 }]">
                <span class="step-num">2</span>
                <span class="step-label">重置密码</span>
              </div>
            </div>

            <template v-if="forgotStep === 1">
              <div class="form-group">
                <label>账号</label>
                <div class="input-wrap">
                  <input v-model="forgotForm.username" type="text" placeholder="请输入需要找回的账号" :class="{ invalid: forgotErrors.username }" />
                </div>
                <span v-if="forgotErrors.username" class="field-error">{{ forgotErrors.username }}</span>
              </div>
              <button type="submit" class="submit-btn" :disabled="loading">
                <ArrowPathIcon v-if="loading" class="w-4 h-4 animate-spin" />
                <span>{{ loading ? '验证中...' : '下一步' }}</span>
              </button>
            </template>

            <template v-else>
              <div class="form-group">
                <label>新密码</label>
                <div class="input-wrap password-wrapper">
                  <input v-model="forgotForm.newPassword" :type="showForgotPassword ? 'text' : 'password'" placeholder="密码长度不少于 6 位" :class="{ invalid: forgotErrors.newPassword }" />
                  <button type="button" class="password-toggle" @click="showForgotPassword = !showForgotPassword">
                    <component :is="showForgotPassword ? EyeSlashIcon : EyeIcon" class="w-5 h-5" />
                  </button>
                </div>
                <span v-if="forgotErrors.newPassword" class="field-error">{{ forgotErrors.newPassword }}</span>
              </div>
              <div class="form-group">
                <label>确认新密码</label>
                <div class="input-wrap password-wrapper">
                  <input v-model="forgotForm.confirmPassword" :type="showForgotConfirmPassword ? 'text' : 'password'" placeholder="请再次输入新密码" :class="{ invalid: forgotErrors.confirmPassword }" />
                  <button type="button" class="password-toggle" @click="showForgotConfirmPassword = !showForgotConfirmPassword">
                    <component :is="showForgotConfirmPassword ? EyeSlashIcon : EyeIcon" class="w-5 h-5" />
                  </button>
                </div>
                <span v-if="forgotErrors.confirmPassword" class="field-error">{{ forgotErrors.confirmPassword }}</span>
              </div>
              <button type="submit" class="submit-btn" :disabled="loading">
                <ArrowPathIcon v-if="loading" class="w-4 h-4 animate-spin" />
                <span>{{ loading ? '重置中...' : '重置密码' }}</span>
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
  background: linear-gradient(135deg, #f8f8fc 0%, #f0f4ff 50%, #fdf8f6 100%);
  position: relative;
  overflow: hidden;
}

/* 灵动背景 */
.ambient {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.55;
  animation: floatOrb 18s ease-in-out infinite;
}

.orb--1 {
  width: 520px;
  height: 520px;
  top: -160px;
  left: -120px;
  background: radial-gradient(circle, rgba(155, 135, 245, 0.55), transparent 70%);
}

.orb--2 {
  width: 440px;
  height: 440px;
  bottom: -120px;
  right: -80px;
  background: radial-gradient(circle, rgba(147, 197, 253, 0.55), transparent 70%);
  animation-delay: -6s;
}

.orb--3 {
  width: 320px;
  height: 320px;
  top: 45%;
  left: 55%;
  background: radial-gradient(circle, rgba(253, 230, 138, 0.45), transparent 70%);
  animation-delay: -12s;
}

@keyframes floatOrb {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(40px, -30px) scale(1.06); }
  66% { transform: translate(-30px, 20px) scale(0.96); }
}

.grid-overlay {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(155, 135, 245, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(155, 135, 245, 0.04) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(ellipse at center, black 0%, transparent 70%);
  -webkit-mask-image: radial-gradient(ellipse at center, black 0%, transparent 70%);
}

.login-container {
  width: min(1120px, 100%);
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  border-radius: 32px;
  overflow: hidden;
  min-height: 720px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(155, 135, 245, 0.14);
  box-shadow:
    0 24px 80px rgba(155, 135, 245, 0.14),
    0 8px 32px rgba(31, 41, 55, 0.04);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  animation: cardIn 0.7s cubic-bezier(0.22, 1, 0.36, 1);
  position: relative;
  z-index: 1;
}

@keyframes cardIn {
  from { opacity: 0; transform: translateY(36px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

/* 左侧介绍 */
.intro-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: clamp(40px, 5vw, 64px);
  color: #1f2937;
  background: linear-gradient(135deg, rgba(237, 233, 254, 0.7) 0%, rgba(219, 234, 254, 0.5) 100%);
  overflow: hidden;
}

.intro-panel::before {
  position: absolute;
  top: -120px;
  right: -120px;
  width: 360px;
  height: 360px;
  border-radius: 50%;
  background: rgba(155, 135, 245, 0.18);
  content: '';
  filter: blur(60px);
}

.intro-panel::after {
  position: absolute;
  bottom: -100px;
  left: -80px;
  width: 280px;
  height: 280px;
  border-radius: 50%;
  background: rgba(147, 197, 253, 0.2);
  content: '';
  filter: blur(60px);
}

.intro-glass {
  position: relative;
  z-index: 1;
}

.intro-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(155, 135, 245, 0.2);
  color: var(--brand-dark);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 24px;
  box-shadow: 0 2px 12px rgba(155, 135, 245, 0.08);
}

.intro-badge__icon {
  width: 16px;
  height: 16px;
}

.intro-title {
  margin: 0;
  font-size: clamp(28px, 3.2vw, 40px);
  line-height: 1.18;
  letter-spacing: -0.03em;
  color: #1f2937;
}

.intro-lead {
  margin: 18px 0 0;
  font-size: 15px;
  line-height: 1.8;
  color: #4b5563;
  max-width: 440px;
}

.feature-list {
  display: grid;
  gap: 14px;
  margin-top: 36px;
}

.feature-item {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding: 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid rgba(155, 135, 245, 0.12);
  transition: transform 0.2s, box-shadow 0.2s;
}

.feature-item:hover {
  transform: translateX(4px);
  box-shadow: 0 8px 24px rgba(155, 135, 245, 0.1);
}

.feature-icon {
  flex: 0 0 auto;
  display: inline-grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: 12px;
  color: #fff;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark));
  box-shadow: 0 6px 16px rgba(155, 135, 245, 0.28);
}

.feature-text h3 {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 700;
  color: #1f2937;
}

.feature-text p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #6b7280;
}

.intro-footer {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 24px;
  font-size: 13px;
  color: #6b7280;
}

.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 0 4px rgba(52, 211, 153, 0.22);
}

/* 右侧登录卡片 */
.auth-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(32px, 4vw, 48px);
  background: rgba(255, 255, 255, 0.78);
}

.auth-card {
  width: 100%;
  max-width: 380px;
  animation: fadeIn 0.5s ease 0.2s both;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.auth-header {
  margin-bottom: 26px;
}

.auth-header h2 {
  margin: 0 0 8px;
  font-size: 28px;
  letter-spacing: -0.02em;
  color: #1f2937;
}

.auth-subtitle {
  margin: 0;
  font-size: 14px;
  color: #6b7280;
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
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border: 1px solid rgba(155, 135, 245, 0.18);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
}

.role-tab:hover {
  border-color: var(--brand);
  background: rgba(155, 135, 245, 0.06);
}

.role-tab.active {
  border-color: var(--brand);
  background: rgba(155, 135, 245, 0.1);
  box-shadow: 0 0 0 1px var(--brand) inset, 0 6px 18px rgba(155, 135, 245, 0.12);
}

.role-tab__icon {
  width: 20px;
  height: 20px;
  color: var(--brand);
  flex-shrink: 0;
}

.role-tab__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.role-tab-label {
  font-weight: 700;
  font-size: 14px;
  color: #1f2937;
}

.role-tab-desc {
  font-size: 11px;
  color: #6b7280;
  line-height: 1.3;
}

/* 全局提示 */
.alert {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px 14px;
  border-radius: 12px;
  font-size: 13px;
  margin-bottom: 16px;
  line-height: 1.5;
}

.alert--error {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid rgba(185, 28, 28, 0.14);
}

.alert--success {
  background: #f0fdf4;
  color: #15803d;
  border: 1px solid rgba(21, 128, 61, 0.14);
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.25s ease;
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-6px);
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
  color: #374151;
}

.input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.input-wrap input {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid rgba(155, 135, 245, 0.2);
  border-radius: 12px;
  font-size: 14px;
  font-family: inherit;
  background: rgba(255, 255, 255, 0.8);
  color: #1f2937;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
}

.input-wrap input::placeholder {
  color: #9ca3af;
}

.input-wrap input:focus {
  outline: none;
  border-color: var(--brand);
  background: #fff;
  box-shadow: 0 0 0 3px rgba(155, 135, 245, 0.12);
}

.input-wrap input.invalid {
  border-color: #ef4444;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.field-error {
  font-size: 12px;
  color: #dc2626;
}

/* 密码可见性切换 */
.password-wrapper input {
  padding-right: 44px;
}

.password-toggle {
  position: absolute;
  right: 10px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  transition: color 0.2s;
}

.password-toggle:hover {
  color: var(--brand);
}

/* 记住密码 */
.remember-row {
  display: flex;
  align-items: center;
  margin: 2px 0;
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
  border: 2px solid rgba(155, 135, 245, 0.35);
  border-radius: 5px;
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
  border: solid #fff;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.checkbox-input:focus + .checkbox-custom {
  box-shadow: 0 0 0 3px rgba(155, 135, 245, 0.12);
}

.checkbox-text {
  font-size: 13px;
  color: #4b5563;
  font-weight: 500;
}

.submit-btn {
  margin-top: 4px;
  padding: 13px 20px;
  border: none;
  border-radius: 14px;
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark));
  cursor: pointer;
  transition: transform 0.18s, box-shadow 0.18s, opacity 0.18s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-shadow: 0 8px 22px rgba(155, 135, 245, 0.32);
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 28px rgba(155, 135, 245, 0.38);
}

.submit-btn:disabled {
  opacity: 0.65;
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
  font-weight: 600;
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
  gap: 10px;
  margin-bottom: 10px;
}

.step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #9ca3af;
}

.step-num {
  display: inline-grid;
  width: 24px;
  height: 24px;
  place-items: center;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  background: #d1d5db;
  transition: background 0.2s;
}

.step.active {
  color: var(--brand-dark);
  font-weight: 600;
}

.step.active .step-num {
  background: var(--brand);
}

.step.done .step-num {
  background: var(--green);
}

.step-line {
  flex: 1;
  height: 2px;
  background: #e5e7eb;
  border-radius: 2px;
}

.step-line.active {
  background: var(--brand);
}

.step-label {
  white-space: nowrap;
}

@media (max-width: 900px) {
  .login-container {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .intro-panel {
    padding: 32px;
    min-height: 320px;
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
    border-radius: 24px;
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
