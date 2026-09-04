const DATA_URL = "data/points.csv";
const EDA_URL = "data/eda_summary.json";
const PAGE_SIZE = 14;

const PHOTO_BY_LOCATION = {
  Lochnagar: {
    src: "photos/lochnagar.jpg",
    credit: "Photograph: Annette Boerlage & Leigh Woltman",
  },
  "Cairngorms Other": {
    src: "photos/cairngorms_other.jpg",
    credit: "Photograph: Matt Trevers",
  },
  "Cairngorms Western Massif": {
    src: "photos/cairngorms_western_massif.jpg",
    credit: "Photograph: Craig Aitchison",
  },
  "Ben Macdui": {
    src: "photos/ben_macdui.jpg",
    credit: "Photograph: Peter Hudson",
  },
  "Ben Nevis": {
    src: "photos/ben_nevis.jpg",
    credit: "Photograph: Rise and Summit",
  },
  "Beinn a' Bhuird & Ben Avon": {
    src: "photos/beinn_a_bhuird_ben_avon.jpg",
    credit: "Photograph: SAIS",
  },
  "Ben Lawers": {
    src: "photos/ben_lawers.JPG",
    credit: "Photograph: Love of Scotland",
  },
  "Central Highlands": {
    src: "photos/central_highlands.jpg",
    credit: "Photograph: Steve Fallon",
  },
  "Ben Lui": {
    src: "photos/ben_lui.jpg",
    credit: "Photograph: Jim Dowley",
  },
  "North West Highlands": {
    src: "photos/north_west_highlands.JPG",
    credit: "Photograph: Gary Hodgson",
  },
  "Glenshee Area": {
    src: "photos/glenshee_area.jpg",
    credit: "Photograph: ski-glenshee",
  },
  "Southern Highlands": {
    src: "photos/southern_highlands.jpg",
    credit: "Photograph: William Starkey",
  },
  "Eastern Highlands": {
    src: "photos/Eastern_highlands.jpg",
    credit: "Photograph: Ian Cameron",
  },
};

const state = {
  rows: [],
  filteredRows: [],
  summary: null,
  visibleCount: PAGE_SIZE,
  map: null,
  markerLayer: null,
  markers: new Map(),
  fittedOnce: false,
  charts: [],
};

const els = {};

document.addEventListener("DOMContentLoaded", initialise);

async function initialise() {
  cacheElements();
  bindHeader();
  bindFilters();

  try {
    if (!window.Papa) throw new Error("The CSV parser did not load.");
    if (!window.L) throw new Error("The map library did not load.");

    const [summary, rows] = await Promise.all([
      fetch(EDA_URL).then(checkResponse).then((response) => response.json()),
      loadCsv(DATA_URL),
    ]);

    state.summary = summary;
    state.rows = rows.map(normaliseRow);
    configureYearInputs(summary.summary);
    populateRegionFilter(summary.locations);
    renderSummary(summary);
    initialiseMap();
    initialiseCharts(summary);
    applyFilters();
    els.explorer.setAttribute("aria-busy", "false");
  } catch (error) {
    console.error(error);
    renderLoadError(error);
    els.explorer.setAttribute("aria-busy", "false");
  }
}

function cacheElements() {
  els.header = document.querySelector("[data-header]");
  els.explorer = document.querySelector("[data-explorer]");
  els.search = document.getElementById("searchInput");
  els.region = document.getElementById("regionFilter");
  els.yearFrom = document.getElementById("yearFrom");
  els.yearTo = document.getElementById("yearTo");
  els.reset = document.getElementById("resetFilters");
  els.resultsKicker = document.getElementById("resultsKicker");
  els.resultsTitle = document.getElementById("resultsTitle");
  els.resultsCount = document.getElementById("resultsCount");
  els.resultsList = document.getElementById("resultsList");
  els.loadMore = document.getElementById("loadMore");
  els.mapCount = document.getElementById("mapCount");
  els.locationPhoto = document.getElementById("locationPhoto");
  els.locationPhotoImage = document.getElementById("locationPhotoImage");
  els.locationPhotoCredit = document.getElementById("locationPhotoCredit");
}

function bindHeader() {
  const updateHeader = () => {
    els.header.classList.toggle("is-scrolled", window.scrollY > 160);
  };
  window.addEventListener("scroll", updateHeader, { passive: true });
  updateHeader();
}

