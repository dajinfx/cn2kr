<template>
  <div>
    <!-- 分类头部 -->
    <section class="cat-hero" :style="{ '--cat-color': catColor }">
      <div class="container">
        <span class="cat-hero-label">CATEGORY</span>
        <h1>{{ catName }}</h1>
        <p class="cat-hero-count">{{ posts.length }}개의 글</p>
      </div>
    </section>

    <div class="container">
      <PostGrid
        :posts="posts"
        empty-title="아직 이 카테고리에 글이 없어요"
      />
    </div>
  </div>
</template>

<script setup>
import { categoryColor } from '~/composables/useCategories'

const route = useRoute()

const catMap = {
  tech: '중국 테크',
  travel: '중국 여행',
  direct: '중국 직구',
}
const catName = computed(() => catMap[route.params.slug] || '카테고리')
const catColor = computed(() => categoryColor(catName.value))

const { data: allPosts } = await useAsyncData('all-posts-for-cat', () =>
  queryCollection('articles').all()
)

// 按分类过滤 + 日期倒序
const posts = computed(() =>
  (allPosts.value || [])
    .filter((p) => p.meta?.category === catName.value)
    .sort((a, b) => (b.meta?.date || '').localeCompare(a.meta?.date || ''))
)
</script>
