document.addEventListener('DOMContentLoaded', () => {
    // State
    const state = {
        search: '',
        dateRange: 'all',
        dateStart: '',
        dateEnd: '',
        manufacturer: 'All',
        missingMsrpOnly: false,
        sortBy: 'created_at',
        sortOrder: 'desc',
        selectedFile: null,
        activeEditItem: null,
        catalogItems: []
    };

    // DOM Elements
    const statTotalItems = document.getElementById('statTotalItems');
    const statAddedToday = document.getElementById('statAddedToday');
    const statMissingMsrp = document.getElementById('statMissingMsrp');
    const cardMissingMsrp = document.getElementById('cardMissingMsrp');

    const searchInput = document.getElementById('searchInput');
    const sortSelect = document.getElementById('sortSelect');
    const brandFilterContainer = document.getElementById('brandFilterContainer');
    const chkMissingMsrp = document.getElementById('chkMissingMsrp');
    const datePills = document.querySelectorAll('.date-pills .pill-btn');
    const customDateRow = document.getElementById('customDateRow');
    const dateStartInput = document.getElementById('dateStart');
    const dateEndInput = document.getElementById('dateEnd');
    const btnApplyDateFilter = document.getElementById('btnApplyDateFilter');
    const btnClearDateFilter = document.getElementById('btnClearDateFilter');

    const catalogTableBody = document.getElementById('catalogTableBody');
    const recordCountBadge = document.getElementById('recordCountBadge');
    const btnExportExcel = document.getElementById('btnExportExcel');
    const sortableHeaders = document.querySelectorAll('th.sortable');

    // Upload Modal
    const btnOpenUploadModal = document.getElementById('btnOpenUploadModal');
    const uploadModal = document.getElementById('uploadModal');
    const btnCloseUploadModal = document.getElementById('btnCloseUploadModal');
    const btnCancelUpload = document.getElementById('btnCancelUpload');
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const selectedFileBanner = document.getElementById('selectedFileBanner');
    const selectedFileName = document.getElementById('selectedFileName');
    const selectedFileSize = document.getElementById('selectedFileSize');
    const btnRemoveSelectedFile = document.getElementById('btnRemoveSelectedFile');
    const processingBox = document.getElementById('processingBox');
    const btnSubmitUpload = document.getElementById('btnSubmitUpload');

    // Results Modal
    const resultsModal = document.getElementById('resultsModal');
    const btnCloseResultsModal = document.getElementById('btnCloseResultsModal');
    const btnFinishResults = document.getElementById('btnFinishResults');
    const resTotalItems = document.getElementById('resTotalItems');
    const resNewItems = document.getElementById('resNewItems');
    const resExistingItems = document.getElementById('resExistingItems');
    const resMissingMsrp = document.getElementById('resMissingMsrp');
    const modalMissingAlert = document.getElementById('modalMissingAlert');

    // Edit Modal
    const editModal = document.getElementById('editModal');
    const btnCloseEditModal = document.getElementById('btnCloseEditModal');
    const btnCancelEdit = document.getElementById('btnCancelEdit');
    const btnSaveEdit = document.getElementById('btnSaveEdit');
    const editItemName = document.getElementById('editItemName');
    const editItemSku = document.getElementById('editItemSku');
    const editItemCost = document.getElementById('editItemCost');
    const editItemPrice = document.getElementById('editItemPrice');

    // ==========================================
    // INITIALIZATION & STATS
    // ==========================================
    async function fetchStats() {
        try {
            const res = await fetch('/api/stats');
            const data = await res.json();
            if (data.success) {
                const s = data.stats;
                statTotalItems.textContent = s.total_items.toLocaleString();
                statAddedToday.textContent = s.added_today.toLocaleString();
                statMissingMsrp.textContent = s.missing_msrp.toLocaleString();

                renderBrandPills(s.manufacturers || []);
            }
        } catch (err) {
            console.error('Error fetching stats:', err);
        }
    }

    function renderBrandPills(manufacturers) {
        brandFilterContainer.innerHTML = '<span class="filter-label">Brand:</span>';
        
        const allBtn = document.createElement('button');
        allBtn.className = `brand-pill ${state.manufacturer === 'All' ? 'active' : ''}`;
        allBtn.dataset.brand = 'All';
        allBtn.textContent = 'All Brands';
        allBtn.onclick = () => selectBrand('All');
        brandFilterContainer.appendChild(allBtn);

        manufacturers.forEach(m => {
            const btn = document.createElement('button');
            btn.className = `brand-pill ${state.manufacturer === m ? 'active' : ''}`;
            btn.dataset.brand = m;
            btn.textContent = m;
            btn.onclick = () => selectBrand(m);
            brandFilterContainer.appendChild(btn);
        });
    }

    function selectBrand(brand) {
        state.manufacturer = brand;
        document.querySelectorAll('.brand-pill').forEach(b => {
            b.classList.toggle('active', b.dataset.brand === brand);
        });
        fetchCatalog();
    }

    // ==========================================
    // CATALOG FETCHING & RENDERING
    // ==========================================
    async function fetchCatalog() {
        catalogTableBody.innerHTML = `
            <tr>
                <td colspan="7" class="loading-state">
                    <div class="spinner"></div>
                    <p>Loading catalog items...</p>
                </td>
            </tr>
        `;

        const params = new URLSearchParams();
        if (state.search) params.append('search', state.search);
        if (state.dateStart) params.append('date_start', state.dateStart);
        if (state.dateEnd) params.append('date_end', state.dateEnd);
        if (state.manufacturer && state.manufacturer !== 'All') params.append('manufacturer', state.manufacturer);
        if (state.missingMsrpOnly) params.append('missing_msrp', 'true');

        try {
            const res = await fetch(`/api/catalog?${params.toString()}`);
            const data = await res.json();

            if (data.success) {
                state.catalogItems = data.data || [];
                sortAndRenderCatalog();
                recordCountBadge.textContent = `${data.total.toLocaleString()} records`;
            } else {
                catalogTableBody.innerHTML = `<tr><td colspan="7" class="loading-state text-accent">Error loading catalog: ${data.error}</td></tr>`;
            }
        } catch (err) {
            console.error('Error loading catalog:', err);
            catalogTableBody.innerHTML = `<tr><td colspan="7" class="loading-state text-accent">Failed to connect to server.</td></tr>`;
        }
    }

    function sortAndRenderCatalog() {
        const sorted = [...state.catalogItems].sort((a, b) => {
            let valA = a[state.sortBy];
            let valB = b[state.sortBy];

            // Handle null/numeric
            if (valA === null || valA === undefined) valA = (state.sortOrder === 'asc' ? Infinity : -Infinity);
            if (valB === null || valB === undefined) valB = (state.sortOrder === 'asc' ? Infinity : -Infinity);

            if (typeof valA === 'string') {
                valA = valA.toLowerCase();
                valB = String(valB).toLowerCase();
                return state.sortOrder === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
            } else {
                return state.sortOrder === 'asc' ? (valA - valB) : (valB - valA);
            }
        });

        renderCatalogRows(sorted);
        updateHeaderSortIcons();
    }

    function renderCatalogRows(items) {
        if (!items || items.length === 0) {
            catalogTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="loading-state">
                        <p style="font-size: 1.05rem; margin-bottom: 0.3rem;">🔍 No matching catalog items found.</p>
                        <span style="font-size: 0.82rem; color: var(--text-muted);">Try clearing filters or search keywords.</span>
                    </td>
                </tr>
            `;
            return;
        }

        catalogTableBody.innerHTML = items.map(item => {
            const brandClass = getBrandBadgeClass(item.manufacturer);
            const hasMsrp = item.price !== null && item.price !== undefined && item.price > 0;
            
            const msrpDisplay = hasMsrp
                ? `<span class="price-cell" title="Click to edit" onclick="openEditModal('${item.id}', '${escapeHtml(item.name)}', '${item.supplier_sku}', '${item.cost || 0}', '${item.price}')">$${Number(item.price).toFixed(2)}</span>`
                : `<span class="badge-missing-msrp" onclick="openEditModal('${item.id}', '${escapeHtml(item.name)}', '${item.supplier_sku}', '${item.cost || 0}', '')">⚠️ Missing MSRP</span>`;

            const costDisplay = item.cost ? `$${Number(item.cost).toFixed(2)}` : '-';

            return `
                <tr data-id="${item.id}">
                    <td>
                        <span class="sku-code">${escapeHtml(item.supplier_sku || '')}</span>
                    </td>
                    <td>
                        <div class="prod-name">${escapeHtml(item.name || '')}</div>
                        ${item.mpn ? `<span style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono);">MPN: ${escapeHtml(item.mpn)}</span>` : ''}
                    </td>
                    <td>
                        <span class="brand-badge ${brandClass}">${escapeHtml(item.manufacturer || 'Other')}</span>
                    </td>
                    <td class="cost-cell">${costDisplay}</td>
                    <td style="text-align: right;">${msrpDisplay}</td>
                    <td class="date-cell">${item.created_date || '-'}</td>
                    <td>
                        <div class="action-btns">
                            <button class="btn-icon" title="Edit MSRP" onclick="openEditModal('${item.id}', '${escapeHtml(item.name)}', '${item.supplier_sku}', '${item.cost || 0}', '${item.price || ''}')">
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M12 20h9"></path>
                                    <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                                </svg>
                            </button>
                            <button class="btn-icon" title="Re-scrape from Hitfar" onclick="rescrapeSku('${item.id}', '${escapeHtml(item.hitfar_sku)}')">
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <polyline points="23 4 23 10 17 10"></polyline>
                                    <polyline points="1 20 1 14 7 14"></polyline>
                                    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                                </svg>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    function getBrandBadgeClass(brand) {
        if (!brand) return 'brand-other';
        const b = brand.toLowerCase();
        if (b.includes('hypergear')) return 'brand-hypergear';
        if (b.includes('zagg')) return 'brand-zagg';
        if (b.includes('gear4')) return 'brand-gear4';
        if (b.includes('spectrum')) return 'brand-spectrum';
        if (b.includes('marley')) return 'brand-marley';
        return 'brand-other';
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

    // ==========================================
    // SORTING CONTROLLERS
    // ==========================================
    sortableHeaders.forEach(th => {
        th.addEventListener('click', () => {
            const field = th.dataset.sort;
            if (state.sortBy === field) {
                state.sortOrder = state.sortOrder === 'asc' ? 'desc' : 'asc';
            } else {
                state.sortBy = field;
                state.sortOrder = (field === 'price' || field === 'cost' || field === 'created_date') ? 'desc' : 'asc';
            }
            syncSortDropdown();
            sortAndRenderCatalog();
        });
    });

    sortSelect.addEventListener('change', (e) => {
        const val = e.target.value;
        const lastUnderscore = val.lastIndexOf('_');
        state.sortBy = val.substring(0, lastUnderscore);
        state.sortOrder = val.substring(lastUnderscore + 1);
        sortAndRenderCatalog();
    });

    function syncSortDropdown() {
        const key = `${state.sortBy}_${state.sortOrder}`;
        if (sortSelect.querySelector(`option[value="${key}"]`)) {
            sortSelect.value = key;
        }
    }

    function updateHeaderSortIcons() {
        sortableHeaders.forEach(th => {
            const field = th.dataset.sort;
            th.classList.remove('sort-asc', 'sort-desc');
            const icon = th.querySelector('.sort-icon');
            if (state.sortBy === field) {
                th.classList.add(state.sortOrder === 'asc' ? 'sort-asc' : 'sort-desc');
                icon.textContent = state.sortOrder === 'asc' ? '▲' : '▼';
            } else {
                icon.textContent = '▲▼';
            }
        });
    }

    // ==========================================
    // FILTER EVENTS
    // ==========================================
    let searchTimeout = null;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            state.search = e.target.value.trim();
            fetchCatalog();
        }, 250);
    });

    datePills.forEach(pill => {
        pill.addEventListener('click', () => {
            const range = pill.dataset.range;
            if (pill.id === 'btnCustomDate') {
                customDateRow.classList.toggle('hidden');
                return;
            }

            datePills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            customDateRow.classList.add('hidden');

            state.dateRange = range;
            calculateDateBounds(range);
            fetchCatalog();
        });
    });

    function calculateDateBounds(range) {
        const today = new Date();
        const formatDate = (d) => d.toISOString().split('T')[0];

        if (range === 'all') {
            state.dateStart = '';
            state.dateEnd = '';
        } else if (range === 'today') {
            state.dateStart = formatDate(today);
            state.dateEnd = formatDate(today);
        } else if (range === '7d') {
            const past7 = new Date();
            past7.setDate(today.getDate() - 7);
            state.dateStart = formatDate(past7);
            state.dateEnd = formatDate(today);
        } else if (range === '30d') {
            const past30 = new Date();
            past30.setDate(today.getDate() - 30);
            state.dateStart = formatDate(past30);
            state.dateEnd = formatDate(today);
        }
    }

    btnApplyDateFilter.addEventListener('click', () => {
        state.dateStart = dateStartInput.value;
        state.dateEnd = dateEndInput.value;
        datePills.forEach(p => p.classList.remove('active'));
        document.getElementById('btnCustomDate').classList.add('active');
        fetchCatalog();
    });

    btnClearDateFilter.addEventListener('click', () => {
        dateStartInput.value = '';
        dateEndInput.value = '';
        state.dateStart = '';
        state.dateEnd = '';
        customDateRow.classList.add('hidden');
        document.querySelector('[data-range="all"]').click();
    });

    chkMissingMsrp.addEventListener('change', (e) => {
        state.missingMsrpOnly = e.target.checked;
        fetchCatalog();
    });

    cardMissingMsrp.addEventListener('click', () => {
        chkMissingMsrp.checked = !chkMissingMsrp.checked;
        state.missingMsrpOnly = chkMissingMsrp.checked;
        fetchCatalog();
    });

    // ==========================================
    // EXPORT TO EXCEL
    // ==========================================
    btnExportExcel.addEventListener('click', () => {
        const params = new URLSearchParams();
        if (state.search) params.append('search', state.search);
        if (state.dateStart) params.append('date_start', state.dateStart);
        if (state.dateEnd) params.append('date_end', state.dateEnd);
        if (state.manufacturer && state.manufacturer !== 'All') params.append('manufacturer', state.manufacturer);
        if (state.missingMsrpOnly) params.append('missing_msrp', 'true');

        window.location.href = `/api/export?${params.toString()}`;
    });

    // ==========================================
    // UPLOAD PDF INGESTION FLOW
    // ==========================================
    btnOpenUploadModal.addEventListener('click', () => {
        resetUploadModal();
        uploadModal.classList.remove('hidden');
    });

    btnCloseUploadModal.addEventListener('click', () => uploadModal.classList.add('hidden'));
    btnCancelUpload.addEventListener('click', () => uploadModal.classList.add('hidden'));

    function resetUploadModal() {
        state.selectedFile = null;
        fileInput.value = '';
        selectedFileBanner.classList.add('hidden');
        dropZone.classList.remove('hidden');
        processingBox.classList.add('hidden');
        btnSubmitUpload.disabled = true;
        btnSubmitUpload.textContent = 'Process & Ingest';
    }

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
            handleFileSelect(e.target.files[0]);
        }
    });

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    function handleFileSelect(file) {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            alert('Please select a valid PDF file.');
            return;
        }
        state.selectedFile = file;
        selectedFileName.textContent = file.name;
        selectedFileSize.textContent = `${(file.size / 1024).toFixed(1)} KB`;
        selectedFileBanner.classList.remove('hidden');
        dropZone.classList.add('hidden');
        btnSubmitUpload.disabled = false;
    }

    btnRemoveSelectedFile.addEventListener('click', resetUploadModal);

    btnSubmitUpload.addEventListener('click', async () => {
        if (!state.selectedFile) return;

        btnSubmitUpload.disabled = true;
        dropZone.classList.add('hidden');
        selectedFileBanner.classList.add('hidden');
        processingBox.classList.remove('hidden');

        const formData = new FormData();
        formData.append('file', state.selectedFile);

        try {
            const res = await fetch('/api/upload-pdf', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();

            if (data.success) {
                uploadModal.classList.add('hidden');
                showResultsModal(data);
                fetchStats();
                fetchCatalog();
            } else {
                alert(`Upload failed: ${data.error}`);
                resetUploadModal();
            }
        } catch (err) {
            console.error('Upload request error:', err);
            alert('Failed to process PDF invoice.');
            resetUploadModal();
        }
    });

    function showResultsModal(data) {
        resTotalItems.textContent = data.total_items_in_pdf;
        resNewItems.textContent = data.new_items_count;
        resExistingItems.textContent = data.existing_items_count;
        resMissingMsrp.textContent = (data.missing_msrp_skus || []).length;

        if (data.missing_msrp_skus && data.missing_msrp_skus.length > 0) {
            modalMissingAlert.classList.remove('hidden');
            document.getElementById('modalMissingAlertText').textContent = 
                `${data.missing_msrp_skus.length} newly added SKU(s) could not be automatically found on Hitfar.com. You can manually enter their prices in the table.`;
        } else {
            modalMissingAlert.classList.add('hidden');
        }

        resultsModal.classList.remove('hidden');
    }

    btnCloseResultsModal.addEventListener('click', () => resultsModal.classList.add('hidden'));
    btnFinishResults.addEventListener('click', () => resultsModal.classList.add('hidden'));

    // ==========================================
    // EDIT & INLINE MSRP PRICE UPDATE
    // ==========================================
    window.openEditModal = function(id, name, supplierSku, cost, currentPrice) {
        state.activeEditItem = id;
        editItemName.textContent = name;
        editItemSku.value = supplierSku;
        editItemCost.value = cost ? `$${Number(cost).toFixed(2)}` : '-';
        editItemPrice.value = currentPrice ? Number(currentPrice).toFixed(2) : '';
        editModal.classList.remove('hidden');
        setTimeout(() => editItemPrice.focus(), 100);
    };

    btnCloseEditModal.addEventListener('click', () => editModal.classList.add('hidden'));
    btnCancelEdit.addEventListener('click', () => editModal.classList.add('hidden'));

    btnSaveEdit.addEventListener('click', async () => {
        const val = parseFloat(editItemPrice.value);
        if (isNaN(val) || val < 0) {
            alert('Please enter a valid price number.');
            return;
        }

        try {
            const res = await fetch('/api/update-price', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: state.activeEditItem, price: val })
            });
            const data = await res.json();
            if (data.success) {
                editModal.classList.add('hidden');
                fetchStats();
                fetchCatalog();
            } else {
                alert(`Error saving price: ${data.error}`);
            }
        } catch (err) {
            console.error('Save price error:', err);
            alert('Failed to update price.');
        }
    });

    // Re-scrape single SKU
    window.rescrapeSku = async function(id, hitfarSku) {
        if (!confirm(`Re-scrape live MSRP for SKU "${hitfarSku}" from Hitfar.com?`)) return;

        try {
            const res = await fetch('/api/rescrape-sku', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id, hitfar_sku: hitfarSku })
            });
            const data = await res.json();
            if (data.success && data.found) {
                alert(`MSRP updated successfully: $${Number(data.price).toFixed(2)}`);
                fetchStats();
                fetchCatalog();
            } else {
                alert(`Scraper could not locate an MSRP for SKU "${hitfarSku}". Please enter it manually.`);
            }
        } catch (err) {
            console.error('Re-scrape error:', err);
            alert('Failed to connect to scraper.');
        }
    };

    // Initial Load
    fetchStats();
    fetchCatalog();
});
