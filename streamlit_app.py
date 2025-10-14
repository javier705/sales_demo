import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
st.set_page_config(page_title="Sales Forecast Tool", layout="wide")

# Initialize data
if 'forecasts' not in st.session_state:
    customers = [
    "Golden Crust Bakery",
    "Sweet Haven Bakeshop",
    "Flour & Whisk Co.",
    "Morning Rise Bakery",
    "Velvet Crumb Patisserie"
    ] 

    today = pd.to_datetime('today')
    closest_sunday = today - pd.to_timedelta((today.weekday() + 1) % 7, unit='d')
    date_range = pd.date_range(end=closest_sunday, periods=24, freq='-1W-SUN')
    weeks = sorted([f"{date.strftime('%Y-%m-%d')}" for date in date_range])
    
    data = []
    for customer in customers:
        for week in weeks:
            data.append({
                'customer': customer,
                'week': week,
                'baseline_forecast': np.random.randint(10000, 60000),
                'adjusted_forecast': None
            })
    
    st.session_state.forecasts = pd.DataFrame(data)

# Always work with the DataFrame from session state
df = st.session_state.forecasts

# Header
st.title("📊 Sales Forecast Tool")

# Metrics
col1, col2, col3, col4 = st.columns(4)
baseline_total = df['baseline_forecast'].sum()
adjusted_total = df['adjusted_forecast'].fillna(df['baseline_forecast']).sum()
variance = ((adjusted_total - baseline_total) / baseline_total * 100) if baseline_total != 0 else 0
modified_count = df['adjusted_forecast'].notna().sum()

# Changed currency symbol to CWT
col1.metric("Baseline Total", f"{baseline_total/1000:.0f}K CWT")
col2.metric("Adjusted Total", f"{adjusted_total/1000:.0f}K CWT")
col3.metric("Variance", f"{variance:.1f}%")
col4.metric("Cells Modified", f"{modified_count}/{len(df)}")

st.divider()

# Customer selection
selected_customer = st.selectbox("Select Customer", df['customer'].unique())

# Filter data for the selected customer
# We use .copy() to ensure we're not modifying a slice of the main df directly before assignment
customer_df = df[df['customer'] == selected_customer].copy()

# Bulk adjustment
st.subheader("🎯 Bulk Adjustment")
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    adj_type = st.selectbox("Type", ["Percentage", "Absolute"])

with col2:
    adj_value = st.number_input(
        "Value" if adj_type == "Absolute" else "Percentage (%)", # Added % for clarity
        value=0.0,
        format="%.2f"
    )

with col3:
    if st.button("Apply to All Weeks", use_container_width=True):
        if adj_type == "Percentage":
            # Apply percentage adjustment
            customer_df['adjusted_forecast'] = (customer_df['baseline_forecast'] * (1 + adj_value/100)).round()
        else:
            # Apply absolute adjustment
            customer_df['adjusted_forecast'] = customer_df['baseline_forecast'] + adj_value
        
        # Update the main DataFrame in session state with the modified customer data
        # Use .loc with a boolean mask for efficient update
        st.session_state.forecasts.loc[df['customer'] == selected_customer, 'adjusted_forecast'] = customer_df['adjusted_forecast']
        
        # st.rerun() is generally needed after direct session_state modifications for UI to reflect immediately
        st.rerun()

if st.button("Reset Customer", use_container_width=False):
    # Reset adjusted_forecast for the selected customer in the main DataFrame
    st.session_state.forecasts.loc[df['customer'] == selected_customer, 'adjusted_forecast'] = None
    st.rerun() # Rerun to reflect the reset in the table and metrics

st.divider()

# Horizontal Forecast Editor
st.subheader(f"📝 {selected_customer} Forecast")

plot_df = customer_df.copy()
plot_df['adjusted_forecast'] = plot_df['adjusted_forecast'].fillna(plot_df['baseline_forecast'])

# Create two rows: one for baseline, one for adjusted
baseline_row = plot_df['baseline_forecast'].values
adjusted_row = plot_df['adjusted_forecast'].values
weeks = plot_df['week'].values

# Create DataFrame with weeks as columns
editor_df = pd.DataFrame({
    'Metric': ['Baseline (CWT)', 'Adjusted (CWT)'],
    **{week: [baseline_row[i], adjusted_row[i]] for i, week in enumerate(weeks)}
})

edited_data = st.data_editor(
    editor_df,
    column_config={
        'Metric': st.column_config.TextColumn('Metric', width=150, disabled=True),
        **{week: st.column_config.NumberColumn(week, format="accounting", disabled=(i==0)) 
           for i, week in enumerate(['Metric'] + list(weeks)) if week != 'Metric'}
    },
    hide_index=True,
    use_container_width=True
)

# Update session state if adjusted row changed
adjusted_edited = edited_data.iloc[1, 1:].values
if not np.array_equal(adjusted_edited, adjusted_row):
    indices_to_update = df[df['customer'] == selected_customer].index
    st.session_state.forecasts.loc[indices_to_update, 'adjusted_forecast'] = adjusted_edited
    st.rerun()



st.divider()

# Visualization
st.subheader("📈 Forecast Comparison")

plot_df = customer_df.copy()
plot_df['adjusted_forecast'] = plot_df['adjusted_forecast'].fillna(plot_df['baseline_forecast'])

import plotly.graph_objects as go

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=plot_df['week'],
    y=plot_df['baseline_forecast'],
    mode='lines+markers',
    name='Baseline',
    line=dict(color='#3b82f6', width=2),
    marker=dict(size=10, opacity=0.7)
))

fig.add_trace(go.Scatter(
    x=plot_df['week'],
    y=plot_df['adjusted_forecast'],
    mode='lines+markers',
    name='Adjusted',
    line=dict(color='#ef4444', width=2),
    marker=dict(size=10, opacity=0.7)
))

fig.update_layout(
    xaxis_title="Week",
    yaxis_title="Forecast (CWT)",
    hovermode='x unified',
    height=500,
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)
# Export
if st.button("📥 Export to CSV", type="primary"):
    export_df = df.copy()
    export_df['adjusted_forecast'] = export_df['adjusted_forecast'].fillna(export_df['baseline_forecast'])
    export_df['variance_%'] = ((export_df['adjusted_forecast'] - export_df['baseline_forecast']) / export_df['baseline_forecast'] * 100).round(1)
    export_df['variance_%'] = export_df['variance_%'].fillna(0) # Handle division by zero

    csv = export_df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="forecast_adjustments.csv",
        mime="text/csv"
    )
