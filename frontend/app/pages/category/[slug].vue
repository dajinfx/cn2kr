<template>
  <div>
    <!-- 分类头部 -->
    <section class="cat-hero" :style="{ '--cat-color': catColor }">
      <div class="container">
        <span class="cat-hero-label">CATEGORY</span>
        <h1>{{ catName }}</h1>
      </div>
    </section>

    <!-- 图文新闻流（Yahoo 式，和首页一致） -->
    <div class="container">
      <div class="section-head">
        <div class="left">
          <h2>{{ catName }} 최신</h2>
        </div>
      </div>
      <div class="news-list">
        <NuxtLink v-for="p in posts" :key="p.path" :to="p.path" class="news-item">
          <div class="news-thumb">
            <img :src="p.meta?.image" :alt="p.title" loading="eager" />
          </div>
          <div class="news-body">
            <h3>{{ p.title }}</h3>
            <span class="news-meta">
              <span :style="{ color: categoryColor(p.meta?.category) }">{{ p.meta?.category }}</span>
              <span>·</span>
              <span>{{ formatDate(p.meta?.date) }}</span>
            </span>
          </div>
        </NuxtLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { CATEGORIES, categoryColor } from '~/composables/useCategories'

const route = useRoute()

const cat = computed(() => CATEGORIES.find((c) => c.slug === route.params.slug))
const catName = computed(() => cat.value?.name || '카테고리')
const catColor = computed(() => cat.value?.color || '#2563eb')

const { data: allPosts } = await useAsyncData('all-posts-for-cat', () =>
  queryCollection('articles').all()
)

// 按分类过滤 + 日期倒序
const posts = computed(() =>
  (allPosts.value || [])
    .filter((p) => p.meta?.category === catName.value)
    .sort((a, b) => (b.meta?.date || '').localeCompare(a.meta?.date || ''))
)

function formatDate(d) {
  if (!d) return ''
  try {
    return new Date(d).toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })
  } catch {
    return d
  }
}

// 分类页 SEO
useSeoMeta({
  title: computed(() => `${catName.value} — cn2kr`),
  description: computed(() => `${catName.value} 관련 중국 정보를 한국 시선으로 소개합니다.`),
  ogUrl: computed(() => `https://cn2kr.net/category/${route.params.slug}`),
})
</script>
