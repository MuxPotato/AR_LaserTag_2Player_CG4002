using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using DG.Tweening;
using System;

public class EnemyShieldBar : MonoBehaviour
{   
    public Slider frontSlider;
    public Slider backSlider;
    private int maxShield = 30;
    public float backFillDuration = 2.0f;

    public MarkerBallThrowAndRollCombined markerBallThrowAndRollCombined;

    public void setMaxShield()
    {
        frontSlider.maxValue = maxShield;
        frontSlider.value = maxShield;
        backSlider.maxValue = maxShield;
        backSlider.value = maxShield;
    }

    public void setShield(int Shield)
    {
        frontSlider.value = Shield;
        backSlider.DOValue(Shield, backFillDuration);


        // Controls whether shield gets displayed on enemy or not
        if (Shield > 0)
        {
            markerBallThrowAndRollCombined.setTrackingToShield();
        }
        else markerBallThrowAndRollCombined.setTrackingToCrossHair();
    }



    // Start is called before the first frame update
    void Start()
    {
        setMaxShield();
    }

    // Update is called once per frame
    void Update()
    {
        
    }
}



// public class HealthBar : MonoBehaviour
// {   
//     public Slider slider;
//     private int maxHealth = 100;
//     public float fillDuration = 1.0f;

//     public void setMaxHealth()
//     {
//         slider.maxValue = maxHealth;
//         slider.value = maxHealth;
//     }

//     public void setHealth(int health)
//     {
//         slider.DOValue(health, fillDuration);
//     }

//     // Start is called before the first frame update
//     void Start()
//     {
//         setMaxHealth();
//     }

//     // Update is called once per frame
//     void Update()
//     {
        
//     }
// }