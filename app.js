const DATA_URL = "data/boletus_edulis_fi_2009_high_precision.geojson";
const FINLAND_VIEW = [[58.6, 19.0], [70.3, 32.0]];
const map = L.map("map", { zoomControl: false, preferCanvas: true });
L.control.zoom({ position: "topright" }).addTo(map);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18,
  attribution: "© OpenStreetMap contributors",
}).addTo(map);
map.fitBounds(FINLAND_VIEW);

const yearMin = document.querySelector("#year-min");
const yearMax = document.querySelector("#year-max");
const yearMinLabel = document.querySelector("#year-min-label");
const yearMaxLabel = document.querySelector("#year-max-label");
const visibleCount = document.querySelector("#visible-count");
const status = document.querySelector("#map-status");
const countryInputs = [...document.querySelectorAll('input[name="country"]')];
const clusters = L.markerClusterGroup({ chunkedLoading: true, showCoverageOnHover: false, maxClusterRadius: 48 });
map.addLayer(clusters);
let observations = [];

function selectedCountries() {
  return new Set(countryInputs.filter((input) => input.checked).map((input) => input.value));
}

function popup(feature) {
  const p = feature.properties;
  const locality = p.locality || p.stateProvince || "Not reported";
  return `<h2 class="popup-title"><i>Boletus edulis</i></h2><dl class="popup-grid">
    <dt>Date</dt><dd>${p.eventDate}</dd>
    <dt>Place</dt><dd>${locality}</dd>
    <dt>Country</dt><dd>${p.countryCode}</dd>
    <dt>Accuracy</dt><dd>${p.coordinateUncertaintyInMeters} m</dd>
    <dt>Record type</dt><dd>${p.basisOfRecord.replaceAll("_", " ")}</dd>
    <dt>GBIF ID</dt><dd>${p.gbifID}</dd>
  </dl>`;
}

function activeFeatures() {
  const min = Number(yearMin.value);
  const max = Number(yearMax.value);
  const countries = selectedCountries();
  return observations.filter((feature) => feature.properties.year >= min && feature.properties.year <= max && countries.has(feature.properties.countryCode));
}

function render() {
  if (Number(yearMin.value) > Number(yearMax.value)) {
    [yearMin.value, yearMax.value] = [yearMax.value, yearMin.value];
  }
  yearMinLabel.textContent = yearMin.value;
  yearMaxLabel.textContent = yearMax.value;
  const selected = activeFeatures();
  clusters.clearLayers();
  const markers = selected.map((feature) => {
    const [lng, lat] = feature.geometry.coordinates;
    return L.circleMarker([lat, lng], { radius: 5, color: "#0c513d", weight: 1.25, fillColor: "#167256", fillOpacity: 0.75 })
      .bindPopup(popup(feature));
  });
  clusters.addLayers(markers);
  visibleCount.textContent = selected.length.toLocaleString();
  status.textContent = selected.length ? "Select a point for its observation details." : "No observations match the current filters.";
}

function fitVisible() {
  const selected = activeFeatures();
  if (!selected.length) return;
  const bounds = L.latLngBounds(selected.map((f) => [f.geometry.coordinates[1], f.geometry.coordinates[0]]));
  map.fitBounds(bounds, { padding: [28, 28], maxZoom: 10 });
}

async function load() {
  try {
    const response = await fetch(DATA_URL);
    if (!response.ok) throw new Error(`Data request failed (${response.status})`);
    const geojson = await response.json();
    observations = geojson.features;
    render();
    status.textContent = "Showing all filtered observations. Select a point for details.";
  } catch (error) {
    status.textContent = `Could not load observation data: ${error.message}`;
    status.classList.add("is-error");
  }
}

yearMin.addEventListener("input", render);
yearMax.addEventListener("input", render);
countryInputs.forEach((input) => input.addEventListener("change", render));
document.querySelector("#fit-map").addEventListener("click", fitVisible);
document.querySelector("#reset-filters").addEventListener("click", () => {
  yearMin.value = yearMin.min;
  yearMax.value = yearMax.max;
  countryInputs.forEach((input) => { input.checked = true; });
  render();
  map.fitBounds(FINLAND_VIEW);
});

load();
