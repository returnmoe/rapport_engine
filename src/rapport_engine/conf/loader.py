from .agent import AgentConfiguration
import yaml


def load(path: str) -> AgentConfiguration:
    with open(path, "r") as f:
        contents = yaml.safe_load(f)
    return AgentConfiguration(contents)
