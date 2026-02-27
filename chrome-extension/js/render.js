const SECTION_NAMES = {
  section_01_hero: { num: '01', name: 'Hero', desc: 'Urgency Header' },
  section_02_pain: { num: '02', name: 'Pain', desc: 'Empathy' },
  section_03_problem: { num: '03', name: 'Problem', desc: 'Root Cause' },
  section_04_story: { num: '04', name: 'Story', desc: 'Before/After' },
  section_05_solution: { num: '05', name: 'Solution', desc: 'Product Intro' },
  section_06_how_it_works: { num: '06', name: 'How It Works', desc: 'Process' },
  section_07_social_proof: { num: '07', name: 'Social Proof', desc: 'Testimonials' },
  section_08_authority: { num: '08', name: 'Authority', desc: 'Credibility' },
  section_09_benefits: { num: '09', name: 'Benefits', desc: 'Value Stack' },
  section_10_risk_removal: { num: '10', name: 'Risk Removal', desc: 'Guarantees' },
  section_11_comparison: { num: '11', name: 'Comparison', desc: 'With vs Without' },
  section_12_target_filter: { num: '12', name: 'Target Filter', desc: 'Ideal Customer' },
  section_13_final_cta: { num: '13', name: 'Final CTA', desc: 'Call to Action' },
};

