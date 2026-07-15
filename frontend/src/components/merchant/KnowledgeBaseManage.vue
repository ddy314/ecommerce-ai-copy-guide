<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/** 携带鉴权头的请求头 */
function authHeaders(extra: Record<string, string> = {}): HeadersInit {
  const token = localStorage.getItem('token')
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  }
}

interface KnowledgeItem {
  id: number
  title: string
  content: string
  category: string
  product_id?: number | null
  product_name?: string | null
  keywords?: string[] | string | null
  created_at?: string
}

interface ProductOption {
  id: number
  name: string
  category?: string
}

interface KnowledgeForm {
  category: string
  product_id: number | string
  title: string
  content: string
  keywords: string
}

const emptyForm = (): KnowledgeForm => ({
  category: 'spec',
  product_id: '',
  title: '',
  content: '',
  keywords: '',
})

/** 知识类型配置 */
const categoryConfig: Record<string, { label: string; color: string }> = {
  spec: { label: '规格参数', color: '#d95f2d' },
  faq: { label: '常见问题', color: '#1f8a5b' },
  after_sale: { label: '售后政策', color: '#bc8321' },
  policy: { label: '政策', color: '#5d6dff' },
}

const builtinCategoryOptions = [
  { value: 'spec', label: '规格参数' },
  { value: 'faq', label: '常见问题' },
  { value: 'after_sale', label: '售后政策' },
  { value: 'policy', label: '政策' },
]

const categoryOptions = ref<{ value: string; label: string }[]>([...builtinCategoryOptions])

const CUSTOM_CATEGORY_VALUE = '__custom__'

// 列表状态
const loading = ref(false)
const error = ref<string | null>(null)
const items = ref<KnowledgeItem[]>([])
const selectedCategory = ref('')
const selectedProduct = ref<number | string>('')
const searchKeyword = ref('')

// 商品下拉选项
const products = ref<ProductOption[]>([])

// 新增/编辑弹窗
const showModal = ref(false)
const form = ref<KnowledgeForm>(emptyForm())
const saving = ref(false)
const formError = ref<string | null>(null)
const editingId = ref<number | null>(null)
const customCategory = ref('')

const isCustomCategory = computed(() => form.value.category === CUSTOM_CATEGORY_VALUE)
const modalTitle = computed(() => (editingId.value ? '编辑知识条目' : '新增知识条目'))

// 自动构建弹窗
const showAutoBuild = ref(false)
const autoBuildProductId = ref<number | string>('')
const autoBuilding = ref(false)
const autoBuildError = ref<string | null>(null)
const autoBuildResult = ref<string | null>(null)

// 删除确认
const deleteTarget = ref<KnowledgeItem | null>(null)
const deleting = ref(false)

function categoryLabel(cat: string): string {
  return categoryConfig[cat]?.label || cat
}

function categoryColor(cat: string): string {
  return categoryConfig[cat]?.color || '#888'
}

function parseKeywords(kw: unknown): string[] {
  if (Array.isArray(kw)) return kw
  if (typeof kw === 'string' && kw.trim()) {
    return kw.split(/[,，;；\n]/).map((s) => s.trim()).filter(Boolean)
  }
  return []
}

const filteredItems = computed(() => {
  return items.value
})

async function loadProducts() {
  try {
    const params = new URLSearchParams()
    params.set('page', '1')
    params.set('page_size', '1000')
    const res = await fetch(
      `${API_BASE}/api/merchant/products?${params.toString()}`,
      { headers: authHeaders() },
    )
    if (res.ok) {
      const data = await res.json()
      const list = data.products || data.items || data.list || []
      products.value = list.map((p: any) => ({
        id: p.id,
        name: p.name,
        category: p.category,
      }))
    }
  } catch (e) {
    console.error('加载商品列表失败:', e)
  }
}

async function loadCategories() {
  try {
    const res = await fetch(`${API_BASE}/api/merchant/knowledge/categories`, {
      headers: authHeaders(),
    })
    if (!res.ok) return
    const data = await res.json()
    const existing = new Set(builtinCategoryOptions.map((o) => o.value))
    const dynamic = (data.categories || [])
      .filter((c: string) => c && !existing.has(c))
      .map((c: string) => ({ value: c, label: c }))
    categoryOptions.value = [...builtinCategoryOptions, ...dynamic]
  } catch (e) {
    console.error('加载知识类型失败:', e)
  }
}

