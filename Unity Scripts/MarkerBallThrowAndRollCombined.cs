using UnityEngine;
using Vuforia;
using TMPro;  // For TextMeshPro UI
using UnityEngine.UI;  // For UI Button
using System.Collections.Generic;
using System.Collections;





/*
    This script is in charge of interacting with the Vuforia's API, and realizing the AR effects in the project
*/

public class MarkerBallThrowAndRollCombined : MonoBehaviour
{
    // Prefabs and properties for arc launch
    public GameObject basketballPrefab;  // Reference to the basketball prefab
    public GameObject volleyballPrefab;  // Reference to the volleyball prefab
    public GameObject bombPrefab;  // Reference to the bomb prefab
    public float basketballMoveSpeed = 5f;  // Speed at which the basketball moves toward the target
    public float basketballArcHeight = 1f;  // Maximum height of the basketball arc
    public float volleyballMoveSpeed = 7f;  // Speed at which the volleyball moves toward the target
    public float volleyballArcHeight = 1.5f;  // Maximum height of the volleyball arc
    public float bombMoveSpeed = 3f;  // Speed at which the bomb moves toward the target
    public float bombArcHeight = 0.5f;  // Maximum height of the bomb arc

    // Prefabs and properties for ground roll
    public GameObject soccerPrefab;  // Reference to the soccer prefab
    public GameObject bowlingBallPrefab;  // Reference to the bowling ball prefab
    public float soccerMoveSpeed = 4f;  // Speed for soccer
    public float bowlingBallMoveSpeed = 2f;  // Speed for bowling ball
    public float soccerSpinSpeed = 360f;  // Spin speed for soccer
    public float bowlingBallSpinSpeed = 120f;  // Spin speed for bowling ball

    // Shared properties
    public float spinSpeed = 360f;  // Speed of spinning (degrees per second) for arc launch
    public Camera arCamera;  // Reference to the AR Camera (Vuforia AR Camera)
    public GameObject imageDetectionText;  // Reference to a UI element to show when the marker is detected
    public TextMeshProUGUI hitText;  // Reference to a UI Text element to display when the marker is detected
    public TextMeshProUGUI infoText;  // Reference to a UI Text element to display information messages

    // UI Buttons for launching balls
    public Button basketballButton;  // Reference to the basketball button
    public Button volleyballButton;  // Reference to the volleyball button
    public Button bombButton;  // Reference to the bomb button
    public Button soccerButton;  // Reference to the soccer button
    public Button bowlingBallButton;  // Reference to the bowling ball button

    private ObserverBehaviour observerBehaviour;  // Reference to handle image target events
    private bool is_other_player_visible = false;  // Track if the other player's image target is visible
    private GameObject currentBall;  // Reference to the current ball instance

    public GameObject trackingRectangle;  // Reference to the rectangle UI element to follow the marker
    private RectTransform rectTransform;  // RectTransform of the UI panel
    
    // Fields for ground and ball positioning
    public float soccerGroundDistance = 0.4f; // Distance from the AR camera to the ground for soccer
    public float soccerInitialDistance = 1.0f; // Distance in front of the player where the soccer ball spawns
    public float bowlingBallGroundDistance = 0.3f; // Distance from the AR camera to the ground for bowling ball
    public float bowlingBallInitialDistance = 1.5f; // Distance in front of the player where the bowling ball spawns
    public float maxGroundDistance = 1.0f; // Maximum ground distance when the target is close
    public float minGroundDistance = 0.1f; // Minimum ground distance when the target is far

    // Fields for managing selected prefab and its properties
    private GameObject selectedPrefab;  // Currently selected ball prefab
    private float currentMoveSpeed;  // Current speed of the moving ball
    private float currentArcHeight;  // Current arc height of the moving ball (for arc launch)
    private float currentGroundDistance;  // Current ground distance (for ground roll)
    private float currentInitialDistance;  // Current initial distance (for ground roll)
    private float currentSpinSpeed;  // Current spin speed (for ground roll)

    [Header("Default Target Position Settings")]
    public float defaultTargetDistance = 10f;  // Default distance away from the camera when marker is not detected

    private Vector3 defaultTargetPosition;  // Default target position when marker is not detected

    public Sprite shieldSprite;
    public Sprite crosshairSprite;

    public GameState gameState;

    public GameObject anchorStage; // Reference to the AnchorStage GameObject

    public GameObject rainBombPrefab;  

    public GameObject hoopPrefab;
    private GameObject currentHoop;  // Reference to the currently instantiated hoop

