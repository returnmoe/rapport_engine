from .authorization_manager import AuthorizationManager
from .message_preprocessor import MessagePreprocessor
from conf.agent import AgentConfiguration
from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from store.daily_stats import DailyStats, DailyStatsStore
from store.daily_stats import DailyStatsStore
from store.message import MessageStore
from store.user_stats import TimeWindow
from store.user_stats import UserStats, UserStatsStore
from telegram import Chat, Message, Update, User
from telegram.ext import CallbackContext
from tenacity import retry, wait_exponential, stop_after_attempt
from typing import List
import logger
import re


class MessageHandler:
    def __init__(
        self,
        tg_bot_id: int,
        agent_configuration: AgentConfiguration,
        openai_client: OpenAI,
        message_preprocessor: MessagePreprocessor,
        authorization_manager: AuthorizationManager,
        daily_stats_store: DailyStatsStore,
        user_stats_store: UserStatsStore,
        message_store: MessageStore,
    ):
        self._tg_bot_id = tg_bot_id
        self._agent_configuration = agent_configuration
        self._openai_client = openai_client
        self._message_preprocessor = message_preprocessor
        self._authorization_manager = authorization_manager
        self._daily_stats_store = daily_stats_store
        self._user_stats_store = user_stats_store
        self._message_store = message_store

    def _log_not_activated(self, user: User, chat: Chat) -> None:
        chat_username, user_username = "", ""

        if isinstance(chat.username, str):
            chat_username = f"@{chat.username}"

        if isinstance(user.username, str):
            user_username = f"@{user.username}"

        logger.get().debug(
            "Discarded message because it does not match activation rules",
            chat_id=chat.id,
            chat_username=chat_username,
            user_id=user.id,
            user_username=user_username,
        )

    def _log_unauthorized(self, user: User, chat: Chat) -> None:
        chat_username, user_username = "", ""

        if isinstance(chat.username, str):
            chat_username = f"@{chat.username}"

        if isinstance(user.username, str):
            user_username = f"@{user.username}"

        logger.get().info(
            "Discarded message from unauthorized user",
            chat_id=chat.id,
            chat_username=chat_username,
            user_id=user.id,
            user_username=user_username,
        )

    def _is_authorized(self, user: User, chat: Chat) -> bool:
        id_list = [str(user.id), str(chat.id)]
        authorized_users = self._authorization_manager.authorized_users

        for entity in (user, chat):
            if isinstance(entity.username, str):
                id_list.append(f"@{entity.username}")

        return any(id in authorized_users for id in id_list)

    def _is_reply_to_bot(self, message: Message) -> bool:
        return (
            message.reply_to_message is not None
            and message.reply_to_message.from_user.id == self._tg_bot_id
        )

    def _has_activation_keyword(self, message: Message, keyword: str) -> bool:
        additional = self._get_additional(message)
        preprocessor = self._message_preprocessor
        effective_keyword = preprocessor.format(keyword, additional)
        return effective_keyword in message.text

    def _should_activate(self, message: Message) -> bool:
        conf = self._agent_configuration.data
        activation_rules = conf["spec"]["activation"]

        for rule in activation_rules:
            if rule["type"] == "reply" and self._is_reply_to_bot(message):
                return True
            if rule["type"] == "keyword" and self._has_activation_keyword(
                message, rule["value"]
            ):
                return True

        return False

    def _get_user_stats(self, user: User) -> UserStats:
        stats_store = self._user_stats_store
        return stats_store.get(user)

    def _get_daily_stats(self) -> DailyStats:
        stats_store = self._daily_stats_store
        return stats_store.get(stats_store.get_current_date_id())

    def _update_user_stats(
        self, user: User, user_stats: UserStats, interactions: int = 1
    ) -> None:
        conf = self._agent_configuration.data
        stats_store = self._user_stats_store

        window_interval = AgentConfiguration.timestr_to_seconds(
            conf["spec"]["messages"]["limits"]["rate"]["user"]["window"]
        )
        window_id = TimeWindow.get_current_window_id(window_interval)

        if user_stats.time_window.id != window_id:
            user_stats.time_window = TimeWindow(window_id, interactions)
        else:
            user_stats.time_window.interactions += interactions

        user_stats.total_interactions += interactions
        stats_store.set(user, user_stats)

    def _update_daily_stats(
        self, daily_stats: DailyStats, completion: ChatCompletion
    ) -> None:
        stats_store = self._daily_stats_store
        completion_tokens = completion.usage.completion_tokens
        prompt_tokens = completion.usage.prompt_tokens
        daily_stats.add_tokens(completion_tokens, prompt_tokens)
        stats_store.set(daily_stats)

    def _has_exceeded_user_limit(self, user_stats: UserStats) -> bool:
        spec = self._agent_configuration.data["spec"]
        limit = spec["messages"]["limits"]["rate"]["user"]["interactions"]
        interval_str = spec["messages"]["limits"]["rate"]["user"]["window"]

        if limit < 0:
            return False

        interval = AgentConfiguration.timestr_to_seconds(interval_str)
        window_id = TimeWindow.get_current_window_id(interval)

        return (
            window_id == user_stats.time_window.id
            and user_stats.time_window.interactions >= limit
        )

    def _has_exceeded_daily_limit(self, daily_stats: DailyStats) -> bool:
        spec = self._agent_configuration.data["spec"]
        limit = spec["messages"]["limits"]["daily"]["tokens"]
        return limit > -1 and daily_stats.total_tokens >= limit

    async def _send_user_limit_error(self, update: Update) -> None:
        spec = self._agent_configuration.data["spec"]
        message = spec["messages"]["errors"]["rateLimitExceeded"]
        await update.effective_message.reply_text(
            message,
            reply_to_message_id=update.effective_message.id,
            allow_sending_without_reply=True,
        )

    async def _send_daily_limit_error(self, update: Update) -> None:
        spec = self._agent_configuration.data["spec"]
        message = spec["messages"]["errors"]["rateLimitExceeded"]
        await update.effective_message.reply_text(
            message,
            reply_to_message_id=update.effective_message.id,
            allow_sending_without_reply=True,
        )

    def _get_additional(self, message: Message) -> dict:
        chat_history = []
        user_input = ""

        reply_chain = self._message_store.get_reply_chain(message)

        for i, entry in enumerate(reply_chain):
            user = entry.from_user
            username = str(user.id)

            if isinstance(user.username, str):
                username = f"@{user.username}"

            entry_text = re.sub(r"\r\n|\r|\n", " ", entry.text)
            message_text = f"{user.full_name} <{username}>: {entry_text}"

            if i == len(reply_chain) - 1:
                user_input = message_text
                break

            chat_history.append(message_text)

        return {
            "RAPPORT_CHAT_HISTORY": "\n".join(chat_history),
            "RAPPORT_USER_INPUT": user_input,
        }

    @retry(
        wait=wait_exponential(multiplier=1, min=6, max=16),
        stop=stop_after_attempt(8),
        reraise=True,
    )
    def _create_chat_completion(
        self,
        messages: List[ChatCompletionMessageParam],
        user_id: str | None = None,
    ) -> ChatCompletion:
        client = self._openai_client
        spec = self._agent_configuration.data["spec"]
        model = spec["model"]
        max_tokens = spec["messages"]["limits"]["output"]["tokens"]
        return client.chat.completions.create(
            model=model, messages=messages, max_tokens=max_tokens, user=user_id
        )

    async def _send_message_response(
        self, update: Update
    ) -> tuple[ChatCompletion, Message]:
        prompts = self._agent_configuration.data["spec"]["prompts"]
        preprocessor = self._message_preprocessor
        message = update.effective_message
        user_id = str(update.effective_user.id)

        additional = self._get_additional(message)
        messages = [
            {
                "role": entry["role"],
                "content": preprocessor.format(entry["content"], additional),
            }
            for entry in prompts
        ]

        completion = self._create_chat_completion(messages, user_id)
        response = completion.choices[0].message.content

        sent_message = await update.effective_message.reply_text(
            response,
            reply_to_message_id=update.effective_message.id,
            allow_sending_without_reply=True,
        )

        return completion, sent_message

    async def message(self, update: Update, context: CallbackContext) -> None:
        message_store = self._message_store
        chat = update.effective_chat
        message = update.effective_message
        user = update.effective_message.from_user

        message_store.add(message)

        if not self._should_activate(message):
            self._log_not_activated(user, chat)
            return

        if not self._is_authorized(user, chat):
            self._log_unauthorized(user, chat)
            return

        user_stats = self._get_user_stats(user)
        if self._has_exceeded_user_limit(user_stats):
            await self._send_user_limit_error(update)
            return

        daily_stats = self._get_daily_stats()
        if self._has_exceeded_daily_limit(daily_stats):
            await self._send_daily_limit_error(update)
            return

        completion, sent_message = await self._send_message_response(update)
        message_store.add(sent_message)

        self._update_user_stats(user, user_stats, 1)
        self._update_daily_stats(daily_stats, completion)
