// Theme toggle (remembers your choice)
document.getElementById('theme-toggle').addEventListener('click', function () {
  var root = document.documentElement;
  var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  root.setAttribute('data-theme', next);
  try { localStorage.setItem('theme', next); } catch (e) {}
});

// Ask before destructive actions
document.querySelectorAll('form[data-confirm]').forEach(function (f) {
  f.addEventListener('submit', function (e) {
    if (!confirm(f.getAttribute('data-confirm'))) e.preventDefault();
  });
});

// Flash messages fade out
document.querySelectorAll('.flash').forEach(function (el) {
  setTimeout(function () {
    el.style.transition = 'opacity .5s'; el.style.opacity = '0';
    setTimeout(function () { el.remove(); }, 500);
  }, 5000);
});

// Editor: tabs, live preview, word count
(function () {
  var form = document.getElementById('editor-form');
  if (!form) return;
  var area = document.getElementById('content');
  var pane = document.getElementById('preview-pane');
  var count = document.getElementById('word-count');
  var tabs = form.querySelectorAll('.tab');

  function updateCount() {
    var words = area.value.trim() ? area.value.trim().split(/\s+/).length : 0;
    count.textContent = words + ' word' + (words === 1 ? '' : 's');
  }
  area.addEventListener('input', updateCount);
  updateCount();

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      tabs.forEach(function (t) { t.classList.toggle('active', t === tab); });
      if (tab.dataset.tab === 'preview') {
        pane.hidden = false; area.hidden = true;
        pane.innerHTML = '<p class="muted">Rendering preview...</p>';
        var data = new FormData();
        data.append('_csrf', form.querySelector('[name=_csrf]').value);
        data.append('content', area.value);
        fetch(form.dataset.previewUrl, { method: 'POST', body: data })
          .then(function (r) { return r.json(); })
          .then(function (j) { pane.innerHTML = j.html || '<p class="muted">Nothing to preview yet.</p>'; })
          .catch(function () { pane.innerHTML = '<p class="muted">Preview unavailable.</p>'; });
      } else {
        pane.hidden = true; area.hidden = false; area.focus();
      }
    });
  });
})();
