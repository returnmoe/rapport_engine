from .authorization_manager import AuthorizationManager
from .command_handler import CommandHandler
from .error_handler import ErrorHandler
from .message_handler import MessageHandler
from .message_preprocessor import MessagePreprocessor
from conf.agent import AgentConfiguration
from openai import OpenAI
from store.daily_stats import DailyStatsStore
from store.message import MessageStore
from store.user_stats import UserStatsStore
from telegram import User
from telegram.ext import (
    Application,
    MessageHandler as TgMessageHandler,
    CommandHandler as TgCommandHandler,
    filters as f,
)
import asyncio
import os
import redis


class Agent:
    def __init__(self, agent_configuration: AgentConfiguration, token: str):
        loop = asyncio.get_event_loop()
        application = Application.builder().token(token).build()
        user: User = loop.run_until_complete(application.updater.bot.get_me())
        agent_name = agent_configuration.data["metadata"]["name"]

        host = os.environ.get("REDIS_HOST", "localhost")
        port = os.environ.get("REDIS_PORT", "6379")
        username = os.environ.get("REDIS_USERNAME", "")
        password = os.environ.get("REDIS_PASSWORD", "")
        db = os.environ.get("REDIS_DB", "0")
        redis_client = redis.StrictRedis(
            host=host,
            port=int(port),
            username=username,
            password=password,
            db=int(db),
        )

        openai_client = OpenAI()
        message_preprocessor = MessagePreprocessor(
            {
                "RAPPORT_FIRST_NAME": user.first_name,
                "RAPPORT_LAST_NAME": user.last_name,
                "RAPPORT_USERNAME": user.username,
            }
        )
        authorization_manager = AuthorizationManager(agent_name, redis_client)
        daily_stats_store = DailyStatsStore(agent_name, redis_client)
        user_stats_store = UserStatsStore(agent_configuration, redis_client)
        message_store = MessageStore(agent_configuration, redis_client)

        self._application = application
        self._agent_configuration = agent_configuration
        self._error_handler = ErrorHandler(agent_configuration)
        self._command_handler = CommandHandler(authorization_manager)
        self._message_handler = MessageHandler(
            user.id,
            agent_configuration,
            openai_client,
            message_preprocessor,
            authorization_manager,
            daily_stats_store,
            user_stats_store,
            message_store,
        )

    def run_polling(self):
        application = self._application
        agent_configuration = self._agent_configuration
        error_handler = self._error_handler
        command_handler = self._command_handler
        message_handler = self._message_handler

        command_filters = f.UpdateType.MESSAGE & ~f.FORWARDED
        message_filters = (
            f.UpdateType.MESSAGE & f.TEXT & ~f.FORWARDED & ~f.COMMAND
        )

        for admin_id in agent_configuration.data["spec"]["admin"]:
            command_filters = command_filters & f.User(user_id=int(admin_id))

        tg_command_handlers = [
            TgCommandHandler("add", command_handler.add, command_filters),
            TgCommandHandler("list", command_handler.list, command_filters),
            TgCommandHandler(
                "remove", command_handler.remove, command_filters
            ),
        ]

        tg_message_handlers = [
            TgMessageHandler(message_filters, message_handler.message)
        ]

        application.add_error_handler(error_handler.error)
        application.add_handlers(tg_command_handlers)
        application.add_handlers(tg_message_handlers)
        application.run_polling()
