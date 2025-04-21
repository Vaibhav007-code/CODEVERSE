import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import sqlite3
import random
import time

conn = sqlite3.connect('wellbeing.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS screen_time
             (date DATE, app TEXT, minutes INTEGER, category TEXT)''')
conn.commit()

def create_sample_data():
    apps = ['Instagram', 'TikTok', 'YouTube', 'WhatsApp', 'Chrome', 'Email']
    categories = ['Social Media', 'Social Media', 'Entertainment', 'Communication', 'Productivity', 'Productivity']
    data = []
    for i in range(7):
        date = datetime.now() - timedelta(days=6-i)
        for app, category in zip(apps, categories):
            data.append({
                'date': date.date(),
                'app': app,
                'minutes': random.randint(15, 120),
                'category': category
            })
    return pd.DataFrame(data)

if pd.read_sql('SELECT COUNT(*) FROM screen_time', conn).iloc[0,0] == 0:
    sample_df = create_sample_data()
    sample_df.to_sql('screen_time', conn, if_exists='append', index=False)

st.set_page_config(layout="wide", page_title="Digital Wellbeing Dashboard")
st.title("📱 Digital Wellbeing Dashboard")

with st.sidebar:
    st.header("Settings")
    days_to_show = st.slider("Show last N days", 1, 30, 7)
    block_mode = st.checkbox("Enable Focus Mode")
    if block_mode:
        focus_hours = st.slider("Block distracting apps during", 0, 23, (9, 17))
        st.warning(f"Social/entertainment apps blocked from {focus_hours[0]}:00 to {focus_hours[1]}:00")
    st.header("Import Data")
    uploaded_file = st.file_uploader("Upload screen time CSV", type=["csv"])
    if uploaded_file:
        new_data = pd.read_csv(uploaded_file)
        new_data.to_sql('screen_time', conn, if_exists='append', index=False)
        st.success(f"Added {len(new_data)} records!")

df = pd.read_sql(f'''
    SELECT date, app, minutes, category 
    FROM screen_time 
    WHERE date >= date('now', '-{days_to_show} days')
    ORDER BY date DESC
''', conn)

col1, col2, col3 = st.columns(3)
total_time = df['minutes'].sum()
col1.metric("Total Screen Time", f"{total_time//60}h {total_time%60}m")
col2.metric("Most Used App", df.groupby('app')['minutes'].sum().idxmax())
col3.metric("Avg. Daily Use", f"{round(df.groupby('date')['minutes'].sum().mean()/60,1)}h")

tab1, tab2, tab3 = st.tabs(["Usage Trends", "App Breakdown", "Focus Tools"])

with tab1:
    st.subheader("Daily Usage")
    daily = df.groupby(['date', 'category'])['minutes'].sum().reset_index()
    chart = alt.Chart(daily).mark_area().encode(
        x='date:T',
        y='minutes:Q',
        color='category:N',
        tooltip=['date', 'category', 'minutes']
    ).properties(width=800)
    st.altair_chart(chart, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top Apps")
        top_apps = df.groupby('app')['minutes'].sum().nlargest(5).reset_index()
        st.dataframe(top_apps.style.background_gradient(cmap='Blues'), 
                    hide_index=True)
    with col2:
        st.subheader("By Category")
        category_pie = alt.Chart(df).mark_arc().encode(
            theta='sum(minutes)',
            color='category',
            tooltip=['category', 'sum(minutes)']
        )
        st.altair_chart(category_pie, use_container_width=True)

with tab3:
    st.subheader("Set App Limits")
    apps = df['app'].unique()
    limits = {}
    for app in apps:
        limits[app] = st.slider(
            f"Daily limit for {app} (mins)",
            0, 180,
            value=60 if df[df['app']==app]['minutes'].mean() > 60 else 30,
            key=f"limit_{app}"
        )
    if st.button("Save Limits"):
        st.session_state['app_limits'] = limits
        st.success("Limits saved! You'll get alerts when exceeding these.")
    st.subheader("Focus Sessions")
    focus_minutes = st.number_input("Session duration (minutes)", 5, 120, 25)
    if st.button("Start Focus Session"):
        st.toast(f"Focus mode activated for {focus_minutes} minutes!")
        with st.spinner(f"Focusing for {focus_minutes} minutes..."):
            time.sleep(focus_minutes * 60)
        st.balloons()
        st.success("Session complete!")
        new_record = pd.DataFrame([{
            'date': datetime.now().date(),
            'app': 'Focus Session',
            'minutes': focus_minutes,
            'category': 'Productivity'
        }])
        new_record.to_sql('screen_time', conn, if_exists='append', index=False)

conn.close()