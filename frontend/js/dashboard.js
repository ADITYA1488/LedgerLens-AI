const API_BASE = "http://127.0.0.1:8000";

const ENTITIES = ["LOG", "MFG", "RET"];
const TARGETS = ["Revenue", "CostOfSales", "SupplierInvoices"];

let analyticsCache = {};
let forecastCache = {};
let forecastChart = null;

const actionCache = {};

function getActionState(entity, action) {
    return action.status || "open";
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    }[char]));
}

async function loadActionCenter(entity) {
    const container = document.getElementById("actionCenterContent");
    const counter = document.getElementById("actionCount");

    container.innerHTML = `
        <div class="insight-placeholder">Scanning financial signals...</div>
    `;

    try {
        const data = await apiGet(`/actions/${entity}`);
        actionCache[entity] = data;

        const actions = data.actions || [];
        const activeActions = actions.filter(action =>
    ["open", "in_progress"].includes(getActionState(entity, action))
);

        counter.textContent = `${activeActions.length} active`;

        if (!actions.length) {
            container.innerHTML = `
                <div class="action-empty">
                    <h4>All clear</h4>
                    <p>No financial risks detected for ${entity}.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = actions.map(action => {
            const status = getActionState(entity, action);
            const severity = String(action.severity || "low").toLowerCase();

            return `
                <article class="action-card ${severity} ${status !== "open" ? "resolved" : ""}">
                    <div class="action-card-top">
                        <span class="severity-badge ${severity}">
                            ${escapeHTML(severity.toUpperCase())}
                        </span>
                        <span class="action-status">${escapeHTML(status.toUpperCase())}</span>
                    </div>

                    <h4>${escapeHTML(action.title)}</h4>

                    <p class="action-trigger">
                        ${escapeHTML(action.trigger)}
                    </p>

                    <div class="action-financial-impact">
                        <span>${escapeHTML(action.financial_value_label || "Financial impact")}</span>
                        <strong>${formatCurrency(action.financial_value)}</strong>
                    </div>

                    <div class="action-recommendation">
                        <strong>Recommended action</strong>
                        <p>${escapeHTML(action.action)}</p>
                    </div>

                    <div class="action-automation">
                        <span>⚙</span>
                        ${escapeHTML(action.automation || "Action generated automatically")}
                    </div>

                    <div class="action-buttons">
    ${
        status === "open"
        ? `
            <button class="action-complete-btn"
                onclick="setLedgerLensActionStatus('${entity}', '${action.id}', 'in_progress')">
                Start Investigation
            </button>
        `
        : ""
    }

    ${
        ["open", "in_progress"].includes(status)
        ? `
            <button class="action-complete-btn"
                onclick="setLedgerLensActionStatus('${entity}', '${action.id}', 'completed')">
                Mark Complete
            </button>

            <button class="action-dismiss-btn"
                onclick="setLedgerLensActionStatus('${entity}', '${action.id}', 'dismissed')">
                Dismiss
            </button>
        `
        : `
            <button class="action-restore-btn"
                onclick="setLedgerLensActionStatus('${entity}', '${action.id}', 'open')">
                Reopen
            </button>
        `
    }
</div>
                </article>
            `;
        }).join("");

    } catch (error) {
        counter.textContent = "Unavailable";

        container.innerHTML = `
            <div class="action-error">
                <strong>Action Engine unavailable</strong>
                <p>${escapeHTML(error.message)}</p>
            </div>
        `;
    }
}

window.setLedgerLensActionStatus = async function(entity, actionId, status) {
    try {
        await apiPatch(`/actions/${encodeURIComponent(actionId)}/status`, {
            status,
            notes: ""
        });

        await loadActionCenter(entity);
    } catch (error) {
        console.error("Action status update failed:", error);
        alert(`Could not update action status: ${error.message}`);
    }
};

const entitySelect = document.getElementById("entitySelect");
const forecastTargetSelect = document.getElementById("forecastTargetSelect");

function formatCurrency(value) {
    if (value == null || !Number.isFinite(Number(value))) return "—";

    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
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


// ADD THIS BELOW apiGet()
async function apiPatch(path, body) {
    const response = await fetch(`${API_BASE}${path}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(body)
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.detail || `${path}: HTTP ${response.status}`);
    }

    return data;
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
                               "₹" + Number(value).toLocaleString("en-IN")
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
    const metadata = forecast?.metadata || {};

    const metricLabels = {
        Revenue: "Revenue",
        CostOfSales: "Cost of Sales",
        SupplierInvoices: "Supplier Invoices"
    };

    const statusLabels = {
        historical_forecast: "Historical Forecast",
        current_period_estimate: "Current Period Estimate",
        future_forecast: "Future Forecast"
    };

    const forecastStatus =
        statusLabels[metadata.forecast_status] ||
        "Status unavailable";

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
            ${escapeHTML(forecast?.model || "Unavailable")}
        </div>

        <div class="insight-placeholder">
            <strong>Forecast period</strong><br>
            ${escapeHTML(point?.period || "Unavailable")}
        </div>

        <div class="insight-placeholder">
            <strong>Predicted ${metricLabels[target]}</strong><br>
            ${point ? formatCurrency(point.predicted_value) : "Unavailable"}
        </div>

        <div class="insight-placeholder">
            <strong>Forecast classification</strong><br>
            ${escapeHTML(forecastStatus)}
        </div>

        <div class="insight-placeholder">
            <strong>Data freshness</strong><br>
            ${escapeHTML(metadata.data_freshness || "Unavailable")}
        </div>

        <div class="insight-placeholder">
            <strong>Training data through</strong><br>
            ${escapeHTML(metadata.training_end || "Unavailable")}
        </div>

        <div class="insight-placeholder">
            <strong>Dataset</strong><br>
            ${escapeHTML(metadata.dataset || "Unavailable")}
            (${escapeHTML(metadata.dataset_type || "Unknown")})
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

    loadActionCenter(entity);
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

// Workspace navigation and visibility controller
const navLinks = document.querySelectorAll('.sidebar .nav-item');

const navigationMap = {
    'Command Center': 'command',
    'Forecasting': 'forecast',
    'Working Capital': 'working-capital',
    'Receivables': 'receivables',
    'Payables': 'payables',
    'Scenario Simulator': 'simulator'
};

navLinks.forEach(link => {
    const label = link.querySelector('span')?.textContent.trim();
    if (navigationMap[label]) {
        link.dataset.view = navigationMap[label];
    }
});

const welcomeSection = document.querySelector('.welcome-section');
const kpiSection = document.querySelector('.kpi-grid');
const contentGrid = document.querySelector('.content-grid');
const forecastPanel = document.querySelector('.forecast-panel');
const insightsPanel = document.querySelector('.insights-panel');
const actionCenterPanel = document.getElementById('actionCenterContent')?.closest('.panel');
const entityPanel = document.querySelector('.entity-panel');
const dataImportPanel = document.getElementById('dataImportPanel');

const workingCapitalPage = document.getElementById('workingCapitalPage');
const simulatorPage = document.getElementById('simulatorPage');
const placeholderPage = document.getElementById('placeholderPage');

const heading = document.querySelector('.topbar h1');

const workspaceLabels = {
    command: 'Command Center',
    forecast: 'Forecasting',
    'working-capital': 'Working Capital',
    receivables: 'Receivables',
    payables: 'Payables',
    simulator: 'Scenario Simulator'
};

function hideAllWorkspaces() {
    [
        welcomeSection,
        kpiSection,
        contentGrid,
        forecastPanel,
        insightsPanel,
        actionCenterPanel,
        entityPanel,
        dataImportPanel,
        workingCapitalPage,
        simulatorPage,
        placeholderPage
    ].forEach(section => {
        if (section) section.hidden = true;
    });
}

function switchWorkspace(view) {
    hideAllWorkspaces();

    // Command Center
    if (view === 'command') {
        if (welcomeSection) welcomeSection.hidden = false;
        if (kpiSection) kpiSection.hidden = false;
        if (contentGrid) contentGrid.hidden = false;
        if (forecastPanel) forecastPanel.hidden = false;
        if (insightsPanel) insightsPanel.hidden = false;
        if (actionCenterPanel) actionCenterPanel.hidden = false;
        if (entityPanel) entityPanel.hidden = false;
        if (dataImportPanel) dataImportPanel.hidden = false;
    }

    // Forecasting
    else if (view === 'forecast') {
        if (contentGrid) contentGrid.hidden = false;
        if (forecastPanel) forecastPanel.hidden = false;
    }

    // Working Capital
    else if (view === 'working-capital') {
        if (workingCapitalPage) workingCapitalPage.hidden = false;
    }

    // Scenario Simulator
    else if (view === 'simulator') {
        if (simulatorPage) simulatorPage.hidden = false;
    }

    // Receivables / Payables
    else if (view === 'receivables' || view === 'payables') {
        if (placeholderPage) placeholderPage.hidden = false;

        const title = document.getElementById('placeholderTitle');
        const description = document.getElementById('placeholderDescription');

        const receivablesContent =
            document.getElementById('receivablesContent');

        const payablesContent =
            document.getElementById('payablesContent');

        const isReceivables = view === 'receivables';

        if (title) {
            title.textContent = isReceivables
                ? 'Receivables Workspace'
                : 'Payables Workspace';
        }

        if (description) {
            description.textContent = isReceivables
                ? 'Monitor customer outstanding balances, collection timelines, and overdue exposure.'
                : 'Monitor supplier obligations, upcoming payments, and cash requirements.';
        }

        if (receivablesContent) {
            receivablesContent.hidden = !isReceivables;
        }

        if (payablesContent) {
            payablesContent.hidden = isReceivables;
        }
    }

    // Update sidebar selection
    navLinks.forEach(link => {
        link.classList.toggle('active', link.dataset.view === view);
    });

    // Update page heading
    if (heading) {
        heading.textContent = workspaceLabels[view] || 'Command Center';
    }
}

navLinks.forEach(link => {
    link.addEventListener('click', event => {
        event.preventDefault();
        switchWorkspace(link.dataset.view);
    });
});

// Start on Command Center
switchWorkspace('command');

function getNumber(id) {
    const value = Number(document.getElementById(id).value);
    return Number.isFinite(value) && value >= 0 ? value : 0;
}

function formatDays(value) {
    return `${value.toFixed(1)} days`;
}

function calculateWorkingCapital() {
    const revenue = getNumber('wcRevenue');
    const cogs = getNumber('wcCogs');
    const dso = getNumber('wcDso');
    const dio = getNumber('wcDio');
    const dpo = getNumber('wcDpo');

    const receivables = revenue / 365 * dso;
    const inventory = cogs / 365 * dio;
    const payables = cogs / 365 * dpo;
    const ccc = dso + dio - dpo;
    const netWC = receivables + inventory - payables;

    document.getElementById('wcReceivables').textContent =
        formatCurrency(receivables);

    document.getElementById('wcInventory').textContent =
        formatCurrency(inventory);

    document.getElementById('wcPayables').textContent =
        formatCurrency(payables);

    document.getElementById('wcCcc').textContent =
        formatDays(ccc);

    document.getElementById('wcNetWorkingCapital').textContent =
        `Estimated net working capital: ${formatCurrency(netWC)} (receivables + inventory − payables).`;
}

document.getElementById('calculateWCButton')
    .addEventListener('click', calculateWorkingCapital);

function runScenario() {
    const revenue = getNumber('simRevenue');
    const cogs = getNumber('simCogs');

    const dso0 = getNumber('simDsoBase');
    const dso1 = getNumber('simDsoNew');

    const dio0 = getNumber('simDioBase');
    const dio1 = getNumber('simDioNew');

    const dpo0 = getNumber('simDpoBase');
    const dpo1 = getNumber('simDpoNew');

    const dailyRevenue = revenue / 365;
    const dailyCogs = cogs / 365;

    const baseCCC = dso0 + dio0 - dpo0;
    const newCCC = dso1 + dio1 - dpo1;

    const baseNWC =
        dailyRevenue * dso0 +
        dailyCogs * dio0 -
        dailyCogs * dpo0;

    const scenarioNWC =
        dailyRevenue * dso1 +
        dailyCogs * dio1 -
        dailyCogs * dpo1;

    const release = baseNWC - scenarioNWC;

    document.getElementById('simCashImpact').textContent =
        `${release >= 0 ? '+' : '−'}${formatCurrency(Math.abs(release))}`;

    document.getElementById('simCccBase').textContent =
        formatDays(baseCCC);

    document.getElementById('simCccNew').textContent =
        formatDays(newCCC);

    document.getElementById('scenarioExplanation').textContent =
        release >= 0
            ? `This scenario reduces estimated net working capital by ${formatCurrency(release)}, potentially releasing cash. Cash release is an estimate, not guaranteed cash flow.`
            : `This scenario increases estimated net working capital by ${formatCurrency(Math.abs(release))}, potentially consuming cash. Cash impact is an estimate.`;
}

document.getElementById('runScenarioButton')
    .addEventListener('click', runScenario);

calculateWorkingCapital();
runScenario();

// Manual CSV refresh: validate and replace the active monthly P&L dataset through the API.
const uploadDatasetButton = document.getElementById('uploadDatasetButton');

if (uploadDatasetButton) {
    uploadDatasetButton.addEventListener('click', async () => {
        const input = document.getElementById('datasetFile');
        const status = document.getElementById('uploadStatus');
        const button = document.getElementById('uploadDatasetButton');
        const file = input.files?.[0];

        if (!file) {
            status.textContent = 'Choose a CSV file first.';
            return;
        }

        if (!file.name.toLowerCase().endsWith('.csv')) {
            status.textContent = 'Only CSV files are supported.';
            return;
        }

        button.disabled = true;
        status.textContent = 'Validating and importing…';

        try {
            const response = await fetch(`${API_BASE}/data/upload`, {
                method: 'POST',
                headers: {'Content-Type': 'text/csv'},
                body: await file.text()
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || `Import failed (${response.status})`);
            }

            status.textContent =
                `Imported ${result.rows} rows · latest ${result.latest_period}`;

            analyticsCache = {};
            forecastCache = {};

            await loadDashboard();

        } catch (error) {
            status.textContent = `Import failed: ${error.message}`;

        } finally {
            button.disabled = false;
        }
    });
}

