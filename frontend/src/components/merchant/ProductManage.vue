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

interface Product {
  id: number
  name: string
  category: string
  price: number | null
  original_price?: number | null
  specs?: string | null
  spec?: string | null
  selling_points?: string | null
  image_url?: string | null
  image_urls?: string[] | null
  videos?: string[] | null
  platform?: string | null
  source?: string | null
  brand?: string | null
  rating?: number | null
  review_count?: number | null
  created_at?: string
}

interface MediaFile {
  file: File
  url: string
  uploading: boolean
  error?: string
}

/** 表单数据结构 */
interface ProductForm {
  name: string
  category: string
  price: number | string
  original_price: number | string
  spec: string
  selling_points: string
  image_url: string
  image_urls: string[]
  videos: string[]
}

const emptyForm = (): ProductForm => ({
  name: '',
  category: '',
  price: '',
  original_price: '',
  spec: '',
  selling_points: '',
  image_url: '',
  image_urls: [],
  videos: [],
})

// 列表状态
const loading = ref(false)
const error = ref<string | null>(null)
const products = ref<Product[]>([])
const categories = ref<string[]>([])
const total = ref(0)
const totalPages = ref(1)
const currentPage = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const selectedCategory = ref('')

// 弹窗状态
const showModal = ref(false)
const editingId = ref<number | null>(null)
const form = ref<ProductForm>(emptyForm())
const saving = ref(false)
const formError = ref<string | null>(null)

// 删除确认弹窗
const deleteTarget = ref<Product | null>(null)
const deleting = ref(false)

// 媒体上传
const pendingImages = ref<MediaFile[]>([])
const pendingVideos = ref<MediaFile[]>([])
const imageUploading = ref(false)
const videoUploading = ref(false)

const modalTitle = computed(() => (editingId.value === null ? '新增商品' : '编辑商品'))

const pageNumbers = computed(() => {
  const pages: number[] = []
  const maxVisible = 7
  let start = Math.max(1, currentPage.value - Math.floor(maxVisible / 2))
  let end = Math.min(totalPages.value, start + maxVisible - 1)
  if (end - start < maxVisible - 1) {
    start = Math.max(1, end - maxVisible + 1)
  }
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

async function loadProducts() {
  loading.value = true
  error.value = null
  try {
    const params = new URLSearchParams()
    params.set('page', currentPage.value.toString())
    params.set('page_size', pageSize.value.toString())
    if (keyword.value) params.set('keyword', keyword.value)
    if (selectedCategory.value) params.set('category', selectedCategory.value)

    const res = await fetch(
      `${API_BASE}/api/merchant/products?${params.toString()}`,
      { headers: authHeaders() },
    )
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${res.status}`)
    }
    const data = await res.json()
    products.value = data.products || data.items || data.list || []
    total.value = data.total || 0
    totalPages.value = data.total_pages || Math.max(1, Math.ceil(total.value / pageSize.value)) || 1
    // 使用后端返回的分类列表（与用户端同步）
    if (data.categories && data.categories.length > 0) {
      categories.value = data.categories
    } else {
      const localCats = products.value.map((p) => p.category).filter(Boolean)
      categories.value = Array.from(new Set(localCats))
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载商品失败'
  } finally {
    loading.value = false
  }
}

function searchProducts() {
  currentPage.value = 1
  loadProducts()
}

function selectCategory(cat: string) {
  selectedCategory.value = cat
  currentPage.value = 1
  loadProducts()
}

function goToPage(page: number) {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    loadProducts()
  }
}

function changePageSize(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadProducts()
}

function openCreate() {
  editingId.value = null
  form.value = emptyForm()
  pendingImages.value = []
  pendingVideos.value = []
  formError.value = null
  showModal.value = true
}

function openEdit(product: Product) {
  editingId.value = product.id
  const imgs = product.image_urls || []
  const firstUrl = product.image_url || (imgs.length ? imgs[0] : '')
  form.value = {
    name: product.name || '',
    category: product.category || '',
    price: product.price ?? '',
    original_price: product.original_price ?? '',
    spec: product.spec || '',
    selling_points: product.selling_points || '',
    image_url: firstUrl,
    image_urls: imgs,
    videos: product.videos || [],
  }
  pendingImages.value = []
  pendingVideos.value = []
  formError.value = null
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

function buildPayload() {
  const f = form.value
  const image_urls = [...f.image_urls]
  const videos = [...f.videos]
  return {
    name: f.name.trim(),
    category: f.category.trim(),
    price: f.price === '' ? null : Number(f.price),
    original_price: f.original_price === '' ? null : Number(f.original_price),
    spec: f.spec.trim(),
    selling_points: f.selling_points.trim(),
    image_url: f.image_url.trim(),
    image_urls,
    videos,
  }
}

async function handleSubmit() {
  if (!form.value.name.trim()) {
    formError.value = '请填写商品名称'
    return
  }
  if (imageUploading.value || videoUploading.value) {
    formError.value = '请等待媒体文件上传完成'
    return
  }
  saving.value = true
  formError.value = null
  try {
    const payload = buildPayload()
    if (editingId.value === null) {
      const res = await fetch(`${API_BASE}/api/merchant/products`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.message || `HTTP ${res.status}`)
      }
    } else {
      const res = await fetch(
        `${API_BASE}/api/merchant/products/${editingId.value}`,
        {
          method: 'PUT',
          headers: authHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify(payload),
        },
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.message || `HTTP ${res.status}`)
      }
    }
    showModal.value = false
    await loadProducts()
  } catch (e) {
    formError.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

function askDelete(product: Product) {
  deleteTarget.value = product
}

function cancelDelete() {
  deleteTarget.value = null
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    const res = await fetch(
      `${API_BASE}/api/merchant/products/${deleteTarget.value.id}`,
      { method: 'DELETE', headers: authHeaders() },
    )
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${res.status}`)
    }
    deleteTarget.value = null
    // 删除后若当前页空了则回退一页
    if (products.value.length === 1 && currentPage.value > 1) {
      currentPage.value -= 1
    }
    await loadProducts()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  } finally {
    deleting.value = false
  }
}

