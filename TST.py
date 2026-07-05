#Gondul
import streamlit as st
import pandas as pd
import numpy as np
import math

st.set_page_config(page_title="Revit Licensing Optimizer", page_icon="🏗️", layout="wide")

st.title("🏗️ Revit Licensing Optimizer")
st.caption("Interactive model to choose the most cost-effective mix of named seats and Flex tokens.")

# =========================
# Sidebar: Inputs
# =========================
with st.sidebar:
    st.header("Inputs")
    st.subheader("Team & Usage")
    total_employees = st.number_input("Total employees", min_value=1, value=300, step=1)
    projects = st.number_input("Active projects", min_value=0, value=50, step=1)

    st.markdown("**Authors by usage intensity**")
    colA, colB, colC = st.columns(3)
    with colA:
        authors_heavy = st.number_input("Heavy authors (#)", min_value=0, value=90, step=1)
        days_heavy = st.number_input("Heavy days/year", min_value=0, value=220, step=5)
    with colB:
        authors_medium = st.number_input("Medium authors (#)", min_value=0, value=40, step=1)
        days_medium = st.number_input("Medium days/year", min_value=0, value=150, step=5)
    with colC:
        authors_light = st.number_input("Light authors (#)", min_value=0, value=20, step=1)
        days_light = st.number_input("Light days/year", min_value=0, value=40, step=5)

    # Derived
    non_authors = max(0, total_employees - (authors_heavy + authors_medium + authors_light))
    st.markdown(f"*Non-authors (viewers/markups only):* **{non_authors}**")

    st.subheader("Flex & Pricing")
    tokens_per_day = st.number_input("Tokens per Revit day", min_value=1, value=10, step=1)
    token_buffer_pct = st.slider("Token buffer (%)", min_value=0, max_value=50, value=10, step=1)
    seat_price = st.number_input("Seat price (USD / year)", min_value=0.0, value=2700.0, step=50.0, format="%.2f")
    token_price = st.number_input("Token price (USD each)", min_value=0.0, value=3.0, step=0.1, format="%.2f")

    st.subheader("Advanced (optional)")
    run_grid = st.checkbox("Run price sensitivity grid", value=False, help="Compare multiple seat/token price points.")
    seat_price_grid_text = st.text_input("Seat prices (comma-separated)", "2300,2700,3100")
    token_price_grid_text = st.text_input("Token prices (comma-separated)", "2.5,3.0,3.5")

# =========================
# Core calculations
# =========================
def compute_tokens_needed(m_count, m_days, l_count, l_days, tokens_per_day, buffer_pct):
    raw = (m_count * m_days + l_count * l_days) * tokens_per_day
    return math.ceil(raw * (1 + buffer_pct / 100.0))

def scenario_costs(
    seat_price,
    token_price,
    authors_heavy,
    authors_medium,
    authors_light,
    days_medium,
    days_light,
    tokens_per_day,
    token_buffer_pct
):
    # 1) Lean Seats: seats for HEAVY; MEDIUM + LIGHT use Flex.
    lean_seats = authors_heavy
    lean_tokens = compute_tokens_needed(
        authors_medium, days_medium,
        authors_light, days_light,
        tokens_per_day, token_buffer_pct
    )
    lean_cost = lean_seats * seat_price + lean_tokens * token_price

    # 2) Balanced Seats: seats for HEAVY + MEDIUM; LIGHT uses Flex.
    balanced_seats = authors_heavy + authors_medium
    balanced_tokens = compute_tokens_needed(
        0, 0,
        authors_light, days_light,
        tokens_per_day, token_buffer_pct
    )
    balanced_cost = balanced_seats * seat_price + balanced_tokens * token_price

    # 3) Max Seats: seats for all authors; small Flex reserve (5% of seats for one day) for bursts.
    max_seats = authors_heavy + authors_medium + authors_light
    max_tokens = math.ceil(0.05 * max(1, max_seats) * tokens_per_day)
    max_cost = max_seats * seat_price + max_tokens * token_price

    breakeven_days = (seat_price / (tokens_per_day * token_price)) if token_price > 0 and tokens_per_day > 0 else float("inf")

    rows = [
        {"strategy": "Lean", "seats": lean_seats, "tokens": lean_tokens, "total_cost": lean_cost},
        {"strategy": "Balanced", "seats": balanced_seats, "tokens": balanced_tokens, "total_cost": balanced_cost},
        {"strategy": "Max", "seats": max_seats, "tokens": max_tokens, "total_cost": max_cost},
    ]
    df = pd.DataFrame(rows).sort_values("total_cost", ascending=True).reset_index(drop=True)
    return df, breakeven_days

# Run main calculation
df, breakeven_days = scenario_costs(
    seat_price, token_price,
    authors_heavy, authors_medium, authors_light,
    days_medium, days_light, tokens_per_day, token_buffer_pct
)

# =========================
# KPIs
# =========================
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric("Seat price (USD/yr)", f"{seat_price:,.0f}")
with kpi2:
    st.metric("Token price (USD)", f"{token_price:,.2f}")
with kpi3:
    st.metric("Breakeven days/user", f"{breakeven_days:,.0f}")
with kpi4:
    st.metric("Tokens per day", f"{tokens_per_day}")

# =========================
# Results
# =========================
st.subheader("Results — Strategies")
st.dataframe(df, use_container_width=True)

best_row = df.iloc[0]
st.success(
    f"**Recommendation:** {best_row['strategy']} — {int(best_row['seats'])} seats + {int(best_row['tokens'])} tokens.\n"
    f"Estimated annual cost: **${best_row['total_cost']:,.0f}**"
)

# =========================
# Visualization
# =========================
try:
    import matplotlib.pyplot as plt
    fig = plt.figure()
    plt.bar(df["strategy"], df["total_cost"])
    plt.title("Total Cost by Strategy")
    plt.ylabel("USD / year")
    st.pyplot(fig, clear_figure=True)
except Exception as e:
    st.warning(f"Chart unavailable: {e}")

# =========================
# Price sensitivity grid (optional)
# =========================
if run_grid:
    try:
        seat_candidates = [float(x.strip()) for x in seat_price_grid_text.split(",") if x.strip()]
        token_candidates = [float(x.strip()) for x in token_price_grid_text.split(",") if x.strip()]
    except ValueError:
        st.error("Please enter valid numbers for the grids.")
        seat_candidates, token_candidates = [], []

    if seat_candidates and token_candidates:
        grid_rows = []
        for sp in seat_candidates:
            for tp in token_candidates:
                dfx, be = scenario_costs(
                    sp, tp,
                    authors_heavy, authors_medium, authors_light,
                    days_medium, days_light, tokens_per_day, token_buffer_pct
                )
                winner = dfx.iloc[0]
                grid_rows.append({
                    "seat_price": sp,
                    "token_price": tp,
                    "breakeven_days": be,
                    "cheapest_strategy": winner["strategy"],
                    "seats": int(winner["seats"]),
                    "tokens": int(winner["tokens"]),
                    "total_cost": float(winner["total_cost"]),
                })
        grid = pd.DataFrame(grid_rows).sort_values(["seat_price", "token_price"]).reset_index(drop=True)
        st.subheader("Price Sensitivity Grid")
        st.dataframe(grid, use_container_width=True)

        csv = grid.to_csv(index=False).encode("utf-8")
        st.download_button("Download Grid CSV", csv, file_name="price_sensitivity_grid.csv", mime="text/csv")

# =========================
# Footer
# =========================
st.caption("Tip: Push batch exports/checks to APS (Design Automation for Revit) to avoid consuming human seat time.")


