/**
 * Minimal & User-Friendly Reviewer UI Logic
 * Designed for non-technical clinical, safety, and quality operations teams
 */

const state = {
  activeCategory: 'ALL',
  searchQuery: '',
  queueItems: [],
  selectedEmailId: null,
  currentDetail: null,
  activeAttachmentId: null,
  isSidebarMinimized: false,
  isNarrativeExpanded: false,
  pollTimer: null,
};

// DOM Elements
const elements = {
  // Sidebar Controls
  sidebar: document.getElementById('sidebar'),
  sidebarExpandBar: document.getElementById('sidebar-expand-bar'),
  btnToggleSidebar: document.getElementById('btn-toggle-sidebar'),
  btnMinimizeInbox: document.getElementById('btn-minimize-inbox'),
  btnExpandInbox: document.getElementById('btn-expand-inbox'),

  // Header Queue Chip
  queueChip: document.getElementById('queue-chip'),
  queueChipDot: document.getElementById('queue-chip-dot'),
  queueChipText: document.getElementById('queue-chip-text'),
  tabQueuedBadge: document.getElementById('tab-queued-badge'),

  // Queue
  queueList: document.getElementById('queue-list'),
  queueCount: document.getElementById('queue-count'),
  queueSearch: document.getElementById('queue-search'),
  categoryFilters: document.getElementById('category-filters'),
  btnPollMailbox: document.getElementById('btn-poll-mailbox'),
  emptyState: document.getElementById('empty-state'),
  detailContainer: document.getElementById('detail-container'),
  btnPromptAddEmail: document.getElementById('btn-prompt-add-email'),

  // Upload Modal
  uploadModal: document.getElementById('upload-modal'),
  btnOpenUpload: document.getElementById('btn-open-upload'),
  btnCloseUpload: document.getElementById('btn-close-upload'),
  btnCancelUpload: document.getElementById('btn-cancel-upload'),
  uploadForm: document.getElementById('upload-form'),
  inputSender: document.getElementById('input-sender'),
  inputSubject: document.getElementById('input-subject'),
  inputBody: document.getElementById('input-body'),
  inputFile: document.getElementById('input-file'),
  selectedFileName: document.getElementById('selected-file-name'),
  btnSubmitUpload: document.getElementById('btn-submit-upload'),

  // Case Progress Bar
  caseProgressCard: document.getElementById('case-progress-card'),
  progressDot: document.getElementById('progress-dot'),
  progressTitle: document.getElementById('progress-title'),
  progressPctBadge: document.getElementById('progress-pct-badge'),
  progressBarFill: document.getElementById('progress-bar-fill'),
  progressMessage: document.getElementById('progress-message'),
  progressJobStatus: document.getElementById('progress-job-status'),

  // Top Case Header
  detailStatus: document.getElementById('detail-status'),
  detailDate: document.getElementById('detail-date'),
  detailSubject: document.getElementById('detail-subject'),
  detailSender: document.getElementById('detail-sender'),
  detailEmailId: document.getElementById('detail-email-id'),

  // SECTION 1: AI ASSESSMENT + REVIEW STATUS
  heroCatLabel: document.getElementById('hero-cat-label'),
  heroCatCode: document.getElementById('hero-cat-code'),
  heroConfBadge: document.getElementById('hero-conf-badge'),
  heroReasonText: document.getElementById('hero-reason-text'),
  heroStatusHeadline: document.getElementById('hero-status-headline'),
  heroStatusTitle: document.getElementById('hero-status-title'),
  heroActionDesc: document.getElementById('hero-action-desc'),

  // SECTION 2: CASE SNAPSHOT
  snapshotFile: document.getElementById('snapshot-file'),
  snapshotSender: document.getElementById('snapshot-sender'),
  snapshotSubject: document.getElementById('snapshot-subject'),
  snapshotDocType: document.getElementById('snapshot-doc-type'),
  snapshotLanguage: document.getElementById('snapshot-language'),
  snapshotReceived: document.getElementById('snapshot-received'),

  // SECTION 3: WHY THIS CLASSIFICATION?
  execWhyContent: document.getElementById('exec-why-content'),

  // SECTION 4: CLASSIFICATION SIGNALS
  signalsTableBody: document.getElementById('signals-table-body'),

  // SECTION 5: DOMAIN-SPECIFIC FINDINGS
  domainContextBadge: document.getElementById('domain-context-badge'),
  domainFindingsContainer: document.getElementById('domain-findings-container'),

  // SECTION 6: DATA QUALITY & TRACEABILITY
  traceStatTotal: document.getElementById('trace-stat-total'),
  traceStatSupported: document.getElementById('trace-stat-supported'),
  traceStatNotStated: document.getElementById('trace-stat-not-stated'),

  // SECTION 7: DETAILED AI NARRATIVE
  btnToggleNarrative: document.getElementById('btn-toggle-narrative'),
  narrativeCtaText: document.getElementById('narrative-cta-text'),
  narrativeWrapper: document.getElementById('narrative-wrapper'),
  narrativeChevron: document.getElementById('narrative-chevron'),
  detailSummary: document.getElementById('detail-summary'),

  // Full Details & Source
  factsTableBody: document.getElementById('facts-table-body'),
  detailEmailBody: document.getElementById('detail-email-body'),
  auditTimeline: document.getElementById('audit-timeline'),

  // Document & Evidence
  inspectorBadge: document.getElementById('inspector-badge'),
  inspectorBody: document.getElementById('inspector-body'),
  docFilename: document.getElementById('doc-filename'),
  btnOpenPdfTab: document.getElementById('btn-open-pdf-tab'),
  pdfViewerFrame: document.getElementById('pdf-viewer-frame'),

  // Reviewer Actions
  btnAcceptReview: document.getElementById('btn-accept-review'),
  btnOpenOverride: document.getElementById('btn-open-override'),

  // Override Modal
  overrideModal: document.getElementById('override-modal'),
  btnCloseOverride: document.getElementById('btn-close-override'),
  btnCancelOverride: document.getElementById('btn-cancel-override'),
  btnSubmitOverride: document.getElementById('btn-submit-override'),
  overrideReviewerId: document.getElementById('override-reviewer-id'),
  overrideJustification: document.getElementById('override-justification'),
  overrideFieldsList: document.getElementById('override-fields-list'),
  chkIcsr: document.getElementById('chk-icsr'),
  chkPqc: document.getElementById('chk-pqc'),
  chkMi: document.getElementById('chk-mi'),
  chkNotRelevant: document.getElementById('chk-not-relevant'),
};

