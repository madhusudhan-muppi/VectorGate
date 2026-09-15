# VectorGate Hardware/Software Contract

## Stage 2 handoff

The software accepts a `SensorRecording` containing a one-dimensional finite sample array, `sample_rate_hz`, and a source label. Optional metadata includes node ID, start time, temperature, and humidity. The preferred prototype sample rate is around 10 kHz with a stable sampling cadence.

Raw or minimally processed ADC samples are preferred for initial integration. The initial DSP analysis band is approximately 80-2000 Hz. Do not clip or saturate the ADC waveform. Report the ADC range and representation, such as signed 12-bit values, unsigned counts, or volts, so amplitudes can be interpreted correctly.

## Recorded handoff

Preferred CSV format:

```text
sample,value
0,2048
1,2051
2,2046
```

A `sample,value` file must be accompanied by the sample rate. The loader also accepts `time_seconds,value` and can infer the rate only from strictly increasing, uniformly spaced timestamps. Include recording duration, node ID, temperature, and humidity when available. Missing metadata remains missing; it is not fabricated.

## Future live handoff

A simple future serial framing can carry a small header followed by sample batches:

```text
rate_hz=10000,node_id=VG-001,count=256\n
<256 ADC sample values>
```

The exact transport and binary encoding should be chosen after hardware measurements. The important contract is a stable sample rate, node identity when available, and an ordered sample batch. This stage does not implement serial transport.

## Bring-up checklist

1. Record background only.
2. Record known LED modulation or another calibration source.
3. Record a known mechanical chopping frequency.
4. Verify that the ADC does not clip or saturate.
5. Compare the known frequency with the DSP result.
6. Only then attempt insect-like events.

Calibration validates sensing and DSP frequency recovery, not mosquito species identification. Biological classification requires labelled biological validation and additional features beyond dominant frequency.
