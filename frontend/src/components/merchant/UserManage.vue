<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function authHeaders(extra: Record<string, string> = {}): HeadersInit {
  const token = localStorage.getItem('token')
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  }
}

interface UserInfo {
  id: number
  username: string
  nickname: string
  role: string
  phone: string | null
  email: string | null
  is_active: boolean
  created_at: string
}

const loading = ref(false)
const error = ref<string | null>(null)
const users = ref<UserInfo[]>([])
const keyword = ref('')
const roleFilter = ref('')
const statusFilter = ref('')

// 弹窗状态
const showModal = ref(false)
const editingId = ref<number | null>(null)
const form = ref({
  username: '',
  password: '',
  nickname: '',
  role: 'user' as 'user' | 'merchant',
  phone: '',
  email: '',
})
const saving = ref(false)
const formError = ref<string | null>(null)

// 删除确认
const deleteTarget = ref<UserInfo | null>(null)
const deleting = ref(false)

const modalTitle = computed(() => editingId.value === null ? '新增用户' : '编辑用户')

const filteredUsers = computed(() => {
  let list = users.value
  if (roleFilter.value) {
    list = list.filter(u => u.role === roleFilter.value)
  }
  if (statusFilter.value) {
    const active = statusFilter.value === 'active'
    list = list.filter(u => u.is_active === active)
  }
  if (keyword.value) {
    const kw = keyword.value.toLowerCase()
    list = list.filter(u =>
      u.username.toLowerCase().includes(kw) ||
      u.nickname.toLowerCase().includes(kw) ||
      (u.phone && u.phone.includes(kw)) ||
      (u.email && u.email.toLowerCase().includes(kw))
    )
  }
  return list
})

const stats = computed(() => {
  const total = users.value.length
  const merchant = users.value.filter(u => u.role === 'merchant').length
  const user = users.value.filter(u => u.role === 'user').length
  const active = users.value.filter(u => u.is_active).length
  const inactive = total - active
  return [
    { key: 'total', label: '总用户', value: total, color: 'var(--brand)' },
    { key: 'merchant', label: '商家管理员', value: merchant, color: '#1677ff' },
    { key: 'user', label: '普通用户', value: user, color: 'var(--green)' },
    { key: 'inactive', label: '已禁用', value: inactive, color: '#999' },
  ]
})

async function fetchUsers() {
  loading.value = true
  error.value = null
  try {
    const params = new URLSearchParams()
    if (roleFilter.value) params.set('role', roleFilter.value)
    if (keyword.value) params.set('keyword', keyword.value)
    const res = await fetch(`${API_BASE}/api/merchant/users?${params}`, {
      headers: authHeaders(),
    })
    if (!res.ok) throw new Error('获取用户列表失败')
    const data = await res.json()
    users.value = data.users || []
  } catch (e) {
    error.value = e instanceof Error ? e.message : '未知错误'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = { username: '', password: '', nickname: '', role: 'user', phone: '', email: '' }
  formError.value = null
  showModal.value = true
}

function openEdit(user: UserInfo) {
  editingId.value = user.id
  form.value = {
    username: user.username,
    password: '',
    nickname: user.nickname,
    role: user.role as 'user' | 'merchant',
    phone: user.phone || '',
    email: user.email || '',
  }
  formError.value = null
  showModal.value = true
}

async function handleSave() {
  saving.value = true
  formError.value = null
  try {
    if (editingId.value === null) {
      if (!form.value.username || !form.value.password) {
        formError.value = '用户名和密码不能为空'
        saving.value = false
        return
      }
      const res = await fetch(`${API_BASE}/api/merchant/users`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(form.value),
      })
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.message || '创建失败')
      }
    } else {
      const body: Record<string, unknown> = {
        nickname: form.value.nickname,
        role: form.value.role,
        phone: form.value.phone,
        email: form.value.email,
      }
      if (form.value.password) {
        body.password = form.value.password
      }
      const res = await fetch(`${API_BASE}/api/merchant/users/${editingId.value}`, {
        method: 'PUT',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.message || '更新失败')
      }
    }
    showModal.value = false
    await fetchUsers()
  } catch (e) {
    formError.value = e instanceof Error ? e.message : '操作失败'
  } finally {
    saving.value = false
  }
}

function confirmDelete(user: UserInfo) {
  deleteTarget.value = user
}

