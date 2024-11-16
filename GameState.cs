using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using uPLibrary.Networking.M2Mqtt;
using uPLibrary.Networking.M2Mqtt.Messages;
using TMPro;
using UnityEngine.UI;
using System.Collections.Generic;
using System.Text;
using System;

public class GameState : MonoBehaviour
{

    /*
    *   This script is the game state script that is meant to be on the Visualizer phones
    *   It is the script that stores variables and display them by interacting with UIManager script
    *   It communicates with the game engine script on the ultra96 before updating the User Interface
    * 
    *   This script does not do any calculations. 
    *   eg. For shooting, it has to ask the ultra96 if the player has the correct amno, listen to its response 
    *       then, allow it to shoot by calling the necessary functions 
    * 
    */
    

    // Overall Variables
    private int max_hp = 100;
    private int max_bullets = 6;
    private int max_shield_health = 30;
    private int hp_rain = 5;
    private int hp_bomb = 5;
    private int hp_AI = 10;
    private int hp_bullet = 5;
    private int max_bombs = 2;
    private int max_shields = 3;


    /*
    *   Here unlike GameEngine, we refer to ourself as hp, and opponent with a surfix to make coding identical.
    *   In order for the GameEngine to know which player is sending data, the data packet will have player_id, 1 or 2
    */

    public int player_id = 1; // For now this is hardcoded
    public int opponent_player_id = 2;

    // Player Variables
    private int hp;
    private int bombs;
    private int shieldCharges;
    private int shieldHp;
    private int bullets;
    private int deaths;

    // Opponent Variables
    private int hp_opponent;
    private int bombs_opponent;
    private int shieldCharges_opponent;
    private int shieldHp_opponent;
    private int bullets_opponent;
    private int deaths_opponent;


    public UIManager uiManager; 

    public SimpleShoot gunModel; 


    bool inView; 


    private MqttClient client;
    public string brokerAddress = "172.26.191.210";  // Replace with your Ultra96's IP address
    public string gamestate_topic = "tovisualizer/gamestate";      
    public string fov_topic = "tovisualizer/field_of_view";     
    public string viz_response = "fromvisualizer/response";

    public Button connectButton; // to connect to MQTT broker 
    public TextMeshProUGUI consoleText;
    private List<string> messageList = new List<string>() ;
    private int maxMessages = 3;

    public MarkerBallThrowAndRollCombined markerBallScript; 


  

    private bool isReconnecting = false;
    private float reconnectDelay = 5.0f; // 5-second delay before retrying connection

    public TextMeshProUGUI mqttStatusText;  // To display MQTT connection status
    public TextMeshProUGUI playerIDText;
    public float checkVisibleDuration = 2f;

    private Coroutine visibilityCoroutine;  // Store reference to active coroutine

 
    public List<Button> debugButtons;
    public List<TextMeshProUGUI> debugTexts;       

    public RectTransform debugRect1;
    public RectTransform debugRect2;
    public Button resetButton;




    public void ResetPlayerStats()
    {
        // Set player variables to max
        hp = max_hp;
        bombs = max_bombs;
        shieldCharges = max_shields;
        shieldHp = 0;
        bullets = max_bullets;
        deaths = 0;

        // Set opponent variables to max
        hp_opponent = max_hp;
        bombs_opponent = max_bombs;
        shieldCharges_opponent = max_shields;
        shieldHp_opponent = 0;
        bullets_opponent = max_bullets;
        deaths_opponent = 0;

        Debug.Log("Player and opponent stats reset to default values.");
    }

    private void UpdateMQTTStatus(string status)
    {
        mqttStatusText.text = "MQTT Status: " + status;
        Debug.Log("MQTT Status: " + status);
    }



