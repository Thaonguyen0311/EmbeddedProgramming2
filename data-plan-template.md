# Data plan — Wristband Physiological State Detection

**Team:** Thao Nguyen, Soen Wu

## Sensor

Our finished device will be a wristband using a **heart-rate sensor** and a **skin-conductivity (EDA/GSR) sensor**. We will train the model using the same sensors that will be used in the final wristband.

## Classes

The device should distinguish between:

* **resting / normal state** — nothing unusual happening
* **lying down** — the person is lying down and relaxed
* **active / stressed state** — the person is moving or experiencing increased physiological activity

Including the resting/normal class is important because the wristband will spend much of its time in this state.

## Collection

Both team members will record data for each class. We will collect multiple recordings per class under different conditions, including different people, sitting/standing positions, movement levels, and recording sessions.

We will aim for at least **20 recordings per class**, with each recording lasting approximately **30–60 seconds**.

We will keep some recordings from each person and session aside as **test data**. These recordings will not be used during training.

## Risk

The two classes most likely to be confused are **resting / normal state** and **lying down**, because both can produce similar heart-rate and skin-conductivity measurements when the person is relaxed.

Another possible confusion is **resting / normal state** and **active / stressed state**, because heart rate and skin conductivity can vary between people and can be affected by factors other than the intended activity.

## Waiting for

We are waiting for the heart-rate and skin-conductivity sensors to be available before starting the final data collection.
