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
    this._showLogs = true;
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
          color: var(--primary-text-color, #212121);
          background-color: var(--primary-background-color, #fafafa);
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
          background: linear-gradient(135deg, #0288d1, #00acc1);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        .badge-version {
          background: rgba(2, 136, 209, 0.12);
          color: #0288d1;
          font-size: 11px;
          padding: 2px 8px;
          border-radius: 12px;
          border: 1px solid rgba(2, 136, 209, 0.3);
          font-weight: 700;
        }

        /* Boutons header */
        .header-actions {
          display: flex;
          gap: 12px;
          align-items: center;
          flex-wrap: wrap;
        }
        .search-input {
          background: var(--card-background-color, #ffffff);
          border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.15));
          color: var(--primary-text-color, #212121);
          padding: 8px 16px;
          border-radius: 8px;
          outline: none;
          font-size: 14px;
          min-width: 220px;
        }
        .btn {
          background: linear-gradient(135deg, #0288d1, #00acc1);
          color: #ffffff;
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
          background: var(--secondary-background-color, rgba(125, 125, 125, 0.1));
          border: 1px solid var(--divider-color, rgba(125, 125, 125, 0.2));
          color: var(--primary-text-color, #212121);
        }
        .btn-secondary:hover {
          background: var(--divider-color, rgba(125, 125, 125, 0.2));
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
          background: var(--card-background-color, #ffffff);
          border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.08));
          border-radius: 12px;
          padding: 16px 20px;
          display: flex;
          align-items: center;
          gap: 16px;
          box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,0.06));
        }
        .stat-icon {
          font-size: 28px;
          width: 48px;
          height: 48px;
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(2, 136, 209, 0.12);
          color: #0288d1;
        }
        .stat-val {
          font-size: 22px;
          font-weight: 700;
          color: var(--primary-text-color, #212121);
        }
        .stat-label {
          font-size: 12px;
          color: var(--secondary-text-color, #757575);
        }

        /* Cartes d'appareils */
        .cards-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
          gap: 20px;
        }
        .card {
          background: var(--card-background-color, #ffffff);
          border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.1));
          border-radius: 14px;
          padding: 20px;
          box-shadow: var(--ha-card-box-shadow, 0 4px 14px rgba(0,0,0,0.08));
          display: flex;
          flex-direction: column;
          gap: 16px;
          position: relative;
          transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }
        .card.ota-active {
          border-color: #0288d1;
          box-shadow: 0 0 18px rgba(2, 136, 209, 0.28);
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
          color: var(--primary-text-color, #212121);
        }
        .card-subtitle {
          font-size: 12px;
          color: var(--secondary-text-color, #757575);
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
        .badge-on { background: rgba(76, 175, 80, 0.15); color: #2e7d32; border: 1px solid rgba(76, 175, 80, 0.35); }
        .badge-off { background: var(--secondary-background-color, rgba(125, 125, 125, 0.1)); color: var(--secondary-text-color, #616161); border: 1px solid var(--divider-color, rgba(125, 125, 125, 0.2)); }
        .badge-unavail { background: rgba(244, 67, 54, 0.15); color: #c62828; border: 1px solid rgba(244, 67, 54, 0.35); }
        .badge-battery { background: rgba(255, 152, 0, 0.15); color: #e65100; border: 1px solid rgba(255, 152, 0, 0.3); }
        .badge-lqi { background: rgba(33, 150, 243, 0.15); color: #0277bd; border: 1px solid rgba(33, 150, 243, 0.3); }

        /* Bandeau Firmware */
        .firmware-banner {
          background: rgba(255, 152, 0, 0.1);
          border: 1px solid rgba(255, 152, 0, 0.35);
          border-radius: 8px;
          padding: 10px 12px;
          display: flex;
          flex-direction: column;
          gap: 8px;
          font-size: 12px;
          color: var(--primary-text-color, #212121);
        }
        .firmware-banner.in-progress {
          background: rgba(2, 136, 209, 0.1);
          border-color: rgba(2, 136, 209, 0.4);
        }
        .fw-top-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 8px;
        }
        .fw-info { display: flex; flex-direction: column; gap: 2px; }
        .fw-pct-badge {
          font-family: monospace;
          font-size: 12px;
          font-weight: 700;
          color: #0277bd;
          background: rgba(2, 136, 209, 0.12);
          padding: 2px 8px;
          border-radius: 6px;
          border: 1px solid rgba(2, 136, 209, 0.35);
        }
        .fw-progress-track {
          width: 100%;
          height: 8px;
          background: var(--divider-color, rgba(0, 0, 0, 0.12));
          border-radius: 4px;
          overflow: hidden;
          position: relative;
        }
        .fw-progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #0288d1, #00acc1, #43a047);
          border-radius: 4px;
          transition: width 0.4s ease;
        }
        .fw-progress-fill.indeterminate {
          width: 40%;
          position: absolute;
          animation: fw-shimmer 1.8s infinite ease-in-out;
        }
        @keyframes fw-shimmer {
          0% { left: -40%; }
          50% { left: 50%; }
          100% { left: 100%; }
        }
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

        /* Encadré Astuce ZHA */
        .zha-hint-box {
          background: rgba(2, 136, 209, 0.08);
          border: 1px solid rgba(2, 136, 209, 0.35);
          border-radius: 8px;
          padding: 10px 12px;
          font-size: 12px;
          color: var(--primary-text-color, #1a237e);
          line-height: 1.45;
        }
        .zha-hint-box strong {
          color: #0277bd;
        }

        /* BLOC OTA KEEP-AWAKE */
        .ota-box {
          background: var(--secondary-background-color, rgba(0, 0, 0, 0.03));
          border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.08));
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
          color: var(--primary-color, #0288d1);
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
          background: rgba(2, 136, 209, 0.08);
          border: 1px solid rgba(2, 136, 209, 0.3);
          border-radius: 6px;
          padding: 8px 12px;
          color: var(--primary-text-color, #212121);
        }
        .ota-timer-text {
          font-family: monospace;
          font-size: 15px;
          font-weight: 800;
          color: #0277bd;
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
          color: var(--primary-text-color, #37474f);
        }
        .slider-val-tag {
          color: #0288d1;
          font-family: monospace;
          font-weight: 700;
        }
        .range-slider {
          -webkit-appearance: none;
          width: 100%;
          height: 6px;
          border-radius: 3px;
          background: var(--divider-color, rgba(0, 0, 0, 0.15));
          outline: none;
        }
        .range-slider::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #0288d1;
          cursor: pointer;
          box-shadow: 0 0 6px rgba(2, 136, 209, 0.5);
        }

        /* Pied de carte */
        .card-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-top: 10px;
          border-top: 1px solid var(--divider-color, rgba(0, 0, 0, 0.08));
          font-size: 12px;
        }
        .sentinel-summary {
          color: var(--secondary-text-color, #757575);
          font-size: 11px;
        }
        .card-actions {
          display: flex;
          gap: 8px;
        }
        .icon-btn {
          background: var(--secondary-background-color, rgba(125, 125, 125, 0.1));
          border: 1px solid var(--divider-color, rgba(125, 125, 125, 0.2));
          color: var(--primary-text-color, #212121);
          padding: 6px 10px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 12px;
          font-weight: 500;
        }
        .icon-btn:hover {
          background: var(--divider-color, rgba(125, 125, 125, 0.2));
        }
        .icon-btn.btn-del:hover {
          background: rgba(244, 67, 54, 0.15);
          border-color: rgba(244, 67, 54, 0.35);
          color: #c62828;
        }
        .icon-btn.btn-burst-ota {
          border-color: rgba(230, 81, 0, 0.4);
          color: #e65100;
        }
        .icon-btn.btn-burst-ota:hover {
          background: rgba(230, 81, 0, 0.12);
        }
        .icon-btn.btn-burst-ota.bursting {
          background: rgba(230, 81, 0, 0.25);
          border-color: #e65100;
          font-weight: 700;
        }

        /* Tiroir des Logs en direct */
        .logs-section {
          margin-top: 28px;
          background: var(--card-background-color, #ffffff);
          border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.1));
          border-radius: 12px;
          padding: 16px 20px;
          color: var(--primary-text-color, #212121);
        }
        .logs-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          cursor: pointer;
        }
        .logs-list {
          margin-top: 12px;
          max-height: 220px;
          overflow-y: auto;
          font-family: monospace;
          font-size: 12px;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .log-item {
          padding: 6px 10px;
          border-radius: 6px;
          background: var(--secondary-background-color, rgba(0, 0, 0, 0.04));
          display: flex;
          gap: 12px;
          color: var(--primary-text-color, #212121);
        }
        .log-time { color: var(--secondary-text-color, #757575); }
        .log-msg.success { color: #2e7d32; font-weight: 600; }
        .log-msg.warning { color: #e65100; font-weight: 600; }
        .log-msg.info { color: #0277bd; font-weight: 600; }
        .log-msg.debug { color: var(--primary-text-color, #37474f); }

        /* MODAL */
        .modal-overlay {
          position: fixed;
          top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0, 0, 0, 0.65);
          backdrop-filter: blur(4px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 9999;
          padding: 20px;
        }
        .modal-card {
          background: var(--card-background-color, #ffffff);
          border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.15));
          border-radius: 14px;
          max-width: 540px;
          width: 100%;
          max-height: 90vh;
          overflow-y: auto;
          padding: 24px;
          display: flex;
          flex-direction: column;
          gap: 16px;
          box-shadow: 0 10px 30px rgba(0,0,0,0.3);
          color: var(--primary-text-color, #212121);
        }
        .form-group {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .form-label {
          font-size: 13px;
          font-weight: 600;
          color: var(--primary-text-color, #37474f);
        }
        .form-input, .form-select {
          background: var(--secondary-background-color, rgba(0, 0, 0, 0.04));
          border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.15));
          color: var(--primary-text-color, #212121);
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
          color: var(--primary-text-color, #212121);
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
              <span class="badge-version">v1.2.5 • ⚡ DÉFIBRILLATEUR OTA</span>
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
            <div class="stat-val" id="statProtected">${this._rules.length}</div>
            <div class="stat-label">Appareils protégés</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">🚀</div>
          <div>
            <div class="stat-val" id="statActiveSessions">${activeOtaCount}</div>
            <div class="stat-label">Sessions OTA actives</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">⚡</div>
          <div>
            <div class="stat-val" id="statPingsSent">${totalPings}</div>
            <div class="stat-label">Pings de maintien envoyés</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">📦</div>
          <div>
            <div class="stat-val" id="statUpdatesAvailable">${updatesAvailableCount}</div>
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
            <div style="display:flex; align-items:center; gap:8px;">
              <h3 style="margin:0;">📜 Journal en direct des Pings & Sessions OTA</h3>
              <span style="font-size:11px; background:rgba(46, 125, 50, 0.15); color:#2e7d32; border:1px solid rgba(46, 125, 50, 0.35); border-radius:10px; padding:2px 8px; font-weight:700;">🟢 En direct</span>
            </div>
            <div style="display:flex; gap:6px;">
              <button class="btn btn-secondary" style="padding:4px 8px; font-size:11px;" id="btnClearLogsData">🧹 Vider</button>
              <button class="btn btn-secondary" style="padding:4px 8px; font-size:11px;" id="btnClearLogsView">Masquer</button>
            </div>
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
          <div class="firmware-banner ${enrich.in_progress ? "in-progress" : ""}">
            <div class="fw-top-row">
              <div class="fw-info">
                <strong>${enrich.in_progress ? "⏳ Transfert OTA en cours..." : `🚀 Firmware v${enrich.latest_version || "disponible"}`}</strong>
                <span>Installé : v${enrich.installed_version || "inconnue"}${enrich.latest_version ? ` → v${enrich.latest_version}` : ""}</span>
              </div>
              ${
                enrich.in_progress
                  ? `
                <span class="fw-pct-badge" data-rule-id="${rId}">
                  ${enrich.update_percentage !== null ? `${enrich.update_percentage}%` : "Préparation..."}
                </span>
              `
                  : `
                <button class="fw-btn btn-install-ota" data-rule-id="${rId}" data-update-id="${enrich.update_entity_id}">
                  Lancer MAJ & Maintien
                </button>
              `
              }
            </div>

            ${
              enrich.in_progress
                ? `
              <div class="fw-progress-track">
                <div
                  class="fw-progress-fill ${enrich.update_percentage === null ? "indeterminate" : ""}"
                  data-rule-id="${rId}"
                  style="width: ${enrich.update_percentage !== null ? Math.max(2, enrich.update_percentage) : 40}%;"
                ></div>
              </div>
            `
                : ""
            }
          </div>
          <div class="zha-hint-box">
            💡 <strong>Important pour démarrer l'OTA (ZHA)</strong> : Dès que la fenêtre affiche <em>« Preparing »</em>, appuyez <strong>1 fois brièvement sur le bouton du capteur</strong> (ou passez la main devant le radar) pour déclencher son réveil radio initial et engager le transfert du firmware !
          </div>
        `
            : ""
        }

        <!-- BLOC OTA KEEP-AWAKE -->
        <div class="ota-box">
          <div class="ota-header-row">
            <span class="ota-title">⚡ DÉFIBRILLATEUR OTA (KEEP-AWAKE)</span>
            ${isActive ? `<span style="font-size:11px; color:#0288d1; font-weight:700;">DÉFIBRILLATION ACTIVE</span>` : ""}
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
                <div>Temps restant : <span class="ota-timer-text timer-display" data-rule-id="${rId}">${this._formatTime(remaining)}</span></div>
                <div style="font-size:11px; color:var(--secondary-text-color, #757575); margin-top:2px;">
                  Dernier ping : <span class="last-ping-display" data-rule-id="${rId}">${session.last_ping_time_str || "Aucun"}</span>
                </div>
              </div>
              <div style="display:flex; gap:6px; align-items:center;">
                <button class="icon-btn btn-extend-ota" data-rule-id="${rId}" title="Prolonger la session de 15 minutes">
                  ➕ 15 min
                </button>
                <button class="icon-btn btn-burst-ota ${session.is_bursting ? "bursting" : ""}" data-rule-id="${rId}" title="Envoyer 1 ping/seconde pendant 15s pour réveiller le capteur en phase Preparing">
                  ${session.is_bursting ? "🔥 Salve..." : "🔥 Salve 15s"}
                </button>
                <button class="icon-btn btn-ping-now" data-rule-id="${rId}" title="Envoyer un ping immédiat">
                  ⚡ Ping (${session.ping_count || 0})
                </button>
              </div>
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
      on_ota_failure: "keep_alive",
      on_ota_timeout: "auto_extend",
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

          <h3 style="margin-bottom:0; color:#0288d1; font-size:14px;">Paramètres OTA Keep-Awake</h3>

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
            <label for="modalAutoOta">Activer automatiquement le Keep-Awake dès qu'une mise à jour démarre</label>
          </div>

          <div class="form-group">
            <label class="form-label">Comportement si la mise à jour échoue</label>
            <select class="form-select" id="modalOnOtaFailure">
              <option value="keep_alive" ${r.on_ota_failure === "keep_alive" || !r.on_ota_failure ? "selected" : ""}>Maintenir le défibrillateur actif pour relancer (Recommandé)</option>
              <option value="stop" ${r.on_ota_failure === "stop" ? "selected" : ""}>Arrêter immédiatement le défibrillateur (économise la batterie)</option>
              <option value="retry" ${r.on_ota_failure === "retry" ? "selected" : ""}>Relancer automatiquement l'OTA (max 2 fois)</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">Comportement si le minuteur expire pendant l'OTA</label>
            <select class="form-select" id="modalOnOtaTimeout">
              <option value="auto_extend" ${r.on_ota_timeout === "auto_extend" || !r.on_ota_timeout ? "selected" : ""}>Prolonger de +15 min si toujours en cours (Recommandé)</option>
              <option value="stop" ${r.on_ota_timeout === "stop" ? "selected" : ""}>Arrêter strictement à l'échéance du temps</option>
            </select>
          </div>

          <h3 style="margin-bottom:0; color:#0288d1; font-size:14px;">Paramètres Proxy Sentinelle</h3>

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
    let needsFullRender = false;
    let activeOtaCount = 0;
    let totalPings = 0;
    let updatesAvailableCount = 0;

    for (const rule of this._rules) {
      const rId = rule.rule_id || rule.source_entity;
      const remaining = this._localRemaining[rId] || 0;
      const session = rule.ota_session || {};
      const enrich = rule.device_enrichment || {};

      if (session.active) activeOtaCount++;
      totalPings += session.ping_count || 0;
      if (enrich.update_available) updatesAvailableCount++;

      const card = this.shadowRoot.querySelector(`.card[data-rule-id="${rId}"]`);
      if (card) {
        const currentlyActive = card.classList.contains("ota-active");
        if (currentlyActive !== !!session.active) {
          needsFullRender = true;
          break;
        }
      }

      const timerEl = this.shadowRoot.querySelector(`.timer-display[data-rule-id="${rId}"]`);
      if (timerEl) {
        timerEl.textContent = this._formatTime(remaining);
      }

      const lastPingEl = this.shadowRoot.querySelector(`.last-ping-display[data-rule-id="${rId}"]`);
      if (lastPingEl) {
        lastPingEl.textContent = session.last_ping_time_str || "Aucun";
      }

      const pingBtn = this.shadowRoot.querySelector(`.btn-ping-now[data-rule-id="${rId}"]`);
      if (pingBtn && !pingBtn.dataset.clicking) {
        pingBtn.textContent = `⚡ Ping (${session.ping_count || 0})`;
      }

      const burstBtn = this.shadowRoot.querySelector(`.btn-burst-ota[data-rule-id="${rId}"]`);
      if (burstBtn) {
        burstBtn.textContent = session.is_bursting ? "🔥 Salve..." : "🔥 Salve 15s";
        if (session.is_bursting) {
          burstBtn.classList.add("bursting");
        } else {
          burstBtn.classList.remove("bursting");
        }
      }

      // Update progress bar & percentage badge if in_progress
      const pctBadge = this.shadowRoot.querySelector(`.fw-pct-badge[data-rule-id="${rId}"]`);
      if (pctBadge) {
        pctBadge.textContent = enrich.update_percentage !== null ? `${enrich.update_percentage}%` : "Préparation...";
      }

      const progressFill = this.shadowRoot.querySelector(`.fw-progress-fill[data-rule-id="${rId}"]`);
      if (progressFill) {
        if (enrich.update_percentage !== null) {
          progressFill.classList.remove("indeterminate");
          progressFill.style.width = `${Math.max(2, enrich.update_percentage)}%`;
        } else {
          progressFill.classList.add("indeterminate");
          progressFill.style.width = "40%";
        }
      }
    }

    // Live update top stat counters
    const statProt = this.shadowRoot.getElementById("statProtected");
    if (statProt) statProt.textContent = this._rules.length;
    const statAct = this.shadowRoot.getElementById("statActiveSessions");
    if (statAct) statAct.textContent = activeOtaCount;
    const statPings = this.shadowRoot.getElementById("statPingsSent");
    if (statPings) statPings.textContent = totalPings;
    const statUpd = this.shadowRoot.getElementById("statUpdatesAvailable");
    if (statUpd) statUpd.textContent = updatesAvailableCount;

    // Live update logs list
    const logsListEl = this.shadowRoot.querySelector(".logs-list");
    if (logsListEl) {
      if (this._logs.length === 0) {
        logsListEl.innerHTML = `<div style="color:#78909c;">Aucune activité récente.</div>`;
      } else {
        logsListEl.innerHTML = this._logs
          .map(
            (l) => `
          <div class="log-item">
            <span class="log-time">[${l.time_str}]</span>
            <span class="log-msg ${l.level}">${l.message}</span>
          </div>
        `
          )
          .join("");
      }
    }

    if (needsFullRender && !this._modalOpen) {
      this.render();
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
    const btnClearLogsData = this.shadowRoot.getElementById("btnClearLogsData");
    if (btnClearLogsData) {
      btnClearLogsData.onclick = () => {
        this._apiCall("clear_logs", {});
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

    // Ping immédiat avec retour visuel instantané
    this.shadowRoot.querySelectorAll(".btn-ping-now").forEach((btn) => {
      btn.onclick = () => {
        const rId = btn.dataset.ruleId;
        btn.dataset.clicking = "true";
        btn.textContent = "✅ Envoyé !";
        btn.style.borderColor = "#2e7d32";
        btn.style.color = "#2e7d32";
        setTimeout(() => {
          delete btn.dataset.clicking;
          btn.style.borderColor = "";
          btn.style.color = "";
        }, 1200);
        this._apiCall("ping_now", { rule_id: rId });
      };
    });

    // Salve rapide 15s (1 ping / sec)
    this.shadowRoot.querySelectorAll(".btn-burst-ota").forEach((btn) => {
      btn.onclick = () => {
        const rId = btn.dataset.ruleId;
        btn.textContent = "🔥 Salve...";
        this._apiCall("burst_ota", { rule_id: rId, seconds: 15 });
      };
    });

    // Prolonger session OTA de 15 min
    this.shadowRoot.querySelectorAll(".btn-extend-ota").forEach((btn) => {
      btn.onclick = () => {
        const rId = btn.dataset.ruleId;
        this._apiCall("extend_ota", { rule_id: rId, minutes: 15 });
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
        const onOtaFailure = this.shadowRoot.getElementById("modalOnOtaFailure")
          ? this.shadowRoot.getElementById("modalOnOtaFailure").value
          : "keep_alive";
        const onOtaTimeout = this.shadowRoot.getElementById("modalOnOtaTimeout")
          ? this.shadowRoot.getElementById("modalOnOtaTimeout").value
          : "auto_extend";
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
          on_ota_failure: onOtaFailure,
          on_ota_timeout: onOtaTimeout,
        });

        this._closeModal();
      };
    }
  }
}

customElements.define("domolink-keep-active-panel", DomolinkKeepActivePanel);
