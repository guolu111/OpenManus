"""
FeishuHandler - 飞书消息处理器

功能：
1. 接收飞书消息（通过Webhook或长连接）
2. 解析消息内容，提取指令
3. 调用Manus统帅执行任务
4. 将执行结果发送回飞书
5. 支持消息卡片、文本、图片等多种格式

使用方式：
    from app.remote_control import FeishuHandler

    handler = FeishuHandler(
        app_id="cli_xxx",
        app_secret="xxx",
        verification_token="xxx",
        encrypt_key="xxx",
    )

    # 处理收到的消息
    result = await handler.handle_message(message_data)

    # 发送消息
    await handler.send_message(chat_id="oc_xxx", text="任务完成")
"""

import json
import time
import hashlib
import hmac
import base64
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.logger import logger


class MessageType(Enum):
    """消息类型"""
    TEXT = "text"
    IMAGE = "image"
    POST = "post"          # 富文本
    INTERACTIVE = "interactive"  # 消息卡片
    FILE = "file"
    AUDIO = "audio"
    MEDIA = "media"
    STICKER = "sticker"


class CommandType(Enum):
    """指令类型"""
    CHAT = "chat"              # 普通对话
    TASK = "task"              # 执行任务
    STATUS = "status"          # 查看状态
    HELP = "help"              # 帮助
    ROLE = "role"              # 切换角色
    UNKNOWN = "unknown"        # 未知指令


@dataclass
class FeishuMessage:
    """飞书消息"""
    message_id: str                    # 消息ID
    chat_id: str                       # 会话ID
    chat_type: str                     # 会话类型（p2p/group）
    sender_id: str                     # 发送者ID
    sender_name: str                   # 发送者名称
    message_type: MessageType          # 消息类型
    content: str                       # 消息内容（文本）
    raw_content: Dict[str, Any] = field(default_factory=dict)  # 原始内容
    timestamp: datetime = field(default_factory=datetime.now)   # 时间戳
    mentions: List[str] = field(default_factory=list)  # @的人


@dataclass
class Command:
    """解析后的指令"""
    command_type: CommandType          # 指令类型
    raw_text: str                      # 原始文本
    args: Dict[str, str] = field(default_factory=dict)  # 参数
    role: Optional[str] = None         # 指定的角色
    task_description: Optional[str] = None  # 任务描述


