import streamlit as st
from yahooquery import Ticker
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

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
    col1, col2 = st.columns([3, 1])
    with col1:
        period = st.selectbox("Time Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"], index=2, key="chart_period")
    interval_map = {
        "1d": "5m", "5d": "15m", "1mo": "1h",
        "3mo": "1d", "6mo": "1d", "1y": "1wk",
        "2y": "1wk", "5y": "1mo"
    }
    interval = interval_map[period]

    hist = get_chart_data(symbol, period, interval)
    if hist.empty:
        st.error("chart said no 😭 no data available")
        return

    date_col = 'date' if 'date' in hist.columns else hist.columns[0]

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=hist[date_col],
        open=hist['open'], high=hist['high'],
        low=hist['low'], close=hist['close'],
        name="Price",
        increasing_line_color='#00C896',
        decreasing_line_color='#FF4B4B'
    ))
    fig.add_trace(go.Bar(
        x=hist[date_col], y=hist['volume'],
        name='Volume',
        marker_color='rgba(100,149,237,0.3)',
        yaxis='y2'
    ))
    hist['MA20'] = hist['close'].rolling(window=20).mean()
    fig.add_trace(go.Scatter(
        x=hist[date_col], y=hist['MA20'],
        mode='lines', name='MA20',
        line=dict(color='orange', width=1.5, dash='dot')
    ))

    first_close = hist['close'].iloc[0]
    last_close  = hist['close'].iloc[-1]
    pct_change  = ((last_close - first_close) / first_close) * 100
    color = "#00C896" if pct_change >= 0 else "#FF4B4B"

    fig.update_layout(
        title=dict(text=f"{symbol}  <span style='color:{color}'>{'+' if pct_change >= 0 else ''}{pct_change:.2f}%</span>", font=dict(size=18)),
        xaxis=dict(rangeslider=dict(visible=False), showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='white'),
        yaxis=dict(title="Price (USD)", showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='white', side='right'),
        yaxis2=dict(title="Volume", overlaying='y', side='left', showgrid=False, color='rgba(100,149,237,0.5)'),
        plot_bgcolor='#0E1117', paper_bgcolor='#0E1117',
        font=dict(color='white'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=500, margin=dict(l=10, r=10, t=60, b=10)
    )

    st.plotly_chart(fig, width='stretch')
    st.caption(f"🕐 last updated: {datetime.now().strftime('%H:%M:%S')} — refreshes every 10 mins (yahoo finance needs its beauty sleep 😴)")

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
            current_price = pr.get("regularMarketPrice")
            shares        = (pr.get("sharesOutstanding") or
                             summ.get("sharesOutstanding") or
                             prof.get("sharesOutstanding"))

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

            st.markdown("---")

            # ---- 2 COLUMN LAYOUT ----
            left_col, right_col = st.columns(2)

            # ======= LEFT COLUMN =======
            with left_col:

                # --- Quick Stats ---
                st.subheader("📌 Quick Stats")
                st.code(f"Market Cap:   {fmt(market_cap)}")
                st.code(f"PE Ratio:     {f'{pe_ratio:.2f}' if pe_ratio else 'N/A'}")
                st.code(f"Stock Price:  {f'${current_price:.2f}' if current_price else 'N/A'}")
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
            with st.spinner("loading the chart, almost done i promise 🎨"):
                render_stock_chart(ticker_input)

            st.markdown("---")
            st.caption("made with 💜 by Nevaan Kant (xotic)")

        except Exception as e:
            st.error(f"yahoo finance said no 😭 error: {e}")

if ticker_input:
    st_autorefresh(interval=600_000, key="chart_refresh")