    private float lastOverlapTime = -3f;  // To store the last time the function was called (-3f to allow immediate first call)
    public float cooldownDuration = 3f;  // Duration of the cooldown (3 seconds)
    public float textDisplayDuration = 2f;  // How long the damage text will be displayed
    private float damageTextStartTime = 0f;  // When the damage text was set


    public GameObject soccerGoalPrefab;  // Reference to the soccer goal prefab
    private GameObject currentSoccerGoal;  // Reference to the currently instantiated soccer goal
    public float soccerGoalOffset = -1.0f;


    public float heightOffset = 0f;

    public TextMeshProUGUI rainHitText;

    // A list to keep track of the instantiated balls
    List<GameObject> rainBombList = new List<GameObject>();


    public GameObject bowlingPinPrefab;  // Reference to the bowling pin prefab
    private List<GameObject> currentBowlingPins = new List<GameObject>();  // To keep track of the instantiated pins
    public float bowlingPinSpacing = 0.2f;
    public float minBowlingPinHitForce = 1f;
    public float maxBowlingPinHitForce = 3f;
    public float ballRollGroundScale = 0f; // set to zero for now


    public RectTransform crosshairDebugRect;  // Assign the UI Image for the crosshair in the Inspector
    public RectTransform ballDebugRect;       // Assign the UI Image for the ball in the Inspector
    public bool debugVisualization = true;    // Toggle to enable/disable visualization

    // Variables for crosshair and ball rectangle sizes
    public float crosshairWidth = 200f;  // Adjustable width of crosshair rectangle
    public float crosshairHeight = 200f; // Adjustable height of crosshair rectangle
    public float ballWidth = 1200f;       // Adjustable width of ball rectangle
    public float ballHeight = 1800f;      // Adjustable height of ball rectangle

     // Add a coroutine variable to keep track of the "marker lost" coroutine
    private Coroutine markerLostCoroutine;  


    public TextMeshProUGUI rainBombDebugText;

    public Button rainBombHitDebugButton;

   



    /* ############################ START OF OPPONENT DETECTION CODE ############################ */

    private void OnTargetStatusChanged(ObserverBehaviour observer, TargetStatus targetStatus)
    {
        if (targetStatus.Status == Status.TRACKED)
        {
            OnMarkerDetected();
        }
        else
        {
            OnMarkerLost();
        }
    }



        

    /*
        MarkerLostCoroutine here serves as a safeguard. When players lose sight of their opponent, it is often bcs of them swinging the phones around and losing the image target,
        in order to fully register that a marker is lost, the marker has to be lost for 3 seconds. 
    */
    private void OnMarkerDetected()
    {
        // If the marker lost coroutine is running, stop it
        if (markerLostCoroutine != null)
        {
            StopCoroutine(markerLostCoroutine);
            markerLostCoroutine = null;
        }

        // Set all anchored balls to active when the marker is detected
        SetBallPrefabsActive(true);

        is_other_player_visible = true;

        if (imageDetectionText != null)
        {
            imageDetectionText.SetActive(true);
        }

        if (infoText != null)
        {
            infoText.text = "Marker detected.";
            infoText.gameObject.SetActive(true);
        }

        Debug.Log("Marker detected.");
    }

    private void OnMarkerLost()
    {
        // Start the coroutine to wait and confirm marker lost
        if (markerLostCoroutine == null)
        {
            markerLostCoroutine = StartCoroutine(WaitAndConfirmMarkerLost());
        }
    }

    private IEnumerator WaitAndConfirmMarkerLost()
    {
        // Wait for the specified delay (e.ga., 2 seconds)
        yield return new WaitForSeconds(2.0f);

        // After the delay, confirm the marker is lost
        SetBallPrefabsActive(false);
        is_other_player_visible = false;

        if (imageDetectionText != null)
        {
            imageDetectionText.SetActive(false);
        }
        if (hitText != null)
        {
            hitText.gameObject.SetActive(false);
        }

        if (infoText != null)
        {
            infoText.text = "Marker not detected.";
            infoText.gameObject.SetActive(true);
        }

        Debug.Log("Marker lost.");

        // Clear the coroutine variablea
        markerLostCoroutine = null;
    }


