<script setup lang="ts">
type Props = {
  modelValue: string
  placeholder?: string
  type?: string
}

const props = withDefaults(defineProps<Props>(), {
  type: 'text',
  placeholder: '',
})
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()
</script>

<template>
  <input
    :value="props.modelValue"
    :type="props.type"
    :placeholder="props.placeholder"
    class="h-10 w-full rounded-lg border border-zinc-200 bg-white px-3 text-sm outline-none transition focus:border-zinc-400 focus:ring-2 focus:ring-zinc-100"
    @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
  />
</template>

