import datetime
import os
import re
import tzlocal


class MessagePreprocessor:
    def __init__(self, base_variables: dict = {}):
        self._base_variables = base_variables

    @property
    def base_variables(self):
        return self._base_variables

    def get_variable(self, name: str, additional: dict = {}):
        base_variables = self.base_variables

        if name in additional:
            return additional[name]

        # Dynamic variables

        if name == "RAPPORT_DATE":
            return datetime.datetime.now().date().strftime("%Y-%m-%d")

        if name == "RAPPORT_TIME":
            return datetime.datetime.now().date().strftime("%I:%M %p")

        if name == "RAPPORT_TIMEZONE":
            return str(tzlocal.get_localzone())

        # Base variables

        if name in base_variables:
            return base_variables[name]

        # Environment variables

        if name.startswith("RAPPORT_ENV_"):
            return os.environ.get(name, None)

        return None

    def format(self, message: str, additional: dict = {}) -> str:
        pattern = re.compile(r"\$\{(\w+)\}")

        def replacer(match):
            name = match.group(1)
            value = self.get_variable(name, additional)
            if value == None:
                return ""
            return value

        return pattern.sub(replacer, message)
