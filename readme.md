# Phone Visualizer Documentation

The **Phone Visualizer** is a Unity-based application designed to provide an Augmented Reality (AR) experience by visualizing game states and player interactions. It consists of three main modules, each built using C# scripts, and each module is further divided into smaller scripts for specific functionalities.


Note: Only the C# scripts are uploaded onto Github, for the full Unity game project see the following google drive link.


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

## Build and Installation Instructions

### Downloading the Unity Project
1. Clone or download the Unity project repository from the provided link: https://drive.google.com/file/d/16tEO5thFZL0QfijFLYbk4o-zJX1wIwLa/view?usp=sharing
2. Open the project in Unity Hub.
3. Ensure all necessary Unity packages are installed (e.g., Vuforia Engine).
4. Verify that the project opens correctly in Unity.

---

### Building for Android
1. **Switch Platform**:
   - Open Unity.
   - Go to `File > Build Settings`.
   - Select **Android** and click `Switch Platform`.
   
2. **Install Android Build Support**:
   - In Unity Hub, ensure that **Android Build Support** is installed, including SDK, NDK, and OpenJDK.

3. **Configure Build Settings**:
   - Go to `File > Build Settings`.
   - Under **Scenes in Build**, ensure all required scenes are checked.
   - Click on **Player Settings**:
     - Set the **Package Name** (e.g., `com.yourcompany.yourproject`).
     - Select the **Minimum API Level** (e.g., API Level 21 or higher).
     - Set the **Target API Level** (match your Android device's version)
    - **Note**: Player Settings heavily depend on the phone you are building for. If errors occur during the build process, check the debug console for detailed messages and adjust Player Settings accordingly.

4. **Connect Android Device**:
   - Enable **Developer Mode** on the Android device.
   - Turn on **USB Debugging**.
    - Turning on USB Debug mode heavily depends on your specific android phone, it commonly requires you to Tap "About Device" or "Aboue Phone" multiple times

5. **Build and Deploy**:
   - In Unity, click **Build and Run**.
   - Select a folder to save the `.apk` file.
   - Unity will build and deploy the app to the connected Android device.

---

### Building for iOS
1. **Switch Platform**:
   - Go to `File > Build Settings`.
   - Select **iOS** and click `Switch Platform`.

2. **Build**:
   - Click **Build** to generate the Xcode project.

3. **Open Xcode Project**:
   - Navigate to the folder where the Unity build was saved.
   - Open the `.xcodeproj` file in Xcode.

4. **Configure Signing and Capabilities**:
   - In Xcode, go to **Signing & Capabilities**.
   - Ensure **All** is selected.
   - Tick **Automatically manage signing**.
   - Under **Team**, select your name (use the Personal Team option if applicable).

5. **Set Bundle Identifier**:
   - Create and set a unique Bundle Identifier.

6. **Connect iPhone**:
   - Connect the iPhone to the MacBook via USB.
   - Ensure **Developer Mode** is enabled on the iPhone.

7. **Build and Deploy**:
   - Click **Build** in Xcode to compile the app.
   - The app will automatically install on the connected iPhone.

