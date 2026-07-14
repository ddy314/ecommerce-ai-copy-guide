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

// ---------- 类型定义 ----------
interface DailyRevenue {
  date: string
  revenue: number
}

interface DailyOrder {
  date: string
  count: number
}

interface TopProduct {
  id: number
  name: string
  category: string
  price: number
  sales_count: number
  review_count: number
  rating: number
  traffic_score: number
}

interface DashboardData {
  total_revenue: number
  total_orders: number
  avg_order_value: number
  status_revenue: Record<string, number>
  category_revenue: Record<string, number>
  daily_revenue: DailyRevenue[]
  daily_orders: DailyOrder[]
  top_products: TopProduct[]
  category_counts: Record<string, number>
  category_sales: Record<string, number>
  total_products: number
  total_qa: number
}

type SortKey = 'name' | 'category' | 'price' | 'sales_count' | 'review_count' | 'rating' | 'traffic_score'

// ---------- 状态 ----------
const loading = ref(false)
const error = ref<string | null>(null)
const data = ref<DashboardData | null>(null)

// 表格排序
const sortKey = ref<SortKey>('traffic_score')
const sortDir = ref<'asc' | 'desc'>('desc')

// ---------- 状态营收配置 ----------
const statusConfig: { key: string; label: string; color: string; bg: string }[] = [
  { key: 'paid', label: '已付款', color: 'var(--green)', bg: 'linear-gradient(90deg, #1f8a5b, #155a3c)' },
  { key: 'shipped', label: '已发货', color: '#1677ff', bg: 'linear-gradient(90deg, #1677ff, #0e5ad6)' },
  { key: 'completed', label: '已完成', color: 'var(--brand)', bg: 'linear-gradient(90deg, var(--brand), var(--brand-dark))' },
]

// ---------- 分类颜色调色板 ----------
const categoryPalette = [
  '#d95f2d',
  '#1f8a5b',
  '#1677ff',
  '#bc8321',
  '#8e44ad',
  '#16a085',
  '#e67e22',
  '#c0392b',
  '#2980b9',
  '#7d6608',
]

function categoryColor(idx: number): string {
  return categoryPalette[idx % categoryPalette.length]
}

// ---------- KPI 卡片 ----------
const kpiCards = computed(() => {
  const d = data.value
  if (!d) return []
  return [
    {
      key: 'revenue',
      label: '总收入',
      icon: '¥',
      value: formatMoney(d.total_revenue),
      sub: `客单价 ¥${formatMoney(d.avg_order_value)}`,
      accent: 'green',
    },
    {
      key: 'orders',
      label: '总订单数',
      icon: '单',
      value: formatNum(d.total_orders),
      sub: `${d.total_qa} 条问答`,
      accent: 'orange',
    },
    {
      key: 'aov',
      label: '客单价',
      icon: '价',
      value: formatMoney(d.avg_order_value),
      sub: `日均 ${formatNum(dailyOrderTotal.value / Math.max(dailyOrders.value.length, 1))} 单`,
      accent: 'blue',
    },
    {
      key: 'products',
      label: '商品总数',
      icon: '品',
      value: formatNum(d.total_products),
      sub: `${categoryList.value.length} 个分类`,
      accent: 'purple',
    },
  ]
})

// ---------- 状态营收（含百分比） ----------
const statusRevenueRows = computed(() => {
  const d = data.value
  if (!d) return []
  const total = statusConfig.reduce((sum, s) => sum + (d.status_revenue[s.key] || 0), 0)
  return statusConfig.map((s) => {
    const value = d.status_revenue[s.key] || 0
    return {
      ...s,
      value,
      percent: total > 0 ? (value / total) * 100 : 0,
      total,
    }
  })
})

// ---------- 日营收柱状图 ----------
const dailyRevenue = computed<DailyRevenue[]>(() => data.value?.daily_revenue || [])
const maxRevenue = computed(() =>
  dailyRevenue.value.reduce((max, item) => Math.max(max, item.revenue), 0),
)

