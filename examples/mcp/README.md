# Grokipedia Ontology MCP Server

MCP (Model Context Protocol) 서버를 통해 Claude와 같은 AI 어시스턴트가 직접 지식 그래프를 검색하고 탐색할 수 있습니다.

## 설치

```bash
pip install grokipedia-ontology[mcp]
```

## 사용법

### CLI로 실행

```bash
# 샘플 데이터로 MCP 서버 시작
grokipedia-ontology mcp-serve examples/sample_ai_ontology.json
```

### Claude Desktop 설정

`claude_desktop_config.json` 파일을 Claude Desktop 설정 디렉토리에 복사:

**macOS:**
```bash
cp claude_desktop_config.json ~/Library/Application\ Support/Claude/
```

**Windows:**
```bash
copy claude_desktop_config.json %APPDATA%\Claude\
```

**Linux:**
```bash
cp claude_desktop_config.json ~/.config/Claude/
```

설정 파일 예시:
```json
{
  "mcpServers": {
    "grokipedia-ontology": {
      "command": "grokipedia-ontology",
      "args": ["mcp-serve", "/absolute/path/to/data.json"],
      "env": {}
    }
  }
}
```

## 사용 가능한 도구 (Tools)

| 도구 | 설명 | 예시 |
|------|------|------|
| `search_concepts` | 키워드로 개념 검색 | "machine learning 관련 개념 찾아줘" |
| `get_concept` | 특정 개념 상세 조회 | "Python 개념에 대해 알려줘" |
| `get_neighbors` | 연결된 개념 조회 | "TensorFlow와 연결된 개념들은?" |
| `find_path` | 두 개념 간 경로 탐색 | "Python에서 Deep Learning까지 어떻게 연결돼?" |
| `get_relations` | 관계 조회 | "is_a 관계인 것들 보여줘" |
| `get_stats` | 통계 조회 | "지식 그래프 통계 알려줘" |
| `add_concept` | 개념 추가 | "GPT-4 개념을 추가해줘" |
| `add_relation` | 관계 추가 | "GPT-4는 LLM의 일종이야" |

## 사용 예시

Claude에게 다음과 같이 질문할 수 있습니다:

```
"이 지식 그래프에서 machine learning 관련 개념들을 찾아줘"

"Python과 Deep Learning 사이의 연결 경로를 알려줘"

"Neural Network 개념과 연결된 모든 기술들을 보여줘"

"새로운 개념 'Transformer'를 technology 타입으로 추가해줘"
```

## 프로그래밍 방식 사용

```python
import asyncio
from grokipedia_ontology.mcp_server import create_mcp_server

async def main():
    server = create_mcp_server(Path("data.json"))
    await server.run()

asyncio.run(main())
```
