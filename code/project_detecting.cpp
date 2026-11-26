// ESP32-S3: thu thap dong thoi PPG (Heart Rate 11 Click / OB1203) + GSR Click
// Xuat CSV qua Serial Monitor (115200 baud) o toc do co dinh 50 Hz de train AI.
//
// Cot CSV:
// t_ms, ppg_raw, ppg_new, gsr_spi, gsr_adc, gsr_mv, bpm_est, stress_state
//   ppg_new = 1 neu mau PPG moi trong tick nay, 0 neu la gia tri giu lai tu mau truoc
//   gsr_spi = 12-bit tu MCP3201 tren GSR Click (qua SPI)
//   gsr_adc = 12-bit analogRead chan AN (GPIO4) de doi chieu
//   bpm_est = nhip tim uoc luong thuat toan don gian (0 neu chua co) - chi de tham khao

#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include "ppg_stress_model.h"

// ---------------- Pins ----------------
constexpr int PIN_SDA = 8;
constexpr int PIN_SCL = 9;
constexpr int PIN_GSR_CS = 5;
constexpr int PIN_GSR_SCK = 18;
constexpr int PIN_GSR_MISO = 19;
constexpr int PIN_GSR_AN = 4;

// ---------------- OB1203 ----------------
constexpr uint8_t OB1203_ADDRESS = 0x53;
constexpr uint8_t REG_STATUS_1 = 0x01;
constexpr uint8_t REG_MAIN_CTRL_0 = 0x15;
constexpr uint8_t REG_MAIN_CTRL_1 = 0x16;
constexpr uint8_t REG_INT_CFG_1 = 0x2C;
constexpr uint8_t REG_PPG_PS_GAIN = 0x2E;
constexpr uint8_t REG_PPG_IRLED_CURR_0 = 0x30;
constexpr uint8_t REG_PPG_AVG = 0x35;
constexpr uint8_t REG_PPG_PWIDTH_PERIOD = 0x36;
constexpr uint8_t REG_FIFO_DATA = 0x3B;
constexpr uint8_t PPG_DATA_READY = 0x10;

// ---------------- Sampling ----------------
constexpr uint32_t SAMPLE_PERIOD_US = 20000;  // 50 Hz
constexpr uint8_t GSR_OVERSAMPLE = 4;

SPIClass gsrSpi(FSPI);
bool sensorReady = false;
uint32_t lastPpgRaw = 0;
uint32_t nextTickUs = 0;
uint32_t startMs = 0;

// ---- BPM tham khao (tu code cu) ----
constexpr size_t PPG_WINDOW_SIZE = 80;
float ppgWindow[PPG_WINDOW_SIZE] = {};
size_t ppgWindowIndex = 0;
size_t ppgSamplesSeen = 0;
float ppgBaseline = 0.0f;
bool previousAboveThreshold = false;
uint32_t lastBeatMs = 0;
float heartRateBpm = 0.0f;

// Row-level PPG classifier with a 25-row vote to smooth 50 Hz predictions.
constexpr uint32_t MIN_VALID_PPG = 10000;
constexpr size_t STRESS_VOTE_WINDOW = 25;
uint8_t stressPredictions[STRESS_VOTE_WINDOW] = {};
size_t stressPredictionCount = 0;
size_t stressPredictionIndex = 0;
uint8_t stressedVoteCount = 0;
uint32_t lastPpgSampleMs = 0;

bool writeRegister(uint8_t reg, uint8_t value) {
    Wire.beginTransmission(OB1203_ADDRESS);
    Wire.write(reg);
    Wire.write(value);
    return Wire.endTransmission() == 0;
}

bool readRegister(uint8_t reg, uint8_t &value) {
    Wire.beginTransmission(OB1203_ADDRESS);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0 || Wire.requestFrom(OB1203_ADDRESS, (uint8_t)1) != 1) {
        return false;
    }
    value = Wire.read();
    return true;
}

