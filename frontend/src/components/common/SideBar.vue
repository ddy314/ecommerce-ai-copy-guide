<script setup lang="ts">
import { h, ref } from 'vue'
import { Avatar, Button, LayoutSider, Menu, Space, TypographyText, Upload, message } from 'ant-design-vue'
import { LogoutOutlined, RobotOutlined, UploadOutlined } from '@ant-design/icons-vue'
import type { Component } from 'vue'
import type { UploadProps } from 'ant-design-vue'

interface UserInfo {
  username: string
  role: string
  nickname?: string
  avatar?: string
  [key: string]: unknown
}

interface MenuItem {
  key: string
  name: string
  icon: Component
  desc?: string
}

const props = defineProps<{
  userInfo: UserInfo
  activePage: string
  menu: MenuItem[]
  title?: string
  subtitle?: string
}>()

const emit = defineEmits<{
  (e: 'select-page', page: string): void
  (e: 'logout'): void
  (e: 'avatar-updated', avatar: string): void
}>()

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const avatarLoading = ref(false)

const antMenuItems = () =>
  props.menu.map((item) => ({
    key: item.key,
    icon: () => h(item.icon),
    label: item.name,
    title: item.desc || item.name,
  }))

const uploadAvatar: UploadProps['beforeUpload'] = async (file) => {
  avatarLoading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/api/auth/avatar`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(data.message || `HTTP ${response.status}`)
    emit('avatar-updated', data.avatar)
    message.success('头像已更新')
  } catch (error) {
    message.error(error instanceof Error ? error.message : '头像上传失败')
  } finally {
    avatarLoading.value = false
  }
  return false
}
</script>

<template>
  <LayoutSider width="256" theme="light" class="!sticky !top-0 !h-screen !border-r !border-slate-100">
    <div class="flex h-full flex-col">
      <div class="flex items-center gap-3 px-6 py-6">
        <span class="grid h-11 w-11 place-items-center rounded-2xl bg-violet-600 text-xl text-white shadow-lg shadow-violet-200">
          <RobotOutlined />
        </span>
        <span class="min-w-0">
          <TypographyText strong class="block !text-base">{{ title || '商家后台' }}</TypographyText>
          <TypographyText type="secondary" class="block truncate !text-xs">{{ subtitle || 'AI 电商运营中心' }}</TypographyText>
        </span>
      </div>

      <Menu
        mode="inline"
        :selected-keys="[activePage]"
        :items="antMenuItems()"
        class="flex-1 !border-0 px-3"
        @click="({ key }) => emit('select-page', String(key))"
      />

      <div class="border-t border-slate-100 p-4">
        <div class="mb-4 flex items-center gap-3 rounded-2xl bg-slate-50 p-3">
          <Upload :show-upload-list="false" accept="image/*" :before-upload="uploadAvatar">
            <Avatar :size="42" :src="props.userInfo.avatar" class="cursor-pointer !bg-violet-600">
              {{ (props.userInfo.nickname || props.userInfo.username || 'M').charAt(0).toUpperCase() }}
            </Avatar>
          </Upload>
          <span class="min-w-0 flex-1">
            <TypographyText strong class="block truncate">{{ props.userInfo.nickname || props.userInfo.username }}</TypographyText>
            <TypographyText type="secondary" class="block !text-xs">商家管理员</TypographyText>
          </span>
          <Button type="text" :loading="avatarLoading" title="上传头像"><UploadOutlined /></Button>
        </div>
        <Space direction="vertical" class="w-full">
          <Button danger block @click="emit('logout')"><LogoutOutlined />退出登录</Button>
        </Space>
      </div>
    </div>
  </LayoutSider>
</template>
