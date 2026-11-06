<template>
  <NuxtLink :to="post.path" class="card">
    <div class="card-thumb">
      <img v-if="post.meta?.image" :src="post.meta.image" :alt="post.title" loading="lazy" />
    </div>
    <div class="card-body">
      <span class="card-cat" :style="{ color: catColor, background: catColor + '18' }">
        {{ post.meta?.category }}
      </span>
      <h3 class="card-title">{{ post.title }}</h3>
      <p class="card-excerpt">{{ post.description }}</p>
      <span class="card-date">{{ date }}</span>
    </div>
  </NuxtLink>
</template>

<script setup>
import { categoryColor } from '~/composables/useCategories'

const props = defineProps({
  post: { type: Object, required: true },
})

const catColor = computed(() => categoryColor(props.post.meta?.category))

const date = computed(() => {
  const d = props.post.meta?.date
  if (!d) return ''
  try {
    return new Date(d).toLocaleDateString('ko-KR')
  } catch {
    return d
  }
})
</script>
