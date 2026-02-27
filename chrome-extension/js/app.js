document.addEventListener('DOMContentLoaded', async () => {
  ImageTab.init();
  CopyTab.init();

  // --- Tab Switching ---
  const tabBar = document.getElementById('mainTabBar');
  const imagePanel = document.getElementById('imagePanel');
  const copyPanel = document.getElementById('copyPanel');

  tabBar.addEventListener('click', (e) => {
    const tab = e.target.closest('.main-tab');
    if (!tab) return;
    tabBar.querySelectorAll('.main-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    const target = tab.dataset.tab;
    imagePanel.style.display = target === 'image' ? 'block' : 'none';
    copyPanel.style.display = target === 'copy' ? 'block' : 'none';
  });

  // --- Credentials ---
  const credToggle = document.getElementById('credToggle');
  const credBody = document.getElementById('credBody');
  const credSaveBtn = document.getElementById('credSaveBtn');
  const credClearBtn = document.getElementById('credClearBtn');
  const credStatus = document.getElementById('credStatus');

  credToggle.addEventListener('click', () => {
    credBody.classList.toggle('open');
    credToggle.classList.toggle('open');
  });

  const saved = await Storage.loadCredentials();
  if (saved) {
    document.getElementById('aws_access_key').value = saved.aws_access_key_id || '';
    document.getElementById('aws_secret_key').value = saved.aws_secret_access_key || '';
    document.getElementById('aws_region').value = saved.aws_region || 'us-east-1';
    credStatus.textContent = 'Saved';
    credStatus.classList.add('saved');
  }

  credSaveBtn.addEventListener('click', async () => {
    const creds = getCredentials();
    if (!creds.aws_access_key_id || !creds.aws_secret_access_key) {
      credStatus.textContent = 'Fill in all fields';
      credStatus.classList.remove('saved');
      return;
    }
    await Storage.saveCredentials(creds);
    credStatus.textContent = 'Saved';
    credStatus.classList.add('saved');
  });

  credClearBtn.addEventListener('click', async () => {
    await Storage.clearCredentials();
    document.getElementById('aws_access_key').value = '';
    document.getElementById('aws_secret_key').value = '';
    document.getElementById('aws_region').value = 'us-east-1';
    credStatus.textContent = '';
    credStatus.classList.remove('saved');
  });

  // --- Image Form ---
  document.getElementById('imageForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const payload = buildImagePayload();
    ImageTab.submit(payload);
  });

  document.getElementById('imageResetBtn')?.addEventListener('click', (e) => {
    e.preventDefault();
    ImageTab.reset();
  });

  // --- Copy Form ---
  document.getElementById('copyForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const payload = buildCopyPayload();
    CopyTab.submit(payload);
  });
});

function getCredentials() {
  return {
    aws_access_key_id: document.getElementById('aws_access_key').value.trim(),
    aws_secret_access_key: document.getElementById('aws_secret_key').value.trim(),
    aws_region: document.getElementById('aws_region').value,
  };
}

function getProductInfo() {
  return {
    product_name: document.getElementById('product_name').value,
    one_liner: document.getElementById('one_liner').value,
    target_audience: document.getElementById('target_audience').value,
    main_problem: document.getElementById('main_problem').value,
    key_benefit: document.getElementById('key_benefit').value,
    price: {
      original: document.getElementById('price_original').value,
      discounted: document.getElementById('price_discounted').value,
      period: document.getElementById('price_period').value,
    },
    urgency: {
      type: 'quantity',
      value: document.getElementById('urgency_value').value,
      bonus: document.getElementById('urgency_bonus').value,
    },
  };
}

function buildImagePayload() {
  const imageData = ImageTab.getFormData();
  return {
    aws_credentials: getCredentials(),
    brief: {
      ...getProductInfo(),
      style_preset: imageData.style_preset,
      brand_colors: imageData.brand_colors,
    },
  };
}

function buildCopyPayload() {
  return {
    aws_credentials: getCredentials(),
    brief: getProductInfo(),
  };
}
