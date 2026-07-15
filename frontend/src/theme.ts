import type { ThemeConfig } from 'ant-design-vue/es/config-provider/context'

export const appTheme: ThemeConfig = {
  token: {
    colorPrimary: '#7c67e1',
    colorInfo: '#7c67e1',
    colorSuccess: '#16a34a',
    colorWarning: '#d97706',
    colorError: '#dc2626',
    colorBgLayout: '#f6f7fb',
    colorText: '#1f2937',
    borderRadius: 10,
    borderRadiusLG: 16,
    controlHeight: 40,
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif',
  },
}

export const pageMotion = {
  initial: { opacity: 0, y: 14, scale: 0.995 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: -8, scale: 0.995 },
  transition: { type: 'spring', stiffness: 360, damping: 34, mass: 0.8 },
} as const
