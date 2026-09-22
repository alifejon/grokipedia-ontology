# 프로젝트 방향

기준일: 2026-09-22. 공개 보도와 `grokipedia.com` JSON API를 같은 날 대조한 결과다.

## 한 줄

이 저장소는 Grokipedia 전체를 따라가는 미러가 아니다. JSON API로 받은 문서를 출처가 남는 OWL/RDF 온톨로지와 지식 그래프로 깎는 도구다.

## Grokipedia 현황

제품 버전은 공개적으로 v0.2(2025-11-21)에 머물러 있다. v0.3는 확인되지 않았다. 2026-09-22 04:00 UTC 기준 라이브 API는 아래와 같다.

| 신호 | 관측 |
| --- | --- |
| `GET /api/stats` | `totalPages` 6,092,140. `indexSizeBytes` 194,699,625,215 (약 181GB). `statsTimestamp` 2026-09-21T20:21:02Z. 사이트 합산 `totalViews`는 `"0"`이라 지표로 쓰지 않는다. |
| `GET /api/page-preview?slug=&includeContent=` | 문서 본문. 200. |
| `GET /api/page` | 404. 예전 클라이언트 경로. |
| `GET /api/full-text-search`, `/api/typeahead` | 200. 검색과 슬러그 해석에 쓴다. |
| `GET /api/list-pages` | 200. `lastModified` 내림차순으로 보인다. `totalCount`는 10000에서 잘리고, `offset=10000`은 빈 목록이다. 전량 색인이 아니다. |
| `GET /api/list-edit-requests` | 502. |
| `https://grokipedia.com/live` | “No live edits available right now.” |

문서 스키마(`page` 객체): `slug`, `title`, `content`(마크다운), `description`, `citations[]`, `images[]`, `stats`, `metadata`.

`metadata`에서 수집에 필요한 필드: `lastModified`(unix 초), `contentLength`, `language`, `categories`, `lastEditor`, `creationSource`, `isRedirect`, `redirectTarget`, `isWithheld`, `visibility`, `version`. 여기서 `version: "1.0"`은 문서 스키마 값이지 제품 버전 v0.2와 같은 것이 아니다. 샘플에서 `lastEditor`는 모두 `system`이었다. `creationSource`는 1이 대부분이고 3이 드물게 보였다. 값의 공식 의미는 공개되어 있지 않으므로 숫자 그대로 보존한다.

### 갱신은 층이 다르다

2026년 8월 Lawfare·The Verge 보도는 2026-04-24 이후 편집 승인/거절이 멈췄다고 했다. 2026-09-22에 유명 문서를 다시 보니 그 층은 대체로 그대로다.

| 문서 | `lastModified` | 비고 |
| --- | --- | --- |
| Semantic Web, OWL | 2026-01-14 | 초기 생성 이후 정체 |
| Artificial Intelligence (대문자 슬러그) | 2026-03-14 | 본문은 `#REDIRECT`로 시작하는데 `isRedirect`는 false. 프랑스어 절이 섞여 있다. |
| Ontology | 2026-03-30 | 카테고리 빈 배열. 인용 배열은 있다. |
| Machine learning, SpaceX, ChatGPT, China, OpenAI, Donald Trump | 2026-04-10–04-25 | 헤드 문서의 마지막 무더기 |
| Grokipedia 자기 문서 | 2026-04-25 | 본문 2,861자. “2026년 초 600만”에서 멈춘 짧은 글 |
| Elon Musk | 2026-08-26 | 헤드 문서 중 확인된 예외. 2026년 사건(xAI와 SpaceX 통합)이 본문에 있다. 인용 832개, 이미지 39개 |
| `list-pages` 최근 200건 | 2026-04-25–2026-09-22 | 181건이 2026-09. 미국 연방법원 판사 전기처럼 긴 꼬리가 많다. 본문 길이 중앙값은 약 3–4만 자 |

정리하면, 편집 큐와 라이브 피드로 대표되는 헤드 갱신은 4월 말에 거의 멈췄고, 시스템 작성 긴 꼬리는 9월에도 쌓인다. 코퍼스를 하나의 시계로 보면 안 된다.

본문 형식도 HTML 백과 관례와 다르다.

- 내부 링크는 마크다운 `[label](/page/Slug)` 이다.
- 인용은 `[](https://...)` 이고, 별도 `citations` 배열과 항상 일치하지 않는다. 판사 문서 `william_dimitrouleas`는 인라인 인용이 있으나 `citations`는 빈 배열이었다.
- 인포박스는 HTML `<table class="infobox">`가 아니라 본문 주석이다. Elon Musk 문서는 `<!--Infobox Start [Entrepreneurs]-->` 다음에 `| name = ...` 줄이 온다.
- 카테고리는 유형 분류가 아니라 별칭 나열인 경우가 많다. Artificial intelligence의 정식 슬러그는 카테고리가 `AI`, `A.I.` 두 개뿐이고, 대문자 리다이렉트 슬러그에 별칭이 몰려 있다.
- `metadata.isRedirect`만으로 리다이렉트를 거를 수 없다. 본문 첫 줄을 본다.

