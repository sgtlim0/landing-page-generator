document.addEventListener('DOMContentLoaded', async () => {
  Chat.init();

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
    credStatus.textContent = '저장됨';
    credStatus.classList.add('saved');
  }

  credSaveBtn.addEventListener('click', async () => {
    const creds = getCredentials();
    if (!creds.aws_access_key_id || !creds.aws_secret_access_key) {
      credStatus.textContent = '모든 필드를 입력하세요';
      credStatus.classList.remove('saved');
      return;
    }
    await Storage.saveCredentials(creds);
    credStatus.textContent = '저장됨';
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

  // --- Search Bar ---
  const form = document.getElementById('researchForm');
  const submitBtn = document.getElementById('submitBtn');
  const queryInput = document.getElementById('queryInput');

  // Auto-resize textarea (1~3 lines)
  queryInput.addEventListener('input', () => {
    queryInput.style.height = 'auto';
    const maxHeight = parseFloat(getComputedStyle(queryInput).lineHeight) * 3;
    queryInput.style.height = Math.min(queryInput.scrollHeight, maxHeight) + 'px';
  });

  // Enter → submit, Shift+Enter → newline
  queryInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      form.dispatchEvent(new Event('submit', { cancelable: true }));
    }
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (submitBtn.disabled) return;

    const query = queryInput.value.trim();
    if (!query) {
      Chat.addErrorMessage('검색어를 입력해주세요.');
      return;
    }

    const creds = getCredentials();
    if (!creds.aws_access_key_id || !creds.aws_secret_access_key) {
      Chat.addErrorMessage('AWS 자격증명을 먼저 설정해주세요.');
      return;
    }

    Chat.addUserMessage(query);

    // Reset input
    queryInput.value = '';
    queryInput.style.height = 'auto';

    submitBtn.disabled = true;
    Chat.addLoadingMessage();

    try {
      const data = await Api.deepResearch({
        aws_credentials: creds,
        query,
      });

      Chat.removeLoadingMessage();
      Chat.addResearchResult(data);
    } catch (err) {
      Chat.removeLoadingMessage();
      Chat.addErrorMessage(err.message);
    } finally {
      submitBtn.disabled = false;
    }
  });
});

function getCredentials() {
  return {
    aws_access_key_id: document.getElementById('aws_access_key').value.trim(),
    aws_secret_access_key: document.getElementById('aws_secret_key').value.trim(),
    aws_region: document.getElementById('aws_region').value,
  };
}
