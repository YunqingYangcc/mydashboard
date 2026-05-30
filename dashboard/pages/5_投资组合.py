"""投资组合 - 交易记录、持仓管理、收益曲线"""
import sys
from pathlib import Path
from datetime import datetime, date
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path: sys.path.insert(0, str(ROOT_DIR))

from dashboard.components import init_page_style, render_signature
from kb.storage import (
    init_db, insert_trade, list_trades, delete_trade, update_trade,
    upsert_position, get_position, list_positions, update_position_price,
    delete_position, calculate_position_weights,
    insert_portfolio_history, list_portfolio_history, get_latest_portfolio_value,
    get_financial, list_financials
)
from kb.market_constants import TARGET_STOCKS, SYMBOL_MAP
from kb.data_fetcher import get_quotes_from_db

init_db()
init_page_style()

tab1, tab2, tab3, tab4 = st.tabs(["📝 交易记录", "📊 持仓管理", "📈 收益曲线", "💰 财务数据"])

with tab1:
    st.subheader("📝 交易记录")
    
    with st.expander("➕ 新增交易", expanded=False):
        c1, c2 = st.columns([1, 1])
        with c1:
            input_mode = st.radio("输入方式", ["预设标的", "自定义标的"], horizontal=True, key="trade_input_mode")
        with c2:
            if input_mode == "预设标的":
                trade_symbol = st.selectbox(
                    "标的",
                    options=[t["symbol"] for t in TARGET_STOCKS],
                    format_func=lambda x: f"{SYMBOL_MAP.get(x, {}).get('name', x)} ({x})",
                    key="trade_symbol_select"
                )
            else:
                trade_symbol = st.text_input("标的代码", placeholder="如：AAPL、600519", key="trade_symbol_input")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            trade_name = st.text_input("标的名称", placeholder="可选", key="trade_name")
        with c2:
            trade_type = st.selectbox("类型", ["买入", "卖出"], key="trade_type")
        with c3:
            trade_quantity = st.number_input("数量", min_value=0.0, value=100.0, step=100.0, key="trade_quantity")
        with c4:
            trade_price = st.number_input("价格", min_value=0.0, value=100.0, step=0.1, key="trade_price")
        
        c5, c6, c7 = st.columns(3)
        with c5:
            trade_date = st.date_input("日期", value=date.today(), key="trade_date")
        with c6:
            trade_fee = st.number_input("手续费", min_value=0.0, value=0.0, step=1.0, key="trade_fee")
        with c7:
            trade_account = st.text_input("账户", placeholder="如：券商A", key="trade_account")
        
        trade_notes = st.text_area("备注", placeholder="交易理由...", key="trade_notes")
        
        trade_amount = trade_quantity * trade_price
        st.caption(f"成交金额: ¥{trade_amount:,.2f}")
        
        if st.button("保存交易", type="primary", use_container_width=True):
            if not trade_symbol:
                st.error("请输入标的代码")
            else:
                insert_trade({
                    "symbol": trade_symbol,
                    "trade_type": trade_type,
                    "quantity": trade_quantity,
                    "price": trade_price,
                    "amount": trade_amount,
                    "fee": trade_fee,
                    "trade_date": str(trade_date),
                    "account": trade_account or None,
                    "notes": trade_notes or None
                })
                st.success("✅ 交易记录已保存")
                st.rerun()
    
    st.divider()
    
    trades = list_trades(limit=200)
    if not trades:
        st.info("暂无交易记录")
    else:
        st.caption(f"共 {len(trades)} 条记录")
        
        for t in trades:
            symbol = t["symbol"]
            name = SYMBOL_MAP.get(symbol, {}).get("name", symbol)
            trade_type_icon = "🟢" if t["trade_type"] == "买入" else "🔴"
            
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([2, 1.5, 1.5, 1.5, 0.5])
                with c1:
                    st.markdown(f"**{trade_type_icon} {name}** ({symbol})")
                    st.caption(f"{t['trade_date']} | {t.get('account', '-')}")
                with c2:
                    st.metric("数量", f"{t['quantity']:,.0f}")
                with c3:
                    st.metric("价格", f"¥{t['price']:,.2f}")
                with c4:
                    st.metric("金额", f"¥{t['amount']:,.2f}")
                with c5:
                    if st.button("🗑", key=f"del_trade_{t['id']}"):
                        delete_trade(t['id'])
                        st.rerun()
                
                if t.get("notes"):
                    st.caption(f"📝 {t['notes']}")
                st.divider()

