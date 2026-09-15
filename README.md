# VectorGate

VectorGate is a prototype for continuous mosquito/vector surveillance. An optical sensing tunnel uses an IR source and photodiode or phototransistor to capture light modulation as a flying insect crosses the beam. The longer-term system will acquire waveforms, extract flight features, classify conservatively, transmit detections, and visualize a network of nodes.

## Stage 1: Python DSP prototype

This stage implements only the reusable signal-processing path:

- synthetic optical-wingbeat-like waveform generation
- DC removal, Hann windowing, one-sided FFT, and configurable band limiting
- dominant-frequency and feature extraction
- deterministic automated tests
- saved time-domain and spectrum plots

The analysis accepts NumPy-compatible samples independently of the simulator, so recorded waveforms and future ESP32/ADC samples can use the same API. The current feature vector includes dominant frequency and magnitude, second/third harmonic ratios, RMS, peak-to-peak amplitude, spectral energy, and an estimated SNR.

## Stage 2: event detection and sensor input contract

Stage 2 adds a source-neutral pipeline:

```text
SensorRecording -> RMS/MAD event detector -> event windows -> Stage 1 DSP -> FlightEventResult
```

`SensorRecording` contains samples, sample rate, source, and optional node/environment metadata. The detector uses configurable frame length, hop, robust background threshold, minimum/maximum duration, merge gap, and pre/post padding. It is an explainable energy detector, not an ML classifier, and can still produce candidates for unusual background transients.

The continuous simulator embeds smoothly ramped temporary events in background noise. The same pipeline accepts simulator data, recorded CSV data, and future ADC/serial data without changing the DSP analysis.

## Setup on Windows PowerShell

From the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run the command below once for the current user, then activate the environment again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Run the Stage 1 demo

```powershell
python -m software.scripts.demo
```

The demo prints the injected and detected frequencies plus all extracted features. It saves `waveform.png` and `spectrum.png` in `outputs`. A different output directory can be selected with `--output-dir`.

## Run the Stage 2 event demo

```powershell
python -m software.scripts.event_demo
```

This generates a five-second continuous recording with approximately 500 Hz and 350 Hz events, detects both automatically, prints timing and frequency results, and saves `event_detection.png` in `outputs`.

## CSV input format

The canonical recorded format is:

```text
sample,value
0,2048
1,2051
2,2046
```

`sample,value` requires an externally supplied sample rate. The loader also accepts `time_seconds,value` with strictly increasing, uniformly spaced timestamps and can infer the sample rate from them. Malformed, empty, non-finite, or inconsistent files are rejected. See [docs/HARDWARE_SOFTWARE_CONTRACT.md](docs/HARDWARE_SOFTWARE_CONTRACT.md) for the hardware handoff.

## Run tests

```powershell
python -m pytest
```

The suite includes the Stage 1 regression tests plus event detection, event timing, short-transient rejection, gap merging, CSV validation, metadata propagation, and an off-bin 517.3 Hz FFT test.

## Scientific scope and limitations

The synthetic waveform, event stream, and any rotating/slotted calibration-disc result validate the sensing and DSP chain only. They do not validate mosquito species classification accuracy. Dominant or fundamental wingbeat frequency is one feature, not a unique species identifier. Temperature and humidity are context features, not species identifiers. Species-level claims require labelled biological validation and additional features such as harmonic structure, spectral energy, signal quality, event duration, temperature, and humidity. No production classifier, dashboard, map UI, or ESP32 firmware is included in the current prototype.

## Stage 3: FastAPI backend and persistent detection store

Stage 3 adds a local SQLite-backed API:

```text
Stage 2 FlightEventResult -> validated API payload -> SQLite detection store -> query/summary endpoints
```

The backend uses SQLAlchemy behind repository helpers so PostgreSQL can replace SQLite later. Tables are initialized automatically. The default database is `data/vectorgate.db`; set `VECTORGATE_DATABASE_URL` to use another SQLAlchemy URL. The local database and journal files are ignored by Git.

### Start the backend

```powershell
python -m uvicorn backend.app.main:app --reload
```

Swagger/OpenAPI is available at `http://127.0.0.1:8000/docs`. The API is a local Buildathon prototype with no authentication. CORS defaults to `http://localhost:3000` and `http://localhost:5173`; override with a comma-separated `VECTORGATE_CORS_ORIGINS` value.

### API overview

- `GET /api/v1/health` checks API/database availability.
- `POST /api/v1/nodes`, `GET /api/v1/nodes`, and `GET /api/v1/nodes/{node_id}` manage fixed manually configured nodes.
- `POST /api/v1/detections`, `GET /api/v1/detections`, and `GET /api/v1/detections/{id}` ingest and query raw DSP detections.
- `GET /api/v1/stats/summary` returns node and detection counts.
- `GET /api/v1/nodes/{node_id}/activity` returns deterministic time buckets.
- `GET /api/v1/map/nodes` returns observed detection activity with configured coordinates for the future map.

Classification fields are nullable and no species is inferred from frequency. A DSP detection with no class or confidence is valid.

### Run the demo publisher

Start the backend first, then in another PowerShell terminal run:

```powershell
python -m backend.scripts.publisher
```

The publisher registers `VG-DEMO-01` when needed, generates a continuous Stage 2 fixture, detects its events, converts the resulting `FlightEventResult` objects, and POSTs them to the API. Its demo coordinates are explicitly labelled as a synthetic fixture, not a physical location. Use `--base-url` and `--node-id` to target another local API/node.

### Run all tests

```powershell
python -m pytest -q
```

Backend tests use isolated temporary SQLite files and do not modify the development database.
