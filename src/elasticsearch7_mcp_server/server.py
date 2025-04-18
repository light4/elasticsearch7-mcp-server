import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

from fastmcp import FastMCP

from .es_client import ElasticsearchClient


@dataclass
class ElasticsearchMCPServerConfig:
    transport: Literal["stdio", "sse"] = "sse"
    sse_addr: str = os.getenv("SSE_ADDR", "localhost:8000")
    es_url: str = os.getenv("ES_URL", "http://localhost:9200")
    es_username: Optional[str] = os.getenv("ES_USERNAME")
    es_password: Optional[str] = os.getenv("ES_PASSWORD")

    def __post_init__(self):
        self.sse_host = self.sse_addr.split(":")[0]
        self.sse_port = (
            int(self.sse_addr.split(":")[1]) if ":" in self.sse_addr else 8000
        )


class ElasticsearchMCPServer:
    def __init__(self, config: ElasticsearchMCPServerConfig):
        self.config = config
        self.logger = self._setup_logger()
        self.es_client = ElasticsearchClient(self.logger).es_client
        self.server = FastMCP(
            name="ElasticsearchMCPServer", host=config.sse_host, port=config.sse_port
        )
        self._setup_handlers()

    def _setup_logger(self) -> logging.Logger:
        """Set up and configure logger."""
        logger = logging.getLogger("elasticsearch7-mcp-server")
        logger.setLevel(logging.INFO)

        # Add console handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _setup_handlers(self):
        """Set up MCP handlers for ES operations."""
        # Add your Elasticsearch 7.x specific handlers here
        self.server.tool(name="es-ping", description="Ping Elasticsearch server")(
            self._handle_ping
        )
        self.server.tool(name="es-info", description="Get Elasticsearch info")(
            self._handle_info
        )
        self.server.tool(
            name="es-search", description="Search documents in Elasticsearch index"
        )(self._handle_search)

        # Add more handlers as needed for your specific use case

    def _handle_ping(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping request to Elasticsearch."""
        try:
            result = self.es_client.ping()
            return {"success": result}
        except Exception as e:
            self.logger.error(f"Error pinging Elasticsearch: {str(e)}")
            return {"success": False, "error": str(e)}

    def _handle_info(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """Get Elasticsearch cluster info."""
        try:
            info = self.es_client.info()
            return {"success": True, "info": info}
        except Exception as e:
            self.logger.error(f"Error getting Elasticsearch info: {str(e)}")
            return {"success": False, "error": str(e)}

    def _handle_search(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """Search documents in Elasticsearch index.

        Expected request format:
        {
            "index": "index_name",
            "query": {
                "match": {"field": "value"}
            },
            "size": 10,  # optional
            "from": 0,   # optional
            "aggs": {    # optional
                "my_agg": {
                    "terms": {"field": "category"}
                }
            },
            # 支持所有其他 Elasticsearch 搜索参数
            "sort": [...],
            "highlight": {...},
            "_source": [...],
            ...
        }
        """
        try:
            # 验证请求参数
            if not req.get("index"):
                return {"success": False, "error": "Missing required parameter: index"}

            # 提取索引名称
            index = req["index"]

            # 构建搜索参数 - 保留所有可能的 Elasticsearch 搜索参数
            # 除了"index"之外的所有参数都传递给 Elasticsearch
            search_params = {k: v for k, v in req.items() if k != "index"}

            # 记录搜索请求
            self.logger.info(f"Searching index '{index}' with params: {search_params}")

            # 执行搜索
            results = self.es_client.search(index=index, body=search_params)
            return {"success": True, "results": results}
        except Exception as e:
            self.logger.error(f"Error searching Elasticsearch: {str(e)}")
            return {"success": False, "error": str(e)}

    def start(self):
        """Start the MCP server."""
        self.logger.info("Starting Elasticsearch MCP server...")
        if self.config.transport == "stdio":
            self.logger.info("MCP server mode: %s", self.config.transport)
        else:
            self.logger.info("MCP server SSE address: %s", self.config.sse_addr)
        self.server.run(transport=self.config.transport)
