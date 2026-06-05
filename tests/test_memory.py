import os
import tempfile
from src.agent.memory import ConversationMemory


def test_save_and_get_history():
    tmp = tempfile.mkdtemp()
    mem = ConversationMemory(storage_dir=tmp)
    mem.save_message("s1", "user", "Hello")
    mem.save_message("s1", "assistant", "Hi there")
    hist = mem.get_history("s1")
    assert len(hist) == 2
    assert hist[0]["role"] == "user"
    assert hist[0]["content"] == "Hello"
    assert hist[1]["role"] == "assistant"
    assert hist[1]["content"] == "Hi there"


def test_get_history_max_messages():
    tmp = tempfile.mkdtemp()
    mem = ConversationMemory(storage_dir=tmp)
    for i in range(10):
        mem.save_message("s2", "user", f"msg{i}")
    hist = mem.get_history("s2", max_messages=3)
    assert len(hist) == 3
    assert hist[0]["content"] == "msg7"
    assert hist[-1]["content"] == "msg9"


def test_empty_session_returns_empty_list():
    tmp = tempfile.mkdtemp()
    mem = ConversationMemory(storage_dir=tmp)
    assert mem.get_history("nonexistent") == []


def test_clear_session():
    tmp = tempfile.mkdtemp()
    mem = ConversationMemory(storage_dir=tmp)
    mem.save_message("s3", "user", "test")
    assert len(mem.get_history("s3")) == 1
    mem.clear_session("s3")
    assert mem.get_history("s3") == []


def test_list_sessions():
    tmp = tempfile.mkdtemp()
    mem = ConversationMemory(storage_dir=tmp)
    mem.save_message("a", "user", "x")
    mem.save_message("b", "user", "y")
    mem.save_message("c", "user", "z")
    sessions = mem.list_sessions()
    assert sorted(sessions) == ["a", "b", "c"]


def test_clear_nonexistent_session_does_not_raise():
    tmp = tempfile.mkdtemp()
    mem = ConversationMemory(storage_dir=tmp)
    mem.clear_session("does-not-exist")


def test_special_characters_in_content():
    tmp = tempfile.mkdtemp()
    mem = ConversationMemory(storage_dir=tmp)
    content = "Lahore mein 35°C, ☀️, 湿度80%"
    mem.save_message("s4", "user", content)
    hist = mem.get_history("s4")
    assert hist[0]["content"] == content


def test_persistence_on_disk():
    tmp = tempfile.mkdtemp()
    mem = ConversationMemory(storage_dir=tmp)
    mem.save_message("persist", "user", "stored")
    path = os.path.join(tmp, "persist.json")
    assert os.path.exists(path)
    mem2 = ConversationMemory(storage_dir=tmp)
    hist = mem2.get_history("persist")
    assert len(hist) == 1
    assert hist[0]["content"] == "stored"


def test_multiple_sessions_isolated():
    tmp = tempfile.mkdtemp()
    mem = ConversationMemory(storage_dir=tmp)
    mem.save_message("s_a", "user", "aaa")
    mem.save_message("s_b", "user", "bbb")
    assert mem.get_history("s_a")[0]["content"] == "aaa"
    assert mem.get_history("s_b")[0]["content"] == "bbb"


def test_timestamp_is_added():
    tmp = tempfile.mkdtemp()
    mem = ConversationMemory(storage_dir=tmp)
    mem.save_message("ts", "user", "hello")
    hist = mem.get_history("ts")
    assert "timestamp" in hist[0]
