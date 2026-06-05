import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from dotenv import load_dotenv

from src.agent.agent import WeatherAgent

load_dotenv()


def run_chat(session_id: str, message: str) -> str:
    async def _run():
        async with WeatherAgent() as agent:
            return await agent.chat(session_id, message)
    return asyncio.run(_run())


def load_history(session_id: str) -> list:
    async def _run():
        async with WeatherAgent() as agent:
            return agent.memory.get_history(session_id)
    return asyncio.run(_run())


def list_sessions() -> list[str]:
    async def _run():
        async with WeatherAgent() as agent:
            return agent.memory.list_sessions()
    return asyncio.run(_run())


def clear_session(session_id: str) -> None:
    async def _run():
        async with WeatherAgent() as agent:
            agent.memory.clear_session(session_id)
    return asyncio.run(_run())


def init_session_state():
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())[:8]
    if "messages" not in st.session_state:
        hist = load_history(st.session_state.session_id)
        st.session_state.messages = [
            {"role": m["role"], "content": m["content"]} for m in hist
        ]


def switch_session(session_id: str):
    st.session_state.session_id = session_id
    hist = load_history(session_id)
    st.session_state.messages = [
        {"role": m["role"], "content": m["content"]} for m in hist
    ]


def new_session():
    sid = str(uuid.uuid4())[:8]
    st.session_state.session_id = sid
    st.session_state.messages = []


st.set_page_config(page_title="Weather AI Agent", page_icon="🌦️")
st.title("🌦️ Weather AI Assistant")

init_session_state()

with st.sidebar:
    st.header("Sessions")
    if st.button("➕ New Chat", use_container_width=True):
        new_session()
        st.rerun()

    sessions = list_sessions()
    for sid in sessions:
        if st.button(sid, use_container_width=True, key=f"sid_{sid}"):
            switch_session(sid)
            st.rerun()

    st.divider()
    if st.button("🗑️ Clear Current", use_container_width=True):
        clear_session(st.session_state.session_id)
        st.session_state.messages = []
        st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask about weather anywhere..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Fetching weather data..."):
            response = run_chat(st.session_state.session_id, prompt)
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
