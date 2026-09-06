import os
import sys
import tempfile
import subprocess
from typing import Dict

from app.tool.base import BaseTool


class PythonExecute(BaseTool):
    """A tool for executing Python code with timeout and safety restrictions.

    Windows 兼容优化：使用 subprocess 代替 threading——
    threading.Thread.join(timeout) 在 Windows 上不会强制终止线程，
    导致超时后线程仍然在运行，进而导致后续工具调用卡住。
    subprocess 可以被强制终止，是更可靠的解决方案。
    """

    name: str = "python_execute"
    description: str = (
        "Executes Python code string. Note: Only print outputs are visible, "
        "function return values are not captured. Use print statements to see results. "
        "⚠️ 警告：不要用此工具创建文件或执行复杂操作，可能会超时卡住。"
        "创建文件请用 str_replace_editor 工具。"
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute.",
            },
        },
        "required": ["code"],
    }

    async def execute(
        self,
        code: str,
        timeout: int = 30,
    ) -> Dict:
        """
        Executes the provided Python code with a timeout using subprocess.

        使用 subprocess 执行代码，确保超时后子进程被强制终止，
        不会导致后续工具调用卡住。

        Args:
            code (str): The Python code to execute.
            timeout (int): Execution timeout in seconds.

        Returns:
            Dict: Contains 'output' with execution output or error message and 'success' status.
        """
        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False, encoding='utf-8'
        ) as f:
            # 添加编码声明和安全的globals
            f.write("# -*- coding: utf-8 -*-\n")
            f.write("import sys\n")
            f.write("sys.stdout.reconfigure(encoding='utf-8')\n")
            f.write(code)
            temp_file = f.name

        try:
            # 使用subprocess执行代码
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='replace',
                cwd=os.getcwd(),
            )

            # 合并stdout和stderr
            output = result.stdout
            if result.stderr:
                output += "\n[stderr]\n" + result.stderr

            return {
                "observation": output if output else "(no output)",
                "success": result.returncode == 0,
            }

        except subprocess.TimeoutExpired:
            return {
                "observation": f"Execution timeout after {timeout} seconds (subprocess terminated)",
                "success": False,
            }
        except Exception as e:
            return {
                "observation": f"Execution error: {str(e)}",
                "success": False,
            }
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file)
            except Exception:
                pass
