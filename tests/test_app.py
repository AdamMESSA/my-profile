from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_terminal_and_interactions():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=60).run(timeout=60)
    assert not app.exception
    assert len(app.metric) >= 10
    app.number_input[2].set_value(0.0).run()
    assert not app.exception
    app.selectbox[2].select('ACT/360').run()
    assert not app.exception
    app.radio(key='input:Maturity input').set_value('Years remaining').run()
    assert not app.exception
    app.radio(key='input:Market price basis').set_value('Dirty').run()
    assert not app.exception
    app.slider[0].set_value(-500).run()
    assert not app.exception
