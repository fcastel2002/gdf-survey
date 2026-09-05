"""Interactive standalone HTML survey report generator with BestBuy-style faceted filters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from gdf_survey.models import GdfSurveyResult

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SCADA Equipment Survey - GraphWorX32</title>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #38bdf8;
      --accent-hover: #0284c7;
      --green: #22c55e;
      --green-bg: rgba(34, 197, 94, 0.15);
      --amber: #f59e0b;
      --amber-bg: rgba(245, 158, 11, 0.15);
      --blue: #3b82f6;
      --blue-bg: rgba(59, 130, 246, 0.15);
      --purple: #a855f7;
      --purple-bg: rgba(168, 85, 247, 0.15);
      --emerald: #10b981;
      --emerald-bg: rgba(16, 185, 129, 0.15);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text-main);
      padding: 24px;
      line-height: 1.5;
    }
    .header {
      margin-bottom: 20px;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 16px;
    }
    .header h1 {
      font-size: 24px;
      font-weight: 700;
      color: #fff;
    }
    .header .subtitle {
      font-size: 13px;
      color: var(--text-muted);
      margin-top: 4px;
    }

    /* Screen Selector Tabs */
    .screen-tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 20px;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 10px;
      overflow-x: auto;
    }
    .screen-tab {
      background-color: var(--card-bg);
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
      white-space: nowrap;
    }
    .screen-tab:hover {
      color: #fff;
      border-color: var(--accent);
    }
    .screen-tab.active {
      background-color: var(--accent);
      color: #0f172a;
      border-color: var(--accent);
    }

    .kpi-row {
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
      margin-bottom: 20px;
    }
    .kpi-pill {
      background-color: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 10px 16px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .kpi-pill .kpi-num {
      font-size: 20px;
      font-weight: 700;
      color: var(--accent);
    }
    .kpi-pill .kpi-lbl {
      font-size: 12px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    /* Layout: Sidebar + Main Content */
    .layout {
      display: flex;
      gap: 24px;
      align-items: flex-start;
    }
    @media (max-width: 960px) {
      .layout { flex-direction: column; }
      .sidebar { width: 100% !important; }
    }

    /* BestBuy-style Faceted Sidebar */
    .sidebar {
      width: 280px;
      flex-shrink: 0;
      background-color: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 18px;
    }
    .sidebar-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 10px;
    }
    .sidebar-header h3 {
      font-size: 16px;
      font-weight: 700;
      color: #fff;
    }
    .clear-btn {
      background: none;
      border: none;
      color: var(--accent);
      font-size: 12px;
      cursor: pointer;
      font-weight: 600;
    }
    .clear-btn:hover { text-decoration: underline; }

    .facet-group {
      margin-bottom: 18px;
      border-bottom: 1px solid rgba(51, 65, 85, 0.4);
      padding-bottom: 14px;
    }
    .facet-group:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
    .facet-title {
      font-size: 13px;
      font-weight: 700;
      color: #e2e8f0;
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .facet-options {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .facet-option {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: var(--text-main);
      cursor: pointer;
      user-select: none;
    }
    .facet-option input[type="checkbox"] {
      width: 16px;
      height: 16px;
      cursor: pointer;
      accent-color: var(--accent);
      border-radius: 4px;
    }
    .facet-option:hover { color: #fff; }
    .facet-count {
      color: var(--text-muted);
      font-size: 11px;
      margin-left: auto;
    }

    /* Main Table Area */
    .main-content {
      flex: 1;
      min-width: 0;
    }
    .search-bar {
      margin-bottom: 14px;
      position: relative;
    }
    .search-bar input {
      width: 100%;
      background-color: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      color: #fff;
      padding: 12px 16px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s;
    }
    .search-bar input:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.15);
    }
    .active-filters {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 14px;
      align-items: center;
    }
    .filter-chip {
      background-color: rgba(56, 189, 248, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.3);
      color: var(--accent);
      padding: 4px 10px;
      border-radius: 16px;
      font-size: 12px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .filter-chip button {
      background: none;
      border: none;
      color: var(--accent);
      cursor: pointer;
      font-size: 13px;
      font-weight: 700;
      line-height: 1;
    }
    .results-count {
      font-size: 13px;
      color: var(--text-muted);
      margin-bottom: 10px;
      font-weight: 500;
    }

    .table-container {
      background-color: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      overflow-x: auto;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 13px;
    }
    th {
      background-color: #0c1322;
      color: #cbd5e1;
      font-weight: 600;
      padding: 12px 14px;
      border-bottom: 1px solid var(--card-border);
      white-space: nowrap;
    }
    td {
      padding: 10px 14px;
      border-bottom: 1px solid rgba(51, 65, 85, 0.4);
      white-space: nowrap;
    }
    tr:hover td {
      background-color: rgba(56, 189, 248, 0.04);
    }
    .badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;
    }
    .badge-highlight { background: var(--blue-bg); color: var(--blue); }
    .flag-yes {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      background: var(--green-bg);
      color: var(--green);
      font-weight: 700;
      font-size: 11px;
    }
    .flag-no {
      color: #64748b;
      font-weight: 500;
      font-size: 11px;
    }
    .footer {
      margin-top: 24px;
      font-size: 12px;
      color: var(--text-muted);
      text-align: center;
    }
  </style>
</head>
<body>

  <div class="header">
    <div>
      <h1>SCADA Equipment Survey - GraphWorX32</h1>
      <div class="subtitle" id="display-subtitle">Consolidated equipment survey (excluding spare rows)</div>
    </div>
  </div>

  <div class="screen-tabs" id="screen-tabs-container" style="display: none;"></div>

  <div class="kpi-row" id="kpi-row"></div>

  <div class="layout">
    <!-- BestBuy-style Faceted Sidebar -->
    <div class="sidebar">
      <div class="sidebar-header">
        <h3>Filters</h3>
        <button class="clear-btn" onclick="clearAllFilters()">Clear all</button>
      </div>
      <div id="dynamic-facets-container"></div>
    </div>

    <!-- Main Content Table Area -->
    <div class="main-content">
      <div class="search-bar">
        <input type="text" id="search-input" placeholder="Search by equipment, root ID, device, tag, or values..." oninput="applyFilters()">
      </div>

      <div class="active-filters" id="active-filters-bar"></div>
      <div class="results-count" id="results-count">Showing 0 items</div>

      <div class="table-container">
        <table id="main-table">
          <thead>
            <tr id="table-head-row"></tr>
          </thead>
          <tbody id="table-body"></tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="footer">
    Generated automatically by GDF Survey Tool &bull; Offline consolidated SCADA survey
  </div>

  <script>
    const surveyData = DATA_PLACEHOLDER;
    let selectedScreenFilter = '__ALL__'; // '__ALL__' or screen_id
    let selectedFacets = {}; // facetKey -> Set of selected values

    function init() {
      // Build screen tabs if multiple displays
      const tabsContainer = document.getElementById('screen-tabs-container');
      const validScreens = surveyData.filter(s => (s.items || s.pumps || []).length > 0);

      if (validScreens.length > 1) {
        tabsContainer.style.display = 'flex';
        const totalItemsAll = validScreens.reduce((acc, s) => acc + (s.items || s.pumps || []).length, 0);

        const allBtn = document.createElement('button');
        allBtn.className = 'screen-tab active';
        allBtn.textContent = `All Displays (${totalItemsAll})`;
        allBtn.onclick = () => selectScreen('__ALL__', allBtn);
        tabsContainer.appendChild(allBtn);

        validScreens.forEach(s => {
          const btn = document.createElement('button');
          btn.className = 'screen-tab';
          const cnt = (s.items || s.pumps || []).length;
          btn.textContent = `${s.sheet_name} (${cnt})`;
          btn.onclick = () => selectScreen(s.screen_id, btn);
          tabsContainer.appendChild(btn);
        });
      }

      updateView();
    }

    function selectScreen(screenName, btnElem) {
      selectedScreenFilter = screenName;
      document.querySelectorAll('.screen-tab').forEach(b => b.classList.remove('active'));
      btnElem.classList.add('active');
      clearAllFilters(false);
      updateView();
    }

    function getActivePool() {
      if (selectedScreenFilter === '__ALL__') {
        const pool = [];
        surveyData.forEach(s => {
          (s.items || s.pumps || []).forEach(p => {
            pool.push({ ...p, screen: s.sheet_name });
          });
        });
        return pool;
      }
      const s = surveyData.find(d => d.screen_id === selectedScreenFilter) || surveyData[0];
      return (s.items || s.pumps || []).map(p => ({ ...p, screen: s.sheet_name }));
    }

    function getActiveCustomDataKeys() {
      const keysSet = new Set();
      if (selectedScreenFilter === '__ALL__') {
        surveyData.forEach(s => (s.custom_data_keys || []).forEach(k => keysSet.add(k)));
      } else {
        const s = surveyData.find(d => d.screen_id === selectedScreenFilter) || surveyData[0];
        (s.custom_data_keys || []).forEach(k => keysSet.add(k));
      }
      return Array.from(keysSet);
    }

    function updateView() {
      const pool = getActivePool();
      const keys = getActiveCustomDataKeys();
      renderKPIs(pool, keys);
      renderTableHeader(keys);
      buildFacetCheckboxes(pool, keys);
      applyFilters();
    }

    function renderKPIs(pool, keys) {
      const kpis = document.getElementById('kpi-row');
      const activeCount = pool.filter(p => p.is_active).length;

      kpis.innerHTML = `
        <div class="kpi-pill">
          <div class="kpi-num">${pool.length}</div>
          <div class="kpi-lbl">Total Items</div>
        </div>
        <div class="kpi-pill">
          <div class="kpi-num" style="color: var(--green);">${activeCount}</div>
          <div class="kpi-lbl">Active Items</div>
        </div>
        <div class="kpi-pill">
          <div class="kpi-num" style="color: var(--accent);">${keys.length}</div>
          <div class="kpi-lbl">Custom Data Attributes</div>
        </div>
      `;
    }

    function renderTableHeader(keys) {
      const tr = document.getElementById('table-head-row');
      tr.innerHTML = `
        <th style="width: 40px; text-align: center;">No.</th>
        <th>Display</th>
        <th>Root ID</th>
        <th>Device</th>
        <th>Controller / Type</th>
        <th>Primary Source</th>
      ` + keys.map(k => `<th>${escapeHtml(k)}</th>`).join('');
    }

    function buildFacetCheckboxes(pool, keys) {
      const container = document.getElementById('dynamic-facets-container');
      container.innerHTML = '';

      // 1. Device facet (if >= 2 distinct devices)
      const devMap = {};
      pool.forEach(p => { if (p.device_name && p.device_name !== '-') devMap[p.device_name] = (devMap[p.device_name] || 0) + 1; });
      if (Object.keys(devMap).length >= 2) {
        buildFacetGroup('Device', '_device', Object.entries(devMap).sort((a,b)=>b[1]-a[1]).map(([b, c]) => ({ label: b, val: b, count: c })));
      }

      // 2. Dynamic custom data facets (for keys with discrete distinct values between 2 and 25)
      keys.forEach(k => {
        const valMap = {};
        pool.forEach(p => {
          const v = (p.custom_data && p.custom_data[k] !== undefined) ? p.custom_data[k] : (p[k] !== undefined ? String(p[k]) : '');
          if (v) valMap[v] = (valMap[v] || 0) + 1;
        });
        const distinctCount = Object.keys(valMap).length;
        if (distinctCount >= 2 && distinctCount <= 25) {
          const title = k.replace(/[<>]/g, '').trim() || k;
          const options = Object.entries(valMap).sort((a,b)=>b[1]-a[1]).map(([val, cnt]) => {
            let lbl = val;
            if (val === '1') lbl = 'YES (1)';
            else if (val === '0') lbl = 'NO (0)';
            return { label: lbl, val: val, count: cnt };
          });
          buildFacetGroup(title, `cd_${k}`, options);
        }
      });
    }

    function buildFacetGroup(groupTitle, facetKey, options) {
      const container = document.getElementById('dynamic-facets-container');
      const grp = document.createElement('div');
      grp.className = 'facet-group';

      const title = document.createElement('div');
      title.className = 'facet-title';
      title.textContent = groupTitle;
      grp.appendChild(title);

      const optsContainer = document.createElement('div');
      optsContainer.className = 'facet-options';

      if (!selectedFacets[facetKey]) {
        selectedFacets[facetKey] = new Set();
      }

      options.forEach(opt => {
        const label = document.createElement('label');
        label.className = 'facet-option';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = selectedFacets[facetKey].has(opt.val);
        checkbox.onchange = (e) => {
          if (e.target.checked) selectedFacets[facetKey].add(opt.val);
          else selectedFacets[facetKey].delete(opt.val);
          applyFilters();
        };

        const nameSpan = document.createElement('span');
        nameSpan.textContent = opt.label;

        const countSpan = document.createElement('span');
        countSpan.className = 'facet-count';
        countSpan.textContent = `(${opt.count})`;

        label.appendChild(checkbox);
        label.appendChild(nameSpan);
        label.appendChild(countSpan);
        optsContainer.appendChild(label);
      });

      grp.appendChild(optsContainer);
      container.appendChild(grp);
    }

    function clearAllFilters(rebuild = true) {
      Object.keys(selectedFacets).forEach(k => selectedFacets[k].clear());
      document.getElementById('search-input').value = '';
      if (rebuild) {
        const pool = getActivePool();
        const keys = getActiveCustomDataKeys();
        buildFacetCheckboxes(pool, keys);
        applyFilters();
      }
    }

    function applyFilters() {
      const pool = getActivePool();
      const keys = getActiveCustomDataKeys();
      const rawSearch = document.getElementById('search-input').value.toLowerCase().trim();
      const searchTerms = rawSearch.split(/\\s+/).filter(Boolean);

      const filtered = pool.filter(p => {
        // Facet: Device
        if (selectedFacets['_device'] && selectedFacets['_device'].size > 0) {
          if (!selectedFacets['_device'].has(p.device_name)) return false;
        }

        // Custom data facets
        for (const [fKey, selSet] of Object.entries(selectedFacets)) {
          if (fKey.startsWith('cd_') && selSet.size > 0) {
            const cdKey = fKey.substring(3);
            const val = (p.custom_data && p.custom_data[cdKey] !== undefined) ? p.custom_data[cdKey] : (p[cdKey] !== undefined ? String(p[cdKey]) : '');
            if (!selSet.has(val)) return false;
          }
        }

        // Search text matching across all properties and custom data
        if (searchTerms.length > 0) {
          let cdTokens = '';
          if (p.custom_data) {
            cdTokens = Object.values(p.custom_data).join(' ');
          }
          const searchable = `${p.screen || ''} ${p.root_id || p.well_id || ''} ${p.device_name || ''} ${p.controller_type || ''} ${p.primary_source || ''} ${cdTokens}`.toLowerCase();
          const allMatch = searchTerms.every(term => searchable.includes(term));
          if (!allMatch) return false;
        }

        return true;
      });

      renderActiveChips();
      renderTableRows(filtered, pool.length, keys);
    }

    function renderActiveChips() {
      const bar = document.getElementById('active-filters-bar');
      bar.innerHTML = '';

      const pool = getActivePool();
      const keys = getActiveCustomDataKeys();
      const addChip = (text, removeFn) => {
        const chip = document.createElement('div');
        chip.className = 'filter-chip';
        chip.innerHTML = `<span>${escapeHtml(text)}</span>`;
        const btn = document.createElement('button');
        btn.innerHTML = '&times;';
        btn.onclick = removeFn;
        chip.appendChild(btn);
        bar.appendChild(chip);
      };

      for (const [fKey, selSet] of Object.entries(selectedFacets)) {
        if (selSet.size > 0) {
          const title = fKey.startsWith('cd_') ? fKey.substring(3).replace(/[<>]/g, '') : 'Device';
          selSet.forEach(val => {
            addChip(`${title}: ${val}`, () => {
              selSet.delete(val);
              buildFacetCheckboxes(pool, keys);
              applyFilters();
            });
          });
        }
      }

      const q = document.getElementById('search-input').value.trim();
      if (q) {
        addChip(`Search: "${q}"`, () => { document.getElementById('search-input').value = ''; applyFilters(); });
      }
    }

    function renderTableRows(items, totalPoolCount, keys) {
      document.getElementById('results-count').textContent = `Showing ${items.length} of ${totalPoolCount} surveyed items`;

      const tbody = document.getElementById('table-body');
      tbody.innerHTML = '';

      if (items.length === 0) {
        const totalCols = 6 + keys.length;
        tbody.innerHTML = `<tr><td colspan="${totalCols}" style="text-align: center; padding: 40px; color: var(--text-muted);">No items matching the filter criteria.</td></tr>`;
        return;
      }

      items.forEach((p, idx) => {
        const tr = document.createElement('tr');
        let cells = `
          <td style="text-align: center; color: var(--text-muted);">${idx + 1}</td>
          <td style="color: var(--accent); font-weight: 600;">${escapeHtml(p.screen || '-')}</td>
          <td style="font-weight: 700;">${escapeHtml(p.root_id || p.well_id || p.pozo_label || '-')}</td>
          <td><span style="background: rgba(51, 65, 85, 0.4); padding: 2px 6px; border-radius: 4px;">${escapeHtml(p.device_name || '-')}</span></td>
          <td style="color: var(--text-muted);">${escapeHtml(p.controller_type || p.controller_brand || '-')}</td>
          <td style="font-family: ui-monospace, monospace; font-size: 11px;">${escapeHtml(p.primary_source || '-')}</td>
        `;

        keys.forEach(k => {
          const v = (p.custom_data && p.custom_data[k] !== undefined) ? p.custom_data[k] : (p[k] !== undefined ? String(p[k]) : '-');
          if (v === '1' || v === 'YES' || v === 'SÍ') {
            cells += `<td style="text-align: center;"><span class="flag-yes">YES</span></td>`;
          } else if (v === '0' || v === 'NO') {
            cells += `<td style="text-align: center;"><span class="flag-no">NO</span></td>`;
          } else {
            cells += `<td>${escapeHtml(v)}</td>`;
          }
        });

        tr.innerHTML = cells;
        tbody.appendChild(tr);
      });
    }

    function escapeHtml(str) {
      return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    window.onload = init;
  </script>
</body>
</html>
"""


