import { defineContentConfig, defineCollection } from '@nuxt/content'
import { z } from 'zod'

export default defineContentConfig({
  collections: {
    articles: defineCollection({
      type: 'page',
      source: 'articles/**/*.md',
      schema: z.object({
        excerpt: z.string().optional(),
      }).passthrough(),
    }),
  },
})
