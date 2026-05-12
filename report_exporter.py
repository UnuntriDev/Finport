"""PDF and CSV report exporter for FinPort.

Generates a professional PDF summary report and CSV data dumps
that users can download from the Export tab.
"""
from __future__ import annotations

import io
from datetime import date

import pandas as pd
from fpdf import FPDF


# ---------------------------------------------------------------------------
# PDF builder
# ---------------------------------------------------------------------------

class _FinPortPDF(FPDF):
    """Subclass with FinPort header, footer, and table helper."""

    def header(self) -> None:
        # Blue accent bar across the top
        self.set_fill_color(37, 99, 235)
        self.rect(0, 0, 210, 3, style="F")
        self.ln(6)

        self.set_font("Helvetica", "B", 20)
        self.set_text_color(15, 23, 42)
        self.cell(18, 10, "Fin", border=False, ln=False)
        self.set_text_color(37, 99, 235)
        self.cell(0, 10, "Port", border=False, ln=True)

        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 116, 139)
        self.cell(0, 5, "Portfolio Analysis & Risk Assessment Platform", ln=True)

        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.3)
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(6)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(
            0, 6,
            f"FinPort  |  Page {self.page_no()}  |  For educational purposes only - not financial advice",
            align="C",
        )

    def ensure_space(self, needed_mm: float) -> None:
        """Trigger a page break if less than `needed_mm` of vertical room remains.

        Prevents a section title or table from being orphaned at the bottom
        of a page when the body would otherwise spill onto the next one.
        """
        if self.get_y() + needed_mm > self.h - self.b_margin:
            self.add_page()

    def section_title(self, title: str, keep_with_next_mm: float = 0.0) -> None:
        """Render a section heading. If ``keep_with_next_mm`` is provided,
        first force a page break when the title plus that much content would
        not fit on the current page (i.e., keep title together with what follows).
        """
        if keep_with_next_mm:
            self.ensure_space(10 + keep_with_next_mm)
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(241, 245, 249)
        self.set_text_color(30, 58, 138)
        self.cell(0, 8, f"  {title}", ln=True, fill=True)
        self.ln(2)

    def kv_row(self, label: str, value: str) -> None:
        self.set_font("Helvetica", "", 10)
        self.set_text_color(100, 116, 139)
        self.cell(75, 7, label)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(15, 23, 42)
        self.cell(0, 7, value, ln=True)

    def data_table(self, headers: list[str], rows: list[list[str]]) -> None:
        col_w = 185.0 / len(headers)

        # Make sure at least the header + first 3 rows fit on the current
        # page; if not, start a new one so the table is not orphaned.
        min_block = 7 + min(len(rows), 3) * 6 + 4
        self.ensure_space(min_block)

        # Header row
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(30, 58, 138)
        self.set_text_color(255, 255, 255)
        for h in headers:
            self.cell(col_w, 7, h, border=False, fill=True)
        self.ln()

        # Data rows with alternating shading
        self.set_font("Helvetica", "", 9)
        for i, row in enumerate(rows):
            fill = i % 2 == 0
            self.set_fill_color(248, 250, 252) if fill else self.set_fill_color(255, 255, 255)
            self.set_text_color(30, 41, 59)
            for cell in row:
                self.cell(col_w, 6, str(cell), border=False, fill=True)
            self.ln()
        self.ln(3)


