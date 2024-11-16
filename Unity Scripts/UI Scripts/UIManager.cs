using TMPro;
using UnityEngine;
using System.Linq;
using System.Collections;
using uPLibrary.Networking.M2Mqtt;
using uPLibrary.Networking.M2Mqtt.Messages;
using Newtonsoft.Json;
using System;
using System.Text;

public class UIManager : MonoBehaviour
{
    public TextMeshProUGUI player1ScoreText;
    public TextMeshProUGUI player2ScoreText;
    public TextMeshProUGUI gameDurationText;
    public TextMeshProUGUI playerShieldsText;
    public TextMeshProUGUI EnemyBulletsText;
    public TextMeshProUGUI publicPlayerID;

    public HealthBar HealthBar;
    public HealthBar EnemyHealthBar;

    public ShieldBar ShieldBar;
    public Bullets Bullets;
    public RainBomb RainBomb;

    public EnemyShieldBar EnemyShieldBar;
    public BulletsEnemy BulletsEnemy;


    void Start()
    {
        // HealthBar.setMaxHealth();
        // UpdateBombs(3);
        // StartCoroutine(WaitAndPrint());
        
        // // Create MQTT client instance
        // client = new MqttClient(brokerAddress);

        // // Register to message received
        // client.MqttMsgPublishReceived += OnMessageReceived;

        // string clientId = Guid.NewGuid().ToString();
        // client.Connect(clientId);

        // // Subscribe to the topic
        // client.Subscribe(new string[] { ui_topic }, new byte[] { MqttMsgBase.QOS_LEVEL_AT_LEAST_ONCE });
    }


    





    

    

    // for now, just for debugging, just player 1
    public void UpdateAllPlayer1(int hp, int bombs, int shieldCharges, int shieldHP, int bullets, int opponent_hp)
    {
        UpdatePlayerHP(hp);
        UpdatePlayerShields(shieldCharges,shieldHP);
        UpdateBombs(bombs);
        UpdateBullets(bullets);
    } 

    // Method to update player scores
    public void UpdatePlayersScores(int player1_deaths, int player2_deaths)
    {
        player1ScoreText.text = "Pl: " + player2_deaths;
        player2ScoreText.text = "P2: " + player1_deaths;
    }

    // Method to update game duration
    public void UpdateGameDuration(string duration)
    {
        gameDurationText.text = duration;
    }

    // Method to update enemy HP
    public void UpdateEnemyHP(int currentHP)
    {
        EnemyHealthBar.setHealth(currentHP);
    }

    public void UpdateEnemyShield(int currentShield)
    {
        EnemyShieldBar.setShield(currentShield);
    }

    // Method to update player's HP
    public void UpdatePlayerHP(int currentHP)
    {
        Debug.Log("Updating HP");
        HealthBar.setHealth(currentHP);
        //playerHPText.text = "HP: " + currentHP + "/100";
    }

    // Method to update player's shields
    public void UpdatePlayerShields(int shieldsRemaining, int shield_hp)
    {
        ShieldBar.setShieldHP(shield_hp);
        playerShieldsText.text = "Shield: " + shieldsRemaining + " /3";
    }

    // Method to update bombs count
    public void UpdateBombs(int bombsRemaining)
    {
        RainBomb.setBombs(bombsRemaining);
    }

    // Method to update bullets count
    public void UpdateBullets(int bulletsRemaining)
    {
        Bullets.SetAmmo(bulletsRemaining);
    }

    // Call this without calling UpdateBullets, it auto does it
    public void reloadBullets()
    {
        Bullets.ReloadAmmo();
    }

    // old but working with text
    // public void updateEnemyBullets(int bullets)
    // {
    //     EnemyBulletsText.text = "Enemy Bullets: " + bullets + " / 6";
    // }


    // Method to update bullets count
    public void updateEnemyBullets(int bulletsRemaining)
    {
        BulletsEnemy.SetAmmo(bulletsRemaining);
    }


    








    // Communication code that is currently irrelevent



