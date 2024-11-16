# Phone Visualizer Documentation

The **Phone Visualizer** is a Unity-based application designed to provide an Augmented Reality (AR) experience by visualizing game states and player interactions. It consists of three main modules, each built using C# scripts, and each module is further divided into smaller scripts for specific functionalities.

---

## Modules Overview

### 1. **User Interface Module**
- **Description**: 
  - Handles the main User Interface (UI) of the game, displaying players' stats on the screen, such as health, shield, and other gameplay details.
  - Composed of multiple smaller C# scripts, each responsible for a specific UI component.
- **Responsibilities**:
  - Updates player statistics dynamically.
  - Ensures seamless integration of UI elements during gameplay.

---

### 2. **Game State Module**
- **Description**:
  - Manages the overall game state of the Phone Visualizer.
  - Facilitates communication with the game engine running on the Ultra96 board using the **MQTT protocol**.
- **Responsibilities**:
  - Synchronizes game state data between the phone and the Ultra96 game engine.
  - Handles message parsing and response handling for seamless interaction.

---

### 3. **Vuforia Image Target Module**
- **Description**:
  - Manages Vuforia library API calls to detect image targets.
  - Controls the AR effects and animations within the Visualizer.
- **Responsibilities**:
  - Anchors AR elements (e.g., rain bombs, goals) to image targets.
  - Ensures smooth AR transitions and interactions during gameplay.

---

