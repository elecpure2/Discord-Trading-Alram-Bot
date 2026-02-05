"""
Discord Bot for Trading Alert System
Provides prefix commands (!) to manage price alerts
"""
import asyncio
import discord
from discord.ext import commands
from typing import Optional
import requests

from alert_manager import AlertManager
from config import DISCORD_BOT_TOKEN
from utils.logger import setup_logger

logger = setup_logger(__name__, "discord_bot.log")


class AlertBot(commands.Bot):
    """Discord Bot with prefix commands for alert management"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # Required for prefix commands
        super().__init__(command_prefix="!", intents=intents)
        self.alert_manager = AlertManager()
    
    async def on_ready(self) -> None:
        """Called when bot is connected and ready"""
        logger.info(f"Bot connected as {self.user}")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="!도움말 | 가격 알림 📈"
            )
        )


# Create bot instance
bot = AlertBot()


# ============================================================
# Help Command
# ============================================================

@bot.command(name="도움말", aliases=["h"])
async def help_command(ctx):
    """Show all available commands"""
    embed = discord.Embed(
        title="📋 Trading Alert Bot 명령어",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="💰 가격 조회",
        value="`!현재가 BTC` - 현재가 + 미니차트\n`!rsi BTC 4h` - RSI 값 조회",
        inline=False
    )
    
    embed.add_field(
        name="🔔 가격 알람",
        value="`!알람추가 crypto BTC above 100000`\n`!알람목록` - 알람 목록\n`!알람삭제 [ID]` - 알람 삭제",
        inline=False
    )
    
    embed.add_field(
        name="📊 지표 알람",
        value="`!다이버전스 BTC 4h` - 다이버전스 알람\n`!rsi알람 BTC below 30 4h` - RSI 레벨 알람\n`!지표목록` - 지표 알람 목록",
        inline=False
    )
    
    embed.add_field(
        name="🐋 고래 알람",
        value="`!고래 on` - 고래 알람 활성화\n`!고래 off` - 비활성화\n`!고래임계값 BTC 1000000`",
        inline=False
    )
    
    embed.add_field(
        name="📊 거래량 알람",
        value="`!거래량알람 on` - 거래량 급증 알람 활성화\n`!거래량알람 상태` - 상태 확인\n`!거래량임계값 200` - 임계값 설정",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ 시스템",
        value="`!상태` - 알람 시스템 상태",
        inline=False
    )
    
    await ctx.send(embed=embed)


# ============================================================
# Price Commands
# ============================================================

def _generate_sparkline(values: list) -> str:
    """Generate a sparkline chart from values using Unicode blocks"""
    if not values or len(values) < 2:
        return ""
    
    blocks = "▁▂▃▄▅▆▇█"
    min_val = min(values)
    max_val = max(values)
    
    if max_val == min_val:
        return blocks[3] * len(values)
    
    sparkline = ""
    for val in values:
        normalized = (val - min_val) / (max_val - min_val)
        index = int(normalized * 7)
        index = max(0, min(7, index))
        sparkline += blocks[index]
    
    return sparkline


@bot.command(name="현재가", aliases=["price", "p"])
async def get_price(ctx, symbol: str = None):
    """Get current price of a cryptocurrency"""
    if not symbol:
        await ctx.send("❌ 사용법: `!현재가 BTC`")
        return
    
    async with ctx.typing():
        try:
            pair = f"{symbol.upper()}USDT"
            
            # Fetch 24hr ticker data
            ticker_url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={pair}"
            ticker_response = requests.get(ticker_url, timeout=10)
            
            # Fetch klines for mini chart
            klines_url = f"https://api.binance.com/api/v3/klines?symbol={pair}&interval=1h&limit=24"
            klines_response = requests.get(klines_url, timeout=10)
            
            if ticker_response.status_code == 200:
                data = ticker_response.json()
                price = float(data.get("lastPrice", 0))
                change_24h = float(data.get("priceChangePercent", 0))
                volume_usdt = float(data.get("quoteVolume", 0))
                high_24h = float(data.get("highPrice", 0))
                low_24h = float(data.get("lowPrice", 0))
                
                # Generate sparkline
                sparkline = ""
                if klines_response.status_code == 200:
                    klines = klines_response.json()
                    closes = [float(k[4]) for k in klines]
                    sparkline = _generate_sparkline(closes)
                
                # Color based on change
                if change_24h > 0:
                    color = discord.Color.green()
                    change_emoji = "📈"
                elif change_24h < 0:
                    color = discord.Color.red()
                    change_emoji = "📉"
                else:
                    color = discord.Color.gold()
                    change_emoji = "➡️"
                
                # Format price
                if price < 0.01:
                    price_str = f"${price:,.6f}"
                elif price < 1:
                    price_str = f"${price:,.4f}"
                else:
                    price_str = f"${price:,.2f}"
                
                embed = discord.Embed(
                    title=f"🪙 {symbol.upper()}/USDT",
                    color=color
                )
                embed.description = f"**{price_str}**  {change_emoji} {change_24h:+.2f}%"
                
                if sparkline:
                    embed.add_field(
                        name="📊 24시간 차트 (1h봉)",
                        value=f"`{sparkline}`",
                        inline=False
                    )
                
                # High/Low format
                if high_24h < 1:
                    high_str = f"${high_24h:,.4f}"
                    low_str = f"${low_24h:,.4f}"
                else:
                    high_str = f"${high_24h:,.2f}"
                    low_str = f"${low_24h:,.2f}"
                
                embed.add_field(name="🔺 24h 고가", value=high_str, inline=True)
                embed.add_field(name="🔻 24h 저가", value=low_str, inline=True)
                embed.add_field(name="💹 거래량", value=f"${volume_usdt/1_000_000:,.1f}M", inline=True)
                
                embed.set_footer(text="데이터: Binance (USDT)")
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ {symbol} 가격을 가져올 수 없습니다.")
        except Exception as e:
            logger.error(f"Error fetching price: {e}")
            await ctx.send(f"❌ 오류: {e}")


# ============================================================
# Alert Commands
# ============================================================

@bot.command(name="알람추가", aliases=["add", "a"])
async def add_alert(ctx, market: str = None, symbol: str = None, condition: str = None, price: float = None):
    """Add a new price alert"""
    if not all([market, symbol, condition, price]):
        await ctx.send("❌ 사용법: `!알람추가 crypto BTC above 100000`\n시장: `crypto` / `us_stock` / `kr_stock`\n조건: `above` / `below`")
        return
    
    market = market.lower()
    condition = condition.lower()
    
    if market not in ["crypto", "us_stock", "kr_stock"]:
        await ctx.send("❌ 시장: `crypto` / `us_stock` / `kr_stock`")
        return
    
    if condition not in ["above", "below"]:
        await ctx.send("❌ 조건: `above` (이상) / `below` (이하)")
        return
    
    alert = bot.alert_manager.add_alert(market, symbol, condition, price)
    
    if alert:
        market_names = {"crypto": "암호화폐", "us_stock": "미국 주식", "kr_stock": "한국 주식"}
        condition_names = {"above": "이상", "below": "이하"}
        
        embed = discord.Embed(title="✅ 알람 추가 완료", color=discord.Color.green())
        embed.add_field(name="시장", value=market_names[market], inline=True)
        embed.add_field(name="심볼", value=symbol.upper(), inline=True)
        embed.add_field(name="조건", value=f"{price:,.0f} {condition_names[condition]}", inline=True)
        embed.add_field(name="알람 ID", value=f"`{alert.id[:8]}`", inline=False)
        
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ 알람 추가 실패")


@bot.command(name="알람목록", aliases=["list", "l"])
async def list_alerts(ctx, market: str = "all"):
    """List all configured alerts"""
    if market == "all":
        alerts = bot.alert_manager.get_alerts()
    else:
        alerts = bot.alert_manager.get_alerts(market=market)
    
    if not alerts:
        await ctx.send("📭 설정된 알람이 없습니다.")
        return
    
    market_emojis = {"crypto": "🪙", "us_stock": "🇺🇸", "kr_stock": "🇰🇷"}
    condition_symbols = {"above": "≥", "below": "≤"}
    
    embed = discord.Embed(title=f"📋 알람 목록 ({len(alerts)}개)", color=discord.Color.blue())
    
    for alert in alerts[:25]:
        status = "🟢" if alert.enabled else "🔴"
        emoji = market_emojis.get(alert.market, "📊")
        cond = condition_symbols.get(alert.condition, "?")
        
        embed.add_field(
            name=f"{status} {emoji} {alert.symbol}",
            value=f"{cond} {alert.price:,.0f}\n`{alert.id[:8]}`",
            inline=True
        )
    
    await ctx.send(embed=embed)


@bot.command(name="알람삭제", aliases=["del", "d"])
async def remove_alert(ctx, alert_id: str = None):
    """Remove an alert by ID"""
    if not alert_id:
        await ctx.send("❌ 사용법: `!알람삭제 [알람ID]`")
        return
    
    alerts = bot.alert_manager.get_alerts()
    matching_alert = None
    
    for alert in alerts:
        if alert.id.startswith(alert_id) or alert.id == alert_id:
            matching_alert = alert
            break
    
    if not matching_alert:
        await ctx.send(f"❌ ID `{alert_id}`를 찾을 수 없습니다.")
        return
    
    if bot.alert_manager.remove_alert(matching_alert.id):
        embed = discord.Embed(
            title="🗑️ 알람 삭제 완료",
            description=f"**{matching_alert.symbol}** {matching_alert.condition} {matching_alert.price:,.0f}",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ 알람 삭제 실패")


@bot.command(name="상태", aliases=["status", "s"])
async def alert_stats(ctx):
    """Show alert system statistics"""
    stats = bot.alert_manager.get_stats()
    
    embed = discord.Embed(title="📊 알람 시스템 상태", color=discord.Color.purple())
    embed.add_field(name="전체 알람", value=str(stats["total"]), inline=True)
    embed.add_field(name="활성화", value=f"🟢 {stats['enabled']}", inline=True)
    embed.add_field(name="비활성화", value=f"🔴 {stats['disabled']}", inline=True)
    
    await ctx.send(embed=embed)


# ============================================================
# RSI / Divergence Commands
# ============================================================

@bot.command(name="rsi")
async def get_rsi(ctx, symbol: str = None, timeframe: str = "4h"):
    """Get current RSI value"""
    if not symbol:
        await ctx.send("❌ 사용법: `!rsi BTC 4h`")
        return
    
    async with ctx.typing():
        try:
            from monitors.indicator_monitor import IndicatorMonitor
            from alert_manager import AlertManager
            from notifier import DiscordNotifier
            
            temp_monitor = IndicatorMonitor(AlertManager(), DiscordNotifier())
            market = "index" if symbol.upper() in ["NASDAQ", "SPX", "SPY", "QQQ"] else "crypto"
            
            result = temp_monitor.get_current_rsi(symbol.upper(), market, timeframe)
            
            if result:
                embed = discord.Embed(
                    title=f"📊 {symbol.upper()} RSI ({timeframe})",
                    color=discord.Color.blue()
                )
                embed.add_field(name="현재 RSI", value=f"**{result['rsi']:.1f}**", inline=True)
                embed.add_field(name="상태", value=result['status'], inline=True)
                embed.add_field(name="현재가", value=f"${result['price']:,.2f}", inline=True)
                
                if result['divergence']:
                    embed.add_field(name="⚠️ 다이버전스!", value=str(result['divergence']), inline=False)
                
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ {symbol} RSI를 가져올 수 없습니다.")
        except Exception as e:
            logger.error(f"Error fetching RSI: {e}")
            await ctx.send(f"❌ 오류: {e}")


@bot.command(name="다이버전스", aliases=["div"])
async def add_divergence_alert(ctx, symbol: str = None, timeframe: str = "4h"):
    """Add RSI divergence alert"""
    if not symbol:
        await ctx.send("❌ 사용법: `!다이버전스 BTC 4h`")
        return
    
    from monitors.indicator_monitor import get_indicator_monitor, IndicatorMonitor, set_indicator_monitor
    from alert_manager import AlertManager
    from notifier import DiscordNotifier
    
    monitor = get_indicator_monitor()
    if not monitor:
        monitor = IndicatorMonitor(AlertManager(), DiscordNotifier())
        set_indicator_monitor(monitor)
        monitor.start()
    
    market = "index" if symbol.upper() in ["NASDAQ", "SPX", "SPY", "QQQ"] else "crypto"
    
    alert = monitor.add_indicator_alert(
        symbol=symbol.upper(),
        market=market,
        indicator="divergence",
        timeframe=timeframe,
    )
    
    embed = discord.Embed(title="✅ 다이버전스 알람 추가", color=discord.Color.green())
    embed.add_field(name="심볼", value=symbol.upper(), inline=True)
    embed.add_field(name="타임프레임", value=timeframe, inline=True)
    embed.add_field(name="ID", value=f"`{alert.id[:8]}`", inline=True)
    
    await ctx.send(embed=embed)


@bot.command(name="rsi알람")
async def add_rsi_alert(ctx, symbol: str = None, condition: str = None, level: float = None, timeframe: str = "4h"):
    """Add RSI level alert"""
    if not all([symbol, condition, level]):
        await ctx.send("❌ 사용법: `!rsi알람 BTC below 30 4h`")
        return
    
    if level < 0 or level > 100:
        await ctx.send("❌ RSI는 0-100 사이여야 합니다.")
        return
    
    from monitors.indicator_monitor import get_indicator_monitor, IndicatorMonitor, set_indicator_monitor
    from alert_manager import AlertManager
    from notifier import DiscordNotifier
    
    monitor = get_indicator_monitor()
    if not monitor:
        monitor = IndicatorMonitor(AlertManager(), DiscordNotifier())
        set_indicator_monitor(monitor)
        monitor.start()
    
    market = "index" if symbol.upper() in ["NASDAQ", "SPX", "SPY", "QQQ"] else "crypto"
    
    alert = monitor.add_indicator_alert(
        symbol=symbol.upper(),
        market=market,
        indicator="rsi",
        timeframe=timeframe,
        condition=condition,
        threshold=level,
    )
    
    cond_text = "이상" if condition == "above" else "이하"
    
    embed = discord.Embed(title="✅ RSI 알람 추가", color=discord.Color.green())
    embed.add_field(name="심볼", value=symbol.upper(), inline=True)
    embed.add_field(name="조건", value=f"RSI {level} {cond_text}", inline=True)
    embed.add_field(name="ID", value=f"`{alert.id[:8]}`", inline=True)
    
    await ctx.send(embed=embed)


@bot.command(name="지표목록")
async def list_indicator_alerts(ctx):
    """List all indicator alerts"""
    from monitors.indicator_monitor import get_indicator_monitor
    
    monitor = get_indicator_monitor()
    if not monitor:
        await ctx.send("📭 설정된 지표 알람이 없습니다.")
        return
    
    alerts = monitor.get_indicator_alerts()
    
    if not alerts:
        await ctx.send("📭 설정된 지표 알람이 없습니다.")
        return
    
    embed = discord.Embed(title=f"📊 지표 알람 ({len(alerts)}개)", color=discord.Color.purple())
    
    for alert in alerts[:25]:
        status = "🟢" if alert.enabled else "🔴"
        if alert.indicator == "divergence":
            value = f"다이버전스 ({alert.timeframe})"
        else:
            cond = "≥" if alert.condition == "above" else "≤"
            value = f"RSI {cond} {alert.threshold} ({alert.timeframe})"
        
        embed.add_field(name=f"{status} {alert.symbol}", value=f"{value}\n`{alert.id[:8]}`", inline=True)
    
    await ctx.send(embed=embed)


@bot.command(name="지표삭제")
async def remove_indicator_alert(ctx, alert_id: str = None):
    """Remove an indicator alert"""
    if not alert_id:
        await ctx.send("❌ 사용법: `!지표삭제 [알람ID]`")
        return
    
    from monitors.indicator_monitor import get_indicator_monitor
    
    monitor = get_indicator_monitor()
    if not monitor:
        await ctx.send("❌ 지표 알람이 없습니다.")
        return
    
    if monitor.remove_indicator_alert(alert_id):
        await ctx.send("🗑️ 지표 알람 삭제 완료")
    else:
        await ctx.send(f"❌ ID `{alert_id}`를 찾을 수 없습니다.")


# ============================================================
# Whale Alert Commands
# ============================================================

@bot.command(name="고래", aliases=["whale"])
async def whale_alert_toggle(ctx, action: str = None):
    """Enable/disable whale alerts"""
    if not action:
        await ctx.send("❌ 사용법: `!고래 on` / `!고래 off` / `!고래 상태`")
        return
    
    from monitors.whale_monitor import get_whale_monitor, set_whale_monitor, WhaleMonitor
    from notifier import DiscordNotifier
    
    monitor = get_whale_monitor()
    
    if action.lower() in ["on", "활성화", "enable"]:
        if not monitor:
            notifier = DiscordNotifier()
            monitor = WhaleMonitor(notifier)
            set_whale_monitor(monitor)
        
        monitor.enable()
        
        embed = discord.Embed(title="🐋 고래 알람 활성화", color=discord.Color.blue())
        embed.add_field(name="BTC", value=f"${monitor.get_threshold('BTC'):,.0f}", inline=True)
        embed.add_field(name="ETH", value=f"${monitor.get_threshold('ETH'):,.0f}", inline=True)
        embed.set_footer(text="임계값 변경: !고래임계값 BTC 1000000")
        
        await ctx.send(embed=embed)
        
    elif action.lower() in ["off", "비활성화", "disable"]:
        if monitor:
            monitor.disable()
        await ctx.send("🐋 고래 알람 비활성화됨")
        
    else:  # status
        if not monitor:
            await ctx.send("🐋 고래 알람이 설정되지 않았습니다.")
            return
        
        status = monitor.get_status()
        
        embed = discord.Embed(
            title="🐋 고래 알람 상태",
            color=discord.Color.blue() if status["enabled"] else discord.Color.gray()
        )
        embed.add_field(name="상태", value="🟢 활성화" if status["enabled"] else "🔴 비활성화", inline=True)
        embed.add_field(name="모니터링", value=", ".join(status["symbols"]), inline=True)
        
        # Show exchanges
        exchanges = status.get("exchanges", {})
        exchange_list = []
        for ex, enabled in exchanges.items():
            exchange_list.append(f"{'✅' if enabled else '❌'} {ex}")
        embed.add_field(name="거래소", value="\n".join(exchange_list), inline=False)
        
        # Show thresholds
        thresholds = status.get("thresholds", {})
        threshold_list = [f"{s}: {v}" for s, v in thresholds.items()]
        embed.add_field(name="임계값", value="\n".join(threshold_list), inline=False)
        
        embed.set_footer(text="거래소 설정: !거래소 Binance on/off")
        
        await ctx.send(embed=embed)


@bot.command(name="고래임계값")
async def set_whale_threshold(ctx, symbol: str = None, amount: int = None):
    """Set whale alert threshold"""
    if not symbol or not amount:
        await ctx.send("❌ 사용법: `!고래임계값 BTC 1000000`")
        return
    
    if symbol.upper() not in ["BTC", "ETH"]:
        await ctx.send("❌ 지원: BTC, ETH")
        return
    
    if amount < 100000:
        await ctx.send("❌ 최소 $100,000")
        return
    
    from monitors.whale_monitor import get_whale_monitor, set_whale_monitor, WhaleMonitor
    from notifier import DiscordNotifier
    
    monitor = get_whale_monitor()
    if not monitor:
        notifier = DiscordNotifier()
        monitor = WhaleMonitor(notifier)
        set_whale_monitor(monitor)
    
    monitor.set_threshold(symbol.upper(), amount)
    
    if amount >= 1_000_000:
        amount_str = f"${amount/1_000_000:.1f}M"
    else:
        amount_str = f"${amount:,.0f}"
    
    krw_amount = amount * 1350 / 100_000_000
    
    embed = discord.Embed(title="🐋 고래 임계값 설정", color=discord.Color.green())
    embed.add_field(name="심볼", value=symbol.upper(), inline=True)
    embed.add_field(name="임계값", value=amount_str, inline=True)
    embed.add_field(name="원화", value=f"약 {krw_amount:.0f}억원", inline=True)
    
    await ctx.send(embed=embed)


@bot.command(name="거래소", aliases=["exchange"])
async def toggle_exchange(ctx, exchange: str = None, action: str = None):
    """Enable/disable specific exchange for whale alerts"""
    if not exchange or not action:
        await ctx.send("❌ 사용법: `!거래소 Binance on` / `!거래소 OKX off`\n거래소: Binance, OKX, Bybit, Upbit")
        return
    
    exchange = exchange.capitalize()
    if exchange == "Okx":
        exchange = "OKX"
    
    if exchange not in ["Binance", "OKX", "Bybit", "Upbit"]:
        await ctx.send("❌ 지원 거래소: Binance, OKX, Bybit, Upbit")
        return
    
    from monitors.whale_monitor import get_whale_monitor, set_whale_monitor, WhaleMonitor
    from notifier import DiscordNotifier
    
    monitor = get_whale_monitor()
    if not monitor:
        notifier = DiscordNotifier()
        monitor = WhaleMonitor(notifier)
        set_whale_monitor(monitor)
    
    enabled = action.lower() in ["on", "enable", "활성화"]
    monitor.toggle_exchange(exchange, enabled)
    
    status_emoji = "✅" if enabled else "❌"
    status_text = "활성화" if enabled else "비활성화"
    
    embed = discord.Embed(
        title=f"🐋 거래소 {status_text}",
        description=f"{status_emoji} **{exchange}** 고래 알람 {status_text}됨",
        color=discord.Color.green() if enabled else discord.Color.orange()
    )
    embed.set_footer(text="변경사항은 봇 재시작 후 적용됩니다")
    
    await ctx.send(embed=embed)


# ============================================================
# Volume Spike Alert Commands
# ============================================================

@bot.command(name="거래량알람", aliases=["volume"])
async def volume_alert_toggle(ctx, action: str = None):
    """Enable/disable volume spike alerts"""
    if not action:
        await ctx.send("❌ 사용법: `!거래량알람 on` / `!거래량알람 off` / `!거래량알람 상태`")
        return
    
    from monitors.volume_monitor import get_volume_monitor, set_volume_monitor, VolumeMonitor
    from notifier import DiscordNotifier
    
    monitor = get_volume_monitor()
    
    if action.lower() in ["on", "활성화", "enable"]:
        if not monitor:
            notifier = DiscordNotifier()
            monitor = VolumeMonitor(notifier)
            set_volume_monitor(monitor)
        
        monitor.enable()
        
        embed = discord.Embed(title="📊 거래량 알람 활성화", color=discord.Color.blue())
        embed.add_field(name="모니터링", value=", ".join(monitor.symbols), inline=True)
        embed.add_field(name="임계값", value=f"{monitor.threshold_percent}%", inline=True)
        embed.set_footer(text="임계값 변경: !거래량임계값 200")
        
        await ctx.send(embed=embed)
        
    elif action.lower() in ["off", "비활성화", "disable"]:
        if monitor:
            monitor.disable()
        await ctx.send("📊 거래량 알람 비활성화됨")
        
    else:  # status
        if not monitor:
            await ctx.send("📊 거래량 알람이 설정되지 않았습니다.")
            return
        
        status = monitor.get_status()
        
        embed = discord.Embed(
            title="📊 거래량 알람 상태",
            color=discord.Color.blue() if status["enabled"] else discord.Color.gray()
        )
        embed.add_field(name="상태", value="🟢 활성화" if status["enabled"] else "🔴 비활성화", inline=True)
        embed.add_field(name="모니터링", value=", ".join(status["symbols"]), inline=True)
        embed.add_field(name="임계값", value=f"{status['threshold_percent']}%", inline=True)
        
        # Show average volumes
        if status["avg_volumes"]:
            avg_info = []
            for symbol, vol in status["avg_volumes"].items():
                avg_info.append(f"{symbol}: {vol:.0f}")
            embed.add_field(name="4시간 평균 거래량", value="\n".join(avg_info), inline=False)
        
        await ctx.send(embed=embed)


@bot.command(name="거래량임계값")
async def set_volume_threshold(ctx, percent: int = None):
    """Set volume spike threshold percentage"""
    if not percent:
        await ctx.send("❌ 사용법: `!거래량임계값 200` (200% = 2배)")
        return
    
    if percent < 100 or percent > 1000:
        await ctx.send("❌ 임계값은 100%~1000% 사이여야 합니다.")
        return
    
    from monitors.volume_monitor import get_volume_monitor, set_volume_monitor, VolumeMonitor
    from notifier import DiscordNotifier
    
    monitor = get_volume_monitor()
    if not monitor:
        notifier = DiscordNotifier()
        monitor = VolumeMonitor(notifier)
        set_volume_monitor(monitor)
    
    monitor.set_threshold(percent)
    
    embed = discord.Embed(title="📊 거래량 임계값 설정", color=discord.Color.green())
    embed.add_field(name="임계값", value=f"{percent}%", inline=True)
    embed.add_field(name="의미", value=f"평균 대비 {percent/100:.1f}배", inline=True)
    
    await ctx.send(embed=embed)



def run_bot():
    """Run the Discord bot"""
    if not DISCORD_BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN not set in .env file")
        raise ValueError("DISCORD_BOT_TOKEN is required")
    
    logger.info("Starting Discord bot...")
    bot.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    run_bot()

