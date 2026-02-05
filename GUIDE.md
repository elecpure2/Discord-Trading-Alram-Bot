# Trading Alert Bot - 사용 가이드

## 🎯 빠른 시작 가이드

### 1단계: Discord 웹훅 설정

1. Discord에서 알림을 받을 채널 선택
2. 채널 설정 → 연동 → 웹후크 → 새 웹후크
3. 웹후크 URL 복사
4. `.env` 파일을 열어서 해당 URL 입력

```env
DISCORD_WEBHOOK_CRYPTO=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL
```

### 2단계: 알람 설정

`alerts.json` 파일을 열어서 원하는 알람 추가:

#### 암호화폐 알람 예시

```json
{
  "id": "my-btc-alert",
  "market": "crypto",
  "symbol": "BTC",           // Upbit (KRW)
  "condition": "above",
  "price": 100000000,        // 1억원
  "enabled": true,
  "created_at": "2026-02-04T19:00:00",
  "last_triggered": null
}
```

**Binance (USDT) 사용 시:**
```json
{
  "symbol": "BTC/USDT",      // 또는 "BTCUSDT"
  "price": 50000
}
```

#### 미국 주식 알람 예시

```json
{
  "id": "my-aapl-alert",
  "market": "us_stock",
  "symbol": "AAPL",          // 티커 심볼
  "condition": "below",
  "price": 150,
  "enabled": true,
  "created_at": "2026-02-04T19:00:00",
  "last_triggered": null
}
```

#### 한국 주식 알람 예시

```json
{
  "id": "my-samsung-alert",
  "market": "kr_stock",
  "symbol": "005930",        // 삼성전자 종목코드
  "condition": "above",
  "price": 80000,
  "enabled": true,
  "created_at": "2026-02-04T19:00:00",
  "last_triggered": null
}
```

**한국 주식 사용 시 추가 설정:**
- [한국투자증권 KIS Developers](https://apiportal.koreainvestment.com/) 가입
- 앱 키 발급 후 `.env`에 추가:

```env
KIS_APP_KEY=your_app_key
KIS_APP_SECRET=your_app_secret
```

### 3단계: 봇 실행

```bash
python main.py
```

## 📊 주요 종목 코드

### 암호화폐
- **Upbit (KRW)**: `BTC`, `ETH`, `XRP`, `ADA`, `SOL`
- **Binance (USDT)**: `BTC/USDT`, `ETH/USDT`, `BNB/USDT`

### 미국 주식
- **테크**: `AAPL`, `MSFT`, `GOOGL`, `AMZN`, `META`, `NVDA`, `TSLA`
- **ETF**: `SPY`, `QQQ`, `VOO`

### 한국 주식
- **삼성전자**: `005930`
- **SK하이닉스**: `000660`
- **NAVER**: `035420`
- **카카오**: `035720`
- **현대차**: `005380`

## 🔧 고급 설정

### 알람 조건
- `"above"`: 가격이 목표가 **이상**일 때
- `"below"`: 가격이 목표가 **이하**일 때

### 알람 활성화/비활성화
```json
"enabled": true   // 활성화
"enabled": false  // 비활성화 (알람 유지하되 작동 안 함)
```

### 쿨다운 시간
- 알람이 한 번 트리거되면 **5분간** 재알림 안 됨
- `config.py`에서 `ALERT_COOLDOWN_SECONDS` 수정 가능

### 체크 주기 조정
`.env` 파일에서:
```env
CRYPTO_CHECK_INTERVAL=1      # 암호화폐: 1초마다 체크
US_STOCK_CHECK_INTERVAL=60   # 미국주식: 60초마다 체크
KR_STOCK_CHECK_INTERVAL=5    # 한국주식: 5초마다 체크
```

## 💡 팁

1. **테스트 먼저**: `python test_webhook.py`로 웹훅 테스트
2. **현재가 근처 알람**: 테스트용으로 현재가 근처에 알람 설정
3. **여러 채널 사용**: 시장별로 다른 Discord 채널 사용 가능
4. **알람 백업**: `alerts.json` 파일 주기적으로 백업

## ❓ 자주 묻는 질문

**Q: 알람이 안 울려요**
- Discord 웹훅 URL 확인
- `alerts.json`에서 `"enabled": true` 확인
- 로그 파일 확인: `logs/app.log`

**Q: 미국 주식 가격이 이상해요**
- yfinance는 15분 지연될 수 있습니다
- 장 마감 후에는 종가가 표시됩니다

**Q: 한국 주식이 작동 안 해요**
- KIS API 키 설정 확인
- 장 시간(09:00-15:30) 확인
- 종목 코드 6자리 숫자 확인

**Q: 알람을 몇 개까지 설정할 수 있나요?**
- 무제한! (단, 한 종목당 최대 10개)

## 🚀 다음 단계

현재는 기본 가격 알람만 지원하지만, 추후 추가 예정:
- RSI, 이동평균선 등 기술적 지표
- 거래량 급증 알림
- 디스코드 봇 명령어로 알람 관리
- 웹 대시보드

## 📝 알람 예시 모음

### 비트코인 1억 돌파 알림
```json
{
  "id": "btc-100m",
  "market": "crypto",
  "symbol": "BTC",
  "condition": "above",
  "price": 100000000,
  "enabled": true
}
```

### 애플 주가 하락 알림
```json
{
  "id": "aapl-dip",
  "market": "us_stock",
  "symbol": "AAPL",
  "condition": "below",
  "price": 180,
  "enabled": true
}
```

### 삼성전자 8만원 돌파 알림
```json
{
  "id": "samsung-80k",
  "market": "kr_stock",
  "symbol": "005930",
  "condition": "above",
  "price": 80000,
  "enabled": true
}
```
