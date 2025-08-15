#!/usr/bin/env python3
"""
Supabase MCP Server (REST API 기반)
Supabase REST API를 통해 작업일보 데이터를 관리하는 MCP 서버
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional
import httpx

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import (
    INVALID_PARAMS,
    INTERNAL_ERROR,
    Resource,
    Tool,
    TextContent,
    CallToolRequest,
    CallToolResult,
    ListResourcesRequest,
    ListResourcesResult,
    ListToolsRequest,
    ListToolsResult,
    ReadResourceRequest,
    ReadResourceResult,
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase 연결 정보
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

class SupabaseMCPServer:
    def __init__(self):
        self.server = Server("supabase-server")
        self.client = None
        self._setup_handlers()
    
    def _get_headers(self) -> Dict[str, str]:
        """API 요청용 헤더를 반환합니다."""
        return {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            "Content-Type": "application/json"
        }
    
    def _setup_handlers(self):
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """사용 가능한 도구 목록을 반환합니다."""
            return [
                Tool(
                    name="query_daily_reports",
                    description="일일작업보고 데이터를 조회합니다",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": "조회할 날짜 (YYYY-MM-DD 형식)"
                            },
                            "table": {
                                "type": "string",
                                "enum": ["weather_reports", "construction_status", "work_content", "personnel_data", "equipment_data"],
                                "description": "조회할 테이블명"
                            }
                        },
                        "required": ["date", "table"]
                    }
                ),
                Tool(
                    name="query_blast_data",
                    description="발파 데이터를 조회합니다",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": "조회할 날짜 (YYYY-MM-DD 형식)"
                            }
                        },
                        "required": ["date"]
                    }
                ),
                Tool(
                    name="query_instrument_data",
                    description="계측기 데이터를 조회합니다",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": "조회할 날짜 (YYYY-MM-DD 형식)"
                            }
                        },
                        "required": ["date"]
                    }
                ),
                Tool(
                    name="get_prompts",
                    description="저장된 프롬프트 목록을 조회합니다",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="get_prompt_content",
                    description="특정 프롬프트의 내용을 조회합니다",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "조회할 프롬프트 이름"
                            }
                        },
                        "required": ["name"]
                    }
                ),
                Tool(
                    name="search_data",
                    description="특정 날짜 범위의 데이터를 검색합니다",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table": {
                                "type": "string",
                                "enum": ["weather_reports", "construction_status", "work_content", "personnel_data", "equipment_data", "blast_data", "instrument_data"],
                                "description": "검색할 테이블명"
                            },
                            "start_date": {
                                "type": "string",
                                "description": "시작 날짜 (YYYY-MM-DD 형식)"
                            },
                            "end_date": {
                                "type": "string",
                                "description": "종료 날짜 (YYYY-MM-DD 형식)"
                            }
                        },
                        "required": ["table", "start_date", "end_date"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """도구 호출을 처리합니다."""
            try:
                if name == "query_daily_reports":
                    return await self._query_daily_reports(arguments)
                elif name == "query_blast_data":
                    return await self._query_blast_data(arguments)
                elif name == "query_instrument_data":
                    return await self._query_instrument_data(arguments)
                elif name == "get_prompts":
                    return await self._get_prompts()
                elif name == "get_prompt_content":
                    return await self._get_prompt_content(arguments)
                elif name == "search_data":
                    return await self._search_data(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.error(f"Tool {name} failed: {e}")
                return [TextContent(type="text", text=f"오류 발생: {str(e)}")]
    
    async def _make_request(self, method: str, endpoint: str, params: Dict = None) -> Dict:
        """Supabase API 요청을 실행합니다."""
        if not self.client:
            self.client = httpx.AsyncClient()
        
        url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
        headers = self._get_headers()
        
        try:
            if method.upper() == "GET":
                response = await self.client.get(url, headers=headers, params=params)
            else:
                response = await self.client.request(method, url, headers=headers, params=params)
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API request failed: {e}")
            raise
    
    async def _query_daily_reports(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """일일작업보고 데이터를 조회합니다."""
        date = arguments["date"]
        table = arguments["table"]
        
        params = {"date": f"eq.{date}", "order": "created_at.desc"}
        results = await self._make_request("GET", table, params)
        
        if results:
            formatted_results = json.dumps(results, ensure_ascii=False, indent=2, default=str)
            return [TextContent(type="text", text=f"{table} 데이터 ({date}):\n{formatted_results}")]
        else:
            return [TextContent(type="text", text=f"{date}의 {table} 데이터가 없습니다.")]
    
    async def _query_blast_data(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """발파 데이터를 조회합니다."""
        date = arguments["date"]
        
        params = {"date": f"eq.{date}", "order": "created_at.desc"}
        results = await self._make_request("GET", "blast_data", params)
        
        if results:
            formatted_results = json.dumps(results, ensure_ascii=False, indent=2, default=str)
            return [TextContent(type="text", text=f"발파 데이터 ({date}):\n{formatted_results}")]
        else:
            return [TextContent(type="text", text=f"{date}의 발파 데이터가 없습니다.")]
    
    async def _query_instrument_data(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """계측기 데이터를 조회합니다."""
        date = arguments["date"]
        
        params = {"date": f"eq.{date}", "order": "created_at.desc"}
        results = await self._make_request("GET", "instrument_data", params)
        
        if results:
            formatted_results = json.dumps(results, ensure_ascii=False, indent=2, default=str)
            return [TextContent(type="text", text=f"계측기 데이터 ({date}):\n{formatted_results}")]
        else:
            return [TextContent(type="text", text=f"{date}의 계측기 데이터가 없습니다.")]
    
    async def _get_prompts(self) -> List[TextContent]:
        """저장된 프롬프트 목록을 조회합니다."""
        params = {"select": "name,description,created_at", "order": "created_at.desc"}
        results = await self._make_request("GET", "prompts", params)
        
        if results:
            formatted_results = json.dumps(results, ensure_ascii=False, indent=2, default=str)
            return [TextContent(type="text", text=f"저장된 프롬프트 목록:\n{formatted_results}")]
        else:
            return [TextContent(type="text", text="저장된 프롬프트가 없습니다.")]
    
    async def _get_prompt_content(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """특정 프롬프트의 내용을 조회합니다."""
        name = arguments["name"]
        
        params = {"name": f"eq.{name}", "select": "name,content,description"}
        results = await self._make_request("GET", "prompts", params)
        
        if results:
            prompt = results[0]
            content = f"프롬프트명: {prompt['name']}\n"
            content += f"설명: {prompt['description']}\n\n"
            content += f"내용:\n{prompt['content']}"
            return [TextContent(type="text", text=content)]
        else:
            return [TextContent(type="text", text=f"'{name}' 프롬프트를 찾을 수 없습니다.")]
    
    async def _search_data(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """특정 날짜 범위의 데이터를 검색합니다."""
        table = arguments["table"]
        start_date = arguments["start_date"]
        end_date = arguments["end_date"]
        
        params = {
            "date": f"gte.{start_date}",
            "date": f"lte.{end_date}",
            "order": "date.desc"
        }
        results = await self._make_request("GET", table, params)
        
        if results:
            formatted_results = json.dumps(results, ensure_ascii=False, indent=2, default=str)
            return [TextContent(type="text", text=f"{table} 데이터 ({start_date} ~ {end_date}):\n총 {len(results)}건\n\n{formatted_results}")]
        else:
            return [TextContent(type="text", text=f"{start_date} ~ {end_date} 기간의 {table} 데이터가 없습니다.")]
    
    async def run(self):
        """서버를 시작합니다."""
        # 환경변수 확인
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise ValueError("SUPABASE_URL과 SUPABASE_ANON_KEY 환경변수가 필요합니다.")
        
        # API 연결 테스트
        try:
            await self._make_request("GET", "prompts", {"limit": "1"})
            logger.info("Supabase API 연결 성공")
        except Exception as e:
            logger.error(f"Supabase API 연결 실패: {e}")
            raise
        
        # 서버 실행
        async with self.server.stdio() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="supabase-server",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )

async def main():
    """메인 함수"""
    server = SupabaseMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main()) 