function bindFilters() {
  const debouncedApply = debounce(applyFilters, 120);
  els.search.addEventListener("input", debouncedApply);
  els.region.addEventListener("change", applyFilters);
  els.yearFrom.addEventListener("change", applyFilters);
  els.yearTo.addEventListener("change", applyFilters);
  els.reset.addEventListener("click", resetFilters);
  els.loadMore.addEventListener("click", () => {
    state.visibleCount += PAGE_SIZE;
    renderResults(false);
  });
}

function checkResponse(response) {
  if (!response.ok) throw new Error(`Could not load ${response.url}`);
  return response;
}

function loadCsv(url) {
  return new Promise((resolve, reject) => {
    window.Papa.parse(url, {
      download: true,
      header: true,
      skipEmptyLines: true,
      transformHeader: (header) => String(header || "").trim().replace(/^\uFEFF/, ""),
      complete: (results) => {
        if (results.errors?.length && !results.data?.length) {
          reject(new Error(results.errors[0].message));
          return;
        }
        resolve(results.data || []);
      },
      error: reject,
    });
  });
}

function normaliseRow(row, index) {
  const year = finiteNumber(row.year);
  const month = finiteNumber(row.month);
  const day = finiteNumber(row.day);
  const score = finiteNumber(row.score);
  return {
    id: index,
    text: clean(row.text),
    entity: clean(row.entity),
    score,
    date: clean(row.date),
    annotatorComment: clean(row.annotator_comment),
    generalLocation: clean(row.general_location) || "Unknown region",
    specificLocation: clean(row.specific_location),
    year,
    season: clean(row.season),
    month,
    day,
    coordinates: parseCoordinates(row.Coordinates),
  };
}

function clean(value) {
  if (value === null || value === undefined) return "";
  const stringValue = String(value).trim();
  return stringValue.toLowerCase() === "nan" ? "" : stringValue;
}

function finiteNumber(value) {
  if (value === "" || value === null || value === undefined) return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function parseCoordinates(value) {
  const match = clean(value).match(/\(\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)\s*\)/);
  if (!match) return null;
  const latitude = Number(match[1]);
  const longitude = Number(match[2]);
  return Number.isFinite(latitude) && Number.isFinite(longitude)
    ? [latitude, longitude]
    : null;
}

function configureYearInputs(summary) {
  const { earliest_year: earliest, latest_year: latest } = summary;
  for (const input of [els.yearFrom, els.yearTo]) {
    input.min = String(earliest);
    input.max = String(latest);
  }
  els.yearFrom.value = String(earliest);
  els.yearTo.value = String(latest);
}

function populateRegionFilter(locations) {
  for (const location of locations) {
    const option = document.createElement("option");
    option.value = location.label;
    option.textContent = `${location.label} (${location.count.toLocaleString()})`;
    els.region.append(option);
  }
}

function renderSummary(summary) {
  for (const [key, value] of Object.entries(summary.summary)) {
    document.querySelectorAll(`[data-stat="${key}"]`).forEach((element) => {
      const isYear = key === "earliest_year" || key === "latest_year";
      element.textContent = typeof value === "number" && !isYear ? value.toLocaleString() : String(value);
    });
  }

  const monthPeak = [...summary.months].sort((a, b) => b.count - a.count)[0];
  document.querySelectorAll("[data-month-peak]").forEach((element) => {
    element.textContent = monthPeak.count.toLocaleString();
  });

  renderTerms(summary.top_entities);
  renderQuality(summary.completeness);
}

function initialiseMap() {
  state.map = window.L.map("map", {
    zoomControl: true,
    scrollWheelZoom: false,
    minZoom: 5,
  }).setView([56.95, -4.25], 7);

  window.L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    },
  ).addTo(state.map);

  state.markerLayer = window.L.layerGroup().addTo(state.map);
}

