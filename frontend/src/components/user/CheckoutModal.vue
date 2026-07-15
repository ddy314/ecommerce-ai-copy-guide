<script setup lang="ts">
import { ref, computed, watch } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export interface CheckoutItem {
  cart_item_id?: number
  product_id: number
  product_name: string
  product_image: string | null
  product_price: number | null
  product_category: string | null
  quantity: number
}

interface Address {
  id: number
  recipient: string
  phone: string
  province: string
  city: string
  district: string
  detail: string
  is_default: boolean
}

const props = defineProps<{
  visible: boolean
  items: CheckoutItem[]
  mode: 'cart' | 'buy-now'
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'success'): void
}>()

// ---------- 状态 ----------
const checkoutLoading = ref(false)
const addresses = ref<Address[]>([])
const selectedAddressId = ref<number | null>(null)
const payMethod = ref<'wechat' | 'alipay'>('wechat')
const remark = ref('')

// 新增地址表单
const showAddressForm = ref(false)
const addressForm = ref({
  recipient: '',
  phone: '',
  province: '',
  city: '',
  district: '',
  detail: '',
})
const addressFormLoading = ref(false)

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

// ---------- 计算属性 ----------
const totalCount = computed(() =>
  props.items.reduce((sum, item) => sum + item.quantity, 0),
)

const totalAmount = computed(() =>
  props.items.reduce((sum, item) => sum + (item.product_price ?? 0) * item.quantity, 0),
)