function revenueBarHeight(value: number): string {
  if (maxRevenue.value === 0) return '0%'
  return `${(value / maxRevenue.value) * 100}%`
}

// ---------- 日订单趋势 ----------
const dailyOrders = computed<DailyOrder[]>(() => data.value?.daily_orders || [])
const dailyOrderTotal = computed(() =>
  dailyOrders.value.reduce((sum, item) => sum + item.count, 0),
)
const maxOrderCount = computed(() =>
  dailyOrders.value.reduce((max, item) => Math.max(max, item.count), 0),
)

function orderBarHeight(value: number): string {
  if (maxOrderCount.value === 0) return '0%'
  return `${(value / maxOrderCount.value) * 100}%`
}

// ---------- 分类分布 ----------
const categoryCountsList = computed(() => {
  const d = data.value
  if (!d) return []
  return Object.entries(d.category_counts)
    .map(([key, value], idx) => ({ name: key, value: Number(value) || 0, color: categoryColor(idx) }))
    .sort((a, b) => b.value - a.value)
})

const categorySalesList = computed(() => {
  const d = data.value
  if (!d) return []
  return Object.entries(d.category_sales)
    .map(([key, value], idx) => ({ name: key, value: Number(value) || 0, color: categoryColor(idx) }))
    .sort((a, b) => b.value - a.value)
})

const categoryList = computed(() => categoryCountsList.value)

const maxCategoryCount = computed(() =>
  categoryCountsList.value.reduce((max, item) => Math.max(max, item.value), 0),
)
const maxCategorySales = computed(() =>
  categorySalesList.value.reduce((max, item) => Math.max(max, item.value), 0),
)

function countBarWidth(value: number): string {
  if (maxCategoryCount.value === 0) return '0%'
  return `${(value / maxCategoryCount.value) * 100}%`
}
function salesBarWidth(value: number): string {
  if (maxCategorySales.value === 0) return '0%'
  return `${(value / maxCategorySales.value) * 100}%`
}

// ---------- Top 商品表 ----------
const sortedProducts = computed<TopProduct[]>(() => {
  const list = [...(data.value?.top_products || [])]
  const key = sortKey.value
  const dir = sortDir.value === 'asc' ? 1 : -1
  return list.sort((a, b) => {
    const av = a[key]
    const bv = b[key]
    if (typeof av === 'string' && typeof bv === 'string') {
      return av.localeCompare(bv, 'zh') * dir
    }
    return ((av as number) - (bv as number)) * dir
  })
})

const maxTrafficScore = computed(() =>
  sortedProducts.value.reduce((max, p) => Math.max(max, p.traffic_score), 0),
)

function trafficBarWidth(score: number): string {
  if (maxTrafficScore.value === 0) return '0%'
  return `${Math.min(100, (score / maxTrafficScore.value) * 100)}%`
}

function trafficColor(score: number): string {
  if (score >= 100) return 'var(--green)'
  if (score >= 50) return 'var(--brand)'
  if (score > 0) return 'var(--yellow)'
  return 'var(--muted)'
}

function toggleSort(key: SortKey) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'desc'
  }
}

function sortIcon(key: SortKey): string {
  if (sortKey.value !== key) return ''
  return sortDir.value === 'asc' ? '▲' : '▼'
}

function medalClass(index: number): string {
  if (index === 0) return 'medal--gold'
  if (index === 1) return 'medal--silver'
  if (index === 2) return 'medal--bronze'
  return ''
}

function rankLabel(index: number): string {
  return String(index + 1)
}

