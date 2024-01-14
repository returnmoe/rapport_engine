from conf import AgentConfiguration
from redis import StrictRedis
from telegram import User
import app
import json
import time

KEY_STATS_USER = app.NAME_SLUG + ":{agent_name}:stats:user"


class TimeWindow:
    @staticmethod
    def create_id(timestamp: int, interval: int) -> str:
        return str(timestamp - (timestamp % interval))

    def __init__(self, window_id: str, interactions: int = 0):
        self.__id = window_id
        self.__interactions = interactions

    @property
    def id(self) -> str:
        return self.__id

    @property
    def interactions(self) -> int:
        return self.__interactions

    @interactions.setter
    def interactions(self, value: int) -> None:
        self.__interactions = value


class UserStats:
    def __init__(
        self,
        time_window: TimeWindow,
        first_seen: int,
        last_updated: int,
        total_interactions: int = 0,
    ):
        self.__time_window = time_window
        self.__first_seen = first_seen
        self.__last_updated = last_updated
        self.__total_interactions = total_interactions

    def to_dict(self) -> dict:
        retval = {
            "first_seen": self.first_seen,
            "last_updated": self.last_updated,
            "total_interactions": self.total_interactions,
            "time_window": {
                "id": self.time_window.id,
                "interactions": self.time_window.interactions,
            },
        }
        return retval

    @property
    def first_seen(self) -> int:
        return self.__first_seen

    @property
    def last_updated(self) -> int:
        return self.__last_updated

    @property
    def total_interactions(self) -> int:
        return self.__total_interactions

    @property
    def time_window(self) -> TimeWindow:
        return self.__time_window

    @total_interactions.setter
    def total_interactions(self, value: int) -> None:
        self.__last_updated = int(time.time())
        self.__total_interactions = value

    @time_window.setter
    def time_window(self, value: TimeWindow) -> None:
        self.__last_updated = int(time.time())
        self.__time_window = value


class UserStatsStore:
    def __init__(
        self, configuration: AgentConfiguration, redis_client: StrictRedis
    ):
        agent_name = configuration.data["metadata"]["name"]
        limits = configuration.data["spec"]["messages"]["limits"]
        window_seconds = AgentConfiguration.timestr_to_seconds(
            limits["rate"]["user"]["window"]
        )

        self.__key = KEY_STATS_USER.format(agent_name=agent_name)
        self.__redis_client = redis_client
        self.__window_seconds = window_seconds

    def get(self, user: User) -> UserStats:
        interval = self.__window_seconds
        key = self.__key
        r = self.__redis_client

        user_id = user.id
        read = r.hget(key, user_id)

        if not isinstance(read, bytes):
            current_time = int(time.time())
            window_id = TimeWindow.create_id(current_time, interval)
            time_window = TimeWindow(window_id, 0)
            return UserStats(time_window, current_time, current_time, 0)

        value = json.loads(read.decode(app.DEFAULT_ENCODING))

        time_window = TimeWindow(
            value["time_window"]["id"], value["time_window"]["interactions"]
        )

        return UserStats(
            time_window,
            value["first_seen"],
            value["last_updated"],
            value["total_interactions"],
        )

    def set(self, user: User, stats: UserStats) -> None:
        key = self.__key
        r = self.__redis_client
        value = json.dumps(stats.to_dict())
        r.hset(key, user.id, value)