function formatPrice(val: number | null | undefined): string {
  if (val === null || val === undefined) return '-'
  return `¥${val.toFixed(2)}`
}

function sourceText(source?: string | null): string {
  if (!source) return '手动录入'
  return source
}

function mainImageUrl(product: Product): string {
  return product.image_url || (product.image_urls && product.image_urls[0]) || ''
}

async function uploadMedia(file: File): Promise<string> {
  const data = new FormData()
  data.append('file', file)
  const res = await fetch(`${API_BASE}/api/merchant/products/upload`, {
    method: 'POST',
    headers: authHeaders(),
    body: data,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.message || `上传失败 ${res.status}`)
  }
  const json = await res.json()
  return json.url
}

async function handleImageSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (!files.length) return
  input.value = ''

  const newItems: MediaFile[] = files.map((file) => ({
    file,
    url: URL.createObjectURL(file),
    uploading: true,
  }))
  pendingImages.value.push(...newItems)
  imageUploading.value = true

  for (const item of newItems) {
    try {
      const url = await uploadMedia(item.file)
      item.url = url
      item.uploading = false
      form.value.image_urls.push(url)
      if (!form.value.image_url) form.value.image_url = url
    } catch (e) {
      item.error = e instanceof Error ? e.message : '上传失败'
      item.uploading = false
    }
  }
  imageUploading.value = pendingImages.value.some((i) => i.uploading)
}

async function handleVideoSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (!files.length) return
  input.value = ''

  const newItems: MediaFile[] = files.map((file) => ({
    file,
    url: URL.createObjectURL(file),
    uploading: true,
  }))
  pendingVideos.value.push(...newItems)
  videoUploading.value = true

  for (const item of newItems) {
    try {
      const url = await uploadMedia(item.file)
      item.url = url
      item.uploading = false
      form.value.videos.push(url)
    } catch (e) {
      item.error = e instanceof Error ? e.message : '上传失败'
      item.uploading = false
    }
  }
  videoUploading.value = pendingVideos.value.some((i) => i.uploading)
}

function removeImage(url: string) {
  form.value.image_urls = form.value.image_urls.filter((u) => u !== url)
  pendingImages.value = pendingImages.value.filter((i) => i.url !== url)
  if (form.value.image_url === url) {
    form.value.image_url = form.value.image_urls[0] || ''
  }
}