class FeishuHandler:
    """
    飞书消息处理器

    负责接收、解析、处理、发送飞书消息。
    """

    def __init__(
        self,
        app_id: str = "",
        app_secret: str = "",
        verification_token: str = "",
        encrypt_key: str = "",
        on_command: Optional[Callable[[Command], Awaitable[str]]] = None,
    ):
        """
        初始化飞书消息处理器

        Args:
            app_id: 飞书应用ID
            app_secret: 飞书应用密钥
            verification_token: 验证令牌
            encrypt_key: 加密密钥
            on_command: 指令处理回调函数
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.verification_token = verification_token
        self.encrypt_key = encrypt_key
        self.on_command = on_command

        self.tenant_access_token: Optional[str] = None
        self.token_expire_time: float = 0

        self.message_history: List[FeishuMessage] = []
        self.command_history: List[Command] = []

        # 指令前缀
        self.command_prefixes = {
            "/task": CommandType.TASK,
            "/status": CommandType.STATUS,
            "/help": CommandType.HELP,
            "/role": CommandType.ROLE,
            "/chat": CommandType.CHAT,
        }

        logger.info("飞书消息处理器初始化完成")

    async def get_tenant_access_token(self) -> str:
        """
        获取租户访问令牌

        Returns:
            访问令牌
        """
        # 如果令牌还没过期，直接返回
        if self.tenant_access_token and time.time() < self.token_expire_time:
            return self.tenant_access_token

        # 模拟获取令牌（实际需要调用飞书API）
        # 这里返回一个占位符，实际使用时需要替换为真实API调用
        logger.info("获取租户访问令牌（模拟）")
        self.tenant_access_token = "t-placeholder-token"
        self.token_expire_time = time.time() + 7200  # 2小时有效期
        return self.tenant_access_token

    def verify_signature(self, timestamp: str, nonce: str, encrypt: str, signature: str) -> bool:
        """
        验证消息签名

        Args:
            timestamp: 时间戳
            nonce: 随机字符串
            encrypt: 加密内容
            signature: 签名

        Returns:
            是否验证通过
        """
        if not self.encrypt_key:
            return True

        content = f"{timestamp}{nonce}{self.encrypt_key}{encrypt}"
        calculated = hashlib.sha256(content.encode()).hexdigest()
        return calculated == signature

    def decrypt_message(self, encrypt: str) -> str:
        """
        解密消息

        Args:
            encrypt: 加密内容

        Returns:
            解密后的内容
        """
        if not self.encrypt_key:
            return encrypt

        # 模拟解密（实际需要AES解密）
        logger.info("解密消息（模拟）")
        return encrypt

    def parse_message(self, event_data: Dict[str, Any]) -> Optional[FeishuMessage]:
        """
        解析飞书消息事件

        Args:
            event_data: 事件数据

        Returns:
            解析后的消息对象
        """
        try:
            event = event_data.get("event", event_data)
            message = event.get("message", {})

            message_id = message.get("message_id", "")
            chat_id = message.get("chat_id", "")
            chat_type = message.get("chat_type", "p2p")
            msg_type = message.get("message_type", "text")

            sender = event.get("sender", {})
            sender_id = sender.get("sender_id", {}).get("open_id", "")
            sender_name = sender.get("sender_id", {}).get("name", "未知用户")

            # 解析内容
            content_str = message.get("content", "{}")
            if isinstance(content_str, str):
                raw_content = json.loads(content_str)
            else:
                raw_content = content_str

            # 提取文本内容
            text = ""
            if msg_type == "text":
                text = raw_content.get("text", "")
            elif msg_type == "post":
                # 富文本，提取所有文本
                title = raw_content.get("title", "")
                content_lines = []
                for paragraph in raw_content.get("content", []):
                    for element in paragraph:
                        if element.get("tag") == "text":
                            content_lines.append(element.get("text", ""))
                text = f"{title}\n" + "\n".join(content_lines)

            # 提取@的人
            mentions = []
            for mention in raw_content.get("mentions", []):
                mentions.append(mention.get("name", ""))

            feishu_msg = FeishuMessage(
                message_id=message_id,
                chat_id=chat_id,
                chat_type=chat_type,
                sender_id=sender_id,
                sender_name=sender_name,
                message_type=MessageType(msg_type),
                content=text,
                raw_content=raw_content,
                mentions=mentions,
            )

            self.message_history.append(feishu_msg)
            logger.info(f"消息解析成功: {sender_name}: {text[:50]}...")
            return feishu_msg

        except Exception as e:
            logger.error(f"消息解析失败: {e}")
            return None

    def parse_command(self, message: FeishuMessage) -> Command:
        """
        从消息中解析指令

        Args:
            message: 飞书消息

        Returns:
            解析后的指令
        """
        text = message.content.strip()

        # 检查是否是指令
        command_type = CommandType.CHAT
        args = {}
        role = None
        task_description = None

        for prefix, cmd_type in self.command_prefixes.items():
            if text.startswith(prefix):
                command_type = cmd_type
                # 提取参数
                remaining = text[len(prefix):].strip()
                if cmd_type == CommandType.TASK:
                    task_description = remaining
                elif cmd_type == CommandType.ROLE:
                    role = remaining
                elif cmd_type == CommandType.STATUS:
                    # 可以指定查看什么状态
                    if remaining:
                        args["target"] = remaining
                break

        # 如果没有指令前缀，检查是否包含角色关键词
        if command_type == CommandType.CHAT:
            # 简单的角色检测
            role_keywords = ["分析", "生成", "老师", "学生", "匹配", "小助手", "管理员"]
            for keyword in role_keywords:
                if keyword in text:
                    role = keyword
                    break

        command = Command(
            command_type=command_type,
            raw_text=text,
            args=args,
            role=role,
            task_description=task_description,
        )

        self.command_history.append(command)
        logger.info(f"指令解析: {command_type.value}, 角色: {role}, 任务: {task_description[:30] if task_description else 'N/A'}...")
        return command

    async def handle_message(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理收到的飞书消息

        Args:
            event_data: 事件数据

        Returns:
            处理结果
        """
        # 解析消息
        message = self.parse_message(event_data)
        if not message:
            return {"status": "error", "message": "消息解析失败"}

        # 解析指令
        command = self.parse_command(message)

        # 处理指令
        result_text = await self._execute_command(command, message)

        # 发送回复
        await self.send_message(
            chat_id=message.chat_id,
            text=result_text,
            reply_to=message.message_id,
        )

        return {
            "status": "success",
            "message_id": message.message_id,
            "command": command.command_type.value,
            "result": result_text,
        }

    async def _execute_command(self, command: Command, message: FeishuMessage) -> str:
        """
        执行指令

        Args:
            command: 指令
            message: 原始消息

        Returns:
            执行结果文本
        """
        # 如果有自定义回调函数，调用它
        if self.on_command:
            try:
                return await self.on_command(command)
            except Exception as e:
                logger.error(f"自定义指令处理失败: {e}")
                return f"指令处理失败: {e}"

        # 默认处理
        if command.command_type == CommandType.HELP:
            return self._get_help_text()
        elif command.command_type == CommandType.STATUS:
            return self._get_status_text()
        elif command.command_type == CommandType.TASK:
            return f"收到任务: {command.task_description}\n\n（任务执行功能需要连接Manus统帅）"
        elif command.command_type == CommandType.ROLE:
            return f"已切换到角色: {command.role}\n\n（角色切换功能需要连接Manus统帅）"
        else:
            return f"收到消息: {command.raw_text[:100]}\n\n（对话功能需要连接Manus统帅）"

    def _get_help_text(self) -> str:
        """获取帮助文本"""
        return """🤖 OpenManus统帅 - 飞书远程操控

可用指令：
/task <任务描述> - 执行任务
/status - 查看系统状态
/role <角色名> - 切换角色
/help - 显示帮助
/chat <内容> - 普通对话

支持的角色：
分析、生成、老师、学生、匹配、小助手、管理员

示例：
/task 分析这段文本的情感倾向
/role 分析
/status
"""

    def _get_status_text(self) -> str:
        """获取状态文本"""
        return f"""📊 系统状态

消息处理器：运行中
已处理消息：{len(self.message_history)} 条
已解析指令：{len(self.command_history)} 条
令牌状态：{'有效' if self.tenant_access_token else '未获取'}

（完整状态需要连接Manus统帅和任务看板）
"""

    async def send_message(
        self,
        chat_id: str,
        text: str,
        msg_type: MessageType = MessageType.TEXT,
        reply_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        发送消息到飞书

        Args:
            chat_id: 会话ID
            text: 消息内容
            msg_type: 消息类型
            reply_to: 回复的消息ID

        Returns:
            发送结果
        """
        # 获取令牌
        token = await self.get_tenant_access_token()

        # 构建消息内容
        if msg_type == MessageType.TEXT:
            content = json.dumps({"text": text})
        else:
            content = json.dumps({"text": text})

        # 模拟发送（实际需要调用飞书API）
        logger.info(f"发送消息到 {chat_id}: {text[:50]}...")

        return {
            "status": "success",
            "chat_id": chat_id,
            "message_type": msg_type.value,
            "content": text,
            "reply_to": reply_to,
            "timestamp": datetime.now().isoformat(),
        }

    async def send_interactive_card(
        self,
        chat_id: str,
        title: str,
        content: str,
        buttons: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        发送交互式消息卡片

        Args:
            chat_id: 会话ID
            title: 卡片标题
            content: 卡片内容
            buttons: 按钮列表

        Returns:
            发送结果
        """
        # 构建卡片内容
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": content},
                }
            ],
        }

        # 添加按钮
        if buttons:
            action_elements = []
            for btn in buttons:
                action_elements.append({
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": btn.get("text", "按钮")},
                    "type": btn.get("type", "primary"),
                    "value": {"action": btn.get("action", "default")},
                })
            card["elements"].append({
                "tag": "action",
                "actions": action_elements,
            })

        logger.info(f"发送消息卡片到 {chat_id}: {title}")

        return {
            "status": "success",
            "chat_id": chat_id,
            "card": card,
            "timestamp": datetime.now().isoformat(),
        }

    def status(self) -> str:
        """获取处理器状态"""
        return f"""=== 飞书消息处理器状态 ===
应用ID: {self.app_id[:10]}...
已处理消息: {len(self.message_history)} 条
已解析指令: {len(self.command_history)} 条
令牌状态: {'有效' if self.tenant_access_token else '未获取'}
回调函数: {'已设置' if self.on_command else '未设置'}
"""
