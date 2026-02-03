<div align="center">

# ArchiveBot

**✨ Version 1.0 | 공식 릴리스**

**🌍 다른 언어로 읽기 / Read this in other languages**

[English](README.en.md) | [简体中文](README.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md)

---

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)

</div>

Telegram Bot 기반 개인 콘텐츠 아카이빙 시스템 | Personal Content Archiving System for Telegram

## 📖 프로젝트 소개

ArchiveBot은 Telegram에서 다양한 콘텐츠(파일, 이미지, 동영상, 텍스트, 링크 등)를 지능적으로 분류하고 아카이빙하여 개인 지식 베이스와 콘텐츠 수집 시스템을 구축할 수 있도록 도와주는 오픈소스 Telegram Bot입니다.

**핵심 포지셔닝**: 개인 인스턴스 도구, 각자가 자신의 Bot을 배포하고 데이터는 완전히 비공개입니다.

## ✨ 핵심 기능

- 📦 **스마트 아카이빙**: 10가지 이상의 콘텐츠 유형을 자동으로 식별하고 분류 저장
- 🏷️ **스마트 태그**: 자동 태그 생성, 수동 태그(#tag) + AI 스마트 태그 지원
- 🔍 **전문 검색**: FTS5 전문 검색 엔진, 페이지네이션 표시(10개/페이지)
- ❤️ **즐겨찾기**: 원클릭으로 중요 콘텐츠 표시, 빠른 필터링
- 📝 **노트 시스템**: 독립 노트 및 연결 노트 지원, 아이디어와 소감 기록
- ↗️ **빠른 전달**: 원클릭으로 아카이빙된 콘텐츠를 채널이나 다른 대화로 전달
- 🗑️ **휴지통**: 실수로 삭제한 콘텐츠 복구 가능, 30일 후 자동 정리
- 💾 **데이터 내보내기**: Markdown/JSON 형식으로 내보내기 지원
- 🔄 **자동 백업**: 정기적으로 데이터베이스 자동 백업, 데이터 안전 보장
- 🤖 **AI 스마트 강화**: Grok-4 지능 분석(요약/핵심 포인트/분류/태그)
- 💬 **AI 스마트 대화**: 자연어 상호작용, 지능적 의도 인식 및 리소스 파일 직접 반환
- 🌏 **다국어 지원**: 6개 언어 지원(영어/간체 중국어/번체 중국어/일본어/한국어/스페인어)
- 🔗 **스마트 링크 추출**: 웹 페이지 제목, 설명, 저자, 주요 정보 등의 메타데이터를 자동으로 추출하여 후속 검색 및 관리를 용이하게 함
- 💾 **간소화된 저장**: 로컬 저장 작은 데이터 → 채널 저장 큰 파일 → 초대형 파일 참조만(3단계 전략)
- 🔒 **개인정보 보호**: 데이터 완전 비공개, 단일 사용자 모드
- 🛡️ **안전하고 신뢰할 수 있음**: SQL 인젝션 방어, 민감 정보 필터링, 스레드 안전
- ⚡ **고성능**: WAL 모드, 인덱스 최적화, 동시 지원

## 🎯 적용 시나리오

- 📝 중요한 메시지와 대화 저장
- 🖼️ 이미지와 전자책 수집
- 📄 문서와 자료 아카이빙
- 🔗 유용한 링크 수집
- 🎬 동영상과 오디오 저장
- 📚 개인 지식 베이스 구축

## 🚀 빠른 시작

### 방법 1: Docker 배포(권장)

**가장 간단한 배포 방법, Python 환경 설정 불필요**

#### 사전 요구사항

- [Docker](https://www.docker.com/get-started) 및 Docker Compose 설치
- Telegram 계정
- Bot Token([@BotFather](https://t.me/BotFather)에서 획득)

#### 배포 단계

```bash
# 1. 프로젝트 복제
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot

# 2. Bot 설정
cp config/config.template.yaml config/config.yaml
nano config/config.yaml  # bot_token, owner_id, channel_id 입력

# 3. 설정 검증(선택 사항이지만 권장)
python verify_docker.py

# 4. 시작(원클릭 배포)
docker-compose up -d --build

# 5. 로그 확인
docker-compose logs -f
```

**완료!** Telegram에서 Bot을 찾아 `/start`를 보내 사용을 시작하세요.

#### 자주 사용하는 명령어

```bash
docker-compose restart          # 재시작
docker-compose logs -f          # 로그 보기
docker-compose down             # 중지
git pull && docker-compose up -d --build  # 최신 버전으로 업데이트
```

#### 설정 방법

**방법 1: 설정 파일(권장)**
- `config/config.yaml` 편집
- 모든 설정을 파일에 작성

**방법 2: 환경 변수(CI/CD에 적합)**
- `docker-compose.yml`의 environment 부분 편집
- 우선순위: 환경 변수 > 설정 파일

---

### 방법 2: 전통적 배포

#### 사전 요구사항

- Python 3.9+
- Telegram 계정
- Bot Token([@BotFather](https://t.me/BotFather)에서 획득)

#### 설치 단계

1. **프로젝트 복제**

```bash
git clone https://github.com/tealun/ArchiveBot.git
cd ArchiveBot
```

2. **종속성 설치**

```bash
pip install -r requirements.txt
```

3. **Bot 설정**

```bash
# 설정 템플릿 복사
cp config/config.template.yaml config/config.yaml

# 설정 파일 편집
nano config/config.yaml
```

**필수 설정 항목**:

- `bot_token`: [@BotFather](https://t.me/BotFather)에서 획득
- `owner_id`: 당신의 Telegram User ID([@userinfobot](https://t.me/userinfobot)에서 획득)
- `storage.telegram.channels.default`: 기본 비공개 채널 ID(파일 저장용, 다중 채널 분류 저장 지원)

4. **Bot 시작**

```bash
python main.py
```

5. **사용 시작**

Telegram에서 당신의 Bot을 찾아 `/start`를 보내 사용을 시작하세요!

📚 **상세 가이드**: [빠른 시작 문서](docs/QUICKSTART.md) | [배포 가이드](docs/DEPLOYMENT.md)

## 📦 저장 전략

ArchiveBot은 간소화된 3단계 저장 전략을 채택하여 Telegram의 무료 저장 공간을 최대한 활용합니다:

| 콘텐츠 유형 | 크기 범위 | 저장 방식 | 설명 |
| --------- | --------- | --------- | ------ |
| 텍스트/링크 | - | SQLite 데이터베이스 | 직접 저장, 전문 검색 지원 |
| 미디어 파일 | 0-2GB | Telegram 비공개 채널 | 영구적이고 신뢰할 수 있음, file_id 전달 |
| 초대형 파일 | >2GB | 참조 정보만 저장 | 공간 차지 없음, 원본 메시지에 의존 |

**핵심 장점**:

- ✅ 다운로드/업로드 불필요, file_id로 직접 전달
- ✅ 채널 메시지 file_id 영구 유효
- ✅ 완전한 2GB 제한 지원
- ✅ 간단하고 신뢰할 수 있음, 시간 초과 위험 없음

## 🎮 사용 방법

### 명령어 목록

| 명령어 | 단축 | 설명 |
| ------ | ------ | ------ |
| `/start` | - | Bot 초기화, 환영 메시지 표시 |
| `/help` | - | 자세한 도움말 정보 보기 |
| `/search <키워드>` | `/s` | 아카이빙된 콘텐츠 검색 |
| `/note` | `/n` | 노트 추가 |
| `/notes` | - | 모든 노트 목록 보기 |
| `/tags` | `/t` | 모든 태그 및 통계 보기 |
| `/stats` | `/st` | 아카이빙 통계 정보 보기 |
| `/setting` | `/set` | 시스템 설정 |
| `/review` | - | 활동 회고 및 통계(주/월/년) |
| `/rand` | `/r` | 랜덤 기록 아카이브 보기 |
| `/trash` | - | 휴지통 콘텐츠 보기 |
| `/export` | - | 아카이빙 데이터 내보내기 |
| `/backup` | - | 데이터베이스 백업 생성 |
| `/ai` | - | AI 기능 상태 보기 |
| `/language` | `/la` | 인터페이스 언어 전환 |
| `/restart` | - | 시스템 재시작 |
| `/cancel` | - | 현재 작업 취소 |

### 콘텐츠 아카이빙

**어떤 콘텐츠든 바로 보내면 아카이빙됩니다!**

```text
지원되는 콘텐츠 유형:
📝 텍스트 메시지
🔗 링크
🖼️ 이미지
🎬 동영상
📄 문서
🎵 오디오
🎤 음성
🎭 스티커
🎞️ 애니메이션
```

**태그 추가**:

```text
메시지를 보낼 때 #태그를 추가하세요:

테스트 메시지입니다 #테스트 #중요
https://github.com #기술 #오픈소스
```

### 콘텐츠 검색

```bash
# 키워드 검색
/search python

# 태그 검색
/search #기술

# 결합 검색
/search #기술 python
```

## 🛠️ 기술 아키텍처

### 기술 스택

| 카테고리 | 기술 |
| ------ | ------ |
| 언어 | Python 3.14.2 |
| 프레임워크 | python-telegram-bot 21.x |
| 데이터베이스 | SQLite (WAL모드, FTS5, AI 필드 인덱스) |
| AI | httpx (Grok-4 via xAI) |
| 설정 | PyYAML |

### 아키텍처 디자인

```text
ArchiveBot/
├── main.py                      # 진입 파일
├── src/
│   ├── bot/                     # Bot 레이어
│   │   ├── commands.py          # 명령 처리
│   │   ├── handlers.py          # 메시지 처리
│   │   ├── callbacks.py         # 콜백 처리
│   │   ├── message_aggregator.py # 메시지 애그리게이터
│   │   └── unknown_command.py   # 알 수 없는 명령 처리
│   ├── core/                    # 핵심 비즈니스
│   │   ├── analyzer.py          # 콘텐츠 분석
│   │   ├── tag_manager.py       # 태그 관리
│   │   ├── storage_manager.py   # 저장 관리
│   │   ├── search_engine.py     # 검색 엔진
│   │   ├── note_manager.py      # 노트 관리
│   │   ├── trash_manager.py     # 휴지통 관리
│   │   ├── export_manager.py    # 데이터 내보내기
│   │   ├── backup_manager.py    # 백업 관리
│   │   ├── review_manager.py    # 콘텐츠 회고
│   │   ├── ai_session.py        # AI 세션 관리
│   │   ├── ai_cache.py          # AI 캐시 기본 클래스
│   │   └── ai_data_cache.py     # AI 데이터 캐시
│   ├── ai/                      # AI 기능
│   │   ├── summarizer.py        # AI 요약 생성
│   │   ├── chat_router.py       # 스마트 대화 라우터
│   │   ├── fallback.py          # AI 폴백 전략
│   │   └── prompts/             # 프롬프트 템플릿
│   │       ├── chat.py
│   │       ├── note.py
│   │       ├── summarize.py
│   │       └── title.py
│   ├── storage/                 # 저장 레이어
│   │   ├── base.py              # 저장 기본 클래스
│   │   ├── database.py          # 데이터베이스 저장
│   │   └── telegram.py          # Telegram 저장
│   ├── models/                  # 데이터 모델
│   │   └── database.py          # 데이터베이스 모델
│   ├── utils/                   # 유틸리티 모듈
│   │   ├── config.py            # 설정 관리
│   │   ├── logger.py            # 로그 시스템
│   │   ├── i18n.py              # 국제화
│   │   ├── language_context.py  # 언어 컨텍스트
│   │   ├── message_builder.py   # 메시지 빌더 프레임워크
│   │   ├── validators.py        # 입력 검증
│   │   ├── helpers.py           # 헬퍼 함수
│   │   ├── constants.py         # 상수 정의
│   │   ├── file_handler.py      # 파일 처리
│   │   ├── link_extractor.py    # 링크 메타데이터 추출
│   │   └── db_maintenance.py    # 데이터베이스 유지보수
│   └── locales/                 # 언어 파일
│       ├── en.json
│       ├── zh-CN.json
│       ├── zh-TW.json
│       ├── ja.json
│       ├── ko.json
│       └── es.json
└── config/
    └── config.yaml              # 설정 파일
```

## 🤖 AI 기능(선택 사항)

ArchiveBot은 클라우드 AI 서비스를 지원하여 콘텐츠 요약을 **자동으로** 생성하고, 핵심 포인트를 추출하고, 지능적으로 분류하고, 태그를 추천하여 콘텐츠 관리 효율성을 크게 향상시킬 수 있습니다.

### 지원되는 AI 서비스

| 제공업체 | 모델 | 특징 | 권장 시나리오 |
| -------- | ------ | ------ | ---------- |
| **xAI** | Grok-4 | 다국어 이해력 강함, 빠른 속도 | 기본 권장 |
| **OpenAI** | GPT-4/GPT-3.5 | 가장 강력한 기능, 최고의 효과 | 충분한 예산 |
| **Anthropic** | Claude 3.5 | 가성비 높음, 중국어 우수 | 비용 민감 |
| **알리바바 클라우드** | 通义千问 | 국내 서비스, 안정적인 접근 | 중국 사용자 |

💡 **경량 디자인**: HTTP API 호출만 사용, 대규모 SDK 설치 불필요

### AI 기능 하이라이트

✅ **스마트 요약**: 30-100자 간결한 요약 자동 생성  
✅ **핵심 포인트 추출**: 3-5개의 핵심 관점 추출  
✅ **스마트 분류**: 적절한 카테고리로 자동 분류  
✅ **정확한 태그**: 검색 가능한 5개의 전문 태그 생성  
✅ **스마트 대화**: 자연어 상호작용, 자동 의도 및 언어 인식  
✅ **프롬프트 엔지니어링**: 역할 수행 + Few-Shot + 사고 체인 최적화  
✅ **언어 감지**: 중국어/영어 콘텐츠 자동 인식  
✅ **스마트 폴백**: 콘텐츠 길이에 따라 분석 깊이 조정  
✅ **다국어 최적화**: 간체/번체/영어 용어 자동 적응  

### 검색 강화

✅ **페이지네이션 표시**: 10개/페이지, 좌우 화살표 탐색  
✅ **AI 분석 버튼**: 🤖 형식 표시, 원클릭으로 AI 분석 보기  
✅ **빠른 보기**: 클릭하여 완전한 AI 요약/태그/분류 보기  
✅ **직접 이동**: 제목 링크 클릭하여 채널 메시지로 이동  

### ⚠️ AI를 활성화하지 않는 경우의 영향

AI 기능을 활성화하지 않기로 선택한 경우 다음 기능이 **사용 불가능**합니다:

❌ **자동 요약 생성** - 콘텐츠 요약 자동 생성 불가  
❌ **AI 스마트 태그** - AI 추천 태그 자동 생성 불가  
❌ **스마트 분류** - 콘텐츠 자동 분류 불가  
❌ **핵심 포인트 추출** - 콘텐츠 핵심 관점 추출 불가  
❌ **스마트 대화** - 자연어 상호작용 사용 불가  
❌ **검색 AI 분석** - 검색 결과에 🤖 버튼 및 AI 정보 없음  

**✅ 영향을 받지 않는 핵심 기능:**

✅ 콘텐츠 아카이빙 저장  
✅ 수동 태그(#tag)  
✅ 전문 검색(FTS5)  
✅ 노트 시스템  
✅ 휴지통  
✅ 데이터 내보내기/백업  
✅ 모든 명령어 정상 사용  

> 💡 **제안**: AI를 활성화하지 않아도 ArchiveBot의 핵심 아카이빙 및 검색 기능은 완전히 사용 가능합니다. 기본 기능을 먼저 사용하고 나중에 필요할 때 AI를 활성화할 수 있습니다.

### AI 빠른 활성화

1. **API 키 설정**

`config/config.yaml` 편집:

```yaml
ai:
  enabled: true              # AI 기능 활성화
  auto_summarize: true       # 자동 요약 생성
  auto_generate_tags: true   # 자동 AI 태그 생성
  api:
    provider: xai            # 제공업체: xai/openai/anthropic/qwen
    api_key: 'xai-xxx'       # API 키
    base_url: 'https://api.x.ai/v1'  # API 엔드포인트
    model: grok-4-1-fast-non-reasoning  # 응답 생성용 빠른 모델
    reasoning_model: grok-4-1-fast-reasoning  # 의도 분석용 추론 모델
    max_tokens: 1000         # 최대 토큰 수
    timeout: 30              # 요청 시간 초과(초)
```

**다른 제공업체 설정 예시:**

<details>
<summary>OpenAI GPT-4</summary>

```yaml
ai:
  enabled: true
  auto_summarize: true
  auto_generate_tags: true
  api:
    provider: openai
    api_key: 'sk-xxx'
    base_url: 'https://api.openai.com/v1'
    model: gpt-4-turbo       # 응답 생성용 모델
    reasoning_model: gpt-4-turbo  # 의도 분석용 추론 모델
    max_tokens: 1000
    timeout: 30
```

</details>

<details>
<summary>Anthropic Claude</summary>

```yaml
ai:
  enabled: true
  auto_summarize: true
  auto_generate_tags: true
  api:
    provider: anthropic
    api_key: 'sk-ant-xxx'
    base_url: 'https://api.anthropic.com/v1'
    model: claude-3-5-sonnet-20241022  # 응답 생성용 모델
    reasoning_model: claude-3-5-sonnet-20241022  # 의도 분석용 추론 모델
    max_tokens: 1000
    timeout: 30
```

</details>

<details>
<summary>알리바바 클라우드 通义千问</summary>

```yaml
ai:
  enabled: true
  auto_summarize: true
  auto_generate_tags: true
  api:
    provider: qwen
    api_key: 'sk-xxx'
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    model: qwen-plus         # 응답 생성용 모델
    reasoning_model: qwen-plus  # 의도 분석용 추론 모델
    max_tokens: 1000
    timeout: 30
```

</details>

2. **Bot 재시작**

```bash
python main.py
```

3. **AI 상태 확인**

```bash
# Telegram에서 Bot에게 다음 명령어 보내기
/ai
```

4. **AI 기능 사용 시작**

Bot에게 어떤 콘텐츠(텍스트/링크/이미지/문서 등)든 보내면 AI가 자동으로 백그라운드에서 분석합니다. `/search` 검색 시 AI 분석이 있는 콘텐츠에는 🤖 버튼이 표시되며, 클릭하면 완전한 AI 분석 결과(요약/핵심 포인트/태그/분류)를 볼 수 있습니다.

## 📚 문서

- 📖 [빠른 시작](docs/QUICKSTART.md) - 5분 만에 빠르게 시작
- 🚀 [배포 가이드](docs/DEPLOYMENT.md) - 프로덕션 환경 배포

## 🔒 보안 기능

- ✅ **SQL 인젝션 방어** - 매개변수화된 쿼리 + ESCAPE 이스케이프
- ✅ **입력 검증** - 모든 입력은 엄격한 검증 및 정리
- ✅ **민감 정보 필터링** - 로그에서 token 및 ID 자동 필터링
- ✅ **스레드 안전** - RLock + WAL 모드
- ✅ **인증** - owner_only 데코레이터 보호
- ✅ **오류 처리** - 완벽한 예외 처리 및 복구 메커니즘

## 🎯 개발 로드맵

### ✅ 1단계 (완료)

- ✅ 기본 Bot 프레임워크 및 명령 시스템
- ✅ 스마트 콘텐츠 분석 및 아카이빙
- ✅ 전문 검색 엔진 (FTS5)
- ✅ 다국어 지원 (en/zh-CN/zh-TW/zh-HK/zh-MO)
- ✅ AI 스마트 강화 (Grok-4)
  - ✅ 스마트 요약/핵심 포인트/분류/태그
  - ✅ 스마트 의도 인식 및 자연어 상호작용
  - ✅ 프롬프트 엔지니어링 최적화
  - ✅ 콘텐츠 언어 감지
  - ✅ 스마트 폴백 전략
  - ✅ 다국어 용어 최적화
- ✅ 검색 경험 최적화
  - ✅ 페이지네이션 표시 (10개/페이지)
  - ✅ AI 분석 버튼
  - ✅ 탐색 최적화
- ✅ 간소화된 Telegram 저장 전략

### ✅ 2단계 (완료)

- ✅ 노트 및 주석 시스템
  - ✅ 독립 노트 및 연결 노트
  - ✅ 노트 모드 빠른 추가
  - ✅ 노트 목록 표시
  - ✅ 노트 상태 표시 (📝/📝✓)
- ✅ 즐겨찾기 기능
  - ✅ 원클릭 즐겨찾기 표시 (🤍/❤️)
  - ✅ 즐겨찾기 필터 쿼리
  - ✅ 즐겨찾기 상태 표시
- ✅ 빠른 조작 버튼
  - ✅ 전달 기능 (↗️)
  - ✅ 각 레코드 조작 버튼
  - ✅ 아카이빙 성공 메시지 조작 버튼
- ✅ 휴지통 시스템
  - ✅ 소프트 삭제 메커니즘
  - ✅ 콘텐츠 복구
  - ✅ 정기 정리
- ✅ 데이터 내보내기 기능 (Markdown/JSON/CSV)
- ✅ 자동 백업 시스템
  - ✅ 예약 백업 스케줄(매 시간 확인)
  - ✅ 백업 파일 관리
  - ✅ 백업 복구
  - ✅ 구성 가능한 백업 간격

### ✅ 3단계 (완료)

- ✅ 사용자 경험 최적화
  - ✅ 명령어 별칭 지원(/s = /search, /t = /tags, /st = /stats, /la = /language)
  - ✅ 자동 중복 제거 감지(파일 MD5 감지, 중복 아카이빙 방지)
- ✅ 콘텐츠 회고 기능
  - ✅ 활동 통계 보고서(주/월/년 트렌드, 인기 태그, 일일 활동)
  - ✅ 무작위 회고 표시(통계 보고서에 무작위 과거 콘텐츠 자동 포함)
  - ✅ `/review` 명령어(버튼으로 기간 선택)
  - ✅ `/rand` 독립 무작위 회고 명령어(구성 가능한 수량, 빠른 과거 아카이빙 보기)
- ✅ AI 기능 강화
  - ✅ 민감한 콘텐츠를 지능적으로 식별하여 지정된 채널에 아카이빙
  - ✅ AI 참조 콘텐츠에서 지정된 아카이빙 채널 제외
  - ✅ AI 참조 콘텐츠에서 지정된 태그 및 분류 제외
- ✅ 아카이빙 기능 강화
  - ✅ 전달 소스에 따라 지정된 아카이빙 채널
  - ✅ 개인이 직접 보낸 문서를 지정된 아카이빙 채널로
  - ✅ 태그에 따라 지정된 아카이빙 채널

### 📝 4단계 (미래 계획)

- 🔄 일괄 작업(하위 API 완료, UI 개발 대기)
  - 🚧 일괄 태그 교체 API(replace_tag)
  - 🚧 일괄 태그 제거 API
  - 🚧 일괄 작업 사용자 인터페이스(명령어/버튼)
  - 🚧 일괄 삭제/복구
  - 🚧 일괄 내보내기
- 🚧 고급 검색
  - 🚧 결합 필터
  - 🚧 시간 범위
  - 🚧 콘텐츠 유형 필터
- 🔮 **AI 기능 강화**
  - 🚧 음성을 텍스트로 변환(Whisper API)
  - 🚧 OCR 이미지 텍스트 인식
  - 🚧 스마트 콘텐츠 유사도 분석
- 🔮 **확장 기능**
  - 🚧 웹 관리 인터페이스
  - 🚧 RESTful API 인터페이스
  - 🚧 클라우드 스토리지 통합(Google Drive/알리바바 클라우드 디스크)
  - 🚧 강화된 URL 콘텐츠 안티 스크래핑 검색
- 🔮 **성능 최적화**
  - 🚧 캐시 메커니즘 최적화
  - 🚧 비동기 처리 강화
  - 🚧 일괄 작업 최적화

## 🤝 기여

Issue 및 Pull Request 제출을 환영합니다!

## 📄 라이선스

이 프로젝트는 [MIT License](LICENSE)를 따릅니다

## 🙏 감사

### 특별 감사

- **[@WangPanBOT](https://t.me/WangPanBOT)** - Telegram 클라우드 드라이브 봇 프로젝트, 이 프로젝트의 영감의 원천으로 Telegram Bot이 개인 콘텐츠 관리 분야에서 가진 거대한 잠재력을 보여줌

### 오픈소스 프로젝트

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - 우수한 Telegram Bot 프레임워크, 강력하고 사용하기 쉬움
- [SQLite](https://www.sqlite.org/) - 신뢰할 수 있는 임베디드 데이터베이스, 가볍고 효율적

### AI 서비스 제공업체

- [xAI](https://x.ai/) - Grok-4 빠른 추론 모델
- [OpenAI](https://openai.com/) - GPT 시리즈 모델
- [Anthropic](https://anthropic.com/) - Claude 시리즈 모델
- [알리바바 클라우드](https://www.aliyun.com/) - 通义千问 모델

## 📧 연락처

- **GitHub Issues**: [문제 제출](https://github.com/tealun/ArchiveBot/issues)
- **X (Twitter)**: [@TealunDu](https://x.com/TealunDu)
- **Email**: <tealun@gmail.com>

### 교류 그룹

- **중국어 교류 그룹**: [@ArchiveBotCN](https://t.me/joinchat/3753827356)
- **English Group**: [@ArchiveBotEN](https://t.me/joinchat/3877196244)

---

## ⚠️ 면책 조항

### 사용 안내

1. **개인 사용**: 이 프로젝트는 학습 연구 및 개인 사용만을 위한 것이며, 상업적 용도나 불법 활동에 사용할 수 없습니다
2. **서비스 약관**: 이 프로젝트를 사용할 때 [Telegram 서비스 약관](https://telegram.org/tos) 및 관련 API 사용 정책을 엄격히 준수하십시오
3. **콘텐츠 책임**: 사용자는 Bot을 통해 아카이빙된 모든 콘텐츠에 대해 전적으로 책임을 지며, 개발자는 사용자가 저장한 콘텐츠에 대해 어떠한 책임도 지지 않습니다
4. **데이터 보안**: 이 프로젝트는 로컬 배포 도구로, 데이터는 사용자 자신의 환경에 저장됩니다. 설정 파일과 데이터베이스를 적절히 관리하여 민감한 정보 유출을 방지하십시오

### 타사 서비스

1. **AI 서비스**: AI 기능을 사용할 때 콘텐츠가 타사 AI 서비스 제공업체(xAI/OpenAI/Anthropic/알리바바 클라우드)로 전송됩니다. 이러한 서비스 제공업체의 사용 약관 및 개인정보 보호정책을 준수하는지 확인하십시오
2. **API 사용**: 사용자는 각 타사 서비스의 API 키를 직접 신청하고 합법적으로 사용해야 하며, API 남용으로 인한 결과는 사용자가 스스로 책임을 집니다

### 지적 재산권 및 개인정보 보호

1. **저작권 보호**: 이 프로젝트를 사용하여 저작권으로 보호되는 콘텐츠나 타인의 지적 재산권을 침해하는 자료를 아카이빙하지 마십시오
2. **개인정보 보호 존중**: 승인 없이 타인의 개인 정보나 대화 내용을 아카이빙하지 마십시오
3. **오픈소스 라이선스**: 이 프로젝트는 MIT License를 채택하지만 어떠한 보증이나 보장도 포함하지 않습니다

### 보증 부인

1. **있는 그대로 제공**: 이 소프트웨어는 "있는 그대로" 제공되며, 상품성, 특정 목적에의 적합성 및 비침해에 대한 것을 포함하되 이에 국한되지 않는 명시적 또는 묵시적 보증을 제공하지 않습니다
2. **위험 부담**: 이 프로젝트를 사용하여 발생하는 직접적 또는 간접적 손실(데이터 손실, 서비스 중단, 비즈니스 손실 등을 포함하되 이에 국한되지 않음)에 대해 개발자는 책임을 지지 않습니다
3. **보안 위험**: 프로젝트가 보안 조치를 취했지만 모든 소프트웨어에는 알려지지 않은 취약점이 존재할 수 있습니다. 사용자는 스스로 보안 위험을 평가해야 합니다

### 법률 준수

1. **지역 법률**: 해당 지역에서 이 프로젝트를 사용하는 것이 현지 법률 및 규정을 준수하는지 확인하십시오
2. **불법 행위 금지**: 이 프로젝트를 사용하여 불법 정보 전파, 개인정보 침해, 네트워크 공격 등을 포함하되 이에 국한되지 않는 불법적이거나 규정을 위반하는 활동에 참여하는 것을 엄격히 금지합니다

---