function removeVideo(url: string) {
  form.value.videos = form.value.videos.filter((u) => u !== url)
  pendingVideos.value = pendingVideos.value.filter((i) => i.url !== url)
}

onMounted(() => {
  loadProducts()
})
</script>

<template>
  <div class="pm-page">
    <!-- 顶部操作区 -->
    <div class="pm-toolbar">
      <div class="pm-search">
        <input
          v-model="keyword"
          type="text"
          class="pm-input"
          placeholder="搜索商品名称..."
          @keyup.enter="searchProducts"
        />
        <button class="pm-btn pm-btn--primary" @click="searchProducts">搜索</button>
      </div>
      <div class="pm-actions">
        <button class="pm-btn pm-btn--primary" @click="openCreate">+ 新增商品</button>
      </div>
    </div>

    <!-- 类目筛选 + 每页条数（同一行，分类在左，条数在右） -->
    <div class="pm-tags-row">
      <div class="pm-tags">
        <button
          :class="['pm-tag', { active: !selectedCategory }]"
          @click="selectCategory('')"
        >
          全部
        </button>
        <button
          v-for="cat in categories"
          :key="cat"
          :class="['pm-tag', { active: selectedCategory === cat }]"
          @click="selectCategory(cat)"
        >
          {{ cat }}
        </button>
      </div>
      <div class="pm-page-size">
        <label>每页显示：</label>
        <select :value="pageSize" @change="changePageSize(Number(($event.target as HTMLSelectElement).value))">
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
        </select>
      </div>
    </div>

    <div v-if="error" class="pm-error">{{ error }}</div>

    <!-- 加载中 -->
    <div v-if="loading" class="pm-loading">
      <div class="pm-spinner"></div>
      <p>加载中...</p>
    </div>

    <!-- 商品表格 -->
    <div v-else class="pm-table-wrap">
      <table class="pm-table">
        <thead>
          <tr>
            <th>名称</th>
            <th>类目</th>
            <th>价格</th>
            <th>来源</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="product in products" :key="product.id">
            <td class="pm-cell-name">
              <div class="pm-name-box">
                <img
                  v-if="mainImageUrl(product)"
                  :src="mainImageUrl(product)"
                  :alt="product.name"
                  class="pm-thumb"
                  @error="(e: any) => e.target.style.visibility = 'hidden'"
                />
                <div class="pm-name-text">
                  <span class="pm-name" :title="product.name">{{ product.name }}</span>
                  <span v-if="product.spec" class="pm-spec">{{ product.spec }}</span>
                </div>
              </div>
            </td>
            <td>
              <span class="pm-cat-badge">{{ product.category || '-' }}</span>
            </td>
            <td>
              <div class="pm-price-box">
                <span class="pm-price">{{ formatPrice(product.price) }}</span>
                <span
                  v-if="product.original_price && product.original_price !== product.price"
                  class="pm-origin-price"
                >¥{{ product.original_price.toFixed(2) }}</span>
              </div>
            </td>
            <td>{{ sourceText(product.source) }}</td>
            <td>
              <div class="pm-ops">
                <button class="pm-op pm-op--edit" @click="openEdit(product)">编辑</button>
                <button class="pm-op pm-op--del" @click="askDelete(product)">删除</button>
              </div>
            </td>
          </tr>
          <tr v-if="products.length === 0">
            <td colspan="5" class="pm-empty">暂无商品数据，点击「新增商品」添加</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div v-if="!loading && totalPages > 1" class="pm-pagination">
      <button
        class="pm-page-btn"
        :disabled="currentPage === 1"
        @click="goToPage(currentPage - 1)"
      >
        上一页
      </button>
      <button
        v-for="page in pageNumbers"
        :key="page"
        :class="['pm-page-btn', { active: page === currentPage }]"
        @click="goToPage(page)"
      >
        {{ page }}
      </button>
      <button
        class="pm-page-btn"
        :disabled="currentPage === totalPages"
        @click="goToPage(currentPage + 1)"
      >
        下一页
      </button>
      <span class="pm-page-info">第 {{ currentPage }} / {{ totalPages }} 页，共 {{ total }} 条</span>
    </div>

    <!-- 新增/编辑弹窗 -->
    <div v-if="showModal" class="pm-modal-mask" @click.self="closeModal">
      <div class="pm-modal">
        <div class="pm-modal__head">
          <h3>{{ modalTitle }}</h3>
          <button class="pm-modal__close" @click="closeModal">×</button>
        </div>
        <div class="pm-modal__body">
          <div v-if="formError" class="pm-error">{{ formError }}</div>
          <div class="pm-form-grid">
            <div class="pm-form-group">
              <label>商品名称 <span class="pm-req">*</span></label>
              <input v-model="form.name" type="text" placeholder="请输入商品名称" />
            </div>
            <div class="pm-form-group">
              <label>类目</label>
              <input v-model="form.category" type="text" placeholder="例如：办公椅" />
            </div>
            <div class="pm-form-group">
              <label>价格（元）</label>
              <input v-model="form.price" type="number" step="0.01" placeholder="0.00" />
            </div>
            <div class="pm-form-group">
              <label>原价（元）</label>
              <input v-model="form.original_price" type="number" step="0.01" placeholder="0.00" />
            </div>
            <div class="pm-form-group pm-form-group--full">
              <label>规格</label>
              <input v-model="form.spec" type="text" placeholder="例如：标准款 / 黑色" />
            </div>
            <div class="pm-form-group pm-form-group--full">
              <label>卖点（每行一个）</label>
              <textarea v-model="form.selling_points" rows="3" placeholder="护腰支撑&#10;透气坐垫"></textarea>
            </div>
            <!-- 图片上传 -->
            <div class="pm-form-group pm-form-group--full">
              <label>商品图片</label>
              <div class="pm-media-upload">
                <input
                  ref="imageInput"
                  type="file"
                  accept="image/*"
                  multiple
                  class="hidden"
                  @change="handleImageSelect"
                />
                <button
                  type="button"
                  class="pm-upload-btn"
                  :disabled="imageUploading"
                  @click="($refs.imageInput as HTMLInputElement).click()"
                >
                  {{ imageUploading ? '上传中...' : '+ 添加图片' }}
                </button>
              </div>
              <div class="pm-media-grid">
                <div
                  v-for="(url, idx) in form.image_urls"
                  :key="`img-${idx}`"
                  class="pm-media-item"
                >
                  <img :src="url" alt="商品图片" />
                  <button type="button" class="pm-media-del" @click="removeImage(url)">×</button>
                </div>
                <div
                  v-for="(item, idx) in pendingImages"
                  :key="`pimg-${idx}`"
                  class="pm-media-item pm-media-item--pending"
                >
                  <img :src="item.url" alt="上传中" />
                  <div v-if="item.uploading" class="pm-media-mask">上传中</div>
                  <div v-else-if="item.error" class="pm-media-mask pm-media-mask--error" :title="item.error">失败</div>
                  <button type="button" class="pm-media-del" @click="removeImage(item.url)">×</button>
                </div>
              </div>
            </div>

            <!-- 视频上传 -->
            <div class="pm-form-group pm-form-group--full">
              <label>商品视频</label>
              <div class="pm-media-upload">
                <input
                  ref="videoInput"
                  type="file"
                  accept="video/*"
                  multiple
                  class="hidden"
                  @change="handleVideoSelect"
                />
                <button
                  type="button"
                  class="pm-upload-btn pm-upload-btn--video"
                  :disabled="videoUploading"
                  @click="($refs.videoInput as HTMLInputElement).click()"
                >
                  {{ videoUploading ? '上传中...' : '+ 添加视频' }}
                </button>
              </div>
              <div class="pm-media-grid">
                <div
                  v-for="(url, idx) in form.videos"
                  :key="`vid-${idx}`"
                  class="pm-media-item pm-media-item--video"
                >
                  <video :src="url" controls preload="metadata"></video>
                  <button type="button" class="pm-media-del" @click="removeVideo(url)">×</button>
                </div>
                <div
                  v-for="(item, idx) in pendingVideos"
                  :key="`pvid-${idx}`"
                  class="pm-media-item pm-media-item--video pm-media-item--pending"
                >
                  <video :src="item.url" preload="metadata"></video>
                  <div v-if="item.uploading" class="pm-media-mask">上传中</div>
                  <div v-else-if="item.error" class="pm-media-mask pm-media-mask--error" :title="item.error">失败</div>
                  <button type="button" class="pm-media-del" @click="removeVideo(item.url)">×</button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="pm-modal__foot">
          <button class="pm-btn pm-btn--ghost" @click="closeModal">取消</button>
          <button class="pm-btn pm-btn--primary" :disabled="saving" @click="handleSubmit">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <div v-if="deleteTarget" class="pm-modal-mask" @click.self="cancelDelete">
      <div class="pm-modal pm-modal--sm">
        <div class="pm-modal__head">
          <h3>确认删除</h3>
          <button class="pm-modal__close" @click="cancelDelete">×</button>
        </div>
        <div class="pm-modal__body">
          <p class="pm-confirm-text">
            确定要删除商品「<strong>{{ deleteTarget.name }}</strong>」吗？此操作不可恢复。
          </p>
        </div>
        <div class="pm-modal__foot">
          <button class="pm-btn pm-btn--ghost" @click="cancelDelete">取消</button>
          <button class="pm-btn pm-btn--danger" :disabled="deleting" @click="confirmDelete">
            {{ deleting ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pm-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 工具栏 */
.pm-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.pm-search {
  display: flex;
  gap: 10px;
  flex: 1 1 360px;
}

.pm-input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  background: var(--panel);
}

.pm-input:focus {
  outline: none;
  border-color: var(--brand);
}

.pm-actions {
  display: flex;
  gap: 10px;
}

/* 按钮 */
.pm-btn {
  padding: 10px 18px;
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

.pm-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.pm-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.pm-btn--primary {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}

.pm-btn--primary:hover:not(:disabled) {
  background: var(--brand-dark);
  border-color: var(--brand-dark);
}

.pm-btn--ghost {
  background: transparent;
}

.pm-btn--danger {
  background: #e4393c;
  color: #fff;
  border-color: #e4393c;
}

.pm-btn--danger:hover:not(:disabled) {
  background: #c5282b;
  border-color: #c5282b;
}

/* 类目标签 */
.pm-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pm-tag {
  padding: 6px 14px;
  border: 1px solid var(--line);
  border-radius: 20px;
  background: transparent;
  color: var(--muted);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.pm-tag:hover {
  border-color: var(--brand);
  color: var(--brand);
}

.pm-tag.active {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}

/* 分类标签 + 每页条数 同一行 */
.pm-tags-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.pm-tags-row .pm-tags {
  margin-bottom: 0;
  flex: 1;
  min-width: 0;
}

.pm-page-size {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--muted);
  flex-shrink: 0;
}

.pm-page-size select {
  padding: 6px 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  font-size: 13px;
  cursor: pointer;
}

/* 加载 */
.pm-loading {
  text-align: center;
  padding: 48px 0;
  color: var(--muted);
}

.pm-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--line);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: pm-spin 1s linear infinite;
  margin: 0 auto 12px;
}

