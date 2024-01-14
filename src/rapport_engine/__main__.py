from agent.agent import Agent
from conf.loader import load
from dotenv import load_dotenv
import argparse
import logger
import os


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Specify a configuration file."
    )

    parser.add_argument(
        "-c",
        "--config",
        default="/etc/rapport_engine/agent.conf.yaml",
        help="Path to the configuration file",
    )

    args = parser.parse_args()

    logger.configure()
    log = logger.get()

    agent_configuration = load(args.config)
    token = os.environ.get("TELEGRAM_TOKEN")
    agent = Agent(agent_configuration, token)
    agent_name = agent_configuration.data["metadata"]["name"]

    log.info("Created agent", agent_name=agent_name)

    agent.run_polling()


if __name__ == "__main__":
    main()
