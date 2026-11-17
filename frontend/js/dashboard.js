const API_BASE = "http://127.0.0.1:8000";

const ENTITIES = ["LOG", "MFG", "RET"];
const TARGETS = ["Revenue", "CostOfSales", "SupplierInvoices"];

let analyticsCache = {};
let forecastCache = {};
let forecastChart = null;

const entitySelect = document.getElementById("entitySelect");
const forecastTargetSelect = document.getElementById("forecastTargetSelect");

function formatCurrency(value) {
    if (value == null || !Number.isFinite(Number(value))) return "—";

    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0
    }).format(value);
}

async function apiGet(path) {
    const response = await fetch(`${API_BASE}${path}`);

    if (!response.ok) {
        throw new Error(`${path}: HTTP ${response.status}`);
    }

    return response.json();
}

async function loadDashboardData(entity) {
    const [analytics, ...forecasts] = await Promise.all([
        apiGet(`/analytics/${entity}`),
        ...TARGETS.map(target =>
            apiGet(`/forecast/${entity}/${target}`)
        )
    ]);

    analyticsCache[entity] = analytics;
    forecastCache[entity] = {};

    TARGETS.forEach((target, index) => {
        forecastCache[entity][target] = forecasts[index];
    });
}

function updateKPIs(entity) {
    const analytics = analyticsCache[entity];
    const forecast = forecastCache[entity]?.Revenue;

    if (!analytics) return;

    const kpis = analytics.kpis;
    const nextForecast = forecast?.forecast?.[0];

    document.getElementById("revenueValue").textContent =
        formatCurrency(kpis.revenue);

    document.getElementById("costValue").textContent =
        formatCurrency(kpis.cost_of_sales);

    document.getElementById("supplierValue").textContent =
        formatCurrency(kpis.supplier_invoices);

    document.getElementById("forecastValue").textContent =
        nextForecast
            ? formatCurrency(nextForecast.predicted_value)
            : "—";
}

function updateChart(entity) {
    const analytics = analyticsCache[entity];
    const target = forecastTargetSelect.value;

    const metricConfig = {
        Revenue: {
            key: "revenue",
            label: "Revenue"
        },
        CostOfSales: {
            key: "cost_of_sales",
            label: "Cost of Sales"
        },
        SupplierInvoices: {
            key: "supplier_invoices",
            label: "Supplier Invoices"
        }
    };

    const metric = metricConfig[target];
    const forecast = forecastCache[entity]?.[target];

    if (!analytics || !metric) return;

    const history = analytics.history;
    const forecastPoint = forecast?.forecast?.[0];

    const labels = history.map(row => row.period);
    const actualValues = history.map(row => row[metric.key]);

    if (forecastPoint) {
        labels.push(forecastPoint.period);
    }

    const historicalDataset = [
        ...actualValues,
        ...(forecastPoint ? [null] : [])
    ];

    const forecastDataset = [
        ...Array(Math.max(0, history.length - 1)).fill(null),
        history[history.length - 1][metric.key],
        ...(forecastPoint ? [forecastPoint.predicted_value] : [])
    ];

    if (forecastChart) forecastChart.destroy();

    forecastChart = new Chart(
        document.getElementById("forecastChart"),
        {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        label: `Historical ${metric.label}`,
                        data: historicalDataset,
                        borderColor: "#203f60",
                        backgroundColor: "rgba(32,63,96,0.08)",
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true,
                        pointRadius: 3
                    },
                    {
                        label: `${metric.label} Forecast`,
                        data: forecastDataset,
                        borderColor: "#d9a441",
                        backgroundColor: "#d9a441",
                        borderWidth: 2,
                        borderDash: [6, 4],
                        tension: 0.2,
                        pointRadius: 4,
                        spanGaps: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: "index"
                },
                plugins: {
                    legend: {
                        position: "bottom"
                    },
                    tooltip: {
                        callbacks: {
                            label: context =>
                                `${context.dataset.label}: ${formatCurrency(context.raw)}`
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: value =>
                                "$" + Number(value).toLocaleString("en-US")
                        },
                        grid: {
                            color: "#edf0f3"
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        }
    );
}
function updateInsights(entity) {
    const analytics = analyticsCache[entity];
    const target = forecastTargetSelect.value;
    const forecast = forecastCache[entity]?.[target];

    if (!analytics) return;

    const kpis = analytics.kpis;
    const point = forecast?.forecast?.[0];

    const metricLabels = {
        Revenue: "Revenue",
        CostOfSales: "Cost of Sales",
        SupplierInvoices: "Supplier Invoices"
    };

    document.getElementById("insightsContent").innerHTML = `
        <div class="insight-placeholder">
            <strong>Gross profit</strong><br>
            ${formatCurrency(kpis.gross_profit)}
        </div>
        <div class="insight-placeholder">
            <strong>Gross margin</strong><br>
            ${Number(kpis.gross_margin_pct).toFixed(2)}%
        </div>
        <div class="insight-placeholder">
            <strong>${metricLabels[target]} forecasting model</strong><br>
            ${forecast?.model || "Unavailable"}
        </div>
        <div class="insight-placeholder">
            <strong>Forecast period</strong><br>
            ${point?.period || "Unavailable"}
        </div>
        <div class="insight-placeholder">
            <strong>Predicted ${metricLabels[target]}</strong><br>
            ${point ? formatCurrency(point.predicted_value) : "Unavailable"}
        </div>
    `;
}
function updateEntityTable() {
    const tbody = document.getElementById("entityTable");

    tbody.innerHTML = ENTITIES.map(entity => {
        const analytics = analyticsCache[entity];

        if (!analytics) {
            return `<tr><td>${entity}</td><td colspan="3">Unavailable</td></tr>`;
        }

        const kpis = analytics.kpis;

        return `
            <tr>
                <td><strong>${entity}</strong></td>
                <td>${formatCurrency(kpis.revenue)}</td>
                <td>${formatCurrency(kpis.cost_of_sales)}</td>
                <td>${formatCurrency(kpis.supplier_invoices)}</td>
            </tr>
        `;
    }).join("");
}

function updateSelectedEntity() {
    const entity = entitySelect.value;

    updateKPIs(entity);
    updateChart(entity);
    updateInsights(entity);
}

async function loadDashboard() {
    const tbody = document.getElementById("entityTable");

    tbody.innerHTML =
        `<tr><td colspan="4">Loading financial data...</td></tr>`;

    try {
        const health = await apiGet("/health");

        if (health.status !== "healthy") {
            throw new Error("Backend is not healthy.");
        }

        const results = await Promise.allSettled(
            ENTITIES.map(entity => loadDashboardData(entity))
        );

        const failures = results.filter(
            result => result.status === "rejected"
        );

        updateEntityTable();
        updateSelectedEntity();

        if (failures.length) {
            console.error("Entity loading failures:", failures);

            document.getElementById("insightsContent").insertAdjacentHTML(
                "afterbegin",
                `<div class="insight-placeholder">
                    Some entity data could not be loaded.
                </div>`
            );
        }

    } catch (error) {
        console.error("Dashboard error:", error);

        tbody.innerHTML =
            `<tr><td colspan="4">Unable to connect to LedgerLens API.</td></tr>`;

        document.getElementById("insightsContent").innerHTML =
            `<div class="insight-placeholder">
                Backend unavailable. Start FastAPI and retry.
            </div>`;
    }
}

entitySelect.addEventListener("change", updateSelectedEntity);

forecastTargetSelect.addEventListener("change", () => {
    const entity = entitySelect.value;
    updateChart(entity);
    updateInsights(entity);
});


loadDashboard();
