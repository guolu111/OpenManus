"""
评论区搜索+代码拉取工具 - 搜索代码/软件问题的成熟解决方案，并拉取可用代码
搜索范围：GitHub Issues、Stack Overflow、掘金、CSDN、知乎技术区、V2EX
核心能力：搜索评论区方案 + 自动拉取GitHub成熟代码，只需微调定制
使用场景：遇到代码bug、软件配置、API接入问题时，先搜成熟方案，拉取代码，只做微调
"""
import asyncio
import urllib.request
from typing import Optional, ClassVar

from pydantic import Field

from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.web_search import WebSearch, SearchResponse, SearchResult, SearchMetadata


class CommentSearchResult(ToolResult):
    """评论区搜索+代码拉取结果"""
    query: str = Field(description="搜索关键词")
    results: list[dict] = Field(default_factory=list, description="搜索结果列表")
    code_snippets: list[dict] = Field(default_factory=list, description="拉取到的代码片段")
    summary: str = Field(default="", description="结果摘要")

    def model_post_init(self, __context) -> None:
        if self.error:
            return
        lines = [f"🔍 成熟方案搜索: '{self.query}'", ""]
        for i, r in enumerate(self.results, 1):
            lines.append(f"{i}. {r.get('title', '无标题')}")
            lines.append(f"   来源: {r.get('source', '?')}")
            lines.append(f"   链接: {r.get('url', '')}")
            if r.get('description'):
                lines.append(f"   摘要: {r['description'][:150]}")
            lines.append("")
        if self.code_snippets:
            lines.append("=" * 50)
            lines.append("📦 拉取到的成熟代码（可直接微调使用）:")
            lines.append("")
            for i, c in enumerate(self.code_snippets, 1):
                lines.append(f"--- 代码{i}: {c.get('source', '?')} ---")
                lines.append(f"文件: {c.get('filename', '?')}")
                lines.append(c.get('code', '')[:2000])
                lines.append("")
        if self.summary:
            lines.append(f"💡 总结: {self.summary}")
        self.output = "\n".join(lines)


