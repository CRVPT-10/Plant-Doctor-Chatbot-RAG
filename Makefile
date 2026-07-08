.PHONY: setup ingest run-backend run-frontend test eval baseline benchmark clean

PYTHON = venv/Scripts/python
STREAMLIT = venv/Scripts/streamlit
UV_SERVER = venv/Scripts/uvicorn

setup:
	@echo "Creating virtual environment..."
	C:/Users/chunk/AppData/Local/Programs/Python/Python312/python.exe -m venv venv
	@echo "Upgrading pip..."
	$(PYTHON) -m pip install --upgrade pip
	@echo "Installing dependencies..."
	$(PYTHON) -m pip install -r requirements.txt
	@echo "Setting up sample documents..."
	$(PYTHON) scripts/download_sample_docs.py
	@echo "Setup complete! Run 'make run-backend' and 'make run-frontend' to start the application."

ingest:
	@echo "Ingesting agricultural documents..."
	$(PYTHON) scripts/build_index.py

ingest-rebuild:
	@echo "Force rebuilding agricultural index..."
	$(PYTHON) scripts/build_index.py --rebuild

run-backend:
	@echo "Starting FastAPI backend server on port 8000..."
	$(UV_SERVER) app.api:app --host 0.0.0.0 --port 8000 --reload

run-frontend:
	@echo "Starting Streamlit frontend on port 8501..."
	$(STREAMLIT) run app/main.py --server.port 8501

test:
	@echo "Running unit tests..."
	$(PYTHON) -m pytest tests/ -v

eval:
	@echo "Running RAG evaluation suite..."
	$(PYTHON) evaluation/evaluate.py

baseline:
	@echo "Running retrieval baseline comparisons..."
	$(PYTHON) evaluation/baselines.py "tomato leaf curl"

benchmark:
	@echo "Running speed and latency benchmarks..."
	$(PYTHON) evaluation/benchmark_runner.py

clean:
	@echo "Cleaning caches, logs and temporary files..."
	rmdir /s /q cache logs data\\processed
	@echo "Done."
