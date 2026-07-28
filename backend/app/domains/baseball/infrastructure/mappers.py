from app.domains.baseball.domain.entities import KboGame
from app.domains.baseball.domain.enums import KboGameStatus
from app.domains.baseball.infrastructure.models import KboGameModel


class KboGameMapper:
    """KBO 경기 ORM Model과 Domain Entity 사이를 변환합니다."""

    @staticmethod
    def to_domain(model: KboGameModel) -> KboGame:
        """SQLAlchemy ORM Model을 순수 Domain Entity로 변환합니다."""

        return KboGame(
            id=model.id,
            season_year=model.season_year,
            source_game_id=model.source_game_id,
            internal_game_key=model.internal_game_key,
            game_date=model.game_date,
            start_time=model.start_time,
            starts_at=model.starts_at,
            away_team_id=model.away_team_id,
            home_team_id=model.home_team_id,
            stadium_id=model.stadium_id,
            away_team_name=model.away_team_name,
            home_team_name=model.home_team_name,
            stadium_name=model.stadium_name,
            game_status=KboGameStatus(model.game_status),
            status_reason=model.status_reason,
            away_score=model.away_score,
            home_score=model.home_score,
            source_name=model.source_name,
            source_url=model.source_url,
            source_collected_at=model.source_collected_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