function renderCopyField(label, value) {
  if (value === undefined || value === null) return '';
  if (Array.isArray(value)) {
    const items = value
      .map(v => `<li>${typeof v === 'object' ? JSON.stringify(v) : escapeHtml(String(v))}</li>`)
      .join('');
    return `<div class="copy-field"><div class="label">${escapeHtml(label)}</div><ul class="value-list">${items}</ul></div>`;
  }
  return `<div class="copy-field"><div class="label">${escapeHtml(label)}</div><div class="value">${escapeHtml(String(value))}</div></div>`;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function renderSection(key, data) {
  const info = SECTION_NAMES[key] || { num: '??', name: key, desc: '' };
  let bodyHtml = '';

  if (key === 'section_01_hero') {
    bodyHtml += '<div class="copy-field"><div class="label">Headlines (Options)</div>';
    (data.headline_options || []).forEach((h, i) => {
      bodyHtml += `<div class="headline-option">${i + 1}. ${escapeHtml(h)}</div>`;
    });
    bodyHtml += '</div>';
    bodyHtml += renderCopyField('Subheadline', data.subheadline);
    bodyHtml += renderCopyField('Urgency Badge', data.urgency_badge);
    bodyHtml += renderCopyField('CTA Text', data.cta_text);
  } else if (key === 'section_02_pain') {
    bodyHtml += renderCopyField('Intro', data.intro);
    bodyHtml += renderCopyField('Pain Points', data.pain_points);
    bodyHtml += renderCopyField('Emotional Hook', data.emotional_hook);
  } else if (key === 'section_03_problem') {
    bodyHtml += renderCopyField('Hook', data.hook);
    bodyHtml += renderCopyField('Reasons', data.reasons);
    bodyHtml += renderCopyField('Reframe', data.reframe);
  } else if (key === 'section_04_story') {
    bodyHtml += renderCopyField('Before', data.before);
    bodyHtml += renderCopyField('Turning Point', data.turning_point);
    bodyHtml += renderCopyField('After', data.after);
    bodyHtml += renderCopyField('Proof', data.proof);
  } else if (key === 'section_05_solution') {
    bodyHtml += renderCopyField('Intro', data.intro);
    bodyHtml += renderCopyField('Product Name', data.product_name);
    bodyHtml += renderCopyField('One Liner', data.one_liner);
    bodyHtml += renderCopyField('Target Fit', data.target_fit);
  } else if (key === 'section_06_how_it_works') {
    bodyHtml += renderCopyField('Headline', data.headline);
    bodyHtml += '<div class="copy-field"><div class="label">Steps</div>';
    (data.steps || []).forEach(s => {
      bodyHtml += `<div class="step-card"><div class="step-num">${escapeHtml(String(s.number))}</div><div><strong>${escapeHtml(s.title)}</strong><br><span class="step-desc">${escapeHtml(s.description)}</span>${s.result ? `<br><span class="step-result">Result: ${escapeHtml(s.result)}</span>` : ''}</div></div>`;
    });
    bodyHtml += '</div>';
  } else if (key === 'section_07_social_proof') {
    bodyHtml += renderCopyField('Headline', data.headline);
    if (data.stats) {
      bodyHtml += '<div class="copy-field"><div class="label">Stats</div><div class="stats-row">';
      (data.stats || []).forEach(s => {
        bodyHtml += `<span class="stat-num">${escapeHtml(s.number)}</span><span class="stat-label">${escapeHtml(s.label)}</span>`;
      });
      bodyHtml += '</div></div>';
    }
    bodyHtml += '<div class="copy-field"><div class="label">Testimonials</div>';
    (data.testimonials || []).forEach(t => {
      bodyHtml += `<div class="testimonial-card"><div class="quote">"${escapeHtml(t.quote)}"</div><div class="meta">${escapeHtml(t.name)} - ${escapeHtml(t.role)} ${t.result ? `| ${escapeHtml(t.result)}` : ''}</div></div>`;
    });
    bodyHtml += '</div>';
  } else if (key === 'section_08_authority') {
    bodyHtml += renderCopyField('Intro', data.intro);
    bodyHtml += renderCopyField('Bio', data.bio);
    bodyHtml += renderCopyField('Credentials', data.credentials);
    bodyHtml += renderCopyField('Message', data.message);
  } else if (key === 'section_09_benefits') {
    bodyHtml += renderCopyField('Headline', data.headline);
    bodyHtml += renderCopyField('Main Benefits', data.main_benefits);
    if (data.bonus_items) {
      bodyHtml += '<div class="copy-field"><div class="label">Bonus Items</div>';
      (data.bonus_items || []).forEach(b => {
        bodyHtml += `<div class="bonus-item"><strong>${escapeHtml(b.name)}</strong> <span class="bonus-value">(${escapeHtml(b.value)})</span></div>`;
      });
      bodyHtml += '</div>';
    }
    bodyHtml += renderCopyField('Total Value', data.total_value);
  } else if (key === 'section_10_risk_removal') {
    bodyHtml += renderCopyField('Guarantee', data.guarantee);
    if (data.faq) {
      bodyHtml += '<div class="copy-field"><div class="label">FAQ</div>';
      (data.faq || []).forEach(f => {
        bodyHtml += `<div class="faq-item"><strong>Q: ${escapeHtml(f.question)}</strong><br><span class="faq-answer">A: ${escapeHtml(f.answer)}</span></div>`;
      });
      bodyHtml += '</div>';
    }
    bodyHtml += renderCopyField('Support', data.support);
  } else if (key === 'section_11_comparison') {
    bodyHtml += `<div class="comparison-grid">
      <div class="comparison-col without"><h4>Without</h4><ul>${(data.without || []).map(w => `<li>${escapeHtml(w)}</li>`).join('')}</ul></div>
      <div class="comparison-col with"><h4>With</h4><ul>${(data.with || []).map(w => `<li>${escapeHtml(w)}</li>`).join('')}</ul></div>
    </div>`;
    bodyHtml += renderCopyField('Question', data.question);
  } else if (key === 'section_12_target_filter') {
    bodyHtml += `<div class="comparison-grid">
      <div class="comparison-col with"><h4>Recommended</h4><ul>${(data.recommended || []).map(r => `<li>${escapeHtml(r)}</li>`).join('')}</ul></div>
      <div class="comparison-col without"><h4>Not Recommended</h4><ul>${(data.not_recommended || []).map(r => `<li>${escapeHtml(r)}</li>`).join('')}</ul></div>
    </div>`;
  } else if (key === 'section_13_final_cta') {
    bodyHtml += renderCopyField('Headline', data.headline);
    bodyHtml += renderCopyField('Urgency', data.urgency);
    bodyHtml += renderCopyField('Price Display', data.price_display);
    bodyHtml += renderCopyField('CTA Button', data.cta_button);
    bodyHtml += renderCopyField('Closing', data.closing);
  } else {
    bodyHtml += `<pre class="json-fallback">${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
  }

  return `<div class="section-output">
    <div class="section-header" data-action="toggle-section">
      <h3>${info.num}. ${info.name} <span class="section-desc">- ${info.desc}</span></h3>
      <span class="badge">Section ${info.num}</span>
    </div>
    <div class="section-body">${bodyHtml}</div>
  </div>`;
}

function renderResearch(research) {
  let html = '';

  if (research.pain_points) {
    html += '<div class="section-output"><div class="section-header" data-action="toggle-section"><h3>Pain Points Analysis</h3></div><div class="section-body open">';
    research.pain_points.forEach(p => {
      html += `<div class="pain-item"><strong>${escapeHtml(p.category)}</strong>: ${escapeHtml(p.pain)}<br><span class="pain-hook">${escapeHtml(p.emotional_hook)}</span></div>`;
    });
    html += '</div></div>';
  }

  if (research.failure_reasons) {
    html += '<div class="section-output"><div class="section-header" data-action="toggle-section"><h3>Failure Reasons</h3></div><div class="section-body open">';
    research.failure_reasons.forEach(f => {
      html += `<div class="failure-item"><strong>${escapeHtml(f.reason)}</strong><br><span class="failure-explain">${escapeHtml(f.explanation)}</span><br><span class="failure-reframe">Reframe: ${escapeHtml(f.reframe)}</span></div>`;
    });
    html += '</div></div>';
  }

  if (research.after_image) {
    const a = research.after_image;
    html += '<div class="section-output"><div class="section-header" data-action="toggle-section"><h3>After Image (Transformation)</h3></div><div class="section-body open">';
    html += renderCopyField('Concrete Result', a.concrete_result);
    html += renderCopyField('Emotional Freedom', a.emotional_freedom);
    html += renderCopyField('Time Saved', a.time_saved);
    html += renderCopyField('Lifestyle Change', a.lifestyle_change);
    html += '</div></div>';
  }

  if (research.objections) {
    html += '<div class="section-output"><div class="section-header" data-action="toggle-section"><h3>Objections & Counters</h3></div><div class="section-body">';
    research.objections.forEach(o => {
      html += `<div class="objection-item"><strong class="obj-q">Q:</strong> ${escapeHtml(o.objection)}<br><strong class="obj-a">A:</strong> ${escapeHtml(o.counter)}</div>`;
    });
    html += '</div></div>';
  }

  if (research.differentiators) {
    html += '<div class="section-output"><div class="section-header" data-action="toggle-section"><h3>Differentiators</h3></div><div class="section-body">';
    research.differentiators.forEach(d => {
      html += `<div class="diff-item"><strong>${escapeHtml(d.point)}</strong><br><span class="diff-explain">${escapeHtml(d.explanation)}</span></div>`;
    });
    html += '</div></div>';
  }

  return html;
}
