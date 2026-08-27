// WanderAmsterdam Tours App
// Load tours from JSON and render with descriptions

// Fallback for tour records with no image. Applied at render time, not just via
// onerror: `src="undefined"` costs a real 404 before onerror can rescue it.
// Local + Pexels-licensed; images/ATTRIBUTION.md records source slug
// "scenic-amsterdam-canal-view-with-boating-activity-33388081",
// which verifies the region from the source URL, not from our own caption.
const FALLBACK_IMAGE = '/images/hero-photo-1.jpg';

let toursData = [];

// Wire the homepage "Verified Tours" stat to the live (non-dead) catalog
// size, replacing the hardcoded value. No-op on pages without the element.
function updateVerifiedToursCount(n) {
    const el = document.getElementById('verified-tours-count');
    if (el) el.textContent = Number(n).toLocaleString();
}

// ===== BOOKING PERFORMANCE OPTIMIZATIONS =====

// 1. URL Caching - Pre-cache FareHarbor URLs for instant clicks
const bookingUrlCache = {};

function cacheBookingUrl(tourId, url) {
    bookingUrlCache[tourId] = {
        url: url,
        cached_at: Date.now()
    };
    try {
        localStorage.setItem('fh_cache_' + tourId, JSON.stringify(bookingUrlCache[tourId]));
    } catch (e) {
        // localStorage full - continue without persistence
    }
}

function getBookingUrl(tourId, fallbackUrl) {
    const cached = bookingUrlCache[tourId];
    if (cached && Date.now() - cached.cached_at < 3600000) {
        return cached.url;
    }
    return fallbackUrl;
}

function preCacheBookingUrls(tours) {
    tours.forEach(tour => {
        if (tour.bookingUrl) {
            cacheBookingUrl(tour.id || tour.name, tour.bookingUrl);
        }
    });
}

// 2. GA4 Tracking Functions
function trackFilterChange(filterType, value) {
    gtag('event', 'filter_used', {
        filter_type: filterType,
        value: value,
        event_category: 'engagement'
    });
}

function trackSearchUsed(searchTerm) {
    gtag('event', 'search_used', {
        query: searchTerm,
        event_category: 'engagement'
    });
}

function trackLoadMoreClick() {
    gtag('event', 'load_more_clicked', {
        event_category: 'engagement'
    });
}

let filteredTours = [];
let displayedCount = 0;
const TOURS_PER_PAGE = 24;

