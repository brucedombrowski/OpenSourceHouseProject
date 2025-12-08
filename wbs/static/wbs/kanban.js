(function() {
    const FILTER_KEY = 'boardFilters';
    const filterPanel = document.getElementById('filter-panel');
    const toggleFilterBtn = document.getElementById('toggle-filters');
    const clearFilterBtn = document.getElementById('clear-filters');
    const board = document.querySelector('.board');

    // Load and apply saved filters on page load
    function loadFilters() {
        const saved = localStorage.getItem(FILTER_KEY);
        if (!saved) return;
        try {
            const filters = JSON.parse(saved);
            Object.entries(filters).forEach(([key, values]) => {
                values.forEach(val => {
                    const checkbox = document.querySelector(`input[name="filter-${key}"][value="${val}"]`);
                    if (checkbox) checkbox.checked = true;
                });
            });
        } catch (_) {
            // ignore parse errors
        }
    }

    function getActiveFilters() {
        const filters = { type: [], priority: [], status: [], owner: [], phase: [] };
        document.querySelectorAll('input[name^="filter-"]:checked').forEach(cb => {
            const key = cb.name.replace('filter-', '');
            if (filters.hasOwnProperty(key)) {
                filters[key].push(cb.value);
            }
        });
        return filters;
    }

    function cardMatchesFilters(card, filters) {
        if (!filters.type.length && !filters.priority.length && !filters.status.length && !filters.owner.length && !filters.phase.length) {
            return true;
        }
        const type = card.dataset.type || '';
        const priority = card.dataset.priority || '';
        const status = card.closest('.column')?.dataset.status || '';
        const owner = card.dataset.owner || '';
        const phase = card.dataset.phase || '';

        const typeMatch = !filters.type.length || filters.type.includes(type);
        const priorityMatch = !filters.priority.length || filters.priority.includes(priority);
        const statusMatch = !filters.status.length || filters.status.includes(status);
        const phaseMatch = !filters.phase.length || filters.phase.includes(phase);

        // Owner filter special handling
        let ownerMatch = true;
        if (filters.owner.length) {
            const hasUnassignedFilter = filters.owner.includes('owner-unassigned');
            const specificOwners = filters.owner.filter(o => o !== 'owner-unassigned');

            if (hasUnassignedFilter && specificOwners.length > 0) {
                // Both unassigned and specific users: match if no owner OR owner in list
                ownerMatch = !owner || specificOwners.includes(owner);
            } else if (hasUnassignedFilter) {
                // Only unassigned: show items with no owner
                ownerMatch = !owner;
            } else if (specificOwners.length > 0) {
                // Specific users: show items owned by those users
                ownerMatch = specificOwners.includes(owner);
            }
        }

        return typeMatch && priorityMatch && statusMatch && ownerMatch && phaseMatch;
    }

    function applyFilters() {
        const filters = getActiveFilters();
        const hasFilters = filters.type.length || filters.priority.length || filters.status.length || filters.owner.length || filters.phase.length;

        if (hasFilters) {
            localStorage.setItem(FILTER_KEY, JSON.stringify(filters));
            board.classList.add('filter-active');
        } else {
            localStorage.removeItem(FILTER_KEY);
            board.classList.remove('filter-active');
        }

        document.querySelectorAll('.card').forEach(card => {
            if (hasFilters) {
                if (cardMatchesFilters(card, filters)) {
                    card.classList.add('matches-filter');
                } else {
                    card.classList.remove('matches-filter');
                }
            } else {
                card.classList.remove('matches-filter');
            }
        });
    }

    // Toggle filter panel
    toggleFilterBtn.addEventListener('click', () => {
        const isHidden = filterPanel.style.display === 'none';
        const nextDisplay = isHidden ? 'block' : 'none';
        filterPanel.style.display = nextDisplay;
        filterPanel.setAttribute('aria-hidden', isHidden ? 'false' : 'true');
        toggleFilterBtn.setAttribute('aria-expanded', isHidden ? 'true' : 'false');
    });

    // Apply filters
    // Auto-apply filters on any checkbox change
    document.querySelectorAll('input[name^="filter-"]').forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            applyFilters();
        });
    });

    // Clear filters
    clearFilterBtn.addEventListener('click', () => {
        document.querySelectorAll('input[name^="filter-"]:checked').forEach(cb => {
            cb.checked = false;
        });
        localStorage.removeItem(FILTER_KEY);
        board.classList.remove('filter-active');
        document.querySelectorAll('.card').forEach(card => {
            card.classList.remove('matches-filter');
        });
        // Keep panel open so users can immediately pick new filters.
        filterPanel.style.display = 'block';
        filterPanel.setAttribute('aria-hidden', 'false');
        toggleFilterBtn.setAttribute('aria-expanded', 'true');
    });

    // Set data attributes on cards for filtering
    document.querySelectorAll('.card').forEach(card => {
        const meta = card.querySelector('.meta');
        if (meta) {
            const pills = meta.querySelectorAll('.pill');
            if (pills.length > 0) {
                const typeText = pills[pills.length - 1]?.textContent?.toLowerCase() || '';
                const typeMap = { issue: 'issue', task: 'task', enhancement: 'enhancement', risk: 'risk', decision: 'decision' };
                const type = Object.keys(typeMap).find(k => typeText.includes(k)) || '';
                if (type) card.dataset.type = type;
            }
            const priority = card.querySelector('.priority');
            if (priority) {
                card.dataset.priority = priority.className.split(' ').find(c => ['critical', 'high', 'medium', 'low'].includes(c)) || '';
            }
        }
    });

    loadFilters();
    applyFilters();

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    const csrfToken =
        getCookie('csrftoken') ||
        document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
        document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
        '';
    const statusUpdateUrl = '/project-items/status/';

    function updateCount(column) {
        const countEl = column.querySelector('.column-count');
        if (countEl) {
            countEl.textContent = column.querySelectorAll('.card').length;
        }
    }

    function refreshEmptyState(column) {
        const body = column.querySelector('.column-body');
        if (!body) return;
        const hasCard = body.querySelector('.card');
        let empty = body.querySelector('.empty');
        if (hasCard && empty) {
            empty.remove();
        } else if (!hasCard && !empty) {
            empty = document.createElement('div');
            empty.className = 'empty';
            empty.textContent = 'No items in this status yet.';
            body.appendChild(empty);
        }
    }

    let draggingCard = null;

    document.querySelectorAll('.card').forEach(card => {
        card.setAttribute('draggable', 'true');

        card.addEventListener('dragstart', e => {
            draggingCard = card;
            card.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
        });

        card.addEventListener('dragend', () => {
            card.classList.remove('dragging');
        });
    });

    document.querySelectorAll('.column').forEach(column => {
        column.addEventListener('dragover', e => {
            if (!draggingCard) return;
            e.preventDefault();
            column.classList.add('drop-hover');
        });

        column.addEventListener('dragleave', () => {
            column.classList.remove('drop-hover');
        });

        column.addEventListener('drop', e => {
            e.preventDefault();
            column.classList.remove('drop-hover');
            const card = draggingCard;
            if (!card) return;

            const sourceColumn = card.closest('.column');
            const targetStatus = column.dataset.status;
            const cardId = card.dataset.id;

            if (!targetStatus || !cardId || sourceColumn === column) {
                draggingCard = null;
                return;
            }

            fetch(statusUpdateUrl, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({ id: cardId, status: targetStatus }),
            })
                .then(async resp => {
                    const text = await resp.text();
                    if (!resp.ok) {
                        let detail = text || `HTTP ${resp.status}`;
                        try {
                            const data = JSON.parse(text);
                            detail = data.error || detail;
                        } catch (_) {
                            // ignore parse errors
                        }
                        throw new Error(detail);
                    }
                    let data = {};
                    try {
                        data = JSON.parse(text);
                    } catch (_) {
                        data = {};
                    }
                    if (!data.ok) throw new Error(data.error || 'Update failed');

                    const targetBody = column.querySelector('.column-body');
                    if (!targetBody) return;

                    card.remove();
                    targetBody.appendChild(card);
                    updateCount(sourceColumn);
                    updateCount(column);
                    refreshEmptyState(sourceColumn);
                    refreshEmptyState(column);
                })
                .catch(err => {
                    console.error(err);
                    const detail = err?.message ? ` (${err.message})` : '';
                    alert(`Could not move card.${detail}`);
                });
        });
    });
})();
