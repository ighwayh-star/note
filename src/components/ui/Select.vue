<script setup lang="ts">
type Option = { value: string; label: string }

type Props = {
  modelValue: string
  options: Option[]
}

const props = defineProps<Props>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()
</script>

<template>
  <select
    :value="props.modelValue"
    class="h-10 w-full rounded-lg border border-zinc-200 bg-white px-3 text-sm outline-none transition focus:border-zinc-400 focus:ring-2 focus:ring-zinc-100"
    @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
  >
    <option v-for="o in props.options" :key="o.value" :value="o.value">{{ o.label }}</option>
  </select>
</template>

