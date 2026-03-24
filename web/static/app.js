/** O'Reilly Downloader */

const API = '';
let currentExpandedCard = null;
let selectedResultIndex = -1;
let defaultOutputDir = '';
const chaptersCache = {};

function getHighResCoverUrl(bookId) {
    return `https://learning.oreilly.com/covers/urn:orm:book:${bookId}/400w/`;
}

async function checkAuth() {
    try {
        const res = await fetch(`${API}/api/status`);
        const data = await res.json();
        const el = document.getElementById('auth-status');
        const loginBtn = document.getElementById('login-btn');
        const statusDot = el.querySelector('.status-dot');
        const statusText = el.querySelector('.status-text');

        if (data.valid) {
            if (statusText) statusText.textContent = 'Connected';
            statusDot.className = 'status-dot w-1.5 h-1.5 rounded-full bg-emerald-500';
            el.className = 'flex items-center gap-1.5 text-xs font-medium text-emerald-600';
            loginBtn.classList.add('hidden');
        } else {
            if (statusText) statusText.textContent = data.reason || 'Not connected';
            statusDot.className = 'status-dot w-1.5 h-1.5 rounded-full bg-amber-500';
            el.className = 'flex items-center gap-1.5 text-xs font-medium text-amber-600';
            loginBtn.classList.remove('hidden');
        }
    } catch (err) {
        console.error('Auth check failed:', err);
    }
}

function showCookieModal() {
    document.getElementById('cookie-modal').classList.remove('hidden');
    document.getElementById('cookie-input').value = '';
    document.getElementById('cookie-error').classList.add('hidden');
    document.body.style.overflow = 'hidden';
}

function hideCookieModal() {
    document.getElementById('cookie-modal').classList.add('hidden');
    document.body.style.overflow = '';
}

async function saveCookies() {
    const input = document.getElementById('cookie-input').value.trim();
    const errorEl = document.getElementById('cookie-error');

    if (!input) {
        errorEl.textContent = 'Please paste your cookie JSON';
        errorEl.classList.remove('hidden');
        return;
    }

    let cookies;
    try {
        if ((input.startsWith("'") && input.endsWith("'")) ||
            (input.startsWith('"') && input.endsWith('"'))) {
            input = input.slice(1, -1);
        }
        cookies = JSON.parse(input);
        if (typeof cookies !== 'object' || Array.isArray(cookies)) {
            throw new Error('Must be a JSON object');
        }
    } catch (e) {
        errorEl.textContent = 'Invalid JSON format: ' + e.message;
        errorEl.classList.remove('hidden');
        return;
    }

    try {
        const res = await fetch(`${API}/api/cookies`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(cookies)
        });
        const data = await res.json();

        if (data.error) {
            errorEl.textContent = data.error;
            errorEl.classList.remove('hidden');
            return;
        }

        hideCookieModal();
        checkAuth();
    } catch (err) {
        errorEl.textContent = 'Failed to save cookies';
        errorEl.classList.remove('hidden');
    }
}

async function loadDefaultOutputDir() {
    try {
        const res = await fetch(`${API}/api/settings`);
        const data = await res.json();
        defaultOutputDir = data.output_dir;
    } catch (err) {
        console.error('Failed to load default output dir:', err);
    }
}

async function search(query) {
    const loader = document.getElementById('search-loader');
    const container = document.getElementById('search-results');

    loader.classList.remove('hidden');

    try {
        const res = await fetch(`${API}/api/search?q=${encodeURIComponent(query)}`);
        const data = await res.json();

        loader.classList.add('hidden');
        container.innerHTML = '';
        container.classList.remove('has-expanded');
        currentExpandedCard = null;
        selectedResultIndex = -1;

        if (!data.results || data.results.length === 0) {
            container.innerHTML = `
                <div class="text-center py-14 text-ink-500">
                    <p class="text-sm font-medium">No books found for "${query}"</p>
                    <p class="text-xs mt-1 text-ink-400">Try a different search term or ISBN</p>
                </div>
            `;
            return;
        }

        for (const book of data.results) {
            const div = document.createElement('article');
            div.className = 'book-card group bg-white rounded-lg border border-ink-200/80 overflow-hidden transition-all duration-200 hover:border-ink-300 hover:shadow-card-hover';
            div.dataset.bookId = book.id;
            div.innerHTML = createBookCardHTML(book);

            setupBookCardEvents(div, book);
            container.appendChild(div);
        }
    } catch (err) {
        loader.classList.add('hidden');
        container.innerHTML = `
            <div class="text-center py-14 text-red-600">
                <p class="text-sm">Search failed. Please try again.</p>
            </div>
        `;
    }
}

