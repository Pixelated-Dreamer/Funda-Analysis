import streamlit as st
import streamlit.components.v1 as components
from yahooquery import Ticker
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

st.set_page_config(layout="wide")
st.header("📊 Fund Analyzer")
st.subheader("dig into any company's fundamentals, no suit required 😄")

ticker_input = st.text_input("🔍 enter a ticker symbol", placeholder="e.g. AAPL, TSLA, MSFT").upper().strip()
year_input = datetime.now().year

def fmt(val, prefix="$", suffix=""):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    try:
        val = float(val)
        if abs(val) >= 1e9:
            return f"{prefix}{val/1e9:.2f}B{suffix}"
        elif abs(val) >= 1e6:
            return f"{prefix}{val/1e6:.2f}M{suffix}"
        return f"{prefix}{val:,.0f}{suffix}"
    except:
        return "N/A"

def safe_val(df, col):
    try:
        if df is None or df.empty:
            return None
        if col not in df.columns:
            return None
        val = df[col].iloc[0]
        return float(val) if pd.notna(val) else None
    except:
        return None

def score_label(score):
    if score >= 85:
        return "🏆 Elite", "#00C896"
    elif score >= 70:
        return "✅ Strong", "#4CAF50"
    elif score >= 55:
        return "👍 Decent", "#FFC107"
    elif score >= 40:
        return "⚠️ Weak", "#FF9800"
    else:
        return "🚨 Risky", "#FF4B4B"

def calculate_score(equity_ratio, npm, dcf_value, current_price, growth_rate):
    score = 0
    breakdown = []

    if equity_ratio is not None:
        if equity_ratio >= 50:
            score += 25
            breakdown.append(("Equity Ratio", 25, 25, "Godly 🤩"))
        elif equity_ratio >= 30:
            score += 20
            breakdown.append(("Equity Ratio", 20, 25, "Great 💪"))
        elif equity_ratio >= 20:
            score += 13
            breakdown.append(("Equity Ratio", 13, 25, "Fine 👌"))
        else:
            score += 5
            breakdown.append(("Equity Ratio", 5, 25, "Weak 😬"))
    else:
        breakdown.append(("Equity Ratio", 0, 25, "N/A"))

    if npm is not None:
        if npm >= 25:
            score += 25
            breakdown.append(("Profit Margin", 25, 25, "Godly 🤩"))
        elif npm >= 15:
            score += 20
            breakdown.append(("Profit Margin", 20, 25, "Very Great 🔥"))
        elif npm >= 10:
            score += 13
            breakdown.append(("Profit Margin", 13, 25, "Average 😐"))
        else:
            score += 5
            breakdown.append(("Profit Margin", 5, 25, "Bad 😓"))
    else:
        breakdown.append(("Profit Margin", 0, 25, "N/A"))

    if dcf_value is not None and current_price is not None and dcf_value > 0:
        margin = (dcf_value - current_price) / dcf_value
        if margin >= 0.3:
            score += 25
            breakdown.append(("DCF Valuation", 25, 25, "Very Undervalued 💎"))
        elif margin >= 0.1:
            score += 18
            breakdown.append(("DCF Valuation", 18, 25, "Slightly Undervalued 📈"))
        elif margin >= -0.1:
            score += 10
            breakdown.append(("DCF Valuation", 10, 25, "Fairly Valued 🤝"))
        else:
            score += 3
            breakdown.append(("DCF Valuation", 3, 25, "Overvalued 📉"))
    else:
        breakdown.append(("DCF Valuation", 0, 25, "N/A"))

    if growth_rate is not None:
        if growth_rate >= 0.20:
            score += 25
            breakdown.append(("Profit Growth", 25, 25, "Rocket Ship 🚀"))
        elif growth_rate >= 0.10:
            score += 20
            breakdown.append(("Profit Growth", 20, 25, "Solid Growth 📊"))
        elif growth_rate >= 0:
            score += 13
            breakdown.append(("Profit Growth", 13, 25, "Slow & Steady 🐢"))
        else:
            score += 3
            breakdown.append(("Profit Growth", 3, 25, "Shrinking 😬"))
    else:
        breakdown.append(("Profit Growth", 0, 25, "N/A"))

    return score, breakdown

