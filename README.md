# World Cup FC

Fantasy World Cup Streamlit app for eight fixed coaches:

Benji, Jeff, Peter, Chad, Lamp, Herb, Jayme, Spencer.

Each coach drafts 8 national teams and 2 star players. The draft order is fixed in code and cannot be edited in Admin.

## Run

```bash
streamlit run app.py
```

## Persistence

The app stores shared state in `draft_state.json`.

On Streamlit Cloud, add these secrets:

```toml
[GITHUB]
TOKEN = "your_github_token"
OWNER = "theleitas"
REPO_NAME = "world-cup-fc"

[FOOTBALL_DATA]
TOKEN = "optional_football_data_api_token"
```

If no GitHub token is present, the app reads and writes local `draft_state.json`.

## Admin

Password: `0102`

Admin can edit coach colors, the 25-player pool, odds, expected points, match results, player stats, advancement bonuses, and reset draft picks.

Admin cannot edit draft order.

## Data Seeds

- Qualified teams are seeded from FIFA's official 48-team qualified list.
- Futures odds are seeded from current pre-tournament winner markets and remain editable in Admin.
- Match data can refresh from Football-Data.org when a token is configured; otherwise use the manual match table in Admin.

## Assets

Root-level assets expected by the app:

- `titlethumb.png`
- `Benji.png`
- `Jeff.png`
- `Peter.png`
- `Chad.png`
- `Lamp.png`
- `Herb.png`
- `Jayme.png`
- `Spencer.png`