def generate_html_survey(
    results: Sequence[GdfSurveyResult],
    output_path: str | Path,
) -> Path:
    """Generate a standalone interactive HTML survey report with dynamic faceted filters."""
    target_path = Path(output_path).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    serialized = []
    for idx, res in enumerate(results):
        screen_id = f"screen_{idx}_{res.gdf_path.stem}"
        items_payload = []
        for it in res.items:
            items_payload.append({
                "index": it.index,
                "root_id": it.root_id,
                "label": it.label,
                "device_name": it.device_name,
                "controller_type": it.controller_type,
                "primary_source": it.primary_source,
                "is_active": it.is_active,
                "custom_data": it.custom_data,
                "well_id": it.root_id,
                "pozo_label": it.label,
                "pump_code": it.pump_code,
                "battery": it.battery,
                "controller_brand": it.controller_brand,
                "has_pt": it.has_pt,
                "has_tke": it.has_tke,
                "has_tkq": it.has_tkq,
                "has_sam": it.has_sam,
                "is_exp": it.is_exp,
            })

        serialized.append({
            "screen_id": screen_id,
            "display_name": res.display_name,
            "sheet_name": res.sheet_name,
            "layer_name": res.layer_name,
            "total_items": res.total_items,
            "total_pumps": res.total_items,
            "custom_data_keys": res.discovered_custom_data_keys,
            "items": items_payload,
            "pumps": items_payload,
        })

    json_payload = json.dumps(serialized, ensure_ascii=False)
    safe_json = json_payload.replace("<", "\\u003c").replace(">", "\\u003e")
    rendered_html = HTML_TEMPLATE.replace("DATA_PLACEHOLDER", safe_json)

    target_path.write_text(rendered_html, encoding="utf-8")
    return target_path
