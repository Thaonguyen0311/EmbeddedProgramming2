# Platform Decision – Stress Detector

## Platform Selection

**We use ESP32-S3 because** our stress detector requires real-time physiological data acquisition, lightweight machine learning inference, low power consumption, and standalone operation. The ESP32-S3 supports both our PPG (OB1203) and GSR (MCP3201) sensors through I²C, SPI and ADC interfaces, allowing us to collect and process physiological signals on one embedded device without requiring a separate computer.

## Project Requirements and Measurements

Our current prototype has the following configuration:

- **Microcontroller:** ESP32-S3 DevKitC-1
- **PPG sensor:** Heart Rate 11 Click (OB1203), I²C
- **Data output:** 115200 baud serial communication
- **Firmware output interval:** 20 ms (50 rows per second)
- **PPG processing window:** 80 samples (approximately 1.6 seconds at the current output interval)

## Why ESP32-S3?

1. **Real-time processing:** It can collect PPG and GSR signals and perform local stress classification.
2. **Low power:** It is more suitable for a portable, wearable stress detector than a Raspberry Pi running a full operating system.
3. **Hardware compatibility:** It already supports our sensor interfaces, including I²C, SPI and ADC.
4. **Standalone operation:** It can process data and trigger an action without requiring a PC or internet connection.
5. **Cost and size:** Its compact form factor is suitable for a small embedded prototype.

## Current Limitation

The machine learning model must be optimized for embedded deployment. Our current Random Forest implementation is too large to embed directly in the firmware, so we need to evaluate smaller models and measure their classification accuracy, RAM usage, Flash usage and inference time on the ESP32-S3.

## Conclusion

The ESP32-S3 is the most suitable platform for our current prototype because it already supports our sensors and meets the requirements for local, real-time embedded processing. Final model deployment will depend on achieving an acceptable balance between classification accuracy, memory consumption and inference latency.