function createBookCardHTML(book) {
    return `
        <div class="book-summary flex items-center gap-3.5 px-4 py-3 cursor-pointer">
            <img src="${book.cover_url}" alt="${book.title} cover" class="w-10 h-14 object-cover rounded shadow-sm flex-shrink-0" loading="lazy">
            <div class="flex-1 min-w-0">
                <h3 class="text-sm font-semibold text-ink-900 leading-snug truncate">${book.title}</h3>
                <p class="text-xs text-ink-500 truncate mt-0.5">${book.authors?.join(', ') || 'Unknown Author'}</p>
            </div>
            <svg class="expand-icon w-4 h-4 text-ink-400 flex-shrink-0 transition-transform duration-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M6 9l6 6 6-6"/>
            </svg>
        </div>

        <div class="book-expanded hidden">
            <button class="close-btn absolute top-3 right-3 w-7 h-7 flex items-center justify-center bg-ink-100 hover:bg-ink-200 rounded-full transition-colors duration-150 z-10 active:scale-[0.95]">
                <svg class="w-3.5 h-3.5 text-ink-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 6L6 18M6 6l12 12"/>
                </svg>
            </button>

            <div class="relative px-4 pb-4 pt-1 border-t border-ink-100 animate-fade-in">
                <div class="flex gap-4 py-4">
                    <img class="w-20 h-28 object-cover rounded-lg shadow-card flex-shrink-0" src="${getHighResCoverUrl(book.id)}" alt="${book.title} cover">
                    <div class="flex-1 min-w-0">
                        <h2 class="text-base font-semibold text-ink-900 leading-tight mb-0.5">${book.title}</h2>
                        <p class="text-sm text-ink-500 mb-2.5">${book.authors?.join(', ') || 'Unknown Author'}</p>
                        <div class="flex gap-4 text-xs text-ink-500 mb-2.5">
                            <span><span class="text-ink-400">Publisher</span> <span class="publisher-value animate-pulse-subtle">...</span></span>
                            <span><span class="text-ink-400">Pages</span> <span class="pages-value animate-pulse-subtle">...</span></span>
                        </div>
                        <div class="book-description text-xs text-ink-600 leading-relaxed max-h-16 overflow-y-auto pr-2 animate-pulse-subtle">
                            Loading...
                        </div>
                    </div>
                </div>

                <div class="py-4 border-t border-ink-100">
                    <div class="mb-4">
                        <h4 class="text-[0.625rem] font-semibold uppercase tracking-wider text-ink-400 mb-2">Format</h4>
                        <div class="format-options flex flex-wrap gap-1">
                            <label class="format-option cursor-pointer">
                                <input type="radio" name="format" value="markdown" checked class="sr-only peer">
                                <span class="inline-flex items-center px-2.5 py-1.5 bg-ink-50 border border-ink-200 rounded-md text-xs font-medium text-ink-600 transition-all duration-150 peer-checked:border-oreilly-blue peer-checked:bg-oreilly-blue-light peer-checked:text-oreilly-blue-dark hover:bg-white hover:border-ink-300">Markdown</span>
                            </label>
                            <label class="format-option cursor-pointer">
                                <input type="radio" name="format" value="json" class="sr-only peer">
                                <span class="inline-flex items-center px-2.5 py-1.5 bg-ink-50 border border-ink-200 rounded-md text-xs font-medium text-ink-600 transition-all duration-150 peer-checked:border-oreilly-blue peer-checked:bg-oreilly-blue-light peer-checked:text-oreilly-blue-dark hover:bg-white hover:border-ink-300">JSON</span>
                            </label>
                            <label class="format-option cursor-pointer">
                                <input type="radio" name="format" value="plaintext" class="sr-only peer">
                                <span class="inline-flex items-center px-2.5 py-1.5 bg-ink-50 border border-ink-200 rounded-md text-xs font-medium text-ink-600 transition-all duration-150 peer-checked:border-oreilly-blue peer-checked:bg-oreilly-blue-light peer-checked:text-oreilly-blue-dark hover:bg-white hover:border-ink-300">Text</span>
                            </label>
                            <label class="format-option cursor-pointer">
                                <input type="radio" name="format" value="pdf" class="sr-only peer">
                                <span class="inline-flex items-center px-2.5 py-1.5 bg-ink-50 border border-ink-200 rounded-md text-xs font-medium text-ink-600 transition-all duration-150 peer-checked:border-oreilly-blue peer-checked:bg-oreilly-blue-light peer-checked:text-oreilly-blue-dark hover:bg-white hover:border-ink-300">PDF</span>
                            </label>
                            <label class="format-option cursor-pointer relative">
                                <input type="radio" name="format" value="chunks" class="sr-only peer">
                                <span class="inline-flex items-center px-2.5 py-1.5 bg-ink-50 border border-ink-200 rounded-md text-xs font-medium text-ink-600 transition-all duration-150 peer-checked:border-oreilly-blue peer-checked:bg-oreilly-blue-light peer-checked:text-oreilly-blue-dark hover:bg-white hover:border-ink-300">Chunks</span>
                                <span class="absolute -top-1 -right-1 text-[0.5rem] font-bold uppercase px-0.5 bg-emerald-500 text-white rounded peer-checked:bg-oreilly-blue leading-tight">RAG</span>
                            </label>
                            <label class="format-option cursor-pointer">
                                <input type="radio" name="format" value="epub" class="sr-only peer">
                                <span class="inline-flex items-center px-2.5 py-1.5 bg-ink-50 border border-ink-200 rounded-md text-xs font-medium text-ink-600 transition-all duration-150 peer-checked:border-oreilly-blue peer-checked:bg-oreilly-blue-light peer-checked:text-oreilly-blue-dark hover:bg-white hover:border-ink-300">EPUB</span>
                            </label>
                        </div>
                    </div>

                    <div class="chapters-selection mb-4">
                        <h4 class="text-[0.625rem] font-semibold uppercase tracking-wider text-ink-400 mb-2">Chapters</h4>
                        <div class="chapters-options grid grid-cols-2 gap-1.5">
                            <label class="chapters-option cursor-pointer">
                                <input type="radio" name="chapters-scope" value="all" checked class="sr-only peer">
                                <span class="flex items-center gap-2.5 p-2.5 bg-ink-50 border border-ink-200 rounded-md transition-all duration-150 peer-checked:border-oreilly-blue peer-checked:bg-oreilly-blue-light hover:bg-white hover:border-ink-300">
                                    <span class="flex flex-col min-w-0">
                                        <span class="text-xs font-medium text-ink-700">All Chapters</span>
                                        <span class="text-[0.625rem] text-ink-400">Full book</span>
                                    </span>
                                </span>
                            </label>
                            <label class="chapters-option cursor-pointer">
                                <input type="radio" name="chapters-scope" value="select" class="sr-only peer">
                                <span class="flex items-center gap-2.5 p-2.5 bg-ink-50 border border-ink-200 rounded-md transition-all duration-150 peer-checked:border-oreilly-blue peer-checked:bg-oreilly-blue-light hover:bg-white hover:border-ink-300">
                                    <span class="flex flex-col min-w-0">
                                        <span class="text-xs font-medium text-ink-700">Select Chapters</span>
                                        <span class="text-[0.625rem] text-ink-400">Pick specific</span>
                                    </span>
                                </span>
                            </label>
                        </div>
                    </div>

                    <div class="chapters-picker hidden mt-3 p-3 bg-ink-50 rounded-lg border border-ink-200">
                        <div class="flex items-center justify-between pb-2 border-b border-ink-200 mb-2">
                            <span class="chapters-summary text-xs font-medium text-ink-600">All chapters</span>
                            <div class="flex gap-1">
                                <button class="select-all-btn px-1.5 py-0.5 text-[0.625rem] font-medium text-oreilly-blue hover:bg-oreilly-blue-light rounded transition-colors duration-150">All</button>
                                <button class="select-none-btn px-1.5 py-0.5 text-[0.625rem] font-medium text-oreilly-blue hover:bg-oreilly-blue-light rounded transition-colors duration-150">None</button>
                            </div>
                        </div>
                        <div class="chapters-list max-h-44 overflow-y-auto space-y-0.5"></div>
                    </div>

                    <div class="output-selection">
                        <h4 class="text-[0.625rem] font-semibold uppercase tracking-wider text-ink-400 mb-2">Output</h4>
                        <div class="output-options grid grid-cols-2 gap-1.5">
                            <label class="output-option cursor-pointer">
                                <input type="radio" name="output-style" value="combined" checked class="sr-only peer">
                                <span class="flex items-center gap-2.5 p-2.5 bg-ink-50 border border-ink-200 rounded-md transition-all duration-150 peer-checked:border-oreilly-blue peer-checked:bg-oreilly-blue-light hover:bg-white hover:border-ink-300">
                                    <span class="flex flex-col min-w-0">
                                        <span class="text-xs font-medium text-ink-700">Combined</span>
                                        <span class="text-[0.625rem] text-ink-400">Single file</span>
                                    </span>
                                </span>
                            </label>
                            <label class="output-option cursor-pointer">
                                <input type="radio" name="output-style" value="separate" class="sr-only peer">
                                <span class="flex items-center gap-2.5 p-2.5 bg-ink-50 border border-ink-200 rounded-md transition-all duration-150 peer-checked:border-oreilly-blue peer-checked:bg-oreilly-blue-light hover:bg-white hover:border-ink-300">
                                    <span class="flex flex-col min-w-0">
                                        <span class="text-xs font-medium text-ink-700">Separate</span>
                                        <span class="text-[0.625rem] text-ink-400">Per chapter</span>
                                    </span>
                                </span>
                            </label>
                        </div>
                        <div class="output-locked-notice hidden flex items-center gap-1.5 p-2 mt-1.5 bg-ink-50 border border-dashed border-ink-200 rounded-md text-xs text-ink-500">
                            <svg class="w-3.5 h-3.5 flex-shrink-0 text-ink-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                                <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
                            </svg>
                            <span>Combined only for this format</span>
                        </div>
                    </div>
                </div>

                <details class="advanced-options border-t border-ink-100 pt-3">
                    <summary class="flex items-center gap-1 text-xs font-medium text-ink-500 cursor-pointer select-none py-1 hover:text-ink-700 transition-colors duration-150">
                        <svg class="toggle-icon w-3 h-3 transition-transform duration-150" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M9 18l6-6-6-6"/>
                        </svg>
                        Advanced
                    </summary>
                    <div class="pt-3 space-y-3">
                        <div>
                            <label class="block text-[0.625rem] font-semibold uppercase tracking-wider text-ink-400 mb-1.5">Save Location</label>
                            <div class="flex gap-1.5">
                                <input type="text" class="output-dir-input flex-1 px-2.5 py-1.5 text-xs font-mono bg-ink-50 border border-ink-200 rounded-md text-ink-600 focus:outline-none focus:border-oreilly-blue focus:bg-white transition-colors duration-150" placeholder="Loading..." readonly>
                                <button class="browse-btn px-2.5 py-1.5 text-[0.625rem] font-medium text-ink-600 bg-white border border-ink-300 rounded-md hover:bg-ink-50 transition-colors duration-150 active:scale-[0.97]">Browse</button>
                            </div>
                        </div>

                        <label class="flex items-center gap-2 cursor-pointer">
                            <input type="checkbox" class="skip-images w-3.5 h-3.5 rounded border-ink-300 text-oreilly-blue focus:ring-oreilly-blue/20">
                            <span class="text-xs text-ink-600">Skip images</span>
                            <span class="text-[0.625rem] text-ink-400">Faster, smaller files</span>
                        </label>

                        <div class="chunking-options hidden flex gap-3 p-3 bg-ink-50 rounded-md">
                            <div class="flex-1">
                                <label class="block text-[0.625rem] font-semibold uppercase tracking-wider text-ink-400 mb-1.5">Chunk Size</label>
                                <input type="number" class="chunk-size-input w-full px-2.5 py-1.5 text-xs border border-ink-200 rounded-md focus:outline-none focus:border-oreilly-blue transition-colors duration-150" value="4000" min="500" max="16000">
                            </div>
                            <div class="flex-1">
                                <label class="block text-[0.625rem] font-semibold uppercase tracking-wider text-ink-400 mb-1.5">Overlap</label>
                                <input type="number" class="chunk-overlap-input w-full px-2.5 py-1.5 text-xs border border-ink-200 rounded-md focus:outline-none focus:border-oreilly-blue transition-colors duration-150" value="200" min="0" max="1000">
                            </div>
                        </div>
                    </div>
                </details>

                <div class="progress-section hidden py-4 border-t border-ink-100">
                    <div class="flex justify-between items-center mb-1.5">
                        <span class="progress-label text-xs font-medium text-ink-700">Downloading...</span>
                        <span class="progress-percent text-xs font-semibold text-oreilly-blue font-mono">0%</span>
                    </div>
                    <div class="h-1 bg-ink-200 rounded-full overflow-hidden">
                        <div class="progress-fill h-full bg-oreilly-blue rounded-full transition-all duration-300 ease-out" style="width: 0%"></div>
                    </div>
                    <p class="progress-status mt-1.5 text-xs text-ink-500"></p>
                </div>

                <div class="result-section hidden py-4 border-t border-ink-100">
                    <div class="flex items-center gap-1.5 mb-3 text-emerald-600 text-xs font-medium">
                        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                            <polyline points="22 4 12 14.01 9 11.01"/>
                        </svg>
                        <span>Download Complete</span>
                    </div>
                    <div class="result-files space-y-1.5"></div>
                </div>

                <div class="flex justify-end gap-1.5 pt-4 border-t border-ink-100">
                    <button class="cancel-btn hidden h-8 px-4 text-xs font-medium text-ink-600 bg-white border border-ink-300 rounded-md hover:bg-ink-50 transition-colors duration-150 active:scale-[0.97]">Cancel</button>
                    <button class="download-btn h-8 px-5 text-xs font-medium text-white bg-oreilly-blue hover:bg-oreilly-blue-dark rounded-md transition-colors duration-150 disabled:bg-ink-300 disabled:cursor-not-allowed active:scale-[0.97]">Download</button>
                </div>
            </div>
        </div>
    `;
}

