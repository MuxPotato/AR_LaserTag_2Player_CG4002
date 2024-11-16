using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using DG.Tweening;
using System;

public class HealthBar : MonoBehaviour
{   
    public Slider frontSlider;
    public Slider backSlider;
    private int maxHealth = 100;
    public float backFillDuration = 2.0f;

    public void setMaxHealth()
    {
        frontSlider.maxValue = maxHealth;
        frontSlider.value = maxHealth;
        backSlider.maxValue = maxHealth;
        backSlider.value = maxHealth;
    }

    public void setHealth(int health)
    {
        frontSlider.value = health;
        backSlider.DOValue(health, backFillDuration);
    }

    // Start is called before the first frame update
    void Start()
    {
        setMaxHealth();
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