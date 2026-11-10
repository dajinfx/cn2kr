<template>
  <div class="container">
    <div class="search-head">
      <h1>검색</h1>
      <input
        v-model="query"
        type="search"
        class="search-input"
        placeholder="검색어를 입력하세요"
        autofocus
      />
    </div>

    <div v-if="query.trim()" class="search-result-area">
      <p class="search-count">{{ results.length }}개의 결과</p>
      <div v-if="results.length" class="search-grid">
        <PostCard v-for="p in results" :key="p.path" :post="p" />
      </div>
      <div v-else class="empty">
        <h2>검색 결과가 없습니다</h2>
        <p>다른 검색어로 시도해보세요.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
const query = ref('')

const { data: allPosts } = await useAsyncData('search-posts', () =>
  queryCollection('articles').all()
)

const results = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return []
  return (allPosts.value || []).filter((p) => {
    return (
      (p.title || '').toLowerCase().includes(q) ||
      (p.description || '').toLowerCase().includes(q)
    )
  })
})

useSeoMeta({
  title: '검색 — cn2kr',
  description: 'cn2kr의 글을 검색해보세요.',
})
</script>
