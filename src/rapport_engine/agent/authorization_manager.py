from app import NAME_SLUG, DEFAULT_ENCODING
from redis import StrictRedis


class AuthorizationManager:
    def __init__(self, agent_name: str, redis_client: StrictRedis):
        self._users_key = f"{NAME_SLUG}:{agent_name}:authorized-users"
        self._redis_client = redis_client
        self._fetch_authorized_users()

    @property
    def authorized_users(self) -> set[str]:
        return self._authorized_users

    def _fetch_authorized_users(self) -> None:
        values = self._redis_client.smembers(self._users_key)
        users = [item.decode(DEFAULT_ENCODING) for item in values]
        self._authorized_users = set(users)

    def _is_user_id_valid(self, id: str) -> bool:
        if id.startswith("@"):
            return True
        try:
            int(id)
            return True
        except ValueError:
            return False

    def _prepare_user_id(self, id: int | str) -> str:
        if not self._is_user_id_valid(id):
            raise ValueError(
                "User ID must either be numeric or an username beginning with @"
            )
        return str(id)

    def add_authorized_user(self, id: int | str) -> None:
        id = self._prepare_user_id(id)
        key = self._users_key
        r = self._redis_client

        success = r.sadd(key, id)
        if success:
            self._fetch_authorized_users()

        return success

    def remove_authorized_user(self, id: int | str) -> bool:
        id = self._prepare_user_id(id)
        key = self._users_key
        r = self._redis_client

        success = not bool(r.srem(key, id))
        if success:
            self._fetch_authorized_users()

        return success
