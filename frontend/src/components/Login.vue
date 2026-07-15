<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Form,
  FormItem,
  Input,
  InputPassword,
  RadioButton,
  RadioGroup,
  Row,
  Space,
  Steps,
  Tag,
  TypographyParagraph,
  TypographyText,
  TypographyTitle,
} from 'ant-design-vue'
import {
  BarChartOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  ShopOutlined,
  ShoppingCartOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'
import { AnimatePresence, motion } from 'motion-v'
import { pageMotion } from '../theme'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

type ViewMode = 'login' | 'register' | 'forgot'
type Role = 'user' | 'merchant'

interface UserInfo {
  username: string
  role: Role
  nickname?: string
  token?: string
  [key: string]: unknown
}

const emit = defineEmits<{ (e: 'login-success', userInfo: UserInfo): void }>()
const viewMode = ref<ViewMode>('login')
const role = ref<Role>('user')
const loading = ref(false)
const errorMsg = ref('')
const successMsg = ref('')
const rememberLogin = ref(false)
const forgotStep = ref(0)

const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', nickname: '', password: '', confirmPassword: '' })
const forgotForm = reactive({ username: '', newPassword: '', confirmPassword: '' })

const features = [
  { icon: RobotOutlined, title: 'AI 商品文案', desc: '生成标题、卖点、详情文案与营销素材' },
  { icon: ShoppingCartOutlined, title: '智能导购', desc: '结合预算、场景和偏好给出可解释推荐' },
  { icon: SafetyCertificateOutlined, title: '知识库客服', desc: '基于商品知识与真实评论回答用户问题' },
  { icon: BarChartOutlined, title: '经营分析', desc: '聚合订单、评论、问答和商品流量数据' },
]

const title = computed(() => ({ login: '欢迎回来', register: '创建用户账号', forgot: '找回密码' })[viewMode.value])
const subtitle = computed(() => {
  if (viewMode.value === 'forgot') return '验证账号后设置新密码'
  return role.value === 'merchant' ? '进入商家运营工作台' : '登录后开始智能购物体验'
})

onMounted(() => {
  const saved = localStorage.getItem('rememberedLogin')
  if (!saved) return
  try {
    const data = JSON.parse(saved) as { username?: string; role?: Role }
    loginForm.username = data.username || ''
    role.value = data.role === 'merchant' ? 'merchant' : 'user'
    rememberLogin.value = true
  } catch {
    localStorage.removeItem('rememberedLogin')
  }
})

async function request<T>(path: string, body: Record<string, unknown>): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const payload = await response.json().catch(() => ({ message: '请求失败' }))
  if (!response.ok) throw new Error(payload.message || `HTTP ${response.status}`)
  return payload as T
}

function setFeedback(error = '', success = '') {
  errorMsg.value = error
  successMsg.value = success
}

function switchMode(mode: ViewMode) {
  viewMode.value = mode
  forgotStep.value = 0
  setFeedback()
}

