"""Interactive standalone HTML survey report generator with BestBuy-style faceted filters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from gdf_survey.models import GdfSurveyResult

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Relevamiento de Bombas PCP - SCADA GraphWorX</title>
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
      <h1>Relevamiento de Equipos SCADA - GraphWorX</h1>
      <div class="subtitle" id="display-subtitle">Relevamiento consolidado por equipo (sin renglones de reserva)</div>
    </div>
  </div>

  <div class="screen-tabs" id="screen-tabs-container" style="display: none;"></div>

  <div class="kpi-row" id="kpi-row"></div>

  <div class="layout">
    <!-- BestBuy-style Faceted Sidebar -->
    <div class="sidebar">
      <div class="sidebar-header">
        <h3>Filtros</h3>
        <button class="clear-btn" onclick="clearAllFilters()">Limpiar todo</button>
      </div>

      <!-- Facet: Controlador -->
      <div class="facet-group">
        <div class="facet-title">Controlador / Interfaz</div>
        <div class="facet-options" id="facet-brands"></div>
      </div>

      <!-- Facet: Tiene Presión PT -->
      <div class="facet-group">
        <div class="facet-title">Presión de Línea (PT)</div>
        <div class="facet-options" id="facet-pt"></div>
      </div>

      <!-- Facet: Batería -->
      <div class="facet-group">
        <div class="facet-title">Grupo / Batería</div>
        <div class="facet-options" id="facet-batteries"></div>
      </div>

      <!-- Facet: Tipo de Controlador -->
      <div class="facet-group">
        <div class="facet-title">Tipo / Modelo Controlador</div>
        <div class="facet-options" id="facet-types"></div>
      </div>

      <!-- Facet: SAM Controller -->
      <div class="facet-group">
        <div class="facet-title">Controlador SAM</div>
        <div class="facet-options" id="facet-sam"></div>
      </div>
    </div>

    <!-- Main Content Table Area -->
    <div class="main-content">
      <div class="search-bar">
        <input type="text" id="search-input" placeholder="Buscar por equipo, tag, grupo o controlador..." oninput="applyFilters()">
      </div>

      <div class="active-filters" id="active-filters-bar"></div>
      <div class="results-count" id="results-count">Mostrando 0 equipos</div>

      <div class="table-container">
        <table id="main-table">
          <thead>
            <tr>
              <th style="width: 40px; text-align: center;">N°</th>
              <th>Pantalla</th>
              <th>Equipo</th>
              <th>Tag (<<pozo>>)</th>
              <th>Grupo (<<bat>>)</th>
              <th>Dispositivo (<<dispositivo>>)</th>
              <th>Controlador</th>
              <th>Tipo de Controlador</th>
              <th style="text-align: center;">Tiene PT</th>
              <th style="text-align: center;">Tiene TKE</th>
              <th style="text-align: center;">Tiene TKQ</th>
              <th style="text-align: center;">Tiene SAM</th>
            </tr>
          </thead>
          <tbody id="table-body"></tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="footer">
    Generado automáticamente por GDF Survey Tool &bull; Relevamiento consolidado por equipo fuera de línea
  </div>

  <script>
    const surveyData = DATA_PLACEHOLDER;
    let selectedScreenFilter = '__ALL__'; // '__ALL__' or screen_id
    let selectedFacets = {
      brands: new Set(),
      pt: new Set(),
      batteries: new Set(),
      types: new Set(),
      sam: new Set()
    };

    function init() {
      // Build screen tabs if multiple displays
      const tabsContainer = document.getElementById('screen-tabs-container');
      const validScreens = surveyData.filter(s => s.pumps.length > 0);

      if (validScreens.length > 1) {
        tabsContainer.style.display = 'flex';
        const totalPumpsAll = validScreens.reduce((acc, s) => acc + s.pumps.length, 0);

        const allBtn = document.createElement('button');
        allBtn.className = 'screen-tab active';
        allBtn.textContent = `Todas las Pantallas (${totalPumpsAll})`;
        allBtn.onclick = () => selectScreen('__ALL__', allBtn);
        tabsContainer.appendChild(allBtn);

        validScreens.forEach(s => {
          const btn = document.createElement('button');
          btn.className = 'screen-tab';
          btn.textContent = `${s.sheet_name} (${s.pumps.length})`;
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

    function getActivePumpsPool() {
      if (selectedScreenFilter === '__ALL__') {
        const pool = [];
        surveyData.forEach(s => {
          s.pumps.forEach(p => {
            pool.push({ ...p, screen: s.sheet_name });
          });
        });
        return pool;
      }
      const s = surveyData.find(d => d.screen_id === selectedScreenFilter) || surveyData[0];
      return s.pumps.map(p => ({ ...p, screen: s.sheet_name }));
    }

    function updateView() {
      const pool = getActivePumpsPool();
      renderKPIs(pool);
      buildFacetCheckboxes(pool);
      applyFilters();
    }

    function renderKPIs(pool) {
      const kpis = document.getElementById('kpi-row');
      const ptCount = pool.filter(p => p.has_pt === '1').length;
      const brandCounts = {};
      pool.forEach(p => {
        if (p.controller_brand && p.controller_brand !== 'Desconocido') {
          brandCounts[p.controller_brand] = (brandCounts[p.controller_brand] || 0) + 1;
        }
      });

      kpis.innerHTML = `
        <div class="kpi-pill">
          <div class="kpi-num">${pool.length}</div>
          <div class="kpi-lbl">Equipos Activos</div>
        </div>
        <div class="kpi-pill">
          <div class="kpi-num" style="color: var(--green);">${ptCount}</div>
          <div class="kpi-lbl">Con Presión PT</div>
        </div>
        ${Object.entries(brandCounts).map(([b, c]) => `
          <div class="kpi-pill">
            <div class="kpi-num" style="color: #fff;">${c}</div>
            <div class="kpi-lbl">${b}</div>
          </div>
        `).join('')}
      `;
    }

    function buildFacetCheckboxes(pool) {
      // 1. Controllers
      const brandMap = {};
      pool.forEach(p => { if (p.controller_brand) brandMap[p.controller_brand] = (brandMap[p.controller_brand] || 0) + 1; });
      buildFacetGroup('facet-brands', 'brands', Object.entries(brandMap).sort((a,b)=>b[1]-a[1]).map(([b, c]) => ({ label: b, val: b, count: c })));

      // 2. PT
      const ptYes = pool.filter(p => p.has_pt === '1').length;
      const ptNo = pool.filter(p => p.has_pt !== '1').length;
      buildFacetGroup('facet-pt', 'pt', [
        { label: 'Con Presión PT', val: '1', count: ptYes },
        { label: 'Sin Presión PT', val: '0', count: ptNo }
      ]);

      // 3. Batteries
      const batMap = {};
      pool.forEach(p => {
        const b = p.battery || 'Sin Asignar';
        batMap[b] = (batMap[b] || 0) + 1;
      });
      const batOptions = Object.entries(batMap).sort((a, b) => b[1] - a[1]).map(([b, c]) => ({ label: b, val: b, count: c }));
      buildFacetGroup('facet-batteries', 'batteries', batOptions);

      // 4. Controller Types
      const typeMap = {};
      pool.forEach(p => {
        const t = p.controller_type || 'Genérico';
        typeMap[t] = (typeMap[t] || 0) + 1;
      });
      const typeOptions = Object.entries(typeMap).sort((a, b) => b[1] - a[1]).map(([t, c]) => ({ label: t, val: t, count: c }));
      buildFacetGroup('facet-types', 'types', typeOptions);

      // 5. SAM
      const samYes = pool.filter(p => p.has_sam === '1').length;
      const samNo = pool.filter(p => p.has_sam !== '1').length;
      buildFacetGroup('facet-sam', 'sam', [
        { label: 'Con SAM', val: '1', count: samYes },
        { label: 'Sin SAM', val: '0', count: samNo }
      ]);
    }

    function buildFacetGroup(containerId, facetKey, options) {
      const container = document.getElementById(containerId);
      container.innerHTML = '';

      options.forEach(opt => {
        if (opt.count === 0 && facetKey !== 'pt') return;
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
        container.appendChild(label);
      });
    }

    function clearAllFilters(rebuild = true) {
      selectedFacets.brands.clear();
      selectedFacets.pt.clear();
      selectedFacets.batteries.clear();
      selectedFacets.types.clear();
      selectedFacets.sam.clear();
      document.getElementById('search-input').value = '';
      if (rebuild) {
        buildFacetCheckboxes(getActivePumpsPool());
        applyFilters();
      }
    }

    function applyFilters() {
      const pool = getActivePumpsPool();
      const rawSearch = document.getElementById('search-input').value.toLowerCase().trim();
      const searchTerms = rawSearch.split(/\\s+/).filter(Boolean);

      const filtered = pool.filter(p => {
        // Facet 1: Controllers
        if (selectedFacets.brands.size > 0 && !selectedFacets.brands.has(p.controller_brand)) {
          return false;
        }

        // Facet 2: PT
        if (selectedFacets.pt.size > 0) {
          const ptVal = (p.has_pt === '1') ? '1' : '0';
          if (!selectedFacets.pt.has(ptVal)) return false;
        }

        // Facet 3: Batteries
        if (selectedFacets.batteries.size > 0 && !selectedFacets.batteries.has(p.battery)) {
          return false;
        }

        // Facet 4: Controller Types
        if (selectedFacets.types.size > 0 && !selectedFacets.types.has(p.controller_type)) {
          return false;
        }

        // Facet 5: SAM
        if (selectedFacets.sam.size > 0) {
          const samVal = (p.has_sam === '1') ? '1' : '0';
          if (!selectedFacets.sam.has(samVal)) return false;
        }

        // Search text matching (AND logic across all search tokens)
        if (searchTerms.length > 0) {
          const searchable = `${p.screen || ''} ${p.well_id || ''} ${p.pump_code || ''} ${p.battery || ''} ${p.device_name || ''} ${p.controller_brand || ''} ${p.controller_type || ''}`.toLowerCase();
          const allMatch = searchTerms.every(term => searchable.includes(term));
          if (!allMatch) return false;
        }

        return true;
      });

      renderActiveChips();
      renderTableRows(filtered, pool.length);
    }

    function renderActiveChips() {
      const bar = document.getElementById('active-filters-bar');
      bar.innerHTML = '';

      const pool = getActivePumpsPool();
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

      selectedFacets.brands.forEach(b => addChip(`Controlador: ${b}`, () => { selectedFacets.brands.delete(b); buildFacetCheckboxes(pool); applyFilters(); }));
      selectedFacets.pt.forEach(v => addChip(`PT: ${v === '1' ? 'Con PT' : 'Sin PT'}`, () => { selectedFacets.pt.delete(v); buildFacetCheckboxes(pool); applyFilters(); }));
      selectedFacets.batteries.forEach(b => addChip(`Grupo: ${b}`, () => { selectedFacets.batteries.delete(b); buildFacetCheckboxes(pool); applyFilters(); }));
      selectedFacets.types.forEach(t => addChip(`Tipo: ${t}`, () => { selectedFacets.types.delete(t); buildFacetCheckboxes(pool); applyFilters(); }));
      selectedFacets.sam.forEach(v => addChip(`SAM: ${v === '1' ? 'Con SAM' : 'Sin SAM'}`, () => { selectedFacets.sam.delete(v); buildFacetCheckboxes(pool); applyFilters(); }));

      const q = document.getElementById('search-input').value.trim();
      if (q) {
        addChip(`Búsqueda: "${q}"`, () => { document.getElementById('search-input').value = ''; applyFilters(); });
      }
    }

    function renderTableRows(pumps, totalPoolCount) {
      document.getElementById('results-count').textContent = `Mostrando ${pumps.length} de ${totalPoolCount} equipos relevados`;

      const tbody = document.getElementById('table-body');
      tbody.innerHTML = '';

      if (pumps.length === 0) {
        tbody.innerHTML = `<tr><td colspan="12" style="text-align: center; padding: 40px; color: var(--text-muted);">No se encontraron equipos que coincidan con los filtros.</td></tr>`;
        return;
      }

      pumps.forEach((p, idx) => {
        const tr = document.createElement('tr');

        let brandBadge = `<span class="badge badge-highlight">${escapeHtml(p.controller_brand || 'Genérico')}</span>`;

        const flag = (val) => val === '1' ? '<span class="flag-yes">SÍ</span>' : '<span class="flag-no">NO</span>';

        tr.innerHTML = `
          <td style="text-align: center; color: var(--text-muted);">${idx + 1}</td>
          <td style="color: var(--accent); font-weight: 600;">${escapeHtml(p.screen || '-')}</td>
          <td style="font-weight: 700;">${escapeHtml(p.well_id || p.pozo_label)}</td>
          <td style="font-weight: 600; color: var(--accent);">${escapeHtml(p.pump_code || '-')}</td>
          <td><span style="background: rgba(51, 65, 85, 0.4); padding: 2px 6px; border-radius: 4px;">${escapeHtml(p.battery || '-')}</span></td>
          <td style="font-family: ui-monospace, monospace; font-size: 11px;">${escapeHtml(p.device_name || '-')}</td>
          <td>${brandBadge}</td>
          <td style="color: var(--text-muted);">${escapeHtml(p.controller_type || '-')}</td>
          <td style="text-align: center;">${flag(p.has_pt)}</td>
          <td style="text-align: center;">${flag(p.has_tke)}</td>
          <td style="text-align: center;">${flag(p.has_tkq)}</td>
          <td style="text-align: center;">${flag(p.has_sam)}</td>
        `;
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
    """Generate a standalone interactive HTML survey report with BestBuy-style faceted filters."""
    target_path = Path(output_path).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    serialized = []
    for idx, res in enumerate(results):
        screen_id = f"screen_{idx}_{res.gdf_path.stem}"
        serialized.append({
            "screen_id": screen_id,
            "display_name": res.display_name,
            "sheet_name": res.sheet_name,
            "layer_name": res.layer_name,
            "total_pumps": res.total_pumps,
            "brand_counts": res.brand_counts,
            "pumps": [
                {
                    "pozo_index": p.pozo_index,
                    "pozo_label": p.pozo_label,
                    "well_id": p.well_id,
                    "pump_code": p.pump_code,
                    "battery": p.battery,
                    "device_name": p.device_name,
                    "controller_brand": p.controller_brand,
                    "controller_type": p.controller_type,
                    "has_pt": p.has_pt,
                    "has_tke": p.has_tke,
                    "has_tkq": p.has_tkq,
                    "has_sam": p.has_sam,
                    "is_exp": p.is_exp,
                    "is_active": p.is_active,
                }
                for p in res.pumps
            ],
        })

    json_payload = json.dumps(serialized, ensure_ascii=False)
    safe_json = json_payload.replace("<", "\\u003c").replace(">", "\\u003e")
    rendered_html = HTML_TEMPLATE.replace("DATA_PLACEHOLDER", safe_json)

    target_path.write_text(rendered_html, encoding="utf-8")
    return target_path
