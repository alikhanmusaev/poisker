function formatDate(iso) {
  try {
    return new Intl.DateTimeFormat('ru-RU', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(iso));
  } catch (e) {
    return '';
  }
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

async function fetchPostStatus(item) {
  if (!item?.postId) return null;
  try {
    let url = `/posts/${item.postId}/meta`;
    if (item.url) {
      const token = new URL(item.url, window.location.origin).searchParams.get('token');
      if (token) url += `?token=${encodeURIComponent(token)}`;
    }
    const res = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!res.ok) return { active: false };
    const data = await res.json();
    return {
      active: Boolean(data.ok),
      expired: Boolean(data.expired),
      status: data.status || 'published',
    };
  } catch (e) {
    return null;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const listEl = document.getElementById('my-posts-list');
  const emptyEl = document.getElementById('my-posts-empty');
  if (!listEl || typeof readSavedPosts !== 'function') return;

  async function render() {
    const items = readSavedPosts();
    listEl.innerHTML = '';

    if (!items.length) {
      emptyEl.hidden = false;
      listEl.hidden = true;
      return;
    }

    emptyEl.hidden = true;
    listEl.hidden = false;

    const statuses = await Promise.all(items.map((item) => fetchPostStatus(item)));

    items.forEach((item, index) => {
      const viewUrl = typeof viewUrlForPost === 'function' ? viewUrlForPost(item) : '';
      const status = statuses[index];
      const li = el('li', 'my-post-card');
      const body = el('div', 'my-post-card-body');

      const titleRow = el('div', 'my-post-card-title-row');
      const titleRowInner = el('h2', 'my-post-card-title');
      if (viewUrl) {
        const titleLink = el('a', 'my-post-card-title-link', item.title || 'Объявление');
        titleLink.href = viewUrl;
        titleRowInner.appendChild(titleLink);
      } else {
        titleRowInner.textContent = item.title || 'Объявление';
      }
      titleRow.appendChild(titleRowInner);

      const badge = el('span', 'my-post-status');
      if (status === null) {
        badge.className += ' my-post-status-muted';
        badge.textContent = '…';
      } else if (!status.active) {
        badge.className += ' my-post-status-ended';
        badge.textContent = 'Не найдено';
      } else if (status.status === 'hidden') {
        badge.className += ' my-post-status-ended';
        badge.textContent = 'Скрыто';
      } else if (status.status === 'pending') {
        badge.className += ' my-post-status-active';
        badge.textContent = 'На проверке';
      } else if (status.expired || status.status === 'expired') {
        badge.className += ' my-post-status-ended';
        badge.textContent = 'Истекло';
      } else {
        badge.className += ' my-post-status-active';
        badge.textContent = 'Активно';
      }
      titleRow.appendChild(badge);
      body.appendChild(titleRow);

      body.appendChild(el('p', 'my-post-card-date', formatDate(item.savedAt)));

      const linkBlock = el('div', 'my-post-card-link-block');
      linkBlock.appendChild(
        el('p', 'my-post-card-link-label', 'Ссылка на объявление')
      );
      const urlEl = el('code', 'my-post-card-url', item.url);
      urlEl.setAttribute('translate', 'no');
      linkBlock.appendChild(urlEl);
      linkBlock.appendChild(
        el(
          'p',
          'my-post-card-link-hint',
          'Сохраните эту ссылку, чтобы открыть или изменить объявление позже.'
        )
      );
      body.appendChild(linkBlock);

      const actions = el('div', 'my-post-card-actions');

      if (viewUrl) {
        const viewLink = el('a', 'btn btn-secondary btn-sm', 'Смотреть');
        viewLink.href = viewUrl;
        actions.appendChild(viewLink);
      }

      const copyBtn = el('button', 'btn btn-primary btn-sm', 'Копировать ссылку');
      copyBtn.type = 'button';
      copyBtn.dataset.copy = item.url;

      const editLink = el('a', 'btn btn-secondary btn-sm', 'Редактировать');
      editLink.href = item.url;
      editLink.addEventListener('click', async (event) => {
        const ok = await confirmDialog({
          title: 'Редактировать?',
          message: 'Откроется страница изменения объявления.',
          confirmLabel: 'Открыть',
        });
        if (!ok) event.preventDefault();
      });

      const removeBtn = el('button', 'btn btn-secondary btn-sm my-post-remove', 'Убрать из списка');
      removeBtn.type = 'button';
      removeBtn.dataset.url = item.url;

      actions.append(copyBtn, editLink, removeBtn);
      li.append(body, actions);
      listEl.appendChild(li);
    });

    listEl.querySelectorAll('[data-copy]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        await copyText(btn.dataset.copy);
        btn.textContent = 'Скопировано';
      });
    });

    listEl.querySelectorAll('.my-post-remove').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const ok = await confirmDialog({
          title: 'Убрать из списка?',
          message: 'Объявление на сайте останется. Ссылку можно сохранить отдельно.',
          confirmLabel: 'Убрать из списка',
          danger: true,
        });
        if (!ok) return;
        if (typeof removeSavedPost === 'function') removeSavedPost(btn.dataset.url);
        render();
      });
    });

    if (window.refreshIcons) refreshIcons();
  }

  render();
});
