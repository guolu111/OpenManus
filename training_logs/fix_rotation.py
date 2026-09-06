# -*- coding: utf-8 -*-
"""修复llm.py中的模型轮转初始化逻辑"""

with open('app/llm.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = """            # 初始化模型轮转器（2026-09-05用户指定）
            self.rotator = None
            try:
                rotation_config = getattr(llm_config, 'model_rotation', None)
                if rotation_config and getattr(rotation_config, 'enabled', False):
                    models = getattr(rotation_config, 'models', [])
                    pattern = getattr(rotation_config, 'rotation_pattern', list(range(len(models))))
                    limits = getattr(rotation_config, 'daily_limits', {})
                    if models:
                        self.rotator = ModelRotator(models, pattern, limits)
                        logger.info(f"[模型轮转] 已启用，模型列表: {models}")
            except Exception as e:
                logger.warning(f"[模型轮转] 初始化失败: {e}，将使用单模型模式")"""

new = """            # 初始化模型轮转器（2026-09-05用户指定）
            # 修复：从config.model_rotation获取，而不是从llm_config对象中获取（之前getattr永远返回None）
            self.rotator = None
            try:
                rotation_config = getattr(config, 'model_rotation', None)
                if rotation_config and getattr(rotation_config, 'enabled', False):
                    models = getattr(rotation_config, 'models', [])
                    pattern = getattr(rotation_config, 'rotation_pattern', list(range(len(models))))
                    limits = getattr(rotation_config, 'daily_limits', {})
                    if models:
                        self.rotator = ModelRotator(models, pattern, limits)
                        logger.info(f"[模型轮转] 已启用，模型列表: {models}, 轮转模式: {pattern}")
                    else:
                        logger.warning("[模型轮转] 配置已启用但models为空，使用单模型模式")
                else:
                    logger.info("[模型轮转] 未启用，使用单模型模式")
            except Exception as e:
                logger.warning(f"[模型轮转] 初始化失败: {e}，将使用单模型模式")
                import traceback
                logger.warning(traceback.format_exc())"""

if old in content:
    content = content.replace(old, new)
    print("已修复模型轮转初始化逻辑")
else:
    print("未找到匹配的文本，检查文件内容")
    # 尝试查找类似文本
    import re
    match = re.search(r'# 初始化模型轮转器.*?将使用单模型模式', content, re.DOTALL)
    if match:
        print("找到类似文本:")
        print(match.group()[:200])

with open('app/llm.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("修改完成")
