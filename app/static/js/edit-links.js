(function () {
  'use strict';

  const STORAGE_KEY = 'saved_edit_urls';
  const MAX_SAVED = 20;
  const P = () => window.Poisker || {};

  function readSavedPosts() {
    const raw = P().parseJsonSafe?.(P().storageGet?.(STORAGE_KEY), []);
    return Array.isArray(raw) ? raw : [];
  }

  function writeSavedPosts(list) {
    if (!Array.isArray(list)) return;
    P().storageSet?.(STORAGE_KEY, JSON.stringify(list.slice(0, MAX_SAVED)));
  }

  function sanitizeEntry(entry) {
    if (!entry || typeof entry !== 'object') return null;
    const url = typeof entry.url === 'string' ? entry.url : '';
    if (!P().isAllowedEditUrl?.(url)) return null;
    const postId = P().isPostId?.(String(entry.postId || '')) ? entry.postId : '';
    const viewUrl = entry.viewUrl && P().isSameOriginUrl?.(entry.viewUrl) ? entry.viewUrl : '';
    const title = String(entry.title || 'Объявление').slice(0, 80);
    const savedAt = typeof entry.savedAt === 'string' ? entry.savedAt : new Date().toISOString();
    return { url, viewUrl, postId, title, savedAt };
  }

  function viewUrlForPostId(postId) {
    const item = findSavedPost(postId);
    return item?.viewUrl || '';
  }

  function viewUrlForPost(item) {
    if (!item) return '';
    let token = '';
    if (item.url) {
      try {
        token = new URL(item.url, window.location.origin).searchParams.get('token') || '';
      } catch (_e) {
        return '';
      }
    }
    if (item.viewUrl && P().isSameOriginUrl?.(item.viewUrl)) {
      if (token && !item.viewUrl.includes('token=')) {
        const joiner = item.viewUrl.includes('?') ? '&' : '?';
        return `${item.viewUrl}${joiner}token=${encodeURIComponent(token)}`;
      }
      return item.viewUrl;
    }
    if (item.postId && P().isPostId?.(item.postId)) {
      const base = `${window.location.origin}/posts/${encodeURIComponent(item.postId)}`;
      return token ? `${base}?token=${encodeURIComponent(token)}` : base;
    }
    return '';
  }

  function findSavedPost(postId) {
    if (!postId) return null;
    return readSavedPosts().find((item) => item.postId === postId) || null;
  }

  function editUrlForPostId(postId) {
    const item = findSavedPost(postId);
    return item?.url || '';
  }

  function saveEditUrl(url, meta = {}) {
    if (!P().isAllowedEditUrl?.(url)) return null;
    const viewUrl = meta.viewUrl && P().isSameOriginUrl?.(meta.viewUrl) ? meta.viewUrl : viewUrlForPostId(meta.postId);
    const entry = sanitizeEntry({
      url,
      viewUrl,
      postId: meta.postId || '',
      title: meta.title || 'Объявление',
      savedAt: meta.savedAt || new Date().toISOString(),
    });
    if (!entry) return null;
    const list = readSavedPosts().filter((item) => item.url !== url);
    list.unshift(entry);
    writeSavedPosts(list);
    P().storageSet?.('last_edit_url', url);
    return entry;
  }

  function removeSavedPost(url) {
    if (!url) return;
    writeSavedPosts(readSavedPosts().filter((item) => item.url !== url));
  }

  function removeSavedPostById(postId, url) {
    writeSavedPosts(
      readSavedPosts().filter((item) => {
        if (postId && item.postId === postId) return false;
        if (url && item.url === url) return false;
        return true;
      })
    );
  }

  async function copyText(text, hintEl, btn) {
    const value = typeof text === 'string' ? text : '';
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
    } catch (_e) {
      const tmp = document.createElement('textarea');
      tmp.value = value;
      tmp.setAttribute('readonly', '');
      tmp.style.position = 'fixed';
      tmp.style.left = '-9999px';
      document.body.appendChild(tmp);
      tmp.select();
      document.execCommand('copy');
      tmp.remove();
    }
    if (hintEl) {
      hintEl.hidden = false;
      hintEl.textContent = 'Ссылка скопирована';
      hintEl.classList.add('is-success');
    }
    if (btn) {
      btn.classList.add('is-copied');
      const label = btn.querySelector('span');
      if (label) label.textContent = 'Скопировано';
    }
  }

  window.saveEditUrl = saveEditUrl;
  window.readSavedPosts = readSavedPosts;
  window.removeSavedPost = removeSavedPost;
  window.removeSavedPostById = removeSavedPostById;
  window.viewUrlForPost = viewUrlForPost;
  window.findSavedPost = findSavedPost;
  window.editUrlForPostId = editUrlForPostId;
  window.copyText = copyText;
})();