def build_pdf(
    tickers: list[str],
    weights: pd.Series,
    start_date: date,
    end_date: date,
    port_metrics: dict[str, float],
    sharpe: float,
    risk_free_rate: float,
    initial_investment: float,
    asset_stats: pd.DataFrame,
    port_value: pd.Series,
    mc_p5: float | None = None,
    mc_p50: float | None = None,
    mc_p95: float | None = None,
    mc_horizon_days: int | None = None,
    max_dd: float | None = None,
    sortino: float | None = None,
    beta: float | None = None,
    alpha: float | None = None,
    r_squared: float | None = None,
    max_sharpe_weights: pd.Series | None = None,
    max_sharpe_metrics: dict | None = None,
    min_var_weights: pd.Series | None = None,
    min_var_metrics: dict | None = None,
) -> bytearray:
    """Build a PDF summary report and return it as a bytearray."""
    pdf = _FinPortPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Report date
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 5, f"Generated: {date.today().strftime('%B %d, %Y')}", align="R", ln=True)
    pdf.ln(2)

    # --- Portfolio Configuration ---
    pdf.section_title("Portfolio Configuration")
    pdf.kv_row("Assets", ", ".join(tickers))
    pdf.kv_row("Analysis period", f"{start_date}  -  {end_date}")
    pdf.kv_row("Initial investment", f"${initial_investment:,.2f}")
    pdf.kv_row("Risk-free rate", f"{risk_free_rate * 100:.2f}% p.a.")
    pdf.ln(4)

    # --- Key Metrics ---
    pdf.section_title("Key Portfolio Metrics")
    ann_ret = port_metrics["return"]
    ann_vol = port_metrics["volatility"]
    final_val = float(port_value.iloc[-1])
    total_ret = (final_val / initial_investment - 1) * 100

    pdf.kv_row("Annualized return", f"{ann_ret * 100:.2f}%")
    pdf.kv_row("Annualized volatility (risk)", f"{ann_vol * 100:.2f}%")
    pdf.kv_row("Sharpe ratio", f"{sharpe:.2f}")
    if sortino is not None:
        pdf.kv_row("Sortino ratio (downside)", f"{sortino:.2f}")
    if max_dd is not None:
        pdf.kv_row("Maximum drawdown", f"{max_dd * 100:.2f}%")
    pdf.kv_row("Final portfolio value", f"${final_val:,.2f}  ({total_ret:+.2f}% total)")
    pdf.ln(4)

    # --- CAPM / Market exposure ---
    if beta is not None:
        pdf.section_title("Market Exposure (CAPM vs S&P 500)")
        pdf.kv_row("Beta", f"{beta:.2f}")
        pdf.kv_row("Alpha (annualized)", f"{(alpha or 0) * 100:+.2f}%")
        pdf.kv_row("R-squared", f"{r_squared or 0:.2f}")
        pdf.ln(4)

    # --- Optimal portfolios ---
    if max_sharpe_metrics is not None and min_var_metrics is not None:
        # 4 rows (header + 3 portfolios) * 6mm + padding
        pdf.section_title("Optimal Portfolios (Markowitz)", keep_with_next_mm=32)
        opt_headers = ["Portfolio", "Ann. Return", "Ann. Volatility", "Sharpe Ratio"]
        custom_sh = (ann_ret - risk_free_rate) / ann_vol if ann_vol > 0 else 0.0
        ms_sh = (
            (max_sharpe_metrics["return"] - risk_free_rate)
            / max_sharpe_metrics["volatility"]
            if max_sharpe_metrics["volatility"] > 0 else 0.0
        )
        mv_sh = (
            (min_var_metrics["return"] - risk_free_rate)
            / min_var_metrics["volatility"]
            if min_var_metrics["volatility"] > 0 else 0.0
        )
        opt_rows = [
            [
                "Custom",
                f"{ann_ret * 100:.2f}%",
                f"{ann_vol * 100:.2f}%",
                f"{custom_sh:.2f}",
            ],
            [
                "Max Sharpe",
                f"{max_sharpe_metrics['return'] * 100:.2f}%",
                f"{max_sharpe_metrics['volatility'] * 100:.2f}%",
                f"{ms_sh:.2f}",
            ],
            [
                "Min Variance",
                f"{min_var_metrics['return'] * 100:.2f}%",
                f"{min_var_metrics['volatility'] * 100:.2f}%",
                f"{mv_sh:.2f}",
            ],
        ]
        pdf.data_table(opt_headers, opt_rows)

        # Weights comparison — needs ~6mm per ticker + header
        weights_table_height = 12 + len(weights) * 6
        pdf.section_title(
            "Optimal Weights Comparison",
            keep_with_next_mm=weights_table_height,
        )
        w_headers = ["Ticker", "Custom", "Max Sharpe", "Min Variance"]
        w_rows = []
        for ticker in weights.index:
            ms_w = max_sharpe_weights.get(ticker, 0.0) if max_sharpe_weights is not None else 0.0
            mv_w = min_var_weights.get(ticker, 0.0) if min_var_weights is not None else 0.0
            w_rows.append([
                ticker,
                f"{weights.get(ticker, 0.0) * 100:.2f}%",
                f"{ms_w * 100:.2f}%",
                f"{mv_w * 100:.2f}%",
            ])
        pdf.data_table(w_headers, w_rows)

    # --- Per-Asset Statistics ---
    per_asset_height = 12 + len(asset_stats) * 6
    pdf.section_title(
        "Per-Asset Statistics (Annualized)",
        keep_with_next_mm=per_asset_height,
    )
    headers = ["Ticker", "Weight", "Ann. Return", "Ann. Volatility", "Avg Daily Return"]
    rows = [
        [
            ticker,
            f"{weights.get(ticker, 0.0) * 100:.2f}%",
            f"{asset_stats.loc[ticker, 'annual_return'] * 100:.2f}%",
            f"{asset_stats.loc[ticker, 'annual_vol'] * 100:.2f}%",
            f"{asset_stats.loc[ticker, 'mean_daily'] * 100:.3f}%",
        ]
        for ticker in asset_stats.index
        if ticker in weights.index
    ]
    pdf.data_table(headers, rows)

    # --- Monte Carlo ---
    if mc_p50 is not None:
        pdf.section_title("Monte Carlo Simulation Summary")
        horizon_label = f"{mc_horizon_days} trading days" if mc_horizon_days else "N/A"
        pdf.kv_row("Simulation horizon", horizon_label)
        pdf.kv_row("Median outcome (50th pct.)", f"${mc_p50:,.2f}")
        pdf.kv_row("Pessimistic outcome (5th pct.)", f"${mc_p5:,.2f}")
        pdf.kv_row("Optimistic outcome (95th pct.)", f"${mc_p95:,.2f}")
        var_95 = initial_investment - mc_p5
        pdf.kv_row("Value at Risk 95%", f"${var_95:,.2f}")
        pdf.ln(4)

    # --- Disclaimer ---
    pdf.section_title("Disclaimer")
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.multi_cell(
        0, 5,
        "This report has been generated by FinPort for educational and academic purposes only. "
        "It does not constitute investment advice, financial recommendation, or any offer to buy or "
        "sell securities. Past performance is not indicative of future results. All data is sourced "
        "from Yahoo Finance and may contain inaccuracies. The authors assume no liability for "
        "decisions made based on this report.",
    )

    return pdf.output()


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