// ---------- 格式化 ----------
function formatMoney(val: number | null | undefined): string {
  if (val === null || val === undefined) return '0.00'
  return val.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatNum(val: number | null | undefined): string {
  if (val === null || val === undefined) return '0'
  return val.toLocaleString('zh-CN')
}

function formatPercent(val: number): string {
  return `${val.toFixed(1)}%`
}

function formatPrice(val: number): string {
  return val.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function starRating(rating: number): string {
  return rating.toFixed(1)
}

// ---------- 加载数据 ----------
async function loadDashboard() {
  loading.value = true
  error.value = null
  try {
    const res = await fetch(`${API_BASE}/api/merchant/dashboard/revenue`, {
      headers: authHeaders(),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${res.status}`)
    }
    const json: DashboardData = await res.json()
    data.value = json
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载营收数据失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadDashboard()
})
</script>

<template>
  <div class="rd-page">
    <!-- 错误提示 -->
    <div v-if="error" class="rd-error">{{ error }}</div>

    <!-- 加载中 -->
    <div v-if="loading" class="rd-loading">
      <div class="rd-spinner"></div>
      <p>正在加载营收数据...</p>
    </div>

    <template v-else-if="data">
      <!-- 1. 顶部 KPI 卡片 -->
      <div class="rd-kpis">
        <div
          v-for="card in kpiCards"
          :key="card.key"
          :class="['rd-kpi', `rd-kpi--${card.accent}`]"
        >
          <div class="rd-kpi__left">
            <span class="rd-kpi__icon">{{ card.icon }}</span>
            <span class="rd-kpi__label">{{ card.label }}</span>
            <span class="rd-kpi__sub">{{ card.sub }}</span>
          </div>
          <div class="rd-kpi__right">
            <span class="rd-kpi__value">{{ card.value }}</span>
          </div>
        </div>
      </div>

      <!-- 图表行：营收趋势 + 订单趋势 -->
      <div class="rd-row rd-row--charts">
        <!-- 2. 营收趋势柱状图 -->
        <section class="rd-section rd-section--chart">
          <div class="rd-section__head">
            <h3 class="rd-section__title">近 7 天营收趋势</h3>
            <span class="rd-section__hint">单位：元</span>
          </div>
          <div v-if="dailyRevenue.length" class="rd-bar-chart">
            <!-- Y 轴刻度 -->
            <div class="rd-bar-chart__yaxis">
              <span>{{ formatMoney(maxRevenue) }}</span>
              <span>{{ formatMoney(maxRevenue / 2) }}</span>
              <span>0</span>
            </div>
            <div class="rd-bar-chart__plot">
              <div class="rd-bar-chart__grid">
                <span class="rd-bar-chart__line"></span>
                <span class="rd-bar-chart__line"></span>
                <span class="rd-bar-chart__line"></span>
              </div>
              <div
                v-for="(item, idx) in dailyRevenue"
                :key="idx"
                class="rd-bar-col"
              >
                <div class="rd-bar-col__bar-wrap">
                  <div class="rd-bar-col__tooltip">¥{{ formatMoney(item.revenue) }}</div>
                  <div
                    class="rd-bar-col__bar"
                    :style="{ height: revenueBarHeight(item.revenue) }"
                  ></div>
                </div>
                <span class="rd-bar-col__label">{{ item.date }}</span>
              </div>
            </div>
          </div>
          <div v-else class="rd-na">暂无营收数据</div>
        </section>

        <!-- 6. 日订单趋势 -->
        <section class="rd-section rd-section--chart">
          <div class="rd-section__head">
            <h3 class="rd-section__title">近 7 天订单量趋势</h3>
            <span class="rd-section__hint">共 {{ formatNum(dailyOrderTotal) }} 单</span>
          </div>
          <div v-if="dailyOrders.length" class="rd-bar-chart rd-bar-chart--orders">
            <div class="rd-bar-chart__yaxis">
              <span>{{ formatNum(maxOrderCount) }}</span>
              <span>{{ formatNum(Math.round(maxOrderCount / 2)) }}</span>
              <span>0</span>
            </div>
            <div class="rd-bar-chart__plot">
              <div class="rd-bar-chart__grid">
                <span class="rd-bar-chart__line"></span>
                <span class="rd-bar-chart__line"></span>
                <span class="rd-bar-chart__line"></span>
              </div>
              <div
                v-for="(item, idx) in dailyOrders"
                :key="idx"
                class="rd-bar-col"
              >
                <div class="rd-bar-col__bar-wrap">
                  <div class="rd-bar-col__tooltip">{{ item.count }} 单</div>
                  <div
                    class="rd-bar-col__bar rd-bar-col__bar--order"
                    :style="{ height: orderBarHeight(item.count) }"
                  ></div>
                </div>
                <span class="rd-bar-col__label">{{ item.date }}</span>
              </div>
            </div>
          </div>
          <div v-else class="rd-na">暂无订单数据</div>
        </section>
      </div>

      <!-- 图表行：状态营收 + 分类分布 -->
      <div class="rd-row rd-row--dist">
        <!-- 3. 状态营收分布 -->
        <section class="rd-section">
          <div class="rd-section__head">
            <h3 class="rd-section__title">各状态营收分布</h3>
          </div>
          <div v-if="statusRevenueRows.length" class="rd-status">
            <div v-for="row in statusRevenueRows" :key="row.key" class="rd-status__row">
              <div class="rd-status__head">
                <span class="rd-status__name">
                  <span class="rd-status__dot" :style="{ background: row.color }"></span>
                  {{ row.label }}
                </span>
                <span class="rd-status__amount">¥{{ formatMoney(row.value) }}</span>
              </div>
              <div class="rd-status__bar-track">
                <div
                  class="rd-status__bar"
                  :style="{ width: row.percent + '%', background: row.bg }"
                ></div>
              </div>
              <span class="rd-status__percent">{{ formatPercent(row.percent) }}</span>
            </div>
          </div>
          <div v-else class="rd-na">暂无状态营收数据</div>
        </section>

        <!-- 4. 分类分布 -->
        <section class="rd-section">
          <div class="rd-section__head">
            <h3 class="rd-section__title">分类分布概览</h3>
          </div>
          <div class="rd-cat-grid">
            <!-- 左：分类商品数量 -->
            <div class="rd-cat-col">
              <h4 class="rd-cat-col__title">分类商品数量</h4>
              <div v-if="categoryCountsList.length" class="rd-cat-list">
                <div
                  v-for="(item, idx) in categoryCountsList"
                  :key="`c-${idx}`"
                  class="rd-cat-row"
                >
                  <span class="rd-cat-row__name" :title="item.name">{{ item.name }}</span>
                  <div class="rd-cat-row__track">
                    <div
                      class="rd-cat-row__bar"
                      :style="{ width: countBarWidth(item.value), background: item.color }"
                    ></div>
                  </div>
                  <span class="rd-cat-row__value">{{ formatNum(item.value) }}</span>
                </div>
              </div>
              <div v-else class="rd-na">暂无数据</div>
            </div>

            <!-- 右：分类销量 -->
            <div class="rd-cat-col">
              <h4 class="rd-cat-col__title">分类销量</h4>
              <div v-if="categorySalesList.length" class="rd-cat-list">
                <div
                  v-for="(item, idx) in categorySalesList"
                  :key="`s-${idx}`"
                  class="rd-cat-row"
                >
                  <span class="rd-cat-row__name" :title="item.name">{{ item.name }}</span>
                  <div class="rd-cat-row__track">
                    <div
                      class="rd-cat-row__bar"
                      :style="{ width: salesBarWidth(item.value), background: item.color }"
                    ></div>
                  </div>
                  <span class="rd-cat-row__value">{{ formatMoney(item.value) }}</span>
                </div>
              </div>
              <div v-else class="rd-na">暂无数据</div>
            </div>
          </div>
        </section>
      </div>

      <!-- 5. Top 10 商品流量表 -->
      <section class="rd-section">
        <div class="rd-section__head">
          <h3 class="rd-section__title">TOP 10 商品流量榜</h3>
          <span class="rd-section__hint">点击表头可排序</span>
        </div>
        <div v-if="sortedProducts.length" class="rd-table-wrap">
          <table class="rd-table">
            <thead>
              <tr>
                <th class="rd-table__rank">排名</th>
                <th
                  class="rd-table__sortable"
                  @click="toggleSort('name')"
                >商品名称 <span class="rd-sort-ico">{{ sortIcon('name') }}</span></th>
                <th
                  class="rd-table__sortable"
                  @click="toggleSort('category')"
                >分类 <span class="rd-sort-ico">{{ sortIcon('category') }}</span></th>
                <th
                  class="rd-table__num rd-table__sortable"
                  @click="toggleSort('price')"
                >价格 <span class="rd-sort-ico">{{ sortIcon('price') }}</span></th>
                <th
                  class="rd-table__num rd-table__sortable"
                  @click="toggleSort('sales_count')"
                >销量 <span class="rd-sort-ico">{{ sortIcon('sales_count') }}</span></th>
                <th
                  class="rd-table__num rd-table__sortable"
                  @click="toggleSort('review_count')"
                >评价数 <span class="rd-sort-ico">{{ sortIcon('review_count') }}</span></th>
                <th
                  class="rd-table__num rd-table__sortable"
                  @click="toggleSort('rating')"
                >评分 <span class="rd-sort-ico">{{ sortIcon('rating') }}</span></th>
                <th
                  class="rd-table__num rd-table__sortable rd-table__traffic"
                  @click="toggleSort('traffic_score')"
                >流量指数 <span class="rd-sort-ico">{{ sortIcon('traffic_score') }}</span></th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(product, idx) in sortedProducts"
                :key="product.id"
                :class="['rd-table__row', medalClass(idx)]"
              >
                <td class="rd-table__rank">
                  <span :class="['rd-medal', medalClass(idx)]">{{ rankLabel(idx) }}</span>
                </td>
                <td class="rd-table__name" :title="product.name">{{ product.name }}</td>
                <td class="rd-table__cat">{{ product.category }}</td>
                <td class="rd-table__num">¥{{ formatPrice(product.price) }}</td>
                <td class="rd-table__num">{{ formatNum(product.sales_count) }}</td>
                <td class="rd-table__num">{{ formatNum(product.review_count) }}</td>
                <td class="rd-table__num">
                  <span class="rd-star">{{ starRating(product.rating) }}</span>
                </td>
                <td class="rd-table__num">
                  <div class="rd-traffic">
                    <div class="rd-traffic__bar-wrap">
                      <div
                        class="rd-traffic__bar"
                        :style="{ width: trafficBarWidth(product.traffic_score), background: trafficColor(product.traffic_score) }"
                      ></div>
                    </div>
                    <span
                      class="rd-traffic__pill"
                      :style="{ color: trafficColor(product.traffic_score), borderColor: trafficColor(product.traffic_score) }"
                    >{{ product.traffic_score }}</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="rd-na">暂无商品流量数据</div>
      </section>
    </template>

    <!-- 空状态 -->
    <div v-else class="rd-empty">
      <div class="rd-empty__icon">板</div>
      <h3>暂无数据</h3>
      <p>还没有营收数据可供展示</p>
      <button class="rd-retry" @click="loadDashboard">重新加载</button>
    </div>
  </div>
</template>

<style scoped>
.rd-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* ===== 1. KPI 卡片 ===== */
.rd-kpis {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.rd-kpi {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--panel);
  box-shadow: var(--shadow);
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
}

.rd-kpi:hover {
  transform: translateY(-3px);
}

.rd-kpi__left {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
  padding: 18px 16px;
  flex: 1;
  min-width: 0;
}

.rd-kpi__icon {
  display: inline-grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 11px;
  font-size: 16px;
  font-weight: 800;
  color: #fff;
  margin-bottom: 2px;
}

.rd-kpi__label {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.rd-kpi__sub {
  font-size: 12px;
  color: var(--muted);
}

.rd-kpi__right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 18px;
  min-width: 130px;
}

.rd-kpi__value {
  font-size: 26px;
  font-weight: 800;
  line-height: 1.1;
  color: #fff;
  text-align: right;
  word-break: break-all;
}

/* 绿色 - 总收入 */
.rd-kpi--green .rd-kpi__icon {
  background: linear-gradient(135deg, #2aa86b, #155a3c);
}
.rd-kpi--green .rd-kpi__right {
  background: linear-gradient(135deg, #1f8a5b, #0f5d3d);
}

/* 橙色 - 总订单数 */
.rd-kpi--orange .rd-kpi__icon {
  background: linear-gradient(135deg, #e8742f, #b34a1c);
}
.rd-kpi--orange .rd-kpi__right {
  background: linear-gradient(135deg, var(--brand), var(--brand-dark));
}

/* 蓝色 - 客单价 */
.rd-kpi--blue .rd-kpi__icon {
  background: linear-gradient(135deg, #2f8bff, #0e5ad6);
}
.rd-kpi--blue .rd-kpi__right {
  background: linear-gradient(135deg, #1677ff, #0e5ad6);
}

/* 紫色 - 商品总数 */
.rd-kpi--purple .rd-kpi__icon {
  background: linear-gradient(135deg, #9b59b6, #6c3483);
}
.rd-kpi--purple .rd-kpi__right {
  background: linear-gradient(135deg, #8e44ad, #5b2c6f);
}

/* ===== 通用区块 ===== */
.rd-row {
  display: grid;
  gap: 16px;
}

.rd-row--charts {
  grid-template-columns: 1fr 1fr;
}

.rd-row--dist {
  grid-template-columns: 1fr 1.4fr;
}

.rd-section {
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--panel);
  box-shadow: var(--shadow);
  padding: 20px;
}

.rd-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
  flex-wrap: wrap;
  gap: 8px;
}

.rd-section__title {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: var(--brand-dark);
}

.rd-section__hint {
  font-size: 12px;
  color: var(--muted);
}

.rd-na {
  text-align: center;
  color: var(--muted);
  padding: 28px 0;
  font-size: 14px;
}

/* ===== 2. 柱状图 ===== */
.rd-bar-chart {
  display: flex;
  gap: 10px;
  height: 260px;
}

.rd-bar-chart--orders {
  height: 260px;
}

.rd-bar-chart__yaxis {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-end;
  padding: 0 6px 22px 0;
  font-size: 11px;
  color: var(--muted);
  border-right: 1px solid var(--line);
  width: 56px;
  flex-shrink: 0;
}

.rd-bar-chart__plot {
  position: relative;
  flex: 1;
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  gap: 8px;
  padding-bottom: 22px;
}

.rd-bar-chart__grid {
  position: absolute;
  inset: 0 0 22px 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  pointer-events: none;
}

.rd-bar-chart__line {
  display: block;
  height: 1px;
  background: var(--line);
  width: 100%;
}

.rd-bar-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  height: 100%;
  justify-content: flex-end;
  gap: 8px;
}

.rd-bar-col__bar-wrap {
  position: relative;
  width: 70%;
  max-width: 44px;
  height: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.rd-bar-col__bar {
  width: 100%;
  border-radius: 8px 8px 0 0;
  background: linear-gradient(180deg, var(--brand), var(--brand-dark));
  transition: height 0.5s cubic-bezier(0.22, 1, 0.36, 1);
  min-height: 2px;
}

.rd-bar-col__bar--order {
  background: linear-gradient(180deg, #2f8bff, #0e5ad6);
}

.rd-bar-col__bar-wrap:hover .rd-bar-col__bar {
  filter: brightness(1.08);
}

.rd-bar-col__tooltip {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  background: var(--ink);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 8px;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s;
  z-index: 5;
}

.rd-bar-col__tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 5px solid transparent;
  border-top-color: var(--ink);
}

.rd-bar-col__bar-wrap:hover .rd-bar-col__tooltip {
  opacity: 1;
}

.rd-bar-col__label {
  position: absolute;
  bottom: 0;
  font-size: 12px;
  color: var(--muted);
  font-weight: 500;
}

/* ===== 3. 状态营收 ===== */
.rd-status {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.rd-status__row {
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-rows: auto auto;
  gap: 6px 12px;
  align-items: center;
}

.rd-status__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  grid-column: 1 / -1;
}

.rd-status__name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.rd-status__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.rd-status__amount {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink);
}

.rd-status__bar-track {
  grid-column: 1 / 2;
  height: 14px;
  background: rgba(118, 107, 94, 0.1);
  border-radius: 7px;
  overflow: hidden;
}

.rd-status__bar {
  height: 100%;
  border-radius: 7px;
  transition: width 0.5s cubic-bezier(0.22, 1, 0.36, 1);
  min-width: 3px;
}

.rd-status__percent {
  grid-column: 2 / 3;
  font-size: 13px;
  font-weight: 700;
  color: var(--brand-dark);
  white-space: nowrap;
}

/* ===== 4. 分类分布 ===== */
.rd-cat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.rd-cat-col__title {
  margin: 0 0 14px;
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
  padding-bottom: 8px;
  border-bottom: 1px dashed var(--line);
}

.rd-cat-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rd-cat-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.rd-cat-row__name {
  width: 72px;
  flex: 0 0 auto;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rd-cat-row__track {
  flex: 1;
  height: 16px;
  background: rgba(118, 107, 94, 0.1);
  border-radius: 8px;
  overflow: hidden;
}

.rd-cat-row__bar {
  height: 100%;
  border-radius: 8px;
  transition: width 0.5s cubic-bezier(0.22, 1, 0.36, 1);
  min-width: 3px;
}

.rd-cat-row__value {
  flex: 0 0 auto;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
  white-space: nowrap;
  min-width: 60px;
  text-align: right;
}

/* ===== 5. Top 商品表 ===== */
.rd-table-wrap {
  overflow-x: auto;
  border-radius: 12px;
  border: 1px solid var(--line);
}

.rd-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  min-width: 760px;
}

.rd-table thead th {
  position: sticky;
  top: 0;
  background: rgba(217, 95, 45, 0.06);
  color: var(--brand-dark);
  font-weight: 700;
  text-align: left;
  padding: 12px 14px;
  border-bottom: 1px solid var(--line);
  white-space: nowrap;
  font-size: 13px;
}

.rd-table__sortable {
  cursor: pointer;
  user-select: none;
  transition: color 0.15s;
}

.rd-table__sortable:hover {
  color: var(--brand);
}

.rd-sort-ico {
  margin-left: 3px;
  font-size: 10px;
  color: var(--brand);
}

.rd-table__num {
  text-align: right;
}

.rd-table__rank {
  width: 64px;
  text-align: center;
}

.rd-table__traffic {
  min-width: 150px;
}

.rd-table tbody tr {
  transition: background 0.15s;
  border-bottom: 1px solid var(--line);
}

.rd-table tbody tr:last-child {
  border-bottom: none;
}

.rd-table tbody tr:hover {
  background: rgba(217, 95, 45, 0.04);
}

.rd-table__row {
  background: var(--panel);
}

/* 奖牌行高亮 */
.rd-table__row.medal--gold {
  background: linear-gradient(90deg, rgba(255, 215, 0, 0.14), rgba(255, 215, 0, 0.02));
}

.rd-table__row.medal--silver {
  background: linear-gradient(90deg, rgba(192, 192, 192, 0.16), rgba(192, 192, 192, 0.02));
}

.rd-table__row.medal--bronze {
  background: linear-gradient(90deg, rgba(205, 127, 50, 0.16), rgba(205, 127, 50, 0.02));
}

.rd-table__row.medal--gold:hover {
  background: linear-gradient(90deg, rgba(255, 215, 0, 0.22), rgba(255, 215, 0, 0.05));
}

.rd-table__row.medal--silver:hover {
  background: linear-gradient(90deg, rgba(192, 192, 192, 0.24), rgba(192, 192, 192, 0.05));
}

.rd-table__row.medal--bronze:hover {
  background: linear-gradient(90deg, rgba(205, 127, 50, 0.24), rgba(205, 127, 50, 0.05));
}

.rd-table td {
  padding: 12px 14px;
  color: var(--ink);
  vertical-align: middle;
}

.rd-table__name {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}

.rd-table__cat {
  color: var(--muted);
  white-space: nowrap;
}

.rd-table__num {
  font-variant-numeric: tabular-nums;
  font-weight: 500;
}

.rd-medal {
  display: inline-grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 13px;
  font-weight: 800;
  color: #fff;
}

.rd-medal.medal--gold {
  background: linear-gradient(135deg, #ffd700, #c9a300);
  box-shadow: 0 2px 6px rgba(255, 215, 0, 0.5);
}

.rd-medal.medal--silver {
  background: linear-gradient(135deg, #c0c0c0, #8a8a8a);
  box-shadow: 0 2px 6px rgba(192, 192, 192, 0.5);
}

.rd-medal.medal--bronze {
  background: linear-gradient(135deg, #cd7f32, #94581f);
  box-shadow: 0 2px 6px rgba(205, 127, 50, 0.5);
}

.rd-star {
  color: var(--yellow);
  font-weight: 700;
}

/* 流量指数 */
.rd-traffic {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: flex-end;
}

.rd-traffic__bar-wrap {
  flex: 1;
  height: 8px;
  background: rgba(118, 107, 94, 0.12);
  border-radius: 4px;
  overflow: hidden;
  min-width: 50px;
}

.rd-traffic__bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s cubic-bezier(0.22, 1, 0.36, 1);
  min-width: 3px;
}

.rd-traffic__pill {
  display: inline-grid;
  place-items: center;
  min-width: 42px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid;
  font-size: 12px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.5);
  white-space: nowrap;
}

/* ===== 加载 / 错误 / 空 ===== */
.rd-loading {
  text-align: center;
  padding: 70px 20px;
  color: var(--muted);
}

.rd-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--line);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: rd-spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

@keyframes rd-spin {
  to {
    transform: rotate(360deg);
  }
}

.rd-error {
  background: #fff0f0;
  color: #c33;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
}

.rd-empty {
  text-align: center;
  padding: 70px 20px;
  color: var(--muted);
}

.rd-empty__icon {
  display: inline-grid;
  width: 72px;
  height: 72px;
  place-items: center;
  border-radius: 20px;
  margin-bottom: 20px;
  font-size: 30px;
  font-weight: 800;
  color: #fffaf0;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark));
}

.rd-empty h3 {
  font-size: 20px;
  color: var(--ink);
  margin: 0 0 8px;
}

.rd-empty p {
  font-size: 14px;
  margin: 0 0 18px;
}

.rd-retry {
  padding: 8px 22px;
  border: 1px solid var(--brand);
  border-radius: 999px;
  background: var(--brand);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.rd-retry:hover {
  background: var(--brand-dark);
  border-color: var(--brand-dark);
}

/* ===== 响应式 ===== */
@media (max-width: 1024px) {
  .rd-kpis {
    grid-template-columns: repeat(2, 1fr);
  }

  .rd-row--charts,
  .rd-row--dist {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .rd-kpis {
    grid-template-columns: 1fr;
  }

  .rd-kpi__right {
    min-width: 110px;
  }

  .rd-kpi__value {
    font-size: 22px;
  }

  .rd-cat-grid {
    grid-template-columns: 1fr;
  }

  .rd-bar-chart__yaxis {
    width: 44px;
    font-size: 10px;
  }

  .rd-section {
    padding: 16px;
  }
}

@media (max-width: 480px) {
  .rd-kpi {
    flex-direction: column;
  }

  .rd-kpi__right {
    width: 100%;
    padding: 14px 18px;
    justify-content: flex-start;
  }

  .rd-cat-row__name {
    width: 60px;
  }
}
</style>
