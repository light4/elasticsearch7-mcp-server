import logging
import sys

from dotenv import load_dotenv

from .server import ElasticsearchMCPServer, ElasticsearchMCPServerConfig


def main():
    """Entry point for the Elasticsearch 7.x MCP server."""
    try:
        load_dotenv()
        config = ElasticsearchMCPServerConfig()
        server = ElasticsearchMCPServer(config=config)
        server.start()
    except Exception as e:
        logging.error(f"Error starting server: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
