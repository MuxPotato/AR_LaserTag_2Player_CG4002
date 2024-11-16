using UnityEngine;
using System.Collections;
using System.Collections.Generic;
using TMPro; // Import the TextMeshPro namespace
using DG.Tweening;
using UnityEngine.UI;
public class BulletsEnemy : MonoBehaviour
{
    public GameObject bulletPrefab; // Reference to the bullet prefab
    public Transform bulletParent;  // Parent transform to hold bullet instances (optional)
    private List<GameObject> bullets = new List<GameObject>(); // List to keep track of bullet instances

    public float bulletVisualGap = 50f;
    private int maxAmmo = 6;  // Maximum ammo count




    void Start()
    {
        InstantiateBullets();  // Instantiate bullets at the start
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
    }

  

   
}