function setupBookCardEvents(div, book) {
    div.querySelector('.book-summary').onclick = () => expandBook(div, book.id);

    div.querySelector('.close-btn').onclick = (e) => {
        e.stopPropagation();
        collapseBook();
    };

    div.querySelector('.download-btn').onclick = (e) => {
        e.stopPropagation();
        download(div);
    };

    div.querySelector('.cancel-btn').onclick = (e) => {
        e.stopPropagation();
        cancelDownload(div);
    };

    div.querySelectorAll('input[name="format"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            handleFormatChange(div, e.target.value, book.id);
        });
    });

    div.querySelectorAll('input[name="chapters-scope"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            handleChaptersScopeChange(div, e.target.value, book.id);
        });
    });

    div.querySelector('.select-all-btn').onclick = (e) => {
        e.stopPropagation();
        selectAllChapters(div, true);
    };
    div.querySelector('.select-none-btn').onclick = (e) => {
        e.stopPropagation();
        selectAllChapters(div, false);
    };

    div.querySelector('.browse-btn').onclick = (e) => {
        e.stopPropagation();
        browseOutputDir(div);
    };

    const advancedOptions = div.querySelector('.advanced-options');
    advancedOptions.addEventListener('toggle', () => {
        const icon = advancedOptions.querySelector('.toggle-icon');
        if (advancedOptions.open) {
            icon.style.transform = 'rotate(90deg)';
        } else {
            icon.style.transform = 'rotate(0deg)';
        }
    });
}

