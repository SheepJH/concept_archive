/**
 * Card page number auto-injection.
 *
 * Each template has:
 *   <body data-page="02" data-total="06">  ← fallback defaults
 *   <span class="page-display"></span>      ← injection target
 *
 * URL params override defaults:
 *   card.html?p=3&t=7   →  "03 / 07"
 *
 * Embedded in iframes? window.name can also set values:
 *   iframe.name = "p:3,t:7"
 */
(function () {
  function pad(n) {
    n = String(parseInt(n, 10));
    return n.length < 2 ? '0' + n : n;
  }

  function readParams() {
    const out = {};
    // 1. URL query string
    const qs = new URLSearchParams(location.search);
    if (qs.get('p')) out.p = qs.get('p');
    if (qs.get('t')) out.t = qs.get('t');
    // 2. iframe name fallback (e.g. "p:3,t:7")
    if (window.name && /p:\d+/.test(window.name)) {
      window.name.split(',').forEach(function (kv) {
        const [k, v] = kv.split(':');
        if (k && v) out[k.trim()] = v.trim();
      });
    }
    return out;
  }

  function apply() {
    const body = document.body;
    const params = readParams();
    const page = params.p || body.dataset.page || '01';
    const total = params.t || body.dataset.total || '06';

    body.dataset.page = pad(page);
    body.dataset.total = pad(total);

    document.querySelectorAll('.page-display').forEach(function (el) {
      el.textContent = pad(page) + ' / ' + pad(total);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', apply);
  } else {
    apply();
  }
})();