@keyframes pm-spin {
  to {
    transform: rotate(360deg);
  }
}

.pm-error {
  background: #fee;
  color: #c33;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
}

/* 表格 */
.pm-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--panel);
}

.pm-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
  min-width: 720px;
}

.pm-table thead {
  background: rgba(217, 95, 45, 0.06);
}

.pm-table th {
  padding: 12px 16px;
  text-align: left;
  font-weight: 700;
  color: var(--brand-dark);
  border-bottom: 1px solid var(--line);
  white-space: nowrap;
}

.pm-table td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--line);
  vertical-align: middle;
}

.pm-table tbody tr:hover {
  background: rgba(217, 95, 45, 0.03);
}

.pm-cell-name {
  min-width: 220px;
}

.pm-name-box {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pm-thumb {
  width: 44px;
  height: 44px;
  flex: 0 0 auto;
  border-radius: 8px;
  object-fit: cover;
  border: 1px solid var(--line);
}

.pm-name-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.pm-name {
  font-weight: 600;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 240px;
}

.pm-spec {
  font-size: 12px;
  color: var(--muted);
}

.pm-cat-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  background: rgba(217, 95, 45, 0.1);
  color: var(--brand-dark);
}

.pm-price-box {
  display: flex;
  flex-direction: column;
}

