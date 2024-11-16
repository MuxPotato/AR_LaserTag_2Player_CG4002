using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

[AddComponentMenu("Nokobot/Modern Guns/Simple Shoot")]
public class SimpleShoot : MonoBehaviour
{

    public Button shootButton; 

    [Header("Prefab Refrences")]
    public GameObject bulletPrefab;
    public GameObject casingPrefab;
    public GameObject muzzleFlashPrefab;

    [Header("Audio Settings")]
    public AudioSource gunshotAudioSource;  // Reference to the AudioSource component for gunshot sound
    public AudioClip gunshotClip;  // Gunshot sound effect




    [Header("Location Refrences")]
    [SerializeField] private Animator gunAnimator;
    [SerializeField] private Transform barrelLocation;
    [SerializeField] private Transform casingExitLocation;

    [Header("Settings")]
    [Tooltip("Specify time to destory the casing object")] [SerializeField] private float destroyTimerCasing = 2f;
    [Tooltip("Specify time to destory the muzzle flash object")] [SerializeField] private float destroyTimerMuzzleFlash = 2f;
    [Tooltip("Specify time to destory the bullet object")] [SerializeField] private float destroyTimerBullet = 2f;

    [Tooltip("Specify time to destory the bullet object")] [SerializeField] private float casingEjectUpForce = 2f;
    [Tooltip("Specify time to destory the bullet object")] [SerializeField] private float casingEjectRightForce = 2f;
    [Tooltip("Specify time to destory the bullet object")] [SerializeField] private float casingEjectRadius = 2f;

    [Tooltip("Bullet Speed")] [SerializeField] private float shotPower = 500f;
    [Tooltip("Casing Ejection Speed")] [SerializeField] private float ejectPower = 150f;
    [Tooltip("Casing Ejection Speed")] [SerializeField] private float tonquePowerMin = 150f;
    [Tooltip("Casing Ejection Speed")] [SerializeField] private float tonquePowerMax = 150f;

    public Animator sliderAnimator;


    void Start()
    {
        if (barrelLocation == null)
            barrelLocation = transform;

        if (gunAnimator == null)
            gunAnimator = GetComponentInChildren<Animator>();


        if (shootButton != null)
        {
            shootButton.onClick.AddListener(Shoot);
            shootButton.onClick.AddListener(fire_animation); 
        }


         // Ensure the AudioSource is set up
        if (gunshotAudioSource == null)
        {
            gunshotAudioSource = gameObject.AddComponent<AudioSource>();
        }
        gunshotAudioSource.clip = gunshotClip;
    }

    public void shootBullet()
    {
        Shoot();
        fire_animation();
    }

    void fire_animation()
    {
        gunAnimator.SetTrigger("Fire"); 
    }


    void Update()
    {
        // //If you want a different input, change it here
        // if (Input.GetButtonDown("Fire1"))
        // {
        //     //Calls animation on the gun that has the relevant animation events that will fire
        //     gunAnimator.SetTrigger("Fire");
        // }
    }


    //This function creates the bullet behavior
    void Shoot()
    {

        // Disable the Slider's Animator to prevent idle animation
        if (sliderAnimator != null)
        {
            sliderAnimator.enabled = false;
        }

        if (muzzleFlashPrefab)
        {
            //Create the muzzle flash
            GameObject tempFlash;
            tempFlash = Instantiate(muzzleFlashPrefab, barrelLocation.position, barrelLocation.rotation);

            //Destroy the muzzle flash effect
            Destroy(tempFlash, destroyTimerMuzzleFlash);
        }

         // Play the gunshot sound
        if (gunshotAudioSource != null && gunshotClip != null)
        {
            gunshotAudioSource.Play();
        }

        //cancels if there's no bullet prefeb
        if (!bulletPrefab)
        { return; }

        // Create a bullet and add force on it in direction of the barrel
        
        // OLD
        //Instantiate(bulletPrefab, barrelLocation.position, barrelLocation.rotation).GetComponent<Rigidbody>().AddForce(barrelLocation.forward * shotPower);
        
        
        GameObject tempBullet;
        tempBullet = Instantiate(bulletPrefab, barrelLocation.position, barrelLocation.rotation) as GameObject;
        tempBullet.GetComponent<Rigidbody>().AddForce(barrelLocation.forward * shotPower);
        Destroy(tempBullet, destroyTimerBullet);

        if (sliderAnimator != null)
        {
            sliderAnimator.enabled = true;
        }

    }

    //This function creates a casing at the ejection slot
    void CasingRelease()
    {
        //Cancels function if ejection slot hasn't been set or there's no casing
        if (!casingExitLocation || !casingPrefab)
        { return; }



        // Code not working, TODO
        
        // //Create the casing
        // GameObject tempCasing;
        // tempCasing = Instantiate(casingPrefab, casingExitLocation.position, casingExitLocation.rotation) as GameObject;
        // //Add force on casing to push it out
        // tempCasing.GetComponent<Rigidbody>().AddExplosionForce(Random.Range(ejectPower * 0.7f, ejectPower), (casingExitLocation.position - casingExitLocation.right * casingEjectRightForce - casingExitLocation.up * casingEjectUpForce), casingEjectRadius);
        // //Add torque to make casing spin in random direction
        // tempCasing.GetComponent<Rigidbody>().AddTorque(new Vector3(0, Random.Range(tonquePowerMin, tonquePowerMax), Random.Range(tonquePowerMin, tonquePowerMax)), ForceMode.Impulse);

        // //Destroy casing after X seconds
        // Destroy(tempCasing, destroyTimerCasing);
    }

}
