# 守山市国際交流協会 ホームページリニューアル

既存サイト <http://mkokusai.org/> のリニューアル制作リポジトリです。

## 構成

| 項目 | 内容 |
| --- | --- |
| フレームワーク | [Astro](https://astro.build/)（静的サイト生成） |
| ホスティング（予定） | Cloudflare Pages（無料枠） |
| CMS（予定） | Decap CMS または Sveltia CMS（GitHub 連携） |
| ソース管理 | GitHub（協会名義アカウント） |

## 開発

```bash
npm install
npm run dev      # http://localhost:4321/
npm run build    # dist/ に静的ファイルを出力
npm run preview
```

## ディレクトリ

```
src/
  assets/            画像（ビルド時に最適化・WebP/AVIF 化）
  components/        Header / Footer
  content/news/      お知らせ記事（Markdown。CMS が書き込む場所）
  data/site.ts       協会名・住所・電話・ナビゲーション
  data/topics.json   トップページ「お知らせ（TOPICS）」
  layouts/Base.astro 共通レイアウト
  pages/             各ページ
  styles/global.css  デザイントークン・共通スタイル
public/
  _redirects         旧URL → 新URL の 301 リダイレクト
  files/             既存サイトから引き継いだ PDF
docs/                調査結果・対応表・要確認事項
tools/               制作用スクリプト（スクリーンショット等）
```

## 制作ステップ

1. 既存サイト調査 → `docs/01_調査結果.md`
2. デザイン設計 → `src/styles/global.css`
3. トップページ制作 → `src/pages/index.astro` ✅
4. 下層ページ制作（次工程）
5. CMS 構築（次工程）
6. 品質確認
