<template>
  <div class="container">
    <div class="tools-hero">
      <h1>실용 도구</h1>
      <p>중국 직구·여행에 필요한 계산기를 모았습니다</p>
    </div>

    <div class="tools-grid">
      <!-- 汇率计算器 -->
      <section class="tool-card">
        <h2 class="tool-title">환율 계산기</h2>
        <p class="tool-note">
          실시간 환율입니다. 한 칸에 입력하면 나머지 통화가 자동으로 연동됩니다.
        </p>

        <div class="rate-rows">
          <label v-for="c in CURRENCIES" :key="c.code" class="rate-row">
            <input
              v-model.number="amounts[c.code]"
              type="number"
              min="0"
              step="any"
              inputmode="decimal"
              class="rate-row-input"
            />
            <span class="rate-row-name">{{ c.name }} ({{ c.code }})</span>
            <span class="rate-row-rate">{{ scaleLabel(c) }} ≈ {{ fmtRate(c) }}</span>
          </label>

          <label class="rate-row rate-row--base">
            <input v-model.number="krw" type="number" min="0" step="any" inputmode="decimal" class="rate-row-input" />
            <span class="rate-row-name">원 (KRW)</span>
            <span class="rate-row-rate">기준 통화</span>
          </label>
        </div>

        <p v-if="loading" class="tool-live">⏳ 실시간 환율을 불러오는 중…</p>
        <p v-else-if="liveTime" class="tool-live">🔄 {{ liveTime }} 기준 · 실시간 자동 갱신</p>
        <p v-else class="tool-live tool-live--warn">⚠️ 실시간 환율을 불러오지 못해 기본값을 표시합니다</p>
      </section>

      <!-- 关税估算器 -->
      <section class="tool-card">
        <h2 class="tool-title">직구 관세 간편 계산</h2>
        <p class="tool-note">간단한 추정용입니다. 정확한 세액은 관세청을 확인하세요.</p>
        <label class="tool-field">
          <span>상품 금액 (USD)</span>
          <input v-model.number="usd" type="number" min="0" step="1" placeholder="예: 80" />
        </label>
        <label class="tool-field">
          <span>배송 국가</span>
          <select v-model="origin">
            <option value="us">미국발</option>
            <option value="other">그 외 국가(중국 등)</option>
          </select>
        </label>
        <div class="tool-duty" :class="dutyStatus">
          <p v-if="isFree" class="duty-free">✅ 면세 범위 내입니다 ({{ limit }}$ 이하)</p>
          <p v-else class="duty-pay">⚠️ 면세 한도 초과 — 예상 관세 약 <strong>{{ duty }}원</strong></p>
        </div>
        <p class="tool-note">면세 한도: 미국발 200$ · 그 외 150$ (물품가 기준, 단순화)</p>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'

// ===== 汇率计算器 =====
// rate = 1 단위 통화의 원(KRW) 가치. scale = 표시용 단위(동은 1000).
const CURRENCIES = reactive([
  { code: 'CNY', name: '위안', scale: 1, decimals: 2, rate: 200 },
  { code: 'USD', name: '달러', scale: 1, decimals: 2, rate: 1337 },
  { code: 'JPY', name: '엔', scale: 1, decimals: 0, rate: 8.36 },
  { code: 'VND', name: '동', scale: 1000, decimals: 0, rate: 0.052 },
  { code: 'EUR', name: '유로', scale: 1, decimals: 2, rate: 1452 },
])

// 基准：韩元金额（单一数据源）。各币种字段由它派生，改任何一个都会反向更新它。
const krw = ref(20000)
const loading = ref(true)
const liveTime = ref('')

function roundTo(v, d) {
  const f = Math.pow(10, d)
  return Math.round(v * f) / f
}

function find(code) {
  return CURRENCIES.find((c) => c.code === code)
}

// 各币种的联动输入框（get/set computed，放进 reactive 让模板自动解包）
const amounts = reactive({})
for (const c of CURRENCIES) {
  amounts[c.code] = computed({
    get: () => {
      if (!c.rate) return 0
      return roundTo(krw.value / c.rate, c.decimals)
    },
    set: (v) => {
      const n = Number(v)
      if (!isFinite(n) || n < 0) return
      if (c.rate) krw.value = Math.round(n * c.rate)
    },
  })
}

function scaleLabel(c) {
  return c.scale === 1 ? '1' : c.scale.toLocaleString('ko-KR')
}

function fmtRate(c) {
  const scaled = c.rate * c.scale
  return scaled.toLocaleString('ko-KR', { maximumFractionDigits: 2 }) + '원'
}

// 拉取实时汇率（免费公开 API，打开页面即调用）
async function loadRates() {
  loading.value = true
  try {
    const res = await fetch('https://open.er-api.com/v6/latest/KRW', { cache: 'no-store' })
    if (!res.ok) throw new Error('HTTP ' + res.status)
    const data = await res.json()
    if (data.result !== 'success' || !data.rates) throw new Error('bad payload')
    // base = KRW，rates[X] = 1 KRW 能换多少 X；取倒数得 1 X = ? KRW
    for (const c of CURRENCIES) {
      if (data.rates[c.code]) c.rate = 1 / data.rates[c.code]
    }
    liveTime.value = (data.time_last_update_utc || '').slice(0, 10)
  } catch {
    liveTime.value = ''
  } finally {
    loading.value = false
  }
}

onMounted(loadRates)

// ===== 关税计算器 =====
const usd = ref(80)
const origin = ref('other')
const limit = computed(() => (origin.value === 'us' ? 200 : 150))
const isFree = computed(() => (usd.value || 0) <= limit.value)
const dutyStatus = computed(() => (isFree.value ? 'free' : 'pay'))
const duty = computed(() => {
  const over = (usd.value || 0) - limit.value
  if (over <= 0) return 0
  const overKrw = over * 1400
  return Math.round(overKrw * 0.2)
})

useSeoMeta({
  title: '실용 도구 — cn2kr',
  description: '중국 직구·여행에 필요한 환율 계산기와 관세 계산기.',
})
</script>
