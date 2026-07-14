<template>
  <div>
    <label v-if="label" class="block text-sm font-medium text-gray-700 mb-1.5">{{ label }}</label>
    <div class="relative">
      <component
        v-if="icon"
        :is="icon"
        class="w-5 h-5 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none"
      />
      <input
        v-if="type !== 'textarea'"
        :type="type"
        :value="modelValue"
        @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
        :placeholder="placeholder"
        :disabled="disabled"
        :step="step"
        :min="min"
        class="w-full rounded-xl border border-primary-light/60 bg-white px-4 py-2.5 text-sm text-gray-800 placeholder-gray-400 outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
        :class="[{ 'pl-11': icon }, inputClass]"
      />
      <textarea
        v-else
        :value="modelValue"
        @input="$emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
        :placeholder="placeholder"
        :disabled="disabled"
        :rows="rows"
        class="w-full min-h-[100px] resize-y rounded-xl border border-primary-light/60 bg-white px-4 py-2.5 text-sm text-gray-800 placeholder-gray-400 outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20"
        :class="[{ 'pl-11': icon }, inputClass]"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue?: string | number
  type?: string
  placeholder?: string
  label?: string
  disabled?: boolean
  icon?: object
  rows?: number
  step?: string
  min?: string | number
  inputClass?: string
}>()

defineEmits(['update:modelValue'])
</script>