const BOOK_ONLY_FORMATS = ['epub', 'chunks'];

function handleFormatChange(cardElement, format, bookId) {
    const outputSelection = cardElement.querySelector('.output-selection');
    const outputOptions = cardElement.querySelector('.output-options');
    const lockedNotice = cardElement.querySelector('.output-locked-notice');
    const chunkingOptions = cardElement.querySelector('.chunking-options');
    const chaptersPicker = cardElement.querySelector('.chapters-picker');

    chunkingOptions.classList.toggle('hidden', format !== 'chunks');

    if (BOOK_ONLY_FORMATS.includes(format)) {
        outputOptions.classList.add('hidden');
        lockedNotice.classList.remove('hidden');

        const combinedRadio = cardElement.querySelector('input[name="output-style"][value="combined"]');
        if (combinedRadio) combinedRadio.checked = true;
    } else {
        outputOptions.classList.remove('hidden');
        lockedNotice.classList.add('hidden');
    }

    const currentChaptersScope = cardElement.querySelector('input[name="chapters-scope"]:checked')?.value;
    if (currentChaptersScope === 'select') {
        loadChaptersIfNeeded(cardElement, bookId);
        chaptersPicker.classList.remove('hidden');
    }
}

function handleChaptersScopeChange(cardElement, chaptersScope, bookId) {
    const chaptersPicker = cardElement.querySelector('.chapters-picker');

    if (chaptersScope === 'select') {
        loadChaptersIfNeeded(cardElement, bookId);
        chaptersPicker.classList.remove('hidden');
    } else {
        chaptersPicker.classList.add('hidden');
    }
}

