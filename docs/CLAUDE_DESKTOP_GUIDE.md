# Claude Desktop에서 Grokipedia Ontology MCP 서버 활용 가이드

이 가이드는 Claude Desktop에서 Grokipedia Ontology MCP 서버를 설정하고 활용하는 방법을 설명합니다.

## 목차

1. [사전 요구사항](#사전-요구사항)
2. [설치](#설치)
   - [pip으로 설치](#방법-1-pip으로-설치)
   - [uv로 설치 (권장)](#방법-2-uv로-설치-권장)
3. [Claude Desktop 설정](#claude-desktop-설정)
   - [uv 환경 설정](#5-uv-환경-설정)
4. [데이터 준비](#데이터-준비)
5. [사용 방법](#사용-방법)
6. [활용 예시](#활용-예시)
7. [문제 해결](#문제-해결)

---

## 사전 요구사항

- **Python**: 3.10 이상
- **Claude Desktop**: 최신 버전 ([다운로드](https://claude.ai/download))
- **pip**: Python 패키지 관리자

## 설치

### 방법 1: pip으로 설치

```bash
# MCP 의존성과 함께 설치
pip install grokipedia-ontology[mcp]

# 또는 전체 기능 설치
pip install grokipedia-ontology[all]
```

### 방법 2: uv로 설치 (권장)

[uv](https://github.com/astral-sh/uv)는 Rust로 작성된 빠른 Python 패키지 관리자입니다.

#### uv 설치

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Homebrew (macOS)
brew install uv
```

#### uv로 패키지 설치

> **📁 실행 경로**: 프로젝트를 관리할 디렉토리에서 실행합니다.

```bash
# 1. 작업 디렉토리 생성 및 이동
mkdir -p ~/projects/grokipedia
cd ~/projects/grokipedia

# 2. 새 가상환경 생성
uv venv

# 3. 가상환경 활성화
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# 4. MCP 의존성과 함께 설치
uv pip install grokipedia-ontology[mcp]

# 또는 전체 기능 설치
uv pip install grokipedia-ontology[all]
```

**설치 후 디렉토리 구조:**
```
~/projects/grokipedia/
├── .venv/                    # 가상환경 (uv가 생성)
│   └── bin/
│       └── grokipedia-ontology  # 실행 파일
└── data/                     # 데이터 파일 (직접 생성)
    └── knowledge_graph.json
```

#### uv tool로 전역 설치

> **📁 실행 경로**: 어느 디렉토리에서든 실행 가능합니다.

```bash
# uv tool로 전역 설치 (별도 가상환경 없이 사용)
uv tool install grokipedia-ontology[mcp]

# 설치 위치 확인
uv tool dir
# 출력 예: /Users/username/.local/share/uv/tools

# 실행 파일 경로 확인
which grokipedia-ontology
# 출력 예: /Users/username/.local/bin/grokipedia-ontology
```

**참고**: `uv tool`은 `~/.local/bin`에 심볼릭 링크를 생성하므로 PATH에 `~/.local/bin`이 포함되어 있어야 합니다.

### 설치 방법 비교

| 방법 | 실행 경로 | 장점 | 단점 |
|------|----------|------|------|
| `pip install` | 가상환경 내 | 전통적인 방식 | venv 활성화 필요 |
| `uv venv` + `uv pip` | 프로젝트 디렉토리 | 빠른 설치, 격리된 환경 | venv 활성화 필요 |
| `uv tool install` | 어디서든 | 전역 설치, 활성화 불필요 | 버전 관리 어려움 |
| `uv run` | 프로젝트 루트 | 소스 개발용 | 프로젝트 클론 필요 |
| `uvx` | 어디서든 | 설치 없이 실행 | 첫 실행 시 느림 |

**권장 사용 사례:**
- **일반 사용자**: `uv tool install` (가장 간단)
- **프로젝트별 관리**: `uv venv` + `uv pip install`
- **개발/기여자**: `uv run` (소스 수정 가능)
- **테스트/실험**: `uvx` (설치 없이 바로 사용)

### 설치 확인

```bash
# CLI가 정상 작동하는지 확인
grokipedia-ontology --help

# MCP 서버 명령어 확인
grokipedia-ontology mcp-serve --help
```

## Claude Desktop 설정

### 1. 설정 파일 위치 찾기

| 운영체제 | 설정 파일 경로 |
|---------|---------------|
| **macOS** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Windows** | `%APPDATA%\Claude\claude_desktop_config.json` |
| **Linux** | `~/.config/Claude/claude_desktop_config.json` |

### 2. 설정 파일 생성/수정

설정 파일이 없으면 새로 생성하고, 있으면 `mcpServers` 섹션을 추가합니다.

#### macOS/Linux

```bash
# 디렉토리 생성 (없는 경우)
mkdir -p ~/.config/Claude  # Linux
mkdir -p ~/Library/Application\ Support/Claude  # macOS

# 설정 파일 편집
nano ~/.config/Claude/claude_desktop_config.json  # Linux
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json  # macOS
```

#### Windows (PowerShell)

```powershell
# 디렉토리 생성 (없는 경우)
New-Item -ItemType Directory -Force -Path "$env:APPDATA\Claude"

# 설정 파일 편집
notepad "$env:APPDATA\Claude\claude_desktop_config.json"
```

### 3. 설정 파일 내용

```json
{
  "mcpServers": {
    "grokipedia-ontology": {
      "command": "grokipedia-ontology",
      "args": ["mcp-serve", "/absolute/path/to/your/data.json"],
      "env": {}
    }
  }
}
```

#### 중요: 경로 설정

- **절대 경로**를 사용해야 합니다
- `~`는 사용 불가 (전체 경로로 작성)

**예시:**
```json
{
  "mcpServers": {
    "grokipedia-ontology": {
      "command": "grokipedia-ontology",
      "args": ["mcp-serve", "/Users/username/projects/knowledge_graph.json"],
      "env": {}
    }
  }
}
```

### 4. Python 경로 문제 해결 (선택사항)

`grokipedia-ontology` 명령어를 찾지 못하는 경우:

```json
{
  "mcpServers": {
    "grokipedia-ontology": {
      "command": "/usr/local/bin/python3",
      "args": ["-m", "grokipedia_ontology.cli", "mcp-serve", "/path/to/data.json"],
      "env": {
        "PATH": "/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```

또는 가상환경 사용 시:

```json
{
  "mcpServers": {
    "grokipedia-ontology": {
      "command": "/path/to/venv/bin/grokipedia-ontology",
      "args": ["mcp-serve", "/path/to/data.json"],
      "env": {}
    }
  }
}
```

### 5. uv 환경 설정

#### uv venv 사용 시

uv로 생성한 가상환경의 경로를 사용합니다:

```json
{
  "mcpServers": {
    "grokipedia-ontology": {
      "command": "/path/to/project/.venv/bin/grokipedia-ontology",
      "args": ["mcp-serve", "/path/to/data.json"],
      "env": {}
    }
  }
}
```

**운영체제별 경로 예시:**

macOS/Linux:
```json
{
  "mcpServers": {
    "grokipedia-ontology": {
      "command": "/Users/username/projects/grokipedia/.venv/bin/grokipedia-ontology",
      "args": ["mcp-serve", "/Users/username/data/knowledge_graph.json"],
      "env": {}
    }
  }
}
```

Windows:
```json
{
  "mcpServers": {
    "grokipedia-ontology": {
      "command": "C:\\Users\\username\\projects\\grokipedia\\.venv\\Scripts\\grokipedia-ontology.exe",
      "args": ["mcp-serve", "C:\\Users\\username\\data\\knowledge_graph.json"],
      "env": {}
    }
  }
}
```

#### uv tool 사용 시

`uv tool install`로 설치한 경우, uv tool 디렉토리의 경로를 사용합니다:

```bash
# uv tool 설치 경로 확인
uv tool dir
# 출력 예: /Users/username/.local/share/uv/tools
```

macOS/Linux:
```json
{
  "mcpServers": {
    "grokipedia-ontology": {
      "command": "/Users/username/.local/share/uv/tools/grokipedia-ontology/bin/grokipedia-ontology",
      "args": ["mcp-serve", "/path/to/data.json"],
      "env": {}
    }
  }
}
```

Windows:
```json
{
  "mcpServers": {
    "grokipedia-ontology": {
      "command": "C:\\Users\\username\\.local\\share\\uv\\tools\\grokipedia-ontology\\Scripts\\grokipedia-ontology.exe",
      "args": ["mcp-serve", "C:\\path\\to\\data.json"],
      "env": {}
    }
  }
}
```

#### uv run 사용 (프로젝트 디렉토리 기반)

프로젝트 소스코드를 직접 클론한 경우 사용합니다:

```bash
# 프로젝트 클론
git clone https://github.com/grokipedia-ontology/grokipedia-ontology.git
cd grokipedia-ontology

# 의존성 동기화 (pyproject.toml 기반)
uv sync --extra mcp
```

**Claude Desktop 설정:**

```json
{
  "mcpServers": {
    "grokipedia-ontology": {
      "command": "uv",
      "args": ["run", "--directory", "/Users/username/projects/grokipedia-ontology", "grokipedia-ontology", "mcp-serve", "/path/to/data.json"],
      "env": {}
    }
  }
}
```

> **⚠️ 중요**: `--directory` 옵션에는 `pyproject.toml`이 있는 프로젝트 루트 경로를 지정합니다.

이 방식은 프로젝트의 `pyproject.toml`에 정의된 의존성을 자동으로 사용합니다.

#### uvx 사용 (일회성 실행)

> **📁 실행 경로**: 별도의 설치 없이 어디서든 실행 가능합니다. PyPI에서 자동으로 패키지를 다운로드합니다.

```json
{
  "mcpServers": {
    "grokipedia-ontology": {
      "command": "uvx",
      "args": ["--from", "grokipedia-ontology[mcp]", "grokipedia-ontology", "mcp-serve", "/path/to/data.json"],
      "env": {}
    }
  }
}
```

> **💡 팁**: `uvx`는 패키지를 캐시에 저장하므로 처음 실행 시에만 다운로드가 발생합니다.

### 6. Claude Desktop 재시작

설정 변경 후 Claude Desktop을 완전히 종료했다가 다시 시작해야 합니다.

## 데이터 준비

### 샘플 데이터 생성

```bash
# 프로젝트 디렉토리로 이동
cd /path/to/grokipedia-ontology

# 샘플 데이터 생성
python examples/generate_sample_data.py

# 생성된 파일 확인
ls examples/sample_ai_ontology.json
```

### 데이터 형식

JSON 형식:
```json
{
  "concepts": [
    {
      "name": "Machine_Learning",
      "label": "Machine Learning",
      "description": "A subset of AI that enables systems to learn from data",
      "concept_type": "technology",
      "categories": ["AI", "Computer Science"],
      "aliases": ["ML"]
    }
  ],
  "relations": [
    {
      "subject": "Machine_Learning",
      "predicate": "is_a",
      "object": "Artificial_Intelligence",
      "confidence": 1.0
    }
  ]
}
```

## 사용 방법

Claude Desktop을 열면 MCP 서버가 자동으로 연결됩니다. 연결되면 다음을 사용할 수 있습니다:

### 1. Tools (도구)

Claude에게 직접 요청:

```
"지식 그래프에서 machine learning을 검색해줘"
→ search_concepts 도구 자동 호출

"Python 개념에 대해 자세히 알려줘"
→ get_concept 도구 자동 호출

"Neural Network와 연결된 개념들을 보여줘"
→ get_neighbors 도구 자동 호출
```

### 2. Resources (리소스)

Claude가 지식 그래프 데이터에 직접 접근:

```
"지식 그래프의 전체 통계를 보여줘"
→ ontology://stats 리소스 읽기

"모든 개념 목록을 보여줘"
→ ontology://concepts 리소스 읽기
```

### 3. Prompts (프롬프트)

미리 정의된 분석 템플릿 사용:

```
"explore_concept 프롬프트로 Deep_Learning을 분석해줘"

"find_connections 프롬프트로 Python과 TensorFlow의 관계를 찾아줘"

"summarize_domain 프롬프트로 AI 분야를 요약해줘"
```

## 활용 예시

### 예시 1: 개념 탐색

**사용자:** "이 지식 그래프에서 딥러닝과 관련된 모든 기술들을 찾아서 설명해줘"

**Claude 응답:**
- `search_concepts` 도구로 "deep learning" 검색
- 관련 개념들의 상세 정보 조회
- 관계 분석 및 설명 제공

### 예시 2: 경로 탐색

**사용자:** "Python에서 자연어 처리까지 어떻게 연결되는지 알려줘"

**Claude 응답:**
- `find_path` 도구로 경로 탐색
- 중간 개념들과 관계 설명
- 연결 구조 시각화 설명

### 예시 3: 지식 추가

**사용자:** "GPT-4라는 새 개념을 추가해줘. Large Language Model의 일종이야."

**Claude 응답:**
- `add_concept` 도구로 GPT-4 개념 생성
- `add_relation` 도구로 LLM과의 관계 설정
- 추가된 내용 확인

### 예시 4: 도메인 분석

**사용자:** "AI 관련 개념들을 전체적으로 요약해줘"

**Claude 응답:**
- `summarize_domain` 프롬프트 활용
- 주요 개념, 관계, 계층 구조 분석
- 인사이트 및 추가 탐색 제안

## 문제 해결

### 1. MCP 서버가 연결되지 않음

**증상:** Claude Desktop에서 도구를 사용할 수 없음

**해결:**
1. 설정 파일 경로 확인
2. JSON 문법 검증 (쉼표, 따옴표 등)
3. 데이터 파일 경로가 절대 경로인지 확인
4. Claude Desktop 완전 재시작

```bash
# 설정 파일 JSON 검증
python -c "import json; json.load(open('설정파일경로'))"
```

### 2. 명령어를 찾을 수 없음

**증상:** `grokipedia-ontology: command not found`

**해결:**
```bash
# 설치 확인
pip show grokipedia-ontology

# 경로 확인
which grokipedia-ontology

# 경로가 나오지 않으면 pip 재설치
pip install --force-reinstall grokipedia-ontology[mcp]
```

### 3. 데이터 파일 로드 실패

**증상:** "No data loaded" 오류

**해결:**
1. 데이터 파일 존재 확인
2. JSON 형식 검증
3. 파일 권한 확인

```bash
# 파일 존재 확인
ls -la /path/to/data.json

# JSON 검증
python -c "import json; json.load(open('/path/to/data.json'))"
```

### 4. MCP 의존성 누락

**증상:** `ImportError: MCP is required`

**해결:**
```bash
pip install grokipedia-ontology[mcp]
```

### 5. 로그 확인

MCP 서버 로그를 직접 확인:

```bash
# 터미널에서 직접 실행하여 오류 확인
grokipedia-ontology mcp-serve /path/to/data.json
```

### 6. uv 환경 문제 해결

#### uv 명령어를 찾을 수 없음

**증상:** `uv: command not found`

**해결:**
```bash
# uv 설치 확인
which uv

# PATH에 추가 (Linux/macOS - .bashrc 또는 .zshrc에 추가)
export PATH="$HOME/.local/bin:$PATH"

# 또는 uv 재설치
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### uv tool 설치 경로 찾기

**증상:** uv tool로 설치했지만 실행 파일 경로를 모름

**해결:**
```bash
# uv tool 디렉토리 확인
uv tool dir

# 설치된 도구 목록 확인
uv tool list

# 특정 도구의 실행 파일 경로 확인
ls $(uv tool dir)/grokipedia-ontology/bin/
```

#### uv venv 활성화 문제

**증상:** 가상환경이 활성화되지 않음

**해결:**
```bash
# 가상환경 재생성
rm -rf .venv
uv venv

# 활성화 (Linux/macOS)
source .venv/bin/activate

# 활성화 (Windows PowerShell)
.venv\Scripts\Activate.ps1

# 활성화 (Windows CMD)
.venv\Scripts\activate.bat
```

#### uvx 실행 오류

**증상:** `uvx` 명령이 패키지를 찾지 못함

**해결:**
```bash
# 캐시 정리
uv cache clean

# 패키지 이름과 extras 확인
uvx --from "grokipedia-ontology[mcp]" grokipedia-ontology --help

# 특정 버전 지정
uvx --from "grokipedia-ontology[mcp]==1.0.0" grokipedia-ontology mcp-serve /path/to/data.json
```

#### Claude Desktop에서 uv 경로 인식 문제

**증상:** Claude Desktop이 uv나 uvx 명령을 찾지 못함

**해결:**
설정 파일에 PATH 환경 변수를 명시적으로 추가:

```json
{
  "mcpServers": {
    "grokipedia-ontology": {
      "command": "uvx",
      "args": ["--from", "grokipedia-ontology[mcp]", "grokipedia-ontology", "mcp-serve", "/path/to/data.json"],
      "env": {
        "PATH": "/Users/username/.local/bin:/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```

또는 uv의 절대 경로를 사용:

```json
{
  "mcpServers": {
    "grokipedia-ontology": {
      "command": "/Users/username/.local/bin/uvx",
      "args": ["--from", "grokipedia-ontology[mcp]", "grokipedia-ontology", "mcp-serve", "/path/to/data.json"],
      "env": {}
    }
  }
}
```

## 고급 설정

### 여러 지식 그래프 사용

```json
{
  "mcpServers": {
    "ai-ontology": {
      "command": "grokipedia-ontology",
      "args": ["mcp-serve", "/path/to/ai_knowledge.json"]
    },
    "science-ontology": {
      "command": "grokipedia-ontology",
      "args": ["mcp-serve", "/path/to/science_knowledge.json"]
    }
  }
}
```

### 환경 변수 설정

```json
{
  "mcpServers": {
    "grokipedia-ontology": {
      "command": "grokipedia-ontology",
      "args": ["mcp-serve", "/path/to/data.json"],
      "env": {
        "PYTHONPATH": "/custom/python/path",
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

## 참고 자료

- [MCP 공식 문서](https://modelcontextprotocol.io/)
- [Claude Desktop 다운로드](https://claude.ai/download)
- [Grokipedia Ontology GitHub](https://github.com/grokipedia-ontology/grokipedia-ontology)
- [uv 공식 문서](https://docs.astral.sh/uv/)
- [uv GitHub](https://github.com/astral-sh/uv)
