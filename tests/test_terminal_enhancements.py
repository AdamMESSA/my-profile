from datetime import date
from pathlib import Path
import json
import pytest
from streamlit.testing.v1 import AppTest
from fixed_income.analytics import portfolio_values, portfolio_risk, scenario_results
from fixed_income.bonds import Bond
from fixed_income.workspace_state import encode_workspace, decode_workspace

APP=Path(__file__).resolve().parents[1]/'app.py'


def test_risk_contributions_reconcile():
    rows=[{'Name':name,'Currency':cur,'Face':1000,'Coupon (%)':4,'Maturity':'2036-10-31',
           'Frequency':2,'Yield (%)':3.5,'Quantity':qty} for name,cur,qty in [('A','EUR',1),('B','USD',3)]]
    values=portfolio_values(rows,date(2026,10,31),'EUR',{'USD':.9})
    table=portfolio_risk(values)
    assert table['Weight (%)'].sum()==pytest.approx(100)
    assert table['DV01 contribution (%)'].sum()==pytest.approx(100)
    assert table['Duration contribution (years)'].sum()==pytest.approx(table.DV01.sum()/table.Value.sum()*10000)
    assert table.loc[1,'DV01 contribution (%)']/table.loc[0,'DV01 contribution (%)']==pytest.approx(2.7)


def test_named_scenarios_exact_and_invalid():
    bond=Bond(1000,.04,date(2036,10,31),date(2026,10,31))
    rows=[{'Name':'Base','Benchmark (bp)':0,'Spread (bp)':0},
          {'Name':'Stress','Benchmark (bp)':50,'Spread (bp)':100}]
    table=scenario_results(bond,.035,rows)
    assert table.iloc[0]['P/L']==pytest.approx(0)
    assert table.iloc[1]['Dirty price']==pytest.approx(bond.value(.05)['dirty'])
    assert table.iloc[1]['P/L']<0
    with pytest.raises(ValueError): scenario_results(bond,.035,[rows[0],rows[0]])
    with pytest.raises(ValueError): scenario_results(bond,.035,[dict(rows[0],**{'Spread (bp)':float('nan')})])


def test_workspace_roundtrip_and_invalid():
    inputs={'input:Settlement date':date(2026,10,31),'input:Face value':2000.,'navigation':'Named scenarios','fx:EUR:USD':.9}
    tables={'named_scenarios':[{'Name':'Stress','Benchmark (bp)':100.,'Spread (bp)':50.}]}
    assert decode_workspace(encode_workspace(inputs,tables))=={'version':1,'inputs':inputs,'tables':tables}
    for data in [{'version':2,'inputs':{},'tables':{}}, {'version':1,'inputs':{'unknown':3},'tables':{}},
                 {'version':1,'inputs':{'input:Face value':'bad'},'tables':{}},
                 {'version':1,'inputs':{},'tables':{'positions':'bad'}}]:
        with pytest.raises(ValueError): decode_workspace(json.dumps(data))


def test_navigation_retains_edits_and_workspace_restores():
    app=AppTest.from_file(APP,default_timeout=60).run()
    app.radio(key='navigation').set_value('Named scenarios').run()
    states=app._tree.get_widget_states()
    states.widgets.add(id=app.dataframe[0].proto.id, string_value=json.dumps({'edited_rows':{'1':{'Name':'Custom stress','Benchmark (bp)':125.}},'added_rows':[],'deleted_rows':[]}))
    app._run(states)
    assert app.session_state['table:named_scenarios'][1]['Name']=='Custom stress'
    app.radio(key='navigation').set_value('Portfolio overview').run()
    app.number_input(key='input:Face value').set_value(2000.).run()
    app.radio(key='navigation').set_value('Named scenarios').run()
    assert not app.exception and not app.error
    assert app.session_state['table:named_scenarios'][1]['Benchmark (bp)']==125.
    # Load the same portable data into a fresh session, as the uploader callback does.
    data=decode_workspace(encode_workspace({'input:Face value':2000.,'navigation':'Named scenarios'},
                                          {'named_scenarios':app.session_state['table:named_scenarios']}))
    restored=AppTest.from_file(APP,default_timeout=60)
    for key,value in data['inputs'].items(): restored.session_state[key]=value
    for key,rows in data['tables'].items(): restored.session_state['table:'+key]=rows
    restored.run()
    assert not restored.exception and not restored.error
    assert restored.number_input(key='input:Face value').value==2000.
    assert restored.dataframe[1].value.iloc[1]['Name']=='Custom stress'


