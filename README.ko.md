# 🤖 Trading Alert Bot

무제한 가격 알람 + RSI 다이버전스 + 멀티거래소 고래 탐지 시스템

> 트레이딩뷰 유료 플랜 대체 + AI 기반 지표 분석

## ✨ Features

### 📊 가격 알람
- 🪙 **암호화폐**: Upbit (KRW) / Binance (USDT) 실시간 모니터링
- 🇺🇸 **미국 주식**: yfinance API
- 🇰🇷 **한국 주식**: 한국투자증권 KIS API
- 📢 **Discord 알림**: 시장별 채널로 알림 전송
- 💾 **무제한 알람**: JSON 기반 저장소

### 📈 RSI 지표 & 다이버전스 알람
- RSI 레벨 알람 (과매수/과매도)
- RSI 다이버전스 자동 감지 (강세/약세)
- 멀티 타임프레임 지원 (1h, 4h, 1d)
- Binance & yfinance 데이터 지원

### 🐋 멀티 거래소 고래 탐지
- **4개 거래소 실시간 모니터링**
  - 🟡 Binance (USDT)
  - 🔵 OKX (USDT)
  - 🟣 Bybit (USDT)
  - 🟢 Upbit (KRW)
- 대규모 거래 즉시 알림 (거래소별 임계값 설정)
- 거래소별 on/off 제어
- 설정 영구 저장

### 🎮 Discord Bot 명령어
- `!` 프리픽스 기반 빠른 명령어
- 실시간 가격 조회 (미니 차트 포함)
- RSI 조회 및 알람 설정
- 고래 알람 제어

## 🚀 Quick Start

### 1. 설치

```bash
# 의존성 설치
pip install -r requirements.txt
```

**필수 패키지:**
- discord.py
- websocket-client
- pandas, numpy
- requests, yfinance

### 2. 환경 설정

`.env.example`을 복사하여 `.env` 파일 생성:

```env
# Discord Bot Token (봇 명령어 사용 시)
DISCORD_BOT_TOKEN=your_bot_token_here

# Discord Webhooks (알람 전송)
DISCORD_WEBHOOK_CRYPTO=https://discord.com/api/webhooks/YOUR_WEBHOOK
DISCORD_WEBHOOK_US_STOCK=https://discord.com/api/webhooks/YOUR_WEBHOOK
DISCORD_WEBHOOK_KR_STOCK=https://discord.com/api/webhooks/YOUR_WEBHOOK

# 한국투자증권 API (선택)
KIS_APP_KEY=your_app_key
KIS_APP_SECRET=your_app_secret
```

