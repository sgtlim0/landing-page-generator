const ImageTab = {
  progressInterval: null,

  init() {
    const chipContainer = document.getElementById('imageStyleChips');
    if (chipContainer) {
      chipContainer.addEventListener('click', (e) => {
        const chip = e.target.closest('.chip');
        if (!chip) return;
        chipContainer.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
      });
    }
  },

  getFormData() {
    return {
      style_preset: document.querySelector('#imageStyleChips .chip.active')?.dataset.value || 'minimal',
      brand_colors: {
        primary: document.getElementById('color_primary').value,
        secondary: document.getElementById('color_secondary').value,
        accent: document.getElementById('color_accent').value,
      },
    };
  },

  showProgress(show) {
    const el = document.getElementById('imageProgress');
    el.classList.toggle('show', show);
  },

  updateProgress(pct, text) {
    document.getElementById('imageProgressFill').style.width = pct + '%';
    document.getElementById('imageProgressText').textContent = text;
  },

  showResult(show) {
    document.getElementById('imageResult').classList.toggle('show', show);
  },

  showError(msg) {
    const el = document.getElementById('imageError');
    el.textContent = msg;
    el.classList.add('show');
  },

  clearError() {
    document.getElementById('imageError').classList.remove('show');
  },

  async submit(payload) {
    const btn = document.getElementById('imageSubmitBtn');
    btn.disabled = true;
    btn.textContent = 'Generating...';
    this.showProgress(true);
    this.clearError();
    this.showResult(false);

    let pct = 0;
    this.progressInterval = setInterval(() => {
      pct = Math.min(pct + (Math.random() * 3 + 1), 95);
      const section = Math.min(Math.ceil(pct / 7.7), 13);
      this.updateProgress(pct, `Generating section ${section}/13... (${Math.round(pct)}%)`);
    }, 3000);

    try {
      const result = await Api.generateImage(payload);

      clearInterval(this.progressInterval);
      this.progressInterval = null;

      if (result.type === 'image') {
        const url = URL.createObjectURL(result.blob);
        this.updateProgress(100, 'Complete!');

        setTimeout(() => {
          this.showProgress(false);
          this.showResult(true);
          document.getElementById('imageResultImg').src = url;
          document.getElementById('imageDownloadBtn').href = url;
        }, 500);
      } else {
        throw new Error('Unexpected response format');
      }
    } catch (err) {
      if (this.progressInterval) {
        clearInterval(this.progressInterval);
        this.progressInterval = null;
      }
      this.showProgress(false);
      this.showError(err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Generate Landing Page (13 Sections)';
    }
  },

  reset() {
    this.showResult(false);
    const img = document.getElementById('imageResultImg');
    if (img.src.startsWith('blob:')) {
      URL.revokeObjectURL(img.src);
    }
    img.src = '';
  },
};