@st.cache_data(ttl=600)
def get_data(symbol, year):
    t = Ticker(symbol)

    def process_df(raw):
        if not isinstance(raw, pd.DataFrame) or raw.empty:
            return None
        df = raw.reset_index()
        if 'symbol' in df.columns:
            df = df[df['symbol'] == symbol]
        if 'periodType' in df.columns:
            df = df[df['periodType'] == '12M']
        if df.empty:
            return None
        df['asOfDate'] = pd.to_datetime(df['asOfDate'])
        matches = df[df['asOfDate'].dt.year == year]
        if matches.empty:
            matches = df.sort_values('asOfDate', ascending=False).head(1)
        return matches.reset_index(drop=True)

    inc = process_df(t.income_statement(frequency='a'))
    bal = process_df(t.balance_sheet(frequency='a'))
    cf  = process_df(t.cash_flow(frequency='a'))

    return inc, bal, cf, t.asset_profile, t.summary_detail, t.price

@st.cache_data(ttl=600)
def get_chart_data(symbol, period, interval):
    t = Ticker(symbol)
    hist = t.history(period=period, interval=interval)
    if isinstance(hist, pd.DataFrame) and not hist.empty:
        hist = hist.reset_index()
        if 'date' in hist.columns:
            hist['date'] = pd.to_datetime(hist['date'])
        elif 'Datetime' in hist.columns:
            hist = hist.rename(columns={'Datetime': 'date'})
        return hist
    return pd.DataFrame()

@st.cache_data(ttl=600)
def get_historical_income(symbol):
    t = Ticker(symbol)
    raw = t.income_statement(frequency='a')
    if not isinstance(raw, pd.DataFrame) or raw.empty:
        return pd.DataFrame()
    df = raw.reset_index()
    if 'symbol' in df.columns:
        df = df[df['symbol'] == symbol]
    if 'periodType' in df.columns:
        df = df[df['periodType'] == '12M']
    df['asOfDate'] = pd.to_datetime(df['asOfDate'])
    df = df.sort_values('asOfDate')
    df['year'] = df['asOfDate'].dt.year
    cols = ['year']
    if 'TotalRevenue' in df.columns:
        cols.append('TotalRevenue')
    if 'NetIncome' in df.columns:
        cols.append('NetIncome')
    return df[cols].reset_index(drop=True)

