<template>
  <div>
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

    <!-- 大图卡片网格 -->
    <div class="container">
      <div class="section-head">
        <div class="left">
          <h2>{{ activeTab === 'all' ? '전체' : activeTab }}</h2>
        </div>
      </div>

      <div class="card-grid">
        <NuxtLink v-for="p in visiblePosts" :key="p.path" :to="p.path" class="img-card">
          <div class="img-card-thumb">
            <img :src="p.meta?.image" :alt="p.title" loading="eager" />
          </div>
          <div class="img-card-body">
            <h3>{{ p.title }}</h3>
            <div class="img-card-meta">
              <span :style="{ color: categoryColor(p.meta?.category) }">{{ p.meta?.category }}</span>
              <span>·</span>
              <span>{{ formatDate(p.meta?.date) }}</span>
            </div>
          </div>
        </NuxtLink>
      </div>

      <div v-if="visiblePosts.length < filteredPosts.length" class="load-more-wrap">
        <button class="load-more" type="button" @click="loadMore">
          더 보기 <span class="load-more-count">({{ filteredPosts.length - visiblePosts.length }}개 남음)</span>
        </button>
      </div>
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

const visibleCount = ref(12)
const visiblePosts = computed(() => filteredPosts.value.slice(0, visibleCount.value))

function loadMore() {
  visibleCount.value += 12
}

watch(activeTab, () => {
  visibleCount.value = 12
})

function formatDate(d) {
  if (!d) return ''
  try {
    return new Date(d).toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })
  } catch {
    return d
  }
}

useSeoMeta({
  title: 'cn2kr — 중국 테크·여행·직구',
  description: '중국의 테크 · 여행 · 직구를 한국 시선으로 소개합니다. 중국 직구, 여행, 테크 실전 정보를 매일 업데이트합니다.',
  ogTitle: 'cn2kr — 중국 테크·여행·직구',
  ogDescription: '중국의 테크 · 여행 · 직구를 한국 시선으로 소개합니다.',
  ogUrl: 'https://cn2kr.net',
})
</script>