async function loadKnowledge() {
  loading.value = true
  error.value = null
  try {
    const params = new URLSearchParams()
    if (selectedProduct.value !== '') params.set('product_id', String(selectedProduct.value))
    if (selectedCategory.value) params.set('category', selectedCategory.value)
    if (searchKeyword.value.trim()) params.set('keyword', searchKeyword.value.trim())

    const res = await fetch(
      `${API_BASE}/api/merchant/knowledge?${params.toString()}`,
      { headers: authHeaders() },
    )
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${res.status}`)
    }
    const data = await res.json()
    items.value = data.entries || data.items || data.knowledge || data.list || data || []
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载知识库失败'
  } finally {
    loading.value = false
  }
}

function applyFilter() {
  loadKnowledge()
}

function openCreate() {
  editingId.value = null
  customCategory.value = ''
  form.value = emptyForm()
  formError.value = null
  showModal.value = true
}

function openEdit(item: KnowledgeItem) {
  editingId.value = item.id
  const isBuiltin = builtinCategoryOptions.some((o) => o.value === item.category)
  customCategory.value = isBuiltin ? '' : item.category
  form.value = {
    category: isBuiltin ? item.category : CUSTOM_CATEGORY_VALUE,
    product_id: item.product_id ?? '',
    title: item.title,
    content: item.content,
    keywords: parseKeywords(item.keywords).join(', '),
  }
  formError.value = null
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  editingId.value = null
  customCategory.value = ''
}

function resolveCategory(): string {
  if (form.value.category === CUSTOM_CATEGORY_VALUE) {
    const cat = customCategory.value.trim()
    return cat || 'faq'
  }
  return form.value.category
}

async function handleSubmit() {
  if (!form.value.title.trim()) {
    formError.value = '请填写标题'
    return
  }
  if (!form.value.content.trim()) {
    formError.value = '请填写内容'
    return
  }
  const category = resolveCategory()
  if (form.value.category === CUSTOM_CATEGORY_VALUE && !customCategory.value.trim()) {
    formError.value = '请填写新类型名称'
    return
  }
  saving.value = true
  formError.value = null
  try {
    const payload = {
      category,
      product_id: form.value.product_id === '' ? null : Number(form.value.product_id),
      title: form.value.title.trim(),
      content: form.value.content.trim(),
      keywords: parseKeywords(form.value.keywords),
    }
    const url = editingId.value
      ? `${API_BASE}/api/merchant/knowledge/${editingId.value}`
      : `${API_BASE}/api/merchant/knowledge`
    const res = await fetch(url, {
      method: editingId.value ? 'PUT' : 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${res.status}`)
    }
    showModal.value = false
    editingId.value = null
    customCategory.value = ''
    await loadCategories()
    await loadKnowledge()
  } catch (e) {
    formError.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

function askDelete(item: KnowledgeItem) {
  deleteTarget.value = item
}

function cancelDelete() {
  deleteTarget.value = null
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    const res = await fetch(
      `${API_BASE}/api/merchant/knowledge/${deleteTarget.value.id}`,
      { method: 'DELETE', headers: authHeaders() },
    )
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${res.status}`)
    }
    deleteTarget.value = null
    await loadKnowledge()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  } finally {
    deleting.value = false
  }
}

function openAutoBuild() {
  autoBuildProductId.value = ''
  autoBuildError.value = null
  autoBuildResult.value = null
  showAutoBuild.value = true
}

function closeAutoBuild() {
  showAutoBuild.value = false
}

async function handleAutoBuild() {
  if (autoBuildProductId.value === '') {
    autoBuildError.value = '请选择商品'
    return
  }
  autoBuilding.value = true
  autoBuildError.value = null
  autoBuildResult.value = null
  try {
    const res = await fetch(
      `${API_BASE}/api/merchant/knowledge/auto-build/${autoBuildProductId.value}`,
      { method: 'POST', headers: authHeaders() },
    )
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${res.status}`)
    }
    const data = await res.json()
    const count = data.created || data.count || data.total || 0
    autoBuildResult.value = `已为该商品自动构建 ${count} 条知识条目`
    await loadKnowledge()
  } catch (e) {
    autoBuildError.value = e instanceof Error ? e.message : '自动构建失败'
  } finally {
    autoBuilding.value = false
  }
}