    void ConnectToBroker()
    {  
        UpdateMQTTStatus("Trying to connect...");  // Update status to "trying to connect"
        try
        {
            client = new MqttClient(brokerAddress);
            string clientId = Guid.NewGuid().ToString();
            client.Connect(clientId);
            Debug.Log("[MQTT] Connected to MQTT Broker at " + brokerAddress);
            UpdateConsole("[MQTT] Connected to MQTT Broker at " + brokerAddress);
            UpdateMQTTStatus("Connected");  // Update status to "connected"

            // Subscribe to the gamestate topic and field_of_view topic to receive updates
            client.Subscribe(new string[] { gamestate_topic}, new byte[] { MqttMsgBase.QOS_LEVEL_AT_LEAST_ONCE });
            client.MqttMsgPublishReceived += OnMessageReceived;

            

            if (isReconnecting)
            {
                StopCoroutine(ReconnectToBroker());
                isReconnecting = false;
            }
        }
        catch (Exception ex)
        {
            Debug.LogError("[MQTT] Failed to connect to MQTT Broker: " + ex.Message);
            UpdateMQTTStatus("Failed to connect");  // Update status to "failed to connect"

            if (!isReconnecting)
            {
                StartCoroutine(ReconnectToBroker());
            }
        }
    }

  
    public void SendCommand(string command)
    {
        if (client != null && client.IsConnected)
        {
            client.Publish(viz_response, Encoding.UTF8.GetBytes(command));
            Debug.Log("[MQTT] Sent field of view response: " + command);
            UpdateConsole("[MQTT] Sent field of view response: " + command);
        }
        else
        {
            Debug.LogWarning("[MQTT] Cannot send command, client not connected.");
        }
    }

    IEnumerator ReconnectToBroker()
    {
        isReconnecting = true;  

        while (!client.IsConnected)
        {
            UpdateMQTTStatus("Reconnecting...");  // Update status to "reconnecting"
            Debug.Log("[MQTT] Attempting to reconnect...");
            UpdateConsole("[MQTT] Attempting to reconnect...");

            try
            {
                ConnectToBroker();
            }
            catch (Exception ex)
            {
                Debug.LogError("[MQTT] Reconnection attempt failed: " + ex.Message);
            }

            // Wait before trying again
            yield return new WaitForSeconds(reconnectDelay);
        }

        isReconnecting = false;
        Debug.Log("[MQTT] Successfully reconnected.");
        UpdateMQTTStatus("Connected");  // Update status to "connected"
        UpdateConsole("[MQTT] Successfully reconnected.");
    }


    // Disconnect event handling and auto-reconnect trigger
    private void HandleDisconnect()
    {
        UpdateMQTTStatus("Disconnected");  // Update status to "disconnected"
        if (!client.IsConnected && !isReconnecting)
        {
            Debug.Log("[MQTT] Disconnected from broker. Starting reconnection attempts...");
            StartCoroutine(ReconnectToBroker());
        }
    }


    // Callback when a message is received
    private void OnMessageReceived(object sender, MqttMsgPublishEventArgs e)
    {
        string receivedMessage = Encoding.UTF8.GetString(e.Message);
        Debug.Log("[MQTT] Received message: " + receivedMessage);
        try
        {
            UnityMainThreadDispatcher.Instance().Enqueue(() => UpdateConsole("[MQTT] Received message: " + receivedMessage));
        }
        catch (Exception ex)
        {
          Debug.LogError("[MQTT] Error enqueuing to main thread: " + ex.Message);
        }
        ProcessMessage(receivedMessage);
    }

    private void UpdateConsole(string message)
    {
            
        messageList.Add(message);


        if (messageList.Count > maxMessages)
        {
            messageList.RemoveAt(0);
        }


        consoleText.text = string.Join("\n", messageList);
        

    }

