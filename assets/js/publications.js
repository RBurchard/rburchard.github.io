/**
 * Publications Renderer & Filter Engine
 * Loads strictly from local GitHub-hosted JSON files (`data/pinned.json` and `data/publications.json`)
 * updated automatically by GitHub Actions — zero automatic third-party requests on page load.
 */
(function () {
  const ICONS = {
    globe: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>',
    arxiv: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>',
    pdf: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><path d="M9 15h6"></path></svg>',
    database: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>',
    github: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path></svg>',
    doi: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>',
    bibtex: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>',
    star: '<svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>',
    copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>'
  };

  function escapeHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function formatAuthors(authors) {
    if (!authors || !authors.length) return '<span class="author-self">Robin Burchard</span>';
    return authors.map(function (a) {
      const clean = escapeHtml(a);
      if (a.toLowerCase().includes('burchard')) {
        return '<span class="author-self">' + clean + '</span>';
      }
      return clean;
    }).join(', ');
  }

  function formatTypeLabel(type) {
    switch (type) {
      case 'journal-article': return 'Journal Article';
      case 'book-chapter': return 'Workshop / Book Chapter';
      case 'preprint': return 'Preprint';
      default: return 'Conference / Workshop Paper';
    }
  }

  function renderPinnedCard(item, index) {
    const isFirst = index === 0;
    const primaryUrl = (item.links && item.links[0] && item.links[0].url) || (item.doi ? 'https://doi.org/' + item.doi : '#');
    const iconHtml = item.icon
      ? '<img src="' + escapeHtml(item.icon) + '" alt="' + escapeHtml(item.title) + ' logo" class="pub-card-icon" loading="lazy">'
      : '';

    const linksHtml = (item.links || []).map(function (lnk) {
      const btnClass = lnk.primary ? 'btn btn-sm btn-gold' : 'btn btn-sm';
      const svg = ICONS[lnk.icon] || ICONS.doi;
      return '<a href="' + escapeHtml(lnk.url) + '" class="' + btnClass + '" target="_blank" rel="noopener noreferrer">' + svg + '<span>' + escapeHtml(lnk.label) + '</span></a>';
    }).join('');

    const bibId = 'bib-pinned-' + index;
    const bibBtn = item.bibtex
      ? '<button type="button" class="btn btn-sm" data-bib-toggle="' + bibId + '">' + ICONS.bibtex + '<span>BibTeX</span></button>' +
        '<button type="button" class="btn btn-sm" data-bib-copy="' + bibId + '">' + ICONS.copy + '<span>Copy BibTeX</span></button>'
      : '';

    const bibDrawer = item.bibtex
      ? '<pre id="' + bibId + '" class="bibtex-drawer">' + escapeHtml(item.bibtex) + '</pre>'
      : '';

    return (
      '<article class="pub-card-pinned ' + (isFirst ? 'featured-first' : '') + '">' +
        iconHtml +
        '<div class="pub-card-body">' +
          '<div class="pub-meta-top">' +
            '<span class="badge badge-pinned">' + ICONS.star + ' ' + escapeHtml(item.badge || 'Highlighted Publication') + '</span>' +
            '<span class="badge badge-year">' + escapeHtml(item.year) + '</span>' +
          '</div>' +
          '<h3 class="pub-title"><a href="' + escapeHtml(primaryUrl) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(item.title) + '</a></h3>' +
          '<p class="pub-authors">' + formatAuthors(item.authors) + '</p>' +
          (item.venue ? '<p class="pub-venue">' + escapeHtml(item.venue) + '</p>' : '') +
          (item.description ? '<p class="pub-desc">' + escapeHtml(item.description) + '</p>' : '') +
          '<div class="pub-links">' + linksHtml + bibBtn + '</div>' +
          bibDrawer +
        '</div>' +
      '</article>'
    );
  }

  function renderChronologicalItem(item, index) {
    const primaryUrl = item.url || (item.doi ? 'https://doi.org/' + item.doi : '');
    const titleHtml = primaryUrl
      ? '<a href="' + escapeHtml(primaryUrl) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(item.title) + '</a>'
      : escapeHtml(item.title);

    const isHarmes = item.title && item.title.toLowerCase().includes('harmes: a multi-modal dataset');
    let actionBtns = '';

    if (isHarmes) {
      actionBtns += '<a href="https://rburchard.github.io/harmes-website/" class="btn btn-sm btn-gold" target="_blank" rel="noopener noreferrer">' + ICONS.globe + '<span>Project Website</span></a>';
    }
    if (item.doi) {
      const label = item.doi.includes('arxiv') ? 'arXiv' : 'DOI';
      const href = item.doi.includes('arxiv') && item.url ? item.url : 'https://doi.org/' + item.doi;
      actionBtns += '<a href="' + escapeHtml(href) + '" class="btn btn-sm" target="_blank" rel="noopener noreferrer">' + ICONS.doi + '<span>' + label + '</span></a>';
    } else if (item.url) {
      actionBtns += '<a href="' + escapeHtml(item.url) + '" class="btn btn-sm" target="_blank" rel="noopener noreferrer">' + ICONS.doi + '<span>Paper</span></a>';
    }

    if (item.pdf_url && item.pdf_url !== ('https://doi.org/' + item.doi)) {
      actionBtns += '<a href="' + escapeHtml(item.pdf_url) + '" class="btn btn-sm" target="_blank" rel="noopener noreferrer">' + ICONS.pdf + '<span>PDF</span></a>';
    }

    const bibId = 'bib-item-' + index;
    if (item.bibtex) {
      actionBtns += '<button type="button" class="btn btn-sm" data-bib-toggle="' + bibId + '">' + ICONS.bibtex + '<span>BibTeX</span></button>';
      actionBtns += '<button type="button" class="btn btn-sm" data-bib-copy="' + bibId + '">' + ICONS.copy + '<span>Copy</span></button>';
    }

    return (
      '<article class="pub-item" data-type="' + escapeHtml(item.type) + '">' +
        '<div class="pub-meta-top">' +
          '<span class="badge badge-year">' + escapeHtml(item.year) + '</span>' +
          '<span class="badge badge-type">' + escapeHtml(formatTypeLabel(item.type)) + '</span>' +
        '</div>' +
        '<h4 class="pub-title">' + titleHtml + '</h4>' +
        '<p class="pub-authors">' + formatAuthors(item.authors) + '</p>' +
        (item.venue ? '<p class="pub-venue">' + escapeHtml(item.venue) + '</p>' : '') +
        '<div class="pub-links">' + actionBtns + '</div>' +
        (item.bibtex ? '<pre id="' + bibId + '" class="bibtex-drawer">' + escapeHtml(item.bibtex) + '</pre>' : '') +
      '</article>'
    );
  }

  function bindBibtexButtons(root) {
    root.querySelectorAll('[data-bib-toggle]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const targetId = btn.getAttribute('data-bib-toggle');
        const pre = document.getElementById(targetId);
        if (pre) {
          pre.classList.toggle('open');
        }
      });
    });

    root.querySelectorAll('[data-bib-copy]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const targetId = btn.getAttribute('data-bib-copy');
        const pre = document.getElementById(targetId);
        if (pre && navigator.clipboard) {
          navigator.clipboard.writeText(pre.textContent).then(function () {
            const span = btn.querySelector('span');
            const orig = span ? span.textContent : 'Copy';
            if (span) span.textContent = 'Copied!';
            setTimeout(function () {
              if (span) span.textContent = orig;
            }, 1800);
          });
        }
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    const pinnedContainer = document.getElementById('pinned-publications');
    const allContainer = document.getElementById('all-publications');
    const syncStamp = document.getElementById('pub-sync-timestamp');

    if (pinnedContainer) {
      fetch('data/pinned.json')
        .then(function (r) { return r.json(); })
        .then(function (pinned) {
          pinnedContainer.innerHTML = pinned.map(renderPinnedCard).join('');
          bindBibtexButtons(pinnedContainer);
        })
        .catch(function (err) {
          console.error('Failed to load pinned.json:', err);
        });
    }

    if (allContainer) {
      fetch('data/publications.json')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          const allPubs = data.publications || [];
          if (syncStamp && data.updated_at) {
            const d = new Date(data.updated_at);
            syncStamp.textContent = 'Auto-synced via GitHub Actions (' + d.toISOString().slice(0, 10) + ') · ' + allPubs.length + ' publications';
          }

          let activeFilter = 'all';
          let searchQuery = '';

          function updateList() {
            const filtered = allPubs.filter(function (p) {
              if (activeFilter !== 'all') {
                if (activeFilter === 'conference' && p.type !== 'conference-paper' && p.type !== 'book-chapter') return false;
                if (activeFilter === 'journal' && p.type !== 'journal-article') return false;
                if (activeFilter === 'preprint' && p.type !== 'preprint') return false;
              }
              if (searchQuery) {
                const hay = [p.title, (p.authors || []).join(' '), p.venue, p.year].join(' ').toLowerCase();
                if (!hay.includes(searchQuery)) return false;
              }
              return true;
            });

            if (!filtered.length) {
              allContainer.innerHTML = '<p style="color: var(--text-muted); padding: 1.5rem 0;">No publications match your current filter.</p>';
              return;
            }

            // Group by year descending
            const byYear = {};
            filtered.forEach(function (item) {
              const y = item.year || 'Other';
              if (!byYear[y]) byYear[y] = [];
              byYear[y].push(item);
            });

            const years = Object.keys(byYear).sort(function (a, b) { return Number(b) - Number(a); });
            let globalIdx = 0;

            allContainer.innerHTML = years.map(function (yr) {
              const items = byYear[yr];
              const listHtml = items.map(function (it) {
                return renderChronologicalItem(it, globalIdx++);
              }).join('');
              return (
                '<div class="year-group">' +
                  '<h3 class="year-heading"><span>' + escapeHtml(yr) + '</span><span class="year-count">' + items.length + '</span></h3>' +
                  '<div class="pub-list">' + listHtml + '</div>' +
                '</div>'
              );
            }).join('');

            bindBibtexButtons(allContainer);
          }

          updateList();

          // Search listener
          const searchInput = document.getElementById('pub-search');
          if (searchInput) {
            searchInput.addEventListener('input', function (e) {
              searchQuery = e.target.value.trim().toLowerCase();
              updateList();
            });
          }

          // Filter pills
          document.querySelectorAll('[data-pub-filter]').forEach(function (btn) {
            btn.addEventListener('click', function () {
              document.querySelectorAll('[data-pub-filter]').forEach(function (b) { b.classList.remove('active'); });
              btn.classList.add('active');
              activeFilter = btn.getAttribute('data-pub-filter');
              updateList();
            });
          });
        })
        .catch(function (err) {
          console.error('Failed to load publications.json:', err);
        });
    }
  });
})();
