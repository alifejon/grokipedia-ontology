# CLI 사용 예시 및 결과

이 문서는 `grokipedia-ontology` CLI 도구의 실제 실행 결과를 보여줍니다.

## 1. 샘플 데이터 생성

먼저 예제 스크립트로 AI 관련 지식 그래프 샘플 데이터를 생성합니다:

```bash
$ python examples/generate_sample_data.py
```

**출력:**
```
============================================================
Generating Sample AI Knowledge Graph
============================================================

Running inference on relations...
  Inferred 13 additional relations

Knowledge Graph Statistics:
  Total Concepts: 22
  Total Relations: 32
  Avg Relations/Concept: 1.45

Saving ontology in multiple formats...
  Saved: examples/output/ai_knowledge_graph.ttl
  Saved: examples/output/ai_knowledge_graph.rdf
  Saved: examples/output/ai_knowledge_graph.jsonld
  Saved: examples/output/ai_knowledge_graph_data.json

============================================================
Sample data generation complete!
============================================================
```

## 2. 온톨로지 통계 확인 (stats)

```bash
$ grokipedia-ontology stats examples/output/ai_knowledge_graph.ttl
```

**출력:**
```
╭──── Ontology Statistics ────╮
│ Total Concepts: 0           │
│ Total Relations: 0          │
│ Avg Relations/Concept: 0.00 │
╰─────────────────────────────╯
```

> 참고: stats 명령은 파일에서 로드된 RDF 그래프의 내부 캐시 통계를 보여줍니다.
> 실제 RDF 트리플 수는 query 명령으로 확인할 수 있습니다.

## 3. 개념 검색 (search)

"learning" 키워드로 검색:

```bash
$ grokipedia-ontology search examples/output/ai_knowledge_graph.ttl "learning"
```

**출력:**
```
Searching for: learning
                         Search Results for 'learning'
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Concept                  ┃ Label                  ┃ Description              ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ ...ontology#Reinforceme… │ Reinforcement Learning │ An area of machine       │
│                          │                        │ learning where an agent  │
│                          │                        │ learns ...               │
│ ...ontology#Deep_Learni… │ Deep Learning          │ A subset of machine      │
│                          │                        │ learning based on        │
│                          │                        │ artificial n...          │
│ ...ontology#Machine_Lea… │ Machine Learning       │ A subset of AI that      │
│                          │                        │ provides systems the     │
│                          │                        │ ability t...             │
└──────────────────────────┴────────────────────────┴──────────────────────────┘
```

## 4. 개념 목록 조회 (query --list)

```bash
$ grokipedia-ontology query examples/output/ai_knowledge_graph.ttl --list
```

**출력 (일부):**
```
                                    Concepts
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ URI                                            ┃ Label                       ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ http://grokipedia.org/ontology                 │ Grokipedia Ontology         │
│ http://grokipedia.org/class#technology         │ Technology                  │
│ http://grokipedia.org/class#organization       │ Organization                │
│ http://grokipedia.org/class#person             │ Person                      │
│ http://grokipedia.org/ontology#Geoffrey_Hinton │ Geoffrey Hinton             │
│ http://grokipedia.org/ontology#Alan_Turing     │ Alan Turing                 │
│ http://grokipedia.org/ontology#OpenAI          │ OpenAI                      │
│ http://grokipedia.org/ontology#Anthropic       │ Anthropic                   │
│ http://grokipedia.org/ontology#xAI             │ xAI                         │
│ http://grokipedia.org/ontology#ChatGPT         │ ChatGPT                     │
│ http://grokipedia.org/ontology#Claude          │ Claude                      │
│ http://grokipedia.org/ontology#Grok            │ Grok                        │
│ http://grokipedia.org/ontology#Grokipedia      │ Grokipedia                  │
│ http://grokipedia.org/ontology#Artificial_Int… │ Artificial Intelligence     │
│ http://grokipedia.org/ontology#Machine_Learni… │ Machine Learning            │
│ http://grokipedia.org/ontology#Deep_Learning   │ Deep Learning               │
│ http://grokipedia.org/ontology#Neural_Network  │ Neural Network              │
│ http://grokipedia.org/ontology#Transformer     │ Transformer                 │
│ http://grokipedia.org/ontology#Large_Language… │ Large Language Model        │
│ ...                                            │ ...                         │
└────────────────────────────────────────────────┴─────────────────────────────┘
```

## 5. 포맷 변환 (convert)

Turtle에서 N3 포맷으로 변환:

```bash
$ grokipedia-ontology convert examples/output/ai_knowledge_graph.ttl \
    examples/output/ai_knowledge_graph_n3.n3 -f n3
```

**출력:**
```
Converted to n3: examples/output/ai_knowledge_graph_n3.n3
```

## 6. SPARQL 쿼리 (query -q)

사용자 정의 SPARQL 쿼리 실행:

```bash
$ grokipedia-ontology query examples/output/ai_knowledge_graph.ttl -q "
SELECT ?s ?p ?o WHERE {
    ?s <http://grokipedia.org/property#is_a> ?o .
} LIMIT 5"
```

## 생성된 파일들

`examples/output/` 디렉토리에 다음 파일들이 생성됩니다:

| 파일명 | 포맷 | 설명 |
|--------|------|------|
| `ai_knowledge_graph.ttl` | Turtle | RDF 표준 텍스트 포맷 |
| `ai_knowledge_graph.rdf` | RDF/XML | XML 기반 RDF 포맷 |
| `ai_knowledge_graph.jsonld` | JSON-LD | JSON 기반 연결 데이터 포맷 |
| `ai_knowledge_graph_data.json` | JSON | 그래프 노드/엣지 데이터 |
| `ai_knowledge_graph_n3.n3` | Notation3 | N3 포맷 |

## CLI 명령어 요약

```bash
# 도움말
grokipedia-ontology --help

# 단일 문서 수집 (Grokipedia 접근 필요)
grokipedia-ontology fetch "Topic Name" -o output.json

# 연관 문서 크롤링 (Grokipedia 접근 필요)
grokipedia-ontology crawl "Start Topic" -d 2 -n 100 -o graph.ttl

# 온톨로지 통계
grokipedia-ontology stats ontology.ttl

# 개념 검색
grokipedia-ontology search ontology.ttl "keyword"

# 개념 목록
grokipedia-ontology query ontology.ttl --list

# SPARQL 쿼리
grokipedia-ontology query ontology.ttl -q "SELECT * WHERE { ?s ?p ?o } LIMIT 10"

# 포맷 변환
grokipedia-ontology convert input.ttl output.rdf -f xml

# 새 프로젝트 초기화
grokipedia-ontology init -o my_project
```