    /*
    Main function that processes messages from the game engine, there are two types of messages 
    1. fovquery -> called when AI is predicting, provides the game engine with 1. Is opponent in sight? 2. How many rain bombs are hitting opponent
    2. update_ui -> called when game engine wants to update the game state of visualizers. 
                    Game state script parses the correct player information (p1 or p2) according to player_id set, and updates game state info
    */
    private void ProcessMessage(string message)
    {
        UnityMainThreadDispatcher.Instance().Enqueue(() =>
        {
           // Check if the message starts with "fovquery"
            if (message.StartsWith("fovquery"))
            {
                // Split the message by ':' and attempt to parse the second part as an integer
                string[] parts = message.Split(':');
                if (parts.Length == 2 && int.TryParse(parts[1], out int targetPlayerId))
                {
                    // Check if the player ID matches the target ID
                    if (targetPlayerId == player_id)
                    {
                        Debug.Log($"[MQTT] Fov Query action received for player {player_id}.");
                        CheckFieldOfViewAndRespond("fovquery");
                    }
                    else
                    {
                        Debug.Log($"[MQTT] Fov Query action received but not for this player (player_id: {player_id}). Skipping response.");
                    }
                }
                else
                {
                    Debug.LogWarning($"[MQTT] Malformed fovquery message: {message}");
                }
                return;  // Exit after handling the fovquery message
            }



            if (message.StartsWith("p1_hp:"))
            {
                string[] stateParts = message.Split(',');
                foreach (string part in stateParts)
                {
                    Debug.Log($"[MQTT] part: {part}");
                    string[] keyValue = part.Split(':');
                    if (keyValue.Length < 2)
                    {
                        Debug.LogWarning($"[MQTT] Malformed message part: {part}");
                        continue;
                    }

                    string key = keyValue[0];
                    string valueString = keyValue[1];

                    // Handle numeric stats separately from actions
                    if (key.StartsWith("p1_") || key.StartsWith("p2_"))
                    {
                        if (key.Contains("_action"))
                        {
                            Debug.Log($"[MQTT] key: {key}, action value: {valueString}");

                            // Handle actions
                            if ((key == "p1_action" && player_id == 1) || (key == "p2_action" && player_id == 2))
                            {
                                Debug.Log("[MQTT] Handling action");
                                HandlePlayerAction(valueString);  // Now correctly handle actions as strings
                            }
                        }
                        else
                        {
                            // Try to parse value as an integer for stats
                            if (int.TryParse(valueString, out int value))
                            {
                                Debug.Log($"[MQTT] key: {key}, value: {value}");

                                // Check if player_id is 1 or 2 and update stats accordingly
                                if (player_id == 1) // Player 1 is the current player
                                {
                                    UpdatePlayerStatsForPlayer1(key, value);
                                }
                                else if (player_id == 2) // Player 2 is the current player
                                {
                                    UpdatePlayerStatsForPlayer2(key, value);
                                }
                            }
                            else
                            {
                                Debug.LogWarning($"[MQTT] Could not parse integer from value: {valueString} for key: {key}");
                            }
                        }
                    }

                    
                }

            }   
        });
    }


    /*
        Reference function to get MarkerLost(), MarkerFound() function of Vuforia's Image target script
    */
    private bool getIsOtherPlayerVisible()
    {
        return markerBallScript.getIsOtherPlayerVisible(); 
    }

    // Update Player 1 Stats
    private void UpdatePlayerStatsForPlayer1(string key, int value)
    {
        switch (key)
        {
            case "p1_hp":
                hp = value;
                break;
            case "p1_bombs":
                bombs = value;
                break;
            case "p1_shieldCharges":
                shieldCharges = value;
                break;
            case "p1_shieldHp":
                shieldHp = value;
                break;
            case "p1_bullets":
                bullets = value;
                break;
            case "p1_deaths":
                deaths = value;
                break;
            case "p2_hp":
                hp_opponent = value;
                break;
            case "p2_bombs":
                bombs_opponent = value;
                break;
            case "p2_shieldCharges":
                shieldCharges_opponent = value;
                break;
            case "p2_shieldHp":
                shieldHp_opponent = value;
                break;
            case "p2_bullets":
                bullets_opponent = value;
                break;
            case "p2_deaths":
                deaths_opponent = value;
                break;
        }
    }

    // Update Player 2 Stats
    private void UpdatePlayerStatsForPlayer2(string key, int value)
    {
        switch (key)
        {
            case "p2_hp":
                hp = value;
                break;
            case "p2_bombs":
                bombs = value;
                break;
            case "p2_shieldCharges":
                shieldCharges = value;
                break;
            case "p2_shieldHp":
                shieldHp = value;
                break;
            case "p2_bullets":
                bullets = value;
                break;
            case "p2_deaths":
                deaths = value;
                break;
            case "p1_hp":
                hp_opponent = value;
                break;
            case "p1_bombs":
                bombs_opponent = value;
                break;
            case "p1_shieldCharges":
                shieldCharges_opponent = value;
                break;
            case "p1_shieldHp":
                shieldHp_opponent = value;
                break;
            case "p1_bullets":
                bullets_opponent = value;
                break;
            case "p1_deaths":
                deaths_opponent = value;
                break;
        }
    }


