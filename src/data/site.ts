// 既存サイト（mkokusai.org）に掲載されている基本情報。変更しないこと。
export const site = {
  name: '守山市国際交流協会',
  nameEn: 'Moriyama International Friendship Association',
  abbr: 'MIFA',
  tagline:
    '守山市国際交流協会は、国際的で活気あるまちづくり・ひとづくりを目指し、姉妹都市や在住外国人との交流の普及に努めています。',
  postal: '〒524-0022',
  address: '滋賀県守山市守山2丁目16-45 守山市民交流センター内',
  tel: '077-583-4653',
  fax: '077-583-4653',
  hours: '平日 9:00～16:30',
  email: 'info@mkokusai.org',
  copyright: 'Moriyama International Friendship Association all rights reserved.',
  sns: {
    facebook: 'https://www.facebook.com/mkokusai1',
    facebookOld: 'http://www.facebook.com/mkokusai',
    instagram: 'https://www.instagram.com/mkokusai1',
    nihongoSalon:
      'https://m.facebook.com/people/%E3%81%AB%E3%81%BB%E3%82%93%E3%81%94%E3%82%B5%E3%83%AD%E3%83%B3-in-Moriyama/100090777482102/',
  },
};

// グローバルナビゲーション（既存サイトのナビゲーション構成を維持）
export const nav = [
  { label: 'トップページ', href: '/' },
  { label: '概要', href: '/concept/' },
  { label: 'イベント・ニュース', href: '/eventnews/' },
  { label: 'にほんごきょうしつ', href: '/japanese/' },
  { label: '通訳について', href: '/interpreter/' },
  { label: '姉妹都市', href: '/sistercity/' },
  { label: 'スピーチコンテスト', href: '/speech/' },
  { label: '会員・ボランティア募集', href: '/wanted/' },
  { label: 'お問い合わせ', href: '/contact/' },
];

// 既存サイトの「バナースペース」にあったリンク
export const subNav = [
  { label: '国際交流の広場', href: '/festival/' },
  { label: 'リンク集', href: '/link/' },
  { label: '新着情報一覧', href: '/news/' },
];
