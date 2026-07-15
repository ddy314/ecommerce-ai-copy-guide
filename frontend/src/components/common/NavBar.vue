<script setup lang="ts">
import { h } from 'vue'
import { Avatar, Button, LayoutHeader, Menu, Space, TypographyText } from 'ant-design-vue'
import {
  CustomerServiceOutlined,
  HomeOutlined,
  LogoutOutlined,
  RobotOutlined,
  ShopOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'

interface UserInfo {
  username: string
  role: 'user' | 'merchant'
  nickname?: string
  avatar?: string
}

const props = defineProps<{ userInfo: UserInfo; activePage: string }>()
const emit = defineEmits<{
  (e: 'select-page', page: string): void
  (e: 'logout'): void
}>()

const menu = [
  { key: 'home', label: '首页', icon: () => h(HomeOutlined) },
  { key: 'products', label: '商品浏览', icon: () => h(ShopOutlined) },
  { key: 'customer-service', label: '客服咨询', icon: () => h(CustomerServiceOutlined) },
  { key: 'profile', label: '个人中心', icon: () => h(UserOutlined) },
]
</script>

<template>
  <LayoutHeader class="!sticky !top-0 !z-50 !flex !h-16 !items-center !border-b !border-slate-100 !bg-white !px-4 shadow-sm sm:!px-6">
    <button class="mr-5 flex shrink-0 items-center gap-2 text-lg font-bold text-violet-700" @click="emit('select-page', 'home')">
      <span class="grid h-9 w-9 place-items-center rounded-xl bg-violet-600 text-white"><RobotOutlined /></span>
      <span class="hidden sm:inline">AI 电商助手</span>
    </button>
    <Menu
      mode="horizontal"
      :selected-keys="[activePage]"
      :items="menu"
      class="min-w-0 flex-1 !border-0"
      @click="({ key }) => emit('select-page', String(key))"
    />
    <Space class="ml-4 shrink-0">
      <Avatar :src="props.userInfo.avatar" class="!bg-violet-600">
        {{ (props.userInfo.nickname || props.userInfo.username || 'U').charAt(0).toUpperCase() }}
      </Avatar>
      <TypographyText class="hidden lg:inline">{{ props.userInfo.nickname || props.userInfo.username }}</TypographyText>
      <Button type="text" danger title="退出登录" @click="emit('logout')"><LogoutOutlined /></Button>
    </Space>
  </LayoutHeader>
</template>