    private void HandlePlayerAction(string action)
    {
        Debug.Log($"[MQTT] Action received: {action}");

        switch (action)
        {
            case "gun":
                doShootAction();
                break;
            case "reload":
                doReloadAction();
                break;
            case "gun_fail":
                // Do not play the shoot animation; action failed
                Debug.Log("[MQTT] Shoot failed, not playing shoot animation.");
                break;
            case "reload_fail":
                // Do not play the reload animation; action failed
                Debug.Log("[MQTT] Reload failed, not playing reload animation.");
                break;
            case "rain_bomb_damage":
                updateHPAndShieldAction();
                break;
            case "shield":
                doChargeShieldAction();
                break;
            case "shield_fail":
                // Do not play the shield animation; action failed
                Debug.Log("[MQTT] Shield charge failed, not playing shield animation.");
                break;

            // AI Actions
            case "basket":
                markerBallScript.ShootBasketball();
                setAllUIElements();
                break;
            case "soccer":
                markerBallScript.ShootSoccer();       
                setAllUIElements();
                break;
            case "volley":
                markerBallScript.ShootVolleyball();           
                setAllUIElements();
                break;
            case "bowl":
                markerBallScript.ShootBowlingBall();            
                setAllUIElements();
                break;
            case "bomb":
                markerBallScript.ShootBomb();
                updateBombs();        
                setAllUIElements();
                break;
            case "bomb_fail":
                // Do not play the bomb animation; action failed
                Debug.Log("[MQTT] Bomb failed, not playing Bomb animation.");
                break;
            case "update_ui":
                Debug.Log("[MQTT] Update UI action received.");
                // Just update the UI based on the current game state
                // Dun send response back         
                break;
            case "logout":
                Debug.Log("[MQTT] Logout action received.");
                break;
            case "none":
                Debug.Log($"[MQTT] Not this phone's action: {action}");
                break;
            
            default:
                Debug.Log($"[MQTT] Unrecognized action: {action}");
                break;
        }
    }


  

    /*
        Here we start a coroutine in order to find out if Vuforia's image target is missing
        We set a timer of 3 seconds (adjusted accordingly) and if the Vuforia image target is not found in 3 seconds, we conclude that 
        opponent is not in sight. If image target and hence opponent is found during this 3 seconds, we return that opponent is in sight
        This is to overcome the problem of players shaking and losing image target when doing the AI action

        Disclaimer: In the MarkerBallThrowAndRollCombined script, in markerLost() and markerDetected() there is a similar mechanism to prevent this, there are just two safeguards in place just in case
    */
    private void CheckFieldOfViewAndRespond(string prevActionString)
    {
        // Stop any existing coroutine to avoid overlap
        if (visibilityCoroutine != null)
        {
            StopCoroutine(visibilityCoroutine);
            visibilityCoroutine = null; // Ensure the coroutine reference is cleared
        }
        
        visibilityCoroutine = StartCoroutine(CheckOpponentInViewCoroutine(prevActionString, queryDuration: checkVisibleDuration));
    }