function applyFilters() {
  if (!state.rows.length) return;

  const query = els.search.value.trim().toLowerCase();
  const region = els.region.value;
  let yearFrom = finiteNumber(els.yearFrom.value);
  let yearTo = finiteNumber(els.yearTo.value);
  const earliest = state.summary.summary.earliest_year;
  const latest = state.summary.summary.latest_year;

  yearFrom = yearFrom ?? earliest;
  yearTo = yearTo ?? latest;
  if (yearFrom > yearTo) [yearFrom, yearTo] = [yearTo, yearFrom];

  const defaultYearRange = yearFrom === earliest && yearTo === latest;
  state.filteredRows = state.rows.filter((row) => {
    if (region && row.generalLocation !== region) return false;
    if (!defaultYearRange && (row.year === null || row.year < yearFrom || row.year > yearTo)) return false;
    if (query && !searchableText(row).includes(query)) return false;
    return true;
  });

  state.filteredRows.sort(compareRows);
  state.visibleCount = PAGE_SIZE;
  renderResults(true);
  renderMarkers(region);
  renderLocationPhoto(region);
}

function searchableText(row) {
  return [
    row.text,
    row.entity,
    row.date,
    row.generalLocation,
    row.specificLocation,
    row.annotatorComment,
  ].join(" ").toLowerCase();
}

function compareRows(a, b) {
  const aYear = a.year ?? Number.POSITIVE_INFINITY;
  const bYear = b.year ?? Number.POSITIVE_INFINITY;
  if (aYear !== bYear) return aYear - bYear;
  const aMonth = validDatePart(a.month, 13);
  const bMonth = validDatePart(b.month, 13);
  if (aMonth !== bMonth) return aMonth - bMonth;
  const aDay = validDatePart(a.day, 32);
  const bDay = validDatePart(b.day, 32);
  return aDay - bDay;
}

function validDatePart(value, fallback) {
  return Number.isFinite(value) && value >= 1 ? value : fallback;
}

function renderResults(resetScroll = true) {
  const rows = state.filteredRows;
  const region = els.region.value;
  const query = els.search.value.trim();

  els.resultsKicker.textContent = query ? `Matches for “${truncate(query, 32)}”` : "Archive results";
  els.resultsTitle.textContent = region || "All observations";
  els.resultsCount.textContent = rows.length.toLocaleString();

  if (!rows.length) {
    els.resultsList.replaceChildren(emptyState());
    els.loadMore.hidden = true;
    els.mapCount.textContent = "No mapped observations";
    return;
  }

  const fragment = document.createDocumentFragment();
  for (const row of rows.slice(0, state.visibleCount)) {
    fragment.append(observationCard(row));
  }
  els.resultsList.replaceChildren(fragment);
  els.loadMore.hidden = state.visibleCount >= rows.length;
  els.loadMore.textContent = `Show more · ${Math.min(PAGE_SIZE, rows.length - state.visibleCount).toLocaleString()} next`;

  if (resetScroll) els.resultsList.scrollTop = 0;
}

function observationCard(row) {
  const article = document.createElement("article");
  article.className = "observation";

  const meta = document.createElement("div");
  meta.className = "observation-meta";

  const date = document.createElement("span");
  date.className = "observation-date";
  date.textContent = row.date || (row.year ? String(row.year) : "Date unavailable");
  meta.append(date);

  const place = document.createElement("span");
  place.textContent = row.specificLocation || row.generalLocation;
  meta.append(place);

  const quote = document.createElement("p");
  quote.className = "observation-text";
  quote.textContent = row.text || "Quotation unavailable.";

  article.append(meta, quote);

  const tags = document.createElement("div");
  tags.className = "observation-tags";
  if (row.entity) tags.append(tag(row.entity));
  if (row.score !== null) tags.append(tag(`snow score ${formatNumber(row.score)}`, true));
  if (row.annotatorComment) {
    const note = tag("annotator note");
    note.title = row.annotatorComment;
    note.setAttribute("aria-label", `Annotator note: ${row.annotatorComment}`);
    tags.append(note);
  }
  if (tags.childElementCount) article.append(tags);

  return article;
}

function tag(text, score = false) {
  const element = document.createElement("span");
  element.className = `observation-tag${score ? " score-tag" : ""}`;
  element.textContent = text;
  return element;
}

function emptyState() {
  const wrapper = document.createElement("div");
  wrapper.className = "empty-state";
  const heading = document.createElement("h3");
  heading.textContent = "No observations found";
  const text = document.createElement("p");
  text.textContent = "Try a wider year range, another region, or a more general search term.";
  wrapper.append(heading, text);
  return wrapper;
}

