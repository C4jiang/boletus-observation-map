const RECORDS_URL = "data/boletus_edulis_laji_2009_50m_records.json";
const GRID_URL = "data/boletus_edulis_laji_2009_50m_etrs_10km_grid.geojson";
const FINLAND_VIEW = [[59.2, 19.0], [70.3, 32.0]];

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
const gridLayer = L.geoJSON(null, { style: gridStyle, onEachFeature: bindCell });
gridLayer.addTo(map);

let records = [];
let gridFeatures = [];

function colorForCount(count) {
  if (count >= 10) return "#0c513d";
  if (count >= 5) return "#167256";
  if (count >= 2) return "#4d9775";
  return "#9bcaae";
}

function gridStyle(feature) {
  const count = feature.properties.visible_count ?? 0;
  return {
    color: "#0c513d",
    weight: 1,
    opacity: 0.8,
    fillColor: colorForCount(count),
    fillOpacity: count ? 0.72 : 0,
  };
}

function popup(properties) {
  const verifiedNote = properties.verified_count ? `${properties.verified_count} community or expert verified` : "No verified records in this filter";
  return `<h2 class="popup-title">${properties.grid_id}</h2><dl class="popup-grid">
    <dt>Cell size</dt><dd>10 km × 10 km</dd>
    <dt>Observations</dt><dd>${properties.visible_count}</dd>
    <dt>Reliability</dt><dd>${verifiedNote}</dd>
    <dt>Years shown</dt><dd>${properties.visible_year_min}-${properties.visible_year_max}</dd>
    <dt>EPSG:3067 N</dt><dd>${properties.northing_min}-${properties.northing_min + 10000}</dd>
    <dt>EPSG:3067 E</dt><dd>${properties.easting_min}-${properties.easting_min + 10000}</dd>
  </dl>`;
}

function bindCell(feature, layer) {
  layer.bindPopup(() => popup(feature.properties));
  layer.on({
    mouseover: () => layer.setStyle({ weight: 2.2, fillOpacity: 0.9 }),
    mouseout: () => gridLayer.resetStyle(layer),
  });
}

function activeRecords() {
  const min = Number(yearMin.value);
  const max = Number(yearMax.value);
  return records.filter((record) => record.year >= min && record.year <= max);
}

function render() {
  if (Number(yearMin.value) > Number(yearMax.value)) {
    [yearMin.value, yearMax.value] = [yearMax.value, yearMin.value];
  }
  yearMinLabel.textContent = yearMin.value;
  yearMaxLabel.textContent = yearMax.value;

  const selected = activeRecords();
  const byCell = new Map();
  selected.forEach((record) => {
    if (!byCell.has(record.grid_id)) byCell.set(record.grid_id, []);
    byCell.get(record.grid_id).push(record);
  });

  const visibleCells = gridFeatures
    .filter((feature) => byCell.has(feature.properties.grid_id))
    .map((feature) => {
      const cellRecords = byCell.get(feature.properties.grid_id);
      return {
        ...feature,
        properties: {
          ...feature.properties,
          visible_count: cellRecords.length,
          verified_count: cellRecords.filter((record) => ["COMMUNITY_VERIFIED", "EXPERT_VERIFIED"].includes(record.reliability)).length,
          visible_year_min: Math.min(...cellRecords.map((record) => record.year)),
          visible_year_max: Math.max(...cellRecords.map((record) => record.year)),
        },
      };
    });

  gridLayer.clearLayers();
  gridLayer.addData({ type: "FeatureCollection", features: visibleCells });
  visibleCount.textContent = selected.length.toLocaleString();
  status.textContent = visibleCells.length
    ? `${visibleCells.length} ETRS-TM35FIN 10 km cells contain matching observations.`
    : "No observations match the current year range.";
}

function fitVisible() {
  const bounds = gridLayer.getBounds();
  if (bounds.isValid()) map.fitBounds(bounds, { padding: [28, 28], maxZoom: 8 });
}

async function load() {
  try {
    const [recordsResponse, gridResponse] = await Promise.all([fetch(RECORDS_URL), fetch(GRID_URL)]);
    if (!recordsResponse.ok || !gridResponse.ok) throw new Error("Could not retrieve the map dataset");
    records = await recordsResponse.json();
    const grid = await gridResponse.json();
    gridFeatures = grid.features;
    render();
    status.textContent = "970 high-precision Laji.fi observations, mapped as Finnish national-grid cells.";
  } catch (error) {
    status.textContent = `Could not load observation data: ${error.message}`;
    status.classList.add("is-error");
  }
}

yearMin.addEventListener("input", render);
yearMax.addEventListener("input", render);
document.querySelector("#fit-map").addEventListener("click", fitVisible);
document.querySelector("#reset-filters").addEventListener("click", () => {
  yearMin.value = yearMin.min;
  yearMax.value = yearMax.max;
  render();
  map.fitBounds(FINLAND_VIEW);
});

load();
