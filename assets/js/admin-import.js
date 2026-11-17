/**
 * CollegeHub Admin Data Import & Cutoff Approval Module
 * Provides CSV parsing, client & server validation preview, duplicate detection,
 * metadata tracking, and an administrator approval workflow.
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.CollegeHubImport = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {

  let parsedPreviewData = null;
  let activePreviewFilter = 'all';
  let selectedCsvContent = null;
  let selectedCsvFilename = null;

  // -------------------------------------------------------------------------
  // 1. Tab & Workspace Switching
  // -------------------------------------------------------------------------
  function switchAdminTab(tab) {
    const tabFaqs = document.getElementById('tab-content-faqs');
    const tabImport = document.getElementById('tab-content-import');
    const tabApprovals = document.getElementById('tab-content-approvals');

    const btnFaqs = document.getElementById('nav-btn-faqs');
    const btnImport = document.getElementById('nav-btn-import');
    const btnApprovals = document.getElementById('nav-btn-approvals');

    // Hide all
    if (tabFaqs) tabFaqs.classList.add('hidden');
    if (tabImport) tabImport.classList.add('hidden');
    if (tabApprovals) tabApprovals.classList.add('hidden');

    // Reset button styles
    [btnFaqs, btnImport, btnApprovals].forEach(btn => {
      if (btn) {
        btn.classList.remove('bg-secondary-container', 'text-on-secondary-container', 'font-bold');
        btn.classList.add('text-on-surface-variant', 'font-semibold');
      }
    });

    if (tab === 'import') {
      if (tabImport) tabImport.classList.remove('hidden');
      if (btnImport) {
        btnImport.classList.add('bg-secondary-container', 'text-on-secondary-container', 'font-bold');
        btnImport.classList.remove('text-on-surface-variant', 'font-semibold');
      }
      initImportDefaults();
    } else if (tab === 'approvals') {
      if (tabApprovals) tabApprovals.classList.remove('hidden');
      if (btnApprovals) {
        btnApprovals.classList.add('bg-secondary-container', 'text-on-secondary-container', 'font-bold');
        btnApprovals.classList.remove('text-on-surface-variant', 'font-semibold');
      }
      loadImportBatches();
    } else {
      if (tabFaqs) tabFaqs.classList.remove('hidden');
      if (btnFaqs) {
        btnFaqs.classList.add('bg-secondary-container', 'text-on-secondary-container', 'font-bold');
        btnFaqs.classList.remove('text-on-surface-variant', 'font-semibold');
      }
    }
  }

  function initImportDefaults() {
    const dateInput = document.getElementById('import-date-checked');
    if (dateInput && !dateInput.value) {
      dateInput.value = new Date().toISOString().split('T')[0];
    }
  }

  function prefillSampleSource() {
    const urlInput = document.getElementById('import-source-url');
    const yearInput = document.getElementById('import-academic-year');
    const dateInput = document.getElementById('import-date-checked');
    const batchNameInput = document.getElementById('import-batch-name');

    if (urlInput) urlInput.value = 'https://fe2024.mahacet.org/StaticPages/HomePage';
    if (yearInput) yearInput.value = '2024-2025';
    if (dateInput) dateInput.value = '2024-08-26';
    if (batchNameInput) batchNameInput.value = 'MHT-CET 2024 CAP Round II Official Cutoffs';

    showToast('Metadata Autofilled', 'Sample State CET Cell source URL and academic year populated.');
  }

  // -------------------------------------------------------------------------
  // 2. File Selection & Drag & Drop Handling
  // -------------------------------------------------------------------------
  function handleCsvFileSelect(event) {
    const files = event.target.files || (event.dataTransfer && event.dataTransfer.files);
    if (!files || files.length === 0) return;

    const file = files[0];
    if (!file.name.toLowerCase().endsWith('.csv')) {
      alert('Invalid file format. Please upload a comma-separated (.csv) file.');
      return;
    }

    selectedCsvFilename = file.name;
    const reader = new FileReader();
    reader.onload = function (e) {
      selectedCsvContent = e.target.result;
      updateFileSelectedUI(file.name, file.size);
    };
    reader.readAsText(file);
  }

  function updateFileSelectedUI(name, sizeBytes) {
    const infoZone = document.getElementById('csv-file-info');
    const nameEl = document.getElementById('csv-file-name');
    const sizeEl = document.getElementById('csv-file-size');
    const parseBtn = document.getElementById('btn-parse-csv');

    if (infoZone) infoZone.classList.remove('hidden');
    if (nameEl) nameEl.textContent = name;
    if (sizeEl) sizeEl.textContent = `${(sizeBytes / 1024).toFixed(1)} KB`;
    if (parseBtn) {
      parseBtn.disabled = false;
      parseBtn.classList.remove('opacity-50', 'cursor-not-allowed');
    }
  }

  function loadSampleCsvIntoForm() {
    fetch('/api/admin/import/sample')
      .then(res => res.text())
      .then(csv => {
        selectedCsvContent = csv;
        selectedCsvFilename = 'maharashtra_colleges_cutoffs_sample.csv';
        updateFileSelectedUI('maharashtra_colleges_cutoffs_sample.csv', csv.length);
        prefillSampleSource();
        showToast('Sample Loaded', 'Authentic Maharashtra sample CSV loaded. Click "Parse & Validate CSV" to preview.');
      })
      .catch(err => {
        alert('Failed to load sample CSV: ' + err.message);
      });
  }

  function loadDsySampleCsvIntoForm() {
    fetch('/api/admin/import/dsy-sample')
      .then(res => res.text())
      .then(csv => {
        selectedCsvContent = csv;
        selectedCsvFilename = 'maharashtra_dse_cutoffs_sample.csv';
        updateFileSelectedUI('maharashtra_dse_cutoffs_sample.csv', csv.length);
        const sourceInput = document.getElementById('import-source-title');
        if (sourceInput) sourceInput.value = 'State CET Cell Maharashtra - Direct Second Year Engineering (DSE) Centralized Admission Process 2024-25';
        showToast('DSY Sample Loaded', 'Direct Second Year Engineering (DSE) sample CSV loaded. Click "Parse & Validate CSV" to preview.');
      })
      .catch(err => {
        alert('Failed to load DSY sample CSV: ' + err.message);
      });
  }

  // -------------------------------------------------------------------------
  // 3. Parse & Preview CSV
  // -------------------------------------------------------------------------
  function parseAndPreviewCsv() {
    const urlInput = document.getElementById('import-source-url');
    const yearInput = document.getElementById('import-academic-year');
    const dateInput = document.getElementById('import-date-checked');
    const parseBtn = document.getElementById('btn-parse-csv');

    const sourceUrl = urlInput ? urlInput.value.trim() : '';
    const academicYear = yearInput ? yearInput.value.trim() : '';
    const dateChecked = dateInput ? dateInput.value.trim() : '';

    if (!selectedCsvContent) {
      alert('Please select or upload a CSV file first.');
      return;
    }

    if (!sourceUrl) {
      alert('Please provide the official Source URL where the data was verified.');
      if (urlInput) urlInput.focus();
      return;
    }

    if (!academicYear) {
      alert('Please enter or select the Academic Year (e.g., 2024-2025).');
      if (yearInput) yearInput.focus();
      return;
    }

    if (!dateChecked) {
      alert('Please provide the Date Checked (YYYY-MM-DD).');
      if (dateInput) dateInput.focus();
      return;
    }

    if (parseBtn) {
      parseBtn.disabled = true;
      parseBtn.innerHTML = '<span class="material-symbols-outlined text-base animate-spin">progress_activity</span> Validating...';
    }

    fetch('/api/admin/import/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        csv_text: selectedCsvContent,
        source_url: sourceUrl,
        academic_year: academicYear,
        date_checked: dateChecked
      })
    })
      .then(async res => {
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.message || 'Validation request failed.');
        }
        return data;
      })
      .then(preview => {
        parsedPreviewData = preview;
        renderPreviewResults(preview);
        showToast('CSV Analyzed', `${preview.summary.valid_rows} valid records found, ${preview.summary.error_rows} errors, ${preview.summary.duplicate_rows} duplicates.`);
      })
      .catch(err => {
        alert('CSV Validation Error: ' + err.message);
      })
      .finally(() => {
        if (parseBtn) {
          parseBtn.disabled = false;
          parseBtn.innerHTML = '<span class="material-symbols-outlined text-base">rule</span> Parse &amp; Validate CSV';
        }
      });
  }

  // -------------------------------------------------------------------------
  // 4. Render Validation Preview Table
  // -------------------------------------------------------------------------
  function renderPreviewResults(preview) {
    const previewContainer = document.getElementById('import-preview-section');
    if (!previewContainer) return;

    previewContainer.classList.remove('hidden');
    previewContainer.scrollIntoView({ behavior: 'smooth' });

    // Summary KPIs
    const totalEl = document.getElementById('preview-kpi-total');
    const validEl = document.getElementById('preview-kpi-valid');
    const errorEl = document.getElementById('preview-kpi-errors');
    const dupEl = document.getElementById('preview-kpi-duplicates');

    if (totalEl) totalEl.textContent = preview.summary.total_rows;
    if (validEl) validEl.textContent = preview.summary.valid_rows;
    if (errorEl) errorEl.textContent = preview.summary.error_rows;
    if (dupEl) dupEl.textContent = preview.summary.duplicate_rows;

    // Filter pill counts
    const countAllEl = document.getElementById('filter-count-all');
    const countValidEl = document.getElementById('filter-count-valid');
    const countErrorEl = document.getElementById('filter-count-errors');
    const countDupEl = document.getElementById('filter-count-duplicates');

    if (countAllEl) countAllEl.textContent = `(${preview.summary.total_rows})`;
    if (countValidEl) countValidEl.textContent = `(${preview.summary.valid_rows})`;
    if (countErrorEl) countErrorEl.textContent = `(${preview.summary.error_rows})`;
    if (countDupEl) countDupEl.textContent = `(${preview.summary.duplicate_rows})`;

    // Commit button update
    const commitBtn = document.getElementById('btn-commit-import');
    const commitCountEl = document.getElementById('commit-valid-count');
    if (commitBtn && commitCountEl) {
      commitCountEl.textContent = preview.summary.valid_rows;
      if (preview.summary.valid_rows > 0) {
        commitBtn.disabled = false;
        commitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
      } else {
        commitBtn.disabled = true;
        commitBtn.classList.add('opacity-50', 'cursor-not-allowed');
      }
    }

    renderPreviewTableRows();
  }

  function setPreviewFilter(filter) {
    activePreviewFilter = filter;
    ['all', 'valid', 'error', 'duplicate'].forEach(f => {
      const btn = document.getElementById(`filter-btn-${f}`);
      if (btn) {
        if (f === filter) {
          btn.classList.add('bg-secondary-container', 'text-on-secondary-container', 'font-bold');
          btn.classList.remove('bg-surface-container', 'text-on-surface-variant');
        } else {
          btn.classList.remove('bg-secondary-container', 'text-on-secondary-container', 'font-bold');
          btn.classList.add('bg-surface-container', 'text-on-surface-variant');
        }
      }
    });
    renderPreviewTableRows();
  }

  function renderPreviewTableRows() {
    if (!parsedPreviewData || !parsedPreviewData.rows) return;
    const tbody = document.getElementById('import-preview-tbody');
    if (!tbody) return;

    let filteredRows = parsedPreviewData.rows;
    if (activePreviewFilter !== 'all') {
      filteredRows = parsedPreviewData.rows.filter(r => r.status === activePreviewFilter);
    }

    if (filteredRows.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" class="text-center py-8 text-xs text-on-surface-variant">
            No records match the selected filter "${activePreviewFilter}".
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = filteredRows.map(row => {
      const d = row.data;
      let badgeClass = '';
      let badgeIcon = '';
      let badgeText = '';

      if (row.status === 'valid') {
        badgeClass = 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20';
        badgeIcon = 'check_circle';
        badgeText = 'Valid';
      } else if (row.status === 'error') {
        badgeClass = 'bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/20';
        badgeIcon = 'cancel';
        badgeText = 'Error';
      } else {
        badgeClass = 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/20';
        badgeIcon = 'warning';
        badgeText = 'Duplicate';
      }

      // Cutoff format
      let cutoffDisplay = '<span class="text-on-surface-variant italic">Unspecified (Pending)</span>';
      if (d.cutoff_value !== null && d.cutoff_value !== undefined) {
        if (d.score_type === 'percentile') {
          cutoffDisplay = `<strong class="text-primary font-bold">${Number(d.cutoff_value).toFixed(4)}%</strong>`;
        } else if (d.score_type === 'rank') {
          cutoffDisplay = `<strong class="text-primary font-bold">#${parseInt(d.cutoff_value, 10)}</strong> (Rank)`;
        } else {
          cutoffDisplay = `<strong class="text-primary font-bold">${d.cutoff_value}</strong> (Marks)`;
        }
      }

      // Fees format (never invent)
      let feesDisplay = '<span class="text-on-surface-variant italic">Unannounced</span>';
      if (d.annual_fees_inr !== null && d.annual_fees_inr !== undefined) {
        feesDisplay = `₹${Number(d.annual_fees_inr).toLocaleString('en-IN')}/yr`;
      }

      // Diagnostic message pills
      let issuesHtml = '';
      if (row.errors && row.errors.length > 0) {
        issuesHtml += row.errors.map(err => `
          <div class="text-[11px] text-rose-600 dark:text-rose-400 flex items-start gap-1 mt-0.5">
            <span class="material-symbols-outlined text-[13px] shrink-0 mt-0.5">error</span>
            <span>${err}</span>
          </div>
        `).join('');
      }
      if (row.warnings && row.warnings.length > 0) {
        issuesHtml += row.warnings.map(warn => `
          <div class="text-[11px] text-amber-600 dark:text-amber-400 flex items-start gap-1 mt-0.5">
            <span class="material-symbols-outlined text-[13px] shrink-0 mt-0.5">warning</span>
            <span>${warn}</span>
          </div>
        `).join('');
      }

      return `
        <tr class="hover:bg-surface-container-low transition-colors border-b border-surface-container-high/60 text-xs">
          <td class="py-3 px-4 font-mono font-bold text-on-surface-variant">#${row.row_number}</td>
          <td class="py-3 px-4">
            <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${badgeClass}">
              <span class="material-symbols-outlined text-[13px]">${badgeIcon}</span>
              ${badgeText}
            </span>
          </td>
          <td class="py-3 px-4">
            <div class="flex flex-col">
              <span class="font-bold text-primary">${d.college_name || '<em class="text-rose-500">Missing Name</em>'}</span>
              <span class="text-[11px] text-on-surface-variant">Code: <strong>${d.college_code || '—'}</strong> • ${d.city || '—'}</span>
            </div>
          </td>
          <td class="py-3 px-4">
            <div class="flex flex-col">
              <span class="font-semibold text-on-surface">${d.branch_name || d.branch_code || '—'}</span>
              <span class="text-[11px] text-on-surface-variant font-mono">${d.program} - ${d.branch_code}</span>
            </div>
          </td>
          <td class="py-3 px-4">
            <span class="px-2 py-0.5 rounded bg-surface-container font-mono text-[11px] font-bold text-secondary mr-1">${d.exam}</span>
            <span class="font-bold text-on-surface">${d.category}</span>
            <span class="text-on-surface-variant text-[11px]">(${d.quota})</span>
          </td>
          <td class="py-3 px-4">
            <span class="text-on-surface-variant font-medium">${d.round}</span>
          </td>
          <td class="py-3 px-4">
            <div>${cutoffDisplay}</div>
            <div class="text-[10px] text-on-surface-variant mt-0.5">${feesDisplay}</div>
          </td>
          <td class="py-3 px-4 max-w-xs">
            ${issuesHtml || '<span class="text-emerald-600 dark:text-emerald-400 text-[11px] font-medium flex items-center gap-1"><span class="material-symbols-outlined text-xs">check</span> All fields verified</span>'}
          </td>
        </tr>
      `;
    }).join('');
  }

  // -------------------------------------------------------------------------
  // 5. Commit Valid Import Records
  // -------------------------------------------------------------------------
  function commitImportBatch() {
    if (!parsedPreviewData || !parsedPreviewData.rows) {
      alert('No parsed data available to import.');
      return;
    }

    const validRows = parsedPreviewData.rows
      .filter(r => r.status === 'valid')
      .map(r => r.data);

    if (validRows.length === 0) {
      alert('There are no valid records to import. Please correct errors and re-upload.');
      return;
    }

    const batchNameInput = document.getElementById('import-batch-name');
    const customBatchName = batchNameInput ? batchNameInput.value.trim() : '';

    const commitBtn = document.getElementById('btn-commit-import');
    if (commitBtn) {
      commitBtn.disabled = true;
      commitBtn.innerHTML = '<span class="material-symbols-outlined text-base animate-spin">progress_activity</span> Importing...';
    }

    fetch('/api/admin/import/commit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        valid_rows: validRows,
        source_url: parsedPreviewData.metadata.source_url,
        academic_year: parsedPreviewData.metadata.academic_year,
        date_checked: parsedPreviewData.metadata.date_checked,
        batch_name: customBatchName
      })
    })
      .then(async res => {
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.message || 'Failed to commit import.');
        }
        return data;
      })
      .then(res => {
        showToast('Batch Imported', `${res.data.count} records imported into Approval Queue (Pending Approval).`);
        // Reset preview state
        parsedPreviewData = null;
        selectedCsvContent = null;
        selectedCsvFilename = null;
        const previewContainer = document.getElementById('import-preview-section');
        if (previewContainer) previewContainer.classList.add('hidden');
        const fileInfo = document.getElementById('csv-file-info');
        if (fileInfo) fileInfo.classList.add('hidden');
        const fileInput = document.getElementById('csv-file-input');
        if (fileInput) fileInput.value = '';

        // Switch automatically to Approval Queue tab
        switchAdminTab('approvals');
      })
      .catch(err => {
        alert('Import Commit Failed: ' + err.message);
      })
      .finally(() => {
        if (commitBtn) {
          commitBtn.disabled = false;
          commitBtn.innerHTML = '<span class="material-symbols-outlined text-base">cloud_upload</span> Import Valid Records (Pending Approval)';
        }
      });
  }

  // -------------------------------------------------------------------------
  // 6. Approval Queue Workflow
  // -------------------------------------------------------------------------
  function loadImportBatches() {
    const listContainer = document.getElementById('approval-batches-list');
    if (!listContainer) return;

    listContainer.innerHTML = `
      <div class="p-8 text-center text-on-surface-variant flex flex-col items-center gap-2">
        <span class="material-symbols-outlined text-2xl animate-spin text-secondary">progress_activity</span>
        <span class="text-xs">Loading import batches from knowledge matrix...</span>
      </div>
    `;

    fetch('/api/admin/import/batches')
      .then(res => res.json())
      .then(res => {
        if (!res.data || res.data.length === 0) {
          listContainer.innerHTML = `
            <div class="p-10 text-center bg-surface-container-lowest rounded-3xl border border-surface-container-high">
              <span class="material-symbols-outlined text-4xl text-outline mb-2">inventory_2</span>
              <h4 class="text-sm font-bold text-primary">No Import Batches Found</h4>
              <p class="text-xs text-on-surface-variant mt-1">Upload a Maharashtra colleges &amp; cutoffs CSV file to create your first batch.</p>
              <button onclick="CollegeHubImport.switchAdminTab('import')" class="mt-4 px-4 py-2 rounded-xl bg-secondary text-on-secondary text-xs font-bold hover:bg-secondary/90 transition-all inline-flex items-center gap-1.5 shadow-sm">
                <span class="material-symbols-outlined text-sm">upload_file</span>
                <span>Go to Data Import</span>
              </button>
            </div>
          `;
          return;
        }

        renderBatchCards(res.data);
      })
      .catch(err => {
        listContainer.innerHTML = `
          <div class="p-6 text-center text-error bg-error-container/20 rounded-2xl border border-error/30 text-xs font-semibold">
            Failed to load import batches: ${err.message}
          </div>
        `;
      });
  }

  function renderBatchCards(batches) {
    const listContainer = document.getElementById('approval-batches-list');
    if (!listContainer) return;

    listContainer.innerHTML = batches.map(batch => {
      const isApproved = batch.status === 'approved';
      const isRejected = batch.status === 'rejected';
      const isPending = !isApproved && !isRejected;

      let statusPill = '';
      if (isApproved) {
        statusPill = `<span class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Approved &amp; Published
        </span>`;
      } else if (isRejected) {
        statusPill = `<span class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-rose-500/10 text-rose-700 dark:text-rose-300 border border-rose-500/20">
          <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span> Rejected
        </span>`;
      } else {
        statusPill = `<span class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/20 animate-pulse">
          <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span> Pending Approval
        </span>`;
      }

      return `
        <div class="bg-surface-container-lowest p-6 rounded-3xl shadow-xs border border-surface-container-high flex flex-col justify-between gap-4 transition-all hover:shadow-md">
          <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
            <div>
              <div class="flex items-center gap-2.5 flex-wrap">
                <h4 class="text-base font-extrabold text-primary tracking-tight">${batch.batch_name}</h4>
                ${statusPill}
              </div>
              <p class="text-xs text-on-surface-variant mt-1">
                Academic Year: <strong class="text-on-surface">${batch.academic_year}</strong> • 
                Date Checked: <strong class="text-on-surface">${batch.date_checked}</strong> • 
                Uploaded by: <strong class="text-on-surface">${batch.uploaded_by || 'Admin'}</strong>
              </p>
              <div class="mt-2 text-xs flex items-center gap-1 text-secondary truncate max-w-xl">
                <span class="material-symbols-outlined text-[15px] shrink-0">link</span>
                <a href="${batch.source_url}" target="_blank" rel="noopener noreferrer" class="hover:underline truncate">${batch.source_url}</a>
              </div>
            </div>

            <!-- Metrics Pills -->
            <div class="flex items-center gap-3 shrink-0">
              <div class="bg-surface-container px-3.5 py-1.5 rounded-xl text-center">
                <span class="block text-xs font-extrabold text-primary">${batch.records_count || batch.total_rows || 0}</span>
                <span class="block text-[10px] text-on-surface-variant uppercase font-semibold">Total Records</span>
              </div>
              <div class="bg-amber-500/10 px-3.5 py-1.5 rounded-xl text-center border border-amber-500/20">
                <span class="block text-xs font-extrabold text-amber-700 dark:text-amber-300">${batch.pending_count || 0}</span>
                <span class="block text-[10px] text-amber-600 dark:text-amber-400 uppercase font-semibold">Pending</span>
              </div>
              <div class="bg-emerald-500/10 px-3.5 py-1.5 rounded-xl text-center border border-emerald-500/20">
                <span class="block text-xs font-extrabold text-emerald-700 dark:text-emerald-300">${batch.approved_count || 0}</span>
                <span class="block text-[10px] text-emerald-600 dark:text-emerald-400 uppercase font-semibold">Live Matrix</span>
              </div>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="pt-3 border-t border-surface-container-high/60 flex flex-wrap items-center justify-between gap-3">
            <div class="text-[11px] text-on-surface-variant">
              Batch ID: <span class="font-mono">${batch.id.substring(0, 8)}...</span>
              ${batch.approved_at ? ` • Approved ${new Date(batch.approved_at).toLocaleDateString()}` : ''}
            </div>

            <div class="flex items-center gap-2">
              <button onclick="CollegeHubImport.viewBatchDetails('${batch.id}')" class="px-3.5 py-1.5 rounded-xl bg-surface-container hover:bg-surface-container-high text-xs font-semibold text-primary transition-all flex items-center gap-1.5 border border-surface-container-high">
                <span class="material-symbols-outlined text-sm">visibility</span>
                <span>Review Records</span>
              </button>

              ${isPending ? `
                <button onclick="CollegeHubImport.approveBatch('${batch.id}')" class="px-4 py-1.5 rounded-xl bg-secondary hover:bg-secondary/90 text-on-secondary text-xs font-bold transition-all shadow-xs flex items-center gap-1.5">
                  <span class="material-symbols-outlined text-sm">check_circle</span>
                  <span>Approve &amp; Publish to Recommendations</span>
                </button>
                <button onclick="CollegeHubImport.rejectBatch('${batch.id}')" class="px-3 py-1.5 rounded-xl bg-error-container/40 hover:bg-error-container text-error text-xs font-bold transition-all flex items-center gap-1">
                  <span class="material-symbols-outlined text-sm">block</span>
                  <span>Reject</span>
                </button>
              ` : ''}
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  function approveBatch(batchId) {
    if (!confirm('Are you sure you want to approve this cutoff batch? All pending records will be published immediately to active student recommendations.')) {
      return;
    }

    fetch(`/api/admin/import/batches/${batchId}/approve`, {
      method: 'POST'
    })
      .then(res => res.json())
      .then(res => {
        showToast('Batch Approved', `${res.data.approved_count} records published to active student recommendations matrix.`);
        loadImportBatches();
      })
      .catch(err => {
        alert('Approval failed: ' + err.message);
      });
  }

  function rejectBatch(batchId) {
    if (!confirm('Are you sure you want to reject this batch? Records will not be published to students.')) {
      return;
    }

    fetch(`/api/admin/import/batches/${batchId}/reject`, {
      method: 'POST'
    })
      .then(res => res.json())
      .then(res => {
        showToast('Batch Rejected', 'Batch status set to rejected.');
        loadImportBatches();
      })
      .catch(err => {
        alert('Rejection failed: ' + err.message);
      });
  }

  function viewBatchDetails(batchId) {
    const modal = document.getElementById('batch-details-modal');
    const titleEl = document.getElementById('batch-modal-title');
    const tbody = document.getElementById('batch-modal-tbody');

    if (!modal) return;
    modal.classList.remove('hidden');

    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-xs text-on-surface-variant animate-pulse">Loading batch records...</td></tr>`;
    }

    fetch(`/api/admin/import/batches/${batchId}`)
      .then(res => res.json())
      .then(res => {
        const batch = res.data.batch;
        const records = res.data.records || [];

        if (titleEl) {
          titleEl.textContent = `${batch.batch_name} (${records.length} records)`;
        }

        if (tbody) {
          if (records.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-xs text-on-surface-variant">No records found in this batch.</td></tr>`;
            return;
          }

          tbody.innerHTML = records.map((r, i) => `
            <tr class="hover:bg-surface-container-low transition-colors border-b border-surface-container-high/60 text-xs">
              <td class="py-2.5 px-3 font-mono font-bold text-on-surface-variant">#${i + 1}</td>
              <td class="py-2.5 px-3">
                <div class="font-bold text-primary">${r.college_name}</div>
                <div class="text-[10px] text-on-surface-variant">Code: ${r.college_code} • ${r.city}</div>
              </td>
              <td class="py-2.5 px-3 font-medium">${r.branch_name} (${r.branch_code})</td>
              <td class="py-2.5 px-3 font-mono">${r.exam} / ${r.category} (${r.quota})</td>
              <td class="py-2.5 px-3">${r.round}</td>
              <td class="py-2.5 px-3 font-bold text-primary">
                ${r.cutoff_value !== null ? (r.score_type === 'percentile' ? `${r.cutoff_value}%` : `#${r.cutoff_value}`) : '<span class="text-on-surface-variant italic font-normal">Pending</span>'}
              </td>
              <td class="py-2.5 px-3">
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${r.status === 'approved' ? 'bg-emerald-500/10 text-emerald-700' : 'bg-amber-500/10 text-amber-700'}">
                  ${r.status}
                </span>
              </td>
            </tr>
          `).join('');
        }
      })
      .catch(err => {
        if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-xs text-error">Failed: ${err.message}</td></tr>`;
      });
  }

  function closeBatchDetailsModal() {
    const modal = document.getElementById('batch-details-modal');
    if (modal) modal.classList.add('hidden');
  }

  // -------------------------------------------------------------------------
  // 7. Column Specifications & Dictionary Modal
  // -------------------------------------------------------------------------
  function openColumnGuide() {
    const modal = document.getElementById('column-guide-modal');
    if (modal) modal.classList.remove('hidden');
  }

  function closeColumnGuide() {
    const modal = document.getElementById('column-guide-modal');
    if (modal) modal.classList.add('hidden');
  }

  // -------------------------------------------------------------------------
  // 8. Public API Export
  // -------------------------------------------------------------------------
  return {
    switchAdminTab,
    prefillSampleSource,
    handleCsvFileSelect,
    loadSampleCsvIntoForm,
    loadDsySampleCsvIntoForm,
    parseAndPreviewCsv,
    setPreviewFilter,
    commitImportBatch,
    loadImportBatches,
    approveBatch,
    rejectBatch,
    viewBatchDetails,
    closeBatchDetailsModal,
    openColumnGuide,
    closeColumnGuide
  };
});
