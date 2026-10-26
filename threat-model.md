# Threat Model — Physiological Deception Detection

## 1. Asset
- **Physiological data:** Heart rate (PPG), skin conductance (EDA/GSR), respiration, and temperature recordings.
- **Participant information:** Truthful/deceptive labels and any information that could identify participants.
- **Machine-learning model:** Trained model weights, extracted features, and experimental results.
- **Credentials:** Passwords, API keys, and database credentials used by the data-processing application.

## 2. Threat
- **Hardcoded secrets:** Credentials stored in source code could be exposed through the team repository, giving unauthorized users access to the application or database.
- **Debug output:** Raw physiological recordings or participant information could be exposed through application logs or USB/UART serial consoles.
- **Trusting all input:** Invalid or malicious sensor readings and dataset files could disrupt processing or compromise data integrity.
- **Insecure updates:** Outdated software, dependencies, or programmable sensor firmware could contain exploitable vulnerabilities.
- **Physical access:** Someone with access to an ESP32 could potentially read unencrypted flash memory and extract firmware, model data, or embedded secrets.
- **Model misuse:** Predictions could be misinterpreted as definitive evidence of deception, leading to unfair judgments about participants.

## 3. Response
- **Protect secrets:** Keep credentials out of source code and Git. Store them in environment variables or a suitable secret manager, and restrict access to the database.
- **Secure debug output:** Avoid printing sensitive physiological recordings, credentials, or identifying information to logs and serial consoles.
- **Validate input:** Check sensor readings, data types, expected ranges, file formats, and dataset labels before passing them to the machine-learning pipeline.
- **Secure updates:** Regularly update software dependencies and programmable sensor firmware using trusted sources. If firmware updates are supported, use signed updates where practical.
- **Data-at-rest encryption:** Encrypt sensitive data stored on the computer or other storage medium when appropriate. Protect encryption keys separately from the encrypted data.
- **Flash encryption:** If the final system uses an ESP32 and physical access to the device is a realistic threat, consider flash encryption to protect firmware and stored data against unauthorized flash extraction.
- **Secure boot:** If the system is deployed on an ESP32, consider secure boot to prevent unauthorized or modified firmware from running.
- **Protect participant privacy:** Obtain informed consent, use participant IDs instead of names, collect only necessary data, and restrict access to recordings.
- **Limit model misuse:** Clearly document the model's limitations. Physiological responses can be affected by stress, movement, and individual differences, so the system is intended for research and educational purposes only, not as definitive evidence of deception or for consequential decisions about individuals.

- AI use: help with ideas and wording

These measures are proportionate to our research prototype. We will prioritize secure credential handling, privacy-conscious logging, input validation, and software updates. Flash encryption and secure boot will be considered if the final hardware configuration and physical-access risks justify them, because enabling these ESP32 protections involves permanent eFuse changes that cannot simply be undone.
