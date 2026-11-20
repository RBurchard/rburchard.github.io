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
    copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>',
    cite: '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"></path><path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2h.75c0 2.25.25 4-2.75 4v3c0 1 0 1 1 1z"></path></svg>',
    close: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>',
    external: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>',
    chevron: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>'
  };

  const citationRegistry = new Map();
  let lastFocusedEl = null;
  let closeTimer = null;

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

  function formatCitationsBadge(count, citeKey) {
    if (typeof count !== 'number' || isNaN(count)) return '';
    const label = count === 1 ? '1 Citation' : count + ' Citations';
    return (
      '<button type="button" class="badge badge-citations badge-citations-btn" data-citations-open="' + escapeHtml(citeKey) + '" aria-haspopup="dialog" title="Click to view citing papers">' +
        ICONS.cite + ' <span>' + label + '</span>' +
      '</button>'
    );
  }

  function renderAbstractHint(abstractId) {
    return (
      '<button type="button" class="abstract-hint-btn" data-abstract-toggle aria-expanded="false" aria-controls="' + escapeHtml(abstractId) + '" title="Show abstract">' +
        '<span class="abstract-hint-label">Abstract</span>' +
        ICONS.chevron +
      '</button>'
    );
  }

  function renderAbstractSection(abstractText, abstractId) {
    return (
      '<div id="' + escapeHtml(abstractId) + '" class="pub-abstract-collapse" aria-hidden="true">' +
        '<div class="pub-abstract-inner">' +
          '<div class="pub-abstract-box">' +
            '<span class="pub-abstract-label">Abstract</span>' +
            '<p class="pub-abstract-text">' + escapeHtml(abstractText) + '</p>' +
          '</div>' +
        '</div>' +
      '</div>'
    );
  }

  function toggleCardAbstract(card) {
    if (!card) return;
    const expanded = card.classList.toggle('is-expanded');
    const btn = card.querySelector('[data-abstract-toggle]');
    if (btn) {
      btn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
      btn.setAttribute('title', expanded ? 'Hide abstract' : 'Show abstract');
    }
    const collapse = card.querySelector('.pub-abstract-collapse');
    if (collapse) {
      collapse.setAttribute('aria-hidden', expanded ? 'false' : 'true');
    }
  }

  function registerCitationEntry(citeKey, item) {
    citationRegistry.set(citeKey, {
      title: item.title || '',
      year: item.year || '',
      doi: item.doi || '',
      url: item.url || '',
      openalex_id: item.openalex_id || '',
      cited_by_count: typeof item.cited_by_count === 'number' ? item.cited_by_count : 0,
      citations: Array.isArray(item.citations) ? item.citations : []
    });
  }

  function formatCitingAuthors(authors) {
    if (!authors || !authors.length) return '';
    const formatOne = function (a) {
      const clean = escapeHtml(a);
      return a.toLowerCase().includes('burchard') ? '<span class="author-self">' + clean + '</span>' : clean;
    };
    if (authors.length <= 8) {
      return authors.map(formatOne).join(', ');
    }
    const head = authors.slice(0, 6).map(formatOne);
    const tail = formatOne(authors[authors.length - 1]);
    return head.join(', ') + ', &hellip;, ' + tail;
  }

  function ensureCitationsModal() {
    let modal = document.getElementById('citations-modal');
    if (modal) return modal;

    modal = document.createElement('div');
    modal.id = 'citations-modal';
    modal.className = 'citations-modal-backdrop';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-labelledby', 'citations-modal-title');
    modal.hidden = true;
    modal.innerHTML =
      '<div class="citations-modal-dialog" role="document">' +
        '<div class="citations-modal-header">' +
          '<div class="citations-modal-heading">' +
            '<div class="citations-modal-kicker">' +
              '<span id="citations-modal-count" class="badge badge-citations"></span>' +
              '<span class="citations-modal-eyebrow">Papers citing</span>' +
            '</div>' +
            '<h3 id="citations-modal-title" class="citations-modal-title"></h3>' +
          '</div>' +
          '<button type="button" class="citations-modal-close" aria-label="Close citations popup" title="Close (Esc)">' +
            ICONS.close +
          '</button>' +
        '</div>' +
        '<div id="citations-modal-body" class="citations-modal-body"></div>' +
        '<div id="citations-modal-footer" class="citations-modal-footer"></div>' +
      '</div>';

    document.body.appendChild(modal);
    return modal;
  }

  function openCitationsModal(citeKey, triggerEl) {
    const entry = citationRegistry.get(citeKey);
    if (!entry) return;

    const modal = ensureCitationsModal();
    if (closeTimer) {
      clearTimeout(closeTimer);
      closeTimer = null;
    }

    lastFocusedEl = triggerEl || document.activeElement;

    const countEl = document.getElementById('citations-modal-count');
    const titleEl = document.getElementById('citations-modal-title');
    const bodyEl = document.getElementById('citations-modal-body');
    const footerEl = document.getElementById('citations-modal-footer');

    const citations = entry.citations || [];
    const total = Math.max(entry.cited_by_count || 0, citations.length);

    if (countEl) {
      let countLabel;
      if (citations.length > 0 && total > citations.length) {
        countLabel = citations.length + ' Indexed Citing Papers (' + total + ' total)';
      } else {
        countLabel = total === 1 ? '1 Citing Paper' : total + ' Citing Papers';
      }
      countEl.innerHTML = ICONS.cite + ' <span>' + escapeHtml(countLabel) + '</span>';
    }

    if (titleEl) {
      titleEl.textContent = entry.title;
    }

    if (bodyEl) {
      if (citations.length > 0) {
        bodyEl.innerHTML = '<ul class="citing-list">' + citations.map(function (c) {
          const linkUrl = (c.url && /^https?:\/\//i.test(c.url)) ? c.url : (c.doi ? 'https://doi.org/' + c.doi : '');
          const titleNode = linkUrl
            ? '<a href="' + escapeHtml(linkUrl) + '" target="_blank" rel="noopener noreferrer" class="citing-title"><span>' + escapeHtml(c.title) + '</span>' + ICONS.external + '</a>'
            : '<span class="citing-title">' + escapeHtml(c.title) + '</span>';
          const authorsHtml = formatCitingAuthors(c.authors);
          const yearHtml = c.year ? '<span class="badge badge-year">' + escapeHtml(c.year) + '</span>' : '';
          const venueHtml = c.venue ? '<span class="citing-venue">' + escapeHtml(c.venue) + '</span>' : '';
          const doiUrl = c.doi ? 'https://doi.org/' + c.doi : '';
          const doiLinkHtml = (c.doi && doiUrl !== linkUrl)
            ? '<a href="' + escapeHtml(doiUrl) + '" target="_blank" rel="noopener noreferrer" class="citing-doi-link">DOI</a>'
            : '';

          return (
            '<li class="citing-item">' +
              titleNode +
              (authorsHtml ? '<p class="citing-authors">' + authorsHtml + '</p>' : '') +
              '<div class="citing-meta">' + yearHtml + venueHtml + doiLinkHtml + '</div>' +
            '</li>'
          );
        }).join('') + '</ul>';
      } else {
        bodyEl.innerHTML =
          '<div class="citing-empty">' +
            '<p>No citing papers are currently indexed in OpenAlex for this publication.</p>' +
            '<p class="citing-empty-hint">You can still check Google Scholar below for recent or non-indexed citations.</p>' +
          '</div>';
      }
      bodyEl.scrollTop = 0;
    }

    if (footerEl) {
      const scholarUrl = 'https://scholar.google.com/scholar?q=' + encodeURIComponent('"' + entry.title + '"');
      let actionsHtml = '';
      if (entry.openalex_id && /^https?:\/\//i.test(entry.openalex_id)) {
        actionsHtml += '<a href="' + escapeHtml(entry.openalex_id) + '" class="btn btn-sm" target="_blank" rel="noopener noreferrer"><span>OpenAlex</span>' + ICONS.external + '</a>';
      }
      actionsHtml += '<a href="' + escapeHtml(scholarUrl) + '" class="btn btn-sm" target="_blank" rel="noopener noreferrer"><span>Google Scholar</span>' + ICONS.external + '</a>';

      footerEl.innerHTML =
        '<span class="citations-modal-source">Synced locally from OpenAlex</span>' +
        '<div class="citations-modal-actions">' + actionsHtml + '</div>';
    }

    modal.hidden = false;
    document.body.classList.add('modal-open');
    if (bodyEl) {
      bodyEl.scrollTop = 0;
    }

    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      modal.classList.add('open');
    } else {
      requestAnimationFrame(function () {
        modal.classList.add('open');
        if (bodyEl) {
          bodyEl.scrollTop = 0;
        }
      });
    }

    const closeBtn = modal.querySelector('.citations-modal-close');
    if (closeBtn) {
      closeBtn.focus();
    }
  }

  function closeCitationsModal() {
    const modal = document.getElementById('citations-modal');
    if (!modal || modal.hidden) return;

    modal.classList.remove('open');
    document.body.classList.remove('modal-open');

    const finishClose = function () {
      modal.hidden = true;
      closeTimer = null;
      if (lastFocusedEl && typeof lastFocusedEl.focus === 'function') {
        lastFocusedEl.focus();
      }
      lastFocusedEl = null;
    };

    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      finishClose();
    } else {
      closeTimer = setTimeout(finishClose, 180);
    }
  }

  function renderPinnedCard(item, index) {
    const citeKey = 'pinned-' + index;
    registerCitationEntry(citeKey, item);
    const isFirst = index === 0;
    const hasAbstract = Boolean(item.abstract && item.abstract.trim());
    const absId = 'abs-pinned-' + index;
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
      '<article class="pub-card-pinned ' + (isFirst ? 'featured-first' : '') + (hasAbstract ? ' pub-expandable' : '') + '">' +
        iconHtml +
        '<div class="pub-card-body">' +
          '<div class="pub-meta-top">' +
            '<span class="badge badge-pinned">' + ICONS.star + ' ' + escapeHtml(item.badge || 'Highlighted Publication') + '</span>' +
            '<span class="badge badge-year">' + escapeHtml(item.year) + '</span>' +
            formatCitationsBadge(item.cited_by_count, citeKey) +
            (hasAbstract ? renderAbstractHint(absId) : '') +
          '</div>' +
          '<h3 class="pub-title"><a href="' + escapeHtml(primaryUrl) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(item.title) + '</a></h3>' +
          '<p class="pub-authors">' + formatAuthors(item.authors) + '</p>' +
          (item.venue ? '<p class="pub-venue">' + escapeHtml(item.venue) + '</p>' : '') +
          (item.description ? '<p class="pub-desc">' + escapeHtml(item.description) + '</p>' : '') +
          (hasAbstract ? renderAbstractSection(item.abstract, absId) : '') +
          '<div class="pub-links">' + linksHtml + bibBtn + '</div>' +
          bibDrawer +
        '</div>' +
      '</article>'
    );
  }

  function renderChronologicalItem(item, index) {
    const citeKey = 'pub-' + index;
    registerCitationEntry(citeKey, item);
    const hasAbstract = Boolean(item.abstract && item.abstract.trim());
    const absId = 'abs-item-' + index;
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
      '<article class="pub-item' + (hasAbstract ? ' pub-expandable' : '') + '" data-type="' + escapeHtml(item.type) + '">' +
        '<div class="pub-meta-top">' +
          '<span class="badge badge-year">' + escapeHtml(item.year) + '</span>' +
          '<span class="badge badge-type">' + escapeHtml(formatTypeLabel(item.type)) + '</span>' +
          formatCitationsBadge(item.cited_by_count, citeKey) +
          (hasAbstract ? renderAbstractHint(absId) : '') +
        '</div>' +
        '<h4 class="pub-title">' + titleHtml + '</h4>' +
        '<p class="pub-authors">' + formatAuthors(item.authors) + '</p>' +
        (item.venue ? '<p class="pub-venue">' + escapeHtml(item.venue) + '</p>' : '') +
        (hasAbstract ? renderAbstractSection(item.abstract, absId) : '') +
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

    document.addEventListener('click', function (e) {
      const openBtn = e.target.closest('[data-citations-open]');
      if (openBtn) {
        openCitationsModal(openBtn.getAttribute('data-citations-open'), openBtn);
        return;
      }
      const closeBtn = e.target.closest('.citations-modal-close');
      if (closeBtn) {
        closeCitationsModal();
        return;
      }
      const modal = document.getElementById('citations-modal');
      if (modal && !modal.hidden && e.target === modal) {
        closeCitationsModal();
        return;
      }
      const absToggleBtn = e.target.closest('[data-abstract-toggle]');
      if (absToggleBtn) {
        toggleCardAbstract(absToggleBtn.closest('.pub-expandable'));
        return;
      }
      const card = e.target.closest('.pub-expandable');
      if (card) {
        if (e.target.closest('a, button, .bibtex-drawer')) return;
        const sel = window.getSelection ? window.getSelection().toString() : '';
        if (sel && sel.trim().length > 0) return;
        toggleCardAbstract(card);
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        const modal = document.getElementById('citations-modal');
        if (modal && !modal.hidden) {
          closeCitationsModal();
        }
      }
    });

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
            const citesText = typeof data.total_citations === 'number' ? ' · ' + data.total_citations + ' citations' : '';
            syncStamp.textContent = 'Auto-synced via GitHub Actions (' + d.toISOString().slice(0, 10) + ') · ' + allPubs.length + ' publications' + citesText;
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
                const hay = [p.title, (p.authors || []).join(' '), p.venue, p.year, p.abstract || ''].join(' ').toLowerCase();
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
