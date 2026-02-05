# Trading Alert Bot

무제한 가격 알람 시스템 - 트레이딩뷰 유료 플랜 대체

## 🎯 Features

- 🪙 **암호화폐**: Upbit (KRW) / Binance (USDT) 실시간 모니터링
- 🇺🇸 **미국 주식**: yfinance API (15분 지연)
- 🇰🇷 **한국 주식**: 한국투자증권 KIS API (실시간)
- 📢 **Discord 알림**: 시장별 채널로 알림 전송
- 💾 **무제한 알람**: JSON 기반 저장소

## 🚀 Quick Start

### 1. 설치

```bash
# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 설정

`.env.example`을 복사하여 `.env` 파일 생성:

```bash
cp .env.example .env
```

`.env` 파일에 Discord 웹훅 URL 입력:

```env
DISCORD_WEBHOOK_CRYPTO=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL
DISCORD_WEBHOOK_US_STOCK=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL
DISCORD_WEBHOOK_KR_STOCK=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL
```

### 3. Discord 웹훅 테스트

```bash
python test_webhook.py
```

### 4. 알람 설정

`alerts.json` 파일을 생성하고 알람 추가:

```json
{
  "alerts": [
    {
      "id": "1",
      "market": "crypto",
      "symbol": "BTC",
      "condition": "above",
      "price": 50000,
      "enabled": true,
      "created_at": "2026-02-04T19:00:00"
    },
    {
      "id": "2",
      "market": "us_stock",
      "symbol": "AAPL",
      "condition": "below",
      "price": 150,
      "enabled": true,
      "created_at": "2026-02-04T19:00:00"
    }
  ]
}
```

### 5. 봇 실행

```bash
python main.py
```

## 📋 Alert Configuration

### 암호화폐 (Crypto)

- **Upbit (KRW)**: `"symbol": "BTC"` 또는 `"symbol": "ETH"`
- **Binance (USDT)**: `"symbol": "BTC/USDT"` 또는 `"symbol": "BTCUSDT"`

### 미국 주식 (US Stock)

- **Symbol**: 티커 심볼 사용 (예: `"AAPL"`, `"TSLA"`, `"NVDA"`)

### 한국 주식 (KR Stock)

- **Symbol**: 종목 코드 사용 (예: `"005930"` - 삼성전자)
- **KIS API 설정 필요**: `.env`에 `KIS_APP_KEY`, `KIS_APP_SECRET` 추가

### Alert Conditions

- `"above"`: 가격이 목표가 이상일 때 알림
- `"below"`: 가격이 목표가 이하일 때 알림

## 📁 Project Structure

```
Alram Bot/
├── main.py                 # 메인 실행 파일
├── config.py               # 설정 관리
├── alert_manager.py        # 알람 관리 시스템
├── notifier.py            # Discord 알림 전송
├── monitors/              # 시장별 모니터
│   ├── crypto_monitor.py
│   ├── us_stock_monitor.py
│   └── kr_stock_monitor.py
├── utils/                 # 유틸리티
│   └── logger.py
├── requirements.txt       # 의존성
├── .env.example          # 환경변수 템플릿
└── alerts.json           # 알람 데이터 (자동 생성)
```

## 🔧 Advanced Configuration

### Check Intervals

`.env`에서 체크 주기 조정:

```env
CRYPTO_CHECK_INTERVAL=1      # 암호화폐 (초)
US_STOCK_CHECK_INTERVAL=60   # 미국 주식 (초)
KR_STOCK_CHECK_INTERVAL=5    # 한국 주식 (초)
```

### Alert Cooldown

`config.py`에서 쿨다운 시간 조정:

```python
ALERT_COOLDOWN_SECONDS = 300  # 5분
```

## 📝 Notes

- 미국 주식 데이터는 15분 지연될 수 있습니다 (yfinance 무료 티어)
- 한국 주식은 KIS API 설정이 필요합니다
- 알람은 트리거 후 5분 쿨다운이 적용됩니다

## 🆘 Troubleshooting

### Discord 알림이 안 와요
- `.env` 파일의 웹훅 URL 확인
- `python test_webhook.py`로 웹훅 테스트

### 암호화폐 가격이 업데이트 안 돼요
- `alerts.json`에 알람이 있는지 확인
- 심볼 형식 확인 (Upbit: `BTC`, Binance: `BTC/USDT`)

### 한국 주식이 작동 안 해요
- KIS API 키가 `.env`에 설정되어 있는지 확인
- 종목 코드가 올바른지 확인 (6자리 숫자)

## 📄 License

MIT License
