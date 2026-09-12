import cv2
import matplotlib.pyplot as plt
import os

# 1. Charger l'image originale
image_path = r'd:\PFE\images_test\cin_user.jpg'
image_originale = cv2.imread(image_path)

if image_originale is not None:
    # Convertir de BGR (OpenCV) à RGB (Matplotlib) pour l'affichage couleur correct
    img_rgb = cv2.cvtColor(image_originale, cv2.COLOR_BGR2RGB)
    
    # 2. Conversion en niveaux de gris
    img_gray = cv2.cvtColor(image_originale, cv2.COLOR_BGR2GRAY)
    
    # 3. Flou (Denoising)
    img_blurred = cv2.GaussianBlur(img_gray, (5, 5), 0)
    
    # 4. Seuillage Adaptatif (Adaptive Thresholding)
    img_thresh = cv2.adaptiveThreshold(
        img_blurred, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # 5. Créer une figure Matplotlib pour l'avant/après
    plt.figure(figsize=(12, 6))
    
    # Afficher l'originale
    plt.subplot(1, 2, 1)
    plt.imshow(img_rgb)
    plt.title('Original Document\n(Color + Noise)', fontsize=13)
    plt.axis('off')
    
    # Afficher le résultat OpenCV
    plt.subplot(1, 2, 2)
    plt.imshow(img_thresh, cmap='gray')
    plt.title('After OpenCV Processing\n(Grayscale + Adaptive Thresholding)', fontsize=13)
    plt.axis('off')
    
    # 6. Sauvegarder l'image générée
    output_path = r'd:\PFE\image_opencv_comparaison.png'
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Image generee avec succes : {output_path}")
else:
    print("Erreur : Impossible de lire l'image.")
