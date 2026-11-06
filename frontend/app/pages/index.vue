<template>
  <div>
    <!-- 头条焦点区 -->
    <section v-if="featured" class="hero">
      <div class="container">
        <NuxtLink :to="featured.path" class="hero-card">
          <img
            :src="featured.meta?.image"
            :alt="featured.title"
            loading="eager"
          />
          <div class="hero-scrim"></div>
          <div class="hero-content">
            <span class="hero-cat" :style="{ background: featuredColor }">
              {{ featured.meta?.category }}
            </span>
            <h1>{{ featured.title }}</h1>
            <p>{{ featured.description }}</p>
            <span class="hero-more">자세히 보기 →</span>
          </div>
        </NuxtLink>
      </div>
    </section>

    <!-- 分类标签页签 -->
    <div class="tabs-wrap">
      <div class="container">
        <div class="tabs">
          <button
            v-for="tab in tabs"
            :key="tab.slug"
            :class="{ active: activeTab === tab.slug }"
            @click="activeTab = tab.slug"
          >
            {{ tab.name }}
          </button>
        </div>
      </div>
    </div>

    <!-- 杂志式混排（头条之后的其余文章） -->
    <div class="container">
      <div class="section-head">
        <div class="left">
          <h2>{{ activeTab === 'all' ? '최신 업데이트' : activeTab }}</h2>
        </div>
      </div>
      <PostGrid :posts="gridPosts" />
    </div>
  </div>
</template>

<script setup>
import { CATEGORIES, categoryColor } from '~/composables/useCategories'

const tabs = [{ name: '전체', slug: 'all' }, ...CATEGORIES]
const activeTab = ref('all')

const { data: posts } = await useAsyncData('home-posts', () =>
  queryCollection('articles').all()
)

// 按日期倒序
const sortedPosts = computed(() =>
  [...(posts.value || [])].sort((a, b) =>
    (b.meta?.date || '').localeCompare(a.meta?.date || '')
  )
)

const filteredPosts = computed(() => {
  if (activeTab.value === 'all') return sortedPosts.value
  const cat = CATEGORIES.find((c) => c.slug === activeTab.value)
  return sortedPosts.value.filter((p) => p.meta?.category === cat?.name)
})

// 头条 = 当前分类下第一篇；网格 = 其余
const featured = computed(() => filteredPosts.value[0] || null)
const gridPosts = computed(() => filteredPosts.value.slice(1))
const featuredColor = computed(() => categoryColor(featured.value?.meta?.category))

// 首页 SEO
useSeoMeta({
  title: 'cn2kr — 중국 테크·여행·직구',
  description: '중국의 테크 · 여행 · 직구를 한국 시선으로 소개합니다. 중국 직구, 여행, 테크 실전 정보를 매일 업데이트합니다.',
  ogTitle: 'cn2kr — 중국 테크·여행·직구',
  ogDescription: '중국의 테크 · 여행 · 직구를 한국 시선으로 소개합니다.',
  ogUrl: 'https://cn2kr.net',
})
</script>