document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  loadQueue();
});

function setupEventListeners() {
  // Sidebar Minimize & Expand Toggles
  if (elements.btnMinimizeInbox) {
    elements.btnMinimizeInbox.addEventListener('click', minimizeSidebar);
  }
  if (elements.btnExpandInbox) {
    elements.btnExpandInbox.addEventListener('click', expandSidebar);
  }
  if (elements.btnToggleSidebar) {
    elements.btnToggleSidebar.addEventListener('click', () => {
      if (state.isSidebarMinimized) {
        expandSidebar();
      } else {
        minimizeSidebar();
      }
    });
  }

  // Narrative Accordion Toggle
  if (elements.btnToggleNarrative) {
    elements.btnToggleNarrative.addEventListener('click', () => {
      state.isNarrativeExpanded = !state.isNarrativeExpanded;
      if (elements.narrativeWrapper) {
        elements.narrativeWrapper.style.display = state.isNarrativeExpanded ? 'block' : 'none';
      }
      if (elements.narrativeChevron) {
        elements.narrativeChevron.style.transform = state.isNarrativeExpanded ? 'rotate(180deg)' : 'rotate(0deg)';
      }
      if (elements.narrativeCtaText) {
        elements.narrativeCtaText.textContent = state.isNarrativeExpanded ? 'Hide narrative' : 'View full narrative';
      }
    });
  }

  // Upload Modal Open/Close
  if (elements.btnOpenUpload) {
    elements.btnOpenUpload.addEventListener('click', openUploadModal);
  }
  if (elements.btnPromptAddEmail) {
    elements.btnPromptAddEmail.addEventListener('click', openUploadModal);
  }
  if (elements.btnCloseUpload) {
    elements.btnCloseUpload.addEventListener('click', closeUploadModal);
  }
  if (elements.btnCancelUpload) {
    elements.btnCancelUpload.addEventListener('click', closeUploadModal);
  }

  // File Input preview name
  if (elements.inputFile) {
    elements.inputFile.addEventListener('change', (e) => {
      const file = e.target.files && e.target.files[0];
      if (file) {
        elements.selectedFileName.textContent = `Attached: ${file.name} (${Math.round(file.size / 1024)} KB)`;
        elements.selectedFileName.style.display = 'inline-block';
      } else {
        elements.selectedFileName.style.display = 'none';
      }
    });
  }

  // Submit Upload Form
  if (elements.uploadForm) {
    elements.uploadForm.addEventListener('submit', handleUploadSubmit);
  }

  // Category tabs
  elements.categoryFilters.addEventListener('click', (e) => {
    const tabBtn = e.target.closest('.cat-tab');
    if (tabBtn) {
      document.querySelectorAll('.cat-tab').forEach(b => b.classList.remove('active'));
      tabBtn.classList.add('active');
      state.activeCategory = tabBtn.dataset.category;
      loadQueue();
    }
  });

  // Search
  let timer = null;
  elements.queueSearch.addEventListener('input', (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      state.searchQuery = e.target.value.trim();
      loadQueue();
    }, 250);
  });

  // Check mailbox button
  elements.btnPollMailbox.addEventListener('click', async () => {
    elements.btnPollMailbox.disabled = true;
    elements.btnPollMailbox.textContent = 'Checking...';
    try {
      const res = await fetch('/api/emails/poll', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        await loadQueue();
      }
    } catch (err) {
      console.error('Check mailbox error:', err);
    } finally {
      elements.btnPollMailbox.disabled = false;
      elements.btnPollMailbox.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="23 4 23 10 17 10"></polyline>
          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
        </svg>
        Check Mailbox`;
    }
  });

  // Approve button
  elements.btnAcceptReview.addEventListener('click', async () => {
    if (!state.selectedEmailId) return;
    const ok = confirm('Approve this case and its findings?');
    if (!ok) return;

    try {
      const res = await fetch(`/api/review-items/${state.selectedEmailId}/accept`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reviewerId: 'Reviewer-01',
          comments: 'Reviewed and confirmed findings.'
        })
      });
      const data = await res.json();
      if (data.success) {
        state.currentDetail = data.data;
        renderDetail(state.currentDetail);
        loadQueue(false);
      }
    } catch (err) {
      alert('Error approving case: ' + err.message);
    }
  });

  // Edit / Override modal
  elements.btnOpenOverride.addEventListener('click', openOverrideModal);
  elements.btnCloseOverride.addEventListener('click', closeOverrideModal);
  elements.btnCancelOverride.addEventListener('click', closeOverrideModal);
  elements.btnSubmitOverride.addEventListener('click', submitOverride);
}

// Minimize / Expand Sidebar functions
function minimizeSidebar() {
  state.isSidebarMinimized = true;
  elements.sidebar.classList.add('minimized');
  elements.sidebarExpandBar.style.display = 'flex';
}

function expandSidebar() {
  state.isSidebarMinimized = false;
  elements.sidebar.classList.remove('minimized');
  elements.sidebarExpandBar.style.display = 'none';
}

// Upload Modal
function openUploadModal() {
  elements.uploadForm.reset();
  elements.selectedFileName.style.display = 'none';
  elements.uploadModal.style.display = 'flex';
}

function closeUploadModal() {
  elements.uploadModal.style.display = 'none';
}

async function handleUploadSubmit(e) {
  e.preventDefault();

  const sender = elements.inputSender.value.trim();
  const subject = elements.inputSubject.value.trim();
  const body = elements.inputBody.value.trim();
  const file = elements.inputFile.files && elements.inputFile.files[0];

  if (!sender || !subject) {
    alert('Please enter sender email and subject.');
    return;
  }

  const formData = new FormData();
  formData.append('sender', sender);
  formData.append('subject', subject);
  formData.append('body', body);
  if (file) {
    formData.append('file', file);
  }

  try {
    elements.btnSubmitUpload.disabled = true;
    elements.btnSubmitUpload.textContent = 'Ingesting & Enqueueing...';

    const res = await fetch('/api/emails/upload', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();

    if (data.success && data.data) {
      closeUploadModal();
      await loadQueue(false);
      selectEmail(data.data.id);
      startActivePolling();
      alert('Case successfully added! AI processing has started.');
    } else {
      alert('Upload failed: ' + (data.message || 'Unknown error'));
    }
  } catch (err) {
    alert('Error uploading email: ' + err.message);
  } finally {
    elements.btnSubmitUpload.disabled = false;
    elements.btnSubmitUpload.textContent = 'Ingest & Process Case';
  }
}

// Load email list from API
async function loadQueue(selectFirst = true) {
  try {
    let url = `/api/review-items?`;
    // REVIEW_REQUIRED is a job-level status, not a category — fetch all and filter locally
    const isReviewRequired = state.activeCategory === 'REVIEW_REQUIRED';
    if (state.activeCategory && state.activeCategory !== 'ALL' && !isReviewRequired) {
      url += `category=${encodeURIComponent(state.activeCategory)}&`;
    }
    if (state.searchQuery) {
      url += `search=${encodeURIComponent(state.searchQuery)}&`;
    }

    const res = await fetch(url);
    const data = await res.json();

    if (data.success && Array.isArray(data.data)) {
      let allItems = data.data;

      // Client-side filter for REVIEW_REQUIRED
      const displayItems = isReviewRequired
        ? allItems.filter(i => i.jobStatus === 'REVIEW_REQUIRED' || i.status === 'REVIEW_REQUIRED')
        : allItems;

      state.queueItems = displayItems;

      // Update Queue Status Indicators (always computed from all items)
      const queuedCount = allItems.filter(i => i.inQueue || i.status === 'RECEIVED' || i.status === 'PROCESSING').length;
      const reviewRequiredCount = allItems.filter(i => i.jobStatus === 'REVIEW_REQUIRED' || i.status === 'REVIEW_REQUIRED').length;

      if (elements.queueChipText) {
        elements.queueChipText.textContent = `${queuedCount} in queue`;
      }
      if (elements.tabQueuedBadge) {
        elements.tabQueuedBadge.textContent = queuedCount;
      }
      if (elements.queueChipDot) {
        elements.queueChipDot.classList.toggle('active', queuedCount > 0);
      }
      const reviewBadge = document.getElementById('tab-review-required-badge');
      if (reviewBadge) {
        reviewBadge.textContent = reviewRequiredCount;
        reviewBadge.style.display = reviewRequiredCount > 0 ? '' : 'none';
      }

      renderQueue(displayItems);

      if (selectFirst && displayItems.length > 0 && !state.selectedEmailId) {
        selectEmail(displayItems[0].emailId);
      } else if (state.selectedEmailId) {
        const currentItem = displayItems.find(i => i.emailId === state.selectedEmailId);
        if (currentItem && (currentItem.inQueue || currentItem.status === 'PROCESSING')) {
          refreshSelectedDetail(state.selectedEmailId);
        }
      }

      if (queuedCount > 0) {
        startActivePolling();
      } else {
        stopActivePolling();
      }
    }
  } catch (err) {
    elements.queueList.innerHTML = `<div class="empty-list-msg">Unable to load inbox.</div>`;
  }
}

function startActivePolling() {
  if (!state.pollTimer) {
    state.pollTimer = setInterval(() => {
      loadQueue(false);
    }, 2500);
  }
}

function stopActivePolling() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

// Render left sidebar list
function renderQueue(items) {
  elements.queueCount.textContent = items.length;

  if (items.length === 0) {
    elements.queueList.innerHTML = `<div class="empty-list-msg">No emails found.</div>`;
    return;
  }

  elements.queueList.innerHTML = items.map(item => {
    const isActive = item.emailId === state.selectedEmailId ? 'active' : '';
    const dateFormatted = new Date(item.receivedAt).toLocaleDateString(undefined, {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    });

    const categoryBadges = (item.categories && item.categories.length > 0)
      ? item.categories.map(c => `<span class="pill pill-cat">${formatCategory(c)}</span>`).join(' ')
      : `<span class="pill pill-cat">${formatCategory(item.primaryCategory)}</span>`;

    let statusPill = '';
    if (item.inQueue || item.status === 'PROCESSING') {
      const pct = item.progressPercent || 25;
      statusPill = `<span class="pill pill-processing">Processing (${pct}%)</span>`;
    } else if (item.status === 'RECEIVED') {
      statusPill = `<span class="pill pill-subtle">Queued (15%)</span>`;
    } else {
      statusPill = `<span class="pill pill-subtle">${getFriendlyStatus(item.status)}</span>`;
    }

    return `
      <div class="email-item ${isActive}" data-id="${item.emailId}" onclick="selectEmail(${item.emailId})">
        <div class="email-item-header">
          <span class="email-sender">${escapeHtml(item.sender)}</span>
          <span class="email-time">${dateFormatted}</span>
        </div>
        <div class="email-subject">${escapeHtml(item.subject)}</div>
        <div class="email-item-footer">
          <div class="pill-group">${categoryBadges}</div>
          ${statusPill}
        </div>
      </div>
    `;
  }).join('');
}

// Select email item
async function selectEmail(emailId) {
  state.selectedEmailId = emailId;

  document.querySelectorAll('.email-item').forEach(el => {
    el.classList.toggle('active', parseInt(el.dataset.id, 10) === emailId);
  });

  await refreshSelectedDetail(emailId);
}

async function refreshSelectedDetail(emailId) {
  try {
    const res = await fetch(`/api/review-items/${emailId}`);
    const data = await res.json();
    if (data.success && data.data) {
      state.currentDetail = data.data;
      renderDetail(state.currentDetail);
    }
  } catch (err) {
    console.error('Failed to load email detail:', err);
  }
}

// Render full case workspace
function renderDetail(detail) {
  elements.emptyState.style.display = 'none';
  elements.detailContainer.style.display = 'flex';

  // Top Case Header
  elements.detailStatus.textContent = getFriendlyStatus(detail.status);
  elements.detailDate.textContent = new Date(detail.receivedAt).toLocaleString();
  elements.detailSubject.textContent = detail.subject;
  elements.detailSender.textContent = detail.sender;
  elements.detailEmailId.textContent = `#${detail.emailId}`;

  // AI Progress Bar Rendering
  const pct = detail.progressPercent || (detail.status === 'REVIEW_REQUIRED' || detail.status === 'REVIEWED' ? 100 : 25);
  const msg = detail.progressMessage || (pct === 100 ? 'AI analysis complete • Ready for human review' : 'Processing document with AI...');
  const isActivelyWorking = (detail.inQueue || detail.jobStatus === 'PROCESSING' || detail.status === 'PROCESSING');

  elements.progressBarFill.style.width = `${pct}%`;
  elements.progressPctBadge.textContent = `${pct}%`;
  elements.progressMessage.textContent = msg;
  elements.progressJobStatus.textContent = detail.jobStatus ? detail.jobStatus : (pct === 100 ? 'Complete' : 'Working');

  elements.progressBarFill.classList.toggle('active', isActivelyWorking);
  elements.progressDot.classList.toggle('active', isActivelyWorking);

  const ai = detail.aiResult;
  const fields = (ai && ai.extractedFields) ? ai.extractedFields : [];
  const classifications = (ai && ai.classifications) ? ai.classifications : [];

  // =========================================================================
  // SECTION 1 — AI ASSESSMENT + REVIEW STATUS
  // =========================================================================
  let primaryCat = 'NOT_RELEVANT';
  let primaryConf = 0.90;
  let primaryReason = 'No adverse event, product complaint, or medical information inquiry was identified.';

  if (classifications.length > 0) {
    const sorted = [...classifications].sort((a, b) => b.confidence - a.confidence);
    primaryCat = sorted[0].category;
    primaryConf = sorted[0].confidence;
    if (sorted[0].reason) primaryReason = sorted[0].reason;
  }

  // Card A: AI Assessment
  elements.heroCatLabel.textContent = formatCategory(primaryCat).toUpperCase();
  elements.heroCatCode.textContent = primaryCat;
  elements.heroConfBadge.textContent = `${Math.round(primaryConf * 100)}% confidence`;
  elements.heroReasonText.textContent = primaryReason;

  // Card B: Review Status
  if (detail.status === 'REVIEWED') {
    elements.heroStatusHeadline.innerHTML = `<span class="status-symbol">✓</span> <span id="hero-status-title">APPROVED BY REVIEWER</span>`;
    elements.heroActionDesc.textContent = 'Case findings have been verified and confirmed for downstream safety and quality processing.';
  } else if (detail.status === 'FAILED') {
    elements.heroStatusHeadline.innerHTML = `<span class="status-symbol">⚠</span> <span id="hero-status-title">CHECK FAILED</span>`;
    elements.heroActionDesc.textContent = 'AI processing encountered an error. Please inspect the documents and complete manual review.';
  } else if (isActivelyWorking) {
    elements.heroStatusHeadline.innerHTML = `<span class="status-symbol">⟳</span> <span id="hero-status-title">ANALYZING WITH AI</span>`;
    elements.heroActionDesc.textContent = 'AI is extracting clinical findings and validating facts against source text. Please wait.';
  } else {
    elements.heroStatusHeadline.innerHTML = `<span class="status-symbol">⚠</span> <span id="hero-status-title">HUMAN REVIEW REQUIRED</span>`;
    elements.heroActionDesc.textContent = 'Verify the classification and extracted findings against the source evidence before downstream processing.';
  }

  // =========================================================================
  // SECTION 2 — CASE SNAPSHOT
  // =========================================================================
  const primaryAttachment = (detail.attachments && detail.attachments.length > 0) ? detail.attachments[0] : null;
  const fileName = primaryAttachment ? primaryAttachment.filename : 'email_body.txt';
  let docType = 'Email Message Body';
  if (primaryAttachment && primaryAttachment.isPdf) {
    docType = 'Safety Report (PDF)';
  } else if (primaryAttachment) {
    docType = 'Document Attachment';
  }

  elements.snapshotFile.textContent = fileName;
  elements.snapshotSender.textContent = detail.sender || '-';
  elements.snapshotSubject.textContent = detail.subject || '-';
  elements.snapshotDocType.textContent = docType;
  elements.snapshotLanguage.textContent = 'English';
  elements.snapshotReceived.textContent = detail.receivedAt
    ? new Date(detail.receivedAt).toLocaleString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    : '-';

  // =========================================================================
  // SECTION 3 — WHY THIS CLASSIFICATION?
  // =========================================================================
  if (classifications.length > 0) {
    elements.execWhyContent.innerHTML = classifications.map(c => `
      <div class="why-row">
        <span class="why-cat-pill">${formatCategory(c.category)} (${c.category})</span>
        <span class="why-desc-text">${escapeHtml(c.reason || 'Classification supported by document evidence.')}</span>
      </div>
    `).join('');
  } else {
    elements.execWhyContent.innerHTML = `
      <div class="why-row">
        <span class="why-cat-pill">NOT_RELEVANT</span>
        <span class="why-desc-text">${escapeHtml(primaryReason)}</span>
      </div>
    `;
  }

  // =========================================================================
  // SECTION 4 — CLASSIFICATION SIGNALS (Matrix)
  // =========================================================================
  const standardCategories = [
    { code: 'ICSR', label: 'Patient Safety (ICSR)' },
    { code: 'PQC', label: 'Product Quality (PQC)' },
    { code: 'MI', label: 'Medical Inquiry (MI)' },
    { code: 'NOT_RELEVANT', label: 'Not Relevant' }
  ];

  elements.signalsTableBody.innerHTML = standardCategories.map(cat => {
    const matched = classifications.find(c => c.category === cat.code);
    if (matched) {
      const confPct = `${Math.round(matched.confidence * 100)}%`;
      return `
        <tr class="row-detected">
          <td><strong>${cat.label}</strong></td>
          <td>${confPct}</td>
          <td>
            <span class="signal-status detected">
              <span class="signal-bullet">●</span> Detected
            </span>
          </td>
        </tr>
      `;
    } else {
      return `
        <tr>
          <td>${cat.label}</td>
          <td class="text-muted">—</td>
          <td>
            <span class="signal-status not-detected">
              <span class="signal-bullet">○</span> Not detected
            </span>
          </td>
        </tr>
      `;
    }
  }).join('');

  // =========================================================================
  // SECTION 5 — DOMAIN-SPECIFIC FINDINGS
  // =========================================================================
  const detectedCodes = classifications.map(c => c.category);
  const isIcsr = detectedCodes.includes('ICSR');
  const isPqc = detectedCodes.includes('PQC');
  const isMi = detectedCodes.includes('MI');
  const isPureNotRelevant = (detectedCodes.includes('NOT_RELEVANT') || detectedCodes.length === 0) && !isIcsr && !isPqc && !isMi;

  let domainHtml = '';

  if (isPureNotRelevant) {
    elements.domainContextBadge.textContent = 'Not Relevant';
    domainHtml = `
      <div class="domain-not-relevant-box">
        <div class="domain-not-relevant-banner">
          No domain-specific case information was identified.
        </div>
        <div class="domain-na-list">
          <div class="domain-na-row">
            <span class="domain-na-label">Patient information</span>
            <span class="domain-na-value">Not applicable</span>
          </div>
          <div class="domain-na-row">
            <span class="domain-na-label">Product information</span>
            <span class="domain-na-value">Not applicable</span>
          </div>
          <div class="domain-na-row">
            <span class="domain-na-label">Reaction / issue</span>
            <span class="domain-na-value">Not applicable</span>
          </div>
          <div class="domain-na-row">
            <span class="domain-na-label">Batch / lot</span>
            <span class="domain-na-value">Not applicable</span>
          </div>
        </div>
      </div>
    `;
  } else {
    const badgeParts = [];
    if (isIcsr) badgeParts.push('Patient Safety');
    if (isPqc) badgeParts.push('Product Quality');
    if (isMi) badgeParts.push('Medical Inquiry');
    elements.domainContextBadge.textContent = badgeParts.join(' + ') || 'Clinical Findings';

    // 1. ICSR Case Findings
    if (isIcsr) {
      domainHtml += `
        <div class="domain-section-block">
          <div class="domain-section-title">Patient</div>
          <div class="domain-fields-grid">
            ${renderDomainTile('Age', findField(fields, 'patient', 'age'))}
            ${renderDomainTile('Sex', findField(fields, 'patient', 'sex'))}
            ${renderDomainTile('Weight', findField(fields, 'patient', 'weight'))}
            ${renderDomainTile('Height', findField(fields, 'patient', 'height'))}
            ${renderDomainTile('Medical History', findField(fields, 'patient', 'relevant_history'))}
          </div>
        </div>

        <div class="domain-section-block">
          <div class="domain-section-title">Reporter</div>
          <div class="domain-fields-grid">
            ${renderDomainTile('Reporter Identity', findField(fields, 'reporter', 'identity'))}
            ${renderDomainTile('Role', findField(fields, 'reporter', 'role'))}
            ${renderDomainTile('Country', findField(fields, 'reporter', 'country'))}
          </div>
        </div>

        <div class="domain-section-block">
          <div class="domain-section-title">Product</div>
          <div class="domain-fields-grid">
            ${renderDomainTile('Product', findField(fields, 'product', 'name'))}
            ${renderDomainTile('Dose', findField(fields, 'product', 'dose'))}
            ${renderDomainTile('Route', findField(fields, 'product', 'route'))}
            ${renderDomainTile('Start Date', findField(fields, 'product', 'start_date'))}
            ${renderDomainTile('Stop Date', findField(fields, 'product', 'stop_date'))}
          </div>
        </div>

        <div class="domain-section-block">
          <div class="domain-section-title">Reaction</div>
          <div class="domain-fields-grid">
            ${renderDomainTile('Reaction', findField(fields, 'reaction', 'description') || findField(fields, 'reaction', 'reaction'))}
            ${renderDomainTile('Onset', findField(fields, 'reaction', 'onset_date'))}
            ${renderDomainTile('Outcome', findField(fields, 'reaction', 'outcome'))}
            ${renderDomainTile('Seriousness', findField(fields, 'other', 'seriousness'))}
            ${renderDomainTile('Narrative', findField(fields, 'other', 'narrative'), true)}
          </div>
        </div>
      `;
    }

    // 2. PQC Case Findings
    if (isPqc) {
      domainHtml += `
        <div class="domain-section-block">
          <div class="domain-section-title">Product</div>
          <div class="domain-fields-grid">
            ${renderDomainTile('Product', findField(fields, 'pqc', 'product') || findField(fields, 'product', 'name'))}
            ${renderDomainTile('Batch / Lot', findField(fields, 'pqc', 'batch_lot') || findField(fields, 'product', 'batch_lot'))}
          </div>
        </div>

        <div class="domain-section-block">
          <div class="domain-section-title">Quality Issue</div>
          <div class="domain-fields-grid">
            ${renderDomainTile('Issue / Complaint', findField(fields, 'pqc', 'issue') || findField(fields, 'complaint', 'issue'))}
            ${renderDomainTile('Severity', findField(fields, 'pqc', 'severity') || findField(fields, 'complaint', 'severity'))}
          </div>
        </div>

        <div class="domain-section-block">
          <div class="domain-section-title">Supporting Evidence</div>
          <div class="domain-fields-grid">
            ${renderDomainTile('Photo Mentioned', findField(fields, 'pqc', 'photo_mentioned'))}
            ${renderDomainTile('Image Evidence', (ai.imageResults && ai.imageResults.length > 0) ? { value: `${ai.imageResults.length} image(s) processed` } : { value: 'None detected' })}
          </div>
        </div>
      `;
    }

    // 3. MI Case Findings
    if (isMi) {
      const qField = findField(fields, 'mi', 'questions');
      const qVal = (qField && qField.value && qField.value !== 'Not stated') ? qField.value : (detail.subject || 'Inquiry question not stated');
      domainHtml += `
        <div class="domain-section-block">
          <div class="domain-section-title">Medical Inquiry</div>
          <div class="mi-question-callout">
            <span class="mi-q-label">Inquiry Question(s)</span>
            <div class="mi-q-text">"${escapeHtml(qVal)}"</div>
          </div>
          <div class="domain-fields-grid" style="margin-top:0.6rem;">
            ${renderDomainTile('Product', findField(fields, 'mi', 'product') || findField(fields, 'product', 'name'))}
            ${renderDomainTile('Topic', findField(fields, 'mi', 'topic'))}
            ${renderDomainTile('Additional Context', findField(fields, 'mi', 'context'))}
          </div>
        </div>
      `;
    }
  }

  elements.domainFindingsContainer.innerHTML = domainHtml;

  // =========================================================================
  // SECTION 6 — DATA QUALITY & TRACEABILITY
  // =========================================================================
  const totalFields = fields.length;
  const supportedFields = fields.filter(f => f.sourceReferences && f.sourceReferences.length > 0).length;
  const notStatedFields = fields.filter(f => !f.value || f.value === 'Not stated').length;

  elements.traceStatTotal.textContent = totalFields;
  elements.traceStatSupported.textContent = supportedFields;
  elements.traceStatNotStated.textContent = notStatedFields;

  // =========================================================================
  // SECTION 7 — DETAILED AI NARRATIVE
  // =========================================================================
  if (ai && ai.summary) {
    elements.detailSummary.textContent = ai.summary;
  } else if (isActivelyWorking) {
    elements.detailSummary.textContent = 'Generating 10–15 sentence clinical narrative summary...';
  } else {
    elements.detailSummary.textContent = 'No narrative summary generated for this case.';
  }

  // =========================================================================
  // Granular Details Table (Below Executive Summary)
  // =========================================================================
  if (fields && fields.length > 0) {
    elements.factsTableBody.innerHTML = fields.map((f, fIdx) => {
      const isNotStated = (!f.value || f.value === 'Not stated');
      const valDisplay = isNotStated ? 'Not stated' : f.value;
      const valClass = isNotStated ? 'table-not-stated' : 'table-val';

      const sourceBtns = (f.sourceReferences && f.sourceReferences.length > 0)
        ? f.sourceReferences.map((s, sIdx) => {
            const label = s.sourceType === 'PDF' ? `Page ${s.pageNumber}` : `Email Body`;
            return `
              <button class="source-btn" onclick="inspectSource(${fIdx}, ${sIdx})">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                </svg>
                ${label}
              </button>
            `;
          }).join(' ')
        : `<span class="text-muted">—</span>`;

      return `
        <tr>
          <td class="table-group">${formatFieldGroup(f.fieldGroup)}</td>
          <td class="table-name">${formatFieldName(f.fieldName)}</td>
          <td class="${valClass}">${escapeHtml(valDisplay)}</td>
          <td>${sourceBtns}</td>
        </tr>
      `;
    }).join('');
  } else {
    elements.factsTableBody.innerHTML = isActivelyWorking
      ? `<tr><td colspan="4" class="empty-list-msg">Extracting clinical facts from document...</td></tr>`
      : `<tr><td colspan="4" class="empty-list-msg">No details found.</td></tr>`;
  }

  // Original Email Message Body
  elements.detailEmailBody.textContent = detail.body || '(No text content in this email)';

  // PDF Document Viewer
  const pdf = detail.attachments.find(a => a.isPdf);
  if (pdf) {
    state.activeAttachmentId = pdf.id;
    elements.docFilename.textContent = pdf.filename;
    const url = `/api/emails/${detail.emailId}/attachments/${pdf.id}/content`;
    elements.pdfViewerFrame.src = url;
    elements.btnOpenPdfTab.href = url;
    elements.btnOpenPdfTab.style.display = 'inline-flex';
  } else if (detail.attachments.length > 0) {
    const first = detail.attachments[0];
    elements.docFilename.textContent = first.filename;
    const url = `/api/emails/${detail.emailId}/attachments/${first.id}/content`;
    elements.pdfViewerFrame.src = url;
    elements.btnOpenPdfTab.href = url;
    elements.btnOpenPdfTab.style.display = 'inline-flex';
  } else {
    elements.docFilename.textContent = 'No attachment (Email Body Processed)';
    elements.pdfViewerFrame.src = 'about:blank';
    elements.btnOpenPdfTab.style.display = 'none';
  }

  // Case Timeline
  if (detail.auditHistory && detail.auditHistory.length > 0) {
    elements.auditTimeline.innerHTML = detail.auditHistory.map(log => {
      const timeStr = new Date(log.timestamp).toLocaleTimeString(undefined, {
        hour: '2-digit', minute: '2-digit', second: '2-digit'
      });
      const friendlyAction = getFriendlyActionName(log.action);
      let note = '';
      if (log.oldValue && log.newValue) {
        note = `Changed from ${log.oldValue} to ${log.newValue}`;
      } else if (log.metadata) {
        note = log.metadata;
      }

      return `
        <div class="timeline-row">
          <div>
            <span class="timeline-action">${friendlyAction}</span>
            <div class="timeline-desc">${escapeHtml(note)}</div>
          </div>
          <span class="timeline-time">${timeStr}</span>
        </div>
      `;
    }).join('');
  } else {
    elements.auditTimeline.innerHTML = `<div class="empty-list-msg">No activity recorded yet.</div>`;
  }
}

// Field Object Finder (exact matching with fallback)
function findField(fields, groupPattern, namePattern) {
  if (!fields || !Array.isArray(fields)) return null;
  const grp = groupPattern.toLowerCase();
  const name = namePattern.toLowerCase();

  // Try exact group and name
  let found = fields.find(f =>
    f.fieldGroup && f.fieldGroup.toLowerCase() === grp &&
    f.fieldName && f.fieldName.toLowerCase() === name
  );

  // If not found, try matching by name
  if (!found) {
    found = fields.find(f => f.fieldName && f.fieldName.toLowerCase() === name);
  }

  return found || null;
}

// Render Domain Tile with proof button
function renderDomainTile(label, fieldObj, isWide = false) {
  const val = (fieldObj && fieldObj.value && fieldObj.value.trim() !== '') ? fieldObj.value : 'Not stated';
  const isNotStated = (!fieldObj || !fieldObj.value || fieldObj.value === 'Not stated');
  const fieldId = fieldObj ? fieldObj.id : null;
  const hasSource = fieldObj && fieldObj.sourceReferences && fieldObj.sourceReferences.length > 0;

  let sourceBtn = '';
  if (hasSource && !isNotStated) {
    const src = fieldObj.sourceReferences[0];
    const srcLabel = src.sourceType === 'PDF' ? `Page ${src.pageNumber || 1}` : 'Email';
    sourceBtn = `
      <button class="source-btn" onclick="inspectSourceByFieldId(${fieldId})" title="Click to view evidence in document">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
        </svg>
        ${srcLabel}
      </button>
    `;
  }

  return `
    <div class="domain-field-tile ${isWide ? 'tile-wide' : ''}">
      <span class="domain-field-k">${label}</span>
      <div class="domain-field-v-row">
        <span class="domain-field-v ${isNotStated ? 'is-not-stated' : ''}">${escapeHtml(val)}</span>
        ${sourceBtn}
      </div>
    </div>
  `;
}

// Inspect source by field id
window.inspectSourceByFieldId = function(fieldId) {
  if (!state.currentDetail || !state.currentDetail.aiResult) return;
  const fields = state.currentDetail.aiResult.extractedFields || [];
  const field = fields.find(f => f.id === fieldId);
  if (!field || !field.sourceReferences || field.sourceReferences.length === 0) return;

  const source = field.sourceReferences[0];
  const originName = source.sourceType === 'PDF' ? `Document (Page ${source.pageNumber})` : 'Email Body';

  elements.inspectorBadge.textContent = originName;
  elements.inspectorBody.innerHTML = `
    <div>
      <div><strong>${formatFieldName(field.fieldName)}:</strong> "${escapeHtml(field.value)}"</div>
      <div class="inspector-quote">
        "${escapeHtml(source.textSnippet || 'Verbatim text referenced')}"
      </div>
    </div>
  `;

  // Navigate PDF to exact page
  if (source.sourceType === 'PDF' && state.activeAttachmentId && source.pageNumber) {
    elements.pdfViewerFrame.src = `/api/emails/${state.selectedEmailId}/attachments/${state.activeAttachmentId}/content#page=${source.pageNumber}`;
  }
};

// User clicks a proof source pill from table
window.inspectSource = function(fIdx, sIdx) {
  if (!state.currentDetail || !state.currentDetail.aiResult) return;
  const field = state.currentDetail.aiResult.extractedFields[fIdx];
  if (!field || !field.sourceReferences[sIdx]) return;

  const source = field.sourceReferences[sIdx];
  const originName = source.sourceType === 'PDF' ? `Document (Page ${source.pageNumber})` : 'Email Body';

  elements.inspectorBadge.textContent = originName;
  elements.inspectorBody.innerHTML = `
    <div>
      <div><strong>${formatFieldName(field.fieldName)}:</strong> "${escapeHtml(field.value)}"</div>
      <div class="inspector-quote">
        "${escapeHtml(source.textSnippet || 'Verbatim text referenced')}"
      </div>
    </div>
  `;

  // Navigate PDF to exact page
  if (source.sourceType === 'PDF' && state.activeAttachmentId && source.pageNumber) {
    elements.pdfViewerFrame.src = `/api/emails/${state.selectedEmailId}/attachments/${state.activeAttachmentId}/content#page=${source.pageNumber}`;
  }
};

// Open Edit modal
function openOverrideModal() {
  const detail = state.currentDetail;
  if (!detail || !detail.aiResult) return;

  const ai = detail.aiResult;
  const categories = (ai.classifications || []).map(c => c.category);

  elements.chkIcsr.checked = categories.includes('ICSR');
  elements.chkPqc.checked = categories.includes('PQC');
  elements.chkMi.checked = categories.includes('MI');
  elements.chkNotRelevant.checked = categories.includes('NOT_RELEVANT');

  elements.overrideJustification.value = '';

  elements.overrideFieldsList.innerHTML = (ai.extractedFields || []).map(f => `
    <div class="modal-field-item" data-id="${f.id}">
      <span title="${escapeHtml(f.fieldName)}">${formatFieldName(f.fieldName)}</span>
      <input type="text" class="text-input modal-field-input" value="${escapeHtml(f.value)}" />
    </div>
  `).join('');

  elements.overrideModal.style.display = 'flex';
}

function closeOverrideModal() {
  elements.overrideModal.style.display = 'none';
}

// Submit manual edits
async function submitOverride() {
  const justification = elements.overrideJustification.value.trim();
  if (!justification) {
    alert('Please enter a brief reason for this change.');
    return;
  }

  const reviewerId = elements.overrideReviewerId.value.trim() || 'Reviewer-01';

  const classifications = [];
  if (elements.chkIcsr.checked) classifications.push({ category: 'ICSR', confidence: 1.0, reason: justification });
  if (elements.chkPqc.checked) classifications.push({ category: 'PQC', confidence: 1.0, reason: justification });
  if (elements.chkMi.checked) classifications.push({ category: 'MI', confidence: 1.0, reason: justification });
  if (elements.chkNotRelevant.checked) classifications.push({ category: 'NOT_RELEVANT', confidence: 1.0, reason: justification });

  const fields = [];
  document.querySelectorAll('.modal-field-item').forEach(row => {
    const fieldId = parseInt(row.dataset.id, 10);
    const input = row.querySelector('.modal-field-input');
    const orig = state.currentDetail.aiResult.extractedFields.find(f => f.id === fieldId);
    if (orig && input.value !== orig.value) {
      fields.push({
        fieldId: fieldId,
        fieldGroup: orig.fieldGroup,
        fieldName: orig.fieldName,
        newValue: input.value,
        confidence: 1.0
      });
    }
  });

  const payload = {
    reviewerId: reviewerId,
    justification: justification,
    classifications: classifications,
    fields: fields
  };

  try {
    elements.btnSubmitOverride.disabled = true;
    elements.btnSubmitOverride.textContent = 'Saving...';

    const res = await fetch(`/api/review-items/${state.selectedEmailId}/override`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success && data.data) {
      state.currentDetail = data.data;
      renderDetail(state.currentDetail);
      closeOverrideModal();
      loadQueue(false);
      alert('Changes saved successfully.');
    } else {
      alert('Error saving changes: ' + (data.message || 'Unknown error'));
    }
  } catch (err) {
    alert('Failed to save changes: ' + err.message);
  } finally {
    elements.btnSubmitOverride.disabled = false;
    elements.btnSubmitOverride.textContent = 'Save Changes';
  }
}

// Plain English Formatters
function formatCategory(cat) {
  switch (cat) {
    case 'ICSR': return 'Patient Safety';
    case 'PQC': return 'Product Quality';
    case 'MI': return 'Medical Inquiry';
    case 'NOT_RELEVANT': return 'Not Relevant';
    default: return cat || 'General';
  }
}

function formatFieldGroup(group) {
  if (!group) return 'General';
  switch (group.toLowerCase()) {
    case 'patient': return 'Patient';
    case 'product': return 'Product';
    case 'reaction': return 'Reaction';
    case 'reporter': return 'Reporter';
    case 'complaint': return 'Quality Complaint';
    case 'pqc': return 'Product Quality';
    case 'mi': return 'Medical Inquiry';
    case 'inquiry': return 'Medical Inquiry';
    default: return group.charAt(0).toUpperCase() + group.slice(1);
  }
}

function formatFieldName(name) {
  if (!name) return '';
  return name
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, str => str.toUpperCase())
    .trim();
}

function getFriendlyStatus(status) {
  switch (status) {
    case 'REVIEW_REQUIRED': return 'Needs Review';
    case 'REVIEWED': return 'Approved';
    case 'RECEIVED': return 'In Queue';
    case 'PROCESSING': return 'Analyzing...';
    case 'FAILED': return 'Check Failed';
    default: return status;
  }
}

function getFriendlyActionName(action) {
  switch (action) {
    case 'EMAIL_INGESTED': return 'Email Received';
    case 'JOB_CREATED': return 'Document Queued';
    case 'JOB_QUEUED': return 'Queued for AI';
    case 'AI_STARTED': return 'AI Processing Started';
    case 'AI_COMPLETED': return 'Analyzed by AI';
    case 'REVIEW_ACCEPTED': return 'Approved by Reviewer';
    case 'REVIEW_OVERRIDE': return 'Updated by Reviewer';
    case 'JOB_RETRIED': return 'Reprocessed';
    default: return action;
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
