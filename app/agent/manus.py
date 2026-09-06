import os
from typing import Dict, List, Optional

from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.config import config
from app.logger import logger
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import Message
from app.tool import Terminate, ToolCollection
from app.tool.ask_human import AskHuman
from app.tool.ask_tag import AskTag
from app.tool.mcp import MCPClients, MCPClientTool
from app.tool.python_execute import PythonExecute
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.zhipu_helper_tool import ZhipuHelper
from app.tool.siliconflow_helper_tool import SiliconflowHelper
from app.tool.bridge_health_tool import BridgeHealth
from app.tool.batch_run_tool import BatchRun
from app.tool.usage_tool import UsageMonitor
from app.tool.voice_correct_tool import VoiceCorrect
from app.tool.ask_enhancer_tool import AskEnhancer
from app.tool.notify_feishu_tool import NotifyFeishu
from app.tool.web_search import WebSearch
from app.tool.comment_search_tool import CommentSearch
from app.tool.status_monitor_tool import StatusMonitor
from app.tool.optimize_plans_tool import OptimizePlansTool
from app.tool.memory_tool import MemoryTool
from app.tool.auto_memory import AutoMemoryExtractor


_BROWSER_USE_SERVER_ID = "browser_use"
_BROWSER_USE_COMMAND = "uvx"
_BROWSER_USE_ARGS = ["browser-use", "--cli-mcp"]
_BROWSER_USE_ENV_VARS = (
    "BROWSER_USE_API_KEY",
    "BROWSER_USE_CLOUD_API_URL",
    "BU_BROWSER_ID",
    "BU_CDP_URL",
    "BU_CDP_WS",
    "BU_NAME",
)
_BROWSER_USE_TRANSPORT_INSTRUCTIONS = """\
Browser Use CLI 3.0 is exposed here as MCP tools. When the Browser Use skill
shows `browser-use <<'PY'`, pass the Python body to `browser_exec` instead.
Use `browser_screenshot` when visual inspection is needed. Both tools use the
same persistent browser-harness session as CLI 3.0.
"""


def _browser_use_env() -> Dict[str, str]:
    return {name: value for name in _BROWSER_USE_ENV_VARS if (value := os.getenv(name))}


