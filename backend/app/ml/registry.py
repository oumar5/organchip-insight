from app.schemas import AnalysisEngine

ADAPTIVE_SEGMENTATION_ENGINE = AnalysisEngine(
    id="adaptive-segmentation-v1",
    name="Segmentation adaptative v1",
    task="segmentation",
    kind="zero-training",
    status="available",
    runnable=True,
    description=(
        "Segmentation locale par seuillage d'Otsu, morphologie et composantes connexes. "
        "Elle fonctionne immédiatement sans poids ni entraînement."
    ),
    training_required=False,
    limitations=[
        "Résultat exploratoire non validé pour une décision biologique ou clinique.",
        "La séparation des objets en contact reste limitée.",
        "Le premier plan est estimé automatiquement et doit être contrôlé visuellement.",
    ],
)

EXPERIMENTAL_QUALITY_ENGINE = AnalysisEngine(
    id="ooc-quality-cnn-campaign-v2-gray448",
    name="QC CNN campagne v2 — démonstrateur",
    task="quality-classification",
    kind="trained",
    status="experimental",
    runnable=False,
    description=(
        "Démonstrateur ONNX du run B sélectionné sur validation. Il expose uniquement "
        "le softmax brut et impose une revue humaine pour chaque image."
    ),
    training_required=False,
    limitations=[
        "Aucune décision automatique bon/mauvais : toutes les sorties sont « À vérifier ».",
        "Le softmax brut n'est ni calibré ni une probabilité de qualité biologique.",
        "Signal RGB modeste et non distinguable d'un effet de sélection sur la validation.",
        "Domaine observé limité aux modes d'acquisition source L et RGB.",
    ],
)

CELLPOSE_ENGINE = AnalysisEngine(
    id="cellpose-pretrained",
    name="Cellpose préentraîné",
    task="segmentation",
    kind="pretrained",
    status="license-review",
    runnable=False,
    description="Moteur candidat pour la segmentation généraliste de cellules et noyaux.",
    training_required=False,
    limitations=[
        "Non activé tant que la compatibilité de licence des poids n'est pas approuvée.",
        "Téléchargement de poids et ressources de calcul supplémentaires requis.",
    ],
)

MICRO_SAM_ENGINE = AnalysisEngine(
    id="micro-sam-pretrained",
    name="µSAM préentraîné",
    task="segmentation",
    kind="pretrained",
    status="experimental",
    runnable=False,
    description=(
        "Moteur spécialisé en microscopie, intégré dans un environnement de benchmark isolé."
    ),
    training_required=False,
    limitations=[
        "Pas encore activé dans le chemin d'inférence de production.",
        "Benchmark BBBC019 zéro-shot réalisé ; promotion produit encore à intégrer.",
        "Empreinte mémoire plus élevée que la baseline adaptative.",
    ],
)

REGISTERED_ENGINES = (
    ADAPTIVE_SEGMENTATION_ENGINE,
    EXPERIMENTAL_QUALITY_ENGINE,
    MICRO_SAM_ENGINE,
    CELLPOSE_ENGINE,
)