    void Update()
    {
        if (observerBehaviour != null && observerBehaviour.TargetStatus.Status == Status.TRACKED)
        {
            trackingRectangle.SetActive(true);
            Vector3 screenPos = arCamera.WorldToScreenPoint(transform.position);
            Debug.Log("Screen Position: " + screenPos);

            if (screenPos.z > 0)
            {
                screenPos.x = Mathf.Clamp(screenPos.x, 0, Screen.width);
                screenPos.y = Mathf.Clamp(screenPos.y, 0, Screen.height);
                rectTransform.position = screenPos;

                Debug.Log("Crosshair Position Updated: " + rectTransform.position);
            }
            else
            {
                trackingRectangle.SetActive(false);
                Debug.Log("Marker is behind the camera, hiding crosshair.");
            }


            // Check if the crosshair overlaps with any of the anchored balls
            CheckForBallOverlap();
        }
        else
        {
            trackingRectangle.SetActive(false);
            Debug.Log("Marker not tracked, hiding crosshair.");
        }

        // Continuously update the default target position in case the camera moves
        UpdateDefaultTargetPosition();


        // Hide rain damage text after the display duration is over
        if (rainHitText.gameObject.activeSelf && (Time.time - damageTextStartTime >= textDisplayDuration))
        {
            rainHitText.gameObject.SetActive(false);
        }
    }




    public void ClearRainBombList()
    {
        // Iterate through each GameObject in the rainBombList
        foreach (GameObject rainBomb in rainBombList)
        {
            if (rainBomb != null)
            {
                Destroy(rainBomb);  // Destroy each rain bomb object in the scene
            }
        }

        // Clear the list after all objects are destroyed
        rainBombList.Clear();
        Debug.Log("Rain bomb list cleared.");
    }

    





    void Start()
    {
        // Initialize components and UI elements
        observerBehaviour = GetComponent<ObserverBehaviour>();
        rectTransform = trackingRectangle.GetComponent<RectTransform>();

        if (observerBehaviour != null)
        {
            observerBehaviour.OnTargetStatusChanged += OnTargetStatusChanged;
        }
        else
        {
            Debug.LogError("ObserverBehaviour component is missing on this GameObject.");
        }

        if (imageDetectionText != null)
        {
            imageDetectionText.SetActive(false);
        }
        if (hitText != null)
        {
            hitText.gameObject.SetActive(false);
        }
        if (infoText != null)
        {
            infoText.gameObject.SetActive(false);
        }

        // // Assign button functionality for arc launch
        // Not needed as now we wait for game engine to tell us
        if (basketballButton != null)
        {
            basketballButton.onClick.AddListener(() => OnShootArcButtonPressed(basketballPrefab, basketballMoveSpeed, basketballArcHeight));
        }
        if (volleyballButton != null)
        {
            volleyballButton.onClick.AddListener(() => OnShootArcButtonPressed(volleyballPrefab, volleyballMoveSpeed, volleyballArcHeight));
        }
        if (bombButton != null)
        {
            bombButton.onClick.AddListener(() => OnShootArcButtonPressed(bombPrefab, bombMoveSpeed, bombArcHeight));
        }

        // Assign button functionality for ground roll
        if (soccerButton != null)
        {
            soccerButton.onClick.AddListener(() => OnShootGroundButtonPressed(soccerPrefab, soccerGroundDistance, soccerInitialDistance, soccerMoveSpeed, soccerSpinSpeed));
        }
        if (bowlingBallButton != null)
        {
            bowlingBallButton.onClick.AddListener(() => OnShootGroundButtonPressed(bowlingBallPrefab, bowlingBallGroundDistance, bowlingBallInitialDistance, bowlingBallMoveSpeed, bowlingBallSpinSpeed));
        }

        // Set the default target position for when the marker is not detected
        UpdateDefaultTargetPosition();


        rainBombHitDebugButton.onClick.AddListener(CheckRainBombHits);
    }

    private void CheckRainBombHits()
    {
        // Call the function and get the hit count
        int hitCount = isRainBombsHittingOpponent();

        // Update the TextMeshPro text to show the hit count
        rainBombDebugText.text = "Number of rain bomb hit count: " + hitCount;
    }


    

    // ################### START OF THROWING OF BALL IN AN ARC #######################

    private void OnShootArcButtonPressed(GameObject prefab, float moveSpeed, float arcHeight)
    {

        
        selectedPrefab = prefab;
        currentMoveSpeed = moveSpeed;
        currentArcHeight = arcHeight;

        if (is_other_player_visible)
        {
            Debug.Log("[Showcase1] AR Script: Ball button pressed with marker detected.");
            Debug.Log("AR Script: Damaging enemy player now");

            if (selectedPrefab == rainBombPrefab) 
            {
                gameState.takeDamageOpponent(5);
            }
            else // for every other action is 10 hp
            {
                gameState.takeDamageOpponent(10);
            }

            if (selectedPrefab == basketballPrefab)
            {
                Debug.Log("[Showcase1] AR Script: generating hoop.");
                GenerateHoop();  // Generate the hoop when basketball is selected
            }

            LaunchBallInArc(transform.position);
        }
        else
        {
            // No damage taken
            Debug.Log("Shoot button pressed without marker detected.");
            LaunchBallInArc(defaultTargetPosition);
        }
    }


