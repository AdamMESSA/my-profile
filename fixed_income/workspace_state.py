"""Portable, versioned JSON workspaces. Never deserialize executable objects."""
from datetime import date
import json
from pathlib import Path
import math
import pandas as pd
import streamlit as st

SPECS = json.loads(Path(__file__).with_name('widget_keys.json').read_text())
TABLES = {'positions', 'spot_curve', 'sovereign_inputs', 'named_scenarios'}
WORKSPACES = ['Valuation & cash flows', 'Portfolio overview', '3D risk simulator',
              'Spot curves & key rate risk', 'Portfolio & comparison',
              'Named scenarios', 'Reinvestment', 'Sovereign relative value']


def encode_workspace(inputs, tables):
    return json.dumps({'version':1, 'inputs':inputs, 'tables':tables},
                      default=lambda value: value.isoformat() if isinstance(value,date) else value,
                      allow_nan=False, indent=2)


def decode_workspace(raw):
    if len(raw) > 2_000_000:
        raise ValueError('Workspace exceeds 2 MB.')
    data=json.loads(raw)
    if not isinstance(data,dict) or set(data) != {'version','inputs','tables'} or type(data['version']) is not int or data['version'] != 1:
        raise ValueError('Unsupported workspace format or version.')
    if not isinstance(data['inputs'],dict) or not isinstance(data['tables'],dict):
        raise ValueError('Workspace inputs and tables must be objects.')
    for key,value in data['inputs'].items():
        if key.startswith('fx:'):
            if type(value) not in (int,float) or not math.isfinite(value) or value<0: raise ValueError('Invalid FX input.')
            continue
        if key not in SPECS:
            raise ValueError(f'Unknown workspace input: {key}')
        kind=SPECS[key]['kind']
        if kind=='date_input':
            try: data['inputs'][key]=date.fromisoformat(value)
            except (ValueError,TypeError): raise ValueError('Invalid workspace date.')
        elif kind in {'number_input','slider'}:
            if kind=='number_input' and isinstance(value,list): raise ValueError('Expected a single number.')
            numbers=value if isinstance(value,list) else [value]
            if not numbers or len(numbers)>2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in numbers):
                raise ValueError('Invalid numeric input.')
        elif kind=='checkbox':
            if type(value) is not bool: raise ValueError('Invalid checkbox input.')
        elif kind=='multiselect':
            if not isinstance(value,list) or any(not isinstance(v,str) for v in value): raise ValueError('Invalid metric selection.')
        elif kind=='text_input':
            if not isinstance(value,str): raise ValueError('Invalid text input.')
        elif not isinstance(value,(str,int,float)) or isinstance(value,bool):
            raise ValueError('Invalid workspace selection.')
    for key, rows in data['tables'].items():
        if key not in TABLES or not isinstance(rows,list) or len(rows)>1000 or any(not isinstance(r,dict) for r in rows):
            raise ValueError('Invalid workspace table.')
        for row in rows:
            for value in row.values():
                if value is not None and not isinstance(value,(str,int,float,bool)):
                    raise ValueError('Invalid table value.')
                if isinstance(value,float) and not math.isfinite(value): raise ValueError('Nonfinite table value.')
    return data


def editor(default, *, key, **kwargs):
    model_key='table:'+key
    base_key='editor_base:'+key
    if base_key not in st.session_state or key not in st.session_state:
        st.session_state[base_key]=st.session_state.get(model_key,default.to_dict('records'))
    source=st.session_state[base_key]
    frame=st.data_editor(pd.DataFrame(source,columns=default.columns),key=key,**kwargs)
    # The result, not Streamlit's editor delta, is the portable source of truth.
    st.session_state[model_key]=json.loads(frame.to_json(orient='records',date_format='iso'))
    return frame


def widget(kind, *args, **kwargs):
    """Check restored values against the actual widget's options and bounds."""
    container=kwargs.pop('container',st)
    key=kwargs['key']
    if key in st.session_state:
        value=st.session_state[key]
        valid=True
        if kind in {'selectbox','radio','select_slider','multiselect'}:
            options=args[1] if len(args)>1 else kwargs['options']
            valid=all(v in options for v in value) if kind=='multiselect' else value in options
        if kind in {'number_input','slider','date_input'}:
            lower=kwargs.get('min_value', args[1] if len(args)>1 and kind!='date_input' else None)
            upper=kwargs.get('max_value', args[2] if len(args)>2 and kind!='date_input' else None)
            items=value if isinstance(value,(list,tuple)) else [value]
            valid=all((lower is None or v>=lower) and (upper is None or v<=upper) for v in items)
            if kind=='slider':
                default=kwargs.get('value',args[3] if len(args)>3 else lower)
                is_range=isinstance(default,(tuple,list))
                valid=valid and (isinstance(value,(tuple,list))==is_range)
                if is_range: valid=valid and len(items)==2 and items[0]<=items[1]
                if type(lower) is int:
                    valid=valid and all(float(v).is_integer() for v in items)
                    if valid: value=tuple(int(v) for v in items) if is_range else int(value)
            if valid and isinstance(value,list): value=tuple(value)
            if valid and (type(value) is not type(st.session_state[key]) or value != st.session_state[key]): st.session_state[key]=value
        if not valid:
            del st.session_state[key]
            st.warning(f'Restored {args[0]} was outside its supported range; using the default.')
    return getattr(container,kind)(*args,**kwargs)


def apply_workspace(raw, state):
    data=decode_workspace(raw)
    for key in list(state):
        if key in SPECS or key in TABLES or key.startswith(('table:','editor_base:','fx:')):
            del state[key]
    state.update(data['inputs'])
    for key,rows in data['tables'].items(): state['table:'+key]=rows


def workspace_controls():
    # Keep keyed controls alive when their page is not rendered.
    for key in list(st.session_state):
        if key in SPECS or key.startswith('fx:'):
            st.session_state[key]=st.session_state[key]
    st.sidebar.markdown('## ◈ FIXED INCOME')
    st.sidebar.caption('ANALYTICS TERMINAL / 02')
    widget('radio','Workspace',WORKSPACES,key='navigation',container=st.sidebar)
    with st.sidebar.expander('Workspace save / restore'):
        def restore():
            upload=st.session_state.get('workspace_upload')
            if upload is None: return
            try:
                apply_workspace(upload.getvalue(),st.session_state)
                st.session_state['workspace_message']='Workspace restored.'
            except (ValueError,TypeError,UnicodeDecodeError) as exc:
                st.session_state['workspace_message']=f'Workspace was not restored: {exc}'
        st.file_uploader('Restore workspace JSON',type=['json'],key='workspace_upload',on_change=restore)
        if 'workspace_message' in st.session_state: st.caption(st.session_state['workspace_message'])
        st.caption('Includes instrument inputs, visited workspace controls, holdings, FX, curves, and named scenarios. JSON files contain your manual financial inputs.')


def workspace_download():
    inputs={k:st.session_state[k] for k in st.session_state if k in SPECS or k.startswith('fx:')}
    tables={k:st.session_state['table:'+k] for k in TABLES if 'table:'+k in st.session_state}
    with st.sidebar:
        st.download_button('Save workspace JSON',encode_workspace(inputs,tables),'bond_workspace.json','application/json')
