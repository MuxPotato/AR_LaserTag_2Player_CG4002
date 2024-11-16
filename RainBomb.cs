using UnityEngine;
using UnityEngine.UI;

public class RainBomb : MonoBehaviour
{
    public int maxBombs = 2; // Maximum number of bombs
    private int currentBombs;
    public GameObject bombPrefab; // Prefab for bomb icon + animation
    public Transform rainBombHolder;
    public float bombSpacing;

    void Start()
    {
        currentBombs = maxBombs; // Initialize with max bombs
        UpdateBombUI();
    }

    // Call this function when a bomb is used
    public void setBombs(int numOfBombs)
    {
       
        currentBombs = numOfBombs;
        UpdateBombUI();
    
    }

    // Update the UI to reflect the current number of bombs
    void UpdateBombUI()
    {
        // Clear existing bombs
        foreach (Transform child in rainBombHolder)
        {
            Destroy(child.gameObject);
        }

        // Create a new bomb UI element for each available bomb
        for (int i = 0; i < currentBombs; i++)
        {
            GameObject bombUI = Instantiate(bombPrefab, rainBombHolder); // Parent it to the holder

            // Position the bombs side by side with a set spacing
            RectTransform bombRect = bombUI.GetComponent<RectTransform>();
            if (bombRect != null)
            {
                bombRect.anchoredPosition = new Vector2(i * bombSpacing, 0); // Adjust the x position based on spacing
            }

            // Find the "Water animation" child and get its Animator component
            Transform waterAnimationChild = bombUI.transform.Find("Water animation");
            if (waterAnimationChild != null)
            {
                Animator animator = waterAnimationChild.GetComponent<Animator>();
                if (animator != null)
                {
                    animator.Play("WaterAnimation"); // Replace with your animation name
                }
                else
                {
                    Debug.LogWarning("Animator component is missing on the 'Water animation' child.");
                }
            }
            else
            {
                Debug.LogWarning("Could not find 'Water animation' child in the instantiated bomb prefab.");
            }
        }
    }
}