class CommentSearch(BaseTool):
    """
    评论区搜索+代码拉取工具 - 遇到代码/软件问题时，搜索成熟方案并拉取可用代码
    搜索范围：GitHub Issues、Stack Overflow、掘金、CSDN、知乎、V2EX
    核心：搜索成熟方案 + 自动拉取GitHub代码，只需微调定制
    """
    name: str = "search_comments"
    description: str = """专门搜索代码和软件问题的成熟解决方案，并自动拉取可用代码。当你遇到代码bug、API接入失败、软件配置问题、依赖冲突等技术问题时，必须先调用此工具搜索别人踩过的坑和成熟方案，不要自己瞎试。
搜索范围包括：GitHub Issues、Stack Overflow、掘金、CSDN、知乎技术区、V2EX等。
开启fetch_code后会自动拉取GitHub上的成熟代码文件，可直接微调使用。
返回结果包含标题、来源、链接、摘要和拉取到的代码。"""

    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "(required) 要搜索的技术问题关键词，用中文或英文都可以",
            },
            "num_results": {
                "type": "integer",
                "description": "(optional) 返回结果数量，默认8条",
                "default": 8,
            },
            "fetch_code": {
                "type": "boolean",
                "description": "(optional) 是否自动拉取GitHub上的成熟代码文件，默认True",
                "default": True,
            },
        },
        "required": ["query"],
    }

    # 技术社区站点列表
    TECH_SITES: ClassVar[list[str]] = [
        "github.com/issues",
        "stackoverflow.com",
        "juejin.cn",
        "csdn.net",
        "zhihu.com",
        "v2ex.com",
        "segmentfault.com",
        "oschina.net",
    ]

    _web_search: ClassVar[WebSearch] = WebSearch()

    async def execute(
        self,
        query: str,
        num_results: int = 8,
        fetch_code: bool = True,
    ) -> CommentSearchResult:
        """执行评论区搜索+代码拉取"""
        logger.info(f"[CommentSearch] 搜索: {query}, fetch_code={fetch_code}")

        # 构造搜索query：加上技术社区站点限制
        site_filter = " OR ".join([f"site:{s}" for s in self.TECH_SITES])
        enhanced_query = f"{query} ({site_filter})"

        try:
            # 用WebSearch搜索
            search_result: SearchResponse = await self._web_search.execute(
                query=enhanced_query,
                num_results=num_results,
                lang="zh",
                fetch_content=False,
            )

            # 过滤结果，只保留技术社区的
            filtered = []
            for r in search_result.results:
                url = r.url.lower()
                if any(site in url for site in self.TECH_SITES):
                    filtered.append({
                        "title": r.title,
                        "url": r.url,
                        "description": r.description,
                        "source": r.source,
                    })

            # 如果过滤后太少，放宽限制（用原始搜索结果）
            if len(filtered) < 3:
                filtered = [{
                    "title": r.title,
                    "url": r.url,
                    "description": r.description,
                    "source": r.source,
                } for r in search_result.results[:num_results]]

            # 拉取GitHub代码
            code_snippets = []
            if fetch_code:
                code_snippets = await self._fetch_github_code(filtered)

            # 生成摘要
            summary = self._generate_summary(query, filtered, code_snippets)

            logger.info(f"[CommentSearch] 找到 {len(filtered)} 条结果, 拉取 {len(code_snippets)} 段代码")
            return CommentSearchResult(
                query=query,
                results=filtered[:num_results],
                code_snippets=code_snippets,
                summary=summary,
            )

        except Exception as e:
            logger.error(f"[CommentSearch] 搜索失败: {e}")
            return CommentSearchResult(
                query=query,
                error=f"搜索失败: {str(e)}",
                output=f"搜索失败: {str(e)}",
            )

    async def _fetch_github_code(self, results: list[dict]) -> list[dict]:
        """从搜索结果中提取GitHub链接，拉取代码文件内容"""
        code_snippets = []
        github_urls = []

        for r in results:
            url = r.get("url", "")
            # 提取GitHub仓库链接
            if "github.com" in url:
                github_urls.append(url)

        # 去重，最多拉取3个
        github_urls = list(dict.fromkeys(github_urls))[:3]

        for url in github_urls:
            try:
                # 尝试转换为raw URL并拉取
                raw_url = self._convert_to_raw_url(url)
                if raw_url:
                    code = await self._fetch_url_content(raw_url)
                    if code and len(code) > 50:
                        filename = raw_url.split("/")[-1]
                        code_snippets.append({
                            "source": url,
                            "filename": filename,
                            "code": code[:3000],
                        })
                        logger.info(f"[CommentSearch] 拉取代码成功: {filename} ({len(code)} chars)")
            except Exception as e:
                logger.warning(f"[CommentSearch] 拉取代码失败 {url}: {e}")

        return code_snippets

    def _convert_to_raw_url(self, url: str) -> Optional[str]:
        """将GitHub URL转换为raw URL"""
        # github.com/user/repo/blob/branch/path -> raw.githubusercontent.com/user/repo/branch/path
        if "github.com" in url and "/blob/" in url:
            return url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        # github.com/user/repo -> 尝试拉取README
        if "github.com" in url and url.count("/") >= 4:
            parts = url.split("?")[0].rstrip("/").split("/")
            if len(parts) >= 5:
                user, repo = parts[3], parts[4]
                return f"https://raw.githubusercontent.com/{user}/{repo}/main/README.md"
        return None

    async def _fetch_url_content(self, url: str, timeout: int = 10) -> Optional[str]:
        """异步拉取URL内容"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._sync_fetch, url, timeout)
        except Exception as e:
            logger.warning(f"拉取URL失败 {url}: {e}")
            return None

    def _sync_fetch(self, url: str, timeout: int = 10) -> Optional[str]:
        """同步拉取URL内容"""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception:
            return None

    def _generate_summary(self, query: str, results: list[dict], code_snippets: list[dict]) -> str:
        """生成搜索结果摘要"""
        if not results:
            return "未找到相关结果，建议换个关键词再试，或者直接描述错误信息搜索。"

        sources = {}
        for r in results:
            url = r.get("url", "")
            for site in self.TECH_SITES:
                if site in url:
                    sources[site] = sources.get(site, 0) + 1
                    break

        source_str = ", ".join([f"{k.split('.')[0]}({v}条)" for k, v in sources.items()])
        code_str = f"，已拉取{len(code_snippets)}段成熟代码可直接微调" if code_snippets else ""
        return f"共找到{len(results)}条相关讨论，来源: {source_str}{code_str}。建议优先看GitHub Issues和Stack Overflow的高赞回答，拉取到的代码只需根据本地配置微调即可使用。"