    // ################### END OF THROWING OF BALL IN AN ARC #######################


    private void GenerateHoop()
    {
       
        // Destroy any existing hoop before creating a new one
        if (currentHoop != null)
        {
            Destroy(currentHoop);
            currentHoop = null;
            Debug.Log("Existing hoop destroyed before generating a new one.");
        }


        Vector3 hoopPosition = transform.position;  // Use the same position as the image target
        Debug.Log("[Showcase1] AR Script: generating hoop prefab.");
        currentHoop = Instantiate(hoopPrefab, hoopPosition, Quaternion.identity);
        currentHoop.transform.SetParent(null, true);  // This ensures it retains its world position and isn't affected by any parent

        // Assign the AR camera to the AITargetsScript on the hoop prefab
        AITargetsScript targetsScript = currentHoop.GetComponent<AITargetsScript>();
        if (targetsScript != null)
        {
            targetsScript.arCamera = arCamera;  // Set the camera reference
        }
        

        // Align the hoop's TargetPoint1 to match the image target's position
        Transform targetPoint1 = currentHoop.transform.Find("TargetPoint1");
        if (targetPoint1 != null)
        {
            targetPoint1.position = hoopPosition;
        }
        
    }

    private void GenerateSoccerGoal()
    {
        // Destroy any existing soccer goal before creating a new one
        if (currentSoccerGoal != null)
        {
            Destroy(currentSoccerGoal);
            currentSoccerGoal = null;
            Debug.Log("Existing soccer goal destroyed before generating a new one.");
        }

         // Calculate the direction vector from the AR camera (player) to the image target
        Vector3 directionFromCameraToTarget = (transform.position - arCamera.transform.position).normalized;

        // Calculate the goal position by moving in the opposite direction (behind the target)
        Vector3 goalPosition = transform.position + directionFromCameraToTarget * soccerGoalOffset;
        Debug.Log("[Showcase1] AR Script: generating soccer goal prefab behind the image target.");
        currentSoccerGoal = Instantiate(soccerGoalPrefab, goalPosition, Quaternion.identity);
        currentSoccerGoal.transform.SetParent(null, true);  // This ensures it retains its world position and isn't affected by any parent


        AITargetsScript targetsScript = currentSoccerGoal.GetComponent<AITargetsScript>();
        if (targetsScript != null)
        {
            targetsScript.arCamera = arCamera;  // Set the camera reference
        }  
    }

   

   private void GenerateBowlingPins(Vector3 basePosition)
    {
        // Destroy existing pins if they exist
        if (currentBowlingPins.Count > 0)
        {
            foreach (var pin in currentBowlingPins)
            {
                if (pin != null)
                {
                    Destroy(pin);
                }
            }
            currentBowlingPins.Clear();  // Clear the list after destroying the pins
            Debug.Log("Existing bowling pins destroyed before generating new ones.");
        }

        // Calculate the center offset to align the triangle formation with the target position
        float centerOffset = bowlingPinSpacing * 1.5f; // Adjust based on the width of your pin arrangement

        // Place the pins in a triangular formation
        for (int i = 0; i < 9; i++)
        {
            Vector3 pinPosition = basePosition;

            // Row 1
            if (i == 0)
            {
                pinPosition += transform.forward * bowlingPinSpacing * 0; // First row
            }
            // Row 2
            else if (i <= 2)
            {
                pinPosition += transform.forward * bowlingPinSpacing + transform.right * ((i - 1) * bowlingPinSpacing - centerOffset);
            }
            // Row 3
            else if (i <= 5)
            {
                pinPosition += transform.forward * bowlingPinSpacing * 2 + transform.right * ((i - 3) * bowlingPinSpacing - centerOffset);
            }
            // Row 4
            else
            {
                pinPosition += transform.forward * bowlingPinSpacing * 3 + transform.right * ((i - 6) * bowlingPinSpacing - centerOffset);
            }

            // Instantiate the pin at the calculated position
            GameObject pin = Instantiate(bowlingPinPrefab, pinPosition, Quaternion.identity);

            // Make the pin face the AR camera
            pin.transform.LookAt(arCamera.transform.position);
            
            // Optionally, you may want to rotate it only around the Y-axis
            pin.transform.rotation = Quaternion.Euler(0, pin.transform.eulerAngles.y, 0);

            // Add the pin to the list
            currentBowlingPins.Add(pin);
        }

        Debug.Log("Bowling pins generated and centered at the target position.");
    }







