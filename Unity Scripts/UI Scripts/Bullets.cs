using UnityEngine;
using System.Collections;
using System.Collections.Generic;
using TMPro; // Import the TextMeshPro namespace
using DG.Tweening;
using UnityEngine.UI;
public class Bullets : MonoBehaviour
{
    public GameObject bulletPrefab; // Reference to the bullet prefab
    public Transform bulletParent;  // Parent transform to hold bullet instances (optional)
    public TextMeshProUGUI reloadTextTMP; // Reference to the "RELOAD RELOAD" TextMeshProUGUI element
    private List<GameObject> bullets = new List<GameObject>(); // List to keep track of bullet instances

    public float bulletVisualGap = 50f;
    private int maxAmmo = 6;  // Maximum ammo count
    private Coroutine reloadCoroutine; // Coroutine to handle flashing text
    public float ReloadFlashInterval = 0.3f;

    public GameObject reloadBar;
    public Slider reloadSlider;
    public float reloadTime = 2.5f;

    public Animator gunAnimator;
    public Animator sliderAnimator;



    void Start()
    {
        InstantiateBullets();  // Instantiate bullets at the start
        //SetAmmo(maxAmmo);  // Initialize with full ammo
        reloadBar.SetActive(false);
        reloadTextTMP.gameObject.SetActive(false); 
    }

    // Method to instantiate bullet prefabs
    void InstantiateBullets()
    {
        for (int i = 0; i < maxAmmo; i++)
        {
            // Instantiate a bullet prefab and set its parent
            GameObject bullet = Instantiate(bulletPrefab, bulletParent);
            
            // Position bullets in a line or as desired
            bullet.transform.localPosition = new Vector3(i * bulletVisualGap, 0f, 0f); // Adjust spacing as needed

            bullets.Add(bullet); // Add the bullet to the list
        }
    }

    // Method to set the number of bullets displayed
    public void SetAmmo(int count)
    {
        // Clamp the count to ensure it's within valid range
        count = Mathf.Clamp(count, 0, maxAmmo);

        // Update the visibility of bullets based on the ammo count
        for (int i = 0; i < bullets.Count; i++)
        {
            if (i < count)
            {
                bullets[i].SetActive(true); // Show bullets within the ammo count
            }
            else
            {
                bullets[i].SetActive(false); // Hide bullets beyond the ammo count
            }
        }

        // Show flashing "RELOAD RELOAD" text if no bullets are left
        if (count == 0)
        {
            if (reloadCoroutine == null) // Start flashing only if it's not already running
            {
                reloadCoroutine = StartCoroutine(FlashReloadText());
            }
        }
        else
        {
            if (reloadCoroutine != null) // Stop flashing when there are bullets
            {
                StopCoroutine(reloadCoroutine);
                reloadCoroutine = null;
            }
            reloadTextTMP.gameObject.SetActive(false); // Hide the reload text
        }
    }

    // Coroutine to flash the "RELOAD RELOAD" text
    IEnumerator FlashReloadText()
    {
        reloadTextTMP.gameObject.SetActive(true); // Enable the text to make it visible

        while (true) // Infinite loop to keep flashing
        {
            reloadTextTMP.enabled = !reloadTextTMP.enabled; // Toggle text visibility
            yield return new WaitForSeconds(ReloadFlashInterval); // Wait for 0.5 seconds
        }
    }

    // Method to reset ammo (e.g., reload)
    public void ReloadAmmo()
    {   
        for (int i = 0; i < bullets.Count; i++)
        {
            bullets[i].SetActive(false); // Hide bullets beyond the ammo count
        }

        reloadTextTMP.gameObject.SetActive(false); // Hide the reload text
        // Enable the reload bar
        reloadBar.SetActive(true);

        // Set the slider value to 0
        reloadSlider.value = 0;


        // Disable the Slider's Animator to prevent idle animation
        if (sliderAnimator != null)
        {
            sliderAnimator.enabled = false;
        }

        // Play the reload animation on the gun
        if (gunAnimator != null)
        {
            gunAnimator.SetTrigger("ReloadTrigger"); // Assuming you have a "Reload" trigger in your Animator
        }

        SetAmmo(0); // Needed bcs updateBothPlayersGameState() in game state script goes first and ask UI to update 6 bullets before
        // reload bar finishes -> bug: means player can already fire before reload is finished, that is a small gap


        // Tween the slider value from 0 to 1 over 1.5 seconds
        reloadSlider.DOValue(1, reloadTime).SetEase(Ease.Linear).OnComplete(() =>
        {
            // Disable the reload bar after the tween is complete
            reloadBar.SetActive(false);

            SetAmmo(maxAmmo); // Reset ammo count to maximum


            // Re-enable the Slider's Animator to allow idle animation to play again
            if (sliderAnimator != null)
            {
                sliderAnimator.enabled = true;
            }
        });

        
    }
}