function renderMarkers(selectedRegion) {
  const groups = groupRowsByCoordinate(state.filteredRows);
  state.markerLayer.clearLayers();
  state.markers.clear();
  const bounds = [];

  for (const group of groups) {
    const selected = selectedRegion && group.region === selectedRegion;
    const radius = Math.min(20, 6 + Math.sqrt(group.rows.length) * 0.62);
    const marker = window.L.circleMarker(group.coordinates, {
      radius: selected ? radius + 3 : radius,
      weight: selected ? 4 : 2,
      color: selected ? "#071e23" : "#ffffff",
      fillColor: selected ? "#ff5d31" : "#ff7148",
      fillOpacity: selected ? 0.96 : 0.82,
      opacity: 0.96,
    });

    marker.bindTooltip(`${group.region} · ${group.rows.length.toLocaleString()}`, {
      direction: "top",
      className: "snow-tooltip",
      offset: [0, -8],
    });
    marker.on("click", () => selectRegion(group.region));
    marker.addTo(state.markerLayer);
    state.markers.set(group.region, marker);
    bounds.push(group.coordinates);
  }

  const mappedCount = groups.reduce((total, group) => total + group.rows.length, 0);
  els.mapCount.textContent = `${mappedCount.toLocaleString()} mapped · ${groups.length} ${groups.length === 1 ? "point" : "points"}`;

  if (!bounds.length) return;
  if (selectedRegion && state.markers.has(selectedRegion)) {
    state.map.flyTo(state.markers.get(selectedRegion).getLatLng(), 8, { duration: 0.65 });
  } else if (!state.fittedOnce) {
    state.map.fitBounds(bounds, { padding: [54, 54], maxZoom: 7 });
    state.fittedOnce = true;
  }
}

function groupRowsByCoordinate(rows) {
  const groups = new Map();
  for (const row of rows) {
    if (!row.coordinates) continue;
    const key = `${row.coordinates[0].toFixed(5)},${row.coordinates[1].toFixed(5)}`;
    if (!groups.has(key)) {
      groups.set(key, {
        coordinates: row.coordinates,
        region: row.generalLocation,
        rows: [],
      });
    }
    groups.get(key).rows.push(row);
  }
  return [...groups.values()];
}

