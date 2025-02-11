#!/usr/bin/env python

from flask import Flask, make_response
from flask_restful import Api, Resource
import time
import datetime
from datetime import date, timedelta
from simplexml import dumps
import os
import sys
import requests
import xml.etree.ElementTree as ET  # for parsing XML
from pathlib import Path
import logging

app = Flask(__name__)
api = Api(app)

host = os.environ.get('HOST')

class commands(Resource):
    def get(self, command1, mac1, command2, mac2, command3, mac3, command4, mac4):

        results = {command1: None, command2: None, command3: None, command4: None}
        watchdog_path = os.environ.get('WATCHDOG_PATH')

        with open("cmds-results/commands.txt", "w+") as fileObject:
            fileObject.write(f"{command1}={mac1}\n")
            fileObject.write(f"{command2}={mac2}\n")
            fileObject.write(f"{command3}={mac3}\n")
            fileObject.write(f"{command4}={mac4}\n")

        print(f"{datetime.datetime.now()} {host}: Commands file created - waiting 30 seconds for command clients to respond (to create results files).")
        time.sleep(30)

        try:
            for key in results:
                file_path = os.path.join(watchdog_path, key + "Result.txt")
                if Path(file_path).exists():
                    print(f"{datetime.datetime.now()} {host}: {key}Result.txt exists. Result will now be extracted.")
                    with open(file_path, "r") as fileObject:
                        result = fileObject.read()
                        if 'success' in result:
                            results[key] = 'success'
                        else:
                            results[key] = 'failure'
                    os.remove(file_path)
                    print(f"{datetime.datetime.now()} {host}: {key}Result.txt deleted.")
                else:
                    print(f"{datetime.datetime.now()} {host}: {key}Result.txt doesn't exist. Response on the API will be negative.")
        except Exception as error:
            logging.exception(f"{host}: Exception while reading result files.")
            print(f"{datetime.datetime.now()} {host}: Got error while reading 4 files")

        @api.representation('application/xml')
        def output_xml(data, code, headers=None):
            resp = make_response(dumps({'monitor': data}), code)
            resp.headers.extend(headers or {})
            return resp

        return {
            command1: {"hostname": command1, "commandType": "MAC-change", "commandValue": mac1, "commandResult": results[command1]},
            command2: {"hostname": command2, "commandType": "MAC-change", "commandValue": mac2, "commandResult": results[command2]},
            command3: {"hostname": command3, "commandType": "MAC-change", "commandValue": mac3, "commandResult": results[command3]},
            command4: {"hostname": command4, "commandType": "MAC-change", "commandValue": mac4, "commandResult": results[command4]},
        }

    def post(self):
        return {"data": "Posted"}

class command(Resource):
    def get(self):
        return {"Error": "Missing double arguments."}

