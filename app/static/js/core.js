/**
 * Poisker client core — shared security and DOM utilities.
 * Load before other app scripts.
 */
(function (global) {
  'use strict';

  const SLUG_RE = /^[a-z0-9-]+$/i;
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function escapeAttr(value) {
    return escapeHtml(value);
  }

  function digitsOnly(value) {
    return String(value || '').replace(/\D/g, '');
  }

  function parseJsonSafe(raw, fallback = null) {
    if (raw == null || raw === '') return fallback;
    try {
      return JSON.parse(raw);
    } catch (_e) {
      return fallback;
    }
  }

  function readJsonScript(id, fallback = null) {
    const node = document.getElementById(id);
    if (!node) return fallback;
    return parseJsonSafe(node.textContent, fallback);
  }

  function csrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || '';
  }

  function isTrustedUserEvent(event) {
    return !event || event.isTrusted;
  }

  function isSameOriginUrl(url) {
    if (!url || typeof url !== 'string') return false;
    try {
      return new URL(url, global.location.origin).origin === global.location.origin;
    } catch (_e) {
      return false;
    }
  }

  function isAllowedEditUrl(url) {
    if (!isSameOriginUrl(url)) return false;
    try {
      const { pathname } = new URL(url, global.location.origin);
      const parts = pathname.split('/').filter(Boolean);
      return parts.length === 3 && parts[0] === 'posts' && parts[2] === 'edit' && isPostId(parts[1]);
    } catch (_e) {
      return false;
    }
  }

  function isPostId(value) {
    return typeof value === 'string' && (UUID_RE.test(value) || /^[a-zA-Z0-9_-]{8,64}$/.test(value));
  }

  function isSafeSlug(value) {
    return typeof value === 'string' && SLUG_RE.test(value);
  }

  function isSafeImageSrc(src) {
    if (!src || typeof src !== 'string') return false;
    if (src.startsWith('blob:')) return true;
    try {
      const parsed = new URL(src, global.location.origin);
      return parsed.protocol === 'https:' || parsed.protocol === 'http:';
    } catch (_e) {
      return false;
    }
  }

  function safeHref(url) {
    return isSameOriginUrl(url) ? url : '';
  }

  function storageGet(key) {
    try {
      return global.localStorage.getItem(key);
    } catch (_e) {
      return null;
    }
  }

  function storageSet(key, value) {
    try {
      global.localStorage.setItem(key, value);
      return true;
    } catch (_e) {
      return false;
    }
  }

  function storageRemove(key) {
    try {
      global.localStorage.removeItem(key);
    } catch (_e) {
      /* ignore */
    }
  }

  async function parseJsonResponse(response) {
    const type = response.headers.get('content-type') || '';
    if (!type.includes('application/json')) return null;
    try {
      return await response.json();
    } catch (_e) {
      return null;
    }
  }

  function cssEscape(value) {
    if (global.CSS && typeof global.CSS.escape === 'function') {
      return global.CSS.escape(String(value));
    }
    return String(value).replace(/["\\]/g, '\\$&');
  }

  const Poisker = {
    escapeHtml,
    escapeAttr,
    digitsOnly,
    parseJsonSafe,
    readJsonScript,
    csrfToken,
    isTrustedUserEvent,
    isSameOriginUrl,
    isAllowedEditUrl,
    isPostId,
    isSafeSlug,
    isSafeImageSrc,
    safeHref,
    storageGet,
    storageSet,
    storageRemove,
    parseJsonResponse,
    cssEscape,
  };

  global.Poisker = Poisker;
})(window);
