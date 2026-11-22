document.addEventListener("DOMContentLoaded", () => {
    const button = document.getElementById("runAiAnalysisBtn");
    const queryInput = document.getElementById("aiQueryInput");
    const results = document.getElementById("aiAnalysisResults");
    const status = document.getElementById("aiAnalysisStatus");
    const entitySelect = document.getElementById("entitySelect");

    if (!button || !queryInput || !results || !status) {
        console.error("AI Analysis: Required elements not found.");
        return;
    }

    button.addEventListener("click", async () => {
        const query = queryInput.value.trim();
        const entity = entitySelect?.value || "LOG";

        if (query.length < 3) {
            status.hidden = false;
            status.textContent = "Please enter a valid financial question.";
            return;
        }

        button.disabled = true;
        button.textContent = "Analyzing...";

        status.hidden = false;
        status.textContent = `Investigating ${entity}...`;

        results.innerHTML = `
            <div class="insight-placeholder">
                Running financial investigation...
            </div>
        `;

        try {
            const response = await fetch(`${window.LEDGERLENS_API_BASE || "http://127.0.0.1:8000"}/analyze`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ query, entity })
            });

            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.detail || `API returned ${response.status}`);
            }

            const findings = data.findings && typeof data.findings === "object"
                ? data.findings
                : {};
            data.errors = Array.isArray(data.errors)
                ? data.errors
                : data.errors ? [String(data.errors)] : [];
            const hasFindings = Object.values(findings).some(value =>
                Array.isArray(value) && value.length > 0
            );
            const hasTrace = Array.isArray(data.trace) && data.trace.length > 0;
            if (!hasFindings && !hasTrace) {
                throw new Error((data.errors || []).join(" ") || "No analysis results were returned.");
            }
            // Older API responses omit `status`; available findings still count as a result.
            data.status = data.status === "partial" || (data.errors || []).length
                ? "partial"
                : "completed";

            renderAIAnalysis(data, entity, query);

            status.textContent = data.status === "partial"
                ? "Analysis completed with some steps unavailable."
                : "Analysis completed successfully.";

        } catch (error) {
            console.error("AI Analysis Error:", error);

            const errorMessage = document.createElement("div");
            errorMessage.className = "ai-error";
            errorMessage.textContent = `Analysis failed: ${error.message}`;
            results.replaceChildren(errorMessage);

            status.textContent = "Analysis failed.";
        } finally {
            button.disabled = false;
            button.textContent = "Run AI Analysis";
        }
    });

    console.log("AI Analysis module loaded successfully.");
});

function escapeAIHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    }[char]));
}