async function handleLogin() {
  setFeedback()
  loading.value = true
  try {
    const data = await request<{
      token?: string
      access_token?: string
      user?: Record<string, unknown>
      username?: string
      nickname?: string
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
      ...(data.user || {}),
    }
    if (token) localStorage.setItem('token', token)
    localStorage.setItem('userInfo', JSON.stringify(userInfo))
    if (rememberLogin.value) {
      localStorage.setItem(
        'rememberedLogin',
        JSON.stringify({ username: loginForm.username.trim(), role: role.value }),
      )
    } else {
      localStorage.removeItem('rememberedLogin')
    }
    emit('login-success', userInfo)
  } catch (error) {
    setFeedback(error instanceof Error ? error.message : '登录失败')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  setFeedback()
  if (registerForm.password !== registerForm.confirmPassword) {
    setFeedback('两次输入的密码不一致')
    return
  }
  loading.value = true
  try {
    await request('/api/auth/register', {
      username: registerForm.username.trim(),
      nickname: registerForm.nickname.trim(),
      password: registerForm.password,
    })
    loginForm.username = registerForm.username.trim()
    switchMode('login')
    setFeedback('', '注册成功，请登录')
  } catch (error) {
    setFeedback(error instanceof Error ? error.message : '注册失败')
  } finally {
    loading.value = false
  }
}

async function handleCheckUsername() {
  setFeedback()
  loading.value = true
  try {
    await request('/api/auth/check-username', { username: forgotForm.username.trim() })
    forgotStep.value = 1
  } catch (error) {
    setFeedback(error instanceof Error ? error.message : '账号校验失败')
  } finally {
    loading.value = false
  }
}

async function handleResetPassword() {
  setFeedback()
  if (forgotForm.newPassword !== forgotForm.confirmPassword) {
    setFeedback('两次输入的密码不一致')
    return
  }
  loading.value = true
  try {
    await request('/api/auth/reset-password', {
      username: forgotForm.username.trim(),
      new_password: forgotForm.newPassword,
    })
    loginForm.username = forgotForm.username.trim()
    switchMode('login')
    setFeedback('', '密码已重置，请重新登录')
  } catch (error) {
    setFeedback(error instanceof Error ? error.message : '密码重置失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="relative min-h-screen overflow-hidden bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
    <motion.div
      class="pointer-events-none absolute -left-24 -top-24 h-96 w-96 rounded-full bg-violet-300/30 blur-3xl"
      :animate="{ x: [0, 48, 0], y: [0, 30, 0], scale: [1, 1.08, 1] }"
      :transition="{ duration: 14, repeat: Infinity, ease: 'easeInOut' }"
    />
    <motion.div
      class="pointer-events-none absolute -bottom-28 -right-20 h-[28rem] w-[28rem] rounded-full bg-blue-300/25 blur-3xl"
      :animate="{ x: [0, -40, 0], y: [0, -28, 0], scale: [1.08, 1, 1.08] }"
      :transition="{ duration: 17, repeat: Infinity, ease: 'easeInOut' }"
    />

    <Row :gutter="[32, 32]" align="middle" class="relative z-10 mx-auto min-h-[calc(100vh-4rem)] max-w-7xl">
      <Col :xs="24" :lg="13">
        <motion.section
          :initial="pageMotion.initial"
          :animate="pageMotion.animate"
          :transition="pageMotion.transition"
          class="mx-auto max-w-2xl"
        >
          <Tag color="purple" class="mb-5 border-0 px-3 py-1">AI COMMERCE WORKSPACE</Tag>
          <TypographyTitle :level="1" class="!mb-5 !text-4xl !font-black !leading-tight sm:!text-6xl">
            从商品数据到成交内容，<span class="text-violet-600">一套工作台完成</span>
          </TypographyTitle>
          <TypographyParagraph class="!mb-8 !max-w-xl !text-base !leading-8 !text-slate-600">
            面向消费者与商家的统一电商平台，覆盖智能导购、内容生成、知识库客服与经营分析。
          </TypographyParagraph>
          <div class="grid gap-4 sm:grid-cols-2">
            <motion.div
              v-for="(feature, index) in features"
              :key="feature.title"
              :initial="{ opacity: 0, y: 18 }"
              :animate="{ opacity: 1, y: 0 }"
              :transition="{ delay: 0.08 * index, type: 'spring', stiffness: 320, damping: 28 }"
            >
              <Card size="small" :bordered="false" class="h-full bg-white/75 backdrop-blur-xl">
                <Space align="start">
                  <span class="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-violet-100 text-lg text-violet-700">
                    <component :is="feature.icon" />
                  </span>
                  <span>
                    <TypographyText strong>{{ feature.title }}</TypographyText>
                    <TypographyParagraph class="!mb-0 !mt-1 !text-sm !text-slate-500">
                      {{ feature.desc }}
                    </TypographyParagraph>
                  </span>
                </Space>
              </Card>
            </motion.div>
          </div>
        </motion.section>
      </Col>

      <Col :xs="24" :lg="11">
        <motion.div
          :initial="{ opacity: 0, x: 28 }"
          :animate="{ opacity: 1, x: 0 }"
          :transition="{ type: 'spring', stiffness: 300, damping: 30 }"
          class="mx-auto max-w-lg"
        >
          <Card :bordered="false" class="bg-white/90 shadow-2xl shadow-violet-950/10 backdrop-blur-xl">
            <Space direction="vertical" :size="4" class="mb-6 w-full">
              <TypographyTitle :level="2" class="!mb-0">{{ title }}</TypographyTitle>
              <TypographyText type="secondary">{{ subtitle }}</TypographyText>
            </Space>

            <RadioGroup
              v-if="viewMode !== 'forgot'"
              v-model:value="role"
              button-style="solid"
              class="mb-6 flex"
              @change="setFeedback()"
            >
              <RadioButton value="user" class="flex-1 text-center"><UserOutlined /> 普通用户</RadioButton>
              <RadioButton value="merchant" class="flex-1 text-center"><ShopOutlined /> 商家管理员</RadioButton>
            </RadioGroup>

            <Alert v-if="errorMsg" type="error" show-icon closable class="mb-4" :message="errorMsg" @close="errorMsg = ''" />
            <Alert v-if="successMsg" type="success" show-icon class="mb-4" :message="successMsg" />

            <AnimatePresence mode="wait">
              <motion.section
                :key="`${viewMode}-${forgotStep}`"
                :initial="{ opacity: 0, x: 18 }"
                :animate="{ opacity: 1, x: 0 }"
                :exit="{ opacity: 0, x: -18 }"
                :transition="{ duration: 0.2 }"
              >
                <Form v-if="viewMode === 'login'" layout="vertical" :model="loginForm" @finish="handleLogin">
                  <FormItem label="账号" name="username" :rules="[{ required: true, message: '请输入账号' }]">
                    <Input v-model:value="loginForm.username" size="large" autocomplete="username" placeholder="请输入账号" />
                  </FormItem>
                  <FormItem label="密码" name="password" :rules="[{ required: true, message: '请输入密码' }]">
                    <InputPassword v-model:value="loginForm.password" size="large" autocomplete="current-password" placeholder="请输入密码" />
                  </FormItem>
                  <div class="mb-5 flex items-center justify-between">
                    <Checkbox v-model:checked="rememberLogin">记住账号</Checkbox>
                    <Button type="link" class="!px-0" @click="switchMode('forgot')">忘记密码？</Button>
                  </div>
                  <Button type="primary" html-type="submit" size="large" block :loading="loading">登录</Button>
                  <Button v-if="role === 'user'" type="link" block class="!mt-3" @click="switchMode('register')">
                    没有账号？立即注册
                  </Button>
                </Form>

                <Form v-else-if="viewMode === 'register'" layout="vertical" :model="registerForm" @finish="handleRegister">
                  <FormItem label="账号" name="username" :rules="[{ required: true, message: '请输入账号' }]">
                    <Input v-model:value="registerForm.username" size="large" />
                  </FormItem>
                  <FormItem label="昵称" name="nickname" :rules="[{ required: true, message: '请输入昵称' }]">
                    <Input v-model:value="registerForm.nickname" size="large" />
                  </FormItem>
                  <FormItem label="密码" name="password" :rules="[{ required: true, min: 6, message: '密码至少 6 位' }]">
                    <InputPassword v-model:value="registerForm.password" size="large" autocomplete="new-password" />
                  </FormItem>
                  <FormItem label="确认密码" name="confirmPassword" :rules="[{ required: true, message: '请确认密码' }]">
                    <InputPassword v-model:value="registerForm.confirmPassword" size="large" autocomplete="new-password" />
                  </FormItem>
                  <Button type="primary" html-type="submit" size="large" block :loading="loading">创建账号</Button>
                  <Button type="link" block class="!mt-3" @click="switchMode('login')">返回登录</Button>
                </Form>

                <Form v-else layout="vertical" :model="forgotForm" @finish="forgotStep === 0 ? handleCheckUsername() : handleResetPassword()">
                  <Steps :current="forgotStep" size="small" class="mb-6" :items="[{ title: '验证账号' }, { title: '设置新密码' }]" />
                  <FormItem label="账号" name="username" :rules="[{ required: true, message: '请输入账号' }]">
                    <Input v-model:value="forgotForm.username" size="large" :disabled="forgotStep === 1" />
                  </FormItem>
                  <template v-if="forgotStep === 1">
                    <FormItem label="新密码" name="newPassword" :rules="[{ required: true, min: 6, message: '密码至少 6 位' }]">
                      <InputPassword v-model:value="forgotForm.newPassword" size="large" autocomplete="new-password" />
                    </FormItem>
                    <FormItem label="确认新密码" name="confirmPassword" :rules="[{ required: true, message: '请确认新密码' }]">
                      <InputPassword v-model:value="forgotForm.confirmPassword" size="large" autocomplete="new-password" />
                    </FormItem>
                  </template>
                  <Button type="primary" html-type="submit" size="large" block :loading="loading">
                    {{ forgotStep === 0 ? '验证账号' : '重置密码' }}
                  </Button>
                  <Button type="link" block class="!mt-3" @click="switchMode('login')">返回登录</Button>
                </Form>
              </motion.section>
            </AnimatePresence>
          </Card>
        </motion.div>
      </Col>
    </Row>
  </main>
</template>
