<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  CubeIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  PhotoIcon,
  VideoCameraIcon,
} from '@heroicons/vue/24/outline'

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
  is_published?: boolean | null
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
  is_published: boolean
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
  is_published: true,
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

const publishedCount = computed(
  () => products.value.filter((p) => p.is_published !== false).length,
)

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
    is_published: product.is_published !== false,
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
    is_published: f.is_published,
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
  <div class="space-y-5 animate-fade-in-up">
    <!-- 顶部统计与操作 -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <div class="w-11 h-11 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
          <CubeIcon class="w-6 h-6" />
        </div>
        <div>
          <h3 class="text-lg font-bold text-gray-800">商品管理</h3>
          <p class="text-xs text-gray-500">
            共 <span class="font-semibold text-primary">{{ total }}</span> 件商品，已上架
            <span class="font-semibold text-emerald-600">{{ publishedCount }}</span> 件
          </p>
        </div>
      </div>
      <button
        @click="openCreate"
        class="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-white text-sm font-semibold hover:bg-primary-dark hover:-translate-y-0.5 transition-all shadow-card"
      >
        <PlusIcon class="w-4 h-4" />
        新增商品
      </button>
    </div>

    <!-- 搜索与筛选 -->
    <div class="bg-white rounded-2xl border border-primary-light/50 shadow-card p-4">
      <div class="flex flex-col md:flex-row gap-4">
        <div class="relative flex-1 min-w-0">
          <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            v-model="keyword"
            type="text"
            class="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none"
            placeholder="搜索商品名称..."
            @keyup.enter="searchProducts"
          />
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <span class="text-xs text-gray-400 whitespace-nowrap">每页</span>
          <select
            :value="pageSize"
            @change="changePageSize(Number(($event.target as HTMLSelectElement).value))"
            class="px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:border-primary outline-none bg-white"
          >
            <option :value="10">10</option>
            <option :value="20">20</option>
            <option :value="50">50</option>
          </select>
        </div>
      </div>

      <div class="flex flex-wrap gap-2 mt-4">
        <button
          :class="[
            'px-4 py-1.5 rounded-full text-xs font-medium border transition-all',
            !selectedCategory
              ? 'bg-primary text-white border-primary'
              : 'bg-white text-gray-600 border-gray-200 hover:border-primary hover:text-primary',
          ]"
          @click="selectCategory('')"
        >
          全部类目
        </button>
        <button
          v-for="cat in categories"
          :key="cat"
          :class="[
            'px-4 py-1.5 rounded-full text-xs font-medium border transition-all',
            selectedCategory === cat
              ? 'bg-primary text-white border-primary'
              : 'bg-white text-gray-600 border-gray-200 hover:border-primary hover:text-primary',
          ]"
          @click="selectCategory(cat)"
        >
          {{ cat }}
        </button>
      </div>
    </div>

    <!-- 错误提示 -->
    <div
      v-if="error"
      class="rounded-xl px-4 py-3 text-sm font-medium bg-rose-50 text-rose-700 border border-rose-100"
    >
      {{ error }}
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-20 text-gray-400">
      <div class="w-10 h-10 border-4 border-primary/20 border-t-primary rounded-full animate-spin mb-3"></div>
      <p>加载商品中...</p>
    </div>

    <!-- 商品卡片网格 -->
    <div v-else-if="products.length" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
      <div
        v-for="product in products"
        :key="product.id"
        class="group bg-white rounded-2xl border border-primary-light/40 shadow-card hover:shadow-card-hover hover:-translate-y-1 transition-all duration-300 overflow-hidden"
      >
        <div class="relative aspect-[4/3] bg-gray-100 overflow-hidden">
          <img
            v-if="mainImageUrl(product)"
            :src="mainImageUrl(product)"
            :alt="product.name"
            class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            @error="(e: any) => (e.target.style.display = 'none')"
          />
          <div
            v-else
            class="w-full h-full flex flex-col items-center justify-center text-gray-300"
          >
            <PhotoIcon class="w-10 h-10 mb-1" />
            <span class="text-xs">暂无图片</span>
          </div>
          <div
            :class="[
              'absolute top-3 left-3 px-2.5 py-1 rounded-lg text-xs font-semibold backdrop-blur-sm',
              product.is_published !== false
                ? 'bg-emerald-500/90 text-white'
                : 'bg-gray-500/80 text-white',
            ]"
          >
            {{ product.is_published !== false ? '已上架' : '已下架' }}
          </div>
          <div
            v-if="product.videos && product.videos.length"
            class="absolute bottom-3 right-3 w-8 h-8 rounded-full bg-black/50 flex items-center justify-center text-white"
          >
            <VideoCameraIcon class="w-4 h-4" />
          </div>
        </div>

        <div class="p-4">
          <div class="flex items-start justify-between gap-3 mb-2">
            <h4 class="text-sm font-bold text-gray-800 line-clamp-2 flex-1" :title="product.name">
              {{ product.name }}
            </h4>
            <span
              v-if="product.category"
              class="shrink-0 px-2 py-0.5 rounded-md bg-primary/10 text-primary text-[11px] font-medium"
            >
              {{ product.category }}
            </span>
          </div>

          <p v-if="product.spec" class="text-xs text-gray-500 mb-3 truncate">
            {{ product.spec }}
          </p>

          <div class="flex items-end gap-2 mb-4">
            <span class="text-lg font-bold text-primary">{{ formatPrice(product.price) }}</span>
            <span
              v-if="product.original_price && product.original_price !== product.price"
              class="text-xs text-gray-400 line-through mb-1"
            >
              ¥{{ product.original_price.toFixed(2) }}
            </span>
          </div>

          <div class="flex items-center justify-between pt-3 border-t border-gray-100">
            <span class="text-xs text-gray-400">来源：{{ sourceText(product.source) }}</span>
            <div class="flex items-center gap-2">
              <button
                @click="openEdit(product)"
                class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-primary bg-primary/5 hover:bg-primary hover:text-white transition-colors"
              >
                <PencilIcon class="w-3.5 h-3.5" />
                编辑
              </button>
              <button
                @click="askDelete(product)"
                class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-rose-600 bg-rose-50 hover:bg-rose-500 hover:text-white transition-colors"
              >
                <TrashIcon class="w-3.5 h-3.5" />
                删除
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div
      v-else
      class="flex flex-col items-center justify-center py-20 text-gray-400 border border-dashed border-gray-200 rounded-2xl bg-white/50"
    >
      <CubeIcon class="w-12 h-12 mb-3 text-primary/30" />
      <p class="text-sm">暂无商品数据</p>
      <button
        @click="openCreate"
        class="mt-3 text-sm text-primary font-medium hover:underline"
      >
        点击新增商品
      </button>
    </div>

    <!-- 分页 -->
    <div v-if="!loading && totalPages > 1" class="flex items-center justify-center gap-2 pt-2">
      <button
        class="px-3 py-2 rounded-lg text-sm font-medium border border-gray-200 text-gray-600 hover:border-primary hover:text-primary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        :disabled="currentPage === 1"
        @click="goToPage(currentPage - 1)"
      >
        上一页
      </button>
      <button
        v-for="page in pageNumbers"
        :key="page"
        :class="[
          'w-9 h-9 rounded-lg text-sm font-medium transition-colors',
          page === currentPage
            ? 'bg-primary text-white'
            : 'border border-gray-200 text-gray-600 hover:border-primary hover:text-primary',
        ]"
        @click="goToPage(page)"
      >
        {{ page }}
      </button>
      <button
        class="px-3 py-2 rounded-lg text-sm font-medium border border-gray-200 text-gray-600 hover:border-primary hover:text-primary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        :disabled="currentPage === totalPages"
        @click="goToPage(currentPage + 1)"
      >
        下一页
      </button>
      <span class="text-xs text-gray-400 ml-2">
        第 {{ currentPage }} / {{ totalPages }} 页，共 {{ total }} 条
      </span>
    </div>

    <!-- 新增/编辑弹窗 -->
    <div
      v-if="showModal"
      class="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in-up"
      @click.self="closeModal"
    >
      <div class="bg-white rounded-2xl shadow-card w-full max-w-3xl max-h-[90vh] overflow-y-auto animate-modal-in">
        <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between sticky top-0 bg-white z-10">
          <h3 class="text-lg font-bold text-gray-800">{{ modalTitle }}</h3>
          <button
            @click="closeModal"
            class="w-8 h-8 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 flex items-center justify-center transition-colors text-xl leading-none"
          >
            ×
          </button>
        </div>

        <div class="p-6 space-y-5">
          <div
            v-if="formError"
            class="rounded-xl px-4 py-3 text-sm font-medium bg-rose-50 text-rose-700 border border-rose-100"
          >
            {{ formError }}
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-gray-600">
                商品名称 <span class="text-rose-500">*</span>
              </label>
              <input
                v-model="form.name"
                type="text"
                class="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none"
                placeholder="请输入商品名称"
              />
            </div>
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-gray-600">类目</label>
              <input
                v-model="form.category"
                type="text"
                class="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none"
                placeholder="例如：办公椅"
              />
            </div>
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-gray-600">价格（元）</label>
              <input
                v-model="form.price"
                type="number"
                step="0.01"
                class="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none"
                placeholder="0.00"
              />
            </div>
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-gray-600">原价（元）</label>
              <input
                v-model="form.original_price"
                type="number"
                step="0.01"
                class="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none"
                placeholder="0.00"
              />
            </div>
            <div class="space-y-1.5 md:col-span-2">
              <label class="text-xs font-semibold text-gray-600">规格</label>
              <input
                v-model="form.spec"
                type="text"
                class="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none"
                placeholder="例如：标准款 / 黑色"
              />
            </div>
            <div class="space-y-1.5 md:col-span-2">
              <label class="text-xs font-semibold text-gray-600">卖点（每行一个）</label>
              <textarea
                v-model="form.selling_points"
                rows="3"
                class="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none resize-none"
                placeholder="护腰支撑&#10;透气坐垫"
              ></textarea>
            </div>

            <!-- 图片上传 -->
            <div class="space-y-2 md:col-span-2">
              <label class="text-xs font-semibold text-gray-600">商品图片</label>
              <div>
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
                  :disabled="imageUploading"
                  @click="($refs.imageInput as HTMLInputElement).click()"
                  class="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-dashed border-primary text-primary text-sm font-medium hover:bg-primary/5 transition-colors disabled:opacity-60"
                >
                  <PhotoIcon class="w-4 h-4" />
                  {{ imageUploading ? '上传中...' : '添加图片' }}
                </button>
              </div>
              <div class="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
                <div
                  v-for="(url, idx) in form.image_urls"
                  :key="`img-${idx}`"
                  class="relative aspect-square rounded-xl overflow-hidden border border-gray-200 group"
                >
                  <img :src="url" class="w-full h-full object-cover" alt="商品图片" />
                  <button
                    type="button"
                    @click="removeImage(url)"
                    class="absolute top-1 right-1 w-6 h-6 rounded-full bg-black/50 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity text-xs"
                  >
                    ×
                  </button>
                </div>
                <div
                  v-for="(item, idx) in pendingImages"
                  :key="`pimg-${idx}`"
                  class="relative aspect-square rounded-xl overflow-hidden border border-gray-200"
                >
                  <img :src="item.url" class="w-full h-full object-cover opacity-70" alt="上传中" />
                  <div
                    v-if="item.uploading"
                    class="absolute inset-0 flex items-center justify-center bg-black/30 text-white text-xs"
                  >
                    上传中
                  </div>
                  <div
                    v-else-if="item.error"
                    class="absolute inset-0 flex items-center justify-center bg-rose-500/80 text-white text-xs text-center px-1"
                    :title="item.error"
                  >
                    失败
                  </div>
                  <button
                    type="button"
                    @click="removeImage(item.url)"
                    class="absolute top-1 right-1 w-6 h-6 rounded-full bg-black/50 text-white flex items-center justify-center text-xs"
                  >
                    ×
                  </button>
                </div>
              </div>
            </div>

            <!-- 视频上传 -->
            <div class="space-y-2 md:col-span-2">
              <label class="text-xs font-semibold text-gray-600">商品视频</label>
              <div>
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
                  :disabled="videoUploading"
                  @click="($refs.videoInput as HTMLInputElement).click()"
                  class="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-dashed border-accent-blue text-accent-blue text-sm font-medium hover:bg-accent-blue/10 transition-colors disabled:opacity-60"
                >
                  <VideoCameraIcon class="w-4 h-4" />
                  {{ videoUploading ? '上传中...' : '添加视频' }}
                </button>
              </div>
              <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                <div
                  v-for="(url, idx) in form.videos"
                  :key="`vid-${idx}`"
                  class="relative rounded-xl overflow-hidden border border-gray-200 group"
                >
                  <video :src="url" controls preload="metadata" class="w-full aspect-video object-cover"></video>
                  <button
                    type="button"
                    @click="removeVideo(url)"
                    class="absolute top-1 right-1 w-6 h-6 rounded-full bg-black/50 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity text-xs"
                  >
                    ×
                  </button>
                </div>
                <div
                  v-for="(item, idx) in pendingVideos"
                  :key="`pvid-${idx}`"
                  class="relative rounded-xl overflow-hidden border border-gray-200"
                >
                  <video :src="item.url" preload="metadata" class="w-full aspect-video object-cover opacity-70"></video>
                  <div
                    v-if="item.uploading"
                    class="absolute inset-0 flex items-center justify-center bg-black/30 text-white text-xs"
                  >
                    上传中
                  </div>
                  <div
                    v-else-if="item.error"
                    class="absolute inset-0 flex items-center justify-center bg-rose-500/80 text-white text-xs text-center px-1"
                    :title="item.error"
                  >
                    失败
                  </div>
                  <button
                    type="button"
                    @click="removeVideo(item.url)"
                    class="absolute top-1 right-1 w-6 h-6 rounded-full bg-black/50 text-white flex items-center justify-center text-xs"
                  >
                    ×
                  </button>
                </div>
              </div>
            </div>

            <!-- 上架开关 -->
            <div class="md:col-span-2 flex items-center gap-3 pt-1">
              <button
                type="button"
                @click="form.is_published = !form.is_published"
                :class="[
                  'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                  form.is_published ? 'bg-primary' : 'bg-gray-300',
                ]"
              >
                <span
                  :class="[
                    'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                    form.is_published ? 'translate-x-6' : 'translate-x-1',
                  ]"
                ></span>
              </button>
              <span class="text-sm font-medium text-gray-700">
                {{ form.is_published ? '立即上架' : '暂不上架' }}
              </span>
            </div>
          </div>
        </div>

        <div class="px-6 py-4 border-t border-gray-100 flex justify-end gap-3 sticky bottom-0 bg-white z-10">
          <button
            @click="closeModal"
            class="px-5 py-2 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
          >
            取消
          </button>
          <button
            @click="handleSubmit"
            :disabled="saving || imageUploading || videoUploading"
            class="px-5 py-2 rounded-xl text-sm font-medium bg-primary text-white hover:bg-primary-dark transition-colors disabled:opacity-60"
          >
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <div
      v-if="deleteTarget"
      class="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in-up"
      @click.self="cancelDelete"
    >
      <div class="bg-white rounded-2xl shadow-card w-full max-w-sm p-6 animate-modal-in">
        <h3 class="text-lg font-bold text-gray-800 mb-2">确认删除</h3>
        <p class="text-sm text-gray-500 leading-relaxed">
          确定要删除商品 <strong class="text-gray-800">{{ deleteTarget.name }}</strong> 吗？此操作不可恢复。
        </p>
        <div class="flex justify-end gap-3 mt-6">
          <button
            @click="cancelDelete"
            class="px-4 py-2 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
          >
            取消
          </button>
          <button
            @click="confirmDelete"
            :disabled="deleting"
            class="px-5 py-2 rounded-xl text-sm font-medium bg-rose-500 text-white hover:bg-rose-600 transition-colors disabled:opacity-60"
          >
            {{ deleting ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
