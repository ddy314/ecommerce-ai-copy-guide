<script setup lang="ts">
import { ref, computed } from 'vue'
import { Card, Layout, LayoutContent, TypographyParagraph, TypographyTitle } from 'ant-design-vue'
import { motion } from 'motion-v'
import SideBar from '../common/SideBar.vue'
import {
  BarChartOutlined,
  AppstoreOutlined,
  BookOutlined,
  CustomerServiceOutlined,
  FileTextOutlined,
  MessageOutlined,
  OrderedListOutlined,
  TeamOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons-vue'
import { pageMotion } from '../../theme'

interface UserInfo {
  username: string
  role: string
  nickname?: string
  avatar?: string
  [key: string]: unknown
}

const props = defineProps<{
  userInfo: UserInfo
}>()

const emit = defineEmits<{
  (e: 'logout'): void
}>()

type MerchantPage =
  | 'dashboard'
  | 'products'
  | 'orders'
  | 'copy'
  | 'knowledge'
  | 'review'
  | 'live'
  | 'qa-stats'
  | 'users'
  | 'profile'
  | 'customer-service'

const menuItems: { key: MerchantPage; name: string; icon: any; desc: string }[] = [
  { key: 'dashboard', name: '数据看板', icon: BarChartOutlined, desc: '收入组成与商品流量监测' },
  { key: 'products', name: '商品管理', icon: AppstoreOutlined, desc: '管理商品信息与上下架' },
  { key: 'orders', name: '订单管理', icon: OrderedListOutlined, desc: '查看订单并发货管理' },
  { key: 'copy', name: '文案生成', icon: FileTextOutlined, desc: 'AI 生成商品营销文案' },
  { key: 'knowledge', name: '知识库管理', icon: BookOutlined, desc: '维护商品知识库内容' },
  { key: 'review', name: '评论分析', icon: MessageOutlined, desc: '评论情感与痛点分析' },
  { key: 'live', name: '直播脚本', icon: VideoCameraOutlined, desc: '生成直播带货话术' },
  { key: 'qa-stats', name: '用户问答统计', icon: BarChartOutlined, desc: '用户咨询数据分析' },
  { key: 'users', name: '用户管理', icon: TeamOutlined, desc: '管理系统用户账号与权限' },
  { key: 'customer-service', name: '客服管理', icon: CustomerServiceOutlined, desc: '回复用户咨询消息' },
]

const activePage = ref<MerchantPage>('dashboard')

const activeMenu = computed(() =>
  menuItems.find((m) => m.key === activePage.value),
)

function selectPage(key: string) {
  activePage.value = key as MerchantPage
}

function handleLogout() {
  localStorage.removeItem('token')
  localStorage.removeItem('userInfo')
  emit('logout')
}

function handleAvatarUpdated(avatar: string) {
  props.userInfo.avatar = avatar
  const stored = localStorage.getItem('userInfo')
  if (stored) {
    try {
      const info = JSON.parse(stored)
      info.avatar = avatar
      localStorage.setItem('userInfo', JSON.stringify(info))
    } catch {
      // ignore
    }
  }
}
</script>

<template>
  <Layout class="min-h-screen">
    <SideBar
      :user-info="props.userInfo"
      :active-page="activePage"
      :menu="menuItems"
      @select-page="selectPage"
      @logout="handleLogout"
      @avatar-updated="handleAvatarUpdated"
    />
    <LayoutContent class="overflow-auto p-6 lg:p-8">
      <motion.div
        :key="activePage"
        :initial="pageMotion.initial"
        :animate="pageMotion.animate"
        :transition="pageMotion.transition"
      >
        <header v-if="activeMenu" class="mb-6">
          <TypographyTitle :level="2" class="!mb-1">{{ activeMenu.name }}</TypographyTitle>
          <TypographyParagraph type="secondary" class="!mb-0">{{ activeMenu.desc }}</TypographyParagraph>
        </header>
        <Card :bordered="false" class="min-h-[420px]">
          <slot :page="activePage" />
        </Card>
      </motion.div>
    </LayoutContent>
  </Layout>
</template>
