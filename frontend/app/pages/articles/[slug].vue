<template>
  <div class="container">
    <article v-if="post" class="article">
      <h1>{{ post.title }}</h1>
      <div class="meta">
        {{ post.meta?.category }} · {{ date }}
      </div>
      <img v-if="post.meta?.image" :src="post.meta.image" :alt="post.title" style="width:100%; border-radius:12px; margin: 8px 0 20px;" />
      <div v-if="videos.length" class="article-videos">
        <div v-for="(v, i) in videos" :key="i" class="video-embed">
          <iframe v-if="v.kind === 'iframe'" :src="v.src" title="영상" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen loading="lazy"></iframe>
          <video v-else-if="v.kind === 'video'" :src="v.src" controls preload="none" playsinline></video>
        </div>
      </div>
      <div class="content">
        <ContentRenderer :value="post" />
      </div>
      <div v-if="tags.length" class="article-tags">
        <span v-for="t in tags" :key="t" class="tag-chip">{{ t }}</span>
      </div>
    </article>

    <div v-if="post" class="article-engagement">
      <LikeButton :path="post.path" />
      <div class="share-buttons">
        <button class="share-btn share-kakao" type="button" @click="shareKakao">카카오톡</button>
        <button class="share-btn" type="button" @click="shareX">X</button>
        <button class="share-btn" type="button" @click="shareFacebook">페이스북</button>
        <button class="share-btn" type="button" @click="copyLink">링크 복사</button>
      </div>
    </div>

    <Comments v-if="post" :path="post.path" />

    <!-- 相关文章推荐（内链） -->
    <section v-if="relatedPosts.length" class="related">
      <div class="section-head">
        <div class="left"><h2>관련 글</h2></div>
      </div>
      <div class="related-grid">
        <PostCard v-for="p in relatedPosts" :key="p.path" :post="p" />
      </div>
    </section>

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

// 标签（frontmatter tags，用于展示 + SEO keywords）
const tags = computed(() => {
  const t = post.value?.meta?.tags
  if (Array.isArray(t)) return t.filter(Boolean)
  if (typeof t === 'string') return t.split(',').map(s => s.trim()).filter(Boolean)
  return []
})

// 原文视频（frontmatter videos，嵌入渲染）
function embedVideo(url) {
  const u = String(url)
  const low = u.toLowerCase()
  // 直连视频文件
  if (/\.(mp4|webm|m3u8)(\?|$)/.test(low)) {
    return { kind: 'video', src: u }
  }
  // B站
  if (low.includes('bilibili')) {
    const bv = u.match(/bilibili\.com\/video\/(BV[0-9A-Za-z]+)/) || u.match(/[?&]bvid=(BV[0-9A-Za-z]+)/i)
    if (bv) return { kind: 'iframe', src: `https://player.bilibili.com/player.html?bvid=${bv[1]}&autoplay=0` }
  }
  // YouTube
  const yt = u.match(/youtube\.com\/watch\?v=([\w-]+)/) || u.match(/youtu\.be\/([\w-]+)/) || u.match(/youtube\.com\/embed\/([\w-]+)/)
  if (yt) return { kind: 'iframe', src: `https://www.youtube.com/embed/${yt[1]}` }
  // 其他平台 iframe（腾讯/优酷/爱奇艺/抖音等，通常已是可嵌入 URL）
  return { kind: 'iframe', src: u }
}
const videos = computed(() => {
  const v = post.value?.meta?.videos
  if (!Array.isArray(v)) return []
  return v.filter(Boolean).map(embedVideo)
})

// 相关文章（同分类，排除当前，最多 6 篇）
const relatedPosts = computed(() => {
  if (!post.value) return []
  const cat = post.value.meta?.category
  return (allPosts.value || [])
    .filter((p) => p.path !== post.value.path && p.meta?.category === cat)
    .slice(0, 6)
})

// 分享
const shareUrl = computed(() => `https://cn2kr.net${post.value?.path || ''}`)
const shareText = computed(() => post.value?.title || '')

function shareX() {
  window.open(
    `https://twitter.com/intent/tweet?url=${encodeURIComponent(shareUrl.value)}&text=${encodeURIComponent(shareText.value)}`,
    '_blank'
  )
}

function shareFacebook() {
  window.open(
    `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl.value)}`,
    '_blank'
  )
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(shareUrl.value)
    alert('링크가 복사되었습니다')
  } catch {
    prompt('링크를 복사하세요', shareUrl.value)
  }
}

function shareKakao() {
  if (window.Kakao?.Share) {
    window.Kakao.Share.sendDefault({
      objectType: 'feed',
      content: {
        title: shareText.value,
        description: post.value?.description || '',
        imageUrl: post.value?.meta?.image ? `https://cn2kr.net${post.value.meta.image}` : '',
        link: { mobileWebUrl: shareUrl.value, webUrl: shareUrl.value },
      },
    })
  } else {
    // 未加载 Kakao SDK 时回退为复制链接
    copyLink()
  }
}

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
  keywords: computed(() => tags.value.join(', ')),
  ogTitle: seoTitle,
  ogDescription: seoDesc,
  ogImage: seoImage,
  ogUrl: seoUrl,
  ogType: 'article',
  articlePublishedTime: computed(() => post.value?.meta?.date || ''),
  canonical: seoUrl,
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
          keywords: tags.value.join(', '),
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
