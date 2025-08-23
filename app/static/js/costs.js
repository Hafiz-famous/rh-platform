// app/static/js/costs.js
async function loadSummary(period) {
  const url = `/costs/api/summary?period=${encodeURIComponent(period)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('API error');
  return res.json();
}

function fmtMoney(x, currency) {
  return new Intl.NumberFormat(undefined, { style: 'currency', currency: currency || 'XOF' }).format(x || 0);
}

let chart;

async function render(period) {
  const data = await loadSummary(period);
  const tbody = document.querySelector('#costsTable tbody');
  tbody.innerHTML = '';
  let currency = 'XOF';

  data.rows.forEach(r => {
    currency = r.currency || currency;
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${r.code}</td>
      <td>${r.name}</td>
      <td>${fmtMoney(r.budget_monthly, r.currency)}</td>
      <td>${fmtMoney(r.actual_with_overhead, r.currency)}</td>
      <td>${fmtMoney(r.variance, r.currency)}</td>
    `;
    tbody.appendChild(tr);
  });

  // Totals
  const totals = document.getElementById('totals');
  totals.innerHTML = '';
  const li1 = document.createElement('li');
  li1.textContent = `Budget total: ${fmtMoney(data.total_budget, currency)}`;
  const li2 = document.createElement('li');
  li2.textContent = `Réel total: ${fmtMoney(data.total_actual, currency)}`;
  totals.appendChild(li1); totals.appendChild(li2);

  // Chart
  const ctx = document.getElementById('costsChart').getContext('2d');
  const labels = data.rows.map(r => r.code);
  const budget = data.rows.map(r => r.budget_monthly);
  const actual = data.rows.map(r => r.actual_with_overhead);
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Budget', data: budget },
        { label: 'Réel + frais', data: actual },
      ]
    },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } }
  });
}

document.getElementById('period-form').addEventListener('submit', (e) => {
  e.preventDefault();
  const p = document.getElementById('period').value;
  render(p);
});

window.addEventListener('DOMContentLoaded', () => {
  const p = document.getElementById('period').value;
  render(p);
});
