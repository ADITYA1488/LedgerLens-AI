# Running LedgerLens AI

## 1. Install dependencies

    pip install -r requirements.txt

## 2. Configure the dataset

Set LEDGERLENS_DATA_DIR to the directory containing:

    DD-WCP-003_FactMonthlyPL.csv

The dataset is synthetic and denominated in USD.

## 3. Start the API

From the project root:

    uvicorn main:app --reload --host 127.0.0.1 --port 8000

## 4. Verify the API

    http://127.0.0.1:8000/health

Interactive API documentation:

    http://127.0.0.1:8000/docs

## 5. Serve the frontend

From the frontend directory:

    python -m http.server 5500

Open:

    http://127.0.0.1:5500

The frontend expects the API at:

    http://127.0.0.1:8000

Only use synthetic demonstration data in public demos.
