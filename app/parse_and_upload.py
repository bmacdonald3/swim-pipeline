#!/usr/bin/env python3
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

import pyodbc

NS = {
    "ns5": "http://www.faa.aero/nas/3.0",
    "ns2": "http://www.fixm.aero/base/3.0",
}

ENV_PATH = os.environ.get("SWIMCTL_ENV", "/home/bmacdonald3/.swimctl_env")

def load_env(path: str) -> None:
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)

def azure_conn_str() -> str:
    # Prefer env vars; fall back to existing values if you really want to.
    server = os.environ.get("AZURE_SQL_SERVER")
    db     = os.environ.get("AZURE_SQL_DATABASE")
    user   = os.environ.get("AZURE_SQL_USER")
    pwd    = os.environ.get("AZURE_SQL_PASSWORD")

    missing = [k for k in ["AZURE_SQL_SERVER","AZURE_SQL_DATABASE","AZURE_SQL_USER","AZURE_SQL_PASSWORD"] if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Missing env vars: {missing} (check {ENV_PATH})")

    return (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER=tcp:{server},1433;"
        f"DATABASE={db};"
        f"UID={user};"
        f"PWD={pwd};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

def connect_azure():
    cs = azure_conn_str()
    return pyodbc.connect(cs)

def parse_flight_message(xml_string: str):
    try:
        root = ET.fromstring(xml_string)
        flight = root.find(".//ns5:flight", NS)
        if flight is None:
            return None

        data = {
            "timestamp": flight.get("timestamp"),
            "center": flight.get("centre"),
        }

        flight_id = flight.find(".//ns5:flightIdentification", NS)
        if flight_id is not None:
            data["callsign"] = flight_id.get("aircraftIdentification")
            data["computer_id"] = flight_id.get("computerId")

        departure = flight.find(".//ns5:departurePoint", NS)
        if departure is not None:
            data["departure"] = departure.text

        arrival = flight.find(".//ns5:arrivalPoint", NS)
        if arrival is not None:
            data["arrival"] = arrival.text

        pos = flight.find(".//ns2:pos", NS)
        if pos is not None and pos.text:
            coords = pos.text.split()
            if len(coords) == 2:
                data["latitude"] = float(coords[0])
                data["longitude"] = float(coords[1])

        altitude = flight.find(".//ns2:altitude", NS)
        if altitude is not None and altitude.text:
            try:
                data["altitude"] = int(float(altitude.text))
            except Exception:
                pass

        speed = flight.find(".//ns2:speed", NS)
        if speed is not None and speed.text:
            try:
                data["speed"] = int(float(speed.text))
            except Exception:
                pass

        status = flight.find(".//ns5:fdpsFlightStatus", NS)
        if status is not None:
            data["status"] = status.text

        operator = flight.find(".//ns2:organization", NS)
        if operator is not None:
            data["operator"] = operator.get("name")

        return data
    except Exception:
        return None

def upload_to_azure(conn, flight_data: dict) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO flights
              (timestamp, callsign, departure, arrival, latitude, longitude,
               altitude, speed, status, operator, center)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                flight_data.get("timestamp"),
                flight_data.get("callsign"),
                flight_data.get("departure"),
                flight_data.get("arrival"),
                flight_data.get("latitude"),
                flight_data.get("longitude"),
                flight_data.get("altitude"),
                flight_data.get("speed"),
                flight_data.get("status"),
                flight_data.get("operator"),
                flight_data.get("center"),
            ),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[ERROR] Upload error: {e}", file=sys.stderr)
        return False

def process_xml_file(filename: str, conn) -> int:
    if not os.path.exists(filename):
        print(f"[ERROR] File not found: {filename}", file=sys.stderr)
        return 0

    with open(filename, "r", errors="ignore") as f:
        content = f.read()

    print(f"[INFO] XML file size: {len(content)} chars")

    messages = re.findall(r"<message[^>]*>.*?</message>", content, re.DOTALL)
    print(f"[INFO] Found {len(messages)} <message> blocks")

    count = 0
    for i, msg in enumerate(messages):
        xml_msg = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<ns5:MessageCollection xmlns:ns5="http://www.faa.aero/nas/3.0" '
            'xmlns:ns2="http://www.fixm.aero/base/3.0" '
            'xmlns:ns3="http://www.fixm.aero/flight/3.0" '
            'xmlns:ns4="http://www.fixm.aero/foundation/3.0">'
            + msg +
            "</ns5:MessageCollection>"
        )

        flight_data = parse_flight_message(xml_msg)

        if i < 3:
            print(f"[DEBUG] Message {i} parsed: {flight_data}")

        if flight_data and flight_data.get("callsign"):
            if upload_to_azure(conn, flight_data):
                count += 1
                print(f"[{count}] {flight_data.get('callsign')} - {flight_data.get('departure')} → {flight_data.get('arrival')}")

    return count

def write_last_success() -> None:
    try:
        with open("/home/bmacdonald3/.swimctl_last_success", "w") as f:
            f.write(datetime.utcnow().isoformat() + "Z\n")
    except Exception as e:
        print(f"[WARN] Could not write last success file: {e}", file=sys.stderr)

def main():
    load_env(ENV_PATH)

    xml_path = os.environ.get("SWIM_XML_PATH", "/home/bmacdonald3/flight_stream.xml")
    print("[INFO] Connecting to Azure SQL...")
    conn = connect_azure()
    print("[INFO] Connected. Processing:", xml_path)

    uploaded = process_xml_file(xml_path, conn)
    conn.close()

    print(f"[INFO] Uploaded {uploaded} rows to Azure")
    if uploaded > 0:
        write_last_success()

if __name__ == "__main__":
    main()
