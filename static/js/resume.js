document.addEventListener('DOMContentLoaded', () => {
  // Close the mobile nav after tapping a link
  const nav = document.getElementById('navbarSupportedContent');
  if (nav) {
    const collapse = bootstrap.Collapse.getOrCreateInstance(nav, { toggle: false });
    document.querySelectorAll('#sideNav .nav-link, .js-scroll-trigger').forEach((a) =>
      a.addEventListener('click', () => {
        if (nav.classList.contains('show')) collapse.hide();
      }));
  }
  // Tooltips
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((el) => new bootstrap.Tooltip(el));
  // Repair scrape-poisoned mailto links: the served HTML carries a "-remove-"
  // marker inside the address so harvesters pick up a dead one. Strip it here so
  // the link works for real visitors. Runs on the href only — the visible text
  // already reads correctly, since the marker is in a display:none span.
  document.querySelectorAll('a.protected-mail').forEach((a) => {
    a.href = a.getAttribute('href').split('-remove-').join('');
  });
  // Sidebar scrollspy
  if (document.querySelector('#sideNav')) {
    new bootstrap.ScrollSpy(document.body, { target: '#sideNav' });
  }

  // Light/dark theme toggle. The initial theme is applied in <head> to avoid a flash.
  const toggle = document.getElementById('themeToggle');
  if (toggle) {
    const label = document.getElementById('themeToggleLabel');
    const sync = () => {
      const dark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
      if (label) label.textContent = dark ? 'Light mode' : 'Dark mode';
      toggle.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
    };
    sync();
    toggle.addEventListener('click', () => {
      const next = document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-bs-theme', next);
      try { localStorage.setItem('theme', next); } catch (e) { /* storage unavailable */ }
      sync();
    });
  }

  // Record image lightbox: fill the shared modal from the clicked thumbnail
  const modalEl = document.getElementById('recordImageModal');
  const thumbs = document.querySelectorAll('.record-image');
  if (modalEl && thumbs.length) {
    const modal = new bootstrap.Modal(modalEl);
    const img = document.getElementById('recordImageModalImg');
    const title = document.getElementById('recordImageModalLabel');
    const caption = document.getElementById('recordImageModalCaption');
    const link = document.getElementById('recordImageModalLink');

    const open = (thumb) => {
      const data = thumb.dataset;
      img.src = data.recordImage;
      img.alt = data.recordCaption || data.recordTitle || '';
      title.textContent = data.recordTitle || '';
      caption.textContent = data.recordCaption || '';
      if (data.recordUrl) {
        link.href = data.recordUrl;
        link.classList.remove('d-none');
      } else {
        link.classList.add('d-none');
      }
      modal.show();
    };

    thumbs.forEach((thumb) => {
      thumb.addEventListener('click', () => open(thumb));
      thumb.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          open(thumb);
        }
      });
    });
  }
});