with tab2:
    st.subheader("📊 持仓管理")
    
    positions = list_positions()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_value = sum(p.get("market_value", 0) for p in positions) if positions else 0
        st.metric("总市值", f"¥{total_value:,.2f}")
    with col2:
        total_cost = sum(p["quantity"] * p["cost_price"] for p in positions) if positions else 0
        st.metric("总成本", f"¥{total_cost:,.2f}")
    with col3:
        total_pl = total_value - total_cost if total_value > 0 else 0
        pl_color = "normal" if total_pl >= 0 else "inverse"
        st.metric("总盈亏", f"¥{total_pl:,.2f}", delta=f"{total_pl/total_cost*100:.2f}%" if total_cost > 0 else None)
    with col4:
        st.metric("持仓数", f"{len(positions)}")
    
    st.divider()
    
    with st.expander("➕ 新增持仓", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            pos_symbol = st.selectbox(
                "标的",
                options=[t["symbol"] for t in TARGET_STOCKS],
                format_func=lambda x: f"{SYMBOL_MAP.get(x, {}).get('name', x)} ({x})",
                key="pos_symbol"
            )
        with c2:
            pos_quantity = st.number_input("持仓数量", min_value=0.0, value=100.0, step=100.0, key="pos_quantity")
        with c3:
            pos_cost = st.number_input("成本价", min_value=0.0, value=100.0, step=0.1, key="pos_cost")
        
        if st.button("保存持仓", type="primary", use_container_width=True):
            upsert_position(pos_symbol, pos_quantity, pos_cost)
            st.success("✅ 持仓已保存")
            st.rerun()
    
    if not positions:
        st.info("暂无持仓")
    else:
        for p in positions:
            symbol = p["symbol"]
            name = SYMBOL_MAP.get(symbol, {}).get("name", symbol)
            market = SYMBOL_MAP.get(symbol, {}).get("market", "")
            
            c1, c2, c3, c4, c5, c6 = st.columns([2, 1.2, 1.2, 1.2, 1.2, 0.5])
            with c1:
                st.markdown(f"**{name}** ({symbol})")
                st.caption(f"{market}")
            with c2:
                st.metric("数量", f"{p['quantity']:,.0f}")
            with c3:
                st.metric("成本", f"¥{p['cost_price']:,.2f}")
            with c4:
                current = p.get("current_price") or p["cost_price"]
                st.metric("现价", f"¥{current:,.2f}")
            with c5:
                pl = p.get("profit_loss", 0)
                pl_pct = p.get("profit_loss_pct", 0)
                st.metric("盈亏", f"¥{pl:,.2f}", delta=f"{pl_pct:.2f}%")
            with c6:
                if st.button("🗑", key=f"del_pos_{symbol}"):
                    delete_position(symbol)
                    st.rerun()
        
        if st.button("🔄 更新价格", type="secondary"):
            for p in positions:
                symbol = p["symbol"]
                df = get_quotes_from_db(symbol, days=1)
                if df is not None and len(df) > 0:
                    latest_price = df.iloc[-1]["close"]
                    update_position_price(symbol, latest_price)
            calculate_position_weights()
            st.success("✅ 价格已更新")
            st.rerun()

with tab3:
    st.subheader("📈 收益曲线")
    
    positions = list_positions()
    auto_total = float(sum(p.get("market_value", 0) or 0 for p in positions) if positions else 0)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("持仓市值", f"¥{auto_total:,.2f}")
    with c2:
        if st.button("🔄 更新持仓价格", use_container_width=True):
            for p in positions:
                symbol = p["symbol"]
                df = get_quotes_from_db(symbol, days=1)
                if df is not None and len(df) > 0:
                    latest_price = df.iloc[-1]["close"]
                    update_position_price(symbol, latest_price)
            calculate_position_weights()
            st.success("✅ 价格已更新")
            st.rerun()
    
    st.divider()
    
    with st.expander("➕ 记录今日净值", expanded=False):
        st.caption(f"💡 当前持仓市值: ¥{auto_total:,.2f}（可自动填充）")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            record_date = st.date_input("日期", value=date.today(), key="record_date")
        with c2:
            total_value_input = st.number_input("总市值", min_value=0.0, value=auto_total, step=1000.0, key="total_value_input")
        with c3:
            cash_input = st.number_input("现金", min_value=0.0, value=0.0, step=1000.0, key="cash_input")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("保存记录", type="primary", use_container_width=True):
                insert_portfolio_history(str(record_date), total_value_input, cash_input)
                st.success("✅ 净值记录已保存")
                st.rerun()
        with c2:
            if st.button("一键记录今日净值", type="secondary", use_container_width=True):
                insert_portfolio_history(str(date.today()), auto_total, 0)
                st.success("✅ 已记录今日净值")
                st.rerun()
    
    st.divider()
    
    history = list_portfolio_history(days=90)
    
    if not history:
        st.info("暂无净值记录")
    else:
        latest = get_latest_portfolio_value()
        if latest:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("最新净值", f"¥{latest['total_value']:,.2f}")
            with c2:
                st.metric("现金", f"¥{latest.get('cash', 0):,.2f}")
            with c3:
                pl = latest.get("profit_loss")
                if pl is not None:
                    st.metric("日盈亏", f"¥{pl:,.2f}")
            with c4:
                pl_pct = latest.get("profit_loss_pct")
                if pl_pct is not None:
                    st.metric("日涨跌", f"{pl_pct:.2f}%")
        
        st.divider()
        
        import pandas as pd
        df = pd.DataFrame(history)
        df = df.sort_values("record_date")
        
        chart_data = df[["record_date", "total_value"]].set_index("record_date")
        st.line_chart(chart_data)
        
        with st.expander("📋 历史记录"):
            for h in history[:30]:
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.caption(h["record_date"])
                with c2:
                    st.caption(f"¥{h['total_value']:,.2f}")
                with c3:
                    pl = h.get("profit_loss")
                    if pl is not None:
                        st.caption(f"¥{pl:,.2f}")
                with c4:
                    pl_pct = h.get("profit_loss_pct")
                    if pl_pct is not None:
                        st.caption(f"{pl_pct:.2f}%")

with tab4:
    st.subheader("💰 财务数据")
    
    c1, c2 = st.columns([1, 1])
    with c1:
        fin_input_mode = st.radio("输入方式", ["预设标的", "自定义标的"], horizontal=True, key="fin_input_mode")
    with c2:
        if fin_input_mode == "预设标的":
            fin_symbol = st.selectbox(
                "选择标的",
                options=[t["symbol"] for t in TARGET_STOCKS],
                format_func=lambda x: f"{SYMBOL_MAP.get(x, {}).get('name', x)} ({x})",
                key="fin_symbol_select"
            )
        else:
            fin_symbol = st.text_input("标的代码", placeholder="如：AAPL、600519", key="fin_symbol_input")
    
    if fin_symbol:
        fin = get_financial(fin_symbol)
        
        if fin:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("PE", f"{fin.get('pe', 0):.2f}")
            with c2:
                st.metric("PB", f"{fin.get('pb', 0):.2f}")
            with c3:
                st.metric("ROE", f"{fin.get('roe', 0):.2f}%")
            with c4:
                st.metric("股息率", f"{fin.get('dividend_yield', 0):.2f}%")
            
            c5, c6, c7, c8 = st.columns(4)
            with c5:
                st.metric("营收增速", f"{fin.get('revenue_yoy', 0):.2f}%")
            with c6:
                st.metric("净利增速", f"{fin.get('net_income_yoy', 0):.2f}%")
            with c7:
                st.metric("毛利率", f"{fin.get('gross_margin', 0):.2f}%")
            with c8:
                st.metric("净利率", f"{fin.get('net_margin', 0):.2f}%")
            
            st.caption(f"报告日期: {fin.get('report_date', '-')} | 类型: {fin.get('report_type', '-')}")
        else:
            st.info("暂无财务数据，请先录入")
        
        st.divider()
        
        with st.expander("➕ 手动录入财务数据"):
            c1, c2, c3 = st.columns(3)
            with c1:
                fin_report_date = st.text_input("报告日期", value="2024-12-31", key="fin_report_date")
            with c2:
                fin_report_type = st.selectbox("报告类型", ["年报", "季报"], key="fin_report_type")
            with c3:
                fin_pe = st.number_input("PE", min_value=0.0, value=0.0, step=1.0, key="fin_pe")
            
            c4, c5, c6 = st.columns(3)
            with c4:
                fin_pb = st.number_input("PB", min_value=0.0, value=0.0, step=0.1, key="fin_pb")
            with c5:
                fin_roe = st.number_input("ROE(%)", min_value=0.0, value=0.0, step=1.0, key="fin_roe")
            with c6:
                fin_dividend = st.number_input("股息率(%)", min_value=0.0, value=0.0, step=0.1, key="fin_dividend")
            
            if st.button("保存财务数据", type="primary"):
                upsert_financial({
                    "symbol": fin_symbol,
                    "report_date": fin_report_date,
                    "report_type": fin_report_type,
                    "pe": fin_pe,
                    "pb": fin_pb,
                    "roe": fin_roe,
                    "dividend_yield": fin_dividend
                })
                st.success("✅ 财务数据已保存")
                st.rerun()

with st.sidebar:
    render_signature()
