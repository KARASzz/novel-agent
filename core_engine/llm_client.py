from typing import Any, Dict, List, Optional
from openai import OpenAI

class LLMClient:
    """
    大语言模型调用代理 (LLM Client Proxy)
    职责：封装 DashScope (OpenAI 兼容接口) 的调用逻辑，
    处理 instructions/input 的拼装，以及 Reasoning Mode (Thinking) 和 Session Cache 的自动注入。
    """
    def __init__(
        self, 
        api_key: str, 
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        timeout: float = 300.0
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        
        # 默认开启 Session Cache Header，优化长剧本上下文解析时的响应速度和 Token 消耗
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            default_headers={"x-dashscope-session-cache": "enable"}
        )

    def create_response(
        self,
        model: str,
        instructions: str,
        input_text: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.1,
        top_p: float = 0.7,
        enable_thinking: bool = True,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """
        发起模型调用请求 (通过 DashScope 的 Responses API)
        
        Args:
            model: 模型 ID (例如 qwen3.6-plus)
            instructions: 系统指令 (System Message)
            input_text: 待处理输入 (User Message / Data)
            tools: 已启用的插件/工具列表
            temperature: 采样温度
            top_p: 核采样概率
            enable_thinking: 是否开启推理模式 (Reasoning Mode)
            **kwargs: 其他透传给 responses.create 的参数 (如 text 格式设置)
        """
        body = {
            "model": model,
            "instructions": instructions,
            "input": input_text,
            "temperature": temperature,
            "top_p": top_p,
            "extra_body": {"enable_thinking": enable_thinking}
        }
        
        if tools:
            body["tools"] = tools
            
        # 允许透传额外的控制参数 (例如强制 JSON Schema 的 'text')
        body.update(kwargs)
        
        if timeout is not None and hasattr(self.client, "with_options"):
            return self.client.with_options(timeout=timeout).responses.create(**body)
        return self.client.responses.create(**body)
