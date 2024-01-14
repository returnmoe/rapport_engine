from .authorization_manager import AuthorizationManager
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
from typing import Callable


class CommandHandler:
    def __init__(
        self,
        authorization_manager: AuthorizationManager,
    ):
        self._authorization_manager = authorization_manager

    def _get_add_handler(self, type: str) -> Callable | None:
        match type:
            case "user":
                return self._add_user
            case _:
                return None

    def _get_list_handler(self, type: str) -> Callable | None:
        match type:
            case "user":
                return self._list_user
            case _:
                return None

    def _get_remove_handler(self, type: str) -> Callable | None:
        match type:
            case "user":
                return self._remove_user
            case _:
                return None

    def _add_user(self, args: list[str] | None) -> str:
        try:
            manager = self._authorization_manager
            manager.add_authorized_user(args[1])
            return "User added successfully"
        except (IndexError, ValueError):
            return "Error: must specify an user to add"

    def _list_user(self, args: list[str] | None) -> str:
        authorized_users = self._authorization_manager.authorized_users
        if len(authorized_users) == 0:
            return "No authorized users."
        return "\n".join(f"• {user}" for user in authorized_users)

    def _remove_user(self, args: list[str] | None) -> str:
        try:
            manager = self._authorization_manager
            manager.remove_authorized_user(args[1])
            return "User removed successfully"
        except (IndexError, ValueError):
            return "Error: must specify an user to remove"

    async def add(self, update: Update, context: CallbackContext) -> None:
        try:
            add_handler = self._get_add_handler(context.args[0])

            if not callable(add_handler):
                await update.message.reply_text("Error: invalid type")
                return

            return await update.message.reply_text(add_handler(context.args))

        except (IndexError, ValueError):
            await update.message.reply_text(
                "Usage: `/add [type] [item]`", parse_mode=ParseMode.MARKDOWN_V2
            )

    async def list(self, update: Update, context: CallbackContext) -> None:
        try:
            list_handler = self._get_list_handler(context.args[0])

            if not callable(list_handler):
                await update.message.reply_text("Error: invalid type")
                return

            return await update.message.reply_text(list_handler(context.args))

        except (IndexError, ValueError):
            await update.message.reply_text(
                "Usage: `/list [type]`",
                parse_mode=ParseMode.MARKDOWN_V2,
            )

    async def remove(self, update: Update, context: CallbackContext) -> None:
        try:
            remove_handler = self._get_remove_handler(context.args[0])

            if not callable(remove_handler):
                await update.message.reply_text("Error: invalid type")
                return

            return await update.message.reply_text(
                remove_handler(context.args)
            )

        except (IndexError, ValueError):
            await update.message.reply_text(
                "Usage: `/add [type] [item]`", parse_mode=ParseMode.MARKDOWN_V2
            )