// Load tours data
async function loadTours() {
    try {
        console.log('🔄 Fetching tours-data.json...');
        const response = await fetch('tours-data.json');
        console.log(`📥 Response status: ${response.status}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const _raw = await response.json();
        toursData = Array.isArray(_raw) ? _raw : _raw.tours;
        toursData = toursData.filter(t => t.status !== 'inactive' && !t.bookingDead);
        updateVerifiedToursCount(toursData.length);
        console.log(`✅ Loaded ${toursData.length} tours`);

        // Initial shuffle for randomization (per page load, non-persistent)
        toursData = shuffleArray(toursData);
        filteredTours = [...toursData];
        
        // Pre-cache booking URLs for instant clicks
        preCacheBookingUrls(toursData);
        
        displayedCount = 0;
        renderTours();
        updateResultsCount();
        console.log('✅ Tours rendered successfully');
    } catch (error) {
        console.error('❌ Error loading tours:', error.message);
        document.getElementById('tours-grid').innerHTML = `
            <div class="error-state">
                <p>⚠️ Unable to load tours. Please refresh the page.</p>
                <p style="font-size: 12px; color: #666;">Error: ${error.message}</p>
            </div>
        `;
    }
}

// Helper functions
function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Pricing unit for the card badge — "per group", "whole boat · up to 4 people".
// Ported verbatim from keywestsandbartours/app.js priceUnit() (via wandernewzealand
// #108): driven ONLY by the explicit _unknownFields.priceUnit string — no inference
// from priceLabel words. Empty for every row that does not carry one, so those cards
// render exactly as they did before this existed. formatPrice() is left alone: it
// answers "what is the number", this answers "what does the number buy".
function priceUnit(tour) {
    const u = (tour._unknownFields || {}).priceUnit;
    return (typeof u === "string" && u.trim()) ? u.trim() : "";
}

function formatPrice(price, confidence) {
    if (!Number.isFinite(price) || price <= 0) return 'Price on request';
    if (confidence === 'low') return 'Price on request';
    return `From €${price}`;
}

function cleanLocation(location = '') {
    return location
        .replace(/^United States\/Amsterdam\//, '')
        .replace(/^Amsterdam\//, '')
        .trim() || 'Amsterdam';
}

function scoreLabel(score) {
    if (score >= 90) return 'Top Rated';
    if (score >= 75) return 'Popular';
    return '';
}

// --- s53 schema unit gate ---------------------------------------------------
// A bare Offer.price is read as per-person by the Bing/ChatGPT/Copilot
// ecosystem -- this network's primary conversion channel -- so a whole-boat
// or private-group tour emitted bare misquotes its total as a per-person fare.
// Ruled s52 (network decision): the gate has THREE states, derived from the
// row's own evidence -- _unknownFields.priceUnit (the exact string the card
// renders), priceLabel, and the anchor tier (the priceBreakdown tier whose
// price equals the emitted price). A tier note is corroborating only and is
// never read here.
//   1. per-person affirmatively asserted   -> bare Offer.price, byte-identical
//      to what shipped before this gate existed.
//   2. non-per-person affirmatively asserted -> no bare price; a
//      UnitPriceSpecification whose unitText is the VERBATIM card string (the
//      same field the card reads) -- never a parallel wording. If the card
//      renders no unit string there is nothing to mirror, so no price at all.
//   3. no unit evidence either way -> no price at all. Absence of evidence is
//      not per-person; silence is honest, a guess is not.
// Every word list below is built from the pool's own vocabulary
// (scripts/evidence/s53-wams-schema-gate/vocab-out.txt), and every string the
// lists do not reach falls to state 3 -- ambiguity resolves toward silence.
// This pool is multilingual (Dutch/English/Spanish/Portuguese/Italian), so
// boundaries are built on Unicode letters/digits, not ASCII \w -- the default
// \b treats accented letters (é, í...) as non-word and silently fails to
// match a word ending in one (e.g. "introducé").
function unitWordBoundary(pattern) {
    return new RegExp(`(?<![\\p{L}\\p{N}_])(?:${pattern})(?![\\p{L}\\p{N}_])`, 'iu');
}
// Leading-boundary-only match: this pool's source data glues "Privé"/"Prive"
// onto a following word with no separator ("Privécharter", "Privérondleiding").
// Every occurrence of this prefix in the pool's vocabulary is about private
// ownership/exclusivity, so matching it as a word-START is safe without also
// requiring a word-END.
function unitWordPrefix(pattern) {
    return new RegExp(`(?<![\\p{L}\\p{N}_])(?:${pattern})`, 'iu');
}

// Classify one evidence string: 'per-person', 'non-per-person', or '' (no
// verdict). An explicit "per person"/"pp" marker wins even when the same
// string also names a group ("per person, Groep vanaf 25 personen" -- this
// pool's own extraction pipeline prefixes "per person, " onto a group-sized
// tier label precisely to assert the price shown is per attendee, not per
// group). That check runs before the non-per-person patterns for the same
// reason Hawaii's shared/semi-private check ran before its exclusivity test.
function classifyUnitText(s) {
    if (typeof s !== 'string' || !s.trim()) return '';
    const str = s.trim();

    const EXPLICIT_PP_RES = [
        unitWordBoundary('per[\\s-]?persons?'), unitWordBoundary('per[\\s-]?persoons?'),
        /\/\s?person\b/i,
        unitWordBoundary('price\\s*pp'), /\(\s*pp\s*\)/i
    ];
    if (EXPLICIT_PP_RES.some((re) => re.test(str))) return 'per-person';

    // Whole-unit evidence: exclusivity (EN/NL), group/party phrasing (EN/NL/
    // ES/PT/IT), vehicle/vessel/equipment nouns, rental terms, capacity counts.
    const NON_PER_PERSON_RES = [
        unitWordPrefix('priv(?:ate|é|e)'),
        unitWordBoundary('charters?|chartered'),
        unitWordBoundary('per[\\s-]?(?:group|groep|booking|party|boat|boot|couple|family|vehicle|van|unit|hour)'),
        unitWordBoundary('grupo\\s?privad[oa]'),
        unitWordBoundary('grupp?o\\s?privato'),
        unitWordBoundary('groep(?:je)?'),
        unitWordBoundary('grupos?'),
        unitWordBoundary('group\\s?(?:of|size|rate)'),
        unitWordBoundary('group'),
        unitWordBoundary('besloten'),
        unitWordBoundary('gezelschap'),
        unitWordBoundary('vanaf'),
        unitWordBoundary('couples?'), unitWordBoundary('koppel'),
        unitWordBoundary('huur'), unitWordBoundary('verhuur'), unitWordBoundary('rentals?'),
        unitWordBoundary('boats?'), unitWordBoundary('cars?'), unitWordBoundary('scooters?'),
        unitWordBoundary('bikes?'), unitWordBoundary('bicycles?'),
        unitWordBoundary('fiets(?:en)?'), unitWordBoundary("kano(?:'s)?"),
        unitWordBoundary('e-?hopper'), unitWordBoundary('klikpedalen'), unitWordBoundary('step(?:pen)?'),
        unitWordBoundary('limo(?:usine)?'), unitWordBoundary('sup'), unitWordBoundary('mtb'),
        unitWordBoundary('gravelbike'), unitWordBoundary('booth'), unitWordBoundary('packages?'),
        unitWordBoundary('of\\s?meer'), unitWordBoundary('or\\s?more'),
        /\d\s*(?:[-–—~]|to|t\/m)\s*\d+\s*(?:people|persons?|personen|pessoas|personas|guests?|passengers?|students?)\b/i,
        /\bup\s?to\s+\d+\s*(?:people|persons?|guests?)\b/i,
        /\b\d+\+?\s?(?:people|persons?|personen|guests?|passengers?)\b/i,
        /\b\d+\s?or\s?more\s?(?:people|persons?)\b/i
    ];
    for (const re of NON_PER_PERSON_RES) {
        if (re.test(str)) return 'non-per-person';
    }

    // Per-person evidence: explicit per-X phrasing, customer-type nouns
    // (EN/NL), age qualifiers, ticket/admission wording, per-student formats.
    const PER_PERSON_RES = [
        unitWordBoundary('per[\\s-]?(?:person|adult|child|guest|passenger|participant|rider|student|traveler|traveller)'),
        unitWordBoundary('adults?'), unitWordBoundary('adulto?s?'), unitWordBoundary('volwassen(?:en?)?'),
        unitWordBoundary('child(?:ren)?'), unitWordBoundary('kids?'), unitWordBoundary('kind(?:eren)?'),
        unitWordBoundary('persons?'), unitWordBoundary('people'), unitWordBoundary('persoon'), unitWordBoundary('personen'),
        unitWordBoundary('travele?rs?'), unitWordBoundary('passengers?'), unitWordBoundary('participants?'),
        unitWordBoundary('guests?'), unitWordBoundary('students?'), unitWordBoundary('studenten'),
        unitWordBoundary('leerlingen'), unitWordBoundary('docent(?:en)?'), unitWordBoundary('introduc[ée]s?'),
        unitWordBoundary('individuals?'), unitWordBoundary('attendees?'), unitWordBoundary('admission'),
        /\bages?\s?\d+/i,
        /\b\d+\s?(?:&|and|or)\s?(?:up|under|over|younger|older)\b/i,
        /\b\d+\+\b/i,
        /\b\d+\s?years?\s?(?:and\s?up|old)?\b/i,
        unitWordBoundary('singles?'), unitWordBoundary('tickets?'),
        unitWordBoundary('courses?'), unitWordBoundary('class(?:es)?'),
        unitWordBoundary('certifications?'), unitWordBoundary('camps?'), unitWordBoundary('lessons?')
    ];
    for (const re of PER_PERSON_RES) {
        if (re.test(str)) return 'per-person';
    }
    return '';
}

// Combine the row's three evidence sources into one state. priceUnit is
// authoritative when it has a verdict: this pool's own pipeline prefixes
// "per person, " onto priceUnit specifically to disclose whether the number
// shown is a per-attendee share or a lump sum, for tiers whose raw name is a
// party-size band ("Groep vanaf 25 personen", "6 People") that reads as a
// capacity assertion in isolation but is actually a bulk-discount PER-PERSON
// rate (confirmed against priceBreakdown: e.g. pk 465763 "Persoon" €26.24 vs
// "Groep vanaf 25 personen" €23.62 -- both per-person, the second just a
// volume discount). priceLabel/anchor are the raw upstream tier names and
// only decide when priceUnit itself is empty or unclassifiable; among those
// two, a whole-unit assertion outranks a per-person one -- the harm of a
// wrong bare price (a private/group tour read as per-person) dwarfs the harm
// of a suppressed one. (Verified: zero rows in this pool have priceUnit
// asserting non-per-person while priceLabel/anchor assert per-person, so this
// priority never suppresses a genuine whole-unit price.)
function unitStateFromEvidence(tour) {
    const cardVerdict = classifyUnitText(priceUnit(tour));
    if (cardVerdict) return cardVerdict;

    const pb = Array.isArray(tour.priceBreakdown) ? tour.priceBreakdown : [];
    const anchor = pb.find((p) => p.price === tour.price);
    const fallbackVerdicts = [
        (tour.priceLabel || '').trim(),
        anchor ? (anchor.singular || '').trim() : ''
    ].map(classifyUnitText);
    if (fallbackVerdicts.includes('non-per-person')) return 'non-per-person';
    if (fallbackVerdicts.includes('per-person')) return 'per-person';
    return 'none';
}

function generateTourSchema(tour) {
    const emitPrice = Number.isFinite(tour.price) && tour.priceConfidence !== 'low';
    const state = emitPrice ? unitStateFromEvidence(tour) : 'none';
    const cardUnit = priceUnit(tour);
    return {
        "@context": "https://schema.org",
        "@type": "TouristTrip",
        "name": tour.name,
        "description": tour.description || "",
        "touristType": tour.tags ? tour.tags.join(", ") : "",
        ...(state === 'per-person' && {
            "offers": {
                "@type": "Offer",
                "price": tour.price,
                "priceCurrency": "EUR",
                "url": tour.bookingUrl,
                "availability": "https://schema.org/InStock"
            }
        }),
        // unitText must mirror the visible card verbatim; a non-per-person row
        // whose card shows no unit string (or whose card string itself reads
        // per-person, a contradiction) has nothing honest to emit, so it emits
        // no price at all.
        ...(state === 'non-per-person' && cardUnit && classifyUnitText(cardUnit) !== 'per-person' && {
            "offers": {
                "@type": "Offer",
                "priceSpecification": {
                    "@type": "UnitPriceSpecification",
                    "price": tour.price,
                    "priceCurrency": "EUR",
                    "unitText": cardUnit
                },
                "url": tour.bookingUrl,
                "availability": "https://schema.org/InStock"
            }
        }),
        "provider": {
            "@type": "LocalBusiness",
            "name": tour.company
        }
    };
}

// Fisher-Yates shuffle (non-mutating)
function shuffleArray(arr) {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
}

// Create tour card HTML
function createTourCard(tour) {
    const tags = tour.tags || [];
    const tagDisplay = tags.slice(0, 3).map(tag =>
        `<span class="tour-tag">${escapeHtml(tag)}</span>`
    ).join(' ');

    const description = tour.description || '';
    const safeDesc = description.replace(/\s+/g, ' ').trim();
    const truncatedDesc = safeDesc.length > 120
        ? safeDesc.substring(0, safeDesc.lastIndexOf(' ', 117)) + '…'
        : safeDesc;

    const score = tour.qualityScore || 0;
    const badge = scoreLabel(score);
    const qualityBadge = badge
        ? `<span class="quality-badge">⭐ ${badge}</span>`
        : '';

    const cleanLoc = cleanLocation(tour.location);
    const priceDisplay = formatPrice(tour.price, tour.priceConfidence);
    const unit = priceUnit(tour);
    const unitHtml = unit ? `<small>${escapeHtml(unit)}</small>` : '';

    const schema = generateTourSchema(tour);
    const schemaJson = JSON.stringify(schema).replace(/<\/script/gi, '<\\/script');

    let badgesHtml = '<div class="tour-badges">';
    if (tour.freeCancellation) {
        badgesHtml += '<span class="trust-badge free-cancel">Free Cancellation</span>';
    }
    badgesHtml += '</div>';

    return `
        <article class="tour-card" data-id="${tour.id}">
            <script type="application/ld+json">${schemaJson}</script>
            <div class="tour-image">
                <img src="${tour.image || FALLBACK_IMAGE}" alt="${escapeHtml(tour.name)}" loading="lazy" width="400" height="300" onerror="this.src='${FALLBACK_IMAGE}'" style="width: 100%; height: auto; object-fit: cover;">
                ${qualityBadge}
            </div>
            <div class="tour-content">
                <div class="tour-meta">
                    <span class="tour-location">📍 ${escapeHtml(cleanLoc)}, ${escapeHtml(capitalizeIsland(tour.island))}</span>
                </div>
                <h3 class="tour-title">${escapeHtml(tour.name)}</h3>
                <p class="tour-description">${escapeHtml(truncatedDesc)}</p>
                <div class="tour-tags">${tagDisplay}</div>
                <div class="tour-footer">
                    <div class="tour-price">${priceDisplay}${unitHtml}</div>
                    <a href="${tour.bookingUrl}" target="_blank" rel="noopener" class="tour-book-btn book-now-btn" data-tour-id="${escapeHtml(tour.id)}" data-tour-name="${escapeHtml(tour.name)}" style="text-decoration: none;">Check Availability →</a>
                </div>
            </div>
        </article>
    `;
}

function capitalizeIsland(island) {
    if (!island) return '';
    if (island.toLowerCase() === 'big island') return 'Big Island';
    return island.charAt(0).toUpperCase() + island.slice(1);
}

// Render tours to grid
function renderTours(append = false) {
    const grid = document.getElementById('tours-grid');
    const toursToShow = filteredTours.slice(
        append ? displayedCount : 0, 
        displayedCount + TOURS_PER_PAGE
    );
    
    const html = toursToShow.map(createTourCard).join('');
    
    if (append) {
        grid.insertAdjacentHTML('beforeend', html);
    } else {
        grid.innerHTML = html;
    }

    // Tour cards render as <a href target="_blank">: navigation happens via
    // the anchor's native click, and tracking.js's delegated handler fires
    // booking_click. No JS click handler needed here.

    displayedCount = append
        ? displayedCount + toursToShow.length
        : toursToShow.length;
    
    // Show/hide load more button
    const loadMoreBtn = document.getElementById('load-more');
    if (loadMoreBtn) {
        loadMoreBtn.style.display = displayedCount >= filteredTours.length ? 'none' : 'block';
    }
}

// Load more tours
function loadMoreTours() {
    trackLoadMoreClick();
    renderTours(true);
}

// Update results count
function updateResultsCount() {
    const countEl = document.getElementById('results-count');
    if (countEl) {
        countEl.textContent = `Showing ${Math.min(displayedCount, filteredTours.length)} of ${filteredTours.length} adventures`;
    }
}

// Filter tours
function filterTours() {
    const islandFilter = document.getElementById('island-filter')?.value?.toLowerCase() || '';
    const activityFilter = document.getElementById('activity-filter')?.value || '';
    const sortFilter = document.getElementById('sort-filter')?.value || 'quality';
    const searchInput = document.getElementById('search-input')?.value?.toLowerCase() || '';
    
    // Track filter usage
    if (islandFilter) trackFilterChange('island', islandFilter);
    if (activityFilter) trackFilterChange('activity', activityFilter);
    if (searchInput) trackSearchUsed(searchInput);
    
    filteredTours = toursData.filter(tour => {
        // Island filter
        if (islandFilter && tour.island?.toLowerCase() !== islandFilter) {
            return false;
        }
        
        // Activity filter
        if (activityFilter && !tour.tags?.includes(activityFilter)) {
            return false;
        }
        
        // Search filter
        if (searchInput) {
            const searchFields = [
                tour.name,
                tour.company,
                tour.location,
                tour.description,
                ...(tour.tags || [])
            ].join(' ').toLowerCase();
            
            if (!searchFields.includes(searchInput)) {
                return false;
            }
        }
        
        return true;
    });
    
    // Sort
    if (sortFilter === 'quality') {
        filteredTours.sort((a, b) => (b.qualityScore || 0) - (a.qualityScore || 0));
    } else if (sortFilter === 'name') {
        filteredTours.sort((a, b) => a.name.localeCompare(b.name));
    }
    
    displayedCount = 0;
    renderTours();
    updateResultsCount();
}

// Shuffle visible tours
function shuffleTours() {
    filteredTours = shuffleArray(filteredTours);
    displayedCount = 0;
    renderTours();
}

// Clear all filters
function clearAllFilters() {
    const islandFilter = document.getElementById('island-filter');
    const activityFilter = document.getElementById('activity-filter');
    const sortFilter = document.getElementById('sort-filter');
    const searchInput = document.getElementById('search-input');
    
    if (islandFilter) islandFilter.value = '';
    if (activityFilter) activityFilter.value = '';
    if (sortFilter) sortFilter.value = 'quality';
    if (searchInput) searchInput.value = '';
    
    filterTours();
}

// Quick filter from tags/buttons
function quickFilter(term) {
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.value = term;
    }
    filterTours();
    
    // Scroll to tours section
    document.getElementById('tours-section')?.scrollIntoView({ behavior: 'smooth' });
}

// Hero search
function executeHeroSearch() {
    const heroSearch = document.getElementById('hero-search');
    if (heroSearch?.value) {
        quickFilter(heroSearch.value);
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    loadTours();
    
    // Filter change listeners
    document.getElementById('island-filter')?.addEventListener('change', () => {
        const val = document.getElementById('island-filter').value;
        if (val) trackFilterChange('island', val);
        filterTours();
    });
    document.getElementById('activity-filter')?.addEventListener('change', () => {
        const val = document.getElementById('activity-filter').value;
        if (val) trackFilterChange('activity', val);
        filterTours();
    });
    document.getElementById('sort-filter')?.addEventListener('change', () => {
        const val = document.getElementById('sort-filter').value;
        if (val) trackFilterChange('sort', val);
        filterTours();
    });
    
    // Search input with debounce
    let searchTimeout;
    document.getElementById('search-input')?.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(filterTours, 300);
    });
    
    // Hero search enter key
    document.getElementById('hero-search')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            executeHeroSearch();
        }
    });
});

// Mobile menu toggle
document.querySelector('.mobile-menu-btn')?.addEventListener('click', function() {
    document.querySelector('.nav-mobile')?.classList.toggle('active');
    this.classList.toggle('active');
});

// FOMO notifications - DISABLED
// These fake notifications were removed to improve user trust
// Users should see real booking confirmations only

// Weather widget
async function loadWeather() {
    const CACHE_KEY = 'wx-cache-wams';
    const TTL_MS = 10 * 60 * 1000;
    const weatherEl = document.getElementById('header-weather');
    if (!weatherEl) return;
    try {
        const cached = JSON.parse(sessionStorage.getItem(CACHE_KEY) || 'null');
        if (cached && Date.now() - cached.ts < TTL_MS) {
            weatherEl.querySelector('.weather-temp').textContent = `${cached.temp}°C`;
            return;
        }
        const response = await fetch('https://api.open-meteo.com/v1/forecast?latitude=52.37&longitude=4.90&current_weather=true&temperature_unit=celsius');
        const data = await response.json();
        const temp = Math.round(data.current_weather.temperature);
        weatherEl.querySelector('.weather-temp').textContent = `${temp}°C`;
        sessionStorage.setItem(CACHE_KEY, JSON.stringify({ temp, ts: Date.now() }));
    } catch (error) {
        // Silent fail
    }
}

loadWeather();

// Promo Banner
function closeBanner() {
    const banner = document.getElementById('promo-banner');
    if (banner) {
        banner.classList.add('hidden');
        sessionStorage.setItem('promoBannerClosed', 'true');
    }
}

// Check if banner was closed this session
if (sessionStorage.getItem('promoBannerClosed') === 'true') {
    document.addEventListener('DOMContentLoaded', () => {
        const banner = document.getElementById('promo-banner');
        if (banner) banner.classList.add('hidden');
    });
}

// ===== STICKY MOBILE CTA BAR =====
document.addEventListener('DOMContentLoaded', () => {
    const stickyBar = document.getElementById('sticky-cta-bar');
    if (!stickyBar) return;
    
    const heroSection = document.querySelector('.hero') || document.querySelector('.tours-section');
    let heroScrolled = false;
    
    window.addEventListener('scroll', () => {
        const scrolled = window.scrollY > (heroSection?.offsetHeight || 300);
        
        if (scrolled && !heroScrolled) {
            stickyBar.classList.add('visible');
            heroScrolled = true;
        } else if (!scrolled && heroScrolled) {
            stickyBar.classList.remove('visible');
            heroScrolled = false;
        }
    });
    
    const ctaButton = stickyBar.querySelector('button');
    if (ctaButton) {
        ctaButton.addEventListener('click', () => {
            const toursGrid = document.getElementById('tours-grid');
            if (toursGrid) {
                toursGrid.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    }
});
