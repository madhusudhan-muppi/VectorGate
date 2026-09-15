const int SENSOR = 34;
const int EMITTER = 25;
const int N = 1024;
const int SAMPLE_HZ = 5000;

uint16_t buf[N];

void setup() {
  Serial.begin(115200);
  pinMode(EMITTER, OUTPUT);
  digitalWrite(EMITTER, HIGH);
  analogSetPinAttenuation(SENSOR, ADC_11db);
  delay(500);
}

void loop() {
  unsigned long period = 1000000UL / SAMPLE_HZ;
  unsigned long t = micros();
  for (int i = 0; i < N; i++) {
    while (micros() - t < period) {}
    t += period;
    buf[i] = analogRead(SENSOR);
  }

  long sum = 0;
  uint16_t lo = 4095, hi = 0;
  for (int i = 0; i < N; i++) {
    sum += buf[i];
    if (buf[i] < lo) lo = buf[i];
    if (buf[i] > hi) hi = buf[i];
  }
  int mean = sum / N;

  int thHi = mean + (hi - mean) / 3;
  int thLo = mean - (mean - lo) / 3;

  int crossings = 0;
  bool above = buf[0] > mean;
  int firstX = -1, lastX = -1;
  for (int i = 1; i < N; i++) {
    if (above && buf[i] < thLo) { above = false; crossings++; if (firstX < 0) firstX = i; lastX = i; }
    else if (!above && buf[i] > thHi) { above = true; }
  }

  float hz = 0;
  if (crossings >= 2 && lastX > firstX)
    hz = (float)(crossings - 1) * SAMPLE_HZ / (lastX - firstX);

  Serial.print("min="); Serial.print(lo);
  Serial.print(" max="); Serial.print(hi);
  Serial.print(" swing="); Serial.print(hi - lo);
  Serial.print("  blade_Hz="); Serial.print(hz, 1);
  Serial.print("  RPM="); Serial.println(hz * 60.0 / 7.0);

  delay(1000);
}