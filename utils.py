import json

import pandas as pd

def series_to_list(series):
    return series.values.tolist()

def load_json(filename):
    with open(filename,'r') as file:
        data = json.load(file)
    return data


def datum_to_dataframe(data, col_name):
    return pd.DataFrame([
        {
            "end": datum.end,
            "accn": datum.accn,
            "form": datum.form,
            "filed": datum.filed,
            "frame": datum.frame,
            col_name: datum.val
        }
        for datum in data
    ])