## 이 저장소와의 간격

`GrokipediaFetcher`는 `https://grokipedia.com/page/{slug}` HTML을 BeautifulSoup으로 읽는다. 페이지는 SSR이라 `<article>`과 `<h1>`은 있으나, 수집기가 지식으로 삼는 구조는 JSON에 있다.

지금 파서가 놓치는 것:

- `lastModified`, `language`, `creationSource`
- 구조화 인용과 인포박스 주석
- 마크다운 링크 전량 (Ontology HTML에서는 `/page/` 링크가 10개 수준으로만 보였다)
- 본문 리다이렉트와 슬러그 대소문자 (`Artificial_Intelligence`와 `Artificial_intelligence`는 다른 문서다)

카테고리로 `ConceptType`을 고르는 경로도 기대와 다르다. 많은 문서의 `categories`가 비어 있거나 별칭이다.

MCP의 “실시간 조회”는 유지한다. 다만 조회 결과에 수집 시각과 `lastModified`가 있어야 한다. 라이브 피드가 비어 있다는 사실과, 문서가 방금 수정됐다는 사실은 별개다.

## 결정

1. **수집의 기준 경로는 `/api/page-preview`다.** 검색은 `/api/full-text-search`, 슬러그 후보는 `/api/typeahead`, 최근 창은 `/api/list-pages`, 코퍼스 크기는 `/api/stats`다. HTML 스크레이핑은 제거 대상이다.
2. **모든 개념은 출처 시각을 가진다.** 저장 필드: 소스 URL, 슬러그, `lastModified`, 수집 시각, `language`, `creationSource`, `contentLength`. 이후 추론은 이 출처를 지우지 않는다.
3. **범위는 도메인 슬라이스다.** 시작 주제, 깊이, 문서 수 상한은 지금 CLI와 같다. 600만 페이지와 181GB 색인을 복제하지 않는다. `list-pages`는 최근 변경 창으로만 쓴다.
4. **그래프의 1단계는 문서가 스스로 말하는 관계만 담는다.** 내부 링크는 `see_also`, 인포박스 줄은 속성, 리다이렉트는 `equivalent_to`로 해석한다. `is_a`, `part_of`, `caused_by` 같은 유형 관계는 그 다음의 별도 추출기다. 링크를 분류 관계로 올리지 않는다.
5. **정규화는 수집 직후에 한다.** 본문이 `#REDIRECT`이면 대상 슬러그를 따라가고 원 슬러그를 별칭으로 남긴다. `language`가 요청 언어와 다르거나 본문 언어가 섞이면 슬라이스에서 제외할 수 있어야 한다. 슬러그는 대소문자를 보존한다.
6. **편집 큐, 승인/거절, 라이브 에딧 피드는 기능으로 만들지 않는다.** `list-edit-requests`는 502이고 `/live`는 비어 있다. 변경 감지는 `metadata.lastModified`다.
7. **제품 버전을 기다리지 않는다.** v0.2 JSON으로 온톨로지를 만들고, 엔드포인트가 바뀌면 클라이언트만 고친다.

## 구현 순서

1. API 클라이언트. `Article`에 인용, `last_modified`, `language`, `creation_source`, 리다이렉트 대상, 원문 마크다운을 둔다.
2. 마크다운 파서. 내부 링크, 인라인 인용, `citations`와 URL 기준 병합, `<!--Infobox Start-->` 블록, `#REDIRECT`.
3. 고정 샘플 테스트. `Ontology`, `Artificial_intelligence`, `Artificial_Intelligence`, `Elon_Musk`, `list-pages` 최신 1건. 네트워크 없이 돌리려면 응답 JSON을 픽스처로 둔다.
4. 기존 `discover_related`와 MCP 실시간 조회를 이 클라이언트로 옮긴다. 응답에 `lastModified`를 포함한다.
5. 그 다음에만 유형 관계 추출. 추출 규칙이나 모델이 만든 관계는 `confidence`와 출처 문장을 가진다. 링크 그래프와 같은 확신도 1.0으로 저장하지 않는다.

## 성공 기준

도메인 슬라이스 하나가 Turtle로 저장되고, 각 개념에서 Grokipedia 슬러그와 `lastModified`로 돌아갈 수 있으며, 리다이렉트 슬러그가 본 문서와 `equivalent_to`로 연결되고, SPARQL로 그 출처를 물을 수 있으면 이 방향의 첫 단계가 끝난 것이다.
