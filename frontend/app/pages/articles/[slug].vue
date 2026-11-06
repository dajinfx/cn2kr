<template>
  <div class="container">
    <article v-if="post" class="article">
      <h1>{{ post.title }}</h1>
      <div class="meta">
        {{ post.meta?.category }} · {{ date }}
      </div>
      <img v-if="post.meta?.image" :src="post.meta.image" :alt="post.title" style="width:100%; border-radius:12px; margin: 8px 0 20px;" />
      <div class="content">
        <ContentRenderer :value="post" />
      </div>
    </article>

    <div v-if="post" class="article-engagement">
      <LikeButton :path="post.path" />
    </div>

    <Comments v-if="post" :path="post.path" />

    <div v-else class="empty">
      <h2>글을 찾을 수 없어요</h2>
      <p>
        <NuxtLink to="/" style="color: var(--accent);">홈으로 돌아가기</NuxtLink>
      </p>
    </div>
  </div>
</template>

<script setup>
const route = useRoute()

const { data: allPosts } = await useAsyncData('all-posts-for-single', () =>
  queryCollection('articles').all()
)

// 按 path 精确匹配
const post = computed(() =>
  (allPosts.value || []).find((p) => p.path === '/articles/' + route.params.slug)
)

const date = computed(() => {
  const d = post.value?.meta?.date
  if (!d) return ''
  try {
    return new Date(d).toLocaleDateString('ko-KR')
  } catch {
    return d
  }
})

// 每篇文章独立 SEO 元标签（标题/描述/OG/结构化数据）
const seoTitle = computed(() => post.value?.title || '')
const seoDesc = computed(() => post.value?.description || '')
const seoImage = computed(() =>
  post.value?.meta?.image ? `https://cn2kr.net${post.value.meta.image}` : ''
)
const seoUrl = computed(() =>
  post.value?.path ? `https://cn2kr.net${post.value.path}` : ''
)

useSeoMeta({
  title: seoTitle,
  description: seoDesc,
  ogTitle: seoTitle,
  ogDescription: seoDesc,
  ogImage: seoImage,
  ogUrl: seoUrl,
  ogType: 'article',
  articlePublishedTime: computed(() => post.value?.meta?.date || ''),
})

useHead({
  script: [
    {
      type: 'application/ld+json',
      innerHTML: computed(() =>
        JSON.stringify({
          '@context': 'https://schema.org',
          '@type': 'Article',
          headline: seoTitle.value,
          description: seoDesc.value,
          image: seoImage.value || undefined,
          datePublished: post.value?.meta?.date,
          dateModified: post.value?.meta?.date,
          author: { '@type': 'Organization', name: 'cn2kr' },
          publisher: { '@type': 'Organization', name: 'cn2kr' },
          mainEntityOfPage: seoUrl.value,
        })
      ),
    },
  ],
})
</script>
