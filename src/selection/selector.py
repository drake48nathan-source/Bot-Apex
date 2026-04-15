"""
Sélection finale des value bets pour le coupon quotidien.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.core.config import settings
from src.core.logging import get_logger
from src.models.markets import asian_handicap, btts, double_chance, result, totals
from src.models.dixon_coles import DixonColesModel
from src.selection.kelly import KellyCriterion
from src.selection.value_calculator import ValueCalculator

logger = get_logger(__name__)

# Mapping marché → module de calcul et outcomes
MARKET_OUTCOMES: dict[str, list[str]] = {
    "h2h": ["home", "draw", "away"],
    "totals": ["over", "under"],
    "btts": ["yes", "no"],
    "asian_handicap": ["home", "away"],
    "double_chance": ["1X", "X2", "12"],
}

OUTCOME_LABELS: dict[str, dict[str, str]] = {
    "h2h": {"home": "Victoire Domicile", "draw": "Match Nul", "away": "Victoire Extérieur"},
    "totals": {"over": "Plus de 2.5 buts", "under": "Moins de 2.5 buts"},
    "btts": {"yes": "Les deux équipes marquent", "no": "Pas les deux équipes"},
    "asian_handicap": {"home": "AH Domicile -0.5", "away": "AH Extérieur +0.5"},
    "double_chance": {"1X": "Domicile ou Nul", "X2": "Nul ou Extérieur", "12": "Domicile ou Extérieur"},
}


@dataclass
class SelectedBet:
    match_name: str
    league: str
    kickoff_utc: datetime
    market: str
    outcome: str
    outcome_label: str
    bookmaker: str
    odds: float
    model_prob: float
    fair_odds: float
    ev: float
    kelly_pct: float
    confidence: str
    match_id: str = ""
    prediction_id: int | None = None

    @property
    def ev_pct(self) -> str:
        sign = "+" if self.ev >= 0 else ""
        return f"{sign}{self.ev * 100:.1f}%"

    @property
    def kelly_pct_str(self) -> str:
        return f"{self.kelly_pct * 100:.1f}%"


class ValueBetSelector:
    """
    Sélectionne les meilleurs value bets du jour.

    Combine le modèle Dixon-Coles, le ValueCalculator et le KellyCriterion
    pour produire une liste filtrée et classée de paris.
    """

    MIN_KELLY_PCT: float = 0.005  # 0.5% minimum de bankroll

    def __init__(self) -> None:
        self.calculator = ValueCalculator()
        self.kelly = KellyCriterion()

    def select_from_events(
        self,
        events: list[dict[str, Any]],
        model: DixonColesModel,
    ) -> list[SelectedBet]:
        """
        Pipeline complet : événements The Odds API → liste de SelectedBet.

        Args:
            events: Liste d'événements au format The Odds API (avec bookmakers + cotes).
            model: Modèle Dixon-Coles calibré.

        Returns:
            Liste de SelectedBet triée par EV décroissant, max MAX_BETS_PER_DAY.
        """
        candidates: list[SelectedBet] = []

        for event in events:
            home_team = event.get("home_team", "")
            away_team = event.get("away_team", "")
            league = event.get("sport_title", event.get("sport_key", ""))
            match_id = event.get("id", "")
            kickoff_str = event.get("commence_time", "")

            try:
                kickoff = datetime.fromisoformat(kickoff_str.replace("Z", "+00:00"))
            except Exception:
                kickoff = datetime.utcnow()

            bookmakers = event.get("bookmakers", [])
            if not bookmakers:
                continue

            # Calculer la matrice de scores
            try:
                matrix = model.predict_score_matrix(home_team, away_team)
            except Exception as e:
                logger.warning("Could not predict", home=home_team, away=away_team, error=str(e))
                continue

            # Évaluer chaque marché
            for market_key in MARKET_OUTCOMES:
                bets = self._evaluate_market(
                    matrix=matrix,
                    market_key=market_key,
                    home_team=home_team,
                    away_team=away_team,
                    bookmakers=bookmakers,
                    match_name=f"{home_team} vs {away_team}",
                    league=league,
                    kickoff=kickoff,
                    match_id=match_id,
                )
                candidates.extend(bets)

        # Filtrer et classer
        filtered = self._apply_filters(candidates)
        filtered.sort(key=lambda b: b.ev, reverse=True)

        # Dédupliquer : un seul pari par match
        seen_matches: set[str] = set()
        final: list[SelectedBet] = []
        for bet in filtered:
            if bet.match_name not in seen_matches:
                final.append(bet)
                seen_matches.add(bet.match_name)
            if len(final) >= settings.MAX_BETS_PER_DAY:
                break

        logger.info(
            "Value bets selected",
            candidates=len(candidates),
            filtered=len(filtered),
            selected=len(final),
        )
        return final

    def _evaluate_market(
        self,
        matrix: Any,
        market_key: str,
        home_team: str,
        away_team: str,
        bookmakers: list[dict],
        match_name: str,
        league: str,
        kickoff: datetime,
        match_id: str,
    ) -> list[SelectedBet]:
        """Évalue un marché pour un match et retourne les paris candidats."""
        bets: list[SelectedBet] = []

        # Calculer les probabilités modèle pour ce marché
        try:
            probs = self._compute_market_probs(matrix, market_key)
        except Exception:
            return []

        outcomes = MARKET_OUTCOMES.get(market_key, [])
        labels = OUTCOME_LABELS.get(market_key, {})

        for outcome in outcomes:
            model_prob = probs.get(outcome, 0.0)
            if model_prob <= 0 or model_prob >= 1:
                continue

            # Trouver la meilleure cote bookmaker pour cet outcome
            bookie_odds_list = self._extract_odds_for_market(bookmakers, market_key)
            if not bookie_odds_list:
                continue

            # Démarginisation
            try:
                demargin = self.calculator.demargin_power(
                    [o["price"] for o in bookie_odds_list]
                )
            except Exception:
                continue

            # Meilleure cote pour cet outcome
            outcome_idx = next(
                (i for i, o in enumerate(bookie_odds_list) if o["outcome"] == outcome),
                None,
            )
            if outcome_idx is None:
                continue

            best_price = bookie_odds_list[outcome_idx]["price"]
            best_bookie = bookie_odds_list[outcome_idx]["bookmaker"]
            fair_odd = demargin.fair_odds[outcome_idx]

            # Chercher la vraie meilleure cote multi-bookmakers
            for bookie_data in bookmakers:
                for mkt in bookie_data.get("markets", []):
                    if mkt.get("key") == market_key:
                        for oc in mkt.get("outcomes", []):
                            oc_name = self._normalize_outcome_name(oc, market_key)
                            if oc_name == outcome:
                                price = float(oc.get("price", 0))
                                if price > best_price:
                                    best_price = price
                                    best_bookie = bookie_data.get("key", "")

            if best_price <= 1.0:
                continue

            # Calculer EV et Kelly
            ev = self.calculator.calculate_ev(model_prob, best_price)
            kelly = self.kelly.calculate(model_prob, best_price)

            bet = SelectedBet(
                match_name=match_name,
                league=league,
                kickoff_utc=kickoff,
                market=market_key,
                outcome=outcome,
                outcome_label=labels.get(outcome, outcome),
                bookmaker=best_bookie,
                odds=best_price,
                model_prob=model_prob,
                fair_odds=fair_odd,
                ev=ev,
                kelly_pct=kelly,
                confidence=self._assign_confidence(ev, model_prob),
                match_id=match_id,
            )
            bets.append(bet)

        return bets

    def _compute_market_probs(self, matrix: Any, market_key: str) -> dict[str, float]:
        """Calcule les probabilités pour un marché depuis la matrice."""
        if market_key == "h2h":
            return result.compute(matrix)
        elif market_key == "totals":
            t = totals.compute(matrix, 2.5)
            return {"over": t["over"], "under": t["under"]}
        elif market_key == "btts":
            return btts.compute(matrix)
        elif market_key == "asian_handicap":
            return asian_handicap.compute(matrix, -0.5)
        elif market_key == "double_chance":
            return double_chance.compute(matrix)
        return {}

    def _extract_odds_for_market(
        self, bookmakers: list[dict], market_key: str
    ) -> list[dict]:
        """Extrait les cotes du premier bookmaker disponible pour un marché."""
        for bookie in bookmakers:
            for mkt in bookie.get("markets", []):
                if mkt.get("key") == market_key:
                    outcomes = mkt.get("outcomes", [])
                    return [
                        {
                            "outcome": self._normalize_outcome_name(oc, market_key),
                            "price": float(oc.get("price", 0)),
                            "bookmaker": bookie.get("key", ""),
                        }
                        for oc in outcomes
                        if float(oc.get("price", 0)) > 1.0
                    ]
        return []

    def _normalize_outcome_name(self, outcome: dict, market_key: str) -> str:
        """Normalise le nom d'un outcome The Odds API vers notre convention interne."""
        name = outcome.get("name", "").lower()
        desc = outcome.get("description", "")

        if market_key == "h2h":
            # La première team = home, Draw = draw, deuxième = away
            # On ne peut pas savoir facilement sans contexte — approche simplifiée
            if name == "draw":
                return "draw"
            # On retourne le nom brut, le matching se fait dans _evaluate_market
            return name
        elif market_key == "totals":
            return "over" if name == "over" else "under"
        elif market_key == "btts":
            return "yes" if name == "yes" else "no"
        elif market_key == "asian_handicap":
            return "home" if "home" in name or "-0.5" in desc else "away"
        elif market_key == "double_chance":
            mapping = {"home/draw": "1X", "draw/away": "X2", "home/away": "12",
                       "1x": "1X", "x2": "X2", "12": "12"}
            return mapping.get(name.lower(), name)
        return name

    def _apply_filters(self, candidates: list[SelectedBet]) -> list[SelectedBet]:
        """Applique EV_THRESHOLD, MIN/MAX_ODDS et MIN_KELLY."""
        return [
            b for b in candidates
            if b.ev >= settings.EV_THRESHOLD
            and settings.MIN_ODDS <= b.odds <= settings.MAX_ODDS
            and b.kelly_pct >= self.MIN_KELLY_PCT
        ]

    def _assign_confidence(self, ev: float, model_prob: float) -> str:
        if ev >= 0.10:
            return "high"
        if ev >= 0.05:
            return "medium"
        return "low"
