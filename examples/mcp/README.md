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

## MCP 기능

### 1. Tools (10개)

| 도구 | 설명 |
|------|------|
| `search_concepts` | 키워드로 개념 검색 |
| `get_concept` | 특정 개념 상세 조회 |
| `get_neighbors` | 연결된 개념 조회 |
| `find_path` | 두 개념 간 경로 탐색 |
| `get_relations` | 관계 조회 |
| `get_stats` | 통계 조회 |
| `add_concept` | 개념 추가 |
| `add_relation` | 관계 추가 |
| `list_concept_types` | 개념 타입 목록 |
| `list_relation_types` | 관계 타입 목록 |

### 2. Resources

지식 그래프 데이터에 직접 접근:

| URI | 설명 |
|-----|------|
| `ontology://stats` | 전체 통계 |
| `ontology://concepts` | 모든 개념 목록 |
| `ontology://relations` | 모든 관계 목록 |
| `ontology://types` | 사용 가능한 타입들 |
| `ontology://concepts/{name}` | 특정 개념 상세 |
| `ontology://neighbors/{name}` | 연결된 개념들 |
| `ontology://search/{query}` | 검색 결과 |

### 3. Prompts (5개)

미리 정의된 프롬프트 템플릿:

| 프롬프트 | 설명 | 인자 |
|---------|------|------|
| `explore_concept` | 개념 탐색 및 설명 | `concept_name` |
| `find_connections` | 두 개념 간 연결 찾기 | `concept_a`, `concept_b` |
| `summarize_domain` | 도메인 요약 | `domain` |
| `compare_concepts` | 개념 비교 | `concepts` (쉼표 구분) |
| `knowledge_qa` | 지식 그래프 기반 Q&A | `question` |

## 사용 예시

Claude에게 다음과 같이 질문할 수 있습니다:

```
"이 지식 그래프에서 machine learning 관련 개념들을 찾아줘"

"Python과 Deep Learning 사이의 연결 경로를 알려줘"

"Neural Network 개념과 연결된 모든 기술들을 보여줘"

"새로운 개념 'Transformer'를 technology 타입으로 추가해줘"

"AI 도메인을 요약해줘" (summarize_domain 프롬프트 사용)

"TensorFlow와 PyTorch를 비교해줘" (compare_concepts 프롬프트 사용)
```

## 프로그래밍 방식 사용

```python
import asyncio
from pathlib import Path
from grokipedia_ontology.mcp_server import create_mcp_server

async def main():
    server = create_mcp_server(Path("data.json"))
    await server.run()

asyncio.run(main())
```
