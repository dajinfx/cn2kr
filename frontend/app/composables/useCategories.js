// 分类定义 + 颜色（全局共享）
export const CATEGORIES = [
  { name: '중국 테크', slug: 'tech', color: '#2563eb' },
  { name: '중국 여행', slug: 'travel', color: '#10b981' },
  { name: '중국 직구', slug: 'direct', color: '#f97316' },
]

export function categoryColor(name) {
  return CATEGORIES.find((c) => c.name === name)?.color || '#2563eb'
}
