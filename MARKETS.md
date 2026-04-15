# APEX BOT V2 — Catalogue des marchés Phase 1

Tous les marchés sont calculés à partir de la **matrice de probabilités de scores** produite par le modèle Dixon-Coles. La matrice `P[i][j]` représente la probabilité que l'équipe domicile marque `i` buts et l'équipe extérieure `j` buts (i, j ∈ [0..10]).

---

## Marché 1 : Match Result (1X2)

**Nom :** Match Result / 1X2  
**Clé API The Odds API :** `h2h`

### Formule de calcul

```
P(home_win)  = Σ P[i][j]  pour tous i > j    (victoire domicile)
P(draw)      = Σ P[i][j]  pour tous i == j   (match nul)
P(away_win)  = Σ P[i][j]  pour tous i < j    (victoire extérieur)

Vérification : P(home_win) + P(draw) + P(away_win) = 1.0
```

### Formule de calcul de la value

```
fair_odds_home = 1 / P(home_win)
best_bookie_odds_home = max(odds["home"] pour chaque bookmaker)
ev_home = (P(home_win) * best_bookie_odds_home) - 1

# Équivalent :
ev = model_prob * demarginized_odds - 1
```

### Seuil de value minimum recommandé
- EV minimum : **+5%** (0.05)
- Cote minimum : **1.50** (éviter les énormes favoris)
- Cote maximum : **5.00** (éviter les trop grands outsiders)

### Exemple concret
**Match :** Arsenal (dom.) vs Chelsea (ext.)  
**Cote bookmaker Arsenal :** 2.10  
**Probabilité modèle Arsenal :** 0.52  

```
Démarginisation (power method) des cotes bookmaker {2.10, 3.50, 3.20} :
  Marge brute = 1/2.10 + 1/3.50 + 1/3.20 = 0.476 + 0.286 + 0.313 = 1.075
  Marge (vig) = 7.5%
  fair_odds_home = 2.10 * (1.075)^k   [k calculé par méthode de Newton]
  → fair_odds_home ≈ 2.25
  → fair_prob_home ≈ 1/2.25 = 0.444

EV = P(modèle) × cote_bookie - 1
   = 0.52 × 2.10 - 1
   = 1.092 - 1
   = +9.2% ✅ (dépasse le seuil de +5%)
```

---

## Marché 2 : Over/Under 2.5 buts

**Nom :** Totals — Over/Under 2.5  
**Clé API The Odds API :** `totals` (avec `description: "2.5"`)

### Formule de calcul

```
P(over_2.5)  = Σ P[i][j]  pour tous (i + j) > 2   (3+ buts au total)
P(under_2.5) = Σ P[i][j]  pour tous (i + j) < 3   (0, 1 ou 2 buts au total)

Vérification : P(over_2.5) + P(under_2.5) = 1.0
```

**Généralisation pour Over/Under X.5 :**
```
P(over_N.5) = Σ P[i][j]  pour tous (i + j) > N
```

### Seuil de value minimum recommandé
- EV minimum : **+5%**
- Cote minimum : **1.60** (marché très équilibré, cotes rarement > 2.20)
- Remarque : ce marché est le plus liquide et le moins exploitable sur les bookmakers classiques

### Exemple concret
**Match :** Arsenal vs Chelsea  
**Cote bookmaker Over 2.5 :** 1.85  
**Probabilité modèle Over 2.5 :** 0.60  

```
EV = 0.60 × 1.85 - 1 = 1.11 - 1 = +11% ✅
```

---

## Marché 3 : Both Teams to Score (BTTS)

**Nom :** Both Teams to Score  
**Clé API The Odds API :** `btts`

### Formule de calcul

```
P(BTTS_yes) = Σ P[i][j]  pour tous i > 0 ET j > 0
            = 1 - P(home_clean_sheet) - P(away_clean_sheet) + P(0-0)

Décomposition :
  P(home_clean_sheet) = Σ P[i][0]  pour tous i  (Chelsea ne marque pas)
  P(away_clean_sheet) = Σ P[0][j]  pour tous j  (Arsenal ne marque pas)
  P(0-0)              = P[0][0]

P(BTTS_yes) = 1 - Σ P[i][0] - Σ P[0][j] + P[0][0]
P(BTTS_no)  = 1 - P(BTTS_yes)
```

### Seuil de value minimum recommandé
- EV minimum : **+5%**
- Remarque : le BTTS est un marché où les bookmakers ont souvent de mauvaises estimations

### Exemple concret
**Match :** Arsenal vs Chelsea  
**Cote bookmaker BTTS Yes :** 1.75  
**Probabilité modèle BTTS Yes :** 0.62  

```
EV = 0.62 × 1.75 - 1 = 1.085 - 1 = +8.5% ✅
```

---

## Marché 4 : Asian Handicap

**Nom :** Asian Handicap  
**Clé API The Odds API :** `asian_handicap`