class Manus(ToolCallAgent):
    """A versatile general-purpose agent with support for both local and MCP tools."""

    name: str = "Manus"
    description: str = "A versatile agent that can solve various tasks using multiple tools including MCP-based tools"

    system_prompt: str = SYSTEM_PROMPT.format(directory=config.workspace_root)
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 10000
    max_steps: int = 50

    # MCP clients for remote tool access
    mcp_clients: MCPClients = Field(default_factory=MCPClients)

    # Add general-purpose tools to the tool collection
    # 按六大分类组织（参照 Hierarchical Tool Organization 最佳实践）
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            # === 1. 核心执行类 Core Execution ===
            PythonExecute(),       # 执行Python代码（计算/数据处理/自动化）
            StrReplaceEditor(),    # 文件读写编辑（替换/插入/删除）
            AskHuman(),            # 询问用户获取输入
            Terminate(),           # 结束任务
            # === 2. 深度思考类 Deep Thinking ===
            AskTag(),              # 3标签网页版（豆包/千问国际版/智谱清言）深度思考/交叉验证
            ZhipuHelper(),         # 智谱GLM API：free=glm-4-flash免费 / air=glm-4.5-air收费中层主力
            SiliconflowHelper(),   # 硅基GLM-4-9B免费底层（纯JSON/搬运/去重/简单分类）
            AskEnhancer(),         # 提问增强：模糊提问→结构化四要素，调用3标签前使用
            OptimizePlansTool(),   # 方案三标签深度优化：拆分方案→发给三个标签→汇总改进建议
            # === 3. 浏览搜索类 Browser & Search ===
            CommentSearch(),       # 评论区搜索：GitHub Issues/Stack Overflow/掘金/CSDN，代码问题P0优先
            WebSearch(),           # 联网搜索：百度/必应/DuckDuckGo/谷歌，通用信息P1
            # Browser Use 走 MCP 动态注册
            # === 4. 跑批自愈类 Batch & Self-healing ===
            BatchRun(),            # 金庸连载章节跑批：四API+3标签协同，内置自愈+断点续跑
            BridgeHealth(),        # 3标签桥接自愈：诊断8010端口+3标签连通性，异常自动重启恢复
            VoiceCorrect(),        # 语音纠错：L1固定词对+L2拼音模糊匹配，纯本地不耗API
            # === 5. 监控通知类 Monitoring & Notification ===
            StatusMonitor(),       # 实时状态监控：更新/查询当前任务状态，关键节点自动记录
            UsageMonitor(),        # API用量监控：各通道今日调用次数/剩余额度
            NotifyFeishu(),        # 飞书推送：跑批完成/出错自动推送到用户手机
            # === 6. 记忆与系统类 Memory & System ===
            MemoryTool(),          # 长期记忆：facts事实/episodes经历/skills技能，remember/recall/forget/list
            # === 7. 系统控制类 System Control ===
            # MCP 工具动态注册（Browser Use CLI 3.0 等）
        )
    )

    special_tool_names: list[str] = Field(default_factory=lambda: [Terminate().name])

    # Track connected MCP servers
    connected_servers: Dict[str, str] = Field(
        default_factory=dict
    )  # server_id -> url/command
    mcp_instruction_servers: set[str] = Field(default_factory=set, exclude=True)
    # 自动记忆提取器（任务完成后自动提取关键信息存入长期记忆）
    # 用下划线前缀表示私有属性，不参与pydantic验证（AutoMemoryExtractor不是pydantic模型）
    _auto_memory = None
    _initialized: bool = False

    @classmethod
    async def create(cls, **kwargs) -> "Manus":
        """Factory method to create and properly initialize a Manus instance."""
        instance = cls(**kwargs)
        await instance.initialize_mcp_servers()
        # 初始化自动记忆提取器（参考Mem0设计：任务结束后自动提取记忆）
        try:
            from app.tool.memory_tool import MemoryTool
            instance._auto_memory = AutoMemoryExtractor(
                llm=instance.llm,
                memory_tool=MemoryTool()
            )
            logger.info("AutoMemoryExtractor 初始化成功（任务完成后自动提取记忆）")
        except Exception as e:
            logger.warning(f"AutoMemoryExtractor 初始化失败（不影响主流程）: {e}")
            instance._auto_memory = None
        instance._initialized = True
        return instance

    async def run(self, request: Optional[str] = None) -> str:
        """重写 run() 方法：任务完成后自动提取记忆（策展式写入）。
        
        参考网友成熟方案：
        - 正信号触发存储：任务成功后才提取正向经验
        - 失败任务单独沉淀：标记为反例陷阱
        - 非对称淘汰：坏经验淘汰速度是好经验的2.4倍
        """
        # 调用父类 run() 执行主流程
        result = await super().run(request)
        
        # 任务完成后自动提取记忆（如果 auto_memory 已初始化）
        if self._auto_memory is not None:
            try:
                logger.info("🧠 任务完成，开始自动记忆提取...")
                extract_result = await self._auto_memory.extract_and_store(self.memory.messages)
                if extract_result.get("stored", 0) > 0:
                    logger.info(
                        f"✅ 自动记忆提取完成：存储 {extract_result['stored']} 条，"
                        f"跳过 {extract_result.get('skipped', 0)} 条"
                    )
                    # 记录提取的记忆条目
                    for item in extract_result.get("items", []):
                        logger.info(f"  📝 [{item['store']}] {item['key']}: {item['value'][:80]}")
                else:
                    reason = extract_result.get("reason", "无值得长期记忆的信息")
                    logger.info(f"ℹ️ 自动记忆提取：{reason}")
            except Exception as e:
                logger.warning(f"自动记忆提取失败（不影响主流程）: {e}")
        
        return result

    async def initialize_mcp_servers(self) -> None:
        """Initialize connections to configured MCP servers."""
        if _BROWSER_USE_SERVER_ID not in config.mcp_config.servers and os.getenv(
            "OPENMANUS_DISABLE_BROWSER_USE", ""
        ).lower() not in {"1", "true", "yes"}:
            try:
                await self.connect_mcp_server(
                    _BROWSER_USE_COMMAND,
                    _BROWSER_USE_SERVER_ID,
                    use_stdio=True,
                    stdio_args=_BROWSER_USE_ARGS,
                    tool_name_prefix=False,
                    stdio_env=_browser_use_env(),
                )
                logger.info("Connected to Browser Use CLI 3.0 through MCP")
            except Exception as e:
                logger.error(f"Failed to connect to Browser Use CLI 3.0: {e}")

        for server_id, server_config in config.mcp_config.servers.items():
            try:
                if server_config.type == "sse":
                    if server_config.url:
                        await self.connect_mcp_server(server_config.url, server_id)
                        logger.info(
                            f"Connected to MCP server {server_id} at {server_config.url}"
                        )
                elif server_config.type == "stdio":
                    if server_config.command:
                        await self.connect_mcp_server(
                            server_config.command,
                            server_id,
                            use_stdio=True,
                            stdio_args=server_config.args,
                            tool_name_prefix=server_id != _BROWSER_USE_SERVER_ID,
                            stdio_env=(
                                _browser_use_env()
                                if server_id == _BROWSER_USE_SERVER_ID
                                else None
                            ),
                        )
                        logger.info(
                            f"Connected to MCP server {server_id} using command {server_config.command}"
                        )
            except Exception as e:
                logger.error(f"Failed to connect to MCP server {server_id}: {e}")

    async def connect_mcp_server(
        self,
        server_url: str,
        server_id: str = "",
        use_stdio: bool = False,
        stdio_args: Optional[List[str]] = None,
        tool_name_prefix: bool = True,
        stdio_env: Optional[Dict[str, str]] = None,
    ) -> None:
        """Connect to an MCP server and add its tools."""
        if use_stdio:
            await self.mcp_clients.connect_stdio(
                server_url,
                stdio_args or [],
                server_id,
                tool_name_prefix=tool_name_prefix,
                env=stdio_env,
            )
            self.connected_servers[server_id or server_url] = server_url
        else:
            await self.mcp_clients.connect_sse(server_url, server_id)
            self.connected_servers[server_id or server_url] = server_url

        # Update available tools with only the new tools from this server
        new_tools = [
            tool for tool in self.mcp_clients.tools if tool.server_id == server_id
        ]
        self.available_tools.add_tools(*new_tools)

        resolved_server_id = server_id or server_url
        instructions = self.mcp_clients.server_instructions.get(resolved_server_id)
        if instructions and resolved_server_id not in self.mcp_instruction_servers:
            transport_instructions = (
                f"{_BROWSER_USE_TRANSPORT_INSTRUCTIONS}\n"
                if resolved_server_id == _BROWSER_USE_SERVER_ID
                else ""
            )
            self.memory.add_message(
                Message.system_message(
                    f"{transport_instructions}MCP server instructions:\n{instructions}"
                )
            )
            self.mcp_instruction_servers.add(resolved_server_id)

    async def disconnect_mcp_server(self, server_id: str = "") -> None:
        """Disconnect from an MCP server and remove its tools."""
        await self.mcp_clients.disconnect(server_id)
        if server_id:
            self.connected_servers.pop(server_id, None)
        else:
            self.connected_servers.clear()

        # Rebuild available tools without the disconnected server's tools
        base_tools = [
            tool
            for tool in self.available_tools.tools
            if not isinstance(tool, MCPClientTool)
        ]
        self.available_tools = ToolCollection(*base_tools)
        self.available_tools.add_tools(*self.mcp_clients.tools)

    async def cleanup(self):
        """Clean up Manus agent resources."""
        # Disconnect from all MCP servers only if we were initialized
        if self._initialized:
            await self.disconnect_mcp_server()
            self._initialized = False

    async def think(self) -> bool:
        """Process current state and decide next actions with appropriate context."""
        if not self._initialized:
            await self.initialize_mcp_servers()
            self._initialized = True

        return await super().think()