def render_profit_sales_chart(symbol, hist_df):
    if hist_df.empty:
        st.warning("no historical income data available 😔")
        return
    fig = go.Figure()
    if 'TotalRevenue' in hist_df.columns:
        fig.add_trace(go.Bar(
            x=hist_df['year'], y=hist_df['TotalRevenue'],
            name='Revenue',
            marker_color='rgba(100,149,237,0.7)',
        ))
    if 'NetIncome' in hist_df.columns:
        fig.add_trace(go.Scatter(
            x=hist_df['year'], y=hist_df['NetIncome'],
            name='Net Income',
            mode='lines+markers',
            line=dict(color='#00C896', width=2),
            marker=dict(size=7)
        ))
    fig.update_layout(
        title=dict(text=f"{symbol} — Revenue & Net Income (Annual)", font=dict(size=15)),
        xaxis=dict(title="Year", showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='white', tickmode='linear'),
        yaxis=dict(title="USD", showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='white'),
        plot_bgcolor='#0E1117', paper_bgcolor='#0E1117',
        font=dict(color='white'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=350, margin=dict(l=10, r=10, t=50, b=10),
        barmode='overlay'
    )
    st.plotly_chart(fig, use_container_width=True)

def render_stock_chart(symbol):
    st.subheader(f"📈 {symbol} Stock Chart")
    chart_height = st.slider("chart height", min_value=300, max_value=1200, value=600, step=50, key="tv_height")
    widget_html = f"""
    <div class="tradingview-widget-container" style="height:{chart_height}px;width:100%">
      <div id="tv_chart_{symbol}"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "{symbol}",
        "interval": "D",
        "timezone": "America/New_York",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#131722",
        "enable_publishing": false,
        "withdateranges": true,
        "hide_side_toolbar": false,
        "allow_symbol_change": false,
        "studies": ["MASimple@tv-basicstudies"],
        "container_id": "tv_chart_{symbol}"
      }});
      </script>
    </div>
    """
    components.html(widget_html, height=chart_height + 20)

def run_ai_analysis(ticker: str, metrics: dict, api_key: str) -> str:
    try:
        import anthropic
    except ImportError:
        return "Install the `anthropic` package to enable AI analysis."

    client = anthropic.Anthropic(api_key=api_key)

    def _fmt_m(v, prefix="", suffix="", scale=1.0, decimals=2):
        if v is None:
            return "N/A"
        try:
            import math
            fv = float(v) * scale
            if math.isnan(fv):
                return "N/A"
            return f"{prefix}{fv:.{decimals}f}{suffix}"
        except Exception:
            return "N/A"

    mc = metrics.get("market_cap")
    ni = metrics.get("net_income")
    fcf = metrics.get("fcf")

    prompt = (
        f"You are a sharp financial analyst. Analyze {ticker} based on the following data and give a concise, opinionated assessment.\n\n"
        f"Market cap: {'${:.1f}B'.format(mc/1e9) if mc else 'N/A'} | "
        f"Stock price: {_fmt_m(metrics.get('current_price'), prefix='$')} | "
        f"PE: {_fmt_m(metrics.get('pe_ratio'), decimals=1)} | "
        f"PEG: {_fmt_m(metrics.get('peg_ratio'))}\n"
        f"Revenue: {'${:.1f}B'.format(metrics['revenue']/1e9) if metrics.get('revenue') else 'N/A'} | "
        f"Net income: {'${:.2f}B'.format(ni/1e9) if ni else 'N/A'} | "
        f"NI/MC: {_fmt_m((ni/mc*100) if ni and mc and mc>0 else None, suffix='%', decimals=2)}\n"
        f"FCF: {'${:.2f}B'.format(fcf/1e9) if fcf else 'N/A'} | "
        f"FCF yield: {_fmt_m((fcf/mc*100) if fcf and mc and mc>0 else None, suffix='%')}\n"
        f"Profit margin: {_fmt_m(metrics.get('npm'), suffix='%', decimals=1)} | "
        f"Equity ratio: {_fmt_m(metrics.get('equity_ratio'), suffix='%', decimals=1)} | "
        f"Revenue growth (YoY): {_fmt_m(metrics.get('revenue_growth'), suffix='%', decimals=1)}\n"
        f"DCF value/share: {_fmt_m(metrics.get('dcf_value'), prefix='$')} | "
        f"Current price: {_fmt_m(metrics.get('current_price'), prefix='$')} | "
        f"Profit growth (YoY): {_fmt_m(metrics.get('growth_rate'), suffix='%', scale=100, decimals=1)}\n"
        f"Equity score: {metrics.get('score', 'N/A')}/100\n\n"
        "Write 5–15 lines of flowing analytical prose. No bullet points, no headers. Cover:\n"
        "- Valuation: is it cheap, fair, or stretched? Use PE, FCF yield, NI/MC as hard anchors\n"
        "- Business quality: profit margins, equity ratio, growth trajectory\n"
        "- If fundamentals look weak but the stock trades at a premium, search for the investor narrative driving it\n"
        "- Give a clear, opinionated overall verdict: overvalued, fairly valued, or undervalued, and why\n"
        "Use web search to find recent news or catalysts. Be specific, not generic."
    )

    def _call(use_search: bool) -> str:
        msgs = [{"role": "user", "content": prompt}]
        tools = [{"type": "web_search_20250305", "name": "web_search"}] if use_search else []
        for _ in range(4):
            kwargs = {"model": "claude-haiku-4-5", "max_tokens": 800, "messages": msgs}
            if tools:
                kwargs["tools"] = tools
            resp = client.messages.create(**kwargs)
            texts = [b.text for b in resp.content if hasattr(b, "text") and b.text]
            if resp.stop_reason in ("end_turn", "stop_sequence"):
                return "\n".join(texts).strip()
            if resp.stop_reason == "pause_turn":
                msgs.append({"role": "assistant", "content": resp.content})
                continue
            if texts:
                return "\n".join(texts).strip()
        return "\n".join([b.text for b in resp.content if hasattr(b, "text") and b.text]).strip()

    try:
        return _call(use_search=True)
    except Exception as e:
        err = str(e)
        if "web_search" in err.lower() or "400" in err or "422" in err:
            try:
                return _call(use_search=False)
            except Exception as e2:
                return f"AI analysis failed: {e2}"
        return f"AI analysis failed: {err}"


if st.button("Run Analysis 🔍"):
    if not ticker_input:
        st.warning("bro you forgot to type a ticker 💀")
    else:
        try:
            with st.spinner(f"give me a sec, im asking yahoo finance nicely about {ticker_input} 🙏"):
                inc, bal, cf, profile, summary, price_data = get_data(ticker_input, year_input)
                hist_income = get_historical_income(ticker_input)

            st.toast(f"found {ticker_input}! let's see what we're working with 👀")

            prof = profile.get(ticker_input, {}) if isinstance(profile, dict) else {}
            summ = summary.get(ticker_input, {}) if isinstance(summary, dict) else {}
            pr   = price_data.get(ticker_input, {}) if isinstance(price_data, dict) else {}

            description   = prof.get("longBusinessSummary", "no description available, they're mysterious like that 🕵️")
            market_cap    = summ.get("marketCap")
            pe_ratio      = summ.get("trailingPE") or summ.get("forwardPE")
            peg_ratio     = summ.get("pegRatio")
            current_price = pr.get("regularMarketPrice")
            shares        = (pr.get("sharesOutstanding") or
                             summ.get("sharesOutstanding") or
                             prof.get("sharesOutstanding"))

            revenue_growth = None
            if not hist_income.empty and 'TotalRevenue' in hist_income.columns and len(hist_income) >= 2:
                rev_curr = hist_income['TotalRevenue'].iloc[-1]
                rev_prev = hist_income['TotalRevenue'].iloc[-2]
                if pd.notna(rev_curr) and pd.notna(rev_prev) and rev_prev != 0:
                    revenue_growth = (float(rev_curr) - float(rev_prev)) / abs(float(rev_prev)) * 100

            if inc is None or bal is None:
                st.error(f"yeah.. **{ticker_input}** doesn't exist bro 💀 double check the ticker symbol")
                st.stop()

            # Income Statement
            revenue       = safe_val(inc, "TotalRevenue")
            cost_of_rev   = safe_val(inc, "CostOfRevenue")
            gross_profit  = safe_val(inc, "GrossProfit")
            op_expense    = safe_val(inc, "OperatingExpense")
            op_income     = safe_val(inc, "OperatingIncome")
            pretax_income = safe_val(inc, "PretaxIncome")
            tax           = safe_val(inc, "TaxProvision")
            net_income    = safe_val(inc, "NetIncome")

            # Balance Sheet
            total_assets = safe_val(bal, "TotalAssets")
            total_liab   = safe_val(bal, "TotalLiabilitiesNetMinorityInterest")
            equity       = safe_val(bal, "StockholdersEquity")

            # Cash Flow
            op_cf = safe_val(cf, "OperatingCashFlow")
            capex = safe_val(cf, "CapitalExpenditure")
            fcf   = safe_val(cf, "FreeCashFlow")
            if fcf is None and op_cf is not None and capex is not None:
                fcf = op_cf + capex

            # DCF growth rate
            growth_rate = None
            try:
                with st.spinner("crunching the DCF numbers, this is the hard part 🧮"):
                    t2 = Ticker(ticker_input)
                    inc_all = t2.income_statement(frequency='a')
                    if isinstance(inc_all, pd.DataFrame) and not inc_all.empty and 'NetIncome' in inc_all.columns:
                        inc_all = inc_all.reset_index()
                        if 'symbol' in inc_all.columns:
                            inc_all = inc_all[inc_all['symbol'] == ticker_input]
                        if 'periodType' in inc_all.columns:
                            inc_all = inc_all[inc_all['periodType'] == '12M']
                        inc_all['asOfDate'] = pd.to_datetime(inc_all['asOfDate'])
                        inc_all = inc_all.sort_values('asOfDate', ascending=False)
                        if len(inc_all) >= 2:
                            ni_curr = float(inc_all['NetIncome'].iloc[0])
                            ni_prev = float(inc_all['NetIncome'].iloc[1])
                            if ni_prev and ni_prev != 0:
                                growth_rate = (ni_curr - ni_prev) / abs(ni_prev)
            except:
                growth_rate = None

            dcf_value = None
            if fcf is not None and growth_rate is not None:
                discount_rate   = 0.10
                terminal_growth = 0.03
                projected_fcf   = fcf
                total_pv        = 0
                for i in range(1, 6):
                    projected_fcf *= (1 + growth_rate)
                    total_pv += projected_fcf / ((1 + discount_rate) ** i)
                terminal_value = (projected_fcf * (1 + terminal_growth)) / (discount_rate - terminal_growth)
                total_pv += terminal_value / ((1 + discount_rate) ** 5)
                if shares and shares > 0:
                    dcf_value = total_pv / shares
                elif market_cap and current_price and current_price > 0:
                    shares = market_cap / current_price
                    dcf_value = total_pv / shares

            equity_ratio = (equity / total_assets * 100) if equity and total_assets else None
            npm = (net_income / revenue * 100) if net_income and revenue else None

            # ---- SCORE SUMMARY ----
            score, breakdown = calculate_score(equity_ratio, npm, dcf_value, current_price, growth_rate)
            label, label_color = score_label(score)

            st.markdown("---")
            st.subheader("🎯 Overall Score")

            scorecols = st.columns(4)
            for i, (metric, pts, max_pts, note) in enumerate(breakdown):
                with scorecols[i]:
                    pct = pts / max_pts
                    color = "#00C896" if pct >= 0.8 else "#FFC107" if pct >= 0.5 else "#FF4B4B"
                    st.markdown(f"""
                    <div style="background:#1a1a2e; border-radius:12px; padding:0.8rem; text-align:center; border:1px solid {color}">
                        <div style="font-size:0.75rem; color:rgba(255,255,255,0.5)">{metric}</div>
                        <div style="font-size:1.4rem; color:{color}; font-weight:700">{pts}/{max_pts}</div>
                        <div style="font-size:0.7rem; color:rgba(255,255,255,0.6)">{note}</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown(f"### final verdict: **{label}** — {score}/100")

            if score >= 85:
                st.success("this company is built different fr 🏆 almost too good to be true")
            elif score >= 70:
                st.success("solid company, your accountant would approve 👍")
            elif score >= 55:
                st.warning("it's giving... average. not bad not great 🤷")
            elif score >= 40:
                st.warning("oof, some red flags here. proceed with caution 🚩")
            else:
                st.error("bro this company is struggling. maybe look elsewhere 💀")

            # ---- AI ANALYSIS ----
            st.markdown("---")
            st.subheader("🤖 AI Analysis")

            ai_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not ai_key:
                try:
                    ai_key = st.secrets["ANTHROPIC_API_KEY"]
                except Exception:
                    pass

            if not ai_key:
                st.caption("Add `ANTHROPIC_API_KEY` to your environment or Streamlit secrets to enable AI analysis.")
                ai_key = st.text_input("Anthropic API Key", type="password", key="anth_key_input")

            if ai_key:
                ai_cache_key = f"ai_{ticker_input}_{year_input}"
                _, col_refresh = st.columns([10, 1])
                with col_refresh:
                    if st.button("↺", key="refresh_ai"):
                        if ai_cache_key in st.session_state:
                            del st.session_state[ai_cache_key]

                if ai_cache_key not in st.session_state:
                    with st.spinner("Claude is researching and analyzing..."):
                        st.session_state[ai_cache_key] = run_ai_analysis(
                            ticker_input,
                            {
                                "market_cap": market_cap,
                                "current_price": current_price,
                                "pe_ratio": pe_ratio,
                                "peg_ratio": peg_ratio,
                                "revenue": revenue,
                                "net_income": net_income,
                                "fcf": fcf,
                                "npm": npm,
                                "equity_ratio": equity_ratio,
                                "revenue_growth": revenue_growth,
                                "dcf_value": dcf_value,
                                "growth_rate": growth_rate,
                                "score": score,
                            },
                            ai_key,
                        )

                analysis_text = st.session_state[ai_cache_key].replace("\n", "<br>")
                st.markdown(
                    f"<div style='background:#1a1a2e;border-left:3px solid #4f8ef7;"
                    f"padding:16px 20px;border-radius:6px;color:#e0e0e0;"
                    f"font-size:0.95rem;line-height:1.7;'>"
                    f"{analysis_text}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            st.markdown("---")

            # ---- 2 COLUMN LAYOUT ----
            left_col, right_col = st.columns(2)

            # ======= LEFT COLUMN =======
            with left_col:

                # --- Quick Stats ---
                st.subheader("📌 Quick Stats")
                st.code(f"Market Cap:      {fmt(market_cap)}")
                st.code(f"Stock Price:     {f'${current_price:.2f}' if current_price else 'N/A'}")
                st.code(f"PE Ratio:        {f'{pe_ratio:.2f}' if pe_ratio else 'N/A'}")
                st.code(f"PEG Ratio:       {f'{peg_ratio:.2f}' if peg_ratio else 'N/A'}")
                st.code(f"Revenue Growth:  {f'{revenue_growth:+.1f}%' if revenue_growth is not None else 'N/A'}")
                st.text(description)

                # --- Profit & Sales Chart ---
                st.subheader("📊 Revenue & Net Income")
                render_profit_sales_chart(ticker_input, hist_income)

                # --- Balance Sheet ---
                st.subheader("🏦 Balance Sheet")
                st.code(f"Assets:      {fmt(total_assets)}\nLiabilities: {fmt(total_liab)}\nEquity:      {fmt(equity)}")

                if equity_ratio is not None:
                    st.text(f"equity ratio: {equity_ratio:.1f}%")
                    st.text("benchmarks → 50%+: godly 🤩  |  30–50%: great 💪  |  20–30%: fine 👌  |  below 20%: yikes 😬")
                    if equity_ratio >= 20:
                        st.success(f"equity ratio is {equity_ratio:.1f}% — not bad at all 💪")
                    else:
                        st.error(f"equity ratio is {equity_ratio:.1f}% — that's a bit concerning ngl 😬")

            # ======= RIGHT COLUMN =======
            with right_col:

                # --- DCF Value ---
                st.subheader("💰 DCF Value")
                st.code(f"Profit growth (YoY): {growth_rate*100:.1f}%" if growth_rate is not None else "Profit growth: N/A")
                st.code(f"Equity:              {fmt(equity)}")
                st.code(f"Net Income:          {fmt(net_income)}")

                if dcf_value is not None and current_price is not None:
                    if dcf_value < 0:
                        dcf_value = 0
                    st.text(f"DCF Value per share: ${dcf_value:.2f}")
                    if current_price < dcf_value:
                        st.success(f"undervalued!! go go go 🚀 (price: ${current_price:.2f} vs dcf: ${dcf_value:.2f})")
                    else:
                        st.error(f"overvalued 😬 you'd be overpaying rn (price: ${current_price:.2f} vs dcf: ${dcf_value:.2f})")
                    if growth_rate is not None and growth_rate < 0:
                        st.caption(f"⚠️ heads up: this company shrank {abs(growth_rate)*100:.1f}% last year so the dcf is a bit cooked lol 🧂 don't bet the house on this one")
                else:
                    st.warning(f"couldn't calculate dcf, yahoo finance is being stingy 😒 — FCF: {fmt(fcf)}, Growth: {f'{growth_rate*100:.1f}%' if growth_rate is not None else 'N/A'}, Price: {current_price}")

                # --- Income Statement ---
                st.subheader("📋 Income Statement")
                st.text(f"Revenue:           {fmt(revenue)}")
                st.error(f"Cost of Revenue:   {fmt(cost_of_rev)}")
                st.text(f"Gross Profit:      {fmt(gross_profit)}")
                st.error(f"Operating Expense: {fmt(op_expense)}")
                st.text(f"Operating Income:  {fmt(op_income)}")
                st.text(f"Pretax Income:     {fmt(pretax_income)}")
                st.error(f"Tax:               {fmt(tax)} (the government always eats 🍽️)")
                st.success(f"Net Income:        {fmt(net_income)} (what actually matters 💰)")

                if npm is not None:
                    st.text("benchmarks → 25–40%: godly 🤩  |  15–25%: great 🔥  |  10–15%: average 😐  |  below 10%: bad 😓")
                    if npm >= 13:
                        st.success(f"net profit margin is {npm:.1f}% 🔥 they're keeping their money!")
                    else:
                        st.error(f"net profit margin is {npm:.1f}% 😓 most of the revenue is flying out the window")

            # ---- Chart ----
            st.divider()
            render_stock_chart(ticker_input)

            # ---- TAILWINDS & HEADWINDS ----
            st.markdown("---")
            st.subheader("🌬️ Tailwinds & Headwinds")

            tw_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not tw_key:
                try:
                    tw_key = st.secrets["ANTHROPIC_API_KEY"]
                except Exception:
                    pass
            if not tw_key and "anth_key_input" in st.session_state:
                tw_key = st.session_state.get("anth_key_input", "")

            if tw_key:
                tw_cache_key = f"tw_{ticker_input}_{year_input}"
                _, tw_col_refresh = st.columns([10, 1])
                with tw_col_refresh:
                    if st.button("↺", key="refresh_tw"):
                        if tw_cache_key in st.session_state:
                            del st.session_state[tw_cache_key]

                if tw_cache_key not in st.session_state:
                    with st.spinner("researching tailwinds and headwinds..."):
                        try:
                            import anthropic
                            tw_client = anthropic.Anthropic(api_key=tw_key)
                            tw_prompt = (
                                f"You are a financial analyst. For {ticker_input}, identify the key tailwinds (positive forces) "
                                f"and headwinds (negative forces/risks) affecting the business right now.\n\n"
                                f"Use web search to find the most current and relevant factors — macro trends, sector dynamics, "
                                f"competitive pressures, regulatory changes, product cycles, geopolitical exposure, etc.\n\n"
                                f"Format your response as two clear sections:\n"
                                f"TAILWINDS: (3–5 specific tailwinds, each 1–2 sentences)\n"
                                f"HEADWINDS: (3–5 specific headwinds/risks, each 1–2 sentences)\n\n"
                                f"Be specific and current. No generic filler."
                            )
                            tw_msgs = [{"role": "user", "content": tw_prompt}]
                            tw_tools = [{"type": "web_search_20250305", "name": "web_search"}]
                            tw_result = ""
                            for _ in range(4):
                                tw_kwargs = {"model": "claude-haiku-4-5", "max_tokens": 800, "messages": tw_msgs, "tools": tw_tools}
                                tw_resp = tw_client.messages.create(**tw_kwargs)
                                tw_texts = [b.text for b in tw_resp.content if hasattr(b, "text") and b.text]
                                if tw_resp.stop_reason in ("end_turn", "stop_sequence"):
                                    tw_result = "\n".join(tw_texts).strip()
                                    break
                                if tw_resp.stop_reason == "pause_turn":
                                    tw_msgs.append({"role": "assistant", "content": tw_resp.content})
                                    continue
                                if tw_texts:
                                    tw_result = "\n".join(tw_texts).strip()
                                    break
                            st.session_state[tw_cache_key] = tw_result or "Could not generate tailwinds/headwinds."
                        except Exception as e_tw:
                            st.session_state[tw_cache_key] = f"Could not load tailwinds/headwinds: {e_tw}"

                tw_text = st.session_state.get(tw_cache_key, "")
                if tw_text:
                    tw_col, hw_col = st.columns(2)
                    tailwinds_part = ""
                    headwinds_part = ""
                    if "HEADWINDS:" in tw_text:
                        parts = tw_text.split("HEADWINDS:", 1)
                        tailwinds_part = parts[0].replace("TAILWINDS:", "").strip()
                        headwinds_part = parts[1].strip()
                    else:
                        tailwinds_part = tw_text

                    with tw_col:
                        st.markdown(
                            f"<div style='background:#0d1f12;border-left:3px solid #00C896;"
                            f"padding:14px 18px;border-radius:6px;color:#e0e0e0;"
                            f"font-size:0.9rem;line-height:1.7;'>"
                            f"<div style='color:#00C896;font-weight:700;margin-bottom:8px;font-size:1rem;'>Tailwinds</div>"
                            f"{tailwinds_part.replace(chr(10), '<br>')}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    with hw_col:
                        st.markdown(
                            f"<div style='background:#1f0d0d;border-left:3px solid #FF4B4B;"
                            f"padding:14px 18px;border-radius:6px;color:#e0e0e0;"
                            f"font-size:0.9rem;line-height:1.7;'>"
                            f"<div style='color:#FF4B4B;font-weight:700;margin-bottom:8px;font-size:1rem;'>Headwinds</div>"
                            f"{headwinds_part.replace(chr(10), '<br>')}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
            else:
                st.caption("API key required for Tailwinds & Headwinds analysis.")

            st.markdown("---")
            st.caption("made with 💜 by Nevaan Kant (xotic)")

        except Exception as e:
            st.error(f"yahoo finance said no 😭 error: {e}")

if ticker_input:
    st_autorefresh(interval=600_000, key="chart_refresh")
