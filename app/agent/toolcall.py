import asyncio
import json
import os
import re
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional, Union

from pydantic import Field, PrivateAttr

from app.agent.react import ReActAgent
from app.exceptions import TokenLimitExceeded
from app.logger import logger
from app.prompt.toolcall import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import TOOL_CHOICE_TYPE, AgentState, Message, ToolCall, ToolChoice
from app.tool import CreateChatCompletion, Terminate, ToolCollection


TOOL_CALL_REQUIRED = "Tool calls required but none provided"


class ToolCallAgent(ReActAgent):
    """Base agent class for handling tool/function calls with enhanced abstraction"""

    name: str = "toolcall"
    description: str = "an agent that can execute tool calls."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    available_tools: ToolCollection = ToolCollection(
        CreateChatCompletion(), Terminate()
    )
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO  # type: ignore
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    tool_calls: List[ToolCall] = Field(default_factory=list)
    _current_base64_image: Optional[str] = None

    max_steps: int = 30
    max_observe: Optional[Union[int, bool]] = None

    # 2026-09-05 一念永恒 · 防并发抢浏览器改造（②重复检测③失败重试上限）
    # 同工具+同参数 连续调用的失败计数与成功缓存，防止 Agent 反复启动同一脚本
    _tool_retry: Dict[str, int] = PrivateAttr(default_factory=dict)   # key -> 连续失败次数
    _tool_cache: Dict[str, str] = PrivateAttr(default_factory=dict)   # key -> 上次成功结果
    max_tool_retries: int = 2  # 同一工具同一参数最多失败重试 2 次，超过则阻断并提示换策略

    async def think(self) -> bool:
        """Process current state and decide next actions using tools"""
        if self.next_step_prompt:
            user_msg = Message.user_message(self.next_step_prompt)
            self.messages += [user_msg]

        try:
            # Get response with tool options
            response = await self.llm.ask_tool(
                messages=self.messages,
                system_msgs=(
                    [Message.system_message(self.system_prompt)]
                    if self.system_prompt
                    else None
                ),
                tools=self.available_tools.to_params(),
                tool_choice=self.tool_choices,
            )
        except ValueError:
            raise
        except Exception as e:
            # Check if this is a RetryError containing TokenLimitExceeded
            if hasattr(e, "__cause__") and isinstance(e.__cause__, TokenLimitExceeded):
                token_limit_error = e.__cause__
                logger.error(
                    f"🚨 Token limit error (from RetryError): {token_limit_error}"
                )
                self.memory.add_message(
                    Message.assistant_message(
                        f"Maximum token limit reached, cannot continue execution: {str(token_limit_error)}"
                    )
                )
                self.state = AgentState.FINISHED
                return False
            raise

        self.tool_calls = tool_calls = (
            response.tool_calls if response and response.tool_calls else []
        )
        content = response.content if response and response.content else ""

        # Log response info
        logger.info(f"✨ {self.name}'s thoughts: {content}")
        logger.info(
            f"🛠️ {self.name} selected {len(tool_calls) if tool_calls else 0} tools to use"
        )
        if tool_calls:
            logger.info(
                f"🧰 Tools being prepared: {[call.function.name for call in tool_calls]}"
            )
            logger.info(f"🔧 Tool arguments: {tool_calls[0].function.arguments}")

        try:
            if response is None:
                raise RuntimeError("No response received from the LLM")

            # Handle different tool_choices modes
            if self.tool_choices == ToolChoice.NONE:
                if tool_calls:
                    logger.warning(
                        f"🤔 Hmm, {self.name} tried to use tools when they weren't available!"
                    )
                if content:
                    self.memory.add_message(Message.assistant_message(content))
                    return True
                return False

            # Create and add assistant message
            assistant_msg = (
                Message.from_tool_calls(content=content, tool_calls=self.tool_calls)
                if self.tool_calls
                else Message.assistant_message(content)
            )
            self.memory.add_message(assistant_msg)

            if self.tool_choices == ToolChoice.REQUIRED and not self.tool_calls:
                return True  # Will be handled in act()

            # For 'auto' mode, continue with content if no commands but content exists
            if self.tool_choices == ToolChoice.AUTO and not self.tool_calls:
                return bool(content)

            return bool(self.tool_calls)
        except Exception as e:
            logger.error(f"🚨 Oops! The {self.name}'s thinking process hit a snag: {e}")
            self.memory.add_message(
                Message.assistant_message(
                    f"Error encountered while processing: {str(e)}"
                )
            )
            return False

    async def act(self) -> str:
        """Execute tool calls and handle their results"""
        if not self.tool_calls:
            if self.tool_choices == ToolChoice.REQUIRED:
                raise ValueError(TOOL_CALL_REQUIRED)

            # Return last message content if no tool calls
            return self.messages[-1].content or "No content or commands to execute"

        results = []
        image_messages = []
        for command in self.tool_calls:
            # Reset base64_image for each tool call
            self._current_base64_image = None

            # ---- 2026-09-05 防并发抢浏览器：重复检测 + 失败重试上限 ----
            # 用「工具名 + 原始参数」作为调用指纹，识别同一脚本被反复启动
            _name = command.function.name if command.function else ""
            _args = command.function.arguments if command.function else ""
            _key = f"{_name}|{_args}"

            # ② 成功缓存：同工具同参数、上次执行成功 → 直接返回缓存，阻断死循环
            if _key in self._tool_cache and self._tool_retry.get(_key, 0) == 0:
                result = self._tool_cache[_key]
                logger.warning(
                    f"🔄 检测到重复工具调用 '{_name}'（相同参数），直接返回上次成功结果，阻断重复执行"
                )
                self.memory.add_message(
                    Message.assistant_message(
                        f"检测到重复调用工具 '{_name}'（相同参数，上次已成功），已直接返回上次结果。"
                        f"请勿继续重复执行同一命令；若任务未完成，请更换策略或向用户说明。"
                    )
                )
            # ③ 失败重试上限：同工具同参数连续失败已达上限 → 阻断执行，提示换策略
            elif self._tool_retry.get(_key, 0) >= self.max_tool_retries:
                _rc = self._tool_retry.get(_key, 0)
                result = (
                    f"Error: Tool '{_name}' 已连续失败 {_rc} 次（达到上限 {self.max_tool_retries}），"
                    f"已自动阻断重复执行。请更换策略，或向用户说明遇到的困难。"
                )
                logger.warning(f"🛑 工具 '{_name}' 连续失败达上限 {_rc} 次，已阻断执行")
                self.memory.add_message(
                    Message.assistant_message(
                        f"工具 '{_name}' 已连续失败 {_rc} 次（达到上限 {self.max_tool_retries}），"
                        f"已阻断。请勿再重试，请更换策略或向用户说明困难。"
                    )
                )
            else:
                result = await self.execute_tool(command)
                # 记录成功/失败状态，供下一次调用判断
                if result.startswith("Error"):
                    self._tool_retry[_key] = self._tool_retry.get(_key, 0) + 1
                    self._tool_cache.pop(_key, None)
                else:
                    self._tool_retry[_key] = 0
                    self._tool_cache[_key] = result

            if self.max_observe:
                result = result[: self.max_observe]

            logger.info(
                f"🎯 Tool '{command.function.name}' completed its mission! Result: {result}"
            )

            # Add tool response to memory
            tool_msg = Message.tool_message(
                content=result,
                tool_call_id=command.id,
                name=command.function.name,
            )
            self.memory.add_message(tool_msg)
            if self._current_base64_image:
                image_messages.append(
                    Message.user_message(
                        content=f"Image returned by {command.function.name}:",
                        base64_image=self._current_base64_image,
                    )
                )
            results.append(result)

        self.memory.add_messages(image_messages)
        return "\n\n".join(results)

    # 工具返回结果自动截断阈值（超过此长度自动存文件）
    TOOL_RESULT_TRUNCATE_THRESHOLD: ClassVar[int] = 2000  # 字符数
    TOOL_OUTPUT_DIR: ClassVar[str] = "logs/tool_outputs"  # 长结果保存目录
    # 工具掩码：None 表示全部可用，列表表示只允许这些工具（参考Manus教训三）
    _allowed_tools: ClassVar[Optional[List[str]]] = None

    @classmethod
    def set_allowed_tools(cls, tools: Optional[List[str]] = None):
        """设置当前允许使用的工具列表（None 表示全部可用）。
        
        参考 Manus 教训三：工具掩码而非移除，保持 KV 缓存稳定。
        常用预设：
        - 浏览器模式: ["browser_exec", "browser_screenshot", "web_search"]
        - 文件模式: ["str_replace_editor", "bash", "python_execute"]
        - 跑批模式: ["batch_run", "bridge_health", "status_monitor", "notify_feishu", "usage_monitor"]
        - 简单查询: ["usage_monitor", "status_monitor", "memory", "terminate"]
        """
        cls._allowed_tools = tools
        if tools:
            logger.info(f"🎭 工具掩码已设置：只允许 {len(tools)} 个工具")
        else:
            logger.info(f"🎭 工具掩码已解除：全部工具可用")

    @classmethod
    def get_allowed_tools(cls) -> Optional[List[str]]:
        """获取当前允许使用的工具列表"""
        return cls._allowed_tools

    def _truncate_long_result(self, name: str, result_str: str) -> str:
        """自动截断长工具结果：保存到文件，返回摘要+文件路径。
        
        参考Manus教训四：文件系统=无限草稿纸，上下文只留路径和摘要。
        """
        if len(result_str) <= self.TOOL_RESULT_TRUNCATE_THRESHOLD:
            return result_str
        
        # 确保输出目录存在
        try:
            os.makedirs(self.TOOL_OUTPUT_DIR, exist_ok=True)
        except Exception:
            pass
        
        # 生成文件名（工具名+时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 清理工具名中的非法字符
        safe_name = re.sub(r'[^\w\-]', '_', name)
        filename = f"{safe_name}_{timestamp}.txt"
        filepath = os.path.join(self.TOOL_OUTPUT_DIR, filename)
        
        # 保存完整结果到文件
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"工具: {name}\n")
                f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"长度: {len(result_str)} 字符\n")
                f.write("=" * 60 + "\n\n")
                f.write(result_str)
            
            # 生成摘要（前500字符 + 后200字符）
            head = result_str[:500]
            tail = result_str[-200:] if len(result_str) > 700 else ""
            summary = f"{head}\n\n... [中间 {len(result_str) - 700} 字符已省略，完整内容已保存] ...\n\n{tail}" if tail else head + "\n\n... [内容已省略，完整内容已保存] ..."
            
            truncated_result = (
                f"{summary}\n\n"
                f"📝 完整输出已保存到: {filepath}\n"
                f"   （完整长度: {len(result_str)} 字符，使用 str_replace_editor 或 bash 读取完整内容）"
            )
            
            logger.info(f"📦 工具 '{name}' 输出过长（{len(result_str)}字符），已自动截断并保存到 {filepath}")
            return truncated_result
            
        except Exception as e:
            logger.warning(f"自动截断保存失败（返回截断内容）: {e}")
            # 保存失败时直接截断
            return result_str[:self.TOOL_RESULT_TRUNCATE_THRESHOLD] + f"\n\n... [输出过长，已截断至{self.TOOL_RESULT_TRUNCATE_THRESHOLD}字符]"

    async def execute_tool(self, command: ToolCall) -> str:
        """Execute a single tool call with robust error handling"""
        if not command or not command.function or not command.function.name:
            return "Error: Invalid command format"

        name = command.function.name
        if name not in self.available_tools.tool_map:
            return f"Error: Unknown tool '{name}'"

        # 工具掩码检查（参考Manus教训三：蒙上眼而非拿走）
        if self._allowed_tools is not None and name not in self._allowed_tools:
            available = ", ".join(self._allowed_tools)
            logger.warning(f"🎭 工具掩码拦截：尝试调用不允许的工具 '{name}'")
            return (
                f"Error: Tool '{name}' is not available in current context (tool masking active).\n"
                f"Available tools: {available}\n"
                f"Please select a tool from the available list above."
            )

        try:
            # Parse arguments
            args = json.loads(command.function.arguments or "{}")

            # Execute the tool（添加超时设置，防止工具执行卡住）
            logger.info(f"🔧 Activating tool: '{name}'...")
            try:
                result = await asyncio.wait_for(
                    self.available_tools.execute(name=name, tool_input=args),
                    timeout=60  # 工具执行超时60秒
                )
            except asyncio.TimeoutError:
                error_msg = f"Tool '{name}' execution timed out after 60 seconds"
                logger.error(f"⏰ {error_msg}")
                return f"Error: {error_msg}"

            # Handle special tools
            await self._handle_special_tool(name=name, result=result)

            # Check if result is a ToolResult with base64_image
            if hasattr(result, "base64_image") and result.base64_image:
                # Store the base64_image for later use in tool_message
                self._current_base64_image = result.base64_image

            # Format result for display (standard case)
            result_str = str(result) if result else ""
            # 自动截断长结果：保存到文件，上下文只留摘要+路径（参考Manus教训四）
            if result_str and len(result_str) > self.TOOL_RESULT_TRUNCATE_THRESHOLD:
                result_str = self._truncate_long_result(name, result_str)
            
            observation = (
                f"Observed output of cmd `{name}` executed:\n{result_str}"
                if result_str
                else f"Cmd `{name}` completed with no output"
            )

            return observation
        except json.JSONDecodeError:
            error_msg = f"Error parsing arguments for {name}: Invalid JSON format"
            logger.error(
                f"📝 Oops! The arguments for '{name}' don't make sense - invalid JSON, arguments:{command.function.arguments}"
            )
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"⚠️ Tool '{name}' encountered a problem: {str(e)}"
            logger.exception(error_msg)
            return f"Error: {error_msg}"

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        """Handle special tool execution and state changes"""
        if not self._is_special_tool(name):
            return

        if self._should_finish_execution(name=name, result=result, **kwargs):
            # Set agent state to finished
            logger.info(f"🏁 Special tool '{name}' has completed the task!")
            self.state = AgentState.FINISHED

    @staticmethod
    def _should_finish_execution(**kwargs) -> bool:
        """Determine if tool execution should finish the agent"""
        return True

    def _is_special_tool(self, name: str) -> bool:
        """Check if tool name is in special tools list"""
        return name.lower() in [n.lower() for n in self.special_tool_names]

    async def cleanup(self):
        """Clean up resources used by the agent's tools."""
        logger.info(f"🧹 Cleaning up resources for agent '{self.name}'...")
        for tool_name, tool_instance in self.available_tools.tool_map.items():
            if hasattr(tool_instance, "cleanup") and asyncio.iscoroutinefunction(
                tool_instance.cleanup
            ):
                try:
                    logger.debug(f"🧼 Cleaning up tool: {tool_name}")
                    await tool_instance.cleanup()
                except Exception as e:
                    logger.error(
                        f"🚨 Error cleaning up tool '{tool_name}': {e}", exc_info=True
                    )
        logger.info(f"✨ Cleanup complete for agent '{self.name}'.")

    async def run(self, request: Optional[str] = None) -> str:
        """Run the agent with cleanup when done."""
        try:
            return await super().run(request)
        finally:
            await self.cleanup()
