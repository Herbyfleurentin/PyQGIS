import sys
from qgis.core import QgsApplication, QgsPointXY, QgsGeometry, QgsFeature, QgsField, QgsVectorLayer, QgsProject
from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import QFileDialog
import requests
import pandas as pd

# Convertir sys.argv en bytes
sys.argv = [arg.encode('utf-8') for arg in sys.argv]

# Initialiser l'application QGIS
QgsApplication.setPrefixPath("C:/Program Files/QGIS 3.28/apps/qgis", True)  # Remplace par ton chemin d'installation QGIS
qgs = QgsApplication(sys.argv, False)
qgs.initQgis()

# Afficher une boîte de dialogue pour sélectionner le fichier CSV
csv_file, _ = QFileDialog.getOpenFileName(None, "Sélectionner le fichier CSV", "", "Fichiers CSV (*.csv)")

# Si aucun fichier n'est sélectionné, on quitte
if not csv_file:
    print("Aucun fichier CSV sélectionné. Le programme va se fermer.")
    qgs.exitQgis()
    exit()

# Charger le fichier CSV dans un DataFrame pandas
try:
    df = pd.read_csv(csv_file)
except Exception as e:
    print(f"Erreur lors du chargement du fichier CSV : {e}")
    qgs.exitQgis()
    exit()

# Vérification de la colonne 'adresse'
if 'adresse' not in df.columns:
    print("La colonne 'adresse' est manquante dans le fichier CSV.")
    qgs.exitQgis()
    exit()

# Modifier la colonne 'adresse' en remplaçant les espaces par des '+'
df['adresse'] = df['adresse'].str.replace(' ', '+')

# Sauvegarder le DataFrame modifié dans un nouveau fichier CSV
nouveau_chemin_csv = 'C:/Users/fleur/script'  # Remplace par ton chemin
try:
    df.to_csv(nouveau_chemin_csv, index=False)
    print(f"Le fichier CSV modifié a été sauvegardé à : {nouveau_chemin_csv}")
except Exception as e:
    print(f"Erreur lors de la sauvegarde du fichier CSV : {e}")
    qgs.exitQgis()
    exit()

# Créer une couche vectorielle sans géométrie depuis le fichier CSV modifié
uri = f'file:///{nouveau_chemin_csv.replace("\\", "/")}?delimiter=,'  
adresses = QgsVectorLayer(uri, 'adresses', 'delimitedtext')

# Vérifier la validité de la couche
if not adresses.isValid():
    print("Erreur : La couche n'est pas valide.")
    qgs.exitQgis()
    exit()

print("La couche CSV a été chargée avec succès.")

# Créer une couche vectorielle en mémoire pour les résultats
layer = QgsVectorLayer("Point?crs=epsg:4326", "Pointlayer", "memory")
pr = layer.dataProvider()

# Ajouter les champs à la couche
pr.addAttributes([QgsField("label", QVariant.String),
                  QgsField("score", QVariant.Double),
                  QgsField("housenumber", QVariant.String),
                  QgsField("id", QVariant.String),
                  QgsField("name", QVariant.String),
                  QgsField("postcode", QVariant.String),
                  QgsField("citycode", QVariant.String),
                  QgsField("x", QVariant.Double),
                  QgsField("y", QVariant.Double),
                  QgsField("city", QVariant.String),
                  QgsField("district", QVariant.String),
                  QgsField("context", QVariant.String),
                  QgsField("type", QVariant.String),
                  QgsField("importance", QVariant.Double),
                  QgsField("street", QVariant.String)])

layer.updateFields()

# Effectuer les requêtes API pour chaque adresse
response_list = []

for entite in adresses.getFeatures():
    api_url = f'https://api-adresse.data.gouv.fr/search/?q={entite["adresse"]}&limit=1'
    print(f"Requête vers l'API: {api_url}")

    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP
        data = response.json()
        response_list.append(data)
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la requête API pour l'adresse {entite['adresse']} : {e}")
        response_list.append(None)

# Ajouter les points géographiques à la couche
if response_list:
    for index, data in enumerate(response_list):
        if data and 'features' in data:
            for feature in data['features']:
                if feature['geometry']['coordinates']:
                    x, y = feature['geometry']['coordinates']
                    geometry = QgsGeometry.fromPointXY(QgsPointXY(x, y))
                    new_feature = QgsFeature()
                    new_feature.setGeometry(geometry)

                    # Ajouter les attributs du feature
                    attributes = [
                        feature['properties'].get('label', ''),
                        feature['properties'].get('score', 0),
                        feature['properties'].get('housenumber', ''),
                        feature['properties'].get('id', ''),
                        feature['properties'].get('name', ''),
                        feature['properties'].get('postcode', ''),
                        feature['properties'].get('citycode', ''),
                        x,  # Coordonnée X
                        y,  # Coordonnée Y
                        feature['properties'].get('city', ''),
                        feature['properties'].get('district', ''),
                        feature['properties'].get('context', ''),
                        feature['properties'].get('type', ''),
                        feature['properties'].get('importance', 0),
                        feature['properties'].get('street', '')
                    ]
                    new_feature.setAttributes(attributes)
                    pr.addFeature(new_feature)
else:
    print("Aucune donnée valide n'a été récupérée de l'API.")

# Rafraîchir la couche dans QGIS
QgsProject.instance().addMapLayer(layer)

# Fermer QGIS après l'exécution
qgs.exitQgis()