    private System.Collections.IEnumerator MoveBallInStraightLine(GameObject ball,Vector3 start, Vector3 end, float moveSpeed)
    {
        float elapsedTime = 0f;
        float totalTime = Vector3.Distance(start, end) / moveSpeed;

        while (elapsedTime < totalTime)
        {
            elapsedTime += Time.deltaTime;
            float t = elapsedTime / totalTime;

            ball.transform.position = Vector3.Lerp(start, end, t);
            yield return null;
        }

        ball.transform.position = end;
        OnBallHitMarker(ball, end);  // Continue to the next function after completing the straight line movement
    }


    // Function to shoot the basketball prefab with arc motion
    public void ShootBasketball()
    {
        OnShootArcButtonPressed(basketballPrefab, basketballMoveSpeed, basketballArcHeight);
    }

    // Function to shoot the volleyball prefab with arc motion
    public void ShootVolleyball()
    {
        OnShootArcButtonPressed(volleyballPrefab, volleyballMoveSpeed, volleyballArcHeight);
    }

    // Function to shoot the bomb prefab with arc motion
    public void ShootBomb()
    {
        OnShootArcButtonPressed(bombPrefab, bombMoveSpeed, bombArcHeight);
    }

    // Function to shoot the soccer ball prefab with ground motion
    public void ShootSoccer()
    {
        OnShootGroundButtonPressed(soccerPrefab, soccerGroundDistance, soccerInitialDistance, soccerMoveSpeed, soccerSpinSpeed);
    }

    // Function to shoot the bowling ball prefab with ground motion
    public void ShootBowlingBall()
    {
        OnShootGroundButtonPressed(bowlingBallPrefab, bowlingBallGroundDistance, bowlingBallInitialDistance, bowlingBallMoveSpeed, bowlingBallSpinSpeed);
    }

    

    public void setTrackingToShield()
    {
        // Get the Image component attached to the trackingRectangle GameObject
        UnityEngine.UI.Image imageComponent = trackingRectangle.GetComponent<UnityEngine.UI.Image>();

        if (imageComponent != null && shieldSprite != null)
        {
            // Set the sprite to the new shieldSprite
            imageComponent.sprite = shieldSprite;
        }
        else
        {
            Debug.LogError("Image component or shieldSprite is missing.");
        }
    }
    public void setTrackingToCrossHair()
    {
        // Get the Image component attached to the trackingRectangle GameObject
        UnityEngine.UI.Image imageComponent = trackingRectangle.GetComponent<UnityEngine.UI.Image>();

        if (imageComponent != null && shieldSprite != null)
        {
            // Set the sprite to the new shieldSprite
            imageComponent.sprite = crosshairSprite;
        }
        else
        {
            Debug.LogError("Image component or crosshairSprite is missing.");
        }
    }


    public bool getIsOtherPlayerVisible()
    {
        return is_other_player_visible;
    }

    private void UpdateDefaultTargetPosition()
    {
        defaultTargetPosition = arCamera.transform.position + arCamera.transform.forward * defaultTargetDistance;  // Configurable distance in front of the camera
    }

    private void CheckForBallOverlap()
    {
        if (Time.time - lastOverlapTime < cooldownDuration)
        {
            Debug.Log("Cooldown active, skipping overlap check.");
            return;
        }

        // Get the 2D position and size of the crosshair using adjustable width and height
        Rect crosshairRect = new Rect(
            rectTransform.position.x - (crosshairWidth / 2), 
            rectTransform.position.y - (crosshairHeight / 2), 
            crosshairWidth, 
            crosshairHeight
        );

        // Set the crosshair debug rectangle's position and size
        if (debugVisualization && crosshairDebugRect != null)
        {
            // Position to the center of crosshairRect
            crosshairDebugRect.position = new Vector3(crosshairRect.center.x, crosshairRect.center.y, crosshairDebugRect.position.z);
            crosshairDebugRect.sizeDelta = new Vector2(crosshairRect.width, crosshairRect.height);
        }

        foreach (GameObject ball in rainBombList)
        {
            if (ball != null)
            {
                Vector3 ballScreenPosition = arCamera.WorldToScreenPoint(ball.transform.position);

                if (ballScreenPosition.z > 0)
                {
                    Rect ballRect = new Rect(
                        ballScreenPosition.x - (ballWidth / 2), 
                        ballScreenPosition.y - (ballHeight / 2), 
                        ballWidth, 
                        ballHeight
                    );

                    // Set the ball debug rectangle's position and size
                    if (debugVisualization && ballDebugRect != null)
                    {
                        // Position to the center of ballRect
                        ballDebugRect.position = new Vector3(ballRect.center.x, ballRect.center.y, ballDebugRect.position.z);
                        ballDebugRect.sizeDelta = new Vector2(ballRect.width, ballRect.height);
                    }

                    if (crosshairRect.Overlaps(ballRect))
                    {
                        Debug.Log("Crosshair overlaps with anchored ball on the screen!");
                        lastOverlapTime = Time.time;
                        OnCrosshairOverlapWithBall(ball);
                    }
                }
            }
        }
    }

