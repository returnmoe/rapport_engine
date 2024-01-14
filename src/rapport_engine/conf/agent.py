from . import schema
from .exc import InvalidConfigurationError
from dateutil import parser
from jsonschema import validate, exceptions
import collections.abc


class AgentConfiguration:
    @staticmethod
    def timestr_to_seconds(timestr: str):
        parsed_time = parser.parse(timestr, fuzzy=True)

        # Convert to seconds
        total_seconds = (
            parsed_time.hour * 3600
            + parsed_time.minute * 60
            + parsed_time.second
        )

        return total_seconds

    __defaults = {
        "spec": {
            "activation": [{"type": "reply"}],
            "history": [
                {"source": "*", "maxStorageSize": 256, "maxContext": 8}
            ],
            "messages": {
                "limits": {
                    "daily": {"tokens": 10240},
                    "input": {"tokens": 1024, "action": "truncate"},
                    "output": {"tokens": 1024, "action": "truncate"},
                    "user": {"interactions": 30, "window": "15m"},
                },
                "errors": {
                    "generic": "Sorry, I am not available right now.",
                    "dailyLimitExceeded": "Sorry, my daily token limit has been exceeded.",
                    "rateLimitExceeded": "Your request has been rate limited. Try again later.",
                },
            },
            "model": "gpt-3.5-turbo",
            "prompts": [],
        }
    }

    def __recursive_update(self, d: dict, u: dict) -> dict:
        """
        Recursively update dictionary d with values from dictionary u.
        """
        for k, v in u.items():
            if isinstance(v, collections.abc.Mapping):
                d[k] = self.__recursive_update(d.get(k, {}), v)
            else:
                d[k] = v
        return d

    def __init__(self, data: dict):
        self.data = self.__recursive_update(self.__defaults, data)
        self.__validate()

    def __validate(self):
        try:
            data = self.data
            validate(instance=data, schema=schema.agent)

            # Additional validation: window must be a valid time string
            self.timestr_to_seconds(
                data["spec"]["messages"]["limits"]["rate"]["user"]["window"]
            )

            # Additional validation: sum of input.tokens and
            # output.tokens
            total_tokens = (
                data["spec"]["messages"]["limits"]["input"]["tokens"]
                + data["spec"]["messages"]["limits"]["output"]["tokens"]
            )
            if total_tokens > 8192:
                raise InvalidConfigurationError(
                    "The sum of 'spec.messages.limits.input.tokens' and "
                    "'spec.messages.limits.output.tokens' exceeds 8192"
                )

        except exceptions.ValidationError as e:
            raise InvalidConfigurationError(
                f"Invalid configuration: {e.message}"
            )
