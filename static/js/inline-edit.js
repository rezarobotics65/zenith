/*
 * Auto-save for the inline Status / Current value / total-hours controls on
 * the KPI & Timetable table (tracker/templates/tracker/kpi_timetable.html).
 *
 * Progressive enhancement: every control is linked to a real <form> via the
 * HTML `form="..."` attribute (so several table cells can share one form),
 * and each form's Save button (.inline-save-btn) works as a normal submit
 * with no JS at all. This script intercepts that same submission — on
 * 'change' for the visible controls, and on the form's own 'submit' event
 * as a safety net for the Enter key — sends it as JSON-accepting AJAX
 * instead, updates the row in place, and hides the now-redundant button.
 */
(function () {
  function post(url, formEl) {
    return fetch(url, {
      method: 'POST',
      body: new FormData(formEl),
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin',
    }).then(function (res) {
      return res.text().then(function (text) {
        var data = {};
        try { data = JSON.parse(text); } catch (err) { /* non-JSON response */ }
        return { ok: res.ok, data: data };
      });
    });
  }

  function flash(row, failed) {
    if (!row) return;
    row.classList.remove('just-saved', 'just-error');
    // Force reflow so the animation restarts on repeated saves.
    void row.offsetWidth;
    row.classList.add(failed ? 'just-error' : 'just-saved');
    window.setTimeout(function () {
      row.classList.remove('just-saved', 'just-error');
    }, 1000);
  }

  function updateProgressCell(row, pct) {
    if (!row || pct === undefined || pct === null) return;
    var fill = row.querySelector('.progress-bar__fill');
    var label = row.querySelector('.progress-row__value');
    if (fill) fill.style.width = pct + '%';
    if (label) label.textContent = pct + '%';
  }

  function setupQuickForm(form, onSaved) {
    var row = form.closest('tr');
    var saving = false;

    function save() {
      if (saving) return;
      saving = true;
      post(form.getAttribute('action'), form).then(function (result) {
        saving = false;
        if (!result.ok) {
          flash(row, true);
          return;
        }
        onSaved(row, result.data || {}, form);
        flash(row, false);
      });
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      save();
    });

    var controls = document.querySelectorAll('[form="' + form.id + '"]');
    controls.forEach(function (control) {
      if (control.tagName === 'BUTTON') return;
      control.addEventListener('change', save);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form[id^="kpi-form-"], form[id^="course-form-"]').forEach(function (form) {
      setupQuickForm(form, function (row, data) {
        updateProgressCell(row, data.progress_pct);
      });
    });

    document.querySelectorAll('form[id^="course-hours-form-"]').forEach(function (form) {
      setupQuickForm(form, function (row, data, savedForm) {
        var hoursDisplay = row.querySelector('.hours-display');
        if (hoursDisplay && data.hours_logged !== undefined) {
          hoursDisplay.textContent = data.hours_logged + '/' + data.planned_hours;
        }
        // The field represents the current total, not a delta to add — sync
        // it to the authoritative server value (e.g. after Decimal rounding).
        var hoursInput = document.querySelector('input[form="' + savedForm.id + '"]');
        if (hoursInput && data.hours_logged !== undefined) {
          hoursInput.value = data.hours_logged;
        }
        updateProgressCell(row, data.progress_pct);
      });
    });
  });
})();
