import app
import json
from telegram import Message
from redis import StrictRedis
from conf import AgentConfiguration


KEY_MESSAGE_STORE = app.NAME_SLUG + ":{agent_name}:updates:{chat_id}"


class MessageStore:
    def __init__(
        self,
        agent_configuration: AgentConfiguration,
        redis_client: StrictRedis,
    ):
        self._agent_configuration = agent_configuration
        self._redis_client = redis_client

    def get_store_rule(self, message: Message) -> dict:
        rules = self._agent_configuration.data["spec"]["history"]
        user_id = str(message.from_user.id)
        chat_id = str(message.chat_id)
        value = None

        for item in rules:
            if item["source"] == user_id or item["source"] == chat_id:
                return item
            if item["source"] == "*":
                value = item

        return value

    def get_reply_chain(self, message: Message) -> list[Message]:
        if not isinstance(message.reply_to_message, Message):
            return [message]

        agent_name = self._agent_configuration.data["metadata"]["name"]
        r = self._redis_client

        rule = self.get_store_rule(message)
        limit = rule["maxChainSize"]

        chain = [message]
        chat_id = str(message.chat_id)
        hash_key = KEY_MESSAGE_STORE.format(
            agent_name=agent_name, chat_id=chat_id
        )

        while (
            isinstance(message.reply_to_message, Message)
            and len(chain) < limit
        ):
            reply_id = message.reply_to_message.message_id
            read = r.hget(hash_key, reply_id)
            if not isinstance(read, bytes):
                break
            value = json.loads(read.decode(app.DEFAULT_ENCODING))
            message = Message.de_json(value, None)
            chain.insert(0, message)

        return chain

    def add(self, message: Message) -> None:
        r = self._redis_client
        agent_name = self._agent_configuration.data["metadata"]["name"]
        rule = self.get_store_rule(message)
        max_size = rule["maxStorageSize"]
        chat_id = str(message.chat_id)

        hash_key = KEY_MESSAGE_STORE.format(
            agent_name=agent_name, chat_id=chat_id
        )
        list_key = "{hash_key}:order".format(hash_key=hash_key)
        field = str(message.id)
        value = message.to_json()

        script = """
        redis.call('HSET', KEYS[1], ARGV[1], ARGV[2])
        redis.call('LPUSH', KEYS[2], ARGV[1])
        while redis.call('LLEN', KEYS[2]) > tonumber(ARGV[3]) do
            local oldest_id = redis.call('RPOP', KEYS[2])
            redis.call('HDEL', KEYS[1], oldest_id)
        end
        """

        r.eval(script, 2, hash_key, list_key, field, value, max_size)
