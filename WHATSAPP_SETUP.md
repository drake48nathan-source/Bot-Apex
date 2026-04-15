# APEX BOT V2 — Guide d'intégration WhatsApp (Meta Cloud API)

---

## Étape 1 : Créer un compte Meta Business

1. Aller sur https://business.facebook.com
2. Cliquer sur "Créer un compte"
3. Renseigner le nom de l'entreprise (ex: "Apex Bot"), votre nom, et votre email professionnel
4. Vérifier l'email et compléter le profil

**Important :** Le compte Meta Business est distinct de votre compte Facebook personnel.

---

## Étape 2 : Créer une application Meta

1. Aller sur https://developers.facebook.com/apps/
2. Cliquer sur "Créer une application"
3. Sélectionner le type : **"Professionnel"**
4. Renseigner :
   - Nom de l'app : "Apex Bot V2"
   - Email de contact
   - Compte Business associé (celui créé à l'étape 1)
5. Cliquer sur "Créer une application"

---

## Étape 3 : Configurer WhatsApp Business

1. Dans le tableau de bord de l'app, chercher **"WhatsApp"** dans la liste des produits
2. Cliquer sur **"Configurer"** à côté de WhatsApp
3. Associer un compte WhatsApp Business Account (WABA) :
   - Soit créer un nouveau WABA
   - Soit lier un WABA existant
4. **Numéro de téléphone :**
   - En mode développement : utiliser le numéro de test fourni par Meta (gratuit)
   - En production : ajouter votre propre numéro de téléphone (doit recevoir un SMS de vérification)
5. Valider le numéro via le code reçu par SMS/appel

**Note :** En mode développement, vous pouvez envoyer des messages à 5 numéros maximum (ajoutés manuellement comme "testeurs").

---

## Étape 4 : Obtenir les tokens

### Token temporaire (développement)
1. Dans l'onglet **WhatsApp > Démarrage rapide**
2. Copier le **"Temporary access token"** (valide 24h)
3. Copier le **"Phone number ID"** (identifiant de votre numéro WhatsApp)
4. Copier le **"WhatsApp Business Account ID"**

### Token permanent (production)
1. Dans les paramètres de l'app, aller dans **"Utilisateurs système"**
2. Créer un utilisateur système avec le rôle "Admin"
3. Cliquer sur **"Générer un nouveau token"**
4. Sélectionner l'application et les permissions : `whatsapp_business_messaging`, `whatsapp_business_management`
5. Le token généré est permanent (valable jusqu'à révocation)

Variables d'environnement à renseigner :
```bash
WHATSAPP_ACCESS_TOKEN=EAAxxxxx...        # Token temporaire ou permanent
WHATSAPP_PHONE_NUMBER_ID=123456789012    # ID du numéro WA Business
WHATSAPP_BUSINESS_ACCOUNT_ID=9876543210 # ID du compte WABA
WHATSAPP_API_VERSION=v19.0
```

---

## Étape 5 : Tester avec curl

### Envoyer un message texte à un numéro de test
```bash
curl -X POST \
  "https://graph.facebook.com/v19.0/${PHONE_NUMBER_ID}/messages" \
  -H "Authorization: Bearer ${WHATSAPP_ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "messaging_product": "whatsapp",
    "recipient_type": "individual",
    "to": "+33612345678",
    "type": "text",
    "text": {
      "preview_url": false,
      "body": "Test depuis Apex Bot V2 🚀"
    }
  }'
```

Réponse attendue :
```json
{
  "messaging_product": "whatsapp",
  "contacts": [{"input": "+33612345678", "wa_id": "33612345678"}],
  "messages": [{"id": "wamid.HBgN..."}]
}
```

### Vérifier le statut d'un message
```bash
curl -X GET \
  "https://graph.facebook.com/v19.0/${WHATSAPP_MESSAGE_ID}" \
  -H "Authorization: Bearer ${WHATSAPP_ACCESS_TOKEN}"
```

---

## Étape 6 : Variables d'environnement à configurer

```bash
# Copier .env.example vers .env
cp .env.example .env

# Renseigner les variables WhatsApp
WHATSAPP_ACCESS_TOKEN=votre_token
WHATSAPP_PHONE_NUMBER_ID=votre_phone_number_id
WHATSAPP_BUSINESS_ACCOUNT_ID=votre_waba_id
WHATSAPP_API_VERSION=v19.0
WHATSAPP_RECIPIENTS=+33612345678,+33687654321  # Destinataires séparés par virgule

# En développement uniquement :
# Ajouter les numéros destinataires dans Meta Developer Console > WhatsApp > Testeurs
```

---

## Format des messages WhatsApp

### Type 1 : Coupon quotidien

Envoyé chaque matin à 06h30 UTC. Contient les meilleurs value bets du jour.

```
🎯 APEX BOT — Coupon du 15/12/2024

📊 FOOTBALL - PREMIER LEAGUE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ Arsenal vs Chelsea
   Marché : Victoire Arsenal (1X2)
   Cote : 2.10 @ Bet365
   EV : +9.2% | Kelly : 3.2%
   Confiance : ⭐⭐⭐

2️⃣ Man City vs Liverpool
   Marché : Over 2.5 buts
   Cote : 1.85 @ Unibet
   EV : +7.1% | Kelly : 2.8%
   Confiance : ⭐⭐

3️⃣ Tottenham vs Man Utd
   Marché : BTTS Oui
   Cote : 1.72 @ Betclic
   EV : +5.8% | Kelly : 2.1%
   Confiance : ⭐⭐

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 EV moyen du coupon : +7.4%
💰 Mise recommandée : 2-3 unités par pari
⚠️ Paris à titre informatif uniquement
```

---

### Type 2 : Alerte value bet (temps réel)

Envoyée dès qu'une nouvelle value bet est détectée (mouvement de cotes).

```
⚡ ALERTE VALUE BET

⚽ Barcelone vs Real Madrid
🕐 Coup d'envoi : 21h00 UTC

📊 Marché : Asian Handicap Barça -0.5
💶 Meilleure cote : 2.08 @ Bwin
📈 EV : +11.4% (probabilité modèle : 0.54)
⚖️ Kelly recommandé : 4.1% de bankroll

🔥 Alerte déclenchée : mouvement de cote
   Cote il y a 1h : 1.95 → maintenant : 2.08
   (bookmaker recalibré à la baisse)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Information uniquement | Vérifiez les cotes avant de parier
```

---

### Type 3 : Analyse match détaillée

Envoyée sur demande ou automatiquement pour les matchs avec EV > 10%.

```
🔍 ANALYSE — Arsenal vs Chelsea
📅 Dimanche 15/12/2024 | 16h30 UTC | Emirates Stadium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 PRÉDICTIONS MODÈLE (Dixon-Coles v1.2)

Score le plus probable : 2-1 (8.3%)
Distribution :
  Victoire Arsenal : 52% (cote fair : 1.92)
  Match nul       : 23% (cote fair : 4.35)
  Victoire Chelsea : 25% (cote fair : 4.00)

Over 2.5 buts : 60% (cote fair : 1.67)
BTTS Oui      : 62% (cote fair : 1.61)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 FORME RÉCENTE (5 derniers matchs)

Arsenal  : WWWDW | Buts pour : 2.4/match | Contre : 0.8/match
Chelsea  : WLWDL | Buts pour : 1.6/match | Contre : 1.4/match

H2H (5 derniers) :
  Arsenal 3 - Chelsea 2 (2024)
  Arsenal 1 - Chelsea 1 (2024)
  Chelsea 2 - Arsenal 1 (2023)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ VALUE BETS DÉTECTÉES

✅ Arsenal Victoire @ 2.10 (Bet365) → EV +9.2%
✅ Over 2.5 @ 1.85 (Unibet)        → EV +11.0%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Information uniquement | Pariez de manière responsable
```

---

## Limites et contraintes

| Contrainte | Valeur | Impact |
|-----------|--------|--------|
| Longueur maximale d'un message | 4 096 caractères | Tronquer le coupon si > 10 matchs |
| Fenêtre de conversation | 24h après dernier message reçu | Utiliser des templates hors fenêtre |
| Quota gratuit | 1 000 conversations/mois | Suffit pour usage personnel (30/mois) |
| Rate limit API | ~80 messages/seconde | Pas un problème pour notre volume |
| Templates WhatsApp | Doivent être approuvés par Meta (24-48h) | Préparer les templates avant le lancement |
