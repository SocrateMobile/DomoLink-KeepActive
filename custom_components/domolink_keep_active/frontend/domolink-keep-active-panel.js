/**
 * DomoLink KeepActive - Custom Panel for Home Assistant
 * Modern glassmorphism dashboard with OTA Keep-Awake engine & Full CRUD management.
 */

class DomolinkKeepActivePanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._rules = [];
    this._logs = [];
    this._availableEntities = [];
    this._searchQuery = "";
    this._showLogs = false;
    this._modalOpen = false;
    this._editingRule = null;
    this._pollTimer = null;
    this._localRemaining = {};
  }

  set hass(hass) {
    const isFirst = !this._hass;
    this._hass = hass;
    if (isFirst) {
      this._fetchData();
      this._startPolling();
    }
  }

  connectedCallback() {
    this._startPolling();
    this.render();
  }

  disconnectedCallback() {
    this._stopPolling();
  }

  _startPolling() {
    this._stopPolling();
    this._pollTimer = setInterval(() => {
      this._fetchData(false);
      this._updateCountdowns();
    }, 2000);
  }

  _stopPolling() {
    if (this._pollTimer) {
      clearInterval(this._pollTimer);
      this._pollTimer = null;
    }
  }

  _updateCountdowns() {
    let hasActive = false;
    for (const rule of this._rules) {
      const rId = rule.rule_id || rule.source_entity;
      const session = rule.ota_session;
      if (session && session.active) {
        hasActive = true;
        if (this._localRemaining[rId] === undefined) {
          this._localRemaining[rId] = session.remaining_seconds;
        } else if (this._localRemaining[rId] > 0) {
          this._localRemaining[rId] -= 2;
        }
      } else {
        delete this._localRemaining[rId];
      }
    }
    if (hasActive) {
      this._updateOtaElements();
    }
  }

  async _fetchData(fullRender = true) {
    if (!this._hass) return;
    try {
      const res = await this._hass.fetchWithAuth("/api/domolink_keep_active/data");
      if (res.ok) {
        const data = await res.json();
        this._rules = data.rules || [];
        this._logs = data.logs || [];
        this._availableEntities = data.available_entities || [];
        // Sync remaining
        for (const rule of this._rules) {
          const rId = rule.rule_id || rule.source_entity;
          if (rule.ota_session && rule.ota_session.active) {
            this._localRemaining[rId] = rule.ota_session.remaining_seconds;
          }
        }
        if (fullRender) {
          this.render();
        } else {
          this._updateOtaElements();
        }
      }
    } catch (e) {
      console.debug("[DomoLink KeepActive] Erreur chargement données:", e);
    }
  }

  async _apiCall(action, payload = {}) {
    if (!this._hass) return;
    try {
      const res = await this._hass.fetchWithAuth(`/api/domolink_keep_active/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      await this._fetchData(true);
      return data;
    } catch (e) {
      alert("Erreur: " + (e.message || e));
    }
  }

  _formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }

  _openModal(rule = null) {
    this._editingRule = rule;
    this._modalOpen = true;
    this.render();
  }

  _closeModal() {
    this._editingRule = null;
    this._modalOpen = false;
    this.render();
  }

  render() {
    const filteredRules = this._rules.filter((r) => {
      const q = this._searchQuery.toLowerCase();
      const name = (r.name || "").toLowerCase();
      const source = (r.source_entity || "").toLowerCase();
      return name.includes(q) || source.includes(q);
    });

    const activeOtaCount = this._rules.filter((r) => r.ota_session && r.ota_session.active).length;
    const totalPings = this._rules.reduce((acc, r) => acc + ((r.ota_session && r.ota_session.ping_count) || 0), 0);
    const updatesAvailableCount = this._rules.filter((r) => r.device_enrichment && r.device_enrichment.update_available).length;

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          color: var(--primary-text-color, #e1e7ec);
          background-color: var(--primary-background-color, #101418);
          font-family: var(--paper-font-body1_-_font-family, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif);
          min-height: 100vh;
          box-sizing: border-box;
          padding: 24px;
        }

        /* En-tête */
        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          gap: 16px;
          margin-bottom: 24px;
        }
        .header-title-box {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .header-title-box h1 {
          margin: 0;
          font-size: 26px;
          font-weight: 700;
          background: linear-gradient(135deg, #0288d1, #26c6da);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        .badge-version {
          background: rgba(38, 198, 218, 0.15);
          color: #26c6da;
          font-size: 11px;
          padding: 2px 8px;
          border-radius: 12px;
          border: 1px solid rgba(38, 198, 218, 0.3);
          font-weight: 600;
        }

        /* Boutons header */
        .header-actions {
          display: flex;
          gap: 12px;
          align-items: center;
          flex-wrap: wrap;
        }
        .search-input {
          background: var(--card-background-color, #1a2026);
          border: 1px solid rgba(255, 255, 255, 0.1);
          color: var(--primary-text-color, #fff);
          padding: 8px 16px;
          border-radius: 8px;
          outline: none;
          font-size: 14px;
          min-width: 220px;
        }
        .btn {
          background: linear-gradient(135deg, #0288d1, #00acc1);
          color: #fff;
          border: none;
          padding: 9px 18px;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 600;
          font-size: 14px;
          display: inline-flex;
          align-items: center;
          gap: 8px;
          transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .btn:hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(2, 136, 209, 0.35);
        }
        .btn-secondary {
          background: rgba(255, 255, 255, 0.08);
          border: 1px solid rgba(255, 255, 255, 0.15);
          color: var(--primary-text-color, #fff);
        }
        .btn-secondary:hover {
          background: rgba(255, 255, 255, 0.15);
          box-shadow: none;
        }

        /* Statistiques */
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 16px;
          margin-bottom: 28px;
        }
        .stat-card {
          background: var(--card-background-color, #191f26);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 12px;
          padding: 16px 20px;
          display: flex;
          align-items: center;
          gap: 16px;
          box-shadow: 0 4px 16px rgba(0,0,0,0.2);
        }
        .stat-icon {
          font-size: 28px;
          width: 48px;
          height: 48px;
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(2, 136, 209, 0.15);
          color: #26c6da;
        }
        .stat-val {
          font-size: 22px;
          font-weight: 700;
        }
        .stat-label {
          font-size: 12px;
          color: var(--secondary-text-color, #8e9ca8);
        }

        /* Cartes d'appareils */
        .cards-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
          gap: 20px;
        }
        .card {
          background: var(--card-background-color, #181e25);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 14px;
          padding: 20px;
          box-shadow: 0 6px 20px rgba(0,0,0,0.25);
          display: flex;
          flex-direction: column;
          gap: 16px;
          position: relative;
          transition: border-color 0.2s ease;
        }
        .card.ota-active {
          border-color: #0288d1;
          box-shadow: 0 0 20px rgba(2, 136, 209, 0.25);
        }

        /* Entête de carte */
        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 12px;
        }
        .card-title-box {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .card-title {
          font-size: 17px;
          font-weight: 600;
          margin: 0;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .card-subtitle {
          font-size: 12px;
          color: var(--secondary-text-color, #8e9ca8);
          font-family: monospace;
        }

        /* Badges de statuts */
        .badges-row {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }
        .badge {
          font-size: 11px;
          font-weight: 600;
          padding: 3px 8px;
          border-radius: 6px;
          display: inline-flex;
          align-items: center;
          gap: 4px;
        }
        .badge-on { background: rgba(76, 175, 80, 0.15); color: #66bb6a; border: 1px solid rgba(76, 175, 80, 0.3); }
        .badge-off { background: rgba(255, 255, 255, 0.05); color: #b0bec5; border: 1px solid rgba(255, 255, 255, 0.1); }
        .badge-unavail { background: rgba(244, 67, 54, 0.15); color: #ef5350; border: 1px solid rgba(244, 67, 54, 0.3); }
        .badge-battery { background: rgba(255, 152, 0, 0.12); color: #ffa726; border: 1px solid rgba(255, 152, 0, 0.25); }
        .badge-lqi { background: rgba(33, 150, 243, 0.12); color: #42a5f5; border: 1px solid rgba(33, 150, 243, 0.25); }

        /* Bandeau Firmware */
        .firmware-banner {
          background: rgba(255, 152, 0, 0.08);
          border: 1px solid rgba(255, 152, 0, 0.25);
          border-radius: 8px;
          padding: 10px 12px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 12px;
        }
        .fw-info { display: flex; flex-direction: column; gap: 2px; }
        .fw-btn {
          background: #f57c00;
          color: #fff;
          font-size: 11px;
          padding: 5px 10px;
          border-radius: 6px;
          border: none;
          cursor: pointer;
          font-weight: 600;
        }

        /* BLOC OTA KEEP-AWAKE */
        .ota-box {
          background: rgba(0, 0, 0, 0.22);
          border: 1px solid rgba(255, 255, 255, 0.07);
          border-radius: 10px;
          padding: 14px;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .ota-header-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .ota-title {
          font-size: 13px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: #26c6da;
          display: flex;
          align-items: center;
          gap: 6px;
        }

        /* Grand bouton switch OTA */
        .ota-toggle-btn {
          width: 100%;
          padding: 11px;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 700;
          border: none;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          transition: all 0.2s ease;
        }
        .ota-toggle-btn.btn-start {
          background: linear-gradient(135deg, #1e88e5, #00897b);
          color: #ffffff;
        }
        .ota-toggle-btn.btn-stop {
          background: linear-gradient(135deg, #e53935, #d81b60);
          color: #ffffff;
          box-shadow: 0 0 14px rgba(229, 57, 53, 0.4);
          animation: pulse 2s infinite;
        }
        @keyframes pulse {
          0% { box-shadow: 0 0 0 0 rgba(229, 57, 53, 0.4); }
          70% { box-shadow: 0 0 0 10px rgba(229, 57, 53, 0); }
          100% { box-shadow: 0 0 0 0 rgba(229, 57, 53, 0); }
        }

        /* Compte à rebours et statut OTA actif */
        .ota-live-status {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 12px;
          background: rgba(2, 136, 209, 0.12);
          border: 1px solid rgba(2, 136, 209, 0.3);
          border-radius: 6px;
          padding: 8px 12px;
        }
        .ota-timer-text {
          font-family: monospace;
          font-size: 15px;
          font-weight: 700;
          color: #4fc3f7;
        }

        /* Sliders */
        .slider-group {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .slider-label-row {
          display: flex;
          justify-content: space-between;
          font-size: 12px;
          font-weight: 600;
          color: var(--secondary-text-color, #b0bec5);
        }
        .slider-val-tag {
          color: #26c6da;
          font-family: monospace;
        }
        .range-slider {
          -webkit-appearance: none;
          width: 100%;
          height: 6px;
          border-radius: 3px;
          background: rgba(255, 255, 255, 0.12);
          outline: none;
        }
        .range-slider::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #26c6da;
          cursor: pointer;
          box-shadow: 0 0 6px rgba(38, 198, 218, 0.6);
        }

        /* Pied de carte */
        .card-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-top: 10px;
          border-top: 1px solid rgba(255, 255, 255, 0.06);
          font-size: 12px;
        }
        .sentinel-summary {
          color: var(--secondary-text-color, #78909c);
          font-size: 11px;
        }
        .card-actions {
          display: flex;
          gap: 8px;
        }
        .icon-btn {
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.1);
          color: var(--primary-text-color, #fff);
          padding: 6px 10px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 12px;
        }
        .icon-btn:hover {
          background: rgba(255, 255, 255, 0.12);
        }
        .icon-btn.btn-del:hover {
          background: rgba(244, 67, 54, 0.2);
          border-color: rgba(244, 67, 54, 0.4);
          color: #ef5350;
        }

        /* Tiroir des Logs en direct */
        .logs-section {
          margin-top: 28px;
          background: var(--card-background-color, #181e25);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 12px;
          padding: 16px 20px;
        }
        .logs-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          cursor: pointer;
        }
        .logs-list {
          margin-top: 12px;
          max-height: 200px;
          overflow-y: auto;
          font-family: monospace;
          font-size: 12px;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .log-item {
          padding: 4px 8px;
          border-radius: 4px;
          background: rgba(0, 0, 0, 0.2);
          display: flex;
          gap: 12px;
        }
        .log-time { color: #78909c; }
        .log-msg.success { color: #81c784; }
        .log-msg.warning { color: #ffb74d; }
        .log-msg.info { color: #64b5f6; }

        /* MODAL */
        .modal-overlay {
          position: fixed;
          top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0, 0, 0, 0.7);
          backdrop-filter: blur(4px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 9999;
          padding: 20px;
        }
        .modal-card {
          background: #1e2630;
          border: 1px solid rgba(255, 255, 255, 0.15);
          border-radius: 14px;
          max-width: 520px;
          width: 100%;
          max-height: 90vh;
          overflow-y: auto;
          padding: 24px;
          display: flex;
          flex-direction: column;
          gap: 16px;
          box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        .form-group {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .form-label {
          font-size: 13px;
          font-weight: 600;
          color: #b0bec5;
        }
        .form-input, .form-select {
          background: #141a20;
          border: 1px solid rgba(255, 255, 255, 0.12);
          color: #fff;
          padding: 9px 12px;
          border-radius: 6px;
          font-size: 14px;
          outline: none;
        }
        .form-checkbox-row {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 13px;
        }
        .modal-actions {
          display: flex;
          justify-content: flex-end;
          gap: 10px;
          margin-top: 12px;
        }
      </style>

      <div class="header">
        <div class="header-title-box">
          <img src="/domolink_keep_active_panel/icon.png" width="42" height="42" alt="DomoLink Defibrillator Icon" style="border-radius:10px; box-shadow:0 0 16px rgba(56, 189, 248, 0.45); border: 1px solid rgba(56, 189, 248, 0.4);" />
          <div>
            <h1 style="display:flex; align-items:center; gap:8px;">
              DomoLink KeepActive
              <span class="badge-version">⚡ DÉFIBRILLATEUR OTA</span>
            </h1>
            <div style="font-size:11px; color:#80deea; letter-spacing:0.8px; font-weight:600;">ANTI DEEP-SLEEP • SENTINELLE ZIGBEE</div>
          </div>
        </div>
        <div class="header-actions">
          <input
            type="text"
            class="search-input"
            placeholder="🔍 Filtrer les appareils..."
            value="${this._searchQuery}"
            id="searchInput"
          />
          <button class="btn btn-secondary" id="btnToggleLogs">
            📜 ${this._showLogs ? "Masquer les logs" : "Logs OTA"}
          </button>
          <button class="btn" id="btnAddDevice">
            ➕ Ajouter un appareil
          </button>
        </div>
      </div>

      <!-- Statistiques globales -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon">🛡️</div>
          <div>
            <div class="stat-val">${this._rules.length}</div>
            <div class="stat-label">Appareils protégés</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">🚀</div>
          <div>
            <div class="stat-val">${activeOtaCount}</div>
            <div class="stat-label">Sessions OTA actives</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">⚡</div>
          <div>
            <div class="stat-val">${totalPings}</div>
            <div class="stat-label">Pings de maintien envoyés</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">📦</div>
          <div>
            <div class="stat-val">${updatesAvailableCount}</div>
            <div class="stat-label">Mises à jour firmware détectées</div>
          </div>
        </div>
      </div>

      <!-- Grille des cartes -->
      <div class="cards-grid">
        ${
          filteredRules.length === 0
            ? `<div style="grid-column: 1/-1; text-align:center; padding: 48px; color:#78909c;">
                Aucun appareil configuré.<br><br>
                <button class="btn" id="btnEmptyAdd">➕ Ajouter votre premier appareil</button>
              </div>`
            : filteredRules.map((rule) => this._renderCard(rule)).join("")
        }
      </div>

      <!-- Tiroir des Logs -->
      ${
        this._showLogs
          ? `
        <div class="logs-section">
          <div class="logs-header">
            <h3 style="margin:0;">📜 Journal en direct des Pings & Sessions OTA</h3>
            <button class="btn btn-secondary" style="padding:4px 8px; font-size:11px;" id="btnClearLogsView">Masquer</button>
          </div>
          <div class="logs-list">
            ${
              this._logs.length === 0
                ? `<div style="color:#78909c;">Aucune activité récente.</div>`
                : this._logs
                    .map(
                      (l) => `
                  <div class="log-item">
                    <span class="log-time">[${l.time_str}]</span>
                    <span class="log-msg ${l.level}">${l.message}</span>
                  </div>
                `
                    )
                    .join("")
            }
          </div>
        </div>
      `
          : ""
      }

      <!-- Modal Ajouter / Modifier -->
      ${this._modalOpen ? this._renderModal() : ""}
    `;

    this._attachEvents();
  }

  _renderCard(rule) {
    const rId = rule.rule_id || rule.source_entity;
    const session = rule.ota_session || {};
    const isActive = session.active;
    const remaining = this._localRemaining[rId] !== undefined ? this._localRemaining[rId] : session.remaining_seconds || 0;
    const enrich = rule.device_enrichment || {};

    let stateClass = "badge-off";
    if (rule.source_state === "on") stateClass = "badge-on";
    else if (rule.source_state === "unavailable" || rule.source_state === "unknown") stateClass = "badge-unavail";

    return `
      <div class="card ${isActive ? "ota-active" : ""}" data-rule-id="${rId}">
        <div class="card-header">
          <div class="card-title-box">
            <h3 class="card-title">
              <span>${rule.platform === "switch" ? "🔌" : rule.platform === "sensor" ? "🌡️" : "📡"}</span>
              ${rule.name || rule.source_entity}
            </h3>
            <span class="card-subtitle">${rule.source_entity}</span>
          </div>
          <div class="badges-row">
            <span class="badge ${stateClass}">${rule.source_state}</span>
            ${enrich.battery_level !== null ? `<span class="badge badge-battery">🔋 ${enrich.battery_level}%</span>` : ""}
            ${enrich.linkquality !== null ? `<span class="badge badge-lqi">📶 ${enrich.linkquality} LQI</span>` : ""}
          </div>
        </div>

        ${
          enrich.update_available || enrich.in_progress
            ? `
          <div class="firmware-banner">
            <div class="fw-info">
              <strong>${enrich.in_progress ? "⏳ Transfert OTA en cours..." : `🚀 Firmware v${enrich.latest_version || "disponible"}`}</strong>
              <span>Installé : v${enrich.installed_version || "inconnue"}</span>
            </div>
            ${!enrich.in_progress ? `
              <button class="fw-btn btn-install-ota" data-rule-id="${rId}" data-update-id="${enrich.update_entity_id}">
                Lancer MAJ & Maintien
              </button>
            ` : ""}
          </div>
          <div style="background: rgba(2, 136, 209, 0.12); border: 1px solid rgba(2, 136, 209, 0.35); border-radius: 8px; padding: 10px 12px; font-size: 12px; color: #b3e5fc; line-height: 1.4;">
            💡 <strong>Important pour démarrer l'OTA (ZHA)</strong> : Dès que la fenêtre affiche <em>« Preparing »</em>, appuyez <strong>1 fois brièvement sur le bouton du capteur</strong> (ou passez la main devant le radar) pour déclencher son réveil radio initial et engager le transfert du firmware !
          </div>
        `
            : ""
        }

        <!-- BLOC OTA KEEP-AWAKE -->
        <div class="ota-box">
          <div class="ota-header-row">
            <span class="ota-title">⚡ DÉFIBRILLATEUR OTA (KEEP-AWAKE)</span>
            ${isActive ? `<span style="font-size:11px; color:#4fc3f7; font-weight:700;">DÉFIBRILLATION ACTIVE</span>` : ""}
          </div>

          <!-- Bouton Toggle Principal -->
          <button
            class="ota-toggle-btn ${isActive ? "btn-stop" : "btn-start"} toggle-ota-btn"
            data-rule-id="${rId}"
          >
            ${isActive ? "🛑 Arrêter la défibrillation" : "⚡ Activer le défibrillateur OTA"}
          </button>

          ${
            isActive
              ? `
            <div class="ota-live-status">
              <div>
                Temps restant : <span class="ota-timer-text timer-display" data-rule-id="${rId}">${this._formatTime(remaining)}</span>
              </div>
              <button class="icon-btn btn-ping-now" data-rule-id="${rId}" title="Envoyer un ping immédiat">
                ⚡ Ping (${session.ping_count || 0})
              </button>
            </div>
          `
              : ""
          }

          <!-- Slider 1 : Durée totale (10 min à 90 min) -->
          <div class="slider-group">
            <div class="slider-label-row">
              <span>Durée totale du maintien :</span>
              <span class="slider-val-tag dur-val" data-rule-id="${rId}">${rule.ota_duration || 30} min</span>
            </div>
            <input
              type="range"
              class="range-slider ota-dur-slider"
              min="10"
              max="90"
              step="1"
              value="${rule.ota_duration || 30}"
              data-rule-id="${rId}"
            />
          </div>

          <!-- Slider 2 : Intervalle de ping (1 s à 60 s) -->
          <div class="slider-group">
            <div class="slider-label-row">
              <span>Intervalle entre chaque ping :</span>
              <span class="slider-val-tag int-val" data-rule-id="${rId}">${rule.ping_interval || 5} s</span>
            </div>
            <input
              type="range"
              class="range-slider ota-int-slider"
              min="1"
              max="60"
              step="1"
              value="${rule.ping_interval || 5}"
              data-rule-id="${rId}"
            />
          </div>
        </div>

        <!-- Pied de carte -->
        <div class="card-footer">
          <div class="sentinel-summary">
            Maintien : ${rule.hold_duration}s | Grâce : ${rule.grace_period}s
          </div>
          <div class="card-actions">
            <button class="icon-btn btn-edit-rule" data-rule-id="${rId}">⚙️ Paramètres</button>
            <button class="icon-btn btn-del btn-del-rule" data-rule-id="${rId}">🗑️</button>
          </div>
        </div>
      </div>
    `;
  }

  _renderModal() {
    const isEdit = !!this._editingRule;
    const r = this._editingRule || {
      source_entity: "",
      name: "",
      hold_duration: 30,
      grace_period: 60,
      optimistic: true,
      ota_duration: 30,
      ping_interval: 5,
      ping_method: "auto",
      auto_ota_trigger: true,
    };

    return `
      <div class="modal-overlay" id="modalOverlay">
        <div class="modal-card">
          <h2 style="margin-top:0;">${isEdit ? "⚙️ Modifier l'appareil" : "➕ Ajouter un appareil"}</h2>

          <div class="form-group">
            <label class="form-label">Entité source Home Assistant</label>
            ${
              isEdit
                ? `<input type="text" class="form-input" id="modalSourceEntity" value="${r.source_entity}" disabled />`
                : `
                <select class="form-select" id="modalSourceEntity">
                  <option value="">-- Sélectionnez une entité --</option>
                  ${this._availableEntities
                    .map((e) => `<option value="${e.entity_id}">${e.name} (${e.entity_id})</option>`)
                    .join("")}
                </select>
              `
            }
          </div>

          <div class="form-group">
            <label class="form-label">Nom personnalisé</label>
            <input type="text" class="form-input" id="modalName" placeholder="Ex: Détecteur Salon" value="${r.name || ""}" />
          </div>

          <h3 style="margin-bottom:0; color:#26c6da; font-size:14px;">Paramètres OTA Keep-Awake</h3>

          <div class="form-group">
            <label class="form-label">Durée totale OTA (10 à 90 min) : <span id="modalDurVal">${r.ota_duration || 30} min</span></label>
            <input type="range" class="range-slider" id="modalOtaDur" min="10" max="90" step="1" value="${r.ota_duration || 30}" />
          </div>

          <div class="form-group">
            <label class="form-label">Intervalle de ping (1 à 60 s) : <span id="modalIntVal">${r.ping_interval || 5} s</span></label>
            <input type="range" class="range-slider" id="modalOtaInt" min="1" max="60" step="1" value="${r.ping_interval || 5}" />
          </div>

          <div class="form-group">
            <label class="form-label">Méthode de ping</label>
            <select class="form-select" id="modalPingMethod">
              <option value="auto" ${r.ping_method === "auto" ? "selected" : ""}>Automatique (Recommandé)</option>
              <option value="z2m_get" ${r.ping_method === "z2m_get" ? "selected" : ""}>Zigbee2MQTT (/get)</option>
              <option value="zha_ping" ${r.ping_method === "zha_ping" ? "selected" : ""}>ZHA Ping</option>
              <option value="ha_update" ${r.ping_method === "ha_update" ? "selected" : ""}>Home Assistant Update Entity</option>
            </select>
          </div>

          <div class="form-checkbox-row">
            <input type="checkbox" id="modalAutoOta" ${r.auto_ota_trigger ? "checked" : ""} />
            <label for="modalAutoOta">Activer automatiquement le Keep-Awake dès qu'une mise à jour firmware démarre</label>
          </div>

          <h3 style="margin-bottom:0; color:#26c6da; font-size:14px;">Paramètres Proxy Sentinelle</h3>

          <div style="display:flex; gap:12px;">
            <div class="form-group" style="flex:1;">
              <label class="form-label">Maintien actif (s)</label>
              <input type="number" class="form-input" id="modalHold" min="0" max="3600" value="${r.hold_duration}" />
            </div>
            <div class="form-group" style="flex:1;">
              <label class="form-label">Période de grâce (s)</label>
              <input type="number" class="form-input" id="modalGrace" min="0" max="3600" value="${r.grace_period}" />
            </div>
          </div>

          <div class="form-checkbox-row">
            <input type="checkbox" id="modalOptimistic" ${r.optimistic ? "checked" : ""} />
            <label for="modalOptimistic">Mode optimiste (retour d'état immédiat)</label>
          </div>

          <div class="modal-actions">
            <button class="btn btn-secondary" id="btnCancelModal">Annuler</button>
            <button class="btn" id="btnSaveModal">Enregistrer</button>
          </div>
        </div>
      </div>
    `;
  }

  _updateOtaElements() {
    for (const rule of this._rules) {
      const rId = rule.rule_id || rule.source_entity;
      const remaining = this._localRemaining[rId] || 0;
      const timerEl = this.shadowRoot.querySelector(`.timer-display[data-rule-id="${rId}"]`);
      if (timerEl) {
        timerEl.textContent = this._formatTime(remaining);
      }
    }
  }

  _attachEvents() {
    // Recherche
    const searchInput = this.shadowRoot.getElementById("searchInput");
    if (searchInput) {
      searchInput.oninput = (e) => {
        this._searchQuery = e.target.value;
        this.render();
      };
    }

    // Toggle logs
    const btnToggleLogs = this.shadowRoot.getElementById("btnToggleLogs");
    if (btnToggleLogs) {
      btnToggleLogs.onclick = () => {
        this._showLogs = !this._showLogs;
        this.render();
      };
    }
    const btnClearLogsView = this.shadowRoot.getElementById("btnClearLogsView");
    if (btnClearLogsView) {
      btnClearLogsView.onclick = () => {
        this._showLogs = false;
        this.render();
      };
    }

    // Bouton ajouter
    const btnAddDevice = this.shadowRoot.getElementById("btnAddDevice");
    if (btnAddDevice) btnAddDevice.onclick = () => this._openModal();
    const btnEmptyAdd = this.shadowRoot.getElementById("btnEmptyAdd");
    if (btnEmptyAdd) btnEmptyAdd.onclick = () => this._openModal();

    // Toggle OTA
    this.shadowRoot.querySelectorAll(".toggle-ota-btn").forEach((btn) => {
      btn.onclick = () => {
        const rId = btn.dataset.ruleId;
        const durSlider = this.shadowRoot.querySelector(`.ota-dur-slider[data-rule-id="${rId}"]`);
        const intSlider = this.shadowRoot.querySelector(`.ota-int-slider[data-rule-id="${rId}"]`);
        this._apiCall("toggle_ota", {
          rule_id: rId,
          duration: durSlider ? parseInt(durSlider.value) : 30,
          interval: intSlider ? parseInt(intSlider.value) : 5,
        });
      };
    });

    // Ping immédiat
    this.shadowRoot.querySelectorAll(".btn-ping-now").forEach((btn) => {
      btn.onclick = () => {
        const rId = btn.dataset.ruleId;
        this._apiCall("ping_now", { rule_id: rId });
      };
    });

    // Lancer MAJ et Maintien
    this.shadowRoot.querySelectorAll(".btn-install-ota").forEach((btn) => {
      btn.onclick = () => {
        const rId = btn.dataset.ruleId;
        const updId = btn.dataset.updateId;
        if (confirm("Lancer la mise à jour firmware et activer immédiatement le maintien éveillé Keep-Awake ?")) {
          this._apiCall("start_ota_update", { rule_id: rId, update_entity_id: updId });
        }
      };
    });

    // Sliders de durée
    this.shadowRoot.querySelectorAll(".ota-dur-slider").forEach((slider) => {
      const rId = slider.dataset.ruleId;
      const tag = this.shadowRoot.querySelector(`.dur-val[data-rule-id="${rId}"]`);
      slider.oninput = (e) => {
        if (tag) tag.textContent = `${e.target.value} min`;
      };
      slider.onchange = (e) => {
        const intSlider = this.shadowRoot.querySelector(`.ota-int-slider[data-rule-id="${rId}"]`);
        this._apiCall("update_ota_params", {
          rule_id: rId,
          duration: parseInt(e.target.value),
          interval: intSlider ? parseInt(intSlider.value) : 5,
        });
      };
    });

    // Sliders d'intervalle
    this.shadowRoot.querySelectorAll(".ota-int-slider").forEach((slider) => {
      const rId = slider.dataset.ruleId;
      const tag = this.shadowRoot.querySelector(`.int-val[data-rule-id="${rId}"]`);
      slider.oninput = (e) => {
        if (tag) tag.textContent = `${e.target.value} s`;
      };
      slider.onchange = (e) => {
        const durSlider = this.shadowRoot.querySelector(`.ota-dur-slider[data-rule-id="${rId}"]`);
        this._apiCall("update_ota_params", {
          rule_id: rId,
          duration: durSlider ? parseInt(durSlider.value) : 30,
          interval: parseInt(e.target.value),
        });
      };
    });

    // Modifier règle
    this.shadowRoot.querySelectorAll(".btn-edit-rule").forEach((btn) => {
      btn.onclick = () => {
        const rId = btn.dataset.ruleId;
        const rule = this._rules.find((r) => (r.rule_id || r.source_entity) === rId);
        if (rule) this._openModal(rule);
      };
    });

    // Supprimer règle
    this.shadowRoot.querySelectorAll(".btn-del-rule").forEach((btn) => {
      btn.onclick = () => {
        const rId = btn.dataset.ruleId;
        if (confirm(`Voulez-vous vraiment supprimer cet appareil (${rId}) de KeepActive ?`)) {
          this._apiCall("delete_rule", { rule_id: rId });
        }
      };
    });

    // Modal sliders readouts
    const modalOtaDur = this.shadowRoot.getElementById("modalOtaDur");
    const modalDurVal = this.shadowRoot.getElementById("modalDurVal");
    if (modalOtaDur && modalDurVal) {
      modalOtaDur.oninput = (e) => (modalDurVal.textContent = `${e.target.value} min`);
    }

    const modalOtaInt = this.shadowRoot.getElementById("modalOtaInt");
    const modalIntVal = this.shadowRoot.getElementById("modalIntVal");
    if (modalOtaInt && modalIntVal) {
      modalOtaInt.oninput = (e) => (modalIntVal.textContent = `${e.target.value} s`);
    }

    // Modal Annuler
    const btnCancelModal = this.shadowRoot.getElementById("btnCancelModal");
    if (btnCancelModal) btnCancelModal.onclick = () => this._closeModal();

    // Modal Enregistrer
    const btnSaveModal = this.shadowRoot.getElementById("btnSaveModal");
    if (btnSaveModal) {
      btnSaveModal.onclick = () => {
        const sourceEntity = this.shadowRoot.getElementById("modalSourceEntity").value.trim();
        if (!sourceEntity) {
          alert("Veuillez sélectionner une entité source.");
          return;
        }
        const name = this.shadowRoot.getElementById("modalName").value.trim();
        const otaDur = parseInt(this.shadowRoot.getElementById("modalOtaDur").value);
        const otaInt = parseInt(this.shadowRoot.getElementById("modalOtaInt").value);
        const pingMeth = this.shadowRoot.getElementById("modalPingMethod").value;
        const autoOta = this.shadowRoot.getElementById("modalAutoOta").checked;
        const hold = parseInt(this.shadowRoot.getElementById("modalHold").value);
        const grace = parseInt(this.shadowRoot.getElementById("modalGrace").value);
        const optimistic = this.shadowRoot.getElementById("modalOptimistic").checked;

        this._apiCall("save_rule", {
          rule_id: this._editingRule ? this._editingRule.rule_id || sourceEntity : sourceEntity,
          source_entity: sourceEntity,
          name: name,
          hold_duration: hold,
          grace_period: grace,
          optimistic: optimistic,
          ota_duration: otaDur,
          ping_interval: otaInt,
          ping_method: pingMeth,
          auto_ota_trigger: autoOta,
        });

        this._closeModal();
      };
    }
  }
}

customElements.define("domolink-keep-active-panel", DomolinkKeepActivePanel);