    private IEnumerator CheckOpponentInViewCoroutine(string prevActionString, float queryDuration)
    {
        // Check if the action is an AI action
        int isPrevActionAnAIAction = (prevActionString == "basket" || prevActionString == "soccer" || prevActionString == "volley" ||
                                    prevActionString == "bowl" || prevActionString == "bomb") ? 1 : 0;

        // Query for opponent visibility for the given duration
        float elapsedTime = 0f;
        bool opponentInView = false;

        while (elapsedTime < queryDuration)
        {
            if (markerBallScript.getIsOtherPlayerVisible())
            {
                opponentInView = true;
                Debug.Log("[Timer] Opponent in view, exiting coroutine early.");
                break;
            }

            elapsedTime += Time.deltaTime;
            Debug.Log($"[Timer] Elapsed Time: {elapsedTime}");
            yield return null; // Wait until the next frame
        }

        int isPrevActionHit = opponentInView ? 1 : 0;

        // Check if rain bombs are hitting the opponent using the markerBallScript reference
        int rainBombHitCount = markerBallScript.isRainBombsHittingOpponent();
        hp_opponent -= hp_rain * rainBombHitCount;

        // Handle specific case for "bomb_fail" action
        if (prevActionString == "bomb_fail")
        {
            prevActionString = "bomb";
        }

        // Build the response message in the format: "player_id:isPrevActionAnAIAction:isPrevActionHit:PrevAction:rainBombHitCount"
        string Response = $"{player_id}:{isPrevActionAnAIAction}:{isPrevActionHit}:{prevActionString}:{rainBombHitCount}";

        // Send the FOV response back to the game engine via MQTT
        SendCommand(Response);

        // Log the response
        Debug.Log($"[MQTT] Field of view response sent: {Response}");
        UpdateConsole($"[MQTT] Field of view response: {Response} for action: {prevActionString}");

        // Nullify coroutine reference when done
        visibilityCoroutine = null;
    }




    void OnDestroy()
    {
        if (client != null && client.IsConnected)
        {
            client.Disconnect();
            UpdateMQTTStatus("Disconnected");  // Update status to "disconnected"
        }
    }

  



    public void setAllUIElements()
    {
        uiManager.UpdateBullets(bullets);
        uiManager.UpdatePlayerHP(hp);    
        uiManager.UpdatePlayerShields(shieldCharges, shieldHp);

        uiManager.updateEnemyBullets(bullets_opponent);
        uiManager.UpdateEnemyHP(hp_opponent);    
        uiManager.UpdateEnemyShield(shieldHp_opponent);


 
        // This function takes in 
        // UpdatePlayersScores(int player1_deaths, int player2_deaths)

        if (player_id == 1)
        {
            uiManager.UpdatePlayersScores(deaths, deaths_opponent);
        }
        else uiManager.UpdatePlayersScores(deaths_opponent, deaths);
        
    }

   

    // Utility function that sends the action to the Game Engine via MQTT.
    private void SendActionToGameEngine(string action)
    {
        if (client != null && client.IsConnected)
        {
            client.Publish(viz_response, Encoding.UTF8.GetBytes(action)); // Send the action message to the Game Engine.
            Debug.Log("[MQTT] Sent action to Game Engine: " + action);
            UpdateConsole("[MQTT] Sent action to Game Engine: " + action);
        }
        else
        {
            Debug.LogWarning("[MQTT] Cannot send action, client not connected.");
        }
    }



    // The syntax here helps to ensure that Game Engine updates the game state before uiManager functions are called
    // Due to the code waiting for bool variable to return.
    public void doShootAction()
    {
        // Note: Game Engine already ask us get player stats so we no need to retrieve anything
        Debug.Log("[Showcase] Game State Script: bullets left: " + bullets);
        uiManager.UpdateBullets(bullets);
        Debug.Log("[MQTT] Shooting Bullet");
        gunModel.shootBullet();
        
    }

    /*
        Debug functions, not used in actual gameplay
    */
    public  void chargeShield()
    {
        if (shieldCharges > 0 && shieldHp == 0)
        {
            shieldCharges--;
            shieldHp = 30;
        }
        doChargeShieldAction();
    }
    

    public void takeDamage(int damage)
    {
        if (shieldHp > 0)
        {
            shieldHp = Math.Max(0, shieldHp - damage);
        }
        else
        {
            hp = Math.Max(0, hp - damage);
        }

        if (hp <= 0)
        {
            respawn();
        }
        updateHPAndShieldAction();
    }

    public  void respawn()
    {
        hp = 100;
        bombs = 2;
        shieldCharges = 3;
        shieldHp = 0;
        bullets = 6;
        deaths++;
    }
    /*
        End of Debug functions
    */



    public void doReloadAction()
    {    
        uiManager.reloadBullets();    
    }

