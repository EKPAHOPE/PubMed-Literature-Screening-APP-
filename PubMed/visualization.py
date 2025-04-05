# visualization.py
import plotly.graph_objs as go
import streamlit as st

def get_yearly_publication_trends(articles):
    trends = {}
    for article in articles:
        year = article.get('year', 'Unknown')
        if year != 'Unknown':
            trends[year] = trends.get(year, 0) + 1
    return dict(sorted(trends.items()))

def get_journal_publication_counts(articles):
    counts = {}
    for article in articles:
        journal = article.get('journal', 'Unknown')
        counts[journal] = counts.get(journal, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10])

def plot_yearly_trends(trends):
    fig = go.Figure(data=go.Scatter(
        x=list(trends.keys()), y=list(trends.values()), 
        mode='lines+markers', line=dict(color='blue', width=3), marker=dict(size=10)
    ))
    fig.update_layout(title="Publication Trends Over Years", xaxis_title="Year", yaxis_title="Number of Publications")
    st.plotly_chart(fig, use_container_width=True)

def plot_journal_counts(counts):
    fig = go.Figure(data=go.Bar(
        x=list(counts.keys()), y=list(counts.values()), marker_color='green'
    ))
    fig.update_layout(title="Top 10 Journals", xaxis_title="Journal", yaxis_title="Number of Publications", xaxis_tickangle=-90)
    st.plotly_chart(fig, use_container_width=True)