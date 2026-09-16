/*
 * VectorGate optical wingbeat sensing node.
 *
 * An IR beam crosses the tunnel. An insect flying through modulates the light
 * with its wingbeats; the photodetector turns that into a voltage the ESP32
 * samples. This sketch captures windows, decides which ones contain an event,
 * and streams the raw window to the host, which extracts features and
 * classifies. Feature extraction deliberately does NOT happen here: the server
 * runs the exact code the model was trained with, so the two cannot drift.
 *
 * Wiring (as built)
 *   Emitter:  GPIO25 -> 220R -> IR LED -> GND
 *   Detector: 3V3 -> detector long leg; short leg -> GPIO34 and -> 10k -> GND
 *
 * GPIO34 is on ADC1, which keeps working while Wi-Fi is active. ADC2 does not.
 *
 * Sample rate is 8 kHz to match the rate the species model was trained at.
 * Resampling on the host would work, but matching here avoids the question.
 *
 * Serial commands (type one character):
 *   c  re-run the calibration report
 *   e  toggle the emitter (beam on/off check)
 *   s  send the next window regardless of whether it looks like an event
 *   q  quieter: stop printing per-window statistics
 */

const int SENSOR_PIN = 34;
const int EMITTER_PIN = 25;

const uint32_t SERIAL_BAUD = 921600;
const uint32_t SAMPLE_HZ = 8000;       // matches the classifier's training rate
const int WINDOW_SAMPLES = 8000;       // 1.0 s: long enough for the host's
                                       // event detector to establish a baseline
const char NODE_ID[] = "VG-VITC-01";

// An event window has to stand well clear of the resting noise. The absolute
// floor stops a dead-quiet baseline from making every window look like an event.
const float TRIGGER_FACTOR = 3.0f;
const uint16_t MIN_EVENT_P2P = 40;

// ADC counts at the extremes mean the waveform is being clipped and only on/off
// information survives. Above this fraction the window is reported but flagged.
const float CLIP_WARN_FRACTION = 0.02f;

uint16_t window[WINDOW_SAMPLES];

float baselineP2P = 0.0f;
bool emitterOn = true;
bool verbose = true;
bool forceSend = false;
uint32_t sequence = 0;

struct WindowStats {
  uint16_t low;
  uint16_t high;
  uint16_t peakToPeak;
  uint32_t mean;
  uint32_t clipLow;
  uint32_t clipHigh;
  float achievedRateHz;
};

/* Capture one window, busy-waiting on micros() so the cadence stays even.
 * The elapsed time is measured rather than assumed: if analogRead ever
 * overruns the 125 us budget the real rate drifts below nominal, and every
 * frequency derived from it would be wrong by the same factor. The host is
 * told the rate that actually happened. */
static uint32_t captureWindow() {
  const uint32_t period = 1000000UL / SAMPLE_HZ;
  const uint32_t started = micros();
  uint32_t next = started;
  for (int i = 0; i < WINDOW_SAMPLES; i++) {
    next += period;
    while ((int32_t)(micros() - next) < 0) {
    }
    window[i] = analogRead(SENSOR_PIN);
  }
  return micros() - started;
}

static WindowStats summarise(uint32_t elapsedMicros) {
  WindowStats stats;
  stats.low = 4095;
  stats.high = 0;
  stats.clipLow = 0;
  stats.clipHigh = 0;
  uint64_t total = 0;
  for (int i = 0; i < WINDOW_SAMPLES; i++) {
    const uint16_t value = window[i];
    total += value;
    if (value < stats.low) stats.low = value;
    if (value > stats.high) stats.high = value;
    if (value == 0) stats.clipLow++;
    if (value >= 4095) stats.clipHigh++;
  }
  stats.mean = (uint32_t)(total / WINDOW_SAMPLES);
  stats.peakToPeak = stats.high - stats.low;
  stats.achievedRateHz = elapsedMicros > 0
      ? (float)WINDOW_SAMPLES * 1000000.0f / (float)elapsedMicros
      : 0.0f;
  return stats;
}

static uint16_t averageLevel(int samples) {
  uint32_t total = 0;
  for (int i = 0; i < samples; i++) {
    total += analogRead(SENSOR_PIN);
    delayMicroseconds(200);
  }
  return (uint16_t)(total / samples);
}

/* Report the operating point and say which way to move it.
 *
 * The detector output has to sit near mid-scale with the beam clear. Too high
 * and the waveform clips against the ADC ceiling; too low and it falls into the
 * ESP32's dead zone below roughly 0.1 V, where readings pin to zero. Either way
 * only on/off information survives and the wingbeat shape is lost. */