def prices_to_csv(prices: pd.DataFrame) -> str:
    return prices.reset_index().to_csv(index=False)


def returns_to_csv(returns: pd.DataFrame) -> str:
    return returns.reset_index().to_csv(index=False)


def summary_to_csv(asset_stats: pd.DataFrame, weights: pd.Series) -> str:
    df = asset_stats.copy()
    df.insert(0, "weight", weights.reindex(df.index).fillna(0.0))
    return df.to_csv()


def build_excel_workbook(
    prices: pd.DataFrame,
    returns: pd.DataFrame,
    asset_stats: pd.DataFrame,
    weights: pd.Series,
    port_value: pd.Series,
    port_metrics: dict[str, float],
    sharpe: float,
    sortino: float | None = None,
    max_dd: float | None = None,
) -> bytes:
    """Build a multi-sheet .xlsx workbook combining all key data.

    Sheets: Summary, Prices, Returns, Per-Asset Stats, Portfolio Value.
    """
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # --- Summary sheet ----------------------------------------------
        summary_rows = [
            ("Annualized return", f"{port_metrics['return'] * 100:.2f}%"),
            ("Annualized volatility", f"{port_metrics['volatility'] * 100:.2f}%"),
            ("Sharpe ratio", f"{sharpe:.2f}"),
        ]
        if sortino is not None:
            summary_rows.append(("Sortino ratio", f"{sortino:.2f}"))
        if max_dd is not None:
            summary_rows.append(("Max drawdown", f"{max_dd * 100:.2f}%"))
        summary_rows.append(
            ("Final value", f"${float(port_value.iloc[-1]):,.2f}")
        )
        summary_df = pd.DataFrame(summary_rows, columns=["Metric", "Value"])
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

        # --- Per-asset stats with weights -------------------------------
        stats_export = asset_stats.copy()
        stats_export.insert(0, "weight", weights.reindex(stats_export.index).fillna(0.0))
        stats_export.to_excel(writer, sheet_name="Per-Asset Stats")

        # --- Prices, Returns, Portfolio Value ---------------------------
        prices.to_excel(writer, sheet_name="Prices")
        returns.to_excel(writer, sheet_name="Daily Returns")
        pd.DataFrame({"portfolio_value": port_value}).to_excel(
            writer, sheet_name="Portfolio Value"
        )

        # Auto-width columns for readability
        for sheet_name in writer.sheets:
            sheet = writer.sheets[sheet_name]
            for col in sheet.columns:
                max_len = max(
                    (len(str(cell.value)) for cell in col if cell.value is not None),
                    default=12,
                )
                sheet.column_dimensions[col[0].column_letter].width = min(
                    max(max_len + 2, 12), 28
                )

    buf.seek(0)
    return buf.getvalue()
