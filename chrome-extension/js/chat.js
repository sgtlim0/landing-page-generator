const Chat = {
  container: null,

  init() {
    this.container = document.getElementById('chatContainer');
  },

  _scrollToBottom() {
    this.container.scrollTop = this.container.scrollHeight;
  },

  _escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  },

  _removeWelcome() {
    const welcome = this.container.querySelector('.chat-welcome');
    if (welcome) welcome.remove();
  },

  addUserMessage(query) {
    this._removeWelcome();

    const el = document.createElement('div');
    el.className = 'chat-msg user-msg';
    el.innerHTML = `
      <div class="msg-avatar">&#128100;</div>
      <div class="msg-content">
        <div class="msg-text">${this._escapeHtml(query)}</div>
      </div>
    `;
    this.container.appendChild(el);
    this._scrollToBottom();
  },

  addLoadingMessage() {
    this._removeWelcome();

    const el = document.createElement('div');
    el.className = 'chat-msg ai-msg loading-msg';
    el.id = 'loadingMsg';
    el.innerHTML = `
      <div class="msg-avatar">&#128269;</div>
      <div class="msg-content">
        <div class="msg-label">리서치 중</div>
        <div class="loading-dots">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
        <div class="loading-text">제품 정보를 분석하고 인사이트를 생성하고 있습니다...</div>
      </div>
    `;
    this.container.appendChild(el);
    this._scrollToBottom();
    return el;
  },

  removeLoadingMessage() {
    const el = document.getElementById('loadingMsg');
    if (el) el.remove();
  },

  addResearchResult(data) {
    const el = document.createElement('div');
    el.className = 'chat-msg ai-msg result-msg';

    const research = data.research || {};
    const copy = data.copy || {};

    let sectionsHtml = '';

    // Extracted brief (from deep research)
    if (research.extracted_brief) {
      const eb = research.extracted_brief;
      sectionsHtml += this._buildResearchSection(
        '추출된 제품 정보', 'framework',
        this._buildField('제품명', eb.product_name) +
        this._buildField('한 줄 정의', eb.one_liner) +
        this._buildField('타겟 고객', eb.target_audience) +
        this._buildField('핵심 문제', eb.main_problem) +
        this._buildField('핵심 혜택', eb.key_benefit)
      );
    }

    // Research sections
    if (research.pain_points && research.pain_points.length > 0) {
      sectionsHtml += this._buildResearchSection(
        'Pain Points', 'pain',
        research.pain_points.map(p =>
          `<div class="research-item pain-item"><strong>${this._escapeHtml(p.category)}</strong>: ${this._escapeHtml(p.pain)}<br><span class="item-sub">${this._escapeHtml(p.emotional_hook)}</span></div>`
        ).join('')
      );
    }

    if (research.failure_reasons && research.failure_reasons.length > 0) {
      sectionsHtml += this._buildResearchSection(
        'Failure Reasons', 'failure',
        research.failure_reasons.map(f =>
          `<div class="research-item"><strong>${this._escapeHtml(f.reason)}</strong><br><span class="item-sub">${this._escapeHtml(f.explanation)}</span><br><span class="item-reframe">Reframe: ${this._escapeHtml(f.reframe)}</span></div>`
        ).join('')
      );
    }

    if (research.after_image) {
      const a = research.after_image;
      sectionsHtml += this._buildResearchSection(
        'After Image', 'after',
        this._buildField('Concrete Result', a.concrete_result) +
        this._buildField('Emotional Freedom', a.emotional_freedom) +
        this._buildField('Time Saved', a.time_saved) +
        this._buildField('Lifestyle Change', a.lifestyle_change)
      );
    }

    if (research.objections && research.objections.length > 0) {
      sectionsHtml += this._buildResearchSection(
        'Objections', 'objection',
        research.objections.map(o =>
          `<div class="research-item"><span class="obj-q">Q:</span> ${this._escapeHtml(o.objection)}<br><span class="obj-a">A:</span> ${this._escapeHtml(o.counter)}</div>`
        ).join('')
      );
    }

    if (research.differentiators && research.differentiators.length > 0) {
      sectionsHtml += this._buildResearchSection(
        'Differentiators', 'diff',
        research.differentiators.map(d =>
          `<div class="research-item"><strong>${this._escapeHtml(d.point)}</strong><br><span class="item-sub">${this._escapeHtml(d.explanation)}</span></div>`
        ).join('')
      );
    }

    if (research.message_framework) {
      const mf = research.message_framework;
      let mfContent = '';
      if (mf.core_message) mfContent += this._buildField('Core Message', mf.core_message);
      if (mf.tone) mfContent += this._buildField('Tone', mf.tone);
      if (mf.key_phrases && mf.key_phrases.length > 0) {
        mfContent += `<div class="field-block"><div class="field-label">Key Phrases</div><div class="field-value">${mf.key_phrases.map(p => `<span class="brief-tag">${this._escapeHtml(p)}</span>`).join(' ')}</div></div>`;
      }
      if (mfContent) {
        sectionsHtml += this._buildResearchSection('Message Framework', 'framework', mfContent);
      }
    }

    // Copy section count
    const copyKeys = Object.keys(copy);
    const copyCountLabel = copyKeys.length > 0 ? `${copyKeys.length}개 섹션 생성됨` : '';

    el.innerHTML = `
      <div class="msg-avatar">&#129302;</div>
      <div class="msg-content">
        <div class="msg-label">리서치 완료</div>
        <div class="result-sections">${sectionsHtml || '<div class="empty-msg">리서치 데이터가 반환되지 않았습니다.</div>'}</div>
        ${copyCountLabel ? `<div class="copy-count">${copyCountLabel}</div>` : ''}
        <div class="result-actions">
          <button class="action-btn" data-action="copy-json">JSON 복사</button>
          <button class="action-btn" data-action="copy-text">텍스트 복사</button>
        </div>
      </div>
    `;

    // Store data for copy actions
    el._resultData = data;

    // Toggle sections
    el.addEventListener('click', (e) => {
      const header = e.target.closest('.section-toggle');
      if (header) {
        const body = header.nextElementSibling;
        if (body) {
          body.classList.toggle('open');
          header.classList.toggle('open');
        }
        return;
      }

      const btn = e.target.closest('[data-action]');
      if (!btn) return;

      if (btn.dataset.action === 'copy-json') {
        this._copyToClipboard(btn, JSON.stringify(el._resultData, null, 2));
      } else if (btn.dataset.action === 'copy-text') {
        this._copyToClipboard(btn, this._formatAsText(el._resultData));
      }
    });

    this.container.appendChild(el);
    this._scrollToBottom();

    // Auto-open first section
    const firstToggle = el.querySelector('.section-toggle');
    const firstBody = el.querySelector('.section-body');
    if (firstToggle && firstBody) {
      firstToggle.classList.add('open');
      firstBody.classList.add('open');
    }
  },

  addErrorMessage(msg) {
    const el = document.createElement('div');
    el.className = 'chat-msg ai-msg error-msg';
    el.innerHTML = `
      <div class="msg-avatar">&#9888;&#65039;</div>
      <div class="msg-content">
        <div class="msg-label">오류</div>
        <div class="error-text">${this._escapeHtml(msg)}</div>
      </div>
    `;
    this.container.appendChild(el);
    this._scrollToBottom();
  },

  _buildResearchSection(title, type, contentHtml) {
    return `
      <div class="research-section ${type}">
        <div class="section-toggle">
          <span class="toggle-arrow">&#9654;</span>
          <span class="section-title">${this._escapeHtml(title)}</span>
        </div>
        <div class="section-body">${contentHtml}</div>
      </div>
    `;
  },

  _buildField(label, value) {
    if (!value) return '';
    return `<div class="field-block"><div class="field-label">${this._escapeHtml(label)}</div><div class="field-value">${this._escapeHtml(String(value))}</div></div>`;
  },

  _copyToClipboard(btn, text) {
    try {
      navigator.clipboard.writeText(text);
      const orig = btn.textContent;
      btn.textContent = '복사됨!';
      btn.classList.add('copied');
      setTimeout(() => {
        btn.textContent = orig;
        btn.classList.remove('copied');
      }, 1500);
    } catch (err) {
      btn.textContent = '실패';
      setTimeout(() => { btn.textContent = 'Copy'; }, 1500);
    }
  },

  _formatAsText(data) {
    let text = '';
    const research = data.research || {};
    const copy = data.copy || {};

    if (research.pain_points) {
      text += '\n=== Pain Points ===\n';
      research.pain_points.forEach(p => {
        text += `[${p.category}] ${p.pain}\n  Hook: ${p.emotional_hook}\n\n`;
      });
    }

    if (research.failure_reasons) {
      text += '\n=== Failure Reasons ===\n';
      research.failure_reasons.forEach(f => {
        text += `${f.reason}\n  ${f.explanation}\n  Reframe: ${f.reframe}\n\n`;
      });
    }

    if (research.after_image) {
      const a = research.after_image;
      text += '\n=== After Image ===\n';
      if (a.concrete_result) text += `Concrete Result: ${a.concrete_result}\n`;
      if (a.emotional_freedom) text += `Emotional Freedom: ${a.emotional_freedom}\n`;
      if (a.time_saved) text += `Time Saved: ${a.time_saved}\n`;
      if (a.lifestyle_change) text += `Lifestyle Change: ${a.lifestyle_change}\n`;
    }

    if (research.objections) {
      text += '\n=== Objections ===\n';
      research.objections.forEach(o => {
        text += `Q: ${o.objection}\nA: ${o.counter}\n\n`;
      });
    }

    if (research.differentiators) {
      text += '\n=== Differentiators ===\n';
      research.differentiators.forEach(d => {
        text += `${d.point}: ${d.explanation}\n\n`;
      });
    }

    if (Object.keys(copy).length > 0) {
      text += '\n\n========== COPY ==========\n';
      Object.entries(copy).forEach(([key, section]) => {
        text += `\n--- ${key} ---\n`;
        Object.entries(section).forEach(([k, v]) => {
          if (Array.isArray(v)) {
            text += `[${k}]\n`;
            v.forEach((item, i) => {
              text += typeof item === 'object' ? `  ${i + 1}. ${JSON.stringify(item)}\n` : `  ${i + 1}. ${item}\n`;
            });
          } else if (typeof v === 'object' && v !== null) {
            text += `[${k}]\n${JSON.stringify(v, null, 2)}\n`;
          } else {
            text += `[${k}] ${v}\n`;
          }
        });
      });
    }

    return text.trim();
  },
};
