# Grokipedia Ontology

Grokipedia를 데이터 소스로 활용하는 지식 그래프 및 온톨로지 프레임워크입니다.

## 개요

이 프로젝트는 [Grokipedia](https://grokipedia.com/)에서 추출한 지식을 OWL/RDF 기반 온톨로지로 구조화하고, 지식 그래프를 구축하여 의미론적 질의 및 추론을 수행할 수 있는 도구를 제공합니다.

### 주요 기능

- **데이터 수집**: Grokipedia 페이지에서 구조화된 데이터 추출
- **온톨로지 관리**: OWL/RDF 표준 기반 온톨로지 생성 및 관리
- **지식 그래프**: NetworkX 기반 그래프 구축 및 분석
- **SPARQL 질의**: 표준 SPARQL 질의 지원
- **추론 엔진**: 관계 추론 및 일관성 검사
- **다양한 포맷 지원**: Turtle, RDF/XML, JSON-LD, GraphML 등

## 설치

```bash
# pip를 통한 설치
pip install grokipedia-ontology

# 개발 환경 설치
pip install -e ".[dev]"

# 시각화 도구 포함 설치
pip install -e ".[visualization]"
```

## 빠른 시작

### Python API 사용

```python
from grokipedia_ontology import (
    GrokipediaFetcher,
    GrokipediaOntology,
    KnowledgeGraph,
    Concept,
    Relation,
)
from grokipedia_ontology.models import ConceptType, RelationType

# 온톨로지 생성
ontology = GrokipediaOntology()

# 개념 추가
ai_concept = Concept(
    name="Artificial_Intelligence",
    label="Artificial Intelligence",
    description="The simulation of human intelligence by machines.",
    concept_type=ConceptType.TECHNOLOGY,
)
ontology.add_concept(ai_concept)

# 관계 추가
relation = Relation(
    subject="Machine_Learning",
    predicate=RelationType.IS_A,
    object="Artificial_Intelligence",
)
ontology.add_relation(relation)

# 온톨로지 저장
ontology.save("my_ontology.ttl", format="turtle")
```

### Grokipedia에서 데이터 수집

```python
import asyncio

async def fetch_articles():
    async with GrokipediaFetcher() as fetcher:
        # 단일 문서 수집
        article = await fetcher.fetch_article("Machine_Learning")

        # 연관 문서 크롤링
        articles = await fetcher.discover_related(
            start_topic="Artificial_Intelligence",
            max_depth=2,
            max_articles=50,
        )

        # 지식 그래프 구축
        graph = KnowledgeGraph()
        for article in articles:
            graph.add_article(article)

        return graph

graph = asyncio.run(fetch_articles())
```

### 지식 그래프 분석

```python
# 경로 탐색
path = graph.find_path("Deep_Learning", "Artificial_Intelligence")
print(f"Path: {' -> '.join(path)}")

# 중심성 분석
centrality = graph.get_centrality(method="pagerank", top_n=10)
for concept, score in centrality.items():
    print(f"{concept}: {score:.4f}")

# 커뮤니티 탐지
communities = graph.detect_communities()
print(f"Found {len(communities)} communities")

# 검색
results = graph.search("learning", limit=5)
for result in results:
    print(f"{result.concept.label}: {result.score:.2f}")
```

### SPARQL 질의

```python
query = """
PREFIX grok: <http://grokipedia.org/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?concept ?label WHERE {
    ?concept a grok:Technology ;
             rdfs:label ?label .
}
LIMIT 10
"""

results = ontology.query(query)
for row in results:
    print(row)
```

## CLI 사용법

```bash
# 단일 문서 수집
grokipedia-ontology fetch "Artificial Intelligence" -o ai.json

# 크롤링 및 지식 그래프 구축
grokipedia-ontology crawl "Machine Learning" -d 2 -n 100 -o ml_graph.ttl

# 온톨로지 통계
grokipedia-ontology stats ml_graph.ttl

# 검색
grokipedia-ontology search ml_graph.ttl "neural network"

# 포맷 변환
grokipedia-ontology convert ml_graph.ttl ml_graph.jsonld -f json-ld
```

## 프로젝트 구조

```
grokipedia-ontology/
├── src/grokipedia_ontology/
│   ├── __init__.py          # 패키지 초기화
│   ├── models.py            # 데이터 모델 (Pydantic)
│   ├── fetcher.py           # Grokipedia 데이터 수집기
│   ├── ontology.py          # OWL/RDF 온톨로지 관리
│   ├── graph.py             # 지식 그래프 (NetworkX)
│   └── cli.py               # CLI 인터페이스
├── ontology/
│   └── grokipedia.ttl       # 기본 온톨로지 스키마
├── examples/
│   └── basic_usage.py       # 사용 예제
├── tests/                   # 테스트 코드
├── pyproject.toml           # 프로젝트 설정
└── README.md
```

## 온톨로지 스키마

### 개념 유형 (ConceptType)

| 유형 | 설명 |
|------|------|
| `entity` | 물리적 또는 추상적 존재 |
| `event` | 시간 내 발생 사건 |
| `process` | 진행 중인 활동 |
| `property` | 속성 또는 특성 |
| `person` | 개인 |
| `organization` | 조직 또는 기관 |
| `location` | 지리적 위치 |
| `technology` | 기술 시스템 또는 도구 |
| `work` | 창작물 또는 지적 저작물 |

### 관계 유형 (RelationType)

| 관계 | 설명 |
|------|------|
| `is_a` | 분류 관계 (하위 유형) |
| `part_of` | 부분-전체 관계 |
| `related_to` | 일반적 연관 |
| `instance_of` | 인스턴스 관계 |
| `caused_by` | 인과 관계 |
| `used_for` | 용도 관계 |
| `located_in` | 공간 관계 |
| `derived_from` | 파생 관계 |
| `equivalent_to` | 의미적 동치 |

## 개발

```bash
# 의존성 설치
pip install -e ".[dev]"

# 테스트 실행
pytest

# 코드 포맷팅
ruff check --fix .
ruff format .

# 타입 검사
mypy src/grokipedia_ontology
```

## 라이선스

MIT License

## 참고 자료

- [Grokipedia](https://grokipedia.com/) - xAI의 AI 생성 백과사전
- [OWL Web Ontology Language](https://www.w3.org/OWL/)
- [RDFLib Documentation](https://rdflib.readthedocs.io/)
- [NetworkX Documentation](https://networkx.org/)

---

**Sources:**
- [Grokipedia - Wikipedia](https://en.wikipedia.org/wiki/Grokipedia)
- [Ontology (information science)](https://grokipedia.com/page/Ontology_(information_science))
- [Web Ontology Language](https://grokipedia.com/page/Web_Ontology_Language)