async function handleDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    const res = await fetch(`${API_BASE}/api/merchant/users/${deleteTarget.value.id}`, {
      method: 'DELETE',
      headers: authHeaders(),
    })
    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.message || '删除失败')
    }
    deleteTarget.value = null
    await fetchUsers()
  } catch (e) {
    alert(e instanceof Error ? e.message : '删除失败')
  } finally {
    deleting.value = false
  }
}

function getCurrentUserId(): number | null {
  const stored = localStorage.getItem('userInfo')
  if (!stored) return null
  try {
    const info = JSON.parse(stored)
    return info.id ?? null
  } catch {
    return null
  }
}

function toggleActive(user: UserInfo) {
  if (user.id === getCurrentUserId() && user.is_active) {
    alert('不能禁用自己当前登录的账号')
    return
  }
  fetch(`${API_BASE}/api/merchant/users/${user.id}`, {
    method: 'PUT',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ is_active: !user.is_active }),
  }).then(res => {
    if (res.ok) fetchUsers()
  })
}

function formatTime(time: string | null): string {
  if (!time) return '-'
  return time.replace('T', ' ').slice(0, 19)
}

onMounted(() => {
  fetchUsers()
})
</script>

<template>
  <div class="user-manage">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header__icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
          <circle cx="9" cy="7" r="4"></circle>
          <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
          <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
        </svg>
      </div>
      <div class="page-header__text">
        <h1>用户管理</h1>
        <p>管理平台普通用户与商家管理员账号，支持启用/禁用、编辑与删除</p>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div v-for="stat in stats" :key="stat.key" class="stat-card">
        <span class="stat-value" :style="{ color: stat.color }">{{ stat.value }}</span>
        <span class="stat-label">{{ stat.label }}</span>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar__filters">
        <input
          v-model="keyword"
          class="search-input"
          placeholder="搜索用户名、昵称、手机号或邮箱..."
          @keydown.enter="fetchUsers"
        />
        <select v-model="roleFilter" class="filter-select" @change="fetchUsers">
          <option value="">全部角色</option>
          <option value="user">普通用户</option>
          <option value="merchant">商家管理员</option>
        </select>
        <select v-model="statusFilter" class="filter-select" @change="fetchUsers">
          <option value="">全部状态</option>
          <option value="active">已启用</option>
          <option value="inactive">已禁用</option>
        </select>
      </div>
      <button class="btn btn--primary" @click="openCreate">
        <span class="btn-icon">+</span>
        新增用户
      </button>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="alert alert--error">{{ error }}</div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-wrap">
      <div class="spinner"></div>
      <p>正在加载用户数据...</p>
    </div>

    <!-- 用户卡片网格 -->
    <div v-else-if="filteredUsers.length > 0" class="user-grid">
      <div v-for="user in filteredUsers" :key="user.id" class="user-card">
        <div class="user-card__header">
          <div class="user-card__avatar">
            {{ user.nickname.charAt(0) || user.username.charAt(0) }}
          </div>
          <div class="user-card__info">
            <div class="user-card__name">{{ user.nickname || user.username }}</div>
            <div class="user-card__username">@{{ user.username }}</div>
          </div>
          <span :class="['status-badge', user.is_active ? 'status-badge--active' : 'status-badge--inactive']">
            {{ user.is_active ? '启用' : '禁用' }}
          </span>
        </div>

        <div class="user-card__meta">
          <div class="meta-item">
            <span class="meta-label">角色</span>
            <span :class="['role-badge', user.role === 'merchant' ? 'role-badge--merchant' : 'role-badge--user']">
              {{ user.role === 'merchant' ? '商家' : '用户' }}
            </span>
          </div>
          <div class="meta-item">
            <span class="meta-label">手机</span>
            <span class="meta-value">{{ user.phone || '-' }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">邮箱</span>
            <span class="meta-value">{{ user.email || '-' }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">创建时间</span>
            <span class="meta-value">{{ formatTime(user.created_at) }}</span>
          </div>
        </div>

        <div class="user-card__actions">
          <button
            :class="['btn btn--sm', user.is_active ? 'btn--warning' : 'btn--success']"
            @click="toggleActive(user)"
          >
            {{ user.is_active ? '禁用' : '启用' }}
          </button>
          <button class="btn btn--sm btn--edit" @click="openEdit(user)">编辑</button>
          <button class="btn btn--sm btn--delete" @click="confirmDelete(user)">删除</button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
          <circle cx="9" cy="7" r="4"></circle>
        </svg>
      </div>
      <h3>暂无用户</h3>
      <p>当前筛选条件下没有找到用户数据</p>
    </div>

    <!-- 新增/编辑弹窗 -->
    <transition name="modal">
      <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
        <div class="modal">
          <div class="modal__header">
            <h3>{{ modalTitle }}</h3>
            <button class="modal__close" @click="showModal = false">×</button>
          </div>
          <div class="modal__body">
            <div v-if="formError" class="alert alert--error">{{ formError }}</div>
            <div class="form-grid">
              <div class="form-group">
                <label>用户名 <span class="required">*</span></label>
                <input v-model="form.username" :disabled="editingId !== null" placeholder="登录账号" />
              </div>
              <div class="form-group">
                <label>{{ editingId !== null ? '新密码' : '密码' }} <span v-if="editingId === null" class="required">*</span></label>
                <input
                  v-model="form.password"
                  type="password"
                  :placeholder="editingId !== null ? '留空则不修改密码' : '至少6位'"
                />
              </div>
              <div class="form-group">
                <label>昵称</label>
                <input v-model="form.nickname" placeholder="用户昵称" />
              </div>
              <div class="form-group">
                <label>角色</label>
                <select v-model="form.role">
                  <option value="user">普通用户</option>
                  <option value="merchant">商家管理员</option>
                </select>
              </div>
              <div class="form-group">
                <label>手机号</label>
                <input v-model="form.phone" placeholder="选填" />
              </div>
              <div class="form-group">
                <label>邮箱</label>
                <input v-model="form.email" placeholder="选填" />
              </div>
            </div>
          </div>
          <div class="modal__footer">
            <button class="btn btn--secondary" @click="showModal = false">取消</button>
            <button class="btn btn--primary" :disabled="saving" @click="handleSave">
              {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- 删除确认弹窗 -->
    <transition name="modal">
      <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
        <div class="modal modal--sm">
          <div class="modal__header">
            <h3>确认删除</h3>
            <button class="modal__close" @click="deleteTarget = null">×</button>
          </div>
          <div class="modal__body">
            <div class="confirm-body">
              <div class="confirm-icon confirm-icon--danger">×</div>
              <p class="confirm-text">确定要删除该用户吗？</p>
              <p class="confirm-hint">用户 <strong>{{ deleteTarget?.nickname || deleteTarget?.username }}</strong> 将被永久删除，此操作不可恢复。</p>
            </div>
          </div>
          <div class="modal__footer">
            <button class="btn btn--secondary" @click="deleteTarget = null">取消</button>
            <button class="btn btn--danger" :disabled="deleting" @click="handleDelete">
              {{ deleting ? '删除中...' : '确认删除' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.user-manage {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 18px;
}

.page-header__icon {
  width: 54px;
  height: 54px;
  border-radius: 18px;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark, #8a3a1f));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 12px 28px rgba(217, 95, 45, 0.28);
  flex-shrink: 0;
}

.page-header__icon svg {
  width: 28px;
  height: 28px;
}

.page-header__text h1 {
  font-size: 28px;
  margin: 0 0 6px 0;
  color: var(--ink);
}

.page-header__text p {
  color: var(--muted);
  margin: 0;
  font-size: 15px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 20px;
  border-radius: 18px;
  background: var(--panel);
  border: 1px solid var(--line);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.stat-value {
  font-size: 32px;
  font-weight: 800;
  line-height: 1;
}

.stat-label {
  font-size: 14px;
  color: var(--muted);
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar__filters {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.search-input {
  padding: 10px 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  font-size: 14px;
  width: 260px;
  background: var(--panel);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(217, 95, 45, 0.1);
}

.filter-select {
  padding: 10px 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  font-size: 14px;
  background: var(--panel);
  cursor: pointer;
  transition: border-color 0.2s;
}

.filter-select:focus {
  outline: none;
  border-color: var(--brand);
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.btn-icon {
  font-size: 18px;
  line-height: 1;
}

.btn--primary {
  background: linear-gradient(135deg, var(--brand), var(--brand-dark, #8a3a1f));
  color: #fff;
  box-shadow: 0 8px 20px rgba(217, 95, 45, 0.25);
}

.btn--primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 12px 26px rgba(217, 95, 45, 0.32);
}

.btn--secondary {
  background: transparent;
  border: 1px solid var(--line);
  color: var(--muted);
}

.btn--secondary:hover {
  border-color: var(--brand);
  color: var(--brand);
}

.btn--danger {
  background: #c0392b;
  color: #fff;
}

.btn--danger:hover:not(:disabled) {
  background: #a93226;
}

.btn--warning {
  background: rgba(250, 173, 20, 0.12);
  color: #d48806;
}

.btn--warning:hover {
  background: rgba(250, 173, 20, 0.2);
}

.btn--success {
  background: rgba(31, 138, 91, 0.12);
  color: #1f8a5b;
}

.btn--success:hover {
  background: rgba(31, 138, 91, 0.2);
}

.btn--edit {
  background: rgba(217, 95, 45, 0.1);
  color: var(--brand);
}

.btn--edit:hover {
  background: rgba(217, 95, 45, 0.2);
}

.btn--delete {
  background: rgba(192, 57, 43, 0.08);
  color: #c0392b;
}

.btn--delete:hover {
  background: rgba(192, 57, 43, 0.15);
}

.btn--sm {
  padding: 7px 14px;
  font-size: 13px;
  border-radius: 10px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.alert {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
}

.alert--error {
  background: #fff0f0;
  color: #c33;
  border: 1px solid rgba(192, 57, 43, 0.15);
}

.loading-wrap {
  text-align: center;
  padding: 60px 20px;
  color: var(--muted);
}

.spinner {
  width: 44px;
  height: 44px;
  border: 3px solid var(--line);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.user-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 18px;
}

.user-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.user-card:hover {
  transform: translateY(-2px);
  border-color: rgba(217, 95, 45, 0.3);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.user-card__header {
  display: flex;
  align-items: center;
  gap: 14px;
}

.user-card__avatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark, #8a3a1f));
  color: #fff;
  display: inline-grid;
  place-items: center;
  font-size: 20px;
  font-weight: 700;
  flex-shrink: 0;
}

.user-card__info {
  flex: 1;
  min-width: 0;
}

.user-card__name {
  font-size: 17px;
  font-weight: 700;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-card__username {
  font-size: 13px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 700;
}

.status-badge--active {
  background: rgba(31, 138, 91, 0.12);
  color: #1f8a5b;
}

.status-badge--inactive {
  background: rgba(192, 57, 43, 0.1);
  color: #c0392b;
}

.user-card__meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-size: 12px;
  color: var(--muted);
}

.meta-value {
  font-size: 14px;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.role-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  width: fit-content;
}

.role-badge--merchant {
  background: rgba(217, 95, 45, 0.12);
  color: var(--brand-dark);
}

.role-badge--user {
  background: rgba(100, 100, 100, 0.08);
  color: #666;
}

.user-card__actions {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--muted);
  text-align: center;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
}

.empty-icon {
  width: 76px;
  height: 76px;
  color: var(--line);
  margin-bottom: 16px;
}

.empty-icon svg {
  width: 100%;
  height: 100%;
}

.empty-state h3 {
  font-size: 20px;
  color: var(--ink);
  margin: 0 0 8px;
}

.empty-state p {
  font-size: 14px;
  margin: 0;
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 20px;
  backdrop-filter: blur(3px);
}

.modal {
  background: var(--panel);
  border-radius: 20px;
  width: min(520px, 100%);
  max-height: 90vh;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.modal--sm {
  width: min(420px, 100%);
}

.modal__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--line);
}

.modal__header h3 {
  margin: 0;
  font-size: 18px;
  color: var(--ink);
}

.modal__close {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.05);
  color: var(--muted);
  font-size: 22px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.modal__close:hover {
  background: rgba(0, 0, 0, 0.12);
  color: var(--ink);
}

.modal__body {
  padding: 24px;
  overflow-y: auto;
}

.modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 0 24px 20px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
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

.required {
  color: var(--brand);
}

.form-group input,
.form-group select {
  padding: 11px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  font-size: 14px;
  font-family: inherit;
  background: #fff;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(217, 95, 45, 0.1);
}

.form-group input:disabled {
  background: rgba(0, 0, 0, 0.04);
  color: var(--muted);
}

.confirm-body {
  text-align: center;
  padding: 8px 8px 16px;
}

.confirm-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  color: #fff;
  font-size: 32px;
  display: inline-grid;
  place-items: center;
  margin-bottom: 16px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12);
}

.confirm-icon--danger {
  background: linear-gradient(135deg, #c0392b, #a93226);
}

.confirm-text {
  font-size: 17px;
  font-weight: 700;
  color: var(--ink);
  margin: 0 0 8px;
}

.confirm-hint {
  font-size: 14px;
  color: var(--muted);
  margin: 0;
  line-height: 1.6;
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

@media (max-width: 820px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar__filters {
    flex-direction: column;
  }

  .search-input,
  .filter-select {
    width: 100%;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