def test_restore_is_atomic_and_replaces_previous_workspace():
    from fixed_income.workspace_state import apply_workspace
    state={'input:Face value':1000.,'table:positions':[{'Name':'old'}],
           'editor_base:positions':[], 'fx:EUR:USD':.9, 'unrelated':'keep'}
    original=dict(state)
    with pytest.raises(ValueError): apply_workspace('{broken',state)
    assert state==original
    apply_workspace(encode_workspace({'input:Face value':2000.},{}),state)
    assert state=={'input:Face value':2000.,'unrelated':'keep'}


def test_portfolio_named_scenarios_reconcile():
    from fixed_income.analytics import portfolio_scenarios
    rows=[{'Name':name,'Currency':cur,'Face':1000,'Coupon (%)':4,'Maturity':'2036-10-31',
           'Frequency':2,'Yield (%)':3.5,'Quantity':qty} for name,cur,qty in [('A','EUR',1),('B','USD',3)]]
    values=portfolio_values(rows,date(2026,10,31),'EUR',{'USD':.9})
    scenarios=[{'Name':'Base','Benchmark (bp)':0.,'Spread (bp)':0.},
               {'Name':'Stress','Benchmark (bp)':50.,'Spread (bp)':100.}]
    result=portfolio_scenarios(values,scenarios)
    assert result.iloc[0]['P/L']==pytest.approx(0.)
    expected=sum(p['_bond'].value(.05)['dirty']*p['Quantity']*p['_fx'] for p in values)
    assert result.iloc[1]['Shocked value']==pytest.approx(expected)
    assert result.iloc[1]['P/L']==pytest.approx(expected-sum(p['Value'] for p in values))


def test_restored_portfolio_fx_curve_and_scenarios():
    app=AppTest.from_file(APP,default_timeout=60)
    app.session_state['navigation']='Portfolio overview'
    app.session_state['input:Reporting currency']='EUR'
    app.session_state['fx:EUR:USD']=.9
    app.session_state['table:positions']=[{'Name':'USD holding','Currency':'USD','Face':1000.,
        'Coupon (%)':4.,'Maturity':'2036-10-31','Frequency':2,'Yield (%)':3.5,'Quantity':2.,'Spread (bp)':0.}]
    app.session_state['table:spot_curve']=[{'Tenor (years)':1.,'Spot (%)':2.5,'Shock (bp)':0.},
                                          {'Tenor (years)':30.,'Spot (%)':4.,'Shock (bp)':25.}]
    app.run()
    assert not app.exception and not app.error
    assert app.number_input(key='fx:EUR:USD').value==.9
    app.radio(key='navigation').set_value('Spot curves & key rate risk').run()
    assert not app.exception and not app.error
    assert app.dataframe[0].value.iloc[0]['Spot (%)']==2.5
    app.radio(key='navigation').set_value('Named scenarios').run()
    app.radio(key='input:Scenario scope').set_value('Saved portfolio').run()
    assert not app.exception and not app.error
    assert app.dataframe[1].value.iloc[0]['P/L']==pytest.approx(0.)
    app.radio(key='navigation').set_value('Portfolio overview').run()
    assert not app.exception and not app.error
    assert app.dataframe[0].value.iloc[0]['Name']=='USD holding'