.pm-price {
  color: #e4393c;
  font-weight: 700;
}

.pm-origin-price {
  font-size: 12px;
  color: var(--muted);
  text-decoration: line-through;
}

.pm-ops {
  display: flex;
  gap: 8px;
}

.pm-op {
  padding: 4px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: transparent;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.pm-op--edit {
  color: var(--brand);
  border-color: rgba(217, 95, 45, 0.4);
}

.pm-op--edit:hover {
  background: var(--brand);
  color: #fff;
}

.pm-op--del {
  color: #e4393c;
  border-color: rgba(228, 57, 60, 0.4);
}

.pm-op--del:hover {
  background: #e4393c;
  color: #fff;
}

.pm-empty {
  text-align: center;
  color: var(--muted);
  padding: 40px 0;
}

/* 分页 */
.pm-pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.pm-page-btn {
  padding: 7px 13px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  color: var(--ink);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.pm-page-btn:hover:not(:disabled) {
  border-color: var(--brand);
  color: var(--brand);
}

.pm-page-btn.active {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}

.pm-page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pm-page-info {
  margin-left: 12px;
  font-size: 13px;
  color: var(--muted);
}

/* 弹窗 */
.pm-modal-mask {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(33, 26, 20, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.pm-modal {
  width: min(560px, 100%);
  max-height: 90vh;
  overflow-y: auto;
  background: var(--panel);
  border-radius: 18px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
}

.pm-modal--sm {
  width: min(420px, 100%);
}

.pm-modal__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid var(--line);
}

.pm-modal__head h3 {
  margin: 0;
  font-size: 18px;
  color: var(--brand-dark);
}

.pm-modal__close {
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

.pm-modal__close:hover {
  background: rgba(217, 95, 45, 0.1);
  color: var(--brand);
}

.pm-modal__body {
  padding: 22px;
  flex: 1;
}

.pm-confirm-text {
  margin: 0;
  font-size: 15px;
  line-height: 1.6;
}

.pm-modal__foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 22px;
  border-top: 1px solid var(--line);
}

/* 表单 */
.pm-form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.pm-form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pm-form-group--full {
  grid-column: 1 / -1;
}

.pm-form-group label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
}

.pm-req {
  color: #e4393c;
}

.pm-form-group input,
.pm-form-group textarea {
  padding: 10px 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  background: var(--panel);
  color: var(--ink);
}

.pm-form-group input:focus,
.pm-form-group textarea:focus {
  outline: none;
  border-color: var(--brand);
}

.pm-form-group textarea {
  resize: vertical;
  min-height: 72px;
}

/* 媒体上传 */
.pm-media-upload {
  margin-bottom: 10px;
}

.pm-upload-btn {
  padding: 9px 16px;
  border: 1px dashed var(--brand, #d95f2d);
  border-radius: 10px;
  background: rgba(217, 95, 45, 0.06);
  color: var(--brand, #d95f2d);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.pm-upload-btn:hover:not(:disabled) {
  background: rgba(217, 95, 45, 0.12);
}

.pm-upload-btn--video {
  border-color: #1677ff;
  background: rgba(22, 119, 255, 0.06);
  color: #1677ff;
}

.pm-upload-btn--video:hover:not(:disabled) {
  background: rgba(22, 119, 255, 0.12);
}

.pm-upload-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.pm-media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
  gap: 10px;
}

.pm-media-item {
  position: relative;
  aspect-ratio: 1;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--line, #e8e4df);
  background: #f7f7f7;
}

.pm-media-item--video {
  aspect-ratio: 16 / 10;
}

.pm-media-item img,
.pm-media-item video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.pm-media-item--pending::after {
  content: '';
  position: absolute;
  inset: 0;
  border: 2px dashed var(--brand, #d95f2d);
  border-radius: 10px;
  pointer-events: none;
}

.pm-media-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}

.pm-media-mask--error {
  background: rgba(196, 30, 30, 0.65);
}

.pm-media-del {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 22px;
  height: 22px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  display: grid;
  place-items: center;
  transition: background 0.2s;
}

.pm-media-del:hover {
  background: rgba(228, 57, 60, 0.85);
}

.hidden {
  display: none;
}

@media (max-width: 640px) {
  .pm-form-grid {
    grid-template-columns: 1fr;
  }

  .pm-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
