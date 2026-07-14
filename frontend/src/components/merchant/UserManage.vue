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
  password: string
  created_at: string
}

const loading = ref(false)
const error = ref<string | null>(null)
const users = ref<UserInfo[]>([])
const total = ref(0)
const keyword = ref('')
const roleFilter = ref('')

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
  if (keyword.value) {
    const kw = keyword.value.toLowerCase()
    list = list.filter(u =>
      u.username.toLowerCase().includes(kw) ||
      u.nickname.toLowerCase().includes(kw)
    )
  }
  return list
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
    total.value = data.total || 0
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
      // 创建
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
      // 更新
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

function toggleActive(user: UserInfo) {
  fetch(`${API_BASE}/api/merchant/users/${user.id}`, {
    method: 'PUT',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ is_active: !user.is_active }),
  }).then(res => {
    if (res.ok) fetchUsers()
  })
}

function copyPassword(password: string) {
  navigator.clipboard.writeText(password).then(() => {
    // 简单提示
  })
}

onMounted(() => {
  fetchUsers()
})
</script>

<template>
  <div class="user-manage">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar__left">
        <input
          v-model="keyword"
          class="search-input"
          placeholder="搜索用户名或昵称..."
          @input="fetchUsers"
        />
        <select v-model="roleFilter" class="role-select" @change="fetchUsers">
          <option value="">全部角色</option>
          <option value="user">普通用户</option>
          <option value="merchant">商家管理员</option>
        </select>
      </div>
      <button class="btn btn--primary" @click="openCreate">+ 新增用户</button>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="alert alert--error">{{ error }}</div>

    <!-- 用户表格 -->
    <div class="table-wrapper">
      <table class="user-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>用户名</th>
            <th>密码</th>
            <th>昵称</th>
            <th>角色</th>
            <th>手机</th>
            <th>邮箱</th>
            <th>状态</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="10" class="loading-cell">加载中...</td>
          </tr>
          <tr v-else-if="filteredUsers.length === 0">
            <td colspan="10" class="empty-cell">暂无用户数据</td>
          </tr>
          <tr v-for="user in filteredUsers" :key="user.id">
            <td>{{ user.id }}</td>
            <td><strong>{{ user.username }}</strong></td>
            <td>
              <span class="password-cell">
                <code>{{ user.password || '-' }}</code>
                <button
                  v-if="user.password"
                  class="copy-btn"
                  title="复制密码"
                  @click="copyPassword(user.password)"
                ></button>
              </span>
            </td>
            <td>{{ user.nickname }}</td>
            <td>
              <span :class="['role-badge', user.role === 'merchant' ? 'role-badge--merchant' : 'role-badge--user']">
                {{ user.role === 'merchant' ? '商家' : '用户' }}
              </span>
            </td>
            <td>{{ user.phone || '-' }}</td>
            <td>{{ user.email || '-' }}</td>
            <td>
              <button
                :class="['status-toggle', user.is_active ? 'status-toggle--active' : 'status-toggle--inactive']"
                @click="toggleActive(user)"
              >
                {{ user.is_active ? '启用' : '禁用' }}
              </button>
            </td>
            <td class="time-cell">{{ user.created_at ? user.created_at.slice(0, 19).replace('T', ' ') : '-' }}</td>
            <td>
              <div class="action-btns">
                <button class="btn btn--sm btn--edit" @click="openEdit(user)">编辑</button>
                <button class="btn btn--sm btn--delete" @click="confirmDelete(user)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 统计 -->
    <div class="stats-bar">
      <span>共 {{ filteredUsers.length }} 个用户</span>
      <span>商家: {{ users.filter(u => u.role === 'merchant').length }}</span>
      <span>普通用户: {{ users.filter(u => u.role === 'user').length }}</span>
    </div>

    <!-- 新增/编辑弹窗 -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <div class="modal__header">
          <h3>{{ modalTitle }}</h3>
          <button class="modal__close" @click="showModal = false">&times;</button>
        </div>
        <div class="modal__body">
          <div v-if="formError" class="alert alert--error">{{ formError }}</div>
          <div class="form-grid">
            <div class="form-group">
              <label>用户名</label>
              <input v-model="form.username" :disabled="editingId !== null" placeholder="登录账号" />
            </div>
            <div class="form-group">
              <label>密码</label>
              <input
                v-model="form.password"
                :type="editingId !== null ? 'password' : 'text'"
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

    <!-- 删除确认弹窗 -->
    <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
      <div class="modal modal--sm">
        <div class="modal__header">
          <h3>确认删除</h3>
          <button class="modal__close" @click="deleteTarget = null">&times;</button>
        </div>
        <div class="modal__body">
          <p>确定要删除用户 <strong>{{ deleteTarget.username }}</strong> 吗？此操作不可恢复。</p>
        </div>
        <div class="modal__footer">
          <button class="btn btn--secondary" @click="deleteTarget = null">取消</button>
          <button class="btn btn--danger" :disabled="deleting" @click="handleDelete">
            {{ deleting ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.user-manage {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar__left {
  display: flex;
  gap: 10px;
  align-items: center;
}

.search-input {
  padding: 8px 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
  font-size: 14px;
  width: 240px;
  background: rgba(255, 255, 255, 0.7);
  transition: border-color 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(217, 95, 45, 0.1);
}

.role-select {
  padding: 8px 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.7);
  cursor: pointer;
}

.btn {
  padding: 8px 18px;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn--primary {
  background: var(--brand);
  color: #fffaf0;
}

.btn--primary:hover:not(:disabled) {
  background: var(--brand-dark);
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

.btn--sm {
  padding: 5px 12px;
  font-size: 12px;
  border-radius: 8px;
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

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.alert {
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
}

.alert--error {
  background: #fdeceb;
  color: #c0392b;
  border: 1px solid rgba(192, 57, 43, 0.2);
}

.table-wrapper {
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--panel);
}

.user-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.user-table th {
  padding: 12px 14px;
  text-align: left;
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--line);
  background: rgba(0, 0, 0, 0.02);
  white-space: nowrap;
}

.user-table td {
  padding: 10px 14px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
  vertical-align: middle;
}

.user-table tr:last-child td {
  border-bottom: none;
}

.user-table tr:hover td {
  background: rgba(217, 95, 45, 0.03);
}

.loading-cell, .empty-cell {
  text-align: center;
  padding: 40px 20px !important;
  color: var(--muted);
  font-size: 14px;
}

.password-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.password-cell code {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
  background: rgba(0, 0, 0, 0.04);
  padding: 2px 8px;
  border-radius: 6px;
}

.copy-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  padding: 2px;
  opacity: 0.5;
  transition: opacity 0.2s;
}

.copy-btn:hover {
  opacity: 1;
}

.role-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.role-badge--merchant {
  background: rgba(217, 95, 45, 0.12);
  color: var(--brand-dark);
}

.role-badge--user {
  background: rgba(100, 100, 100, 0.08);
  color: #666;
}

.status-toggle {
  padding: 4px 12px;
  border: none;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.status-toggle--active {
  background: rgba(31, 138, 91, 0.1);
  color: #1f8a5b;
}

.status-toggle--active:hover {
  background: rgba(31, 138, 91, 0.2);
}

.status-toggle--inactive {
  background: rgba(192, 57, 43, 0.1);
  color: #c0392b;
}

.status-toggle--inactive:hover {
  background: rgba(192, 57, 43, 0.2);
}

.time-cell {
  font-size: 12px;
  color: var(--muted);
  white-space: nowrap;
}

.action-btns {
  display: flex;
  gap: 6px;
}

.stats-bar {
  display: flex;
  gap: 20px;
  font-size: 13px;
  color: var(--muted);
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal {
  background: var(--panel);
  border-radius: 18px;
  width: min(560px, 90vw);
  max-height: 85vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.modal--sm {
  width: min(400px, 90vw);
}

.modal__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px 0;
}

.modal__header h3 {
  margin: 0;
  font-size: 18px;
  color: var(--ink);
}

.modal__close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--muted);
  padding: 0 4px;
}

.modal__close:hover {
  color: var(--ink);
}

.modal__body {
  padding: 20px 24px;
}

.modal__body p {
  margin: 0;
  font-size: 14px;
  color: var(--ink);
  line-height: 1.6;
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
  gap: 14px;
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

.form-group input,
.form-group select {
  padding: 9px 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  background: rgba(255, 255, 255, 0.7);
  transition: border-color 0.2s;
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

@media (max-width: 760px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  .toolbar__left {
    flex-direction: column;
  }
  .search-input {
    width: 100%;
  }
}
</style>
