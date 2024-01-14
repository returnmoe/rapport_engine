# import os
# import re
# import tzlocal
# import datetime


# class Processor:
#     def __init__(self, variables: dict = {}):
#         self.__variables = variables

#     def set_variable(self, name: str, value: str | None):
#         if not isinstance(value, str):
#             return
#         self.__variables[name] = value

#     def get_variable(
#         self, name: str, additional_data: dict = {}
#     ) -> str | None:
#         variables = self.__variables

#         if name in additional_data:
#             return additional_data[name]

#         # Dynamic variables

#         if name == "RAPPORT_DATE":
#             return datetime.datetime.now().date().strftime("%Y-%m-%d")

#         if name == "RAPPORT_TIME":
#             return datetime.datetime.now().date().strftime("%I:%M %p")

#         if name == "RAPPORT_TIMEZONE":
#             return str(tzlocal.get_localzone())

#         if name in variables:
#             return variables[name]

#         # Allow environment variables starting with "RAPPORT_ENV_"

#         if name.startswith("RAPPORT_ENV_"):
#             os.environ.get(name, None)

#         return None

#     def format(self, value: str, additional_data: dict = {}) -> str:
#         pattern = re.compile(r"\$\{(\w+)\}")

#         def replacer(match):
#             name = match.group(1)
#             value = self.get_variable(name, additional_data)
#             if value == None:
#                 return ""
#             return value

#         return pattern.sub(replacer, value)
