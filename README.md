# LedgerLens AI

**Financial Digital Twin and Working Capital Intelligence for Indian MSMEs**

LedgerLens AI aims to help manufacturing and trading MSMEs understand
cash-flow patterns, working-capital requirements and financial risks.

## Current implementation

The initial forecasting foundation includes:

- `forecasting.py` — Holt-Winters and moving-average forecasting.
- `evaluation.py` — MAE, RMSE, MAPE, sMAPE and forecast bias.
- `intervals.py` — prediction intervals and empirical coverage.
- `model_registry.py` — model serialization and metadata.
- `ledgerlens_pipeline.py` — integrated forecasting workflow.

## Current experiment

The initial experiments use the synthetic DD-WCP-003 working-capital
dataset from Findi360.

The dataset contains synthetic USD-denominated financial records.
It is not real Indian MSME transaction data.

RET Revenue forecasting experiment:
- Training: January 2023 – November 2025.
- Validation: December 2025 – September 2026.
- Evaluation: expanding-window, one-step-ahead.
- Holt-Winters MAPE: 3.20%.
- Moving-average baseline MAPE: 7.11%.

These are preliminary results on synthetic data, not evidence of
performance on real Indian businesses.

## Technology

- Python
- Pandas and NumPy
- Statsmodels
- Joblib

## Planned development

1. Multi-entity financial forecasting.
2. Cash-flow and working-capital analytics.
3. Financial data ingestion and normalization.
4. Scenario simulation and liquidity intelligence.
5. FastAPI backend.
6. Integration with SYNTHEGRA through its API.

## Project structure

This is an early experimental checkpoint. Production API integration,
real-world validation and deployment are not yet complete.

## Data and security

Datasets, trained model artifacts, credentials and private financial
records must not be committed to this repository.

## License

To be decided.
