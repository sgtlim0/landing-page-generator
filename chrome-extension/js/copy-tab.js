const CopyTab = {
  lastResult: null,
  progressInterval: null,

  init() {
    const tabBar = document.getElementById('copyResultTabs');
    if (tabBar) {
      tabBar.addEventListener('click', (e) => {
        const tab = e.target.closest('.result-tab');
        if (!tab) return;
        tabBar.querySelectorAll('.result-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const target = tab.dataset.tab;
        document.getElementById('copySectionsTab').style.display = target === 'copy' ? 'block' : 'none';
        document.getElementById('copyResearchTab').style.display = target === 'research' ? 'block' : 'none';
      });
    }

    const resultContainer = document.getElementById('copyResult');
    if (resultContainer) {
      resultContainer.addEventListener('click', (e) => {
        const header = e.target.closest('[data-action="toggle-section"]');
        if (header) {
          const body = header.nextElementSibling;
          if (body) body.classList.toggle('open');
          return;
        }

        const btn = e.target.closest('[data-action]');
        if (!btn) return;

        if (btn.dataset.action === 'copy-json') {
          this.copyJson(btn);
        } else if (btn.dataset.action === 'copy-text') {
          this.copyText(btn);
        } else if (btn.dataset.action === 'reset-copy') {
          this.reset();
        }
      });
    }
  },

  showProgress(show) {
    document.getElementById('copyProgress').classList.toggle('show', show);
  },

  updateProgress(pct, text) {
    document.getElementById('copyProgressFill').style.width = pct + '%';
    document.getElementById('copyProgressText').textContent = text;
  },

  showResult(show) {
    document.getElementById('copyResult').classList.toggle('show', show);
  },

  showError(msg) {
    const el = document.getElementById('copyError');
    el.textContent = msg;
    el.classList.add('show');
  },

  clearError() {
    document.getElementById('copyError').classList.remove('show');
  },

  async submit(payload) {
    const btn = document.getElementById('copySubmitBtn');
    btn.disabled = true;
    btn.textContent = 'Generating...';
    this.showProgress(true);
    this.clearError();
    this.showResult(false);

    let pct = 0;
    const steps = ['Analyzing product info...', 'Running research analysis...', 'Generating 13-section copy...', 'Finalizing...'];
    let stepIdx = 0;
    this.progressInterval = setInterval(() => {
      pct = Math.min(pct + (Math.random() * 5 + 2), 95);
      if (pct > 25 && stepIdx < 1) stepIdx = 1;
      if (pct > 50 && stepIdx < 2) stepIdx = 2;
      if (pct > 85 && stepIdx < 3) stepIdx = 3;
      this.updateProgress(pct, `${steps[stepIdx]} (${Math.round(pct)}%)`);
    }, 2000);

    try {
      const data = await Api.generateCopy(payload);
      clearInterval(this.progressInterval);
      this.progressInterval = null;

      this.lastResult = data;
      this.updateProgress(100, 'Complete!');

      setTimeout(() => {
        this.showProgress(false);
        this.showResult(true);
        this.renderResults(data);
      }, 500);
    } catch (err) {
      if (this.progressInterval) {
        clearInterval(this.progressInterval);
        this.progressInterval = null;
      }
      this.showProgress(false);
      this.showError(err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Generate Sales Copy (13 Sections)';
    }
  },

  renderResults(data) {
    const copyContainer = document.getElementById('copySectionsTab');
    let copyHtml = '';
    const copyData = data.copy || {};
    Object.keys(SECTION_NAMES).forEach(key => {
      if (copyData[key]) {
        copyHtml += renderSection(key, copyData[key]);
      }
    });
    copyContainer.innerHTML = copyHtml || '<p class="empty-msg">No copy data returned.</p>';

    const firstBody = copyContainer.querySelector('.section-body');
    if (firstBody) firstBody.classList.add('open');

    const researchContainer = document.getElementById('copyResearchTab');
    researchContainer.innerHTML = data.research
      ? renderResearch(data.research)
      : '<p class="empty-msg">No research data.</p>';
  },

  copyJson(btn) {
    if (!this.lastResult) return;
    navigator.clipboard.writeText(JSON.stringify(this.lastResult, null, 2));
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = orig; }, 1500);
  },

  copyText(btn) {
    if (!this.lastResult?.copy) return;
    let text = '';
    const copy = this.lastResult.copy;
    Object.keys(SECTION_NAMES).forEach(key => {
      const info = SECTION_NAMES[key];
      if (!copy[key]) return;
      text += `\n${'='.repeat(40)}\n${info.num}. ${info.name} (${info.desc})\n${'='.repeat(40)}\n`;
      const section = copy[key];
      Object.entries(section).forEach(([k, v]) => {
        if (Array.isArray(v)) {
          text += `\n[${k}]\n`;
          v.forEach((item, i) => {
            text += typeof item === 'object' ? `  ${i + 1}. ${JSON.stringify(item)}\n` : `  ${i + 1}. ${item}\n`;
          });
        } else if (typeof v === 'object' && v !== null) {
          text += `\n[${k}]\n${JSON.stringify(v, null, 2)}\n`;
        } else {
          text += `\n[${k}]\n${v}\n`;
        }
      });
    });
    navigator.clipboard.writeText(text);
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = orig; }, 1500);
  },

  reset() {
    this.showResult(false);
    this.lastResult = null;
  },
};