static void calibrate() {
  digitalWrite(EMITTER_PIN, LOW);
  delay(120);
  const uint16_t dark = averageLevel(200);
  digitalWrite(EMITTER_PIN, emitterOn ? HIGH : LOW);
  delay(120);
  const uint16_t lit = averageLevel(200);

  Serial.printf("#CAL dark=%u lit=%u contrast=%d\n", dark, lit, (int)lit - (int)dark);
  if (abs((int)lit - (int)dark) < 100) {
    Serial.println("#ADVICE beam not reaching the detector: check alignment, wiring and the emitter resistor");
  } else if (lit >= 3900) {
    Serial.println("#ADVICE detector saturating high: lower the load resistor (10k -> 2.2k -> 1k) or widen the gap");
  } else if (lit <= 250) {
    Serial.println("#ADVICE signal too weak: lower the emitter resistor (220R -> 100R) or narrow the gap");
  } else if (lit >= 1200 && lit <= 2900) {
    Serial.println("#ADVICE operating point is good: clear-beam level sits near mid-scale");
  } else {
    Serial.println("#ADVICE usable but off-centre: aim for a clear-beam level of 1500-2500 counts");
  }
}

static void emitWindow(const WindowStats &stats, const char *reason) {
  sequence++;
  Serial.printf("#EVENT node=%s seq=%lu rate_hz=%.1f count=%d mean=%lu p2p=%u clip_lo=%lu clip_hi=%lu reason=%s\n",
                NODE_ID, (unsigned long)sequence, stats.achievedRateHz, WINDOW_SAMPLES,
                (unsigned long)stats.mean, stats.peakToPeak,
                (unsigned long)stats.clipLow, (unsigned long)stats.clipHigh, reason);
  for (int i = 0; i < WINDOW_SAMPLES; i++) {
    Serial.print(window[i]);
    // Wrapping keeps each line short enough for a host reading line by line.
    Serial.print((i % 40 == 39 || i == WINDOW_SAMPLES - 1) ? '\n' : ',');
  }
  Serial.printf("#END seq=%lu\n", (unsigned long)sequence);
}

static void handleCommand() {
  while (Serial.available() > 0) {
    switch (Serial.read()) {
      case 'c':
        calibrate();
        break;
      case 'e':
        emitterOn = !emitterOn;
        digitalWrite(EMITTER_PIN, emitterOn ? HIGH : LOW);
        Serial.printf("#EMITTER %s\n", emitterOn ? "on" : "off");
        break;
      case 's':
        forceSend = true;
        Serial.println("#FORCE next window will be sent");
        break;
      case 'q':
        verbose = !verbose;
        Serial.printf("#VERBOSE %s\n", verbose ? "on" : "off");
        break;
      default:
        break;
    }
  }
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  pinMode(EMITTER_PIN, OUTPUT);
  digitalWrite(EMITTER_PIN, HIGH);
  analogReadResolution(12);
  analogSetPinAttenuation(SENSOR_PIN, ADC_11db);
  delay(400);

  Serial.printf("\n#VG1 READY node=%s rate=%lu window=%d adc_bits=12 vref=3.3\n",
                NODE_ID, (unsigned long)SAMPLE_HZ, WINDOW_SAMPLES);
  calibrate();
}

void loop() {
  handleCommand();

  const uint32_t elapsed = captureWindow();
  const WindowStats stats = summarise(elapsed);

  const uint32_t clipped = stats.clipLow + stats.clipHigh;
  const bool saturated = clipped > (uint32_t)(CLIP_WARN_FRACTION * WINDOW_SAMPLES);
  if (saturated) {
    Serial.printf("#WARN clipping: %lu of %d samples at an ADC rail - waveform shape is lost\n",
                  (unsigned long)clipped, WINDOW_SAMPLES);
  }

  const float trigger = max(baselineP2P * TRIGGER_FACTOR, (float)MIN_EVENT_P2P);
  const bool isEvent = stats.peakToPeak > trigger;

  if (forceSend) {
    emitWindow(stats, "forced");
    forceSend = false;
  } else if (isEvent) {
    emitWindow(stats, saturated ? "event_clipped" : "event");
  } else {
    // Quiet windows train the baseline; event windows must not, or a steady
    // signal would slowly raise the trigger until it stopped firing.
    baselineP2P = baselineP2P == 0.0f
        ? (float)stats.peakToPeak
        : baselineP2P * 0.9f + (float)stats.peakToPeak * 0.1f;
    if (verbose) {
      Serial.printf("#STAT mean=%lu min=%u max=%u p2p=%u clip_lo=%lu clip_hi=%lu rate_hz=%.1f baseline=%.0f trigger=%.0f\n",
                    (unsigned long)stats.mean, stats.low, stats.high, stats.peakToPeak,
                    (unsigned long)stats.clipLow, (unsigned long)stats.clipHigh,
                    stats.achievedRateHz, baselineP2P, trigger);
    }
  }
}
