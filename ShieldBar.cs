using UnityEngine;
using UnityEngine.UI;
using DG.Tweening;

public class ShieldBar : MonoBehaviour
{
    public Slider slider;
    public Image shieldImage; // Reference to the Image component that displays the shield
    public Sprite[] shieldSprites; // Array of shield sprites for different damage levels
    public int shieldsRemaining = 3;
    public float FillDuration = 1.0f;
    public Image shieldFill;
    
 
    private float maxShieldPoints = 30f; // Maximum shield points
    private float currentShieldPoints; // Current shield points


    private Color color_100 = new Color(0/255f, 255/255f, 255/255f, 163/255f);
    private Color color_70 = new Color(0/255f, 255/255f, 255/255f, 163/255f);
    private Color color_50 = new Color(255/255f, 203/255f, 0/255f, 163/255f);
    private Color color_30 = new Color(255/255f, 101/255f, 0/255f, 161/255f);
    private Color color_20 = new Color(220/255f, 0/255f, 0/255f, 163/255f);



    

    void Start()
    {
        currentShieldPoints = maxShieldPoints; // Initialize shield points
        UpdateShieldSprite(); // Initial update to set the correct sprite
        setStartingShield();
    }

    public void setMaxShield()
    {
        slider.maxValue = maxShieldPoints;
        slider.value = maxShieldPoints;
        currentShieldPoints = maxShieldPoints; // Initialize shield points
        shieldFill.GetComponent<Image>().color = color_100;

    }

    public void setStartingShield()
    {
        slider.maxValue = maxShieldPoints;
        slider.value = 0;
        setShieldHP(0);
    }


    public void setShieldHP(float HP)
    {
        currentShieldPoints = HP;
        UpdateShieldSprite(); // Update the sprite based on new shield points

        slider.DOValue(HP, FillDuration);
    }

    public void powerUpShield()
    {
        shieldsRemaining--;
        setMaxShield();
    }


    // Method to update the shield sprite based on current shield points
    void UpdateShieldSprite()
    {
        if (currentShieldPoints <= 0)
        {
            // Disable the shield image when shield is gone
            shieldImage.enabled = false;
            return; // Exit the method early since there's no shield to display
        }
        else
        {
            // Enable the shield image if there is shield left
            shieldImage.enabled = true;
        }

        // Determine which sprite to use based on the current shield percentage
        float shieldPercentage = currentShieldPoints / maxShieldPoints;

        if (shieldPercentage > 0.90f)
        {
            shieldImage.sprite = shieldSprites[0]; // No damage or minimal damage
            shieldFill.GetComponent<Image>().color = color_100;

        }
        else if (shieldPercentage > 0.7f)
        {
            shieldImage.sprite = shieldSprites[1]; // Low damage
            shieldFill.GetComponent<Image>().color = color_70;
        }
        else if (shieldPercentage > 0.5f)
        {
            shieldImage.sprite = shieldSprites[2]; // Medium damage
            shieldFill.GetComponent<Image>().color = color_50;
        }
        else if (shieldPercentage > 0.3f)
        {
            shieldImage.sprite = shieldSprites[3]; // Medium damage
            shieldFill.GetComponent<Image>().color = color_30;
        }
        else
        {
            shieldImage.sprite = shieldSprites[4]; // Heavy damage
            shieldFill.GetComponent<Image>().color = color_20;
        }
    }
}