    private void OnCrosshairOverlapWithBall(GameObject ball)
    {
        // Display the damage message
        rainHitText.text = "Opponent Damaged!";
        rainHitText.gameObject.SetActive(true);
        damageTextStartTime = Time.time;  // Store the current time for text hiding logic

        Debug.Log("[Debug] player walked into rain, doing rain damage!");
        
        // gameState.queueDoRainBombDamage();
    }
    

    public int isRainBombsHittingOpponent()
    {
        int rainBombHitCount = 0;
        // Get the 2D position and size of the crosshair (RectTransform)
        Rect crosshairRect = new Rect(rectTransform.position.x - (rectTransform.rect.width / 2),
                                    rectTransform.position.y - (rectTransform.rect.height / 2),
                                    rectTransform.rect.width,
                                    rectTransform.rect.height);

        // Iterate through each ball in the rainBombList
        foreach (GameObject ball in rainBombList)
        {
            if (ball != null)
            {
                // Convert the 3D world position of the ball to screen position
                Vector3 ballScreenPosition = arCamera.WorldToScreenPoint(ball.transform.position);

                // Check if the ball is in front of the camera (z > 0)
                if (ballScreenPosition.z > 0)
                {
                    // Create a rectangle around the ball's screen position using adjustable width and height
                    Rect ballRect = new Rect(
                        ballScreenPosition.x - (ballWidth / 2), 
                        ballScreenPosition.y - (ballHeight / 2), 
                        ballWidth, 
                        ballHeight
                    );

                    // Check if the crosshair rectangle overlaps with the ball's screen position
                    if (crosshairRect.Overlaps(ballRect))
                    {
                        Debug.Log("Crosshair overlaps with anchored ball on the screen!");

                        // Increment the counter for each overlap
                        rainBombHitCount++;
                    }
                }
            }
        }
        return rainBombHitCount;
    }

    private void SetBallPrefabsActive(bool isActive)
    {
        foreach (GameObject ball in rainBombList)
        {
            if (ball != null)
            {
                ball.SetActive(isActive);
                Debug.Log($"Ball {ball.name} active state set to: {isActive}");
            }
        }
    }

    private void OnShootGroundButtonPressed(GameObject prefab, float groundDistance, float initialDistance, float moveSpeed, float spinSpeed)
    {
        selectedPrefab = prefab;
        currentGroundDistance = groundDistance;
        currentInitialDistance = initialDistance;
        currentMoveSpeed = moveSpeed;
        currentSpinSpeed = spinSpeed;

        if (is_other_player_visible)
        {
            Debug.Log("Shoot button pressed with marker detected.");


            // Check if the soccer ball is selected
            if (selectedPrefab == soccerPrefab)
            {
                GenerateSoccerGoal();  // Generate the soccer goal when the soccer ball is selected
            }

            

            LaunchBallOnGround(transform.position);
        }
        else
        {
            Debug.Log("Shoot button pressed without marker detected.");
            LaunchBallOnGround(defaultTargetPosition);
        }
    }

    private void LaunchBallInArc(Vector3 targetPosition)
    {
        if (selectedPrefab != null)
        {
            Debug.Log("[Showcase1] Launching Ball towards Target.");
            Vector3 spawnPosition = arCamera.transform.position + arCamera.transform.forward * 0.5f;
            GameObject newBall = Instantiate(selectedPrefab, spawnPosition, Quaternion.identity);
            StartCoroutine(MoveBallInArc(newBall, spawnPosition, targetPosition, currentMoveSpeed, currentArcHeight, is_other_player_visible));
        }
        else
        {
            Debug.LogWarning("BallPrefab is not assigned.");
        }
    }