function productName(id?: number | null): string {
  if (!id) return '通用'
  const p = products.value.find((x) => x.id === id)
  return p ? p.name : `商品#${id}`
}

onMounted(() => {
  loadProducts()
  loadCategories()
  loadKnowledge()
})
</script>

<template>
  <div class="kb-page">
    <!-- 顶部操作区 -->
    <div class="kb-toolbar">
      <div class="kb-filters">
        <select v-model="selectedCategory" class="kb-select" @change="applyFilter">
          <option value="">全部类型</option>
          <option v-for="opt in categoryOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <select v-model="selectedProduct" class="kb-select" @change="applyFilter">
          <option value="">全部商品</option>
          <option v-for="p in products" :key="p.id" :value="p.id">
            {{ p.name }}
          </option>
        </select>
        <input
          v-model="searchKeyword"
          type="text"
          class="kb-select kb-search"
          placeholder="搜索标题 / 内容 / 关键词"
          @keyup.enter="applyFilter"
        />
      </div>
      <div class="kb-actions">
        <button class="kb-btn kb-btn--ghost" @click="openAutoBuild">从商品自动构建</button>
        <button class="kb-btn kb-btn--primary" @click="openCreate">+ 新增知识条目</button>
      </div>
    </div>

    <!-- 类型筛选标签 -->
    <div class="kb-tags">
      <button
        :class="['kb-tag', { active: !selectedCategory }]"
        @click="selectedCategory = ''; applyFilter()"
      >
        全部
      </button>
      <button
        v-for="opt in categoryOptions"
        :key="opt.value"
        :class="['kb-tag', { active: selectedCategory === opt.value }]"
        @click="selectedCategory = opt.value; applyFilter()"
      >
        {{ opt.label }}
      </button>
    </div>

    <div v-if="error" class="kb-error">{{ error }}</div>

    <!-- 加载中 -->
    <div v-if="loading" class="kb-loading">
      <div class="kb-spinner"></div>
      <p>加载中...</p>
    </div>

    <!-- 知识列表 -->
    <div v-else class="kb-list">
      <div v-for="item in filteredItems" :key="item.id" class="kb-card">
        <div class="kb-card__head">
          <span
            class="kb-type-badge"
            :style="{ background: categoryColor(item.category), color: '#fff' }"
          >
            {{ categoryLabel(item.category) }}
          </span>
          <h4 class="kb-card__title">{{ item.title }}</h4>
          <div class="kb-card__actions">
            <button class="kb-edit" @click="openEdit(item)">编辑</button>
            <button class="kb-del" @click="askDelete(item)">删除</button>
          </div>
        </div>
        <p class="kb-card__content">{{ item.content }}</p>
        <div class="kb-card__foot">
          <span class="kb-product">
            关联商品：<strong>{{ productName(item.product_id) }}</strong>
          </span>
          <div v-if="parseKeywords(item.keywords).length" class="kb-keywords">
            <span
              v-for="kw in parseKeywords(item.keywords)"
              :key="kw"
              class="kb-kw-tag"
            >{{ kw }}</span>
          </div>
        </div>
      </div>
      <div v-if="filteredItems.length === 0" class="kb-empty">
        暂无知识条目，点击「新增知识条目」或「从商品自动构建」添加
      </div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <div v-if="showModal" class="kb-modal-mask" @click.self="closeModal">
      <div class="kb-modal">
        <div class="kb-modal__head">
          <h3>{{ modalTitle }}</h3>
          <button class="kb-modal__close" @click="closeModal">×</button>
        </div>
        <div class="kb-modal__body">
          <div v-if="formError" class="kb-error">{{ formError }}</div>
          <div class="kb-form">
            <div class="kb-form-group">
              <label>类型 <span class="kb-req">*</span></label>
              <select v-model="form.category">
                <option v-for="opt in categoryOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
                <option :value="CUSTOM_CATEGORY_VALUE">+ 新增类型</option>
              </select>
            </div>
            <div v-if="isCustomCategory" class="kb-form-group kb-form-group--full">
              <label>新类型名称 <span class="kb-req">*</span></label>
              <input
                v-model="customCategory"
                type="text"
                placeholder="例如：物流说明、使用教程"
              />
            </div>
            <div class="kb-form-group">
              <label>关联商品</label>
              <select v-model="form.product_id">
                <option value="">通用（不关联）</option>
                <option v-for="p in products" :key="p.id" :value="p.id">
                  {{ p.name }}
                </option>
              </select>
            </div>
            <div class="kb-form-group kb-form-group--full">
              <label>标题 <span class="kb-req">*</span></label>
              <input v-model="form.title" type="text" placeholder="例如：坐垫尺寸说明" />
            </div>
            <div class="kb-form-group kb-form-group--full">
              <label>内容 <span class="kb-req">*</span></label>
              <textarea v-model="form.content" rows="5" placeholder="请输入知识内容..."></textarea>
            </div>
            <div class="kb-form-group kb-form-group--full">
              <label>关键词（逗号分隔）</label>
              <input v-model="form.keywords" type="text" placeholder="尺寸,坐垫,规格" />
            </div>
          </div>
        </div>
        <div class="kb-modal__foot">
          <button class="kb-btn kb-btn--ghost" @click="closeModal">取消</button>
          <button class="kb-btn kb-btn--primary" :disabled="saving" @click="handleSubmit">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 自动构建弹窗 -->
    <div v-if="showAutoBuild" class="kb-modal-mask" @click.self="closeAutoBuild">
      <div class="kb-modal kb-modal--sm">
        <div class="kb-modal__head">
          <h3>从商品自动构建知识</h3>
          <button class="kb-modal__close" @click="closeAutoBuild">×</button>
        </div>
        <div class="kb-modal__body">
          <div v-if="autoBuildError" class="kb-error">{{ autoBuildError }}</div>
          <p class="kb-confirm-text">
            选择一个商品，系统将根据商品信息自动生成规格参数、常见问题等知识条目。
          </p>
          <div class="kb-form-group">
            <label>选择商品 <span class="kb-req">*</span></label>
            <select v-model="autoBuildProductId">
              <option value="">请选择商品</option>
              <option v-for="p in products" :key="p.id" :value="p.id">
                {{ p.name }}
              </option>
            </select>
          </div>
          <div v-if="autoBuildResult" class="kb-success">{{ autoBuildResult }}</div>
        </div>
        <div class="kb-modal__foot">
          <button class="kb-btn kb-btn--ghost" @click="closeAutoBuild">关闭</button>
          <button class="kb-btn kb-btn--primary" :disabled="autoBuilding" @click="handleAutoBuild">
            {{ autoBuilding ? '构建中...' : '开始构建' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <div v-if="deleteTarget" class="kb-modal-mask" @click.self="cancelDelete">
      <div class="kb-modal kb-modal--sm">
        <div class="kb-modal__head">
          <h3>确认删除</h3>
          <button class="kb-modal__close" @click="cancelDelete">×</button>
        </div>
        <div class="kb-modal__body">
          <p class="kb-confirm-text">
            确定要删除知识条目「<strong>{{ deleteTarget.title }}</strong>」吗？此操作不可恢复。
          </p>
        </div>
        <div class="kb-modal__foot">
          <button class="kb-btn kb-btn--ghost" @click="cancelDelete">取消</button>
          <button class="kb-btn kb-btn--danger" :disabled="deleting" @click="confirmDelete">
            {{ deleting ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kb-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 工具栏 */
.kb-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.kb-filters {
  display: flex;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.kb-select {
  flex: 1;
  min-width: 0;
  padding: 9px 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  background: var(--panel);
  color: var(--ink);
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  box-sizing: border-box;
}

.kb-select:focus {
  outline: none;
  border-color: var(--brand);
}

.kb-actions {
  display: flex;
  gap: 10px;
}

/* 按钮 */
.kb-btn {
  padding: 9px 18px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--panel);
  color: var(--ink);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.kb-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.kb-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.kb-btn--primary {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}

.kb-btn--primary:hover:not(:disabled) {
  background: var(--brand-dark);
  border-color: var(--brand-dark);
}

.kb-btn--ghost {
  background: transparent;
}

.kb-btn--danger {
  background: #e4393c;
  color: #fff;
  border-color: #e4393c;
}

.kb-btn--danger:hover:not(:disabled) {
  background: #c5282b;
  border-color: #c5282b;
}

/* 类型标签 */
.kb-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.kb-tag {
  padding: 6px 14px;
  border: 1px solid var(--line);
  border-radius: 20px;
  background: transparent;
  color: var(--muted);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.kb-tag:hover {
  border-color: var(--brand);
  color: var(--brand);
}

.kb-tag.active {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}

/* 加载 */
.kb-loading {
  text-align: center;
  padding: 48px 0;
  color: var(--muted);
}

.kb-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--line);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: kb-spin 1s linear infinite;
  margin: 0 auto 12px;
}

@keyframes kb-spin {
  to {
    transform: rotate(360deg);
  }
}

.kb-error {
  background: #fee;
  color: #c33;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
}

.kb-success {
  background: rgba(82, 196, 26, 0.12);
  color: var(--green, #1f8a5b);
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
  margin-top: 12px;
}

/* 列表 */
.kb-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.kb-card {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--panel);
  padding: 16px 18px;
  transition: box-shadow 0.2s;
}

.kb-card:hover {
  box-shadow: var(--shadow, 0 2px 8px rgba(0, 0, 0, 0.08));
}

.kb-card__head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.kb-card__actions {
  display: flex;
  gap: 8px;
  flex: 0 0 auto;
}

.kb-type-badge {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  flex: 0 0 auto;
}

.kb-card__title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
  flex: 1;
  min-width: 0;
}

.kb-edit,
.kb-del {
  padding: 4px 12px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  flex: 0 0 auto;
}

.kb-edit {
  border: 1px solid rgba(31, 138, 91, 0.4);
  background: transparent;
  color: #1f8a5b;
}

.kb-edit:hover {
  background: #1f8a5b;
  color: #fff;
}

.kb-del {
  border: 1px solid rgba(228, 57, 60, 0.4);
  background: transparent;
  color: #e4393c;
}

.kb-del:hover {
  background: #e4393c;
  color: #fff;
}

.kb-search::placeholder {
  color: var(--muted);
}

.kb-card__content {
  margin: 0 0 12px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--ink);
  white-space: pre-wrap;
  word-break: break-word;
}

.kb-card__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.kb-product {
  font-size: 13px;
  color: var(--muted);
}

.kb-product strong {
  color: var(--brand-dark);
}

.kb-keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.kb-kw-tag {
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  background: rgba(217, 95, 45, 0.1);
  color: var(--brand-dark);
}

.kb-empty {
  text-align: center;
  color: var(--muted);
  padding: 48px 0;
  border: 1px dashed var(--line);
  border-radius: 14px;
}

/* 弹窗 */
.kb-modal-mask {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(33, 26, 20, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.kb-modal {
  width: min(560px, 100%);
  max-height: 90vh;
  overflow-y: auto;
  background: var(--panel);
  border-radius: 18px;
  box-shadow: var(--shadow, 0 2px 8px rgba(0, 0, 0, 0.08));
  display: flex;
  flex-direction: column;
}

.kb-modal--sm {
  width: min(440px, 100%);
}

.kb-modal__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid var(--line);
}

.kb-modal__head h3 {
  margin: 0;
  font-size: 18px;
  color: var(--brand-dark);
}

.kb-modal__close {
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 8px;
  background: transparent;
  font-size: 22px;
  line-height: 1;
  color: var(--muted);
  cursor: pointer;
  transition: all 0.2s;
}

.kb-modal__close:hover {
  background: rgba(217, 95, 45, 0.1);
  color: var(--brand);
}

.kb-modal__body {
  padding: 22px;
  flex: 1;
}

.kb-confirm-text {
  margin: 0 0 16px;
  font-size: 15px;
  line-height: 1.6;
}

.kb-modal__foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 22px;
  border-top: 1px solid var(--line);
}

/* 表单 */
.kb-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.kb-form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.kb-form-group--full {
  grid-column: 1 / -1;
}

.kb-form-group label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
}

.kb-req {
  color: #e4393c;
}

.kb-form-group input,
.kb-form-group select,
.kb-form-group textarea {
  padding: 10px 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  background: var(--panel);
  color: var(--ink);
}

.kb-form-group input:focus,
.kb-form-group select:focus,
.kb-form-group textarea:focus {
  outline: none;
  border-color: var(--brand);
}

.kb-form-group textarea {
  resize: none;
  min-height: 110px;
}

@media (max-width: 640px) {
  .kb-form {
    grid-template-columns: 1fr;
  }

  .kb-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