    // private MqttClient client;
    // public string brokerAddress = "172.26.190.191";  // Replace with your HiveMQ broker IP or hostname
    // public string ui_topic = "unity/uiUpdate";  // Topic to subscribe to

    // void OnMessageReceived(object sender, MqttMsgPublishEventArgs e)
    // {
    //     string message = Encoding.UTF8.GetString(e.Message);
    //     Debug.Log("Received MQTT message: " + message);

    //     // Ensure JSON is parsed correctly
    //     try
    //     {
    //         // Deserialize JSON on the main thread
    //         UnityMainThreadDispatcher.Instance().Enqueue(() => ProcessMessage(message));
    //     }
    //     catch (Exception ex)
    //     {
    //         Debug.LogError("Error parsing JSON: " + ex.Message);
    //     }
    // }

    // void ProcessMessage(string message)
    // {
    //     try
    //     {
    //         UIData uiData = JsonConvert.DeserializeObject<UIData>(message);
    //         Debug.Log("Parsed JSON successfully.");
    //         UpdateUI(uiData);
    //     }
    //     catch (Exception ex)
    //     {
    //         Debug.LogError("Error processing message: " + ex.Message);
    //     }
    // }


    // void UpdateUI(UIData uiData)
    // {
    //     // Update your UI elements with received data
    //     Debug.Log("Player 1 HP: " + uiData.hp);
    //     Debug.Log("Player 1 Bullets: " + uiData.bullets);
    //     Debug.Log("Player 1 Bombs: " + uiData.bombs);
    //     Debug.Log("Player 2 HP: " + uiData.opponent_hp);
  
        
    //     // Here you can update UI elements like health bars, ammo counts, etc.

    //     UpdatePlayerHP(uiData.hp);
    //     UpdateBullets(uiData.bullets);
    //     UpdatePlayersScores(uiData.opponent_deaths, uiData.deaths);
    //     UpdateEnemyHP(uiData.opponent_hp);
    //     UpdatePlayerShields(uiData.shields, uiData.shield_hp);
    //     UpdateBombs(uiData.bombs);
    // }

    // [Serializable]
    // public class UIData
    // {
    //     public int hp;
    //     public int bullets;
    //     public int bombs;
    //     public int shield_hp;
    //     public int shields;
    //     public int opponent_hp;
    //     public int deaths;
    //     public int opponent_deaths;
    // }

    // void OnDestroy()
    // {
    //     if (client != null && client.IsConnected)
    //     {
    //         client.Disconnect();
    //     }
    // }





    // DEBUGING CODE

    // IEnumerator WaitAndPrint()
    // {
    //     int health = 100;
    //     int shield = 30;
    //     int bullets = 6;
    //     int bombs = 3;

    //     int enemyHealth = 100;
    //     int enemyShield = 30;
    //     int enemyBullets = 6;


    //     for (int i = 0; i < 10; i++)
    //     {
    //         UpdateBullets(0);
    //         reloadBullets();
    //         yield return new WaitForSeconds(3f);
    //     }

    //     for (int i = 0; i < 10; i++)
    //     {   
            
    //         UpdateEnemyHP(enemyHealth);
    //         enemyHealth -= 30;
    //         health -= 10;
    //         shield -= 3;
    //         bullets -= 2;
    //         bombs -= 1;
    //         HealthBar.setHealth(health);
    //         ShieldBar.setShieldHP(shield);
    //         UpdateBullets(bullets);
    //         UpdateBombs(bombs);
    //         // Wait for 2 seconds
    //         yield return new WaitForSeconds(3f);
    //     }
    //     reloadBullets();
    //     yield return new WaitForSeconds(10f);
        

    //     for (int i = 0; i < 3; i++)
    //     {   
    //         // health -= 10;
    //         // shield -= 3;
    //         bullets += 2;
    //         // HealthBar.setHealth(health);
    //         // ShieldBar.setShieldHP(shield);
    //         UpdateBullets(bullets);
    //         // Wait for 2 seconds
    //         yield return new WaitForSeconds(2f);
    //     }

    //     // Print message after 2 seconds
    //     Debug.Log("Waited for 2 seconds!");
    // }


}
