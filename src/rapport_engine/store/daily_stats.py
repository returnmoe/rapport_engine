from conf import AgentConfiguration
from redis import StrictRedis
import app
import datetime

KEY_STATS_DAILY = app.NAME_SLUG + ":{agent_name}:stats:daily"


class DailyStats:
    def __init__(
        self, date_id: str, completion_tokens: int = 0, prompt_tokens: int = 0
    ):
        self.__date_id = date_id
        self.__completion_tokens = completion_tokens
        self.__prompt_tokens = prompt_tokens

    def to_dict(self) -> dict:
        return {
            "completion_tokens": self.completion_tokens,
            "prompt_tokens": self.prompt_tokens,
            "total_tokens": self.total_tokens,
        }

    @property
    def date_id(self) -> str:
        return self.__date_id

    @property
    def completion_tokens(self) -> int:
        return self.__completion_tokens

    @property
    def prompt_tokens(self) -> int:
        return self.__prompt_tokens

    @property
    def total_tokens(self) -> int:
        return self.completion_tokens + self.prompt_tokens

    def add_tokens(self, completion_tokens: int = 0, prompt_tokens: int = 0):
        self.__completion_tokens += completion_tokens
        self.__prompt_tokens += prompt_tokens


class DailyStatsStore:
    @staticmethod
    def get_current_date_id() -> str:
        return datetime.datetime.now().strftime("%Y%m%d")

    def __init__(self, agent_name: str, redis_client: StrictRedis):
        self.__key = KEY_STATS_DAILY.format(agent_name=agent_name)
        self.__redis_client = redis_client

    def get(self, date_id: str) -> DailyStats:
        key = self.__key + ":" + date_id
        r = self.__redis_client

        completion_tokens = r.hget(key, "completion_tokens")
        prompt_tokens = r.hget(key, "prompt_tokens")

        if not (
            isinstance(completion_tokens, bytes)
            and isinstance(prompt_tokens, bytes)
        ):
            return DailyStats(date_id)

        return DailyStats(date_id, int(completion_tokens), int(prompt_tokens))

    def set(self, stats: DailyStats) -> None:
        key = self.__key + ":" + stats.date_id
        r = self.__redis_client

        r.hset(key, "completion_tokens", stats.completion_tokens)
        r.hset(key, "prompt_tokens", stats.prompt_tokens)

        if r.ttl(key) == -1:
            combine = datetime.datetime.combine
            now = datetime.datetime.now()

            future_date = now + datetime.timedelta(days=16)
            next_midnight = combine(future_date.date(), datetime.time.min)
            next_midnight += datetime.timedelta(days=1)
            expire = int(next_midnight.timestamp())

            r.expireat(key, expire)
