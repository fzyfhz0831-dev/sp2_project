from __future__ import annotations

import os
from pathlib import Path


# This file is the single place for project-wide settings.
# Path(__file__) points to app/pipeline_config.py, so parents[1] is the
# backend project root. Automation can set SP2_PIPELINE_ROOT to keep generated
# data, logs, and archives under sp2-automatic/.
PROJECT_ROOT: Path = Path(
    os.getenv("SP2_PIPELINE_ROOT") or Path(__file__).resolve().parents[1]
).resolve()

# Shared project folders. Keeping these in one file avoids duplicated path logic.
DATA_DIR: Path = PROJECT_ROOT / "data"
LOGS_DIR: Path = PROJECT_ROOT / "logs"
ARCHIVE_DIR: Path = PROJECT_ROOT / "archive"

# Shared output and log files used by the pipeline.
LATEST_INSIGHTS_PATH: Path = DATA_DIR / "latest_insights.json"
PIPELINE_LOG_PATH: Path = LOGS_DIR / "pipeline.log"

# Reddit defaults used by backend/reddit_collector.py.
REDDIT_POST_LIMIT: int = 50
DEFAULT_SUBREDDIT: str = "slaythespire"

# Archive management: keep only the newest N run_insights backup files.
MAX_ARCHIVE_FILES: int = 30
COMPRESS_ARCHIVE: bool = True

# Steam news settings used by backend/steam_news_collector.py.
STEAM_NEWS_APPID: str = "646570"
STEAM_NEWS_COUNT: int = 20

# Additional source settings.
REDDIT_COMMENT_SUBREDDITS: list[str] = ["slaythespire"]
REDDIT_COMMENT_LIMIT: int = 50
STEAM_REVIEW_APPIDS: list[str] = ["646570", "730", "570"]
STEAM_REVIEW_COUNT: int = 20
OFFICIAL_NEWS_URLS: list[str] = [
    "https://store.steampowered.com/feeds/news/app/646570/",
]

# Player run input / parser output used by backend/run_parser.py.
PLAYER_RUN_PATH: Path = DATA_DIR / "player_run.json"
NORMALIZED_RUN_PATH: Path = DATA_DIR / "normalized_run.json"

# Loss classification output used by backend/loss_classifier.py.
LOSS_CLASSIFICATION_PATH: Path = DATA_DIR / "loss_classification.json"

# Run analysis output used by backend/run_analyzer.py.
RUN_ANALYSIS_PATH: Path = DATA_DIR / "run_analysis.json"

# Recommendation outputs used by backend/recommendation_generator.py.
RUN_ANALYSIS_TXT_PATH: Path = DATA_DIR / "run_analysis.txt"
RUN_RECOMMENDATIONS_PATH: Path = DATA_DIR / "run_recommendations.json"

# Alert settings. Replace these placeholders with real SMTP credentials when
# you want email notifications. If they remain placeholders, alerts are logged.
ALERT_EMAIL: str = "your_email@example.com"
SMTP_SERVER: str = "smtp.example.com"
SMTP_PORT: int = 587
SMTP_USER: str = "your_smtp_user"
SMTP_PASSWORD: str = "your_smtp_password"


def ensure_project_directories() -> None:
    """Create folders needed by the data pipeline if they do not exist yet."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