    public void updateHPAndShieldAction()
    {
        uiManager.UpdatePlayerHP(hp);    
        uiManager.UpdatePlayerShields(shieldCharges, shieldHp);
    }

    public void doChargeShieldAction()
    {
        
        uiManager.UpdatePlayerShields(shieldCharges, shieldHp);
    }

    // Only for rain bomb does a player queue the damage for the opponent
    public void queueDoRainBombDamage()
    {
        Debug.Log("[Game State Script] Sending 'rain_bomb_damage' request for opponent to Game Engine");
        string action = $"rain_bomb_damage:{opponent_player_id}"; // Send rain bomb damage to the opponent
        SendActionToGameEngine(action);
    }
    
    public void updateBombs()
    {
        uiManager.UpdateBombs(bombs);
    }

    public void takeDamageOpponent(int damage)
    {
        // Reduce opponent's health by the amount of damage
        hp_opponent -= damage;
        Debug.Log($"Opponent took {damage} damage. Remaining HP: {hp_opponent}");

        // Check if the opponent's health falls below or equal to zero
        if (hp_opponent <= 0)
        {
            Debug.Log("Opponent's HP has dropped to 0 or below. Triggering respawn.");

            // Handle respawn logic
            RespawnOpponent();
        }
    }

    private void RespawnOpponent()
    {
        // Set opponent attributes for respawn
        hp_opponent = 100;               // Reset health to 100
        shieldCharges_opponent = 3;       // Reset shield charges to 3
        shieldHp_opponent = 0;            // Reset shield health to 0
        bullets_opponent = 6;             // Reset bullets to 6
        deaths_opponent += 1;             // Increment death count by 1

        Debug.Log($"Opponent has been respawned. HP: {hp_opponent}, Shield Charges: {shieldCharges_opponent}, Shield HP: {shieldHp_opponent}, Bullets: {bullets_opponent}, Deaths: {deaths_opponent}");

    }




    // Start is called before the first frame update
    void Start()
    {
        //getAndSetPlayerState();
        connectButton.onClick.AddListener(ConnectToBroker);
        resetButton.onClick.AddListener(ToggleDebugButtonsAndResetGame);
        inView = false;
        ResetPlayerStats();
        playerIDText.text = $"Player ID: {player_id}";


        
    }

    // Update is called once per frame
    void Update()
    {
        setAllUIElements();

        // Ensure the connection is maintained, and try to reconnect if disconnected
        if (client != null && !client.IsConnected && !isReconnecting)
        {
            HandleDisconnect();
        }
    }


    public void ToggleDebugButtonsAndResetGame()
    {
        // Check if the first button's GameObject is currently active (assuming all buttons share the same active state)
        bool areDebugElementsCurrentlyActive = debugButtons.Count > 0 && debugButtons[0].gameObject.activeSelf;

        // Toggle the active state of each button's GameObject
        foreach (Button button in debugButtons)
        {
            if (button != null)
            {
                button.gameObject.SetActive(!areDebugElementsCurrentlyActive);
            }
        }

        // Toggle the active state of the debug rectangles
        if (debugRect1 != null)
        {
            debugRect1.gameObject.SetActive(!areDebugElementsCurrentlyActive);
        }

        if (debugRect2 != null)
        {
            debugRect2.gameObject.SetActive(!areDebugElementsCurrentlyActive);
        }

        // Toggle the active state of each debug text
        foreach (TextMeshProUGUI text in debugTexts)
        {
            if (text != null)
            {
                text.gameObject.SetActive(!areDebugElementsCurrentlyActive);
            }
        }

        // Reset player stats
        ResetPlayerStats();
        
        // Clear all rain bombs
        if (markerBallScript != null)
        {
            markerBallScript.ClearRainBombList();
            Debug.Log("All rain bombs cleared.");
        }
        else
        {
            Debug.LogWarning("MarkerBallThrowAndRollCombined script reference is null. Cannot clear rain bombs.");
        }
        Debug.Log($"Game reset and debug buttons toggled. Debug buttons are now {(areDebugElementsCurrentlyActive ? "hidden" : "visible")}.");
    }



}