function renderAIAnalysis(data, entity, query) {
    const findings = data.findings || {};
    const risks = Array.isArray(findings.risks) ? findings.risks : [];
    const riskData = risks.find(item => item.agent === "risk_agent") || {};
    const riskList = Array.isArray(riskData.risks) ? riskData.risks : [];

    const riskScore = Number(riskData.risk_score ?? 0);
    const riskLevel = riskData.overall_risk || "Unknown";
    const levelClass = String(riskLevel).toLowerCase();

    const analystData = Array.isArray(findings.financial_analysis)
        ? findings.financial_analysis[0] || {}
        : {};
    const financialContext = riskData.financial_context || analystData.context || {};
    const financials = financialContext.current_financials || analystData.metrics || {};
    const comparison = financialContext.historical_comparison || {};

    const score = Math.max(0, Math.min(100, riskScore));

    const fmtMoney = value => {
        if (value == null || !Number.isFinite(Number(value))) {
            return "—";
        }

        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: financialContext.currency || "USD",
            maximumFractionDigits: 0
        }).format(Number(value));
    };

    const fmtPercent = value =>
        value == null || !Number.isFinite(Number(value))
            ? "—"
            : `${Number(value).toFixed(2)}%`;

    const getTrendClass = (value, metric) => {
        if (value == null || Number(value) === 0) {
            return "neutral";
        }

        const val = Number(value);

        const unfavorableWhenIncreasing = [
            "cost_of_sales",
            "supplier_invoices",
            "expenses",
            "debt"
        ];

        const isUnfavorableMetric =
            unfavorableWhenIncreasing.includes(metric);

        if (isUnfavorableMetric) {
            return val > 0 ? "negative" : "positive";
        }

        return val > 0 ? "positive" : "negative";
    };

    const metricCard = (label, value, trend, metricType = "normal") => `
        <div class="ll-metric-card">
            <span class="ll-metric-label">${escapeAIHTML(label)}</span>
            <strong class="ll-metric-value ${
                trend == null
                    ? "neutral"
                    : metricType === "cost"
                        ? (Number(trend) > 0 ? "negative" : "positive")
                        : (Number(trend) > 0 ? "positive" : "negative")
        }">
            ${escapeAIHTML(value)}
            </strong>
        </div>
    `;

    const getRiskActionPlan = (riskName) => {
    const name = String(riskName || "").toLowerCase();

    if (name.includes("cost") || name.includes("margin")) {
        return {
            priority: "HIGH PRIORITY",
            owner: "Finance + Operations",
            reason: "Costs are increasing faster than revenue, potentially compressing margins.",
            actions: [
                "Identify the major contributors to cost growth.",
                "Compare operational costs against the previous period.",
                "Investigate expenses that increased despite declining revenue.",
                "Evaluate opportunities to control costs without disrupting operations."
            ]
        };
    }

    if (name.includes("gross profit") || name.includes("profit")) {
        return {
            priority: "HIGH PRIORITY",
            owner: "Finance",
            reason: "Gross profit deterioration may indicate declining profitability.",
            actions: [
                "Review gross-profit trends across recent periods.",
                "Identify whether cost increases or revenue declines are driving deterioration.",
                "Evaluate product, service, or business-segment margins.",
                "Review pricing and cost structure."
            ]
        };
    }

    if (name.includes("supplier")) {
        return {
            priority: "REVIEW REQUIRED",
            owner: "Finance + Procurement",
            reason: "Supplier invoices are high relative to revenue and may require cash-flow investigation.",
            actions: [
                "Review outstanding supplier invoices and their due dates.",
                "Identify concentration among major suppliers.",
                "Compare upcoming obligations against expected cash inflows.",
                "Review payment schedules and potential liquidity pressure."
            ]
        };
    }

    if (name.includes("revenue")) {
        return {
            priority: "REVIEW REQUIRED",
            owner: "Finance + Sales",
            reason: "Declining revenue may indicate reduced demand or loss of business.",
            actions: [
                "Identify customers or segments contributing to revenue decline.",
                "Compare revenue across recent reporting periods.",
                "Investigate changes in sales volume and customer activity.",
                "Identify opportunities to recover declining revenue."
            ]
        };
    }

    return {
        priority: "INVESTIGATE",
        owner: "Finance Team",
        reason: "This indicator requires further investigation.",
        actions: [
            "Validate the underlying financial data.",
            "Compare the indicator against previous periods.",
            "Identify potential contributing factors.",
            "Document findings and determine appropriate next steps."
        ]
    };
};

    const riskCards = riskList.map((risk, index) => {
        const evidence = risk.evidence || {};
        const severity = String(risk.severity || "medium").toLowerCase();

        const plan = getRiskActionPlan(risk.risk);

        const evidenceHTML = Object.entries(evidence).map(([key, value]) => `
            <div class="ll-evidence-item">
                <span>${escapeAIHTML(key.replace(/_/g, " "))}</span>
                <strong>
                    ${escapeAIHTML(
                        typeof value === "number"
                            ? fmtPercent(value)
                            : String(value)
                    )}
                </strong>
            </div>
        `).join("");

        const actionHTML = plan.actions.map(action => `
            <li>${escapeAIHTML(action)}</li>
        `).join("");

        return `
            <article class="ll-risk-card ${escapeAIHTML(severity)}">

                <div class="ll-risk-topline">
                    <span class="ll-risk-number">
                        RISK ${String(index + 1).padStart(2, "0")}
                    </span>

                    <span class="ll-severity ${escapeAIHTML(severity)}">
                        ${escapeAIHTML(severity)}
                    </span>
                </div>

                <h4>${escapeAIHTML(risk.risk || "Unspecified risk")}</h4>

                <p class="ll-risk-description">
                    ${escapeAIHTML(risk.description || "No description available.")}
                </p>

                ${evidenceHTML ? `
                    <div class="ll-risk-evidence">
                        <span class="ll-evidence-title">Supporting evidence</span>
                        <div class="ll-evidence-grid">
                            ${evidenceHTML}
                        </div>
                    </div>
                ` : ""}

                <div class="ll-action-plan">

                    <div class="ll-action-plan-header">
                        <span>RECOMMENDED RESPONSE</span>
                        <span class="ll-action-priority">
                            ${escapeAIHTML(plan.priority)}
                        </span>
                    </div>

                    <p class="ll-action-reason">
                        ${escapeAIHTML(plan.reason)}
                    </p>

                    <div class="ll-action-owner">
                        <span>Suggested owner</span>
                        <strong>${escapeAIHTML(plan.owner)}</strong>
                    </div>

                    <h5>Investigation checklist</h5>

                    <ul class="ll-action-list">
                        ${actionHTML}
                    </ul>

                </div>

            </article>
        `;
    }).join("");

    const trace = (Array.isArray(data.trace) ? data.trace : []).map(step => `
        <li>${escapeAIHTML(step)}</li>
    `).join("");

    const sectionItems = [
        ["Financial Analysis", findings.financial_analysis],
        ["Forecast", findings.forecast],
        ["Investigation", findings.investigation],
        ["Recommended Actions", findings.actions],
    ].filter(([, items]) => Array.isArray(items) && items.length);

    const sectionText = item => {
        const analysis = item.analysis || {};
        const summary = analysis.executive_summary || item.executive_summary ||
            item.summary || item.conclusion || item.message;
        if (summary) return String(summary);
        if (Array.isArray(item.forecast)) {
            return item.forecast.map(point =>
                `${point.period || "Forecast"}: ${point.predicted_value ?? point.value ?? "—"}`
            ).join(" · ");
        }
        const details = Object.entries(item)
            .filter(([key, value]) => !["context", "financial_context", "evidence", "agent", "entity", "query"].includes(key) && value != null)
            .map(([key, value]) => `${key.replace(/_/g, " ")}: ${typeof value === "object" ? JSON.stringify(value) : value}`);
        return details.join(" · ") || "Analysis step completed.";
    };

    const sectionHTML = sectionItems.map(([title, items]) => `
        <section class="ll-report-section">
            <div class="ll-section-heading"><h3>${escapeAIHTML(title)}</h3></div>
            <ul class="ll-action-list">${items.map(item => `<li>${escapeAIHTML(sectionText(item))}</li>`).join("")}</ul>
        </section>
    `).join("");

    const responseErrors = Array.isArray(data.errors) ? data.errors : [];
    const errors = responseErrors.length
        ? `
            <div class="ll-analysis-errors">
                ${responseErrors.map(error => escapeAIHTML(error)).join("<br>")}
            </div>
        `
        : "";

    const supplierExposure =
        financials.supplier_invoices != null && financials.revenue
            ? (financials.supplier_invoices / financials.revenue) * 100
            : financialContext.financial_ratios?.supplier_invoices_to_revenue_pct;

    const revenueChange = comparison.revenue_change_pct;
    const costChange = comparison.cost_of_sales_change_pct;
    const grossProfitChange = comparison.gross_profit_change_pct;

    document.getElementById("aiAnalysisResults").innerHTML = `
        <div class="ll-report">

            <!-- HEADER -->
            <header class="ll-report-header">
                <div class="ll-report-heading">
                    <div class="ll-report-label">
                        <span class="ll-report-dot"></span>
                        LEDGERLENS INTELLIGENCE
                    </div>

                    <h2>Financial Risk Assessment</h2>

                    <p class="ll-report-subtitle">
                        Entity ${escapeAIHTML(entity)} ·
                        ${escapeAIHTML(financialContext.latest_period || "Latest available data")}
                    </p>
                </div>

                <div class="ll-report-status">
                    ${data.status === "partial" ? "PARTIAL ANALYSIS" : "ANALYSIS COMPLETE"}
                </div>
            </header>

            <!-- RISK SCORE + SNAPSHOT -->
            <section class="ll-overview">

                <div class="ll-score-panel">
                    <div class="ll-section-label">RISK INDEX</div>

                    <div class="ll-score-gauge"
                        style="--score-angle: ${score * 3.6}deg">

                        <div class="ll-score-inner">
                            <strong>${escapeAIHTML(riskScore)}</strong>
                            <span>OUT OF 100</span>
                        </div>
                    </div>

                    <div class="ll-risk-level ${escapeAIHTML(levelClass)}">
                        ${escapeAIHTML(String(riskLevel).toUpperCase())} RISK
                    </div>

                    <p class="ll-score-caption">
                        Heuristic risk score · Not a probability
                    </p>
                </div>

                <div class="ll-financial-snapshot">

                    <div class="ll-snapshot-heading">
                        <span class="ll-section-label">FINANCIAL SNAPSHOT</span>
                        <span class="ll-period">
                            ${escapeAIHTML(financialContext.latest_period || "—")}
                        </span>
                    </div>

            <div class="ll-snapshot-grid">

                <div class="ll-snapshot-card">
                    <span>Revenue</span>
                    <strong>${fmtMoney(financials.revenue)}</strong>
                </div>

                <div class="ll-snapshot-card">
                    <span>Gross Margin</span>
                    <strong>${fmtPercent(financials.gross_margin_pct)}</strong>
                </div>

                <div class="ll-snapshot-card">
                    <span>Risk Indicators</span>
                    <strong>${escapeAIHTML(riskData.risk_count ?? riskList.length)}</strong>
                </div>

                <div class="ll-snapshot-card">
                    <span>Supplier Exposure</span>
                    <strong>${fmtPercent(supplierExposure)}</strong>
                </div>

            </div>
        </div>
    </section>

    <!-- PERFORMANCE -->
    <section class="ll-report-section">

        <div class="ll-section-heading">
            <div>
                <span class="ll-section-label">PERFORMANCE</span>
                <h3>Financial Trends</h3>
            </div>
            <span class="ll-section-caption">
                Historical comparison
            </span>
        </div>

        <div class="ll-metrics-grid">

            ${metricCard(
                "Revenue",
                fmtPercent(revenueChange),
                revenueChange,
                "normal"
            )}

            ${metricCard(
                "Cost of Sales",
                fmtPercent(costChange),
                costChange,
                "cost"
            )}

            ${metricCard(
                "Gross Profit",
                fmtPercent(grossProfitChange),
                grossProfitChange,
                "normal"
            )}

            ${metricCard(
                "Supplier / Revenue",
                fmtPercent(supplierExposure),
                null,
                "neutral"
            )}

        </div>
    </section>

            ${sectionHTML}

            <!-- RISK FINDINGS -->
            <section class="ll-report-section">

                <div class="ll-section-heading">
                    <div>
                        <span class="ll-section-label">DETECTED INDICATORS</span>
                        <h3>Risk Findings</h3>
                    </div>

                    <span class="ll-risk-count">
                        ${riskList.length} identified
                    </span>
                </div>

                <div class="ll-risk-list">
                    ${riskCards || `
                        <div class="ll-empty-state">
                            No risk findings returned for this analysis.
                        </div>
                    `}
                </div>

            </section>

            <!-- EXECUTION DETAILS -->
            <details class="ll-execution-details">

                <summary>
                    <div>
                        <span class="ll-section-label">SYSTEM TRANSPARENCY</span>
                        <strong>Analysis execution details</strong>
                    </div>
                    <span class="ll-details-toggle">＋</span>
                </summary>

                <div class="ll-execution-content">

                    <div class="ll-execution-meta">
                        <div>
                            <span>Entity</span>
                            <strong>${escapeAIHTML(entity)}</strong>
                        </div>

                        <div>
                            <span>Dataset</span>
                            <strong>${escapeAIHTML(financialContext.dataset || "Unknown")}</strong>
                        </div>

                        <div>
                            <span>Type</span>
                            <strong>${escapeAIHTML(financialContext.dataset_type || "Unknown")}</strong>
                        </div>

                        <div>
                            <span>Duration</span>
                            <strong>${escapeAIHTML(data.execution_duration_ms ?? "—")} ms</strong>
                        </div>
                    </div>

                    <h4>Agent Execution Trace</h4>

                    <ol class="ll-trace-list">
                        ${trace || "<li>No execution trace available.</li>"}
                    </ol>

                    <p class="ll-methodology">
                        ${escapeAIHTML(
                            riskData.methodology ||
                            "Risk indicators are heuristic assessments derived from financial metrics."
                        )}
                    </p>

                </div>
            </details>

            ${errors}

        </div>
    `;
}

