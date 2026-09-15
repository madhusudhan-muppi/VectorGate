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

## Run the demo

```powershell
python -m software.scripts.demo
```

The demo prints the injected and detected frequencies plus all extracted features. It saves `waveform.png` and `spectrum.png` in `outputs`. A different output directory can be selected with `--output-dir`.

## Run tests

```powershell
python -m pytest
```

## Scientific scope and limitations

The synthetic waveform and any rotating/slotted calibration-disc result validate the sensing and DSP chain only. They do not validate mosquito species classification accuracy. Dominant or fundamental wingbeat frequency is one feature, not a unique species identifier. Species-level claims require labelled biological validation and additional features such as harmonic structure, spectral energy, signal quality, event duration, temperature, and humidity. No production classifier, backend, database, dashboard, or ESP32 firmware is included in Stage 1.
