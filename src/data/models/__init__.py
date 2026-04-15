# Importer tous les modèles ici pour que SQLAlchemy les découvre via init_db()
from src.data.models.match import Match
from src.data.models.prediction import Prediction

__all__ = ["Match", "Prediction"]
