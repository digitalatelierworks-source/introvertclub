const navToggle = document.querySelector('.nav-toggle');
const siteNav = document.querySelector('.site-nav');

navToggle?.addEventListener('click', () => {
  siteNav?.classList.toggle('open');
});

const instagramPosts = [
  {
    title: '週末のカフェスタイル',
    handle: '@introvertclub_jp',
    caption: '落ち着いた色合いで、話しかけやすい背面メッセージ。'
  },
  {
    title: 'ライブ前のリラックス',
    handle: '@ic_official',
    caption: 'ボルドーアクセントのフーディーで自然体に。'
  },
  {
    title: 'オフ会のコーディネート',
    handle: '@shy_street',
    caption: '静かに目を引く、言葉のチョイスがポイント。'
  },
  {
    title: '夕方の散歩',
    handle: '@quiet_mood',
    caption: 'シンプルなキャップがアクセントに。'
  },
];

function renderInstagramGrid() {
  const grid = document.querySelector('.instagram-grid');
  if (!grid) return;

  instagramPosts.forEach((post) => {
    const item = document.createElement('article');
    item.className = 'instagram-post';
    item.innerHTML = `
      <div>
        <p class="instagram-post-title">${post.title}</p>
        <p class="instagram-post-handle">${post.handle}</p>
      </div>
      <p>${post.caption}</p>
    `;
    grid.appendChild(item);
  });
}

function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener('click', (event) => {
      const targetId = link.getAttribute('href');
      if (!targetId || targetId === '#') return;
      const target = document.querySelector(targetId);
      if (!target) return;
      event.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      siteNav?.classList.remove('open');
    });
  });
}

renderInstagramGrid();
initSmoothScroll();
