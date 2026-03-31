<script setup lang="ts">
const props = defineProps<{
  totalSeconds: number
}>()

const emit = defineEmits<{
  expired: []
  tick: [remaining: number]
}>()

const remaining = ref(props.totalSeconds)
let timer: ReturnType<typeof setInterval> | null = null

const displayTime = computed(() => {
  const m = Math.floor(remaining.value / 60)
  const s = remaining.value % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

const isWarning = computed(() => remaining.value <= 300)
const isDanger = computed(() => remaining.value <= 60)

onMounted(() => {
  timer = setInterval(() => {
    if (remaining.value <= 0) {
      if (timer) clearInterval(timer)
      emit('expired')
      return
    }
    remaining.value -= 1
    emit('tick', remaining.value)
  }, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div
    class="font-mono text-2xl font-bold px-4 py-2 rounded-lg border-2 transition-colors"
    :class="{
      'border-gray-200 text-gray-700': !isWarning && !isDanger,
      'border-yellow-300 text-yellow-600 bg-yellow-50': isWarning && !isDanger,
      'border-red-400 text-red-600 bg-red-50 animate-pulse': isDanger,
    }"
  >
    {{ displayTime }}
  </div>
</template>