### Principe
L'Asian Handicap élimine le match nul en donnant un avantage fictif à l'équipe plus faible. Les handicaps courants Phase 1 : -0.5, +0.5, -1.0, +1.0.

- **AH -0.5 (équipe domicile)** : L'équipe domicile doit gagner pour que le pari soit gagnant.
- **AH +0.5 (équipe domicile)** : L'équipe domicile doit ne pas perdre (victoire ou nul).

### Formule de calcul

```
# Asian Handicap -0.5 (home) = équivalent à "domicile gagne"
P(AH_home_-0.5) = P(home_win)
                = Σ P[i][j]  pour tous i > j

# Asian Handicap +0.5 (home) = équivalent à "domicile ne perd pas"
P(AH_home_+0.5) = P(home_win) + P(draw)
                = Σ P[i][j]  pour tous i >= j

# Asian Handicap -1.0 (home) = domicile gagne par 2+ buts
P(AH_home_-1.0) = Σ P[i][j]  pour tous (i - j) > 1

# Asian Handicap -1.0 remboursement = domicile gagne exactement par 1 but
P(AH_home_-1.0_push) = Σ P[i][j]  pour tous (i - j) == 1

P(AH_home_-1.0_effective) = P(AH_home_-1.0) + 0.5 * P(AH_home_-1.0_push)
```

### Seuil de value minimum recommandé
- EV minimum : **+4%** (marché très liquide, moins de marge bookmaker)
- Cotes typiques : 1.85-2.05 (proches de 50/50)

### Exemple concret
**Match :** Arsenal vs Chelsea  
**Cote bookmaker AH Arsenal -0.5 :** 2.05  
**Probabilité modèle victoire Arsenal :** 0.52  

```
EV = 0.52 × 2.05 - 1 = 1.066 - 1 = +6.6% ✅
```

---

## Marché 5 : Double Chance

**Nom :** Double Chance  
**Clé API The Odds API :** `double_chance`

### Principe
Permet de parier sur deux des trois issues possibles simultanément. Moins risqué, mais cotes plus basses.

- **1X** : Victoire domicile OU match nul
- **X2** : Match nul OU victoire extérieur
- **12** : Victoire domicile OU victoire extérieur (pas de nul)

### Formule de calcul

```
P(1X) = P(home_win) + P(draw)
      = Σ P[i][j]  pour tous i >= j

P(X2) = P(draw) + P(away_win)
      = Σ P[i][j]  pour tous i <= j

P(12) = P(home_win) + P(away_win)
      = 1 - P(draw)
      = 1 - Σ P[i][j]  pour tous i == j

Vérifications :
  P(1X) + P(away_win) = 1
  P(X2) + P(home_win) = 1
  P(12) + P(draw)     = 1
```

### Seuil de value minimum recommandé
- EV minimum : **+3%** (cotes très basses, seuil abaissé)
- Cote minimum : **1.20** (seuil abaissé car cotes naturellement basses)
- Remarque : marché utile quand un gros favori a une probabilité modèle très supérieure aux cotes

### Exemple concret
**Match :** Arsenal vs Chelsea  
**Cote bookmaker 1X :** 1.38  
**Probabilité modèle 1X :** 0.75 (= 0.52 victoire + 0.23 nul)  

```
EV = 0.75 × 1.38 - 1 = 1.035 - 1 = +3.5% ✅ (dépasse le seuil de +3%)
```

---

## Récapitulatif des marchés Phase 1

| Marché | Clé API | EV Min | Cote Min | Cote Max | Difficulté implémentation |
|--------|---------|--------|----------|----------|--------------------------|
| 1X2 | `h2h` | +5% | 1.50 | 5.00 | Facile |
| Over/Under | `totals` | +5% | 1.60 | 3.00 | Facile |
| BTTS | `btts` | +5% | 1.50 | 3.50 | Facile |
| Asian Handicap | `asian_handicap` | +4% | 1.75 | 2.20 | Moyen (push cases) |
| Double Chance | `double_chance` | +3% | 1.20 | 2.50 | Facile |

---

## Méthode de démarginisation : Power Method

Étant donné les cotes bookmaker `[o1, o2, o3]` :

```python
import numpy as np
from scipy.optimize import brentq

def demargin_power(odds: list[float]) -> list[float]:
    """
    Retire la marge du bookmaker via la méthode 'power'.
    Trouve k tel que : sum(1/o_i^k) = 1
    Probabilité vraie : p_i = (1/o_i)^k
    """
    implied = [1 / o for o in odds]
    overround = sum(implied)

    def equation(k):
        return sum(p**k for p in implied) - 1.0

    k = brentq(equation, 0.5, 2.0)  # k=1 = méthode additive
    true_probs = [p**k for p in implied]
    return true_probs
```

Pour un match avec `[2.10, 3.50, 3.20]` :
- Probs implicites : [0.476, 0.286, 0.313] → total = 1.075 (marge 7.5%)
- Après power method : [0.455, 0.270, 0.275] → total = 1.000
- fair_odds : [2.20, 3.70, 3.64]
