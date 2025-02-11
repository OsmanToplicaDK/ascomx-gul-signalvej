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

        # Get environment variable with path to folder to watch
        watchdog_path = os.environ.get('WATCHDOG_PATH')

        # Create commands file and write MAC-addresses to machines by their name. Files will
        # be synced by file system to servers which runs the command 
        self.fileObject = open("cmds-results/commands.txt", "w+")
        self.fileObject.write(command1 + "=" + mac1 + "\n")
        self.fileObject.write(command2 + "=" + mac2 + "\n")
        self.fileObject.write(command3 + "=" + mac3 + "\n")
        self.fileObject.write(command4 + "=" + mac4 + "\n")
        self.fileObject.close()

        print(str(datetime.datetime.now()) + ' ' + host + ': Commands file created - waiting 30 seconds for command clients to respond (to create results files).')
        time.sleep(30)

        # Check for results files from command clients
        try:
           for key in results:
               if Path(watchdog_path + key + "Result.txt").exists():
                   print(str(datetime.datetime.now()) + ' ' + host + ': ' + key + 'Result.txt exist. Result will now be extracted.')
                   fileObject = open(watchdog_path + key + "Result.txt", "r")
                   if fileObject.mode == "r":
                       result = fileObject.read()

                       if 'success' in result:
                           results.update({key:'success'})

                           #for item in results:
                                #print(str(datetime.datetime.now()) + " Key: {}, Value: {}".format(item,results[item]))
                       else:
                           results.update({key:'failure'})
                       
                       fileObject.close()

                       # Delete file
                       os.remove(watchdog_path + key + "Result.txt")
                       print(str(datetime.datetime.now()) + ' ' + host + ': ' + key + 'Result.txt deleted.')
               else:
                   print(str(datetime.datetime.now()) + ' ' + host + ': ' + key + 'Result.txt doesn\'t exist. Response on the API will be negative.')
        except Exception as error:
            logging.exception(host + ': This is all shit - see what happened')
            print(str(datetime.datetime.now()) + ' ' + host + ': Got error while reading 4 files')

        # Return XML instead of standard JSON (for EventHandler to know about results)
        @api.representation('application/xml')
        def output_xml(data, code, headers=None):
            resp = make_response(dumps({'monitor': data}), code)
            resp.headers.extend(headers or {})
            return resp

        return {
                command1: {"hostname": command1, "commandType": "MAC-change", "commandValue": mac1, "commandResult": list(results.values())[0]},
                command2: {"hostname": command2, "commandType": "MAC-change", "commandValue": mac2, "commandResult": list(results.values())[1]},
                command3: {"hostname": command3, "commandType": "MAC-change", "commandValue": mac3, "commandResult": list(results.values())[2]},
                command4: {"hostname": command4, "commandType": "MAC-change", "commandValue": mac4, "commandResult": list(results.values())[3]},
               }

    def post(self):
        return {"data": "Posted"}

class command(Resource):
    def get(self):
        return {"Error": "Missing double arguments."}

