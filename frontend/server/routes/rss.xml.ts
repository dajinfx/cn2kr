// RSS 2.0 피드 생성 (정적 사이트용, 빌드 시 prerender)
const SITE_URL = 'https://cn2kr.net'

function escapeXml(value: string): string {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

function toPubDate(date: string | Date | undefined): string {
  if (!date) return ''
  const d = new Date(date)
  if (Number.isNaN(d.getTime())) return ''
  return d.toUTCString()
}

export default defineEventHandler(async (event) => {
  const posts = await queryCollection(event, 'articles').all()

  const sorted = [...posts].sort((a, b) =>
    (b.meta?.date || '').localeCompare(a.meta?.date || ''),
  )

  const items = sorted
    .map((p) => {
      // content v3: title/description 为顶层字段，category/date/image 在 meta 下
      const title = p.title || p.meta?.title || ''
      const description = p.description || p.meta?.description || ''
      const category = p.meta?.category || ''
      const date = toPubDate(p.meta?.date)
      const link = `${SITE_URL}${p.path}`

      return [
        '    <item>',
        `      <title>${escapeXml(title)}</title>`,
        `      <link>${escapeXml(link)}</link>`,
        `      <guid isPermaLink="true">${escapeXml(link)}</guid>`,
        date ? `      <pubDate>${escapeXml(date)}</pubDate>` : '',
        `      <description><![CDATA[${description}]]></description>`,
        category ? `      <category>${escapeXml(category)}</category>` : '',
        '    </item>',
      ]
        .filter(Boolean)
        .join('\n')
    })
    .join('\n')

  const xml = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
    '  <channel>',
    '    <title>cn2kr — 중국 테크·여행·직구</title>',
    `    <link>${SITE_URL}</link>`,
    '    <description>중국의 테크 · 여행 · 직구를 한국 시선으로 소개합니다.</description>',
    '    <language>ko</language>',
    `    <atom:link href="${SITE_URL}/rss.xml" rel="self" type="application/rss+xml" />`,
    items,
    '  </channel>',
    '</rss>',
  ]
    .filter(Boolean)
    .join('\n')

  setHeader(event, 'Content-Type', 'application/rss+xml; charset=utf-8')
  return xml
})