    private System.Collections.IEnumerator MoveBallInArc(GameObject ball ,Vector3 start, Vector3 target, float moveSpeed, float arcHeight, bool do_damage)
    {
        float elapsedTime = 0f;
        float totalTime = Vector3.Distance(start, target) / moveSpeed;

        while (elapsedTime < totalTime)
        {
            elapsedTime += Time.deltaTime;
            float t = elapsedTime / totalTime;

            Vector3 currentPosition = Vector3.Lerp(start, target, t);
            currentPosition.y += arcHeight * Mathf.Sin(Mathf.PI * t);
            ball.transform.position = currentPosition;
            ball.transform.Rotate(Vector3.up, spinSpeed * Time.deltaTime, Space.Self);

            yield return null;
        }

        ball.transform.position = target;

         // Check if the selectedPrefab is the basketballPrefab before moving it through the hoop
        if (selectedPrefab == basketballPrefab)
        {
            StartCoroutine(MoveBallInStraightLine(ball ,target, target + Vector3.down * 0.5f, moveSpeed));  // Move through the hoop
        }
        else
        {
            OnBallHitMarker(ball, target);
        }
    }

    private void LaunchBallOnGround(Vector3 targetPosition)
    {
        if (selectedPrefab != null)
        {
            Vector3 spawnPosition = arCamera.transform.position + arCamera.transform.forward * currentInitialDistance;
            spawnPosition.y -= currentGroundDistance;

            GameObject newBall = Instantiate(selectedPrefab, spawnPosition, Quaternion.identity);

            float distanceToTarget = Vector3.Distance(arCamera.transform.position, targetPosition);
            float targetGroundDistance = CalculateDynamicGroundDistance(distanceToTarget);

            StartCoroutine(MoveBallToTarget(newBall, spawnPosition, targetPosition, targetGroundDistance,is_other_player_visible));
        }
        else
        {
            Debug.LogWarning("Selected ball prefab is not assigned.");
        }
    }

    private float CalculateDynamicGroundDistance(float distanceToTarget)
    {
        float normalizedDistance = Mathf.InverseLerp(0, 10, distanceToTarget); // Adjust '10' as needed for your max distance range
        float dynamicGroundDistance = Mathf.Lerp(maxGroundDistance, minGroundDistance, normalizedDistance);
        return dynamicGroundDistance;
    }

    private System.Collections.IEnumerator MoveBallToTarget(GameObject ball, Vector3 start, Vector3 target, float targetGroundDistance, bool do_damage)
    {
        float elapsedTime = 0f;
        float totalTime = Vector3.Distance(start, target) / currentMoveSpeed;

        Vector3 adjustedTarget = new Vector3(target.x, target.y - ballRollGroundScale * targetGroundDistance, target.z);

         // If the soccer ball is selected, set the final destination to the goal instead of the target
        if (selectedPrefab == soccerPrefab && currentSoccerGoal != null)
        {
            Vector3 goalPosition = currentSoccerGoal.transform.position;
            adjustedTarget = goalPosition;
        }

        
        if (selectedPrefab  == bowlingBallPrefab)
        {
            GenerateBowlingPins(adjustedTarget);
        }
  
       

        while (elapsedTime < totalTime)
        {
            elapsedTime += Time.deltaTime;
            float t = elapsedTime / totalTime;

            Vector3 currentPosition = Vector3.Lerp(start, adjustedTarget, t);
            ball.transform.position = currentPosition;
            ball.transform.Rotate(Vector3.up, currentSpinSpeed * Time.deltaTime, Space.Self);

            yield return null;
        }


        ball.transform.position = adjustedTarget;
        OnBallHitMarker(ball, target);
    }

 


    private System.Collections.IEnumerator MoveBowlingPins()
    {
        foreach (GameObject pin in currentBowlingPins)
        {
            if (pin != null)
            {
                // Apply an upward and backward movement to simulate impact (customize as needed)
                Vector3 direction = new Vector3(Random.Range(-0.5f, 0.5f), 1f, Random.Range(-0.5f, 0.5f));
                StartCoroutine(AnimatePin(pin));
            }
        }

        yield return null;
    }

    private System.Collections.IEnumerator AnimatePin(GameObject pin)
    {
        float elapsedTime = 0f;
        float duration = 1f;  // Duration of the animation

        Vector3 startPosition = pin.transform.position;

        // Generate a random direction and force for each pin
        Vector3 randomDirection = new Vector3(Random.Range(-0.5f, 0.5f), Random.Range(0.5f, 1.0f), Random.Range(-0.5f, 0.5f));
        float randomForce = Random.Range(minBowlingPinHitForce, maxBowlingPinHitForce);  // Adjust the range to control the spread

        // Calculate the end position based on the random direction and force
        Vector3 endPosition = startPosition + randomDirection * randomForce;

        while (elapsedTime < duration)
        {
            elapsedTime += Time.deltaTime;
            float t = elapsedTime / duration;

            pin.transform.position = Vector3.Lerp(startPosition, endPosition, t);
            pin.transform.Rotate(Vector3.right, 360 * Time.deltaTime, Space.Self);  // Optional: Add rotation for realism

            yield return null;
        }

        // Destroy the pin or keep it in its final position
        Destroy(pin);
    }

