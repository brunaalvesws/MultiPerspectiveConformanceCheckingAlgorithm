# -*- coding: utf-8 -*-

import pandas as pd
from Declare4Py.ProcessModels.DeclareModel import DeclareModel
from Declare4Py.D4PyEventLog import D4PyEventLog
import pm4py
from xml.etree import ElementTree as ET
from datetime import datetime
import re
import tempfile

def normalize_xes_timestamps_to_tempfile(xes_path: str) -> str: 
    tree = ET.parse(xes_path)
    root = tree.getroot()
    ns = {"xes": "http://www.xes-standard.org/"}

    for date_elem in root.findall(".//xes:date", ns):
        value = date_elem.attrib.get("value")
        if not value:
            continue

        # separa timezone (Z ou +hh:mm)
        tz_match = re.search(r"(Z|[+-]\d{2}:\d{2})$", value)
        tz = tz_match.group(1) if tz_match else "+00:00"

        # remove timezone temporariamente
        value_no_tz = re.sub(r"(Z|[+-]\d{2}:\d{2})$", "", value)

        # corta fração para no máximo 6 dígitos
        value_no_tz = re.sub(
            r"\.(\d{6})\d+",
            r".\1",
            value_no_tz
        )

        # se não tiver fração, adiciona .000000
        if "." not in value_no_tz:
            value_no_tz += ".000000"

        # valida
        dt = datetime.strptime(value_no_tz, "%Y-%m-%dT%H:%M:%S.%f")

        # reconstroi com timezone
        date_elem.attrib["value"] = dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + tz

    tmp = tempfile.NamedTemporaryFile(
        mode="wb",
        suffix=".xes",
        delete=False
    )
    tree.write(tmp, encoding="utf-8", xml_declaration=True)
    tmp.close()

    return tmp.name


def pre_process_data(process_log_path, access_log_path, model_log_path, process_model_path, access_model_path):
    #temp_xes_path = normalize_xes_timestamps_to_tempfile(access_log_path)
    access_log = pm4py.read_xes(str(access_log_path))
    processed_access_log = access_log.sort_values(['case:concept:name', 'concept:instance'])
    processed_process_model = pd.read_csv(model_log_path, sep=';')
    processed_access_model = pd.read_csv(access_model_path, sep=';')
    declare_model = DeclareModel().parse_from_file(process_model_path)
    event_log = D4PyEventLog(case_name="case:concept:name")
    #temp_xes_path = normalize_xes_timestamps_to_tempfile(process_log_path)
    event_log.parse_xes_log(str(process_log_path))
    allowed_activities = extract_allowed_activities(process_model_path)
    return event_log, processed_access_log, processed_process_model, declare_model, processed_access_model, allowed_activities


def extract_allowed_activities(declare_filepath):
    allowed_activities = set()

    with open(declare_filepath, 'r', encoding='utf-8') as f:
        for line in f:
            clean_line = line.strip()
            if clean_line.startswith('activity '):
                activity_name = clean_line[len('activity '):].strip()
                if activity_name:
                    allowed_activities.add(activity_name)

    return allowed_activities