// ---------- 请求头 ----------
function authHeaders(): HeadersInit {
  const token = localStorage.getItem('token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

// ---------- 地址 ----------
async function loadAddresses() {
  try {
    const response = await fetch(`${API_BASE}/api/user/addresses`, {
      headers: authHeaders(),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    addresses.value = data.addresses || data || []
    const defaultAddr = addresses.value.find((a) => a.is_default)
    if (defaultAddr) {
      selectedAddressId.value = defaultAddr.id
    } else if (addresses.value.length > 0) {
      selectedAddressId.value = addresses.value[0].id
    }
  } catch {
    showToast('加载地址失败', 'error')
  }
}

function toggleAddressForm() {
  showAddressForm.value = !showAddressForm.value
  if (showAddressForm.value) {
    addressForm.value = {
      recipient: '',
      phone: '',
      province: '',
      city: '',
      district: '',
      detail: '',
    }
  }
}

async function saveAddress() {
  if (!addressForm.value.recipient || !addressForm.value.phone || !addressForm.value.detail) {
    showToast('请填写完整收货信息', 'error')
    return
  }
  addressFormLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/api/user/addresses`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(addressForm.value),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${response.status}`)
    }
    const data = await response.json()
    showToast('地址添加成功')
    showAddressForm.value = false
    await loadAddresses()
    if (data.id) {
      selectedAddressId.value = data.id
    } else if (addresses.value.length > 0) {
      selectedAddressId.value = addresses.value[addresses.value.length - 1].id
    }
  } catch (e) {
    showToast(e instanceof Error ? e.message : '添加地址失败', 'error')
  } finally {
    addressFormLoading.value = false
  }
}

function formatAddress(addr: Address): string {
  return `${addr.province}${addr.city}${addr.district}${addr.detail}`
}

// ---------- 下单 ----------
async function confirmOrder() {
  if (!selectedAddressId.value) {
    showToast('请选择收货地址', 'error')
    return
  }
  if (props.items.length === 0) {
    showToast('没有可下单的商品', 'error')
    return
  }

  checkoutLoading.value = true
  try {
    const payload: Record<string, unknown> = {
      address_id: selectedAddressId.value,
      pay_method: payMethod.value,
      remark: remark.value,
    }

    if (props.mode === 'buy-now') {
      const item = props.items[0]
      payload.product_id = item.product_id
      payload.quantity = item.quantity
    } else {
      const itemIds = props.items
        .map((item) => item.cart_item_id)
        .filter((id): id is number => id !== undefined)
      if (itemIds.length === 0) {
        throw new Error('购物车商品信息缺失')
      }
      payload.item_ids = itemIds
    }

    const response = await fetch(`${API_BASE}/api/user/orders`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(payload),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${response.status}`)
    }
    showToast('下单成功！')
    emit('success')
  } catch (e) {
    showToast(e instanceof Error ? e.message : '下单失败', 'error')
  } finally {
    checkoutLoading.value = false
  }
}

function close() {
  emit('close')
  showAddressForm.value = false
}

// ---------- 格式化 ----------
function formatPrice(price: number | null | undefined): string {
  if (price == null) return '--'
  return price.toFixed(2)
}

// ---------- 监听 ----------
watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      loadAddresses()
      remark.value = ''
    }
  },
  { immediate: true },
)
</script>

<template>
  <transition name="modal">
    <div v-if="visible" class="cm-overlay" @click.self="close">
      <div class="cm-modal">
        <!-- Toast -->
        <transition name="toast">
          <div v-if="toast.visible" :class="['cm-toast', `cm-toast--${toast.type}`]">
            {{ toast.message }}
          </div>
        </transition>

        <div class="cm-modal__header">
          <h2>确认订单</h2>
          <button class="cm-modal__close" @click="close">×</button>
        </div>

        <div class="cm-modal__body">
          <!-- 商品清单 -->
          <div class="cm-section">
            <div class="cm-section__title">商品清单</div>
            <div class="cm-items">
              <div v-for="item in items" :key="item.product_id" class="cm-item">
                <div class="cm-item__image">
                  <img v-if="item.product_image" :src="item.product_image" :alt="item.product_name" />
                  <div v-else class="cm-item__noimg">暂无图片</div>
                </div>
                <div class="cm-item__info">
                  <h4 class="cm-item__name">{{ item.product_name }}</h4>
                  <span v-if="item.product_category" class="cm-item__cat">{{ item.product_category }}</span>
                </div>
                <div class="cm-item__price">
                  <div>¥{{ formatPrice(item.product_price) }}</div>
                  <div class="cm-item__qty">×{{ item.quantity }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 收货地址 -->
          <div class="cm-section">
            <div class="cm-section__title">收货地址</div>

            <div v-if="addresses.length > 0 && !showAddressForm" class="cm-addr-list">
              <label
                v-for="addr in addresses"
                :key="addr.id"
                :class="['cm-addr', { active: selectedAddressId === addr.id }]"
              >
                <input type="radio" :value="addr.id" v-model="selectedAddressId" />
                <div class="cm-addr__info">
                  <div class="cm-addr__head">
                    <span class="cm-addr__name">{{ addr.recipient }}</span>
                    <span class="cm-addr__phone">{{ addr.phone }}</span>
                    <span v-if="addr.is_default" class="cm-addr__default">默认</span>
                  </div>
                  <p class="cm-addr__detail">{{ formatAddress(addr) }}</p>
                </div>
              </label>
            </div>

            <!-- 新增地址表单 -->
            <div v-if="showAddressForm" class="cm-addr-form">
              <div class="cm-addr-form__row">
                <div class="cm-addr-form__field">
                  <label>收货人</label>
                  <input v-model="addressForm.recipient" type="text" placeholder="请输入收货人姓名" />
                </div>
                <div class="cm-addr-form__field">
                  <label>手机号</label>
                  <input v-model="addressForm.phone" type="text" placeholder="请输入手机号" />
                </div>
              </div>
              <div class="cm-addr-form__row">
                <div class="cm-addr-form__field">
                  <label>省份</label>
                  <input v-model="addressForm.province" type="text" placeholder="省份" />
                </div>
                <div class="cm-addr-form__field">
                  <label>城市</label>
                  <input v-model="addressForm.city" type="text" placeholder="城市" />
                </div>
                <div class="cm-addr-form__field">
                  <label>区/县</label>
                  <input v-model="addressForm.district" type="text" placeholder="区/县" />
                </div>
              </div>
              <div class="cm-addr-form__field">
                <label>详细地址</label>
                <input v-model="addressForm.detail" type="text" placeholder="请输入详细地址" />
              </div>
              <div class="cm-addr-form__actions">
                <button class="cm-btn cm-btn--ghost" @click="toggleAddressForm">取消</button>
                <button class="cm-btn cm-btn--primary" :disabled="addressFormLoading" @click="saveAddress">
                  {{ addressFormLoading ? '保存中...' : '保存地址' }}
                </button>
              </div>
            </div>

            <button v-if="!showAddressForm" class="cm-addr__add" @click="toggleAddressForm">
              + 新增收货地址
            </button>
          </div>

          <!-- 支付方式 -->
          <div class="cm-section">
            <div class="cm-section__title">支付方式</div>
            <div class="cm-pay">
              <label :class="['cm-pay__option', { active: payMethod === 'wechat' }]">
                <input type="radio" value="wechat" v-model="payMethod" />
                <span class="cm-pay__icon cm-pay__icon--wechat">微</span>
                <span>微信支付</span>
              </label>
              <label :class="['cm-pay__option', { active: payMethod === 'alipay' }]">
                <input type="radio" value="alipay" v-model="payMethod" />
                <span class="cm-pay__icon cm-pay__icon--alipay">支</span>
                <span>支付宝</span>
              </label>
            </div>
          </div>

          <!-- 备注 -->
          <div class="cm-section">
            <div class="cm-section__title">订单备注</div>
            <textarea
              v-model="remark"
              class="cm-remark"
              placeholder="选填，给商家留言（如配送时间、发票信息等）"
              rows="3"
            ></textarea>
          </div>

          <!-- 订单摘要 -->
          <div class="cm-section">
            <div class="cm-section__title">订单摘要</div>
            <div class="cm-summary">
              <div class="cm-summary__row">
                <span>商品数量</span>
                <span>{{ totalCount }} 件</span>
              </div>
              <div class="cm-summary__row">
                <span>商品总额</span>
                <span>¥{{ formatPrice(totalAmount) }}</span>
              </div>
              <div class="cm-summary__row cm-summary__row--total">
                <span>应付金额</span>
                <span class="cm-summary__amount">¥{{ formatPrice(totalAmount) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="cm-modal__footer">
          <button class="cm-btn cm-btn--ghost" @click="close">取消</button>
          <button
            class="cm-btn cm-btn--primary cm-btn--lg"
            :disabled="checkoutLoading || !selectedAddressId"
            @click="confirmOrder"
          >
            {{ checkoutLoading ? '提交中...' : '确认下单' }}
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.cm-overlay {
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

.cm-modal {
  width: min(640px, 100%);
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  background: var(--panel, #fff);
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.3);
}

.cm-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--line, #eee);
}

.cm-modal__header h2 {
  font-size: 18px;
  margin: 0;
}

.cm-modal__close {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.06);
  font-size: 20px;
  cursor: pointer;
  transition: background 0.2s;
}

.cm-modal__close:hover {
  background: rgba(0, 0, 0, 0.14);
}

.cm-modal__body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.cm-section {
  margin-bottom: 24px;
}

.cm-section:last-child {
  margin-bottom: 0;
}

.cm-section__title {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink, #333);
  margin-bottom: 12px;
  padding-left: 10px;
  border-left: 3px solid var(--brand, #8b5cf6);
}

/* 商品清单 */
.cm-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cm-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px;
  border: 1px solid var(--line, #eee);
  border-radius: 12px;
  background: rgba(139, 92, 246, 0.02);
}

.cm-item__image {
  width: 64px;
  height: 64px;
  border-radius: 8px;
  overflow: hidden;
  background: #f8f4ef;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.cm-item__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cm-item__noimg {
  font-size: 12px;
  color: var(--muted, #888);
}

.cm-item__info {
  flex: 1;
  min-width: 0;
}

.cm-item__name {
  font-size: 14px;
  margin: 0 0 6px;
  line-height: 1.4;
  color: var(--ink, #333);
}

.cm-item__cat {
  font-size: 12px;
  color: var(--muted, #888);
  padding: 1px 8px;
  background: rgba(139, 92, 246, 0.08);
  border-radius: 4px;
}

.cm-item__price {
  text-align: right;
  font-size: 14px;
  color: var(--ink, #333);
  font-weight: 600;
}

.cm-item__qty {
  font-size: 12px;
  color: var(--muted, #888);
  font-weight: 400;
  margin-top: 4px;
}

/* 地址 */
.cm-addr-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.cm-addr {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--line, #eee);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.cm-addr:hover {
  border-color: var(--brand, #8b5cf6);
}

.cm-addr.active {
  border-color: var(--brand, #8b5cf6);
  background: rgba(139, 92, 246, 0.04);
}

.cm-addr input[type='radio'] {
  margin-top: 3px;
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: var(--brand, #8b5cf6);
}

.cm-addr__info {
  flex: 1;
}

.cm-addr__head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.cm-addr__name {
  font-weight: 700;
  font-size: 14px;
  color: var(--ink, #333);
}

.cm-addr__phone {
  font-size: 13px;
  color: var(--muted, #888);
}

.cm-addr__default {
  padding: 1px 8px;
  border-radius: 4px;
  font-size: 11px;
  color: #fff;
  background: var(--brand, #8b5cf6);
}

.cm-addr__detail {
  margin: 0;
  font-size: 13px;
  color: var(--muted, #888);
  line-height: 1.5;
}

.cm-addr__add {
  width: 100%;
  padding: 12px;
  border: 1px dashed var(--brand, #8b5cf6);
  border-radius: 12px;
  background: transparent;
  color: var(--brand, #8b5cf6);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.cm-addr__add:hover {
  background: rgba(139, 92, 246, 0.06);
}

.cm-addr-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
  border: 1px solid var(--line, #eee);
  border-radius: 12px;
  background: rgba(139, 92, 246, 0.02);
}

.cm-addr-form__row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.cm-addr-form__row:first-child {
  grid-template-columns: 1fr 1fr;
}

.cm-addr-form__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cm-addr-form__field label {
  font-size: 12px;
  color: var(--muted, #888);
  font-weight: 600;
}

.cm-addr-form__field input {
  padding: 9px 12px;
  border: 1px solid var(--line, #eee);
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  background: var(--panel, #fff);
  transition: border-color 0.2s;
}

.cm-addr-form__field input:focus {
  outline: none;
  border-color: var(--brand, #8b5cf6);
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
}

.cm-addr-form__actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

/* 支付 */
.cm-pay {
  display: flex;
  gap: 12px;
}

.cm-pay__option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
  border: 1px solid var(--line, #eee);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.cm-pay__option:hover {
  border-color: var(--brand, #8b5cf6);
}

.cm-pay__option.active {
  border-color: var(--brand, #8b5cf6);
  background: rgba(139, 92, 246, 0.04);
}

.cm-pay__option input[type='radio'] {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: var(--brand, #8b5cf6);
}

.cm-pay__icon {
  display: inline-grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: 8px;
  font-weight: 800;
  font-size: 14px;
  color: #fff;
}

.cm-pay__icon--wechat {
  background: #07c160;
}

.cm-pay__icon--alipay {
  background: #1677ff;
}

/* 备注 */
.cm-remark {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--line, #eee);
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  background: var(--panel, #fff);
  transition: border-color 0.2s;
}

.cm-remark:focus {
  outline: none;
  border-color: var(--brand, #8b5cf6);
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
}

/* 摘要 */
.cm-summary {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px 18px;
  border: 1px solid var(--line, #eee);
  border-radius: 12px;
  background: rgba(139, 92, 246, 0.02);
}

.cm-summary__row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: var(--muted, #888);
}

.cm-summary__row--total {
  padding-top: 10px;
  border-top: 1px solid var(--line, #eee);
  font-size: 16px;
  color: var(--ink, #333);
  font-weight: 700;
}

.cm-summary__amount {
  font-size: 22px;
  color: var(--brand, #8b5cf6);
  font-weight: 800;
}

/* 按钮 */
.cm-btn {
  padding: 10px 24px;
  border: 1px solid var(--brand, #8b5cf6);
  border-radius: 999px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.cm-btn--ghost {
  color: var(--muted, #888);
  background: transparent;
  border-color: var(--line, #eee);
}

.cm-btn--ghost:hover {
  border-color: var(--brand, #8b5cf6);
  color: var(--brand, #8b5cf6);
}

.cm-btn--primary {
  color: #fff;
  background: var(--brand, #8b5cf6);
  border-color: var(--brand, #8b5cf6);
}

.cm-btn--primary:hover:not(:disabled) {
  background: var(--brand-dark, #7c3aed);
}

.cm-btn--primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cm-btn--lg {
  padding: 12px 36px;
  font-size: 15px;
}

.cm-modal__footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 18px 24px;
  border-top: 1px solid var(--line, #eee);
}

/* Toast */
.cm-toast {
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

.cm-toast--success {
  background: #07c160;
}

.cm-toast--error {
  background: #ff4d4f;
}

/* 弹窗过渡 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s;
}

.modal-enter-active .cm-modal,
.modal-leave-active .cm-modal {
  transition: transform 0.25s;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .cm-modal,
.modal-leave-to .cm-modal {
  transform: scale(0.95) translateY(20px);
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

/* 响应式 */
@media (max-width: 600px) {
  .cm-addr-form__row {
    grid-template-columns: 1fr !important;
  }
}
</style>