    private void OnBallHitMarker(GameObject ball, Vector3 target)
    {
        if (hitText != null)
        {
            hitText.gameObject.SetActive(true);
            hitText.text = "Hit Opponent! ";


            // Start coroutine to hide the hit text after 1.5 seconds
            StartCoroutine(HideHitTextAfterDelay(1.5f));
        }

        Debug.Log("[Showcase1] AR Script: Ball hit the marker!");
        

        

        if (selectedPrefab == bowlingBallPrefab)
        {
            StartCoroutine(MoveBowlingPins());  // Animate the pins when the bowling ball hits the target
        }

        if (currentHoop != null)
        {
            Destroy(currentHoop);
            currentHoop = null;  // Clear the reference to the destroyed hoop
            Debug.Log("Hoop destroyed.");
        }

        if (currentSoccerGoal != null)
        {
            Destroy(currentSoccerGoal);
            currentSoccerGoal = null;  // Clear the reference to the destroyed goal
            Debug.Log("Soccer goal destroyed.");
        }

        if (selectedPrefab == bombPrefab && is_other_player_visible)
        {
            // Check if the current ball is not null
            if (ball != null)
            {
                GameObject clonedBall = Instantiate(rainBombPrefab);
                clonedBall.transform.SetParent(null, true);  // 'true' ensures it retains its current world position
                clonedBall.transform.position = target;  // Ensure it's set to the correct target location

                // Add the cloned ball to the list
                rainBombList.Add(clonedBall);

                // Set the initial position using the Ball's script method
                FixedPositionAnchor anchorScript = clonedBall.GetComponent<FixedPositionAnchor>();
                if (anchorScript != null)
                {
                    // Set the AnchorStage dynamically from the BallThrowingScript
                    anchorScript.SetAnchorStage(anchorStage);

                     // Add height offset to target position to make the rain bomb spawn above the target
                    Vector3 targetPositionAbove = new Vector3(target.x, target.y + heightOffset, target.z);             // Adjust the '5f' value to the desired height

                    // Set the initial position of the cloned ball
                    anchorScript.SetInitialPosition(targetPositionAbove, Quaternion.identity);
                 
                }
                else
                {
                    Debug.LogError("No FixedPositionAnchor script found on the cloned ball.");
                }

                Destroy(ball);
                 
            }
        }
        else 
        {
            if (ball != null)
            {
                Destroy(ball);
            }
        }
    }



    



    private System.Collections.IEnumerator HideHitTextAfterDelay(float delay)
    {
        // Wait for the specified delay
        yield return new WaitForSeconds(delay);

        // Hide the hit text
        if (hitText != null)
        {
            hitText.gameObject.SetActive(false);
        }
    }



    // Function to spawn and anchor the rain bomb using the same method as the ball
    private void SpawnAndAnchorRainBomb(Vector3 targetPosition)
    {   
        Debug.Log("[Rain Bomb] Rain Bomb: Spawning rain bomb");
        // Instantiate the rain bomb prefab
        GameObject rainBomb = Instantiate(rainBombPrefab);

        // Unparent the rain bomb to make it a standalone object
        rainBomb.transform.SetParent(null, true);  // 'true' ensures it retains its current world position

        // Print the parent of the rain bomb before anchoring
        Debug.Log("[Rain Bomb] Rain bomb's current parent before anchoring: " + (rainBomb.transform.parent != null ? rainBomb.transform.parent.name : "None"));

        // Get the RainBombAnchorScript from the rain bomb prefab 
        RainBombAnchorScript rainBombAnchor = rainBomb.GetComponent<RainBombAnchorScript>();

        if (rainBombAnchor != null)
        {
            
            // Set the AnchorStage dynamically for the rain bomb
            rainBombAnchor.SetAnchorStage(anchorStage);

            Debug.Log("[Rain Bomb] Pass Anchoring");
        
            // Anchor the rain bomb above the target position
            rainBombAnchor.AnchorRainBomb(targetPosition);

            Debug.Log("[Rain Bomb] Rain bomb spawned and anchored above the target position.");
        }
        else
        {
            Debug.Log("[Rain Bomb] No RainBombAnchorScript found on the rain bomb prefab.");
        }

        // Optionally log the rain bomb's position after setting the initial target
        Debug.Log("[Rain Bomb] Rain bomb initial position set to world position: " + rainBomb.transform.position);
    }
}
