document.addEventListener('DOMContentLoaded', async () => {
  const root = document.querySelector('[data-post-detail]');
  if (!root) return;

  const postId = root.dataset.postId || '';
  const contactUrl = root.dataset.contactUrl || '';
  const metaUrl = root.dataset.metaUrl || '';
  const editLink = document.getElementById('owner-edit-link');
  const showPhone = document.getElementById('show-phone');
  const phoneDisplay = document.getElementById('phone-display');
  const phoneText = document.getElementById('phone-text');
  const sharePost = document.getElementById('share-post');

  if (editLink && typeof findSavedPost === 'function') {
    const saved = findSavedPost(postId);
    if (saved?.url && metaUrl) {
      try {
        const token = new URL(saved.url, window.location.origin).searchParams.get('token');
        if (token) {
          const res = await fetch(`${metaUrl}?token=${encodeURIComponent(token)}`, {
            headers: { Accept: 'application/json' },
          });
          const data = await res.json();
          if (data.ok && data.can_edit) {
            editLink.href = saved.url;
            editLink.hidden = false;
          }
        }
      } catch (e) {}
    }
  }

  showPhone?.addEventListener('click', async function () {
    if (!contactUrl) return;
    const res = await fetch(contactUrl, { headers: { Accept: 'application/json' } });
    const data = await res.json();
    if (phoneText) phoneText.textContent = data.phone_masked;
    phoneDisplay?.classList.remove('hidden');
    this.hidden = true;
    if (window.refreshIcons) refreshIcons();
  });

  sharePost?.addEventListener('click', async () => {
    const shareData = { title: document.title, url: window.location.href };
    if (navigator.share) {
      try {
        await navigator.share(shareData);
        return;
      } catch (e) {
        if (e.name === 'AbortError') return;
      }
    }
    await copyText(window.location.href);
  });

  if (window.refreshIcons) refreshIcons();
});
