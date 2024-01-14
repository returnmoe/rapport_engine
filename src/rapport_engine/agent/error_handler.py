from conf import AgentConfiguration
from telegram import Update
from telegram.ext import CallbackContext
import logger
import traceback


class ErrorHandler:
    def __init__(self, agent_configuration: AgentConfiguration):
        self._agent_configuration = agent_configuration

    async def error(self, update: Update, context: CallbackContext) -> None:
        log = logger.get()
        spec = self._agent_configuration.data["spec"]
        error_message = spec["messages"]["errors"]["generic"]

        error = context.error
        tb_str = "".join(
            traceback.TracebackException.from_exception(error).format()
        )

        log.error(
            "Unable to respond to update {id} due to error: {message}".format(
                id=str(update.update_id), message=str(context.error)
            ),
            update_id=update.update_id,
            user_id=update.effective_user.id,
            error=str(context.error.__class__.__name__),
            traceback=tb_str,
        )

        await update.message.reply_text(error_message)
