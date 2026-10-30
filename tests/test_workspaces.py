from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

APP=Path(__file__).resolve().parents[1]/'app.py'

@pytest.mark.parametrize('workspace',['Spot curves & key rate risk','Portfolio & comparison','Reinvestment','Sovereign relative value'])
def test_advanced_navigation(workspace):
    app=AppTest.from_file(APP,default_timeout=60).run()
    next(w for w in app.selectbox if w.label=='Advanced workspace').select(workspace).run()
    assert not app.exception
    assert not app.error
    assert len(app.get('plotly_chart'))>=2


@pytest.mark.parametrize('measure',['Dirty price','Price change (%)','Position profit/loss','Modified duration','Convexity'])
def test_surface_measures(measure):
    app=AppTest.from_file(APP,default_timeout=60).run()
    next(w for w in app.select_slider if w.label=='Surface grid resolution').set_value(15)
    next(w for w in app.selectbox if w.label=='Surface measure').select(measure).run(timeout=60)
    assert not app.exception
    assert not app.error
    assert len(app.get('plotly_chart'))>=4