function selectRegion(region) {
  els.region.value = region;
  applyFilters();
  document.querySelector(".results-panel").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderLocationPhoto(region) {
  const photo = PHOTO_BY_LOCATION[region];
  if (!photo) {
    els.locationPhoto.hidden = true;
    els.locationPhotoImage.removeAttribute("src");
    return;
  }

  els.locationPhotoImage.src = photo.src;
  els.locationPhotoImage.alt = `${region} in winter conditions`;
  els.locationPhotoCredit.textContent = photo.credit;
  els.locationPhoto.hidden = false;
}

function resetFilters() {
  els.search.value = "";
  els.region.value = "";
  els.yearFrom.value = String(state.summary.summary.earliest_year);
  els.yearTo.value = String(state.summary.summary.latest_year);
  state.fittedOnce = false;
  renderLocationPhoto("");
  applyFilters();
}

function initialiseCharts(summary) {
  if (!window.Chart) return;

  window.Chart.defaults.font.family = getComputedStyle(document.documentElement).getPropertyValue("--sans");
  window.Chart.defaults.color = "rgba(255,255,255,.58)";
  window.Chart.defaults.borderColor = "rgba(255,255,255,.11)";

  const sharedPlugins = {
    legend: { display: false },
    tooltip: {
      backgroundColor: "#e8f7fa",
      titleColor: "#081b20",
      bodyColor: "#081b20",
      padding: 12,
      cornerRadius: 2,
      displayColors: false,
      titleFont: { weight: "700" },
    },
  };

  state.charts.push(new window.Chart(document.getElementById("decadeChart"), {
    type: "bar",
    data: {
      datasets: [{
        data: summary.decades.map((item) => ({ x: item.decade, y: item.count })),
        parsing: false,
        backgroundColor: summary.decades.map((item) => item.decade >= 1890 && item.decade <= 1940 ? "#ff7148" : "#95cbd4"),
        borderRadius: 2,
        barThickness: 11,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: sharedPlugins,
      scales: {
        x: {
          type: "linear",
          min: 1600,
          max: 2020,
          grid: { display: false },
          ticks: {
            stepSize: 50,
            callback: (value) => value,
            maxRotation: 0,
          },
        },
        y: {
          beginAtZero: true,
          grid: { color: "rgba(255,255,255,.09)" },
          ticks: { precision: 0 },
        },
      },
    },
  }));

  state.charts.push(new window.Chart(document.getElementById("monthChart"), {
    type: "line",
    data: {
      labels: summary.months.map((item) => item.label),
      datasets: [{
        data: summary.months.map((item) => item.count),
        borderColor: "#ff7148",
        backgroundColor: "rgba(255,113,72,.15)",
        pointBackgroundColor: "#e8f7fa",
        pointBorderColor: "#081b20",
        pointRadius: 4,
        pointHoverRadius: 6,
        tension: 0.3,
        fill: true,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: sharedPlugins,
      scales: {
        x: { grid: { display: false } },
        y: { beginAtZero: true, grid: { color: "rgba(255,255,255,.09)" }, ticks: { precision: 0 } },
      },
    },
  }));

  const topLocations = summary.locations.slice(0, 10).reverse();
  state.charts.push(new window.Chart(document.getElementById("locationChart"), {
    type: "bar",
    data: {
      labels: topLocations.map((item) => item.label),
      datasets: [{
        data: topLocations.map((item) => item.count),
        backgroundColor: topLocations.map((_, index) => index >= 8 ? "#ff7148" : "#95cbd4"),
        borderRadius: 2,
        barPercentage: 0.72,
        categoryPercentage: 0.8,
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: sharedPlugins,
      scales: {
        x: { beginAtZero: true, grid: { color: "rgba(255,255,255,.09)" }, ticks: { precision: 0 } },
        y: { grid: { display: false }, ticks: { autoSkip: false, font: { size: 11 } } },
      },
    },
  }));

  state.charts.push(new window.Chart(document.getElementById("scoreChart"), {
    type: "bar",
    data: {
      labels: summary.scores.map((item) => item.label),
      datasets: [{
        data: summary.scores.map((item) => item.count),
        backgroundColor: summary.scores.map((item) => `rgba(149,203,212,${0.28 + item.score * 0.065})`),
        borderRadius: 2,
        barPercentage: 0.78,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: sharedPlugins,
      scales: {
        x: { grid: { display: false }, title: { display: true, text: "snow description score", color: "rgba(255,255,255,.42)" } },
        y: { beginAtZero: true, grid: { color: "rgba(255,255,255,.09)" }, ticks: { precision: 0 } },
      },
    },
  }));
}

function renderTerms(terms) {
  const container = document.getElementById("termList");
  const maxCount = Math.max(...terms.map((term) => term.count));
  for (const term of terms) {
    const item = document.createElement("span");
    item.className = "term-pill";
    item.style.setProperty("--term-alpha", String(0.055 + (term.count / maxCount) * 0.13));
    const label = document.createElement("span");
    label.textContent = term.label;
    const count = document.createElement("strong");
    count.textContent = term.count.toLocaleString();
    item.append(label, count);
    container.append(item);
  }
}

function renderQuality(items) {
  const container = document.getElementById("qualityBars");
  for (const item of items) {
    const row = document.createElement("div");
    row.className = "quality-row";
    const head = document.createElement("div");
    head.className = "quality-row-head";
    const label = document.createElement("span");
    label.textContent = item.label;
    const percent = document.createElement("span");
    percent.textContent = `${item.percent}% complete`;
    head.append(label, percent);
    const track = document.createElement("div");
    track.className = "quality-track";
    const fill = document.createElement("div");
    fill.className = "quality-fill";
    fill.style.width = `${item.percent}%`;
    track.append(fill);
    row.append(head, track);
    container.append(row);
  }
}

function renderLoadError(error) {
  const wrapper = document.createElement("div");
  wrapper.className = "error-state";
  const heading = document.createElement("h3");
  heading.textContent = "The archive could not be loaded";
  const text = document.createElement("p");
  text.textContent = "Run the site through a local web server rather than opening index.html directly, then refresh the page.";
  wrapper.append(heading, text);
  els.resultsList.replaceChildren(wrapper);
  els.resultsCount.textContent = "0";
  els.mapCount.textContent = "Data unavailable";
  console.error(error);
}

function formatNumber(number) {
  return Number.isInteger(number) ? String(number) : number.toFixed(1);
}

function truncate(value, length) {
  return value.length > length ? `${value.slice(0, length - 1)}…` : value;
}

function debounce(callback, wait) {
  let timeout;
  return (...args) => {
    window.clearTimeout(timeout);
    timeout = window.setTimeout(() => callback(...args), wait);
  };
}
