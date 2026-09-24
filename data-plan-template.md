# Data Plan — Physiological Deception Detection

**Team:** Thao Nguyen, Seonmi Wu

## Objective

The goal of this project is to investigate whether physiological signals can be used to distinguish between **truthful and deceptive responses**.

The system will collect physiological measurements while a participant answers questions or performs tasks under two conditions:

* **Truthful** — the participant provides a truthful answer.
* **Deceptive** — the participant intentionally provides a false answer.

The collected signals will then be used to train and evaluate a machine-learning model for **truthful vs. deceptive classification**.

> **Note:** The system is intended as an experimental deception-classification system. Physiological responses can also be affected by stress, movement, cognitive effort, and other factors, so the model should not be interpreted as a general-purpose lie detector.

## Sensors

We are considering the following physiological sensors:

1. **PPG** → heart rate / heart-rate variability
2. **EDA/GSR** → skin conductance and sympathetic arousal
3. **Respiration sensor** → breathing rate and breathing pattern
4. **Temperature sensor** → peripheral/skin temperature

### Alternative: Nose-mounted measurement

Instead of placing all sensors on a wristband, some measurements could be collected from the **nose or facial area**, particularly temperature and respiration-related signals.

A nose-mounted or facial sensor could potentially provide:

* **Nose temperature**
* **Respiration**
* Other physiological measurements depending on the selected hardware

This approach is relevant because existing deception datasets include measurements such as **nose temperature, heart-rate response, EDA, and respiratory depth**.

## Classes

The system will distinguish between two classes:

| Class         | Description                                              |
| ------------- | -------------------------------------------------------- |
| **Truthful**  | The participant provides a truthful response.            |
| **Deceptive** | The participant intentionally provides a false response. |

The target classification is therefore:

```text
Physiological signals
        ↓
PPG + EDA + Respiration + Temperature
        ↓
Feature extraction
        ↓
Machine-learning model
        ↓
┌──────────────┬──────────────┐
│   Truthful   │  Deceptive   │
└──────────────┴──────────────┘
```

## Data Collection

Both team members will record data for both classes.

For each participant, we will collect multiple recordings under different questions and recording sessions. Each recording will contain a known ground-truth label indicating whether the response was **truthful or deceptive**.

We will aim for at least **20 recordings per class**, with each recording lasting approximately **30–60 seconds**.

To reduce overfitting to individual participants, the dataset should include recordings from different people and multiple recording sessions.

Where possible, we will also vary:

* Questions
* Recording sessions
* Response content
* Body position
* Normal movement conditions

## Train / Test Split

Some recordings from each participant and session will be kept aside as **test data**.

These recordings will **not be used during training**.

Ideally, some participants should be completely excluded from the training data and used only for testing. This will help evaluate whether the model can generalize to a person it has not seen during training.

```text
Participants
      │
      ├── Training participants
      │       └── Truthful + Deceptive
      │
      └── Test participants
              └── Truthful + Deceptive
```

## Risk and Challenges

The main challenge is that physiological responses are not unique to deception.

For example, a person may experience increased heart rate or skin conductance because of:

* Nervousness
* Stress
* Surprise
* Cognitive effort
* Movement
* The difficulty of the question

Therefore, the model may confuse **truthful responses with deceptive responses** when both produce similar physiological reactions.

Another challenge is the variation between individuals. Different people can have very different baseline heart rates, skin conductance levels, respiration patterns, and temperature.

To address this, we will collect data from multiple people and recording sessions and investigate appropriate normalization and feature-extraction methods.

## Existing Dataset

We will also investigate publicly available deception datasets containing explicit **truthful/control and deceptive/test conditions**.

For example, the dataset currently being examined contains physiological features including:

* EDA response
* Heart-rate response
* HR deceleration
* Nose temperature
* Respiratory depth
* Pupil response

The dataset contains a `Condition` field with **Control** and **Test** classes.

These existing data can potentially be used to develop and evaluate the classification approach before collecting our own sensor data.

## Waiting For

We are currently waiting for the **PPG and EDA sensors** to become available before starting the final data-collection phase.

After the sensors are available, we will finalize the hardware configuration and determine whether the system will use a **wristband configuration, a nose/facial sensor configuration, or a combination of both**.
