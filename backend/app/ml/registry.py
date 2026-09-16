from app.schemas import AnalysisEngine

ADAPTIVE_SEGMENTATION_ENGINE = AnalysisEngine(
    id="adaptive-segmentation-v1",
    name="Segmentation adaptative v1",
    kind="zero-training",
    status="available",
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

CELLPOSE_ENGINE = AnalysisEngine(
    id="cellpose-pretrained",
    name="Cellpose préentraîné",
    kind="pretrained",
    status="license-review",
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
    kind="pretrained",
    status="experimental",
    description=(
        "Moteur spécialisé en microscopie, intégré dans un environnement de benchmark isolé."
    ),
    training_required=False,
    limitations=[
        "Pas encore activé dans le chemin d'inférence de production.",
        "Benchmark BBBC019 zéro-shot requis avant décision de promotion.",
        "Empreinte mémoire plus élevée que la baseline adaptative.",
    ],
)


def list_engines() -> list[AnalysisEngine]:
    return [ADAPTIVE_SEGMENTATION_ENGINE, MICRO_SAM_ENGINE, CELLPOSE_ENGINE]


def get_available_engine(engine_id: str) -> AnalysisEngine:
    if engine_id != ADAPTIVE_SEGMENTATION_ENGINE.id:
        raise ValueError(f"Inference engine '{engine_id}' is not available")
    return ADAPTIVE_SEGMENTATION_ENGINE
