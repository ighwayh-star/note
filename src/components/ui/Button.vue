<script setup lang="ts">
type Props = {
  variant?: 'primary' | 'ghost' | 'danger'
  size?: 'sm' | 'md'
  type?: 'button' | 'submit' | 'reset'
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  type: 'button',
  disabled: false,
})

const base =
  'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition outline-none focus:ring-2 focus:ring-zinc-300 disabled:opacity-50 disabled:pointer-events-none'
const variants: Record<NonNullable<Props['variant']>, string> = {
  primary: 'bg-zinc-900 text-white hover:bg-zinc-800',
  ghost: 'bg-transparent text-zinc-900 hover:bg-zinc-100',
  danger: 'bg-red-600 text-white hover:bg-red-700',
}
const sizes: Record<NonNullable<Props['size']>, string> = {
  sm: 'h-9 px-3 text-sm',
  md: 'h-10 px-4 text-sm',
}
</script>

<template>
  <button :type="props.type" :disabled="props.disabled" :class="[base, variants[props.variant], sizes[props.size]]">
    <slot />
  </button>
</template>