async function loadChaptersIfNeeded(cardElement, bookId) {
    if (chaptersCache[bookId]) {
        // Already loaded
        if (cardElement.querySelector('.chapters-list').children.length === 0) {
            renderChapters(cardElement, chaptersCache[bookId]);
        }
        return;
    }

    const listContainer = cardElement.querySelector('.chapters-list');
    listContainer.innerHTML = '<p class="text-xs text-ink-400 animate-pulse-subtle py-2">Loading chapters...</p>';

    try {
        const res = await fetch(`${API}/api/book/${bookId}/chapters`);
        const data = await res.json();
        chaptersCache[bookId] = data.chapters;
        renderChapters(cardElement, data.chapters);
    } catch (err) {
        listContainer.innerHTML = '<p class="text-xs text-red-600 py-2">Failed to load chapters</p>';
    }
}

async function expandBook(cardElement, bookId) {
    if (currentExpandedCard && currentExpandedCard !== cardElement) {
        collapseBook();
    }

    if (cardElement.classList.contains('expanded')) {
        return;
    }

    const expanded = cardElement.querySelector('.book-expanded');

    cardElement.classList.add('expanded');
    cardElement.classList.remove('hover:border-ink-300', 'hover:shadow-card-hover');
    cardElement.classList.add('border-oreilly-blue', 'shadow-card-expanded');

    const expandIcon = cardElement.querySelector('.expand-icon');
    expandIcon.style.transform = 'rotate(180deg)';

    expanded.classList.remove('hidden');
    document.getElementById('search-results').classList.add('has-expanded');
    currentExpandedCard = cardElement;

    setTimeout(() => {
        cardElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);

    const outputDirInput = expanded.querySelector('.output-dir-input');
    outputDirInput.value = defaultOutputDir || 'Loading...';

    try {
        const res = await fetch(`${API}/api/book/${bookId}`);
        const book = await res.json();

        const publisherEl = expanded.querySelector('.publisher-value');
        const pagesEl = expanded.querySelector('.pages-value');
        const descEl = expanded.querySelector('.book-description');

        publisherEl.textContent = book.publishers?.join(', ') || 'Unknown';
        publisherEl.classList.remove('animate-pulse-subtle');

        pagesEl.textContent = book.virtual_pages || 'N/A';
        pagesEl.classList.remove('animate-pulse-subtle');

        descEl.innerHTML = book.description || 'No description available.';
        descEl.classList.remove('animate-pulse-subtle');
    } catch (error) {
        const descEl = expanded.querySelector('.book-description');
        descEl.textContent = 'Failed to load details.';
        descEl.classList.remove('animate-pulse-subtle');
    }
}

function collapseBook() {
    if (currentExpandedCard) {
        const expanded = currentExpandedCard.querySelector('.book-expanded');

        currentExpandedCard.classList.remove('expanded', 'border-oreilly-blue', 'shadow-card-expanded');
        currentExpandedCard.classList.add('hover:border-ink-300', 'hover:shadow-card-hover');

        const expandIcon = currentExpandedCard.querySelector('.expand-icon');
        expandIcon.style.transform = 'rotate(0deg)';

        expanded.classList.add('hidden');

        const progressSection = currentExpandedCard.querySelector('.progress-section');
        const resultSection = currentExpandedCard.querySelector('.result-section');
        progressSection.classList.add('hidden');
        resultSection.classList.add('hidden');

        document.getElementById('search-results').classList.remove('has-expanded');
        currentExpandedCard = null;
    }
}

function renderChapters(cardElement, chapters) {
    const listContainer = cardElement.querySelector('.chapters-list');

    listContainer.innerHTML = chapters.map((ch) => `
        <label class="chapter-item flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer hover:bg-ink-100 transition-colors duration-150">
            <input type="checkbox" class="chapter-checkbox w-3.5 h-3.5 rounded border-ink-300 text-oreilly-blue focus:ring-oreilly-blue/20" data-index="${ch.index}" checked>
            <span class="flex-1 text-xs text-ink-700 truncate">${ch.title || 'Chapter ' + (ch.index + 1)}</span>
            ${ch.pages ? `<span class="text-[0.625rem] text-ink-400 flex-shrink-0">${ch.pages}p</span>` : ''}
        </label>
    `).join('');

    updateChapterCount(cardElement);

    listContainer.querySelectorAll('.chapter-checkbox').forEach(cb => {
        cb.addEventListener('change', () => updateChapterCount(cardElement));
    });
}

function updateChapterCount(cardElement) {
    const checkboxes = cardElement.querySelectorAll('.chapter-checkbox');
    const checked = cardElement.querySelectorAll('.chapter-checkbox:checked');
    const summaryEl = cardElement.querySelector('.chapters-summary');

    if (checked.length === checkboxes.length) {
        summaryEl.textContent = `All ${checkboxes.length} chapters`;
    } else if (checked.length === 0) {
        summaryEl.textContent = 'No chapters selected';
    } else {
        summaryEl.textContent = `${checked.length} of ${checkboxes.length} chapters`;
    }
}

function selectAllChapters(cardElement, selectAll) {
    cardElement.querySelectorAll('.chapter-checkbox').forEach(cb => cb.checked = selectAll);
    updateChapterCount(cardElement);
}

async function download(cardElement) {
    const bookId = cardElement.dataset.bookId;

    const formatRadio = cardElement.querySelector('input[name="format"]:checked');
    const format = formatRadio ? formatRadio.value : null;

    if (!format) {
            const formatOptions = cardElement.querySelector('.format-options');
        formatOptions.classList.add('animate-shake');
        setTimeout(() => formatOptions.classList.remove('animate-shake'), 500);
        return;
    }

    const chaptersScopeRadio = cardElement.querySelector('input[name="chapters-scope"]:checked');
    const chaptersScope = chaptersScopeRadio ? chaptersScopeRadio.value : 'all';

    const outputStyleRadio = cardElement.querySelector('input[name="output-style"]:checked');
    const outputStyle = outputStyleRadio ? outputStyleRadio.value : 'combined';

    let finalFormat = format;
    if (outputStyle === 'separate' && !BOOK_ONLY_FORMATS.includes(format)) {
        finalFormat = `${format}-chapters`;
    }

    let selectedChapters = null;
    if (chaptersScope === 'select') {
        const chapterCheckboxes = cardElement.querySelectorAll('.chapter-checkbox');
        const checkedBoxes = cardElement.querySelectorAll('.chapter-checkbox:checked');

        if (checkedBoxes.length === 0) {
            const chaptersPicker = cardElement.querySelector('.chapters-picker');
            chaptersPicker.classList.add('animate-shake');
            setTimeout(() => chaptersPicker.classList.remove('animate-shake'), 500);
            return;
        }

        if (checkedBoxes.length < chapterCheckboxes.length) {
            selectedChapters = Array.from(checkedBoxes).map(cb => parseInt(cb.dataset.index));
        }
    }

    const progressSection = cardElement.querySelector('.progress-section');
    const resultSection = cardElement.querySelector('.result-section');
    const downloadBtn = cardElement.querySelector('.download-btn');
    const cancelBtn = cardElement.querySelector('.cancel-btn');
    const progressFill = cardElement.querySelector('.progress-fill');

    progressSection.classList.remove('hidden');
    resultSection.classList.add('hidden');
    downloadBtn.classList.add('hidden');
    cancelBtn.classList.remove('hidden');
    progressFill.style.width = '0%';

    const outputDirInput = cardElement.querySelector('.output-dir-input');
    const outputDir = outputDirInput.value.trim();

    const requestBody = { book_id: bookId, format: finalFormat };
    if (selectedChapters !== null) {
        requestBody.chapters = selectedChapters;
    }
    if (outputDir && outputDir !== defaultOutputDir) {
        requestBody.output_dir = outputDir;
    }
    if (format === 'chunks') {
        const chunkSize = parseInt(cardElement.querySelector('.chunk-size-input').value) || 4000;
        const chunkOverlap = parseInt(cardElement.querySelector('.chunk-overlap-input').value) || 200;
        requestBody.chunking = {
            chunk_size: chunkSize,
            overlap: chunkOverlap
        };
    }
    if (cardElement.querySelector('.skip-images').checked) {
        requestBody.skip_images = true;
    }

    try {
        const res = await fetch(`${API}/api/download`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        const result = await res.json();

        if (result.error) {
            cardElement.querySelector('.progress-status').textContent = `Error: ${result.error}`;
            downloadBtn.classList.remove('hidden');
            cancelBtn.classList.add('hidden');
            return;
        }

        pollProgress(cardElement);
    } catch (err) {
        cardElement.querySelector('.progress-status').textContent = 'Download failed. Please try again.';
        downloadBtn.classList.remove('hidden');
        cancelBtn.classList.add('hidden');
    }
}

async function cancelDownload(cardElement) {
    const cancelBtn = cardElement.querySelector('.cancel-btn');
    cancelBtn.disabled = true;
    cancelBtn.textContent = 'Cancelling...';

    try {
        await fetch(`${API}/api/cancel`, { method: 'POST' });
    } catch (err) {
        console.error('Cancel request failed:', err);
    }
}

function formatETA(seconds) {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins < 60) return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
    const hours = Math.floor(mins / 60);
    const remainMins = mins % 60;
    return `${hours}h ${remainMins}m`;
}

async function pollProgress(cardElement) {
    try {
        const res = await fetch(`${API}/api/progress`);
        const data = await res.json();

        const progressFill = cardElement.querySelector('.progress-fill');
        const progressStatus = cardElement.querySelector('.progress-status');
        const progressPercent = cardElement.querySelector('.progress-percent');
        const progressSection = cardElement.querySelector('.progress-section');
        const resultSection = cardElement.querySelector('.result-section');
        const downloadBtn = cardElement.querySelector('.download-btn');
        const cancelBtn = cardElement.querySelector('.cancel-btn');

        let status = data.status || 'waiting';
        const details = [];

        if (data.current_chapter && data.total_chapters) {
            details.push(`Chapter ${data.current_chapter}/${data.total_chapters}`);
        }

        if (typeof data.percentage === 'number') {
            progressFill.style.width = `${data.percentage}%`;
            progressPercent.textContent = `${data.percentage}%`;
        }

        if (data.eta_seconds && data.eta_seconds > 0) {
            details.push(`~${formatETA(data.eta_seconds)} remaining`);
        }

        if (data.chapter_title) {
            const title = data.chapter_title.length > 40
                ? data.chapter_title.substring(0, 40) + '...'
                : data.chapter_title;
            status = title;
        }

        progressStatus.textContent = details.length > 0 ? details.join(' • ') : status;

        function restoreButtons() {
            downloadBtn.classList.remove('hidden');
            downloadBtn.disabled = false;
            cancelBtn.classList.add('hidden');
            cancelBtn.disabled = false;
            cancelBtn.textContent = 'Cancel';
        }

        if (data.status === 'completed') {
            restoreButtons();
            progressSection.classList.add('hidden');
            resultSection.classList.remove('hidden');

            let filesHTML = '';
            if (data.epub) filesHTML += createFileResultHTML('EPUB', data.epub);
            if (data.pdf) {
                if (Array.isArray(data.pdf)) {
                    filesHTML += `<div class="flex items-center gap-2 px-3 py-2 bg-ink-50 rounded-md text-xs"><span class="font-medium text-ink-700 min-w-[56px]">PDF</span><span class="flex-1 font-mono text-[0.625rem] text-ink-500 truncate">${data.pdf.length} chapter files</span></div>`;
                } else {
                    filesHTML += createFileResultHTML('PDF', data.pdf);
                }
            }
            if (data.markdown) filesHTML += createFileResultHTML('Markdown', data.markdown);
            if (data.plaintext) filesHTML += createFileResultHTML('Plain Text', data.plaintext);
            if (data.json) filesHTML += createFileResultHTML('JSON', data.json);
            if (data.chunks) filesHTML += createFileResultHTML('Chunks', data.chunks);

            cardElement.querySelector('.result-files').innerHTML = filesHTML;
        } else if (data.status === 'error') {
            restoreButtons();
            progressStatus.textContent = `Error: ${data.error}`;
        } else {
            setTimeout(() => pollProgress(cardElement), 500);
        }
    } catch (err) {
        console.error('Progress polling failed:', err);
        setTimeout(() => pollProgress(cardElement), 1000);
    }
}

function createFileResultHTML(label, path) {
    const escapedPath = path.replace(/'/g, "\\'");
    return `
        <div class="flex items-center gap-2 px-3 py-2 bg-ink-50 rounded-md text-xs">
            <span class="font-medium text-ink-700 min-w-[56px]">${label}</span>
            <span class="flex-1 font-mono text-[0.625rem] text-ink-500 truncate" title="${path}">${path}</span>
            <button class="px-1.5 py-0.5 text-[0.625rem] font-medium text-oreilly-blue hover:bg-oreilly-blue-light rounded transition-colors duration-150" onclick="revealFile('${escapedPath}')">Reveal</button>
        </div>
    `;
}

async function revealFile(path) {
    try {
        const res = await fetch(`${API}/api/reveal`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path })
        });
        const data = await res.json();
        if (data.error) {
            console.error('Reveal failed:', data.error);
        }
    } catch (err) {
        console.error('Reveal request failed:', err);
    }
}

