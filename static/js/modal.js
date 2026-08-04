/*
 * Progressive-enhancement modal for the tracker's Add/Edit/Delete CRUD pages
 * (tracker/templates/tracker/form.html, confirm_delete.html).
 *
 * Every Add/Edit/Delete link still has a normal href — without this script,
 * or if fetch() fails, they navigate to a full page exactly as before. With
 * it, clicks are intercepted, the target page is fetched, its form is lifted
 * into an overlay on top of the current page, and the page behind is
 * blurred for as long as the overlay is open. Saving still does a full
 * navigation to the redirect target (simplest way to guarantee every table,
 * chart and total on the page is correct afterwards) — only *opening* the
 * form avoids a page load.
 */
(function () {
  var CRUD_PATTERN = /^\/tracker\/(add|edit|delete)\//;

  var overlay = null;
  var dialog = null;
  var content = null;
  var lastFocused = null;

  function buildOverlay() {
    overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.hidden = true;
    overlay.innerHTML =
      '<div class="modal-dialog" role="dialog" aria-modal="true">' +
      '<button type="button" class="modal-close" aria-label="Close">&times;</button>' +
      '<div class="modal-content"></div>' +
      '</div>';
    document.body.appendChild(overlay);
    dialog = overlay.querySelector('.modal-dialog');
    content = overlay.querySelector('.modal-content');

    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) closeModal();
    });
    overlay.querySelector('.modal-close').addEventListener('click', closeModal);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && overlay && !overlay.hidden) closeModal();
    });
  }

  function extractFragment(htmlText) {
    // .modal-target wraps the heading + card in form.html / confirm_delete.html,
    // deliberately excluding the page's {% if messages %} block so a stale
    // message from an earlier action never bleeds into a fresh modal.
    var doc = new DOMParser().parseFromString(htmlText, 'text/html');
    var target = doc.querySelector('.modal-target');
    if (target) return target.innerHTML;
    var main = doc.querySelector('main');
    return main ? main.innerHTML : htmlText;
  }

  function openModal(html, triggerEl) {
    if (!overlay) buildOverlay();
    lastFocused = triggerEl || document.activeElement;
    content.innerHTML = html;
    overlay.hidden = false;
    document.body.classList.add('modal-open');
    wireContent();
    var firstField = content.querySelector('input:not([type=hidden]), select, textarea, button');
    if (firstField) firstField.focus();
  }

  function closeModal() {
    if (!overlay || overlay.hidden) return;
    overlay.hidden = true;
    document.body.classList.remove('modal-open');
    content.innerHTML = '';
    if (lastFocused && typeof lastFocused.focus === 'function') lastFocused.focus();
  }

  function wireContent() {
    var cancelLink = content.querySelector('.modal-cancel');
    if (cancelLink) {
      cancelLink.addEventListener('click', function (e) {
        e.preventDefault();
        closeModal();
      });
    }

    var form = content.querySelector('form');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var submitBtn = form.querySelector('button[type=submit]');
      if (submitBtn) submitBtn.disabled = true;

      fetch(form.getAttribute('action') || window.location.href, {
        method: 'POST',
        body: new FormData(form),
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin',
      })
        .then(function (res) {
          if (res.redirected) {
            window.location = res.url;
            return null;
          }
          return res.text();
        })
        .then(function (html) {
          if (html === null) return;
          // Re-render (validation errors) — keep the modal open.
          openModal(extractFragment(html), lastFocused);
        })
        .catch(function () {
          // Network/fetch failure — fall back to a plain synchronous submit.
          // HTMLFormElement.prototype.submit() does not fire a 'submit'
          // event, so this can't re-trigger this same handler.
          if (submitBtn) submitBtn.disabled = false;
          HTMLFormElement.prototype.submit.call(form);
        });
    });
  }

  function loadIntoModal(url, triggerEl) {
    fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' }, credentials: 'same-origin' })
      .then(function (res) {
        if (!res.ok) throw new Error('bad response');
        return res.text();
      })
      .then(function (html) {
        openModal(extractFragment(html), triggerEl);
      })
      .catch(function () {
        window.location = url;
      });
  }

  document.addEventListener('click', function (e) {
    var link = e.target.closest('a[href]');
    if (!link) return;
    var url;
    try {
      url = new URL(link.href, window.location.origin);
    } catch (err) {
      return;
    }
    if (url.origin !== window.location.origin) return;
    if (!CRUD_PATTERN.test(url.pathname)) return;

    e.preventDefault();
    loadIntoModal(link.href, link);
  });
})();
