<script setup lang="ts">
import { ref, computed, onMounted, inject } from 'vue'
import CheckoutModal, { type CheckoutItem } from './CheckoutModal.vue'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// ---------- 类型定义 ----------
interface CartItem {
  id: number
  product_id: number
  product_name: string
  product_image: string | null
  product_price: number | null
  product_category: string | null
  quantity: number
  selected: boolean
}

// ---------- 导航 ----------
const navigate = inject<(page: string) => void>('navigate', () => {})
const switchToOrdersTab = inject<() => void>('switchToOrdersTab', () => navigate('orders'))

// ---------- 状态 ----------
const loading = ref(false)
const error = ref<string | null>(null)
const cartItems = ref<CartItem[]>([])

// 结算弹窗
const checkoutVisible = ref(false)
const checkoutItems = ref<CheckoutItem[]>([])

// 提示
const toast = ref<{ visible: boolean; message: string; type: 'success' | 'error' }>({
  visible: false,
  message: '',
  type: 'success',
})
let toastTimer: ReturnType<typeof setTimeout> | null = null

function showToast(message: string, type: 'success' | 'error' = 'success') {
  toast.value = { visible: true, message, type }
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toast.value.visible = false
  }, 2500)
}

// ---------- 请求头 ----------
function authHeaders(): HeadersInit {
  const token = localStorage.getItem('token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

// ---------- 计算属性 ----------
const allSelected = computed({
  get: () => cartItems.value.length > 0 && cartItems.value.every((item) => item.selected),
  set: (val: boolean) => {
    cartItems.value.forEach((item) => {
      updateItemSelection(item, val)
    })
  },
})

const selectedItems = computed(() => cartItems.value.filter((item) => item.selected))

const selectedCount = computed(() =>
  selectedItems.value.reduce((sum, item) => sum + item.quantity, 0),
)

const totalAmount = computed(() =>
  selectedItems.value.reduce((sum, item) => sum + (item.product_price ?? 0) * item.quantity, 0),
)

// ---------- 加载购物车 ----------
async function loadCart() {
  loading.value = true
  error.value = null
  try {
    const response = await fetch(`${API_BASE}/api/user/cart`, {
      headers: authHeaders(),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    cartItems.value = data.items || data.cart || []
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载购物车失败'
  } finally {
    loading.value = false
  }
}

// ---------- 更新购物车项 ----------
async function updateQuantity(item: CartItem, delta: number) {
  const newQty = item.quantity + delta
  if (newQty < 1) return
  const oldQty = item.quantity
  item.quantity = newQty
  try {
    const response = await fetch(`${API_BASE}/api/user/cart/${item.id}`, {
      method: 'PUT',
      headers: authHeaders(),
      body: JSON.stringify({ quantity: newQty, selected: item.selected }),
    })
    if (!response.ok) {
      item.quantity = oldQty
      throw new Error(`HTTP ${response.status}`)
    }
  } catch {
    item.quantity = oldQty
    showToast('更新数量失败', 'error')
  }
}

async function updateItemSelection(item: CartItem, selected: boolean) {
  const oldSelected = item.selected
  item.selected = selected
  try {
    const response = await fetch(`${API_BASE}/api/user/cart/${item.id}`, {
      method: 'PUT',
      headers: authHeaders(),
      body: JSON.stringify({ quantity: item.quantity, selected }),
    })
    if (!response.ok) {
      item.selected = oldSelected
      throw new Error(`HTTP ${response.status}`)
    }
  } catch {
    item.selected = oldSelected
    showToast('更新选择失败', 'error')
  }
}

function toggleSelect(item: CartItem) {
  updateItemSelection(item, !item.selected)
}

// ---------- 删除购物车项 ----------
async function removeItem(item: CartItem) {
  if (!confirm(`确定要删除「${item.product_name}」吗？`)) return
  try {
    const response = await fetch(`${API_BASE}/api/user/cart/${item.id}`, {
      method: 'DELETE',
      headers: authHeaders(),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    cartItems.value = cartItems.value.filter((i) => i.id !== item.id)
    showToast('已删除')
  } catch (e) {
    showToast(e instanceof Error ? e.message : '删除失败', 'error')
  }
}

// ---------- 结算流程 ----------
function openCheckout() {
  if (selectedItems.value.length === 0) {
    showToast('请先选择商品', 'error')
    return
  }
  checkoutItems.value = selectedItems.value.map((item) => ({
    cart_item_id: item.id,
    product_id: item.product_id,
    product_name: item.product_name,
    product_image: item.product_image,
    product_price: item.product_price,
    product_category: item.product_category,
    quantity: item.quantity,
  }))
  checkoutVisible.value = true
}

function closeCheckout() {
  checkoutVisible.value = false
}

function onCheckoutSuccess() {
  checkoutVisible.value = false
  showToast('下单成功！')
  loadCart()
  // 切换到订单标签
  setTimeout(() => {
    switchToOrdersTab()
  }, 800)
}

// ---------- 格式化 ----------
function formatPrice(price: number | null | undefined): string {
  if (price == null) return '--'
  return price.toFixed(2)
}

onMounted(() => {
  loadCart()
})
</script>

<template>
  <div class="shopping-cart">
    <!-- 提示 Toast -->
    <transition name="toast">
      <div v-if="toast.visible" :class="['sc-toast', `sc-toast--${toast.type}`]">
        {{ toast.message }}
      </div>
    </transition>

    <!-- 错误提示 -->
    <div v-if="error" class="sc-error">{{ error }}</div>

    <!-- 加载中 -->
    <div v-if="loading" class="sc-loading">
      <div class="sc-loading__spinner"></div>
      <p>正在加载购物车...</p>
    </div>

    <!-- 购物车列表 -->
    <div v-else-if="cartItems.length > 0" class="sc-list">
      <!-- 表头 -->
      <div class="sc-list__header">
        <label class="sc-checkbox sc-checkbox--all">
          <input type="checkbox" v-model="allSelected" />
          <span>全选</span>
        </label>
        <span class="sc-col-info">商品信息</span>
        <span class="sc-col-price">单价</span>
        <span class="sc-col-qty">数量</span>
        <span class="sc-col-subtotal">小计</span>
        <span class="sc-col-action">操作</span>
      </div>

      <!-- 商品行 -->
      <div
        v-for="item in cartItems"
        :key="item.id"
        :class="['sc-item', { 'sc-item--unselected': !item.selected }]"
      >
        <label class="sc-checkbox">
          <input
            type="checkbox"
            :checked="item.selected"
            @change="toggleSelect(item)"
          />
        </label>

        <div class="sc-item__info">
          <div class="sc-item__image">
            <img
              v-if="item.product_image"
              :src="item.product_image"
              :alt="item.product_name"
              @error="(e: any) => e.target.style.display = 'none'"
            />
            <div v-if="!item.product_image" class="sc-item__noimg">暂无图片</div>
          </div>
          <div class="sc-item__text">
            <h3 class="sc-item__name" :title="item.product_name">{{ item.product_name }}</h3>
            <span v-if="item.product_category" class="sc-item__cat">{{ item.product_category }}</span>
          </div>
        </div>

        <div class="sc-item__price">¥{{ formatPrice(item.product_price) }}</div>

        <div class="sc-item__qty">
          <button @click="updateQuantity(item, -1)" :disabled="item.quantity <= 1">−</button>
          <span>{{ item.quantity }}</span>
          <button @click="updateQuantity(item, 1)">+</button>
        </div>

        <div class="sc-item__subtotal">
          ¥{{ formatPrice((item.product_price ?? 0) * item.quantity) }}
        </div>

        <button class="sc-item__del" @click="removeItem(item)">删除</button>
      </div>

      <!-- 底部结算栏 -->
      <div class="sc-footer">
        <label class="sc-checkbox sc-checkbox--all">
          <input type="checkbox" v-model="allSelected" />
          <span>全选</span>
        </label>
        <span class="sc-footer__selected">
          已选 <strong>{{ selectedCount }}</strong> 件商品
        </span>
        <div class="sc-footer__right">
          <span class="sc-footer__total">
            合计：<strong>¥{{ formatPrice(totalAmount) }}</strong>
          </span>
          <button
            class="sc-footer__btn"
            :disabled="selectedItems.length === 0"
            @click="openCheckout"
          >
            去结算 ({{ selectedItems.length }})
          </button>
        </div>
      </div>
    </div>

    <!-- 空购物车 -->
    <div v-else class="sc-empty">
      <div class="sc-empty__icon">车</div>
      <h3>购物车空空如也</h3>
      <p>快去挑选心仪的商品吧</p>
      <button class="sc-empty__btn" @click="navigate('products')">去购物</button>
    </div>

    <!-- 结算弹窗 -->
    <CheckoutModal
      :visible="checkoutVisible"
      :items="checkoutItems"
      mode="cart"
      @close="closeCheckout"
      @success="onCheckoutSuccess"
    />
  </div>
</template>

<style scoped>
.shopping-cart {
  position: relative;
}

/* Toast */
.sc-toast {
  position: fixed;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 200;
  padding: 12px 28px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

.sc-toast--success {
  background: var(--green);
}

.sc-toast--error {
  background: var(--brand);
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-10px);
}

/* 加载 */
.sc-loading {
  text-align: center;
  padding: 80px 20px;
  color: var(--muted);
}

.sc-loading__spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--line);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: sc-spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

@keyframes sc-spin {
  to { transform: rotate(360deg); }
}

/* 错误 */
.sc-error {
  background: #fff0f0;
  color: #c33;
  padding: 14px 18px;
  border-radius: 12px;
  margin-bottom: 20px;
  font-size: 14px;
}

/* 购物车列表 */
.sc-list {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
}

.sc-list__header {
  display: grid;
  grid-template-columns: 60px 1fr 120px 140px 120px 80px;
  align-items: center;
  padding: 14px 20px;
  background: rgba(217, 95, 45, 0.04);
  border-bottom: 1px solid var(--line);
  font-size: 13px;
  color: var(--muted);
  font-weight: 600;
}

/* 复选框 */
.sc-checkbox {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 13px;
  color: var(--muted);
}

.sc-checkbox input[type='checkbox'] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: var(--brand);
}

.sc-checkbox--all {
  font-weight: 600;
}

/* 商品行 */
.sc-item {
  display: grid;
  grid-template-columns: 60px 1fr 120px 140px 120px 80px;
  align-items: center;
  padding: 18px 20px;
  border-bottom: 1px solid var(--line);
  transition: background 0.2s;
}

.sc-item:hover {
  background: rgba(217, 95, 45, 0.02);
}

.sc-item--unselected {
  opacity: 0.6;
}

.sc-item__info {
  display: flex;
  align-items: center;
  gap: 14px;
}

.sc-item__image {
  width: 80px;
  height: 80px;
  border-radius: 10px;
  overflow: hidden;
  background: #f8f4ef;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.sc-item__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.sc-item__noimg {
  font-size: 12px;
  color: var(--muted);
}

.sc-item__text {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sc-item__name {
  font-size: 14px;
  margin: 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  color: var(--ink);
}

.sc-item__cat {
  font-size: 12px;
  color: var(--muted);
  padding: 1px 8px;
  background: rgba(217, 95, 45, 0.08);
  border-radius: 4px;
  width: fit-content;
}

.sc-item__price {
  font-size: 14px;
  color: var(--ink);
}

.sc-item__qty {
  display: flex;
  align-items: center;
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
  width: fit-content;
}

.sc-item__qty button {
  width: 32px;
  height: 32px;
  border: none;
  background: var(--panel);
  font-size: 16px;
  cursor: pointer;
  color: var(--ink);
  transition: background 0.2s;
}

.sc-item__qty button:hover:not(:disabled) {
  background: rgba(217, 95, 45, 0.08);
  color: var(--brand);
}

.sc-item__qty button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.sc-item__qty span {
  width: 44px;
  text-align: center;
  font-size: 14px;
  font-weight: 600;
}

.sc-item__subtotal {
  font-size: 16px;
  font-weight: 700;
  color: var(--brand);
}

.sc-item__del {
  padding: 6px 12px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: transparent;
  color: var(--muted);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.sc-item__del:hover {
  border-color: var(--brand);
  color: var(--brand);
  background: rgba(217, 95, 45, 0.06);
}

/* 底部结算栏 */
.sc-footer {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 18px 20px;
  background: rgba(217, 95, 45, 0.04);
  position: sticky;
  bottom: 0;
}

.sc-footer__selected {
  font-size: 14px;
  color: var(--muted);
}

.sc-footer__selected strong {
  color: var(--brand);
  font-size: 16px;
}

.sc-footer__right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 20px;
}

.sc-footer__total {
  font-size: 15px;
  color: var(--ink);
}

.sc-footer__total strong {
  font-size: 22px;
  color: var(--brand);
  font-weight: 800;
}

.sc-footer__btn {
  padding: 12px 36px;
  border: none;
  border-radius: 999px;
  color: #fff;
  background: var(--brand);
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s;
}

.sc-footer__btn:hover:not(:disabled) {
  background: var(--brand-dark);
}

.sc-footer__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 空状态 */
.sc-empty {
  text-align: center;
  padding: 80px 20px;
  color: var(--muted);
}

.sc-empty__icon {
  display: inline-grid;
  width: 80px;
  height: 80px;
  place-items: center;
  border-radius: 24px;
  margin-bottom: 20px;
  font-size: 32px;
  font-weight: 800;
  color: #fffaf0;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark));
}

.sc-empty h3 {
  font-size: 20px;
  color: var(--ink);
  margin: 0 0 8px;
}

.sc-empty p {
  font-size: 14px;
  margin: 0 0 20px;
}

.sc-empty__btn {
  padding: 10px 28px;
  border: none;
  border-radius: 999px;
  color: #fff;
  background: var(--brand);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.sc-empty__btn:hover {
  background: var(--brand-dark);
}

/* 结算弹窗 */
.sc-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 150;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  backdrop-filter: blur(4px);
}

.sc-modal {
  width: min(640px, 100%);
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  background: var(--panel);
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.3);
}

.sc-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--line);
}

.sc-modal__header h2 {
  font-size: 18px;
  margin: 0;
}

.sc-modal__close {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.06);
  font-size: 20px;
  cursor: pointer;
  transition: background 0.2s;
}

.sc-modal__close:hover {
  background: rgba(0, 0, 0, 0.14);
}

.sc-modal__body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.sc-section {
  margin-bottom: 24px;
}

.sc-section:last-child {
  margin-bottom: 0;
}

.sc-section__title {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 12px;
  padding-left: 10px;
  border-left: 3px solid var(--brand);
}

/* 地址列表 */
.sc-addr-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.sc-addr {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.sc-addr:hover {
  border-color: var(--brand);
}

.sc-addr.active {
  border-color: var(--brand);
  background: rgba(217, 95, 45, 0.04);
}

.sc-addr input[type='radio'] {
  margin-top: 3px;
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: var(--brand);
}

.sc-addr__info {
  flex: 1;
}

.sc-addr__head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.sc-addr__name {
  font-weight: 700;
  font-size: 14px;
  color: var(--ink);
}

.sc-addr__phone {
  font-size: 13px;
  color: var(--muted);
}

.sc-addr__default {
  padding: 1px 8px;
  border-radius: 4px;
  font-size: 11px;
  color: #fff;
  background: var(--brand);
}

.sc-addr__detail {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
  line-height: 1.5;
}

.sc-addr__add {
  width: 100%;
  padding: 12px;
  border: 1px dashed var(--brand);
  border-radius: 12px;
  background: transparent;
  color: var(--brand);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.sc-addr__add:hover {
  background: rgba(217, 95, 45, 0.06);
}

/* 地址表单 */
.sc-addr-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(217, 95, 45, 0.02);
}

.sc-addr-form__row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.sc-addr-form__row:first-child {
  grid-template-columns: 1fr 1fr;
}

.sc-addr-form__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sc-addr-form__field label {
  font-size: 12px;
  color: var(--muted);
  font-weight: 600;
}

.sc-addr-form__field input {
  padding: 9px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  background: var(--panel);
  transition: border-color 0.2s;
}

.sc-addr-form__field input:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(217, 95, 45, 0.1);
}

.sc-addr-form__actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

/* 支付方式 */
.sc-pay {
  display: flex;
  gap: 12px;
}

.sc-pay__option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
  border: 1px solid var(--line);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.sc-pay__option:hover {
  border-color: var(--brand);
}

.sc-pay__option.active {
  border-color: var(--brand);
  background: rgba(217, 95, 45, 0.04);
}

.sc-pay__option input[type='radio'] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: var(--brand);
}