class systematic(Resource):
    def get(self, seconds):
        """
        1. Lav en SOAP-forespørgsel med MATCH_objectClass i stedet for MATCH_epc
        2. Svaret indeholder >1000 tags. Iterer over alle tags og tjek, om et tag har et
           <recordTime> der er nyere end det angivne antal sekunder (f.eks. 900).
           - Ved fund returneres OK (success)
           - Hvis ingen tag er opdateret indenfor threshold returneres FAIL (failure)
        """
        try:
            accepted_delay = int(seconds)
        except ValueError:
            sys.exit(f"{datetime.datetime.now()} {host}: Received wrong input for seconds. Expected an integer. Will now exit.")

        track_api_url = os.environ.get('TRACK_SERVICES_API_URL')
        headers = {'content-type': 'text/xml'}

        # --- Ny SOAP-forespørgsel med MATCH_objectClass parameter ---
        body = """<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <epcis:Poll xmlns:epcis="urn:epcglobal:epcis-query:xsd:1">
            <queryName xmlns="">SimpleEventQuery</queryName>
            <params xmlns="">
                <param>
                    <name>eventType</name>
                    <value xsi:type="epcis:ArrayOfString">
                        <string>ObjectEvent</string>
                    </value>
                </param>
                <param>
                    <name>EQ_action</name>
                    <value xsi:type="epcis:ArrayOfString">
                        <string>OBSERVE</string>
                    </value>
                </param>
                <param>
                    <name>EQ_bizStep</name>
                    <value xsi:type="epcis:ArrayOfString">
                        <string>urn:Servicelogistics:bizstep:locations_changed</string>
                    </value>
                </param>
                <param>
                    <name>MATCH_objectClass</name>
                    <value xmlns:ns="urn:epcglobal:epcis-query:xsd:1" xsi:type="ns:ArrayOfString">
                        <string xmlns="">urn:servicelogistics:object:class:alarm</string>
                    </value>
                </param>
                <param>
                    <name>WD_bizLocation</name>
                    <value xsi:type="epcis:ArrayOfString">
                        <string>urn:epc:id:sgln:57980100.3584.0</string>
                    </value>
                </param>
                <param>
                    <name>mostRecent</name>
                    <value xsi:type="xsd:boolean">true</value>
                </param>
            </params>
        </epcis:Poll>
    </s:Body>
</s:Envelope>"""

        try:
            print(f"{datetime.datetime.now()} {host}: Requesting Track API for tags with objectClass alarm.")
            response = requests.post(track_api_url, data=body, headers=headers)
            print(f"{datetime.datetime.now()} {host}: Response from Track API received.")
            responseXML = ET.fromstring(response.content)
        except Exception as error:
            print(f"{datetime.datetime.now()} {host}: API request failed. Exception:")
            print(error)
            @api.representation('application/xml')
            def output_xml(data, code, headers=None):
                resp = make_response(dumps({'monitor': data}), code)
                resp.headers.extend(headers or {})
                return resp
            return {
                "commandType": "positioningDelayTest",
                "communicationWithAPI": "failure",
                "commandResult": "none",
                "commandValue": "N/A"
            }

        # --- Gennemløb af alle ObjectEvent-elementer for at finde et opdateret tag ---
        success_found = False
        delay_seconds = None
        latitude_val = None
        longitude_val = None

        # Prøv at finde ObjectEvent-elementerne – de kan være uden eller med namespace
        object_events = responseXML.findall('.//ObjectEvent')
        if not object_events:
            ns = {'ns': 'urn:epcglobal:epcis-query:xsd:1'}
            object_events = responseXML.findall('.//ns:ObjectEvent', ns)

        for event in object_events:
            rt_elem = event.find('recordTime')
            if rt_elem is None:
                continue
            rt_text = rt_elem.text
            try:
                try:
                    record_time = datetime.datetime.strptime(rt_text, "%Y-%m-%dT%H:%M:%S.%f")
                except ValueError:
                    record_time = datetime.datetime.strptime(rt_text, "%Y-%m-%dT%H:%M:%S")
            except Exception as e:
                print(f"{datetime.datetime.now()} {host}: Error parsing recordTime: {e}")
                continue

            current_time = datetime.datetime.now(datetime.timezone.utc)
            time_delta = current_time - record_time

            if time_delta < timedelta(seconds=accepted_delay):
                success_found = True
                delay_seconds = int(time_delta.total_seconds())
                # Udtræk position (Latitude og Longitude) – husk at positionselementet er navngivet med et namespace
                lat_elem = event.find('.//{http://schemas.systematic.com/2015/02/Epcis}Latitude')
                lon_elem = event.find('.//{http://schemas.systematic.com/2015/02/Epcis}Longitude')
                if lat_elem is not None:
                    latitude_val = lat_elem.text
                if lon_elem is not None:
                    longitude_val = lon_elem.text
                break  # Stop, så snart et opdateret tag er fundet

        @api.representation('application/xml')
        def output_xml(data, code, headers=None):
            resp = make_response(dumps({'monitor': data}), code)
            resp.headers.extend(headers or {})
            return resp

        if success_found:
            print(f"{datetime.datetime.now()} {host}: SUCCESS: Found a tag with recordTime within {accepted_delay} seconds (delay: {delay_seconds} seconds).")
            google_map_url = ""
            if latitude_val and longitude_val:
                google_map_url = f"https://www.google.com/maps/search/?api=1&query={latitude_val}%2C{longitude_val}"
            return {
                "commandType": "positioningDelayTest",
                "communicationWithAPI": "success",
                "commandResult": "success",
                "commandValue": "urn:servicelogistics:object:class:alarm",
                "positioningDelayInSeconds": delay_seconds,
                "Latitude": latitude_val,
                "Longitude": longitude_val,
                "GoogleMAP": google_map_url
            }
        else:
            print(f"{datetime.datetime.now()} {host}: FAILURE: No tag with recordTime updated within {accepted_delay} seconds found.")
            return {
                "commandType": "positioningDelayTest",
                "communicationWithAPI": "success",
                "commandResult": "failure",
                "commandValue": "urn:servicelogistics:object:class:alarm"
            }


# Registrer API‑endpoints
api.add_resource(command, "/commands")
api.add_resource(commands, "/commands/<string:command1>/<string:mac1>/<string:command2>/<string:mac2>/<string:command3>/<string:mac3>/<string:command4>/<string:mac4>")
api.add_resource(systematic, "/commands/systematic/<string:mac>/<string:seconds>")

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