bool readPpgSample(uint32_t &sample) {
    Wire.beginTransmission(OB1203_ADDRESS);
    Wire.write(REG_FIFO_DATA);
    if (Wire.endTransmission(false) != 0 || Wire.requestFrom(OB1203_ADDRESS, (uint8_t)3) != 3) {
        return false;
    }
    sample = (uint32_t)Wire.read();
    sample |= (uint32_t)Wire.read() << 8;
    sample |= (uint32_t)Wire.read() << 16;
    return true;
}

void updateBpm(uint32_t raw, uint32_t now) {
    if (ppgSamplesSeen == 0) ppgBaseline = (float)raw;
    ppgBaseline += 0.05f * ((float)raw - ppgBaseline);
    const float ac = (float)raw - ppgBaseline;

    ppgWindow[ppgWindowIndex] = ac;
    ppgWindowIndex = (ppgWindowIndex + 1) % PPG_WINDOW_SIZE;
    if (ppgSamplesSeen < PPG_WINDOW_SIZE) ++ppgSamplesSeen;
    if (ppgSamplesSeen < PPG_WINDOW_SIZE) return;

    float minAC = ppgWindow[0], maxAC = ppgWindow[0];
    for (size_t i = 1; i < PPG_WINDOW_SIZE; ++i) {
        if (ppgWindow[i] < minAC) minAC = ppgWindow[i];
        if (ppgWindow[i] > maxAC) maxAC = ppgWindow[i];
    }
    const float amplitude = maxAC - minAC;
    const bool above = ac > (minAC + amplitude * 0.60f);
    if (amplitude > 10.0f && above && !previousAboveThreshold) {
        if (lastBeatMs != 0) {
            const uint32_t interval = now - lastBeatMs;
            if (interval >= 300 && interval <= 2000) {
                const float newBpm = 60000.0f / interval;
                heartRateBpm = heartRateBpm == 0.0f ? newBpm : 0.7f * heartRateBpm + 0.3f * newBpm;
            }
        }
        lastBeatMs = now;
    }
    previousAboveThreshold = above;
}

void resetStressVotes() {
    stressPredictionCount = 0;
    stressPredictionIndex = 0;
    stressedVoteCount = 0;
}

void updateStressVotes(uint32_t raw) {
    if (raw < MIN_VALID_PPG) {
        resetStressVotes();
        return;
    }

    const uint8_t prediction = (uint8_t)ppg_stress_predict((float)raw);
    if (stressPredictionCount == STRESS_VOTE_WINDOW) {
        if (stressPredictions[stressPredictionIndex] == PPG_STRESS_STRESSED) {
            --stressedVoteCount;
        }
    } else {
        ++stressPredictionCount;
    }

    stressPredictions[stressPredictionIndex] = prediction;
    if (prediction == PPG_STRESS_STRESSED) ++stressedVoteCount;
    stressPredictionIndex = (stressPredictionIndex + 1) % STRESS_VOTE_WINDOW;
}

const char *stressStatus(uint32_t nowMs) {
    if (lastPpgSampleMs == 0 || nowMs - lastPpgSampleMs > 1000) return "NO_PPG";
    if (lastPpgRaw < MIN_VALID_PPG) return "NO_FINGER";
    if (stressPredictionCount < STRESS_VOTE_WINDOW) return "WARMING";
    return stressedVoteCount > (STRESS_VOTE_WINDOW / 2) ? "STRESSED" : "RELAX";
}

// MCP3201 (12-bit ADC tren GSR Click), SPI mode 0
uint16_t readGsrSpi() {
    gsrSpi.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));
    digitalWrite(PIN_GSR_CS, LOW);
    const uint8_t b0 = gsrSpi.transfer(0x00);
    const uint8_t b1 = gsrSpi.transfer(0x00);
    digitalWrite(PIN_GSR_CS, HIGH);
    gsrSpi.endTransaction();
    return ((((uint16_t)(b0 & 0x1F)) << 8) | b1) >> 1;
}

