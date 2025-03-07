#!/usr/bin/env python
import os
from flask import Flask, Response

app = Flask(__name__)

@app.route('/mock', methods=['POST'])
def mock_api():
    # Angiv stien til din XML-fil med testpayloaden
    xml_file_path = os.path.join(os.getcwd(), 'test_payload.xml')
    
    # Tjek om filen eksisterer
    if not os.path.exists(xml_file_path):
        return Response("XML-fil ikke fundet", status=404)
    
    # Læs XML-indholdet
    with open(xml_file_path, 'r', encoding='utf-8') as file:
        xml_content = file.read()
    
    # Returner XML-indholdet med den korrekte Content-Type
    return Response(xml_content, mimetype='text/xml')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