async function browseOutputDir(cardElement) {
    const browseBtn = cardElement.querySelector('.browse-btn');
    const outputDirInput = cardElement.querySelector('.output-dir-input');

    browseBtn.disabled = true;
    browseBtn.textContent = 'Opening...';

    try {
        const res = await fetch(`${API}/api/settings/output-dir`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ browse: true })
        });
        const data = await res.json();

        if (data.success && data.path) {
            outputDirInput.value = data.path;
        }
    } catch (err) {
        console.error('Browse request failed:', err);
    }

    browseBtn.disabled = false;
    browseBtn.textContent = 'Browse';
}

function updateSelectedResult() {
    const results = document.querySelectorAll('.book-card');
    results.forEach((r, i) => {
        if (i === selectedResultIndex) {
            r.classList.add('ring-2', 'ring-oreilly-blue/30');
        } else {
            r.classList.remove('ring-2', 'ring-oreilly-blue/30');
        }
    });
    if (selectedResultIndex >= 0 && results[selectedResultIndex]) {
        results[selectedResultIndex].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    loadDefaultOutputDir();

    document.getElementById('login-btn').onclick = showCookieModal;
    document.getElementById('cancel-modal-btn').onclick = hideCookieModal;
    document.getElementById('save-cookies-btn').onclick = saveCookies;
    document.getElementById('cookie-modal').onclick = (e) => {
        if (e.target.id === 'cookie-modal') hideCookieModal();
    };

    let searchTimeout;
    const searchInput = document.getElementById('search-input');

    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        const query = e.target.value.trim();
        if (query.length >= 2) {
            searchTimeout = setTimeout(() => search(query), 300);
        } else if (query.length === 0) {
            document.getElementById('search-results').innerHTML = '';
            currentExpandedCard = null;
        }
    });

    document.addEventListener('click', (e) => {
        if (currentExpandedCard && !currentExpandedCard.contains(e.target)) {
            collapseBook();
        }
    });

    document.addEventListener('keydown', (e) => {
        const results = document.querySelectorAll('.book-card');
        const searchInput = document.getElementById('search-input');

        if (e.key === 'Escape') {
            if (currentExpandedCard) {
                collapseBook();
                e.preventDefault();
            }
            return;
        }

        if (e.key === 'Enter' && document.activeElement === searchInput) {
            clearTimeout(searchTimeout);
            const query = searchInput.value.trim();
            if (query.length >= 2) {
                search(query);
            }
            e.preventDefault();
            return;
        }

        if (!results.length || currentExpandedCard) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            selectedResultIndex = Math.min(selectedResultIndex + 1, results.length - 1);
            updateSelectedResult();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            selectedResultIndex = Math.max(selectedResultIndex - 1, 0);
            updateSelectedResult();
        } else if (e.key === 'Enter' && selectedResultIndex >= 0) {
            e.preventDefault();
            const selected = results[selectedResultIndex];
            if (selected) {
                expandBook(selected, selected.dataset.bookId);
            }
        }
    });
});
