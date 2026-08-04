/*
 * Renders the three Chart.js charts described in BUILD_BRIEF.md Section 9.
 * Data always arrives via {{ data|json_script:"id" }} and is read here with
 * JSON.parse — never build JS objects inside Django template tags.
 * Every chart has a plain-table fallback that stays visible unless this file
 * successfully loads and Chart is available (see the .js/.no-js toggle below).
 */
(function () {
  document.documentElement.classList.replace('no-js', 'js');

  function collapseFallback(fallbackId) {
    var details = document.getElementById(fallbackId);
    if (details) details.removeAttribute('open');
  }

  function readJSON(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  function getCssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function hexToRgba(hex, alpha) {
    var m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (!m) return hex;
    var r = parseInt(m[1], 16), g = parseInt(m[2], 16), b = parseInt(m[3], 16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
  }

  function whenChartReady(callback) {
    if (window.Chart) {
      callback();
      return;
    }
    window.addEventListener('load', function () {
      if (window.Chart) callback();
    });
  }

  function renderSkillRadar() {
    var canvas = document.getElementById('skill-radar-chart');
    var data = readJSON('skill-chart-data');
    if (!canvas || !data) return;

    var navy = getCssVar('--color-navy') || '#0B1120';
    var teal = getCssVar('--color-accent') || '#E8503D';
    var border = getCssVar('--color-border') || '#DCE1E6';
    var textSecondary = getCssVar('--color-text-secondary') || '#4A5568';

    new Chart(canvas, {
      type: 'radar',
      data: {
        labels: data.labels,
        datasets: [
          {
            label: 'Current',
            data: data.current,
            borderColor: teal,
            backgroundColor: hexToRgba(teal, 0.15),
            pointBackgroundColor: teal,
          },
          {
            label: 'Target',
            data: data.target,
            borderColor: navy,
            backgroundColor: hexToRgba(navy, 0.08),
            pointBackgroundColor: navy,
            borderDash: [4, 4],
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          r: {
            min: 0,
            max: 5,
            ticks: { stepSize: 1, backdropColor: 'transparent', color: textSecondary },
            grid: { color: border },
            angleLines: { color: border },
            pointLabels: { color: textSecondary },
          },
        },
        plugins: {
          legend: { position: 'bottom', labels: { color: textSecondary } },
        },
      },
    });
    collapseFallback('skill-chart-fallback');
  }

  function renderMonthlyHoursBar() {
    var canvas = document.getElementById('monthly-hours-chart');
    var data = readJSON('monthly-hours-chart-data');
    if (!canvas || !data) return;

    var navy = getCssVar('--color-navy') || '#0B1120';
    var teal = getCssVar('--color-accent') || '#E8503D';
    var border = getCssVar('--color-border') || '#DCE1E6';
    var textSecondary = getCssVar('--color-text-secondary') || '#4A5568';

    new Chart(canvas, {
      type: 'bar',
      data: {
        labels: data.labels,
        datasets: [
          { label: 'Actual hours', data: data.actual, backgroundColor: teal },
          { label: 'Target hours', data: data.target, backgroundColor: navy },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        aspectRatio: 3.5,
        scales: {
          y: { beginAtZero: true, ticks: { color: textSecondary }, grid: { color: border } },
          x: { ticks: { color: textSecondary }, grid: { color: border } },
        },
        plugins: { legend: { position: 'bottom', labels: { color: textSecondary } } },
      },
    });
    collapseFallback('monthly-hours-fallback');
  }

  function renderWeeklyHoursLine() {
    var canvas = document.getElementById('weekly-hours-chart');
    var data = readJSON('weekly-hours-chart-data');
    if (!canvas || !data) return;

    var teal = getCssVar('--color-accent') || '#E8503D';
    var border = getCssVar('--color-border') || '#DCE1E6';
    var textSecondary = getCssVar('--color-text-secondary') || '#4A5568';

    new Chart(canvas, {
      type: 'line',
      data: {
        labels: data.labels,
        datasets: [
          {
            label: 'Hours',
            data: data.hours,
            borderColor: teal,
            backgroundColor: hexToRgba(teal, 0.15),
            fill: true,
            tension: 0.25,
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          y: { beginAtZero: true, ticks: { color: textSecondary }, grid: { color: border } },
          x: { ticks: { color: textSecondary }, grid: { color: border } },
        },
        plugins: { legend: { display: false } },
      },
    });
    collapseFallback('weekly-hours-fallback');
  }

  document.addEventListener('DOMContentLoaded', function () {
    whenChartReady(function () {
      renderSkillRadar();
      renderMonthlyHoursBar();
      renderWeeklyHoursLine();
    });
  });
})();
