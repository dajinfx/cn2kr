<template>
  <div>
    <!-- 头条焦点区 -->
    <section v-if="featured" class="hero">
      <div class="container">
        <NuxtLink :to="featured.path" class="hero-card">
          <img :src="featured.meta?.image" :alt="featured.title" loading="eager" />
          <div class="hero-scrim"></div>
          <div class="hero-content">
            <span class="hero-cat" :style="{ background: featuredColor }">{{ featured.meta?.category }}</span>
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

    <!-- 主内容：两栏（新闻列表 + 侧栏） -->
    <div class="container home-main">
      <div class="home-left">
        <div class="section-head">
          <div class="left">
            <h2>{{ activeTab === 'all' ? '최신 업데이트' : activeTab }}</h2>
          </div>
        </div>

        <!-- 密集新闻列表（MSN 风格） -->
        <div class="news-list">
          <article v-for="p in visibleGridPosts" :key="p.path" class="news-item">
            <NuxtLink :to="p.path" class="news-link">
              <div class="news-thumb">
                <img :src="p.meta?.image" :alt="p.title" loading="lazy" />
              </div>
              <div class="news-body">
                <h3>{{ p.title }}</h3>
                <p class="news-desc">{{ p.description }}</p>
                <div class="news-meta">
                  <span class="news-cat" :style="{ color: categoryColor(p.meta?.category) }">{{ p.meta?.category }}</span>
                  <span class="news-dot">·</span>
                  <span class="news-date">{{ formatDate(p.meta?.date) }}</span>
                </div>
              </div>
            </NuxtLink>
          </article>
        </div>

        <div v-if="visibleGridPosts.length < gridPosts.length" class="load-more-wrap">
          <button class="load-more" type="button" @click="loadMore">
            더 보기 <span class="load-more-count">({{ gridPosts.length - visibleGridPosts.length }}개 남음)</span>
          </button>
        </div>
      </div>

      <!-- 侧栏 -->
      <aside class="home-side">
        <section class="side-block">
          <h3 class="side-title">인기 글</h3>
          <ul class="side-list">
            <li v-for="p in popularPosts" :key="p.path">
              <NuxtLink :to="p.path">{{ p.title }}</NuxtLink>
            </li>
          </ul>
        </section>

        <section class="side-block">
          <h3 class="side-title">카테고리</h3>
          <ul class="side-list">
            <li v-for="cat in CATEGORIES" :key="cat.slug">
              <NuxtLink :to="`/category/${cat.slug}`">{{ cat.name }}</NuxtLink>
            </li>
          </ul>
        </section>

        <section class="side-block">
          <h3 class="side-title">실용 도구</h3>
          <ul class="side-list">
            <li><NuxtLink to="/tools">환율 · 관세 계산기</NuxtLink></li>
            <li><NuxtLink to="/about">cn2kr 소개</NuxtLink></li>
          </ul>
        </section>
      </aside>
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

// 头条 = 第一篇；列表 = 其余
const featured = computed(() => filteredPosts.value[0] || null)
const gridPosts = computed(() => filteredPosts.value.slice(1))
const featuredColor = computed(() => categoryColor(featured.value?.meta?.category))

// 侧栏「인기 글」= 最近 6 篇（暂无浏览量数据）
const popularPosts = computed(() => sortedPosts.value.slice(0, 6))

// 加载更多
const visibleCount = ref(12)
const visibleGridPosts = computed(() => gridPosts.value.slice(0, visibleCount.value))

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