class systematic(Resource):
    def get(self, mac, seconds):
        
        """ Get environment variable for Track Services API and build request """
        mac = mac.replace(":", "") 
        try:
            seconds = int(seconds)
        except ValueError:
            sys.exit(str(datetime.datetime.now()) + ' ' + host + ': Received wrong input for seconds. Expected a number (integer). Will now exit.')
        track_api_url = os.environ.get('TRACK_SERVICES_API_URL')
        headers = {'content-type': 'text/xml'}
        body = f"""<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
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
                <name>MATCH_epc</name>
                <value xsi:type="epcis:ArrayOfString">
                <string>urn:dev:mac.{mac}</string>
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

        """ GET Systematic Track API with SOAP request and look for specific time stamp """
        try:
            print(str(datetime.datetime.now()) + ' ' + host + ': Requesting Track API for delay and position for device with MAC: ' + mac)
            response = requests.post(track_api_url,data=body,headers=headers)
            print(str(datetime.datetime.now()) + ' ' + host + ': Response from Track API:')
            
            ## Decides if system is running in production or decelopment environments
            responseXML = ET.fromstring(response.content)
            #responseXML = ET.fromstring(responseTest) # For testing without access to API
        
            ## TODO Pretty print XML to console 
            #responseXML.indent(response.content)
            #print(ET.tostring(responseXML, encoding='unicode'))

            # For testing without access to API
            responseTest = f"""<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
                <s:Body xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                    <QueryResults xmlns="urn:epcglobal:epcis-query:xsd:1">
                        <queryName xmlns="">SimpleEventQuery</queryName>
                        <subscriptionID xmlns="">subscriptionID</subscriptionID>
                        <resultsBody xmlns="">
                            <EventList>
                                <ObjectEvent>
                                    <eventTime>2021-09-11T09:30:25.773</eventTime>
                                    <recordTime>2021-08-10T14:53:26.063</recordTime>
                                    <eventTimeZoneOffset>+02:00</eventTimeZoneOffset>
                                    <epcList>
                                        <epc>urn:dev:mac.000ccc0d1b0c</epc>
                                    </epcList>
                                    <action>OBSERVE</action>
                                    <bizStep>urn:ServiceLogistics:bizstep:locations_changed</bizStep>
                                    <bizLocation>
                                        <id>urn:epc:id:sgln:57980102.6456.0</id>
                                    </bizLocation>
                                    <Position xmlns="http://schemas.systematic.com/2015/02/Epcis">
                                        <Latitude>56.1915521807393</Latitude>
                                        <Longitude>10.164439060826641</Longitude>
                                        <Floor>2</Floor>
                                    </Position>
                                    <Locations xmlns="http://schemas.systematic.com/2015/02/Epcis">
                                        <LocationId Index="0">urn:epc:id:sgln:57980102.6456.0</LocationId>
                                        <LocationId Index="1">urn:epc:id:sgln:57980102.2866.0</LocationId>
                                        <LocationId Index="2">urn:epc:id:sgln:57980102.2916.0</LocationId>
                                        <LocationId Index="3">urn:epc:id:sgln:57980102.2711.0</LocationId>
                                        <LocationId Index="4">urn:epc:id:sgln:57980101.3348.0</LocationId>
                                        <LocationId Index="5">urn:epc:id:sgln:57980100.3584.0</LocationId>
                                    </Locations>
                                </ObjectEvent>
                            </EventList>
                        </resultsBody>
                    </QueryResults>
                </s:Body>
            </s:Envelope>"""

        except Exception as error:
            print(str(datetime.datetime.now()) + ' ' + host + ': API request did not work. Exception says: ')
            print(error.__dict__)

            # Return XML instead of standard JSON 
            @api.representation('application/xml')
            def output_xml(data, code, headers=None):
                resp = make_response(dumps({'monitor': data}), code)
                resp.headers.extend(headers or {})
                return resp
            
            return {"commandType" : "positioningDelayTest", "communicationWithAPI" : "failure", "commandResult": "none", "commandValue" : mac}

        """ Compare time stamp with current time - if too old, then report slow processing of positioning 

            The eventTime is the time where a tracking system (in this case Cisco CMX) has tracked the device. 
            The time is reported to Track Service and exposed on the Track API. 
            A recordTime event also exists which is the time Track Service received the event from the tracking system.
        """
        # Check responseXML for recordTime, latitude and longitude tags. If not then inform API visitor and log.        
        for recordTime in responseXML.iter('recordTime'):              
            print(str(datetime.datetime.now()) + ' ' + host + ': recordTime received from Track API: ' + recordTime.text)
            try:
                recordTimeFormatted = datetime.datetime.strptime(recordTime.text, "%Y-%m-%dT%H:%M:%S.%f")
            except ValueError:
                recordTimeFormatted = datetime.datetime.strptime(recordTime.text, "%Y-%m-%dT%H:%M:%S")

            timeNow = datetime.datetime.utcnow()
            timeDelta = timeNow - recordTimeFormatted
            
            accepted_delay = seconds

            if timeDelta > datetime.timedelta(seconds=accepted_delay):
                print(str(datetime.datetime.now()) + ' ' + host + ": FAILURE: API is delayed more than the allowed {} seconds. Delay is {} seconds.".format(accepted_delay, int(timeDelta.total_seconds())))
                commandResult = "failure"
            else:
                print(str(datetime.datetime.now()) + ' ' + host + ": SUCCESS: API is not delayed")
                commandResult = "success"

            # Expose longitude & latitude
            for longitude in responseXML.findall('.//{http://schemas.systematic.com/2015/02/Epcis}Longitude'):
                print(str(datetime.datetime.now()) + ' ' + host + ': Longitude: ' + longitude.text) 

            for latitude in responseXML.findall('.//{http://schemas.systematic.com/2015/02/Epcis}Latitude'):
                print(str(datetime.datetime.now()) + ' ' + host + ': Latitude: ' + latitude.text) 

            """ Return result back to own API visitor in XML """ 
            # Return XML instead of standard JSON 
            @api.representation('application/xml')
            def output_xml(data, code, headers=None):
                resp = make_response(dumps({'monitor': data}), code)
                resp.headers.extend(headers or {})
                return resp

            # Return positive result since recordTime, latitude and longitude was found in responseXML
            return {"commandType" : "positioningDelayTest", "communicationWithAPI" : "success", "commandResult": commandResult, "commandValue" : mac, "positioningDelayInSeconds" : int(timeDelta.total_seconds()), "Latitude" : latitude.text, "Longitude" : longitude.text, "GoogleMAP" : "https://www.google.com/maps/search/?api=1&query=" + latitude.text + "%2C" + longitude.text }


        """ Return failure since recordTime wasn't found in returned response """
        # Return XML instead of standard JSON 
        @api.representation('application/xml')
        def output_xml(data, code, headers=None):
            resp = make_response(dumps({'monitor': data}), code)
            resp.headers.extend(headers or {})
            return resp
        
        # Return 'negative' since response didn't contain result for the supplied MAC-address = the MAC-address was unknown or a position wasn't available
        return {"commandType" : "positioningDelayTest", "communicationWithAPI" : "negative", "commandResult": "none", "commandValue" : mac}
       

api.add_resource(command, "/commands")
api.add_resource(commands, "/commands/<string:command1>/<string:mac1>/<string:command2>/<string:mac2>/<string:command3>/<string:mac3>/<string:command4>/<string:mac4>")
api.add_resource(systematic, "/commands/systematic/<string:mac>/<string:seconds>")


if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0')