**Discord 봇 설정:**
1. [Discord Developer Portal](https://discord.com/developers/applications)에서 봇 생성
2. **Bot** 탭 → `MESSAGE CONTENT INTENT` 활성화 ✅
3. 봇 토큰 복사 → `.env`에 입력

### 3. Discord 봇 실행

```bash
python discord_bot.py
```

### 4. 가격 모니터 실행 (선택)

```bash
python main.py
```

## 🎮 Discord 명령어

### 💰 가격 조회
```
!현재가 BTC          # 현재가 + 24시간 미니차트
!rsi BTC 4h          # RSI 값 조회
```

### 🔔 가격 알람
```
!알람추가 crypto BTC above 100000    # 가격 알람 추가
!알람목록                            # 알람 목록
!알람삭제 [ID]                       # 알람 삭제
!상태                                # 시스템 상태
```

### 📊 지표 알람
```
!다이버전스 BTC 4h                   # RSI 다이버전스 알람
!rsi알람 BTC below 30 4h             # RSI 레벨 알람
!지표목록                            # 지표 알람 목록
!지표삭제 [ID]                       # 지표 알람 삭제
```

### 🐋 고래 알람
```
!고래 on                             # 고래 알람 활성화
!고래 off                            # 고래 알람 비활성화
!고래 상태                           # 상태 확인
!고래임계값 BTC 1000000              # 임계값 설정 ($1M)
!거래소 Binance off                  # 특정 거래소 끄기
```

### ⚙️ 기타
```
!도움말                              # 전체 명령어 목록
```

## 📋 고급 설정

### 고래 알람 임계값 예시

| 임계값 | 의미 | 추천 대상 |
|--------|------|----------|
| $100K | 작은 고래 | 빈번한 알림 원하는 경우 |
| $500K | 중형 고래 | 일반적인 사용 |
| $1M+ | 대형 고래만 | 중요한 거래만 보고 싶을 때 |

### 거래소별 활성화

```bash
# Discord에서:
!거래소 Binance on      # Binance 활성화
!거래소 Upbit off       # Upbit 비활성화
```

설정은 `whale_settings.json`에 자동 저장됩니다.

## 📁 프로젝트 구조

```
Alram Bot/
├── discord_bot.py           # Discord 봇 (! 명령어)
├── main.py                  # 가격 모니터 메인
├── config.py                # 설정 관리
├── alert_manager.py         # 알람 관리 시스템
├── notifier.py              # Discord 알림 전송
├── monitors/                # 시장별 모니터
│   ├── crypto_monitor.py    # 암호화폐 모니터
│   ├── us_stock_monitor.py  # 미국 주식 모니터
│   ├── kr_stock_monitor.py  # 한국 주식 모니터
│   ├── indicator_monitor.py # RSI/다이버전스 모니터
│   └── whale_monitor.py     # 멀티거래소 고래 모니터
├── utils/                   # 유틸리티
│   ├── logger.py
│   └── indicators.py        # 기술 지표 계산
├── requirements.txt
├── .env.example
├── alerts.json              # 가격 알람 데이터
└── whale_settings.json      # 고래 알람 설정
```

## 🐋 고래 알람 작동 원리

1. **WebSocket 실시간 연결**: 4개 거래소와 동시 연결
2. **대형 거래 감지**: 설정한 임계값 이상 거래 발생 시
3. **즉시 알림**: Discord로 거래소명 + 거래 정보 전송

**알림 예시:**
```
🐋 고래 발견! [Binance] 🐋

BTC/USDT 🟢 매수
━━━━━━━━━━━━━━━━
💰 거래 금액: $1.5M (약 20억원)
📊 수량: 15.38 BTC
💵 체결가: $97,500.00
⏰ 시간: 14:23:15
```

## 🔧 체크 인터벌 조정

`.env`에서 체크 주기 조정:

```env
CRYPTO_CHECK_INTERVAL=1      # 암호화폐 (초)
US_STOCK_CHECK_INTERVAL=60   # 미국 주식 (초)
KR_STOCK_CHECK_INTERVAL=5    # 한국 주식 (초)
```

## 📝 주의사항

- 미국 주식 데이터는 15분 지연될 수 있습니다 (yfinance 무료 티어)
- 한국 주식은 KIS API 설정이 필요합니다
- 알람은 트리거 후 5분 쿨다운이 적용됩니다
- Discord 봇은 `MESSAGE CONTENT INTENT` 필수

## 🆘 문제 해결

### Discord 알림이 안 와요
- `.env` 파일의 웹훅 URL 확인
- `python test_webhook.py`로 웹훅 테스트

### ! 명령어가 작동 안 해요
- Discord 봇 설정에서 `MESSAGE CONTENT INTENT` 활성화 확인
- `discord_bot.py` 실행 중인지 확인

### 고래 알람이 안 와요
- `!고래 on`으로 활성화했는지 확인
- 임계값이 너무 높지 않은지 확인 (`!고래 상태`)
- 봇 재시작 (`Ctrl+C` 후 재실행)

## 🛠️ 기술 스택

- **Python 3.8+**
- **Discord.py**: 봇 명령어
- **WebSocket**: 실시간 데이터 (거래소별 WS API)
- **Pandas/NumPy**: 지표 계산
- **Requests**: REST API 호출

## 📄 라이선스

MIT License

## 🙏 기여

이슈와 PR은 언제나 환영합니다!

---

**Made with ❤️ for Crypto Traders**
