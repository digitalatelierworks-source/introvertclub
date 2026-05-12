const navToggle = document.querySelector('.nav-toggle');
const siteNav = document.querySelector('.site-nav');

navToggle?.addEventListener('click', () => {
  siteNav?.classList.toggle('open');
});

const instagramPosts = [
  {
    title: 'オフ会の入口で',
    handle: '@introvertclub_jp',
    caption: '最初の一言がむずかしい日に。背中の言葉が、会話のきっかけになります。'
  },
  {
    title: 'バーでひとり飲み',
    handle: '@introvertclub_jp',
    caption: '話しかけてもらえたら嬉しい。そんな気持ちを、さりげなく伝える一枚。'
  },
  {
    title: 'サークルの飲み会',
    handle: '@introvertclub_jp',
    caption: '輪に入るタイミングが迷子でも、服が少しだけ助けてくれる。'
  },
  {
    title: 'ライブ一人参戦',
    handle: '@introvertclub_jp',
    caption: '同じ好きを持つ人と、少しだけ話すきっかけに。'
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