void setup() {
    Serial.begin(115200);
    delay(1000);

    // Khoi tao I2C + OB1203 truoc (giong code goc), GSR sau cung
    Wire.begin(PIN_SDA, PIN_SCL);
    Wire.setClock(100000);

    bool found = false;
    for (int attempt = 0; attempt < 5 && !found; ++attempt) {
        Wire.beginTransmission(OB1203_ADDRESS);
        found = (Wire.endTransmission() == 0);
        if (!found) delay(200);
    }
    if (!found) {
        Serial.println("# ERROR: OB1203 not found at 0x53. Check 3V3, GND, SDA, SCL.");
        return;
    }

    bool ok = writeRegister(REG_MAIN_CTRL_0, 0x80);  // reset
    delay(100);
    ok &= writeRegister(REG_MAIN_CTRL_1, 0x03);
    ok &= writeRegister(REG_INT_CFG_1, 0x10);
    ok &= writeRegister(REG_PPG_PS_GAIN, 0x09);
    ok &= writeRegister(REG_PPG_AVG, 0x5A);
    ok &= writeRegister(REG_PPG_PWIDTH_PERIOD, 0x42);
    ok &= writeRegister(REG_PPG_IRLED_CURR_0, 0xCD);
    ok &= writeRegister(REG_PPG_IRLED_CURR_0 + 1, 0x00);
    if (!ok) {
        Serial.println("# ERROR: OB1203 configuration failed.");
        return;
    }

    // GSR Click: SPI (MCP3201) + ADC chan AN
    pinMode(PIN_GSR_CS, OUTPUT);
    digitalWrite(PIN_GSR_CS, HIGH);
    gsrSpi.begin(PIN_GSR_SCK, PIN_GSR_MISO, -1, PIN_GSR_CS);
    analogReadResolution(12);
    analogSetPinAttenuation(PIN_GSR_AN, ADC_11db);
                                
    sensorReady = true;
    Serial.println("# OB1203 + GSR ready");
    Serial.println("t_ms,ppg_raw,ppg_new,gsr_spi,gsr_adc,gsr_mv,bpm_est,stress_state");
    startMs = millis();
    nextTickUs = micros();
}

void loop() {
    if (!sensorReady) {
        delay(1000);
        return;
    }

    // Cho den tick tiep theo (giu 50 Hz on dinh)
    if ((int32_t)(micros() - nextTickUs) < 0) return;
    nextTickUs += SAMPLE_PERIOD_US;

    const uint32_t nowMs = millis();

    // PPG: doc het cac mau san sang (toi da vai mau), giu mau moi nhat
    uint8_t ppgNew = 0;
    uint8_t status = 0;
    for (uint8_t i = 0; i < 4; ++i) {
        if (!readRegister(REG_STATUS_1, status) || !(status & PPG_DATA_READY)) break;
        uint32_t raw;
        if (!readPpgSample(raw)) break;
        lastPpgRaw = raw;
        lastPpgSampleMs = nowMs;
        ppgNew = 1;
        updateBpm(raw, nowMs);
    }

    // Match the row-level training input: classify each 50 Hz row.
    // Repeated held PPG values are included as they were in the training CSVs.
    if (lastPpgSampleMs != 0 && nowMs - lastPpgSampleMs <= 1000) {
        updateStressVotes(lastPpgRaw);
    } else {
        resetStressVotes();
    }
    // GSR: trung binh nhieu mau de giam nhieu
    uint32_t spiSum = 0, adcSum = 0;
    for (uint8_t i = 0; i < GSR_OVERSAMPLE; ++i) {
        spiSum += readGsrSpi();
        adcSum += analogRead(PIN_GSR_AN);
    }
    const uint16_t gsrSpi12 = spiSum / GSR_OVERSAMPLE;
    const uint16_t gsrAdc12 = adcSum / GSR_OVERSAMPLE;
    const float gsrMv = gsrSpi12 * 3300.0f / 4095.0f;

    const float bpm = (heartRateBpm > 0.0f && lastBeatMs != 0 && nowMs - lastBeatMs < 3000)
                          ? heartRateBpm : 0.0f;

    Serial.printf("%lu,%lu,%u,%u,%u,%.1f,%.1f,%s\n",
                  (unsigned long)(nowMs - startMs), (unsigned long)lastPpgRaw, ppgNew,
                  gsrSpi12, gsrAdc12, gsrMv, bpm, stressStatus(nowMs));
}



