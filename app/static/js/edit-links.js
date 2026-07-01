const STORAGE_KEY = 'saved_edit_urls';

function readSavedPosts() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const list = raw ? JSON.parse(raw) : [];
    return Array.isArray(list) ? list : [];
  } catch (e) {
    return [];
  }
}

function writeSavedPosts(list) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  } catch (e) {}
}

function viewUrlForPostId(postId) {
  const item = findSavedPost(postId);
  return item?.viewUrl || '';
}

function viewUrlForPost(item) {
  if (!item) return '';
  if (item.viewUrl) return item.viewUrl;
  const fromId = viewUrlForPostId(item.postId);
  if (fromId) return fromId;
  if (!item.url) return '';
  try {
    const parsed = new URL(item.url, window.location.origin);
    const match = parsed.pathname.match(/^\/posts\/([^/]+)\/edit\/?$/);
    if (match) {
      return `${parsed.origin}/posts/${match[1]}`;
    }
  } catch (e) {}
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
  if (!url) return;
  const viewUrl = meta.viewUrl || viewUrlForPostId(meta.postId);
  const entry = {
    url,
    viewUrl,
    postId: meta.postId || '',
    title: meta.title || 'Объявление',
    savedAt: meta.savedAt || new Date().toISOString(),
  };
  const list = readSavedPosts().filter((item) => item.url !== url);
  list.unshift(entry);
  writeSavedPosts(list.slice(0, 20));
  try {
    localStorage.setItem('last_edit_url', url);
  } catch (e) {}
  return entry;
}

function removeSavedPost(url) {
  writeSavedPosts(readSavedPosts().filter((item) => item.url !== url));
}

window.saveEditUrl = saveEditUrl;
window.readSavedPosts = readSavedPosts;
window.removeSavedPost = removeSavedPost;
window.viewUrlForPost = viewUrlForPost;
window.findSavedPost = findSavedPost;
window.editUrlForPostId = editUrlForPostId;

async function copyText(text, hintEl, btn) {
  try {
    await navigator.clipboard.writeText(text);
  } catch (e) {
    const tmp = document.createElement('textarea');
    tmp.value = text;
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

window.copyText = copyText;