.sc-pay__icon {
  display: inline-grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: 8px;
  font-weight: 800;
  font-size: 14px;
  color: #fff;
}

.sc-pay__icon--wechat {
  background: var(--green);
}

.sc-pay__icon--alipay {
  background: #1677ff;
}

/* 备注 */
.sc-remark {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  background: var(--panel);
  transition: border-color 0.2s;
}

.sc-remark:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(217, 95, 45, 0.1);
}

/* 订单摘要 */
.sc-summary {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px 18px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(217, 95, 45, 0.02);
}

.sc-summary__row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: var(--muted);
}

.sc-summary__row--total {
  padding-top: 10px;
  border-top: 1px solid var(--line);
  font-size: 16px;
  color: var(--ink);
  font-weight: 700;
}

.sc-summary__amount {
  font-size: 22px;
  color: var(--brand);
  font-weight: 800;
}

/* 按钮 */
.sc-btn {
  padding: 10px 24px;
  border: 1px solid var(--brand);
  border-radius: 999px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.sc-btn--ghost {
  color: var(--muted);
  background: transparent;
  border-color: var(--line);
}

.sc-btn--ghost:hover {
  border-color: var(--brand);
  color: var(--brand);
}

.sc-btn--primary {
  color: #fff;
  background: var(--brand);
  border-color: var(--brand);
}

.sc-btn--primary:hover:not(:disabled) {
  background: var(--brand-dark);
}

.sc-btn--primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sc-btn--lg {
  padding: 12px 36px;
  font-size: 15px;
}

.sc-modal__footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 18px 24px;
  border-top: 1px solid var(--line);
}

/* 弹窗过渡 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s;
}

.modal-enter-active .sc-modal,
.modal-leave-active .sc-modal {
  transition: transform 0.25s;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .sc-modal,
.modal-leave-to .sc-modal {
  transform: scale(0.95) translateY(20px);
}

/* 响应式 */
@media (max-width: 900px) {
  .sc-list__header {
    display: none;
  }

  .sc-item {
    grid-template-columns: 40px 1fr;
    gap: 12px;
    padding: 16px;
  }

  .sc-item__info {
    grid-column: 2;
  }

  .sc-item__price,
  .sc-item__qty,
  .sc-item__subtotal,
  .sc-item__del {
    grid-column: 2;
  }

  .sc-item__price::before {
    content: '单价：';
    color: var(--muted);
  }

  .sc-item__subtotal::before {
    content: '小计：';
    color: var(--muted);
    font-weight: 400;
    font-size: 14px;
  }

  .sc-footer {
    flex-wrap: wrap;
    gap: 12px;
  }

  .sc-footer__right {
    width: 100%;
    justify-content: space-between;
  }

  .sc-addr-form__row {
    grid-template-columns: 1fr !important;
  }
}
</style>
