import { defineConfig } from 'astro/config';

// 守山市国際交流協会 リニューアルサイト
// プレビュー環境（GitHub Pages）ではサブディレクトリ配信のため base を切り替える
const base = process.env.PUBLIC_BASE_PATH || '/';
const siteUrl = process.env.PUBLIC_SITE_URL || 'https://mkokusai.org';

export default defineConfig({
  site: siteUrl,
  base,
  output: 'static',
  trailingSlash: 'always',
  build: {
    format: 'directory',
    inlineStylesheets: 'auto',
  },
  compressHTML: true,
});
