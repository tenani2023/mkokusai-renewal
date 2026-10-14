import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// お知らせ・イベント記事（CMSから投稿される記事）
const news = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/news' }),
  schema: () =>
    z.object({
      title: z.string(),
      date: z.coerce.date(),
      category: z.enum(['お知らせ', '参加者募集', '開催報告', '姉妹都市']).default('お知らせ'),
      thumbnail: z.string().optional(), // 例: /uploads/photo.webp（CMS がアップロード）
      link: z.string().optional(),
      draft: z.boolean().default(false),
    }),
});

export const collections = { news };